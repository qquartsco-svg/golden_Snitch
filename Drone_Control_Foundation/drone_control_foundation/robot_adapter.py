from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .contracts import MixerIntent

_RAC_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Robot_Adapter_Core")
if os.path.isdir(_RAC_PATH) and _RAC_PATH not in sys.path:
    sys.path.insert(0, _RAC_PATH)

from robot_adapter_core.contracts import (  # type: ignore
    BaseTickLog,
    DomainDriverBase,
    parse_generic_intent,
)


ACTUATOR_INTENT_SCHEMA_VERSION = "drone_actuator_intent.v0.1"


@dataclass
class DroneTickLog(BaseTickLog):
    motor_thrust_0_1: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    collective_thrust_0_1: float = 0.0
    roll_torque_cmd_0_1: float = 0.0
    pitch_torque_cmd_0_1: float = 0.0
    yaw_torque_cmd_0_1: float = 0.0
    transport_hint: str = "pwm_normalized"
    schema_version: str = ACTUATOR_INTENT_SCHEMA_VERSION


class DroneDriverBase(DomainDriverBase):
    domain_tag: str = "drone"


def build_drone_actuator_intent(
    mixer: MixerIntent,
    *,
    mission_pause: bool = False,
    estop_recommended: bool = False,
    step_id: str = "",
    flow_id: str = "",
    transport_hint: str = "pwm_normalized",
) -> Dict[str, Any]:
    motors = tuple(max(0.0, min(1.0, float(x))) for x in mixer.motor_thrust_0_1)
    motion_allowed = max(motors, default=0.0) > 0.0 and not estop_recommended
    return {
        "schema_version": ACTUATOR_INTENT_SCHEMA_VERSION,
        "flow_id": flow_id,
        "step_id": step_id,
        "primary_output_0_1": max(0.0, min(1.0, float(mixer.collective_thrust_0_1))),
        "thrust_ceiling_0_1": max(0.0, min(1.0, float(mixer.collective_thrust_0_1))),
        "allow_motion": motion_allowed,
        "mission_pause": bool(mission_pause),
        "estop_recommended": bool(estop_recommended),
        "motor_thrust_0_1": motors,
        "roll_torque_cmd_0_1": float(mixer.roll_torque_cmd_0_1),
        "pitch_torque_cmd_0_1": float(mixer.pitch_torque_cmd_0_1),
        "yaw_torque_cmd_0_1": float(mixer.yaw_torque_cmd_0_1),
        "transport_hint": transport_hint,
    }


def parse_drone_actuator_intent(intent: Mapping[str, Any]) -> Dict[str, Any]:
    base = parse_generic_intent(intent)
    motors_raw = intent.get("motor_thrust_0_1") or (0.0, 0.0, 0.0, 0.0)
    if not isinstance(motors_raw, (list, tuple)) or len(motors_raw) != 4:
        raise TypeError("motor_thrust_0_1 must be a 4-element list/tuple")
    motors = tuple(max(0.0, min(1.0, float(x))) for x in motors_raw)
    return {
        **base,
        "schema_version": str(intent.get("schema_version") or ACTUATOR_INTENT_SCHEMA_VERSION),
        "motor_thrust_0_1": motors,
        "collective_thrust_0_1": base["primary_0_1"],
        "roll_torque_cmd_0_1": float(intent.get("roll_torque_cmd_0_1", 0.0)),
        "pitch_torque_cmd_0_1": float(intent.get("pitch_torque_cmd_0_1", 0.0)),
        "yaw_torque_cmd_0_1": float(intent.get("yaw_torque_cmd_0_1", 0.0)),
        "transport_hint": str(intent.get("transport_hint") or "pwm_normalized"),
    }


@dataclass
class StubDroneDriver(DroneDriverBase):
    tick_logs: List[DroneTickLog] = field(default_factory=list)
    collective_log: List[float] = field(default_factory=list)
    motion_allowed_log: List[bool] = field(default_factory=list)
    estop_latched: bool = False

    def apply_intent(self, intent: Mapping[str, Any]) -> DroneTickLog:
        if not isinstance(intent, Mapping):
            raise TypeError("intent must be a mapping")
        f = parse_drone_actuator_intent(intent)
        if f["estop"]:
            self.estop_latched = True
        self.collective_log.append(f["collective_thrust_0_1"])
        self.motion_allowed_log.append(f["motion_commanded"])
        log = DroneTickLog(
            raw_intent=intent,
            primary_0_1=f["primary_0_1"],
            motion_commanded=f["motion_commanded"],
            estop_triggered=f["estop"],
            mission_paused=f["mission_pause"],
            step_id=f["step_id"],
            domain_tag=self.domain_tag,
            domain_extra={"flow_id": f["flow_id"]},
            motor_thrust_0_1=f["motor_thrust_0_1"],
            collective_thrust_0_1=f["collective_thrust_0_1"],
            roll_torque_cmd_0_1=f["roll_torque_cmd_0_1"],
            pitch_torque_cmd_0_1=f["pitch_torque_cmd_0_1"],
            yaw_torque_cmd_0_1=f["yaw_torque_cmd_0_1"],
            transport_hint=f["transport_hint"],
            schema_version=f["schema_version"],
        )
        self.tick_logs.append(log)
        return log

    def estop(self) -> None:
        self.estop_latched = True

    @property
    def is_estopped(self) -> bool:
        return self.estop_latched

    def last_log(self) -> Optional[DroneTickLog]:
        return self.tick_logs[-1] if self.tick_logs else None

    def summary(self) -> Dict[str, Any]:
        return {
            "domain": self.domain_tag,
            "tick_count": len(self.tick_logs),
            "estop_latched": self.estop_latched,
            "mission_pause_count": sum(1 for l in self.tick_logs if l.mission_paused),
            "collective_max": max(self.collective_log, default=0.0),
            "collective_min": min(self.collective_log, default=0.0),
            "motion_allowed_rate": (
                sum(self.motion_allowed_log) / len(self.motion_allowed_log)
                if self.motion_allowed_log
                else 0.0
            ),
            "transport_hints": list(dict.fromkeys(l.transport_hint for l in self.tick_logs)),
        }


def apply_mixer_intent_stub(
    mixer: MixerIntent,
    *,
    mission_pause: bool = False,
    estop_recommended: bool = False,
    transport_hint: str = "pwm_normalized",
) -> Dict[str, Any]:
    driver = StubDroneDriver()
    intent = build_drone_actuator_intent(
        mixer,
        mission_pause=mission_pause,
        estop_recommended=estop_recommended,
        transport_hint=transport_hint,
    )
    log = driver.apply_intent(intent)
    return {
        "collective_last": log.collective_thrust_0_1,
        "mission_paused": log.mission_paused,
        "estop_latched": driver.estop_latched,
        "transport_hint": log.transport_hint,
        "motor_thrust_0_1": log.motor_thrust_0_1,
    }
