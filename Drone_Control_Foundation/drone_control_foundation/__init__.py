"""Drone_Control_Foundation — extensible multicopter control contracts and reference tick."""

from .arbiter import ControlArbitration, evaluate_control_arbitration
from .battery_adapter import (
    DroneBatteryBridgeConfig,
    DroneBatteryBridgeOutput,
    advance_battery_from_mixer,
    estimate_current_draw_a,
    estimate_propulsion_power_w,
    patch_drone_state_soc,
)
from .contracts import (
    ControlGains,
    ControlTickResult,
    DroneFlightMode,
    DronePlatformSpec,
    DroneSetpoint,
    DroneState,
    GeofenceConfig,
    MixerIntent,
)
from .control_tick import run_control_tick
from .flight_bridges import (
    air_jordan_atmosphere_for_altitude,
    patch_spec_from_air_jordan,
    patch_spec_from_morphing_assessment,
)
from .mixer import build_mixer_intent, quad_x_mix, total_thrust_n
from .reference_plant import integrate_vertical_yaw_reference
from .robot_adapter import (
    ACTUATOR_INTENT_SCHEMA_VERSION,
    DroneDriverBase,
    DroneTickLog,
    StubDroneDriver,
    apply_mixer_intent_stub,
    build_drone_actuator_intent,
    parse_drone_actuator_intent,
)
from .health import DroneHealthReport, observe_drone_health
from .sensory_adapter import drone_state_from_sensory_stimulus, drone_state_from_snapshot
from .surface import run_drone_tick, validate_drone_tick_payload

__all__ = [
    "ControlArbitration",
    "DroneBatteryBridgeConfig",
    "DroneBatteryBridgeOutput",
    "ControlGains",
    "ControlTickResult",
    "DroneDriverBase",
    "DroneFlightMode",
    "DronePlatformSpec",
    "DroneSetpoint",
    "DroneState",
    "DroneTickLog",
    "GeofenceConfig",
    "MixerIntent",
    "StubDroneDriver",
    "ACTUATOR_INTENT_SCHEMA_VERSION",
    "apply_mixer_intent_stub",
    "air_jordan_atmosphere_for_altitude",
    "advance_battery_from_mixer",
    "estimate_current_draw_a",
    "estimate_propulsion_power_w",
    "build_mixer_intent",
    "build_drone_actuator_intent",
    "DroneHealthReport",
    "drone_state_from_sensory_stimulus",
    "drone_state_from_snapshot",
    "observe_drone_health",
    "evaluate_control_arbitration",
    "patch_spec_from_air_jordan",
    "patch_spec_from_morphing_assessment",
    "patch_drone_state_soc",
    "integrate_vertical_yaw_reference",
    "parse_drone_actuator_intent",
    "quad_x_mix",
    "run_control_tick",
    "run_drone_tick",
    "total_thrust_n",
    "validate_drone_tick_payload",
]

__version__ = "0.2.0"
