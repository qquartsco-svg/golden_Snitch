# Vendor Binding Slots

> **한국어 (정본)** — `Drone_Control_Foundation` 를 실제 FCU/ESC/SDK와 연결할 때, 어느 경계에서 무엇을 붙여야 하는지 정리한 메모.

## 원칙

`Drone_Control_Foundation` 안에는 **벤더 SDK를 직접 넣지 않는다.**

DCF는 다음 두 경계까지만 책임진다.

1. `DroneState`
2. `MixerIntent` / actuator intent

즉 제품형 적층은 다음처럼 가야 한다.

```text
Sensors / EKF / GPS / IMU
    -> drone_state_from_snapshot()
    -> run_control_tick()
    -> build_drone_actuator_intent()
    -> vendor binding layer
    -> PX4 / ArduPilot / ESC / CAN / PWM
```

## 바인딩 슬롯

### 1. State Ingress Slot

- 입력:
  - IMU/EKF pose
  - GPS / VIO / mocap
  - battery telemetry
- 출력:
  - `DroneState`
- 권장 위치:
  - `sensory_adapter.py` 앞단 또는 별도 `vendor_state_adapter.py`

### 2. Command Egress Slot

- 입력:
  - `MixerIntent`
  - `build_drone_actuator_intent()` 결과
- 출력:
  - PWM normalized
  - CAN ESC packet
  - MAVLink actuator / setpoint
- 권장 위치:
  - DCF 바깥 별도 패키지
  - 예: `Drone_Robot_Adapter`, `PX4_Driver`, `ArduPilot_Bridge`

### 3. Safety Watchdog Slot

- 입력:
  - estop
  - mission_pause
  - driver heartbeat
- 역할:
  - link timeout
  - watchdog disarm
  - transport fallback
- 권장 위치:
  - vendor binding layer 또는 상위 HAL supervisor

## 권장 파일 구조

```text
Drone_Control_Foundation/
  drone_control_foundation/
    contracts.py
    control_tick.py
    arbiter.py
    robot_adapter.py      # generic actuator intent boundary only

Drone_Robot_Adapter/
  drone_robot_adapter/
    px4_bridge.py
    ardupilot_bridge.py
    nexus_bridge.py
```

## 왜 분리하는가

- DCF는 물리/제어 코어여야 한다.
- PX4, MAVLink, CAN, PWM, vendor SDK는 수명이 다르고 자주 바뀐다.
- 이 둘을 섞으면 제어 검증과 하드웨어 검증이 함께 꼬인다.

## 최소 제품 흐름

1. 센서/추정기에서 `DroneState` 생성
2. `run_control_tick()` 호출
3. `build_drone_actuator_intent()`로 HAL 경계 고정
4. 벤더 바인딩에서 실제 transport 변환
5. watchdog과 estop은 바인딩/HAL 층에서 1차 실행

## 한 줄 결론

DCF는 **제어 코어**, vendor binding은 **별도 HAL 제품층**이다.  
정밀함을 높이려면 둘을 더 강하게 섞는 게 아니라, 경계를 더 정확히 고정해야 한다.

현재 스캐폴드:
- [Drone_Robot_Adapter](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Robot_Adapter/README.md)
