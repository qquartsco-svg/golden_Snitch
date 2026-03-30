"""
golden_Snitch 통합 테스트: DCF → DRA 계약 경계 검증
=====================================================

DCF(제어)와 DRA(HAL) 사이의 계약(actuator intent dict)이
양방향으로 올바르게 동작하는지 검증한다.
"""
from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_DCF = os.path.join(_ROOT, "Drone_Control_Foundation")

for _p in [_ROOT, _DCF]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest

from drone_control_foundation import (
    DroneState,
    DroneSetpoint,
    DronePlatformSpec,
    GeofenceConfig,
    build_drone_actuator_intent,
    run_control_tick,
)
from drone_robot_adapter import (
    BindingWatchdog,
    build_ardupilot_command_envelope,
    build_nexus_drone_signal,
    build_px4_command_envelope,
    render_nexus_drone_lines,
)


# ── 공통 픽스처 ───────────────────────────────────────────────────────────────

def _run_tick(
    pd_m: float = -10.0,
    soc: float = 0.80,
    mode: str = "altitude_hold",
    alt_target: float = 10.0,
    pn_m: float = 0.0,
    geo_radius: float = 200.0,
):
    state = DroneState(pd_m=pd_m, battery_soc_0_1=soc, pn_m=pn_m)
    sp = DroneSetpoint(mode=mode, altitude_m_above_home_target=alt_target)
    spec = DronePlatformSpec()
    geo = GeofenceConfig(enabled=True, max_horizontal_m=geo_radius)
    return run_control_tick(state, sp, spec, geo, dt_s=0.02)


def _make_intent(result, *, step_id: str = "t0", flow_id: str = "test"):
    # ControlArbitration: disarm_recommended → estop_recommended 매핑
    return build_drone_actuator_intent(
        result.mixer,
        mission_pause=result.arbitration.mission_pause,
        estop_recommended=result.arbitration.disarm_recommended,
        step_id=step_id,
        flow_id=flow_id,
    )


# ── §1 계약 경계: actuator intent 구조 ───────────────────────────────────────

class TestActuatorIntentContract:
    def test_intent_has_required_fields(self):
        intent = _make_intent(_run_tick())
        required = {
            "schema_version", "primary_output_0_1", "motor_thrust_0_1",
            "mission_pause", "estop_recommended", "allow_motion",
            "step_id", "flow_id",
        }
        assert required.issubset(intent.keys())

    def test_motor_thrust_is_4tuple_normalized(self):
        intent = _make_intent(_run_tick())
        motors = intent["motor_thrust_0_1"]
        assert len(motors) == 4
        assert all(0.0 <= m <= 1.0 for m in motors)

    def test_primary_output_normalized(self):
        intent = _make_intent(_run_tick())
        assert 0.0 <= intent["primary_output_0_1"] <= 1.0

    def test_step_flow_id_preserved(self):
        intent = _make_intent(_run_tick(), step_id="cruise_001", flow_id="mission_alpha")
        assert intent["step_id"] == "cruise_001"
        assert intent["flow_id"] == "mission_alpha"


# ── §2 정상 비행 → PX4 envelope ───────────────────────────────────────────────

class TestNormalFlightToPX4:
    def test_px4_envelope_transport_name(self):
        env = build_px4_command_envelope(_make_intent(_run_tick()))
        assert env.transport == "px4_actuator_controls"

    def test_px4_thrust_matches_intent_primary(self):
        result = _run_tick(pd_m=-5.0, alt_target=10.0)
        intent = _make_intent(result)
        env = build_px4_command_envelope(intent)
        assert abs(env.thrust_sp_0_1 - intent["primary_output_0_1"]) < 1e-6

    def test_px4_motors_length_4(self):
        env = build_px4_command_envelope(_make_intent(_run_tick()))
        assert len(env.actuator_controls_0_1) == 4

    def test_px4_motors_normalized(self):
        env = build_px4_command_envelope(_make_intent(_run_tick()))
        assert all(0.0 <= m <= 1.0 for m in env.actuator_controls_0_1)

    def test_px4_metadata_contains_transport_hint(self):
        intent = _make_intent(_run_tick())
        intent["transport_hint"] = "pwm_normalized"
        env = build_px4_command_envelope(intent)
        assert env.metadata.get("transport_hint") == "pwm_normalized"


# ── §3 정상 비행 → ArduPilot envelope ────────────────────────────────────────

class TestNormalFlightToArduPilot:
    def test_ardupilot_transport_name(self):
        env = build_ardupilot_command_envelope(_make_intent(_run_tick()))
        assert env.transport == "ardupilot_motor_outputs"

    def test_ardupilot_collective_matches_primary(self):
        result = _run_tick()
        intent = _make_intent(result)
        env = build_ardupilot_command_envelope(intent)
        assert abs(env.collective_0_1 - intent["primary_output_0_1"]) < 1e-6

    def test_ardupilot_motor_outputs_4(self):
        env = build_ardupilot_command_envelope(_make_intent(_run_tick()))
        assert len(env.motor_outputs_0_1) == 4


# ── §4 지오펜스 이탈 → mission_pause 전파 ─────────────────────────────────────

class TestGeofenceBreachPropagation:
    def test_breach_sets_mission_pause_in_dcf(self):
        result = _run_tick(pn_m=250.0, geo_radius=100.0)
        assert result.arbitration.mission_pause is True

    def test_mission_pause_propagates_to_intent(self):
        result = _run_tick(pn_m=250.0, geo_radius=100.0)
        intent = _make_intent(result)
        assert intent["mission_pause"] is True

    def test_mission_pause_propagates_to_px4(self):
        result = _run_tick(pn_m=250.0, geo_radius=100.0)
        intent = _make_intent(result)
        env = build_px4_command_envelope(intent)
        # mission_pause는 envelope의 직접 필드
        assert env.mission_pause is True

    def test_mission_pause_propagates_to_ardupilot(self):
        result = _run_tick(pn_m=250.0, geo_radius=100.0)
        intent = _make_intent(result)
        env = build_ardupilot_command_envelope(intent)
        assert env.mission_pause is True

    def test_breach_allow_motion_false_when_estop(self):
        """estop_recommended 시 allow_motion = False."""
        result = _run_tick(pn_m=250.0, geo_radius=100.0)
        # estop_recommended 강제
        intent = build_drone_actuator_intent(
            result.mixer,
            mission_pause=True,
            estop_recommended=True,
        )
        assert intent["allow_motion"] is False


# ── §5 Nexus signal + Watchdog 통합 ──────────────────────────────────────────

class TestNexusSignalIntegration:
    def test_nexus_signal_mission_pause_flag(self):
        result = _run_tick(pn_m=250.0, geo_radius=100.0)
        intent = _make_intent(result)
        watchdog = BindingWatchdog(stale_after_s=1.0)
        watchdog.mark_heartbeat(0.0, transport="px4_actuator_controls")
        snap = watchdog.snapshot(0.3)
        signal = build_nexus_drone_signal(
            mission_pause=intent["mission_pause"],
            estop_recommended=intent["estop_recommended"],
            binding_health=snap,
            collective_0_1=intent["primary_output_0_1"],
        )
        assert signal.flags["mission_pause"] is True

    def test_nexus_signal_vendor_link_ok_when_heartbeat_fresh(self):
        result = _run_tick()
        intent = _make_intent(result)
        watchdog = BindingWatchdog(stale_after_s=1.0)
        watchdog.mark_heartbeat(0.0, transport="px4_actuator_controls")
        snap = watchdog.snapshot(0.5)  # 0.5 s < stale_after_s
        signal = build_nexus_drone_signal(
            mission_pause=intent["mission_pause"],
            estop_recommended=intent["estop_recommended"],
            binding_health=snap,
            collective_0_1=intent["primary_output_0_1"],
        )
        assert signal.vendor_link_ok is True

    def test_nexus_signal_vendor_link_stale_when_old_heartbeat(self):
        result = _run_tick()
        intent = _make_intent(result)
        watchdog = BindingWatchdog(stale_after_s=1.0)
        watchdog.mark_heartbeat(0.0, transport="px4_actuator_controls")
        snap = watchdog.snapshot(2.0)  # 2 s > stale_after_s
        signal = build_nexus_drone_signal(
            mission_pause=intent["mission_pause"],
            estop_recommended=intent["estop_recommended"],
            binding_health=snap,
            collective_0_1=intent["primary_output_0_1"],
        )
        assert signal.vendor_link_ok is False

    def test_nexus_render_lines_nonempty(self):
        result = _run_tick()
        intent = _make_intent(result)
        watchdog = BindingWatchdog(stale_after_s=1.0)
        watchdog.mark_heartbeat(0.0)
        snap = watchdog.snapshot(0.1)
        signal = build_nexus_drone_signal(
            mission_pause=False,
            estop_recommended=False,
            binding_health=snap,
            collective_0_1=intent["primary_output_0_1"],
        )
        lines = render_nexus_drone_lines(signal)
        assert len(lines) > 0
        assert any("transport" in line for line in lines)


# ── §6 disarmed 상태 → 모터 차단 전파 ───────────────────────────────────────

class TestDisarmedPropagation:
    def test_disarmed_motors_all_zero(self):
        state = DroneState(pd_m=-5.0, battery_soc_0_1=1.0)
        sp = DroneSetpoint(mode="disarmed")
        result = run_control_tick(state, sp, DronePlatformSpec(), GeofenceConfig(), 0.02)
        assert result.arbitration.allow_thrust is False
        motors = result.mixer.motor_thrust_0_1
        assert all(m == 0.0 for m in motors)

    def test_disarmed_intent_allow_motion_false(self):
        state = DroneState(pd_m=-5.0)
        sp = DroneSetpoint(mode="disarmed")
        result = run_control_tick(state, sp, DronePlatformSpec(), GeofenceConfig(), 0.02)
        intent = _make_intent(result)
        assert intent["allow_motion"] is False

    def test_disarmed_px4_thrust_zero(self):
        state = DroneState(pd_m=-5.0)
        sp = DroneSetpoint(mode="disarmed")
        result = run_control_tick(state, sp, DronePlatformSpec(), GeofenceConfig(), 0.02)
        intent = _make_intent(result)
        env = build_px4_command_envelope(intent)
        assert env.thrust_sp_0_1 == 0.0
