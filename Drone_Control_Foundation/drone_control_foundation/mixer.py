from __future__ import annotations

from typing import Tuple

from .contracts import DronePlatformSpec, MixerIntent


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def quad_x_mix(
    collective_thrust_0_1: float,
    roll_torque_cmd_0_1: float,
    pitch_torque_cmd_0_1: float,
    yaw_torque_cmd_0_1: float,
    torque_scale_0_1: float,
) -> Tuple[float, float, float, float]:
    """
    Quad-X motor order (0..3):

    - 0: front-right, 1: rear-left, 2: front-left, 3: rear-right
      (body +X forward, +Y right, +Z down — thrust along -Z_body).

    Commands are *normalized* [-1, 1] for torque channels; scaled inside.
    """
    ts = max(0.0, min(1.0, torque_scale_0_1))
    c = max(0.0, min(1.0, collective_thrust_0_1))
    tr = max(-1.0, min(1.0, roll_torque_cmd_0_1)) * ts * 0.25
    tp = max(-1.0, min(1.0, pitch_torque_cmd_0_1)) * ts * 0.25
    ty = max(-1.0, min(1.0, yaw_torque_cmd_0_1)) * ts * 0.15

    # X layout coupling (simplified)
    m0 = _clamp01(c + tr - tp + ty)
    m1 = _clamp01(c - tr + tp + ty)
    m2 = _clamp01(c - tr - tp - ty)
    m3 = _clamp01(c + tr + tp - ty)
    return (m0, m1, m2, m3)


def build_mixer_intent(
    collective_thrust_0_1: float,
    roll_torque_cmd_0_1: float,
    pitch_torque_cmd_0_1: float,
    yaw_torque_cmd_0_1: float,
    torque_scale_0_1: float,
) -> MixerIntent:
    m = quad_x_mix(
        collective_thrust_0_1,
        roll_torque_cmd_0_1,
        pitch_torque_cmd_0_1,
        yaw_torque_cmd_0_1,
        torque_scale_0_1,
    )
    return MixerIntent(
        motor_thrust_0_1=m,
        collective_thrust_0_1=collective_thrust_0_1,
        roll_torque_cmd_0_1=roll_torque_cmd_0_1,
        pitch_torque_cmd_0_1=pitch_torque_cmd_0_1,
        yaw_torque_cmd_0_1=yaw_torque_cmd_0_1,
    )


def total_thrust_n(motor_thrust_0_1: Tuple[float, float, float, float], spec: DronePlatformSpec) -> float:
    cap = spec.max_total_thrust_n / 4.0
    return sum(max(0.0, min(1.0, mi)) * cap for mi in motor_thrust_0_1)
