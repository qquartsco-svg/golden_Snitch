from __future__ import annotations

from drone_robot_adapter import (
    BindingWatchdog,
    VendorBindingHealthSnapshot,
    build_ardupilot_command_envelope,
    build_nexus_drone_signal,
    build_px4_command_envelope,
    render_nexus_drone_lines,
)


def _sample_intent():
    return {
        "schema_version": "drone_actuator_intent.v0.1",
        "primary_output_0_1": 0.62,
        "motor_thrust_0_1": (0.60, 0.61, 0.63, 0.64),
        "mission_pause": False,
        "estop_recommended": False,
        "step_id": "hover",
        "flow_id": "demo",
        "transport_hint": "pwm_normalized",
    }


def test_px4_envelope_preserves_motor_outputs_and_meta():
    env = build_px4_command_envelope(_sample_intent())
    assert env.transport == "px4_actuator_controls"
    assert env.thrust_sp_0_1 == 0.62
    assert env.actuator_controls_0_1[0] == 0.60
    assert env.metadata["transport_hint"] == "pwm_normalized"


def test_ardupilot_envelope_preserves_collective():
    env = build_ardupilot_command_envelope(_sample_intent())
    assert env.transport == "ardupilot_motor_outputs"
    assert env.collective_0_1 == 0.62
    assert len(env.motor_outputs_0_1) == 4


def test_nexus_signal_renders_vendor_binding_health():
    signal = build_nexus_drone_signal(
        mission_pause=True,
        estop_recommended=False,
        binding_health=VendorBindingHealthSnapshot(
            link_alive=True,
            heartbeat_age_s=0.2,
            driver_fault=False,
            last_transport="px4_actuator_controls",
        ),
        collective_0_1=0.58,
    )
    lines = render_nexus_drone_lines(signal)
    assert signal.vendor_link_ok is True
    assert signal.flags["mission_pause"] is True
    assert "transport=px4_actuator_controls" in lines[0]


def test_watchdog_marks_stale_heartbeat():
    watchdog = BindingWatchdog(stale_after_s=1.0)
    watchdog.mark_heartbeat(5.0, transport="ardupilot_motor_outputs")
    snap = watchdog.snapshot(6.5)
    assert snap.link_alive is False
    assert snap.heartbeat_age_s == 1.5
    assert snap.last_transport == "ardupilot_motor_outputs"
