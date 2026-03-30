from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .contracts import DronePlatformSpec, DroneState, MixerIntent

_BDE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Battery_Dynamics_Engine")
if os.path.isdir(_BDE_PATH) and _BDE_PATH not in sys.path:
    sys.path.insert(0, _BDE_PATH)


def _import_battery_symbols():
    try:
        from battery_dynamics import BatteryState, ECMParams, step_ecm, terminal_voltage

        return BatteryState, ECMParams, step_ecm, terminal_voltage
    except Exception:
        return None, None, None, None


@dataclass(frozen=True)
class DroneBatteryBridgeConfig:
    nominal_pack_voltage_v: float = 22.2
    propulsion_efficiency_0_1: float = 0.86
    hover_power_fraction_0_1: float = 0.58
    max_power_w_per_kg: float = 220.0


@dataclass(frozen=True)
class DroneBatteryBridgeOutput:
    battery_state: Any
    estimated_current_a: float
    terminal_voltage_v: float
    soc_0_1: float
    diagnostics: Dict[str, float]


def estimate_propulsion_power_w(
    mixer: MixerIntent,
    spec: DronePlatformSpec,
    cfg: DroneBatteryBridgeConfig = DroneBatteryBridgeConfig(),
) -> float:
    """
    Rough multicopter propulsion power proxy.

    We keep this intentionally simple and monotonic: collective thrust dominates
    power, while attitude torques contribute a small extra penalty.
    """

    collective = max(0.0, min(1.0, float(mixer.collective_thrust_0_1)))
    torque_penalty = (
        abs(float(mixer.roll_torque_cmd_0_1))
        + abs(float(mixer.pitch_torque_cmd_0_1))
        + 0.5 * abs(float(mixer.yaw_torque_cmd_0_1))
    )
    normalized = max(0.0, min(1.2, collective + 0.15 * torque_penalty))
    hover_bias = cfg.hover_power_fraction_0_1
    scale = hover_bias + (1.0 - hover_bias) * normalized
    return max(0.0, spec.mass_kg * cfg.max_power_w_per_kg * scale)


def estimate_current_draw_a(
    mixer: MixerIntent,
    spec: DronePlatformSpec,
    cfg: DroneBatteryBridgeConfig = DroneBatteryBridgeConfig(),
) -> float:
    power_w = estimate_propulsion_power_w(mixer, spec, cfg)
    voltage = max(1e-6, cfg.nominal_pack_voltage_v)
    eta = max(0.1, min(1.0, cfg.propulsion_efficiency_0_1))
    return power_w / (voltage * eta)


def advance_battery_from_mixer(
    battery_state: Any,
    battery_params: Any,
    mixer: MixerIntent,
    spec: DronePlatformSpec,
    dt_s: float,
    cfg: DroneBatteryBridgeConfig = DroneBatteryBridgeConfig(),
) -> DroneBatteryBridgeOutput:
    BatteryState, ECMParams, step_ecm, terminal_voltage = _import_battery_symbols()
    if BatteryState is None or ECMParams is None or step_ecm is None or terminal_voltage is None:
        raise ImportError("battery_dynamics is not available")

    if not isinstance(battery_state, BatteryState):
        raise TypeError("battery_state must be battery_dynamics.BatteryState")
    if not isinstance(battery_params, ECMParams):
        raise TypeError("battery_params must be battery_dynamics.ECMParams")

    current_a = estimate_current_draw_a(mixer, spec, cfg)
    next_state = step_ecm(battery_state, current_a, dt_s, battery_params)
    v_term = terminal_voltage(next_state, current_a, battery_params)
    return DroneBatteryBridgeOutput(
        battery_state=next_state,
        estimated_current_a=current_a,
        terminal_voltage_v=v_term,
        soc_0_1=max(0.0, min(1.0, float(next_state.soc))),
        diagnostics={
            "power_w": estimate_propulsion_power_w(mixer, spec, cfg),
            "nominal_pack_voltage_v": cfg.nominal_pack_voltage_v,
            "propulsion_efficiency_0_1": cfg.propulsion_efficiency_0_1,
        },
    )


def patch_drone_state_soc(
    drone_state: DroneState,
    battery_bridge: DroneBatteryBridgeOutput,
) -> DroneState:
    return DroneState(
        time_s=drone_state.time_s,
        pn_m=drone_state.pn_m,
        pe_m=drone_state.pe_m,
        pd_m=drone_state.pd_m,
        vn_mps=drone_state.vn_mps,
        ve_mps=drone_state.ve_mps,
        vd_mps=drone_state.vd_mps,
        roll_rad=drone_state.roll_rad,
        pitch_rad=drone_state.pitch_rad,
        yaw_rad=drone_state.yaw_rad,
        p_rps=drone_state.p_rps,
        q_rps=drone_state.q_rps,
        r_rps=drone_state.r_rps,
        battery_soc_0_1=battery_bridge.soc_0_1,
    )
