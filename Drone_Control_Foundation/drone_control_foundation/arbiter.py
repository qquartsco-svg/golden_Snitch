from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

from .contracts import DronePlatformSpec, DroneSetpoint, DroneState, GeofenceConfig


@dataclass(frozen=True)
class ControlArbitration:
    """
    Safety / mission gate on top of the control stack (compare: Cooking arbiter).

    - ``allow_thrust``: False → motors idled by controller path.
    - ``torque_scale_0_1``: soft cap on attitude torque commands.
    - ``mission_pause``: host may freeze mission planner upstream.
    - ``disarm_recommended``: critical condition; host should land & disarm.
    """

    allow_thrust: bool
    torque_scale_0_1: float
    mission_pause: bool
    disarm_recommended: bool
    reasons: Tuple[str, ...]


def evaluate_control_arbitration(
    state: DroneState,
    setpoint: DroneSetpoint,
    fence: GeofenceConfig,
    spec: DronePlatformSpec,
) -> ControlArbitration:
    reasons: list[str] = []
    allow = True
    torque_scale = 1.0
    pause = False
    disarm = False

    if setpoint.mode == "disarmed":
        return ControlArbitration(
            allow_thrust=False,
            torque_scale_0_1=0.0,
            mission_pause=True,
            disarm_recommended=False,
            reasons=("mode_disarmed",),
        )

    soc = max(0.0, min(1.0, state.battery_soc_0_1))
    if soc <= spec.critical_battery_soc:
        disarm = True
        allow = False
        torque_scale = 0.0
        reasons.append("battery_critical")
    elif soc <= spec.low_battery_soc:
        torque_scale = min(torque_scale, 0.55)
        reasons.append("battery_low")

    horiz = math.hypot(state.pn_m, state.pe_m)
    alt = -state.pd_m

    if fence.enabled:
        if horiz > fence.max_horizontal_m:
            pause = True
            torque_scale = min(torque_scale, 0.45)
            reasons.append("geofence_horizontal")
        if alt < fence.min_altitude_m_above_home or alt > fence.max_altitude_m_above_home:
            pause = True
            torque_scale = min(torque_scale, 0.45)
            reasons.append("geofence_altitude")

    horiz_speed = math.hypot(state.vn_mps, state.ve_mps)
    if horiz_speed > spec.max_horizontal_speed_mps:
        pause = True
        torque_scale = min(torque_scale, 0.60)
        reasons.append("speed_horizontal_soft")

    if abs(state.vd_mps) > spec.max_vertical_speed_mps:
        pause = True
        torque_scale = min(torque_scale, 0.60)
        reasons.append("speed_vertical_soft")

    if (
        setpoint.mode in {"armed_hover", "altitude_hold", "position_hold"}
        and spec.hover_margin_hint < spec.minimum_hover_margin_hint
    ):
        pause = True
        torque_scale = min(torque_scale, 0.50)
        reasons.append("hover_margin_low")

    tilt = max(abs(state.roll_rad), abs(state.pitch_rad))
    if tilt > spec.max_tilt_rad:
        torque_scale = min(torque_scale, 0.35)
        reasons.append("tilt_limit_soft")

    if not allow:
        pause = True

    return ControlArbitration(
        allow_thrust=allow,
        torque_scale_0_1=max(0.0, min(1.0, torque_scale)),
        mission_pause=pause,
        disarm_recommended=disarm,
        reasons=tuple(reasons),
    )
