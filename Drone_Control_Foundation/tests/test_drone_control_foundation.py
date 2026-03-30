from __future__ import annotations

import math

import pytest

from drone_control_foundation import (
    ACTUATOR_INTENT_SCHEMA_VERSION,
    ControlGains,
    DroneBatteryBridgeConfig,
    DroneHealthReport,
    DronePlatformSpec,
    StubDroneDriver,
    DroneSetpoint,
    DroneState,
    GeofenceConfig,
    advance_battery_from_mixer,
    apply_mixer_intent_stub,
    build_mixer_intent,
    build_drone_actuator_intent,
    drone_state_from_sensory_stimulus,
    drone_state_from_snapshot,
    evaluate_control_arbitration,
    estimate_current_draw_a,
    estimate_propulsion_power_w,
    air_jordan_atmosphere_for_altitude,
    integrate_vertical_yaw_reference,
    observe_drone_health,
    patch_drone_state_soc,
    patch_spec_from_air_jordan,
    patch_spec_from_morphing_assessment,
    parse_drone_actuator_intent,
    quad_x_mix,
    run_control_tick,
    run_drone_tick,
    validate_drone_tick_payload,
)


def test_arbiter_geofence_pauses_mission_but_preserves_thrust_authority():
    st = DroneState(pn_m=100.0, pd_m=-10.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=10.0)
    spec = DronePlatformSpec()
    fence = GeofenceConfig(max_horizontal_m=50.0)
    arb = evaluate_control_arbitration(st, sp, fence, spec)
    assert arb.allow_thrust is True
    assert arb.mission_pause is True
    assert arb.torque_scale_0_1 < 1.0
    assert "geofence_horizontal" in arb.reasons


def test_arbiter_critical_battery_disarm():
    st = DroneState(battery_soc_0_1=0.05)
    sp = DroneSetpoint(mode="altitude_hold")
    arb = evaluate_control_arbitration(st, sp, GeofenceConfig(), DronePlatformSpec())
    assert arb.disarm_recommended is True
    assert arb.allow_thrust is False


def test_quad_x_mix_sums_near_collective():
    m = quad_x_mix(0.5, 0.0, 0.0, 0.0, 1.0)
    assert len(m) == 4
    assert all(0.0 <= x <= 1.0 for x in m)


def test_altitude_hold_converges_toward_setpoint():
    spec = DronePlatformSpec(mass_kg=1.5, max_total_thrust_n=30.0)
    fence = GeofenceConfig()
    gains = ControlGains(alt_kp=0.12, alt_kd=0.35)
    st = DroneState(pd_m=-5.0, vd_mps=0.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=8.0)
    for _ in range(600):
        out = run_control_tick(st, sp, spec, fence, 0.02, gains=gains)
        st = out.state
    h = -st.pd_m
    assert 6.0 < h < 10.0


def test_position_hold_moves_toward_target():
    spec = DronePlatformSpec()
    fence = GeofenceConfig()
    gains = ControlGains(pos_kp=0.12, alt_kp=0.12, alt_kd=0.35)
    st = DroneState(pn_m=0.0, pe_m=0.0, pd_m=-5.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(
        mode="position_hold",
        altitude_m_above_home_target=5.0,
        pn_m_target=3.0,
        pe_m_target=0.0,
    )
    for _ in range(500):
        st = run_control_tick(st, sp, spec, fence, 0.02, gains=gains).state
    assert st.pn_m > 1.0
    assert abs(st.pe_m) < 2.0


def test_position_hold_respects_yaw_in_reference_plant():
    spec = DronePlatformSpec()
    fence = GeofenceConfig()
    gains = ControlGains(pos_kp=0.12, alt_kp=0.12, alt_kd=0.35)
    st = DroneState(pn_m=0.0, pe_m=0.0, pd_m=-5.0, yaw_rad=math.pi / 2.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(
        mode="position_hold",
        altitude_m_above_home_target=5.0,
        yaw_rad_target=math.pi / 2.0,
        pn_m_target=0.0,
        pe_m_target=3.0,
    )
    for _ in range(500):
        st = run_control_tick(st, sp, spec, fence, 0.02, gains=gains).state
    assert st.pe_m > 1.0
    assert abs(st.pn_m) < 2.0


def test_speed_limit_soft_reduces_torque_without_cutting_thrust():
    st = DroneState(vn_mps=20.0, ve_mps=0.0, vd_mps=0.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=5.0)
    arb = evaluate_control_arbitration(st, sp, GeofenceConfig(), DronePlatformSpec(max_horizontal_speed_mps=10.0))
    assert arb.allow_thrust is True
    assert arb.mission_pause is True
    assert arb.torque_scale_0_1 < 1.0
    assert "speed_horizontal_soft" in arb.reasons


def test_low_hover_margin_enters_recoverable_pause_mode():
    st = DroneState(pd_m=-5.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=5.0)
    spec = DronePlatformSpec(hover_margin_hint=0.02, minimum_hover_margin_hint=0.08)
    arb = evaluate_control_arbitration(st, sp, GeofenceConfig(), spec)
    assert arb.allow_thrust is True
    assert arb.mission_pause is True
    assert arb.torque_scale_0_1 < 1.0
    assert "hover_margin_low" in arb.reasons


def test_disarmed_yields_idle_and_zero_motors():
    st = DroneState(pd_m=-2.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(mode="disarmed")
    res = run_control_tick(st, sp, DronePlatformSpec(), GeofenceConfig(), 0.05)
    assert res.diagnostics.get("idle") is True
    assert max(res.mixer.motor_thrust_0_1) == 0.0
    assert res.arbitration.allow_thrust is False


def test_attitude_filter_and_rates_stay_bounded():
    spec = DronePlatformSpec()
    fence = GeofenceConfig()
    gains = ControlGains(pos_kp=0.12, alt_kp=0.12, alt_kd=0.35)
    st = DroneState(pn_m=0.0, pe_m=0.0, pd_m=-5.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(
        mode="position_hold",
        altitude_m_above_home_target=5.0,
        pn_m_target=5.0,
        pe_m_target=0.0,
    )
    out = run_control_tick(st, sp, spec, fence, 0.02, gains=gains)
    assert abs(out.state.roll_rad) <= 0.6
    assert abs(out.state.pitch_rad) <= 0.6
    assert out.state.p_rps == pytest.approx((out.state.roll_rad - st.roll_rad) / 0.02)
    assert out.state.q_rps == pytest.approx((out.state.pitch_rad - st.pitch_rad) / 0.02)


def test_surface_payload_roundtrip():
    assert validate_drone_tick_payload({})[0] is False
    out = run_drone_tick(
        {
            "dt_s": 0.05,
            "state": {"pd_m": -3.0, "battery_soc_0_1": 1.0},
            "setpoint": {"mode": "altitude_hold", "altitude_m_above_home_target": 5.0},
        }
    )
    assert out["mixer_intent"]["schema_version"] == "drone_mixer_intent.v0.1"
    assert len(out["mixer_intent"]["motor_thrust_0_1"]) == 4
    assert "arbitration" in out


def test_sensory_snapshot_maps_nested_pose_velocity_attitude():
    state = drone_state_from_snapshot(
        {
            "timestamp": 12.5,
            "pose": {"north_m": 4.0, "east_m": -2.0, "altitude_m_above_home": 15.0},
            "velocity": {"north_mps": 1.2, "east_mps": -0.4, "climb_rate_mps": 0.8},
            "attitude": {"roll_rad": 0.1, "pitch_rad": -0.05, "heading_rad": 1.57},
            "rates": {"roll_rate_rps": 0.2, "pitch_rate_rps": -0.1, "yaw_rate_rps": 0.4},
            "battery": {"soc": 0.76},
        }
    )
    assert state.time_s == pytest.approx(12.5)
    assert state.pn_m == pytest.approx(4.0)
    assert state.pe_m == pytest.approx(-2.0)
    assert state.pd_m == pytest.approx(-15.0)
    assert state.vn_mps == pytest.approx(1.2)
    assert state.ve_mps == pytest.approx(-0.4)
    assert state.vd_mps == pytest.approx(-0.8)
    assert state.yaw_rad == pytest.approx(1.57)
    assert state.r_rps == pytest.approx(0.4)
    assert state.battery_soc_0_1 == pytest.approx(0.76)


def test_sensory_stimulus_context_overlays_base_state():
    class Stimulus:
        def __init__(self):
            self.timestamp = 8.0
            self.context = {
                "drone_state": {
                    "pn_m": 9.0,
                    "pe_m": 3.0,
                    "pd_m": -7.0,
                    "battery_soc_0_1": 0.55,
                },
                "attitude": {"yaw": 0.6},
            }

    base = DroneState(vn_mps=2.0, ve_mps=1.0, vd_mps=0.2)
    state = drone_state_from_sensory_stimulus(Stimulus(), base_state=base)
    assert state.time_s == pytest.approx(8.0)
    assert state.pn_m == pytest.approx(9.0)
    assert state.pe_m == pytest.approx(3.0)
    assert state.pd_m == pytest.approx(-7.0)
    assert state.yaw_rad == pytest.approx(0.6)
    assert state.vn_mps == pytest.approx(2.0)
    assert state.ve_mps == pytest.approx(1.0)
    assert state.vd_mps == pytest.approx(0.2)
    assert state.battery_soc_0_1 == pytest.approx(0.55)


def test_robot_adapter_builds_and_parses_actuator_intent():
    mixer = build_mixer_intent(0.5, 0.1, -0.05, 0.02, 1.0)
    intent = build_drone_actuator_intent(
        mixer,
        mission_pause=True,
        estop_recommended=False,
        step_id="hover",
        flow_id="demo",
    )
    parsed = parse_drone_actuator_intent(intent)
    assert intent["schema_version"] == ACTUATOR_INTENT_SCHEMA_VERSION
    assert parsed["mission_pause"] is True
    assert parsed["step_id"] == "hover"
    assert parsed["flow_id"] == "demo"
    assert len(parsed["motor_thrust_0_1"]) == 4


def test_stub_drone_driver_records_tick_log():
    mixer = build_mixer_intent(0.45, 0.0, 0.0, 0.0, 1.0)
    driver = StubDroneDriver()
    log = driver.apply_intent(
        build_drone_actuator_intent(
            mixer,
            mission_pause=False,
            estop_recommended=False,
            transport_hint="can_esc_stub",
        )
    )
    assert log.domain_tag == "drone"
    assert log.transport_hint == "can_esc_stub"
    assert log.collective_thrust_0_1 > 0.0
    assert driver.summary()["tick_count"] == 1


def test_apply_mixer_intent_stub_reports_pause_and_estop():
    mixer = build_mixer_intent(0.3, 0.0, 0.0, 0.0, 1.0)
    out = apply_mixer_intent_stub(mixer, mission_pause=True, estop_recommended=True)
    assert out["mission_paused"] is True
    assert out["estop_latched"] is True
    assert len(out["motor_thrust_0_1"]) == 4


def test_battery_bridge_estimates_more_current_for_more_collective():
    spec = DronePlatformSpec(mass_kg=3.0)
    cfg = DroneBatteryBridgeConfig(nominal_pack_voltage_v=22.2)
    lo = build_mixer_intent(0.25, 0.0, 0.0, 0.0, 1.0)
    hi = build_mixer_intent(0.75, 0.0, 0.0, 0.0, 1.0)
    assert estimate_propulsion_power_w(hi, spec, cfg) > estimate_propulsion_power_w(lo, spec, cfg)
    assert estimate_current_draw_a(hi, spec, cfg) > estimate_current_draw_a(lo, spec, cfg)


def test_battery_bridge_advances_ecm_and_patches_drone_soc():
    try:
        from battery_dynamics import BatteryState as EcmBatteryState
        from battery_dynamics import NMC_EV
    except Exception:
        pytest.skip("battery_dynamics not available")

    spec = DronePlatformSpec(mass_kg=4.0)
    mixer = build_mixer_intent(0.65, 0.02, -0.01, 0.0, 1.0)
    battery_state = EcmBatteryState(soc=0.80, v_rc=0.0, temp_k=298.15)
    out = advance_battery_from_mixer(battery_state, NMC_EV, mixer, spec, 1.0)
    assert out.soc_0_1 < 0.80
    assert out.estimated_current_a > 0.0
    assert out.terminal_voltage_v > 0.0

    drone_state = DroneState(battery_soc_0_1=0.80)
    patched = patch_drone_state_soc(drone_state, out)
    assert patched.battery_soc_0_1 == pytest.approx(out.soc_0_1)


def test_morphing_assessment_patches_mass_and_thrust_budget():
    class Assessment:
        mass_kg = 12.5
        lift_thrust_available_n = 280.0
        hover_margin = 0.14

    spec = DronePlatformSpec(mass_kg=10.0, max_total_thrust_n=200.0)
    patched = patch_spec_from_morphing_assessment(spec, Assessment())
    assert patched.mass_kg == pytest.approx(12.5)
    assert patched.max_total_thrust_n == pytest.approx(280.0)
    assert patched.hover_margin_hint == pytest.approx(0.14)


def test_air_jordan_bridge_patches_gravity_and_density():
    try:
        atm = air_jordan_atmosphere_for_altitude(1500.0)
    except Exception:
        pytest.skip("Air_Jordan is not available")
    assert atm["air_density_kg_m3"] > 0.0
    assert atm["gravity_mps2"] > 0.0

    spec = DronePlatformSpec()
    patched = patch_spec_from_air_jordan(spec, altitude_m_above_home=1500.0)
    assert patched.air_density_kg_m3 == pytest.approx(atm["air_density_kg_m3"])
    assert patched.gravity_mps2 == pytest.approx(atm["gravity_mps2"])


def test_reference_plant_drag_changes_with_density():
    lo = DronePlatformSpec(air_density_kg_m3=0.6, horizontal_drag_coeff_1ps=0.10)
    hi = DronePlatformSpec(air_density_kg_m3=1.6, horizontal_drag_coeff_1ps=0.10)
    state = DroneState(vn_mps=5.0, pd_m=-5.0, battery_soc_0_1=1.0)
    mixer = build_mixer_intent(0.0, 0.0, 0.0, 0.0, 1.0)
    out_lo = integrate_vertical_yaw_reference(state, mixer, lo, 0.5)
    out_hi = integrate_vertical_yaw_reference(state, mixer, hi, 0.5)
    assert abs(out_hi.vn_mps) < abs(out_lo.vn_mps)


# ─── v0.2.0 추가 테스트 ─────────────────────────────────────────────────────


def test_position_hold_east_at_yaw0_moves_east():
    """roll 부호 수정 검증: yaw=0에서 동쪽(pe>0) 목표 → 실제 동쪽 이동."""
    spec = DronePlatformSpec()
    fence = GeofenceConfig()
    gains = ControlGains(pos_kp=0.12, alt_kp=0.12, alt_kd=0.35)
    st = DroneState(pn_m=0.0, pe_m=0.0, pd_m=-5.0, yaw_rad=0.0, battery_soc_0_1=1.0)
    sp = DroneSetpoint(
        mode="position_hold",
        altitude_m_above_home_target=5.0,
        pn_m_target=0.0,
        pe_m_target=4.0,
    )
    for _ in range(500):
        st = run_control_tick(st, sp, spec, fence, 0.02, gains=gains).state
    assert st.pe_m > 1.0, f"pe_m={st.pe_m:.3f}: 동쪽으로 이동해야 함"
    assert abs(st.pn_m) < 2.0, f"pn_m={st.pn_m:.3f}: 북쪽 이탈 없어야 함"


def test_roll_command_gives_east_acceleration_at_yaw0():
    """단일 틱: roll 음수 명령 → phi 음수 → ae 양수(동쪽)."""
    spec = DronePlatformSpec()
    mixer = build_mixer_intent(0.49, -0.10, 0.0, 0.0, 1.0)  # roll_torque < 0 → phi < 0 → east
    state = DroneState(pd_m=-5.0, yaw_rad=0.0, battery_soc_0_1=1.0)
    # 직접 phi 음수 주입
    import math as _math
    state.roll_rad = -0.10
    out = integrate_vertical_yaw_reference(state, mixer, spec, 0.05)
    assert out.ve_mps > 0.0, f"ve_mps={out.ve_mps:.4f}: phi<0, yaw=0 → 동쪽 가속 기대"


def test_health_observer_healthy_run():
    """정상 호버링 로그 → healthy 판정."""
    spec = DronePlatformSpec()
    mixer = build_mixer_intent(0.49, 0.0, 0.0, 0.0, 1.0)
    driver = StubDroneDriver()
    for _ in range(20):
        intent = build_drone_actuator_intent(
            mixer,
            mission_pause=False,
            estop_recommended=False,
        )
        intent["battery_soc_0_1"] = 0.80
        driver.apply_intent(intent)
    report = observe_drone_health(driver.tick_logs, spec=spec)
    assert isinstance(report, DroneHealthReport)
    assert report.verdict in {"healthy", "degraded"}
    assert report.omega_total > 0.0
    assert "power" in report.extra_axes
    assert "navigation" in report.extra_axes
    assert "authority" in report.extra_axes
    assert "motor_sat" in report.extra_axes


def test_health_observer_estop_degrades():
    """ESTOP 발생 → verdict = critical 또는 degraded (healthy 아님)."""
    spec = DronePlatformSpec()
    mixer = build_mixer_intent(0.49, 0.0, 0.0, 0.0, 1.0)
    driver = StubDroneDriver()
    for _ in range(10):
        intent = build_drone_actuator_intent(
            mixer,
            mission_pause=True,
            estop_recommended=True,
        )
        intent["battery_soc_0_1"] = 0.05  # critical battery
        driver.apply_intent(intent)
    report = observe_drone_health(driver.tick_logs, spec=spec)
    assert report.verdict != "healthy"
    assert report.extra_axes["power"] < 0.5


def test_health_observer_nav_penalty_on_pause():
    """mission_pause 100% → navigation 점수 낮음."""
    spec = DronePlatformSpec()
    mixer = build_mixer_intent(0.49, 0.0, 0.0, 0.0, 1.0)
    driver = StubDroneDriver()
    for _ in range(15):
        intent = build_drone_actuator_intent(mixer, mission_pause=True)
        intent["battery_soc_0_1"] = 0.90
        driver.apply_intent(intent)
    report = observe_drone_health(driver.tick_logs, spec=spec)
    assert report.extra_axes["navigation"] < 0.7


def test_health_observer_motor_sat_penalty():
    """포화 모터(thrust≥0.97) 다수 → motor_sat 점수 낮음."""
    spec = DronePlatformSpec()
    # 강제 포화: collective=1.0
    mixer_sat = build_mixer_intent(1.0, 0.0, 0.0, 0.0, 1.0)
    driver = StubDroneDriver()
    for _ in range(15):
        intent = build_drone_actuator_intent(mixer_sat)
        intent["battery_soc_0_1"] = 0.90
        driver.apply_intent(intent)
    report = observe_drone_health(driver.tick_logs, spec=spec)
    assert report.extra_axes["motor_sat"] < 0.6


def test_health_observer_str_format():
    """__str__ 출력에 omega와 verdict 포함."""
    spec = DronePlatformSpec()
    mixer = build_mixer_intent(0.49, 0.0, 0.0, 0.0, 1.0)
    driver = StubDroneDriver()
    intent = build_drone_actuator_intent(mixer)
    intent["battery_soc_0_1"] = 0.75
    driver.apply_intent(intent)
    report = observe_drone_health(driver.tick_logs, spec=spec)
    s = str(report)
    assert "Ω=" in s
    assert "verdict=" in s


def test_health_observer_empty_logs_critical():
    """빈 로그 → critical."""
    report = observe_drone_health([])
    assert report.verdict == "critical"
    assert report.tick_count == 0
