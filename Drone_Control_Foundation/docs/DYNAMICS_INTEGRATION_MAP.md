# Drone Dynamics Integration Map

> **한국어 (정본)** — 드론 정밀도를 높이기 위해 `Drone_Control_Foundation` 에 바로 붙일 수 있는 기존 엔진들을 정리한 맵.

## 1. 지금 당장 붙이는 축

| 엔진 | DCF 안 역할 | 지금 상태 |
|------|-------------|-----------|
| [Sensory_Input_Kernel](/Users/jazzin/Desktop/00_BRAIN/_staging/Sensory_Input_Kernel/README.md) | 센서 ingress / snapshot → `DroneState` | `sensory_adapter.py` 로 연결됨 |
| [Transformable_Air_Mobility_Stack](/Users/jazzin/Desktop/00_BRAIN/_staging/Transformable_Air_Mobility_Stack/README.md) | 상위 모드 FSM → `DroneSetpoint` / `DronePlatformSpec` | TAM 어댑터로 연결됨 |
| [Battery_Dynamics_Engine](/Users/jazzin/Desktop/00_BRAIN/_staging/Battery_Dynamics_Engine/README.md) | 추진 전류 추정, SOC·전압·열 상태 갱신 | `battery_adapter.py` 로 얇게 연결 |
| [Morphing_Flight_Foundation](/Users/jazzin/Desktop/00_BRAIN/_staging/Morphing_Flight_Foundation/README.md) | 형상/모드별 질량·가용 수직추력 budget → `DronePlatformSpec` | `flight_bridges.py` 로 질량/추력 상한 연결 |
| [Air_Jordan](/Users/jazzin/Desktop/00_BRAIN/_staging/Air_Jordan/README.md) | ISA 대기 밀도 / 중력 보정 | `flight_bridges.py` 로 density/gravity 연결 |
| [Robot_Adapter_Core](/Users/jazzin/Desktop/00_BRAIN/_staging/Robot_Adapter_Core/README.md) | `MixerIntent` → actuator intent / tick log | `robot_adapter.py` 스텁 연결 |
| [Drone_Robot_Adapter](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Robot_Adapter/README.md) | actuator intent → PX4 / ArduPilot / vendor transport envelope | DCF 밖 별도 HAL 제품층 |

## 2. 다음 자연스러운 축

| 엔진 | DCF 안 역할 | 메모 |
|------|-------------|------|
| [Morphing_Flight_Foundation](/Users/jazzin/Desktop/00_BRAIN/_staging/Morphing_Flight_Foundation/README.md) | hover margin / thrust vector / transition budget 고도화 | 현재는 질량·추력 상한만 소비 |
| [Air_Jordan](/Users/jazzin/Desktop/00_BRAIN/_staging/Air_Jordan/README.md) | 고도별 대기 밀도 / 중력 / 공력 proxy 고도화 | 현재는 density/gravity만 소비, 공력항력은 아직 미연결 |
| `vendor FCU SDK` | PX4/ArduPilot/ESC/CAN 실제 출력 | DCF 바깥 HAL 계층에서만 붙여야 함 |

## 3. 상위 오케스트레이션 축

| 엔진 | 관계 | 왜 바로 DCF 안에 안 넣는가 |
|------|------|-----------------------------|
| `ATON / Nexus` | 여러 하위 엔진을 묶는 수평 통합 오케스트레이터 | 제어 틱 안의 물리 코어가 아니라, 상위 플릿/미션/상태공간 orchestration 쪽에 더 자연스러움 |

## 4. 권장 적층 순서

1. `Sensory_Input_Kernel` → `DroneState`
2. `TAM` → `DroneSetpoint`, `DronePlatformSpec`
3. `Battery_Dynamics_Engine` → SOC/전압/열 갱신
4. `Morphing_Flight_Foundation` / `Air_Jordan` → thrust / density / drag budget
5. `Robot_Adapter_Core` 기반 HAL
6. 그 위에 `Nexus` / 상위 오케스트레이션

## 5. 한 줄 원칙

`Nexus` 는 **드론 틱을 직접 계산하는 엔진**이 아니라, 여러 하위 엔진을 묶는 상위 orchestration 쪽이다.  
반대로 `Battery_Dynamics_Engine`, `Sensory_Input_Kernel`, `Morphing_Flight_Foundation`, `Air_Jordan` 은 **DCF 물리·상태 레이어에 직접 붙일 수 있는 엔진**이다.
