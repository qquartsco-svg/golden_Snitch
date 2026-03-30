# 드론 제어 — 레이어 맵 (확장형)

> **한국어 (정본).** English: [LAYER_MAP_EN.md](LAYER_MAP_EN.md)

## 1. 이 패키지의 층

| 층 | 모듈 | 역할 |
|----|------|------|
| 계약 | `contracts.py` | `DroneState`(NED), `DroneSetpoint`, `DronePlatformSpec`, `GeofenceConfig`, `MixerIntent` |
| 안전 | `arbiter.py` | 배터리·지오펜스·틸트 → `ControlArbitration` (Cooking `ArbiterVerdict` 와 유사 역할) |
| 믹서 | `mixer.py` | `quad_x_mix`, 정규화 모터 0..1 |
| 제어 루프 | `control_tick.py` | `run_control_tick` — 참조 PID + 믹서 호출 |
| 플랜트 | `reference_plant.py` | **교체 가능** 단순 역학 |
| 비행 브리지 | `flight_bridges.py` | `Morphing_Flight_Foundation` / `Air_Jordan` 값을 `DronePlatformSpec` 공통 분모로 내림 |
| 센서 브리지 | `sensory_adapter.py` | `Sensory_Input_Kernel` 류 snapshot / `SensoryStimulus.context` → `DroneState` |
| HAL 어댑터 | `robot_adapter.py` | `MixerIntent` → actuator intent / `DroneTickLog` (실제 PWM·CAN·SDK 바인딩 전 스텁) |
| 표면 | `surface.py` | JSON 틱 — L4/임베디드 게이트웨이용 |

## 2. 인접 00_BRAIN / 스테이징 엔진

| 엔진 | 관계 |
|------|------|
| [Morphing_Flight_Foundation](../Morphing_Flight_Foundation/README.md) | 형상·모드별 양력/항력 예산 — **기체 물리 상한** 입력으로 `DronePlatformSpec` 확장 가능 |
| [Transformable_Air_Mobility_Stack](../Transformable_Air_Mobility_Stack/README.md) | 플랫폼 모드 FSM·시퀀스 — **상위 미션 상태**가 `DroneSetpoint.mode`·아비터 정책으로 내려옴 |
| [Morphing_Flight_Foundation](../Morphing_Flight_Foundation/README.md) | 형상/모드별 thrust·mass budget — `DronePlatformSpec.max_total_thrust_n` / `mass_kg` 로 내려올 수 있음 |
| [Vehicle_Platform_Foundation](../Vehicle_Platform_Foundation/README.md) | 지상 주행/4WD — **접지·택시** 단계와 드론 틱 분리 유지 |
| [Air_Jordan](../Air_Jordan/README.md) | ISA 대기·고도 보정 중력 — `gravity_mps2` / `air_density_kg_m3` 로 내려올 수 있음 |
| [Sensory_Input_Kernel](../Sensory_Input_Kernel/README.md) | 감각/센서 ingress — 위치·속도·자세·배터리 snapshot을 `DroneState`로 정규화 |
| Defense `aerial_autonomy` | 포인트 질량 6DOF 스타일 — **고해상도 시뮬** 교체 시 참고(의존성으로 끌어오지 않음) |
| [Cooking_Process_Foundation](../Cooking_Process_Foundation/README.md) | 패턴 참고: 틱 페이로드·HAL intent·아비터 |

## 3. 확장 체크리스트

1. **추정기**: `drone_state_from_snapshot()` 을 기본 브리지로 쓰고, 필요 시 EKF/SLAM 전용 어댑터로 승격.
2. **미션**: 웨이포인트 FSM → `DroneSetpoint` 생성.
3. **FCU**: `robot_adapter.build_drone_actuator_intent()` 이후 실제 PWM/`actuator_controls` / 벤더 SDK 바인딩.
4. **시뮬**: `integrate_vertical_yaw_reference` 대체.

*v0.1 — 참조 루프; 실기체 튜닝은 통합사.*

## 4. 점검 메모 (v0.1.2)

- `armed_hover` / `altitude_hold` 는 참조 루프에서 **동일 경로**; FCU 모드 1:1 매핑은 어댑터 책임.
- 지오펜스 이탈은 `mission_pause + torque_scale` 중심의 **recoverable safety mode** 로 처리; 즉시 thrust cut은 `battery_critical` 같은 하드 fault에 한정.
- `reference_plant` 수평축은 이제 `yaw`를 반영해 `position_hold` 참조 시뮬레이션과 프레임 일치.
- `flight_bridges` 는 공력 엔진 전체를 끌어오지 않고, DCF가 안전하게 소비할 수 있는 공통 분모(`mass`, `thrust`, `density`, `gravity`)만 내린다.
- `flight_bridges` 는 공력 엔진 전체를 끌어오지 않고, DCF가 안전하게 소비할 수 있는 공통 분모(`mass`, `thrust`, `density`, `gravity`, `hover_margin_hint`)만 내린다.
- `sensory_adapter` 는 특정 센서 SDK에 묶이지 않고, flat/nested snapshot·`SensoryStimulus.context` 를 모두 허용하는 얇은 정규화 층이다.
- `robot_adapter` 는 하드웨어 SDK를 넣지 않고 `MixerIntent -> actuator intent -> DroneTickLog` 경계만 고정하는 스텁이다.
- `examples/run_sensor_dcf_battery_stub.py` 는 센서 snapshot에서 시작해 제어·배터리·HAL 스텁까지 이어지는 최소 end-to-end 점검 경로다.
- `SIGNATURE.sha256` / 블록체인 번들은 **미도입** (COOKing 패키지와 별도).
- 상세 체크리스트: [README.md](../README.md) «점검 체크리스트» 절.
