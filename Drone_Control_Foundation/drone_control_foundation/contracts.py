from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Tuple

DroneFlightMode = Literal["disarmed", "armed_hover", "altitude_hold", "position_hold"]

G_STD = 9.80665


@dataclass
class DroneState:
    """
    Minimal multicopter state (NED position from home: North-East-Down).

    Altitude above home (positive up) is ``h = -pd_m``.
    """

    time_s: float = 0.0
    pn_m: float = 0.0
    pe_m: float = 0.0
    pd_m: float = 0.0
    vn_mps: float = 0.0
    ve_mps: float = 0.0
    vd_mps: float = 0.0
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0
    p_rps: float = 0.0
    q_rps: float = 0.0
    r_rps: float = 0.0
    battery_soc_0_1: float = 1.0


@dataclass
class DroneSetpoint:
    mode: DroneFlightMode = "disarmed"
    altitude_m_above_home_target: float = 0.0
    yaw_rad_target: float = 0.0
    pn_m_target: Optional[float] = None
    pe_m_target: Optional[float] = None


@dataclass
class DronePlatformSpec:
    mass_kg: float = 1.5
    gravity_mps2: float = G_STD
    air_density_kg_m3: float = 1.225
    """Atmospheric density used by the bundled reference plant damping proxy."""
    horizontal_drag_coeff_1ps: float = 0.10
    """Light first-order horizontal drag proxy [1/s] at sea-level density."""
    max_total_thrust_n: float = 30.0
    """Total thrust if all motors at full (N)."""
    arm_m: float = 0.12
    """Hub-to-motor distance for torque scaling (m)."""
    max_tilt_rad: float = 0.52
    """Arbiter: above this |roll| or |pitch|, torque is scaled down."""
    max_horizontal_speed_mps: float = 15.0
    """Soft safety speed cap before torque authority is reduced."""
    max_vertical_speed_mps: float = 6.0
    """Soft vertical speed cap before torque authority is reduced."""
    hover_margin_hint: float = 0.25
    """Optional hover/thrust margin hint from upper flight-physics stacks."""
    minimum_hover_margin_hint: float = 0.08
    """Below this margin, the arbiter enters a recoverable low-authority mode."""
    low_battery_soc: float = 0.18
    critical_battery_soc: float = 0.10


@dataclass
class GeofenceConfig:
    enabled: bool = True
    max_horizontal_m: float = 80.0
    min_altitude_m_above_home: float = -5.0
    max_altitude_m_above_home: float = 120.0


@dataclass
class ControlGains:
    """Dimensionless / SI mixed gains for the bundled reference controller."""

    alt_kp: float = 0.12
    alt_kd: float = 0.35
    yaw_kp: float = 1.6
    pos_kp: float = 0.08
    max_tilt_cmd_rad: float = 0.22


@dataclass
class MixerIntent:
    """
    HAL-facing one-tick output: per-motor normalized thrust + diagnostic commands.

    Integrators map ``motor_thrust_0_1`` to PWM / CAN; vendor SDK stays outside.
    """

    schema_version: str = "drone_mixer_intent.v0.1"
    motor_thrust_0_1: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    collective_thrust_0_1: float = 0.0
    roll_torque_cmd_0_1: float = 0.0
    pitch_torque_cmd_0_1: float = 0.0
    yaw_torque_cmd_0_1: float = 0.0


@dataclass
class ControlTickResult:
    state: DroneState
    mixer: MixerIntent
    arbitration: "ControlArbitration"
    diagnostics: dict = field(default_factory=dict)
