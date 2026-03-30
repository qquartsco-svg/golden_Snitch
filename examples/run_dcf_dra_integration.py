"""
golden_Snitch 통합 예제: DCF → DRA 완전 파이프라인
=======================================================

흐름:
  DroneState  (센서 입력)
      → Drone_Control_Foundation: run_control_tick()
      → MixerIntent / ControlTickResult
      → build_drone_actuator_intent()
      → actuator intent dict (계약 경계)
      → Drone_Robot_Adapter: build_px4_command_envelope()
                             build_ardupilot_command_envelope()
                             build_nexus_drone_signal()
      → 벤더 envelope / Nexus signal 출력

두 레이어가 분리된 이유:
  - DCF: "무엇을 해야 하는가" — 제어 계산, 아비터, 믹서
  - DRA: "어떻게 전달하는가" — PX4/ArduPilot transport, watchdog
  - 계약 경계(actuator intent dict)만 공유, 내부 구현은 서로 모름
"""
from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_DCF = os.path.join(_ROOT, "Drone_Control_Foundation")
_RAC = os.path.abspath(os.path.join(_ROOT, "..", "Robot_Adapter_Core"))

for _p in [_ROOT, _DCF, _RAC]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

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


def _print_section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def demo_altitude_hold() -> None:
    """시나리오 1: 고도 유지 — DCF가 추력 계산 → DRA가 PX4 envelope 생성."""
    _print_section("시나리오 1: altitude_hold → PX4 envelope")

    # 1. 드론 현재 상태 (센서 입력 대신 직접 생성)
    state = DroneState(
        pd_m=-8.0,           # 현재 고도 8 m
        battery_soc_0_1=0.82,
        vd_mps=-0.1,         # 약간 하강 중
    )

    # 2. 세트포인트: 10 m 고도 유지
    setpoint = DroneSetpoint(
        mode="altitude_hold",
        altitude_m_above_home_target=10.0,
    )

    # 3. DCF: 한 틱 제어 계산 (dt=20 ms)
    spec = DronePlatformSpec()
    geo = GeofenceConfig()
    result = run_control_tick(state, setpoint, spec, geo, dt_s=0.02)

    print(f"[DCF] 아비터: thrust_allowed={result.arbitration.allow_thrust}, "
          f"mission_pause={result.arbitration.mission_pause}, "
          f"torque_scale={result.arbitration.torque_scale_0_1:.2f}")
    print(f"[DCF] 믹서: collective={result.mixer.collective_thrust_0_1:.3f}, "
          f"motors={[f'{m:.3f}' for m in result.mixer.motor_thrust_0_1]}")

    # 4. DCF → actuator intent (계약 경계)
    intent = build_drone_actuator_intent(
        result.mixer,
        mission_pause=result.arbitration.mission_pause,
        estop_recommended=result.arbitration.disarm_recommended,
        step_id="alt_hold_tick0",
        flow_id="demo_flight",
    )
    print(f"[계약] actuator intent: schema={intent['schema_version']}, "
          f"primary={intent['primary_output_0_1']:.3f}, "
          f"pause={intent['mission_pause']}")

    # 5. DRA: PX4 envelope 생성
    px4_env = build_px4_command_envelope(intent)
    print(f"[DRA/PX4] transport={px4_env.transport}, "
          f"thrust_sp={px4_env.thrust_sp_0_1:.3f}, "
          f"motors={[f'{m:.3f}' for m in px4_env.actuator_controls_0_1]}")


def demo_geofence_breach() -> None:
    """시나리오 2: 지오펜스 이탈 → mission_pause → DRA가 이를 ArduPilot에 전달."""
    _print_section("시나리오 2: 지오펜스 이탈 → ArduPilot envelope")

    state = DroneState(
        pn_m=120.0,          # 지오펜스 반경(100 m) 이탈
        pd_m=-15.0,
        battery_soc_0_1=0.65,
    )
    setpoint = DroneSetpoint(mode="position_hold")
    spec = DronePlatformSpec()
    geo = GeofenceConfig(enabled=True, max_horizontal_m=100.0)

    result = run_control_tick(state, setpoint, spec, geo, dt_s=0.02)

    print(f"[DCF] 아비터: allow_thrust={result.arbitration.allow_thrust}, "
          f"mission_pause={result.arbitration.mission_pause}, "
          f"torque_scale={result.arbitration.torque_scale_0_1:.2f}")

    intent = build_drone_actuator_intent(
        result.mixer,
        mission_pause=result.arbitration.mission_pause,
        estop_recommended=result.arbitration.disarm_recommended,
        step_id="breach_tick",
        flow_id="demo_flight",
    )
    print(f"[계약] mission_pause={intent['mission_pause']}, "
          f"estop_recommended={intent['estop_recommended']}, "
          f"allow_motion={intent['allow_motion']}")

    ardu_env = build_ardupilot_command_envelope(intent)
    print(f"[DRA/ArduPilot] transport={ardu_env.transport}, "
          f"collective={ardu_env.collective_0_1:.3f}, "
          f"motors={[f'{m:.3f}' for m in ardu_env.motor_outputs_0_1]}")


def demo_nexus_signal_with_watchdog() -> None:
    """시나리오 3: DCF 틱 결과 → DRA watchdog → Nexus signal 브리핑."""
    _print_section("시나리오 3: DCF → watchdog → Nexus signal")

    state = DroneState(pd_m=-20.0, battery_soc_0_1=0.45)
    setpoint = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=20.0)
    result = run_control_tick(state, setpoint, DronePlatformSpec(), GeofenceConfig(), 0.02)

    intent = build_drone_actuator_intent(
        result.mixer,
        mission_pause=result.arbitration.mission_pause,
        estop_recommended=result.arbitration.disarm_recommended,
        flow_id="nexus_demo",
    )

    # watchdog: 하드웨어 바인딩 생존 확인 (t=10.0에 heartbeat, t=10.3에 확인)
    watchdog = BindingWatchdog(stale_after_s=1.0)
    watchdog.mark_heartbeat(10.0, transport="px4_actuator_controls")
    snap = watchdog.snapshot(10.3)

    signal = build_nexus_drone_signal(
        mission_pause=intent["mission_pause"],
        estop_recommended=intent["estop_recommended"],
        binding_health=snap,
        collective_0_1=intent["primary_output_0_1"],
    )

    print("[DRA/Nexus] signal:")
    for line in render_nexus_drone_lines(signal):
        print(f"  {line}")

    print(f"\n[배터리 경고] SOC={state.battery_soc_0_1:.0%} "
          f"({'저전압 주의' if state.battery_soc_0_1 < 0.50 else 'OK'})")


def main() -> None:
    print("\n[golden_Snitch] DCF + DRA 통합 파이프라인 데모")
    print("  Drone_Control_Foundation (제어) → Drone_Robot_Adapter (HAL)")

    demo_altitude_hold()
    demo_geofence_breach()
    demo_nexus_signal_with_watchdog()

    print("\n[완료] 세 시나리오 모두 정상 동작.")
    print("  실제 구축 시: MAVLink/PWM/CAN 드라이버를 DRA 위에 올리면 됩니다.")


if __name__ == "__main__":
    main()
