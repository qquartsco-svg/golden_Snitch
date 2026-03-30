# golden_Snitch

**저장소:** [`qquartsco-svg/golden_Snitch`](https://github.com/qquartsco-svg/golden_Snitch)
**버전:** 0.1.7
**구성:** `Drone_Control_Foundation` (제어 코어) + `Drone_Robot_Adapter` (HAL)
**영문 개요:** [`README_EN.md`](README_EN.md)

> **한 저장소, 두 레이어.**
> 드론 제어 연산과 하드웨어 바인딩을 명확한 계약 경계로 분리한다.
> DCF가 "무엇을 해야 하는가"를 계산하고, DRA가 "어떻게 전달하는가"를 처리한다.

---

## 핵심 개념

`golden_Snitch`는 드론 하나의 거대한 패키지가 아니라, 아래 두 층을 한 저장소 안에서 함께 관리하는 구조다.

1. **Drone_Control_Foundation (DCF)**
   - 드론이 현재 상태에서 어떤 추력/토크를 내야 하는지 계산하는 제어 코어
2. **Drone_Robot_Adapter (DRA)**
   - 그 계산 결과를 PX4, ArduPilot, PWM, CAN 같은 실제 transport 표현으로 번역하는 제품층 HAL

이 분리는 단순한 코드 스타일 문제가 아니다.

- 제어 로직이 벤더 SDK에 오염되지 않는다.
- FCU를 바꿔도 DCF는 다시 튜닝하지 않고 유지할 수 있다.
- 감사/audit에서는 `의도 계산`과 `전달 계층`을 따로 검증할 수 있다.
- 상위 orchestration(`TAM`, `Nexus`)은 하위 구현 세부 대신 계약과 health만 읽으면 된다.

---

## 레이어 구성

| 레이어 | 경로 | 역할 |
|--------|------|------|
| **Drone_Control_Foundation (DCF)** | [`Drone_Control_Foundation/`](Drone_Control_Foundation/README.md) | 제어 코어 — 상태·세트포인트, 안전 아비터, 쿼드-X 믹서, 참조 플랜트, 건강도 옵저버 |
| **Drone_Robot_Adapter (DRA)** | `drone_robot_adapter/` (루트 패키지) | HAL — DCF actuator intent → PX4·ArduPilot envelope, watchdog, Nexus signal |

---

## 아키텍처: 한 줄 흐름

```
센서 입력 (DroneState)
    → Drone_Control_Foundation
        · evaluate_control_arbitration()   : 안전 게이트 (지오펜스, 배터리, estop)
        · run_control_tick()               : 고도/요/수평 제어 계산
        · quad_x_mix()                     : 4축 모터 믹서
        → MixerIntent  →  build_drone_actuator_intent()
    ──────────────── actuator intent dict (계약 경계) ─────────────────
    → Drone_Robot_Adapter
        · build_px4_command_envelope()     : PX4 transport envelope
        · build_ardupilot_command_envelope(): ArduPilot transport envelope
        · BindingWatchdog.snapshot()       : HAL 생존 확인
        · build_nexus_drone_signal()       : 상위 orchestration 브리핑
    → PX4 / ArduPilot FCU · ESC · PWM · CAN
```

**계약 경계 (`actuator intent dict`)** 는 두 레이어가 공유하는 유일한 인터페이스다.
DCF는 DRA 내부를 모르고, DRA는 DCF 제어 로직을 모른다.

---

## 계약 경계: actuator intent 필드

| 필드 | 구분 | 의미 |
|------|------|------|
| `schema_version` | 필수 | 현재 계약 버전 (`drone_actuator_intent.v0.1`) |
| `primary_output_0_1` | 필수 | collective/thrust 1차 출력 [0, 1] |
| `motor_thrust_0_1` | 필수 | 4축 모터 정규화 추력 tuple |
| `allow_motion` | 필수 | 실제 움직임 허용 여부 |
| `mission_pause` | 필수 | 상위 안전 계층의 미션 정지 요구 |
| `estop_recommended` | 필수 | 즉시 안전 정지 권고 |
| `step_id` | 보존 | 스텝/시퀀스 식별자 (운용 추적) |
| `flow_id` | 보존 | 플로우/세션 식별자 (감사) |
| `transport_hint` | 선택 | 하위 벤더 바인딩 참고용 transport 힌트 |

이 표의 의미는 간단하다.

- **DCF는 이 dict까지만 책임진다.**
- **DRA는 이 dict부터 아래를 책임진다.**
- 실제 FCU/ESC SDK는 그 다음 층에서만 다룬다.

즉 이 dict가 두 레이어 사이의 유일한 합의면이다.

---

## 빠른 시작: 통합 파이프라인

### 설치 (로컬 개발)

```bash
git clone https://github.com/qquartsco-svg/golden_Snitch.git
cd golden_Snitch
# Robot_Adapter_Core가 ../Robot_Adapter_Core 에 있으면 자동 인식
```

### DCF → DRA 전체 파이프라인

```python
import sys
sys.path.insert(0, "Drone_Control_Foundation")   # DCF 패키지 경로

from drone_control_foundation import (
    DroneState, DroneSetpoint, DronePlatformSpec, GeofenceConfig,
    build_drone_actuator_intent, run_control_tick,
)
from drone_robot_adapter import (
    BindingWatchdog,
    build_px4_command_envelope,
    build_nexus_drone_signal,
    render_nexus_drone_lines,
)

# 1. 센서 상태
state = DroneState(pd_m=-8.0, battery_soc_0_1=0.82)

# 2. 세트포인트
setpoint = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=10.0)

# 3. DCF: 제어 계산
result = run_control_tick(state, setpoint, DronePlatformSpec(), GeofenceConfig(), dt_s=0.02)

# 4. 계약 경계 생성
intent = build_drone_actuator_intent(
    result.mixer,
    mission_pause=result.arbitration.mission_pause,
    estop_recommended=result.arbitration.disarm_recommended,
    step_id="hover_tick0",
    flow_id="mission_alpha",
)

# 5. DRA: PX4 envelope
px4_env = build_px4_command_envelope(intent)
print(f"PX4 thrust: {px4_env.thrust_sp_0_1:.3f}, motors: {px4_env.actuator_controls_0_1}")

# 6. DRA: watchdog + Nexus signal
watchdog = BindingWatchdog(stale_after_s=1.0)
watchdog.mark_heartbeat(0.0, transport="px4_actuator_controls")
signal = build_nexus_drone_signal(
    mission_pause=intent["mission_pause"],
    estop_recommended=intent["estop_recommended"],
    binding_health=watchdog.snapshot(0.3),
    collective_0_1=intent["primary_output_0_1"],
)
for line in render_nexus_drone_lines(signal):
    print(line)
```

### 실행 가능 예제

```bash
# DCF + DRA 통합 파이프라인 (3시나리오)
python3 examples/run_dcf_dra_integration.py

# DRA 단독: Nexus signal 브리핑
python3 examples/run_nexus_drone_brief.py

# DCF 단독: 센서→제어→배터리→HAL 스텁
cd Drone_Control_Foundation && python3 examples/run_sensor_dcf_battery_stub.py
```

---

## 디렉터리 구조

```text
golden_Snitch/
│
├── Drone_Control_Foundation/               ← 제어 코어 (DCF)
│   ├── drone_control_foundation/
│   │   ├── contracts.py                    DroneState, DroneSetpoint, MixerIntent 등
│   │   ├── arbiter.py                      안전 아비터 (지오펜스·배터리·estop)
│   │   ├── control_tick.py                 한 틱 제어 파이프라인
│   │   ├── mixer.py                        쿼드-X 믹서
│   │   ├── reference_plant.py              참조 플랜트 (NED, ZYX 회전행렬)
│   │   ├── robot_adapter.py                actuator intent 생성, StubDroneDriver
│   │   ├── sensory_adapter.py              센서 snapshot → DroneState
│   │   ├── battery_adapter.py              배터리 SOC 브리지
│   │   ├── flight_bridges.py               대기·모핑 물리 브리지
│   │   ├── health.py                       7축 Ω 건강도 옵저버
│   │   └── surface.py                      JSON 틱 표면
│   ├── tests/
│   │   └── test_drone_control_foundation.py    29개
│   ├── examples/
│   └── README.md                           ← DCF 상세 문서
│
├── drone_robot_adapter/                    ← HAL 패키지 (DRA)
│   ├── contracts.py                        PX4/ArduPilot/Nexus envelope 계약
│   ├── px4_bridge.py                       PX4 transport envelope
│   ├── ardupilot_bridge.py                 ArduPilot transport envelope
│   ├── nexus_bridge.py                     Nexus signal 빌더
│   └── watchdog.py                         BindingWatchdog
│
├── docs/
│   ├── PX4_ARDUPILOT_MAPPING.md            벤더 필드 매핑 표
│   └── NEXUS_CONSUMPTION.md                Nexus 연결 방향
│
├── examples/
│   ├── run_dcf_dra_integration.py          ★ DCF+DRA 통합 데모 (3시나리오)
│   └── run_nexus_drone_brief.py            DRA 단독 Nexus 데모
│
├── tests/
│   ├── test_dcf_dra_integration.py         ★ 통합 테스트 24개
│   └── test_drone_robot_adapter.py         DRA 단독 테스트
│
├── scripts/
│   ├── regenerate_signature.py
│   ├── verify_signature.py
│   ├── release_check.py
│   └── cleanup_generated.py
│
├── BLOCKCHAIN_INFO.md
├── CHANGELOG.md
├── PHAM_BLOCKCHAIN_LOG.md
├── SIGNATURE.sha256
├── VERSION                                 0.1.6
└── pyproject.toml
```

---

## Drone_Control_Foundation (DCF)

| 기능 | 설명 |
|------|------|
| **안전 아비터** | 지오펜스 이탈 → `mission_pause + torque_scale` (호버/복구 권한 유지) |
| **제어 루프** | 고도·요·수평 PD 제어, `dt_s` 기반 적분 |
| **쿼드-X 믹서** | roll/pitch/yaw 토크 + collective → 4축 모터 [0, 1] |
| **참조 플랜트** | NED 좌표계, ZYX 회전행렬 기반 6DOF 수평 가속 |
| **센서 브리지** | `drone_state_from_snapshot()` — sensory snapshot → DroneState |
| **배터리 브리지** | 전력·전류 추정, SOC 갱신 |
| **대기 브리지** | `patch_spec_from_air_jordan()` — 고도별 밀도·중력 반영 |
| **건강도 옵저버** | 7축 Ω: safety·motion·flow·power·navigation·authority·motor_sat |
| **JSON 표면** | `run_drone_tick()` — dict 입출력, FCU 통합 가능 |

비행 모드:

| 모드 | 동작 |
|------|------|
| `disarmed` | 추력 차단 완전 |
| `altitude_hold` | 고도·요 유지 |
| `position_hold` | N/E 목표 추종 (소각도 롤·피치 명령) |

---

## Drone_Robot_Adapter (DRA)

| 컴포넌트 | 출력 |
|----------|------|
| `build_px4_command_envelope()` | `PX4CommandEnvelope` — thrust_sp, actuator_controls[4] |
| `build_ardupilot_command_envelope()` | `ArduPilotCommandEnvelope` — collective, motor_outputs[4] |
| `build_nexus_drone_signal()` | `DroneAdapterNexusSignal` — 상위 orchestration 브리핑 |
| `render_nexus_drone_lines()` | 브리핑 → 텍스트 목록 |
| `BindingWatchdog` | heartbeat 추적, stale/degraded 감지 |

DRA가 하지 않는 것: 실제 MAVLink 연결, PWM/CAN 전송, 비행 제어 계산, 센서 융합.

### Watchdog 건강도 기준

| 상태 | 기준 | 의미 |
|------|------|------|
| `healthy` | heartbeat가 `stale_after_s` 이내, driver fault 없음 | 바인딩 생존, 상위 보고 정상 |
| `stale` | heartbeat age 초과 | 링크는 있었지만 현재 신선하지 않음 |
| `degraded` | driver fault 또는 transport 불일치/불명확 | 즉시 상위 보고 및 복구 절차 권장 |

이 기준은 `Nexus`나 운영 대시보드가 "지금 드론이 날 수 있는가"가 아니라, "제어 의도가 제품층에서 제대로 전달되고 있는가"를 읽기 위한 신호다.

---

## 테스트

```bash
# DRA + 통합 (28개)
python3 -m pytest tests/ -v

# DCF 단독 (29개)
cd Drone_Control_Foundation && python3 -m pytest tests/ -v
```

| 파일 | 범위 | 통과 |
|------|------|------|
| `tests/test_dcf_dra_integration.py` | 계약·PX4·ArduPilot·pause전파·Nexus·disarmed | **24** |
| `tests/test_drone_robot_adapter.py` | DRA 단독 | **4** |
| `Drone_Control_Foundation/tests/…` | DCF 단독 | **29** |

---

## 활용성

이 저장소는 단순 연구용 샘플보다 조금 더 실전적인 위치를 겨냥한다.

- **민수/연구용 드론 제어 스택 분리**
  - 제어 코어와 하드웨어 바인딩을 분리한 채 제품화 가능
- **벤더 교체 내성**
  - PX4에서 ArduPilot로 넘어가도 DCF를 다시 짜지 않는다
- **시뮬레이션/실기 간 공통 경계 유지**
  - DCF의 출력은 동일한 `actuator intent`이고, DRA만 달라진다
- **상위 시스템 통합**
  - `Transformable_Air_Mobility_Stack`, `Nexus`, 배터리/센서/형상 엔진이 읽기 좋은 형태로 연결 가능
- **감사와 안전 분석**
  - step/flow 식별자, mission pause, estop 권고가 끝까지 보존된다

---

## 확장 경로

현재 `golden_Snitch`는 **제어 코어 + HAL 계약 + 제품층 스캐폴드**까지 닫힌 상태다. 다음 확장은 아래 순서가 자연스럽다.

1. **실제 vendor binding**
   - PX4 MAVLink message binding
   - ArduPilot motor/servo output binding
   - PWM/CAN ESC transport stub
2. **binding health 강화**
   - watchdog에 driver-side diagnostics 추가
   - heartbeat 외 timeout/fault taxonomy 분리
3. **운영 계층 강화**
   - `Nexus` executive brief 확대
   - adapter fault와 mission blocker 연결
4. **하드웨어 검증 루프**
   - bench HIL/SIL
   - FCU SITL
   - transport replay / audit trace

즉 이 저장소는 "바로 실기 송신기"가 아니라, **실기 제품층으로 자라기 위한 안정된 경계면**이다.

---

## Nexus와의 관계

DRA는 Nexus의 제어기가 아니다. Nexus는 상위 orchestration이고,
DRA는 드론 runtime 상태를 읽기 좋은 외부 신호로만 요약한다.

→ [`docs/NEXUS_CONSUMPTION.md`](docs/NEXUS_CONSUMPTION.md)

---

## 어떤 문서를 먼저 읽어야 하나

- 전체 구조와 철학: [`README.md`](README.md)
- 제어 코어 상세: [`Drone_Control_Foundation/README.md`](Drone_Control_Foundation/README.md)
- PX4/ArduPilot 필드 매핑: [`docs/PX4_ARDUPILOT_MAPPING.md`](docs/PX4_ARDUPILOT_MAPPING.md)
- Nexus 소비 방향: [`docs/NEXUS_CONSUMPTION.md`](docs/NEXUS_CONSUMPTION.md)

실무적으로는 루트 README가 개요이고, 실제 제품층 판단은 `docs/` 두 문서와 DCF README를 함께 보는 것이 가장 정확하다.

---

## Watchdog 상태

| 상태 | 조건 | 의미 |
|------|------|------|
| healthy | `link_alive=True`, 하트비트 신선 | 바인딩 정상 |
| stale | `heartbeat_age_s > stale_after_s` | 하트비트 지연 |
| degraded | `driver_fault=True` 또는 `link_alive=False` | transport 이상 |

---

## 무결성

```bash
python3 scripts/verify_signature.py    # 검증
python3 scripts/regenerate_signature.py # 재생성 (릴리스 시)
```

| 파일 | 역할 |
|------|------|
| [`SIGNATURE.sha256`](SIGNATURE.sha256) | 전 파일 SHA-256 매니페스트 |
| [`BLOCKCHAIN_INFO.md`](BLOCKCHAIN_INFO.md) | 무결성 체계 설명 |
| [`PHAM_BLOCKCHAIN_LOG.md`](PHAM_BLOCKCHAIN_LOG.md) | 릴리스 연속 기록 |

---

## 확장 방향

1. PX4 / ArduPilot 실 MAVLink transport stub 고도화
2. PWM / CAN ESC envelope 추가
3. watchdog: heartbeat jitter / reconnect 상태 추가
4. Nexus executive brief 포맷 확장
5. private repo에서 실제 벤더 SDK 바인딩 구현

**원칙:** 확장은 항상 DRA 위에서만. DCF 내부를 건드리지 않는다.
