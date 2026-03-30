from __future__ import annotations

import math
from typing import Optional, Tuple

from .arbiter import evaluate_control_arbitration
from .contracts import (
    ControlGains,
    ControlTickResult,
    DronePlatformSpec,
    DroneSetpoint,
    DroneState,
    GeofenceConfig,
)
from .mixer import build_mixer_intent, total_thrust_n
from .reference_plant import integrate_vertical_yaw_reference


def _normalize_angle(a: float) -> float:
    return (a + math.pi) % (2 * math.pi) - math.pi


def _hover_collective_0_1(spec: DronePlatformSpec) -> float:
    return max(0.0, min(1.0, (spec.mass_kg * spec.gravity_mps2) / max(spec.max_total_thrust_n, 1e-6)))


def _attitude_commands(
    state: DroneState,
    setpoint: DroneSetpoint,
    gains: ControlGains,
) -> Tuple[float, float, float]:
    """Returns roll_cmd, pitch_cmd, yaw_torque_cmd (normalized torque channels)."""
    yaw_err = _normalize_angle(setpoint.yaw_rad_target - state.yaw_rad)
    yaw_cmd = max(-1.0, min(1.0, gains.yaw_kp * yaw_err / math.pi))

    roll_cmd = 0.0
    pitch_cmd = 0.0
    if setpoint.mode == "position_hold" and setpoint.pn_m_target is not None and setpoint.pe_m_target is not None:
        en = setpoint.pn_m_target - state.pn_m
        ee = setpoint.pe_m_target - state.pe_m
        psi = state.yaw_rad
        # desired NED velocity from position error
        vn_des = gains.pos_kp * en
        ve_des = gains.pos_kp * ee
        # map to body forward / right
        c, s = math.cos(psi), math.sin(psi)
        vx_des = c * vn_des + s * ve_des
        vy_des = -s * vn_des + c * ve_des
        # small-angle: pitch for forward (body +X), roll for right (+Y)
        pitch_cmd = max(
            -gains.max_tilt_cmd_rad,
            min(gains.max_tilt_cmd_rad, 0.12 * vx_des),
        )
        roll_cmd = max(
            -gains.max_tilt_cmd_rad,
            min(gains.max_tilt_cmd_rad, -0.12 * vy_des),
        )

    return roll_cmd, pitch_cmd, yaw_cmd


def run_control_tick(
    state: DroneState,
    setpoint: DroneSetpoint,
    spec: DronePlatformSpec,
    fence: GeofenceConfig,
    dt_s: float,
    *,
    gains: Optional[ControlGains] = None,
) -> ControlTickResult:
    """
    One control tick: arbitration → attitude/altitude commands → mixer → plant integration.

    Replace ``integrate_vertical_yaw_reference`` with a full 6-DOF adapter in product code.
    """
    g = gains or ControlGains()
    arb = evaluate_control_arbitration(state, setpoint, fence, spec)

    if not arb.allow_thrust or setpoint.mode == "disarmed":
        mixer = build_mixer_intent(0.0, 0.0, 0.0, 0.0, arb.torque_scale_0_1)
        new_state = integrate_vertical_yaw_reference(state, mixer, spec, dt_s)
        new_state.time_s = state.time_s + dt_s
        return ControlTickResult(
            state=new_state,
            mixer=mixer,
            arbitration=arb,
            diagnostics={"idle": True},
        )

    h = -state.pd_m
    err_h = setpoint.altitude_m_above_home_target - h
    vd_meas = state.vd_mps
    # e = h_target - h  →  de/dt = -dh/dt = vd (NED: h = -pd)
    hover = _hover_collective_0_1(spec)
    collective = hover + g.alt_kp * err_h + g.alt_kd * vd_meas
    # Limit excursion from hover to reduce thrust saturation in the reference plant
    collective = max(hover - 0.35, min(hover + 0.35, collective))
    collective = max(0.0, min(1.0, collective))

    roll_c, pitch_c, yaw_c = _attitude_commands(state, setpoint, g)
    roll_c *= arb.torque_scale_0_1
    pitch_c *= arb.torque_scale_0_1
    yaw_c *= arb.torque_scale_0_1

    mixer = build_mixer_intent(collective, roll_c, pitch_c, yaw_c, arb.torque_scale_0_1)

    new_state = integrate_vertical_yaw_reference(state, mixer, spec, dt_s)
    new_state.time_s = state.time_s + dt_s
    new_roll = max(-0.6, min(0.6, roll_c * 0.4 + state.roll_rad * 0.60))
    new_pitch = max(-0.6, min(0.6, pitch_c * 0.4 + state.pitch_rad * 0.60))
    new_state.roll_rad = new_roll
    new_state.pitch_rad = new_pitch
    new_state.yaw_rad += state.r_rps * dt_s
    new_state.r_rps = 0.35 * yaw_c + 0.92 * state.r_rps
    if dt_s > 1e-9:
        new_state.p_rps = (new_roll - state.roll_rad) / dt_s
        new_state.q_rps = (new_pitch - state.pitch_rad) / dt_s

    diag = {
        "altitude_m": h,
        "collective_0_1": collective,
        "total_thrust_n": total_thrust_n(mixer.motor_thrust_0_1, spec),
        "mission_pause": arb.mission_pause,
        "reasons": list(arb.reasons),
    }
    return ControlTickResult(state=new_state, mixer=mixer, arbitration=arb, diagnostics=diag)
