from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Tuple


@dataclass(frozen=True)
class PX4CommandEnvelope:
    schema_version: str
    actuator_controls_0_1: Tuple[float, float, float, float]
    thrust_sp_0_1: float
    mission_pause: bool
    estop_recommended: bool
    step_id: str = ""
    flow_id: str = ""
    transport: str = "px4_actuator_controls"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArduPilotCommandEnvelope:
    schema_version: str
    motor_outputs_0_1: Tuple[float, float, float, float]
    collective_0_1: float
    mission_pause: bool
    estop_recommended: bool
    step_id: str = ""
    flow_id: str = ""
    transport: str = "ardupilot_motor_outputs"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VendorBindingHealthSnapshot:
    link_alive: bool = True
    heartbeat_age_s: float = 0.0
    driver_fault: bool = False
    last_transport: str = ""


@dataclass(frozen=True)
class DroneAdapterNexusSignal:
    omega_control: float
    mission_pause: bool
    estop_recommended: bool
    vendor_link_ok: bool
    binding_transport: str
    flags: Dict[str, bool] = field(default_factory=dict)
    notes: Tuple[str, ...] = ()


def clamp_motor_tuple(values: Any) -> Tuple[float, float, float, float]:
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        raise TypeError("motor outputs must be a 4-element list/tuple")
    return tuple(max(0.0, min(1.0, float(v))) for v in values)  # type: ignore[return-value]


def parse_dcf_actuator_intent(intent: Mapping[str, Any]) -> Dict[str, Any]:
    motors = clamp_motor_tuple(intent.get("motor_thrust_0_1") or (0.0, 0.0, 0.0, 0.0))
    return {
        "schema_version": str(intent.get("schema_version") or "drone_actuator_intent.v0.1"),
        "motor_thrust_0_1": motors,
        "collective_thrust_0_1": max(0.0, min(1.0, float(intent.get("primary_output_0_1", 0.0)))),
        "mission_pause": bool(intent.get("mission_pause", False)),
        "estop_recommended": bool(intent.get("estop_recommended", False)),
        "step_id": str(intent.get("step_id") or ""),
        "flow_id": str(intent.get("flow_id") or ""),
        "transport_hint": str(intent.get("transport_hint") or ""),
    }
