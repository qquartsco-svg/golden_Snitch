from __future__ import annotations

from typing import Mapping

from .contracts import ArduPilotCommandEnvelope, parse_dcf_actuator_intent


def build_ardupilot_command_envelope(intent: Mapping[str, object]) -> ArduPilotCommandEnvelope:
    parsed = parse_dcf_actuator_intent(intent)
    return ArduPilotCommandEnvelope(
        schema_version=parsed["schema_version"],
        motor_outputs_0_1=parsed["motor_thrust_0_1"],
        collective_0_1=parsed["collective_thrust_0_1"],
        mission_pause=parsed["mission_pause"],
        estop_recommended=parsed["estop_recommended"],
        step_id=parsed["step_id"],
        flow_id=parsed["flow_id"],
        metadata={"transport_hint": parsed["transport_hint"]},
    )
