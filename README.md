# Drone_Robot_Adapter

> **한국어 (정본).**
> **v0.1.4** · Python 3.9+ · 의존: `Robot_Adapter_Core`, `Drone_Control_Foundation`

**GitHub 공개 저장소:** 이 패키지 코드는 저장소 **[qquartsco-svg/golden_Snitch](https://github.com/qquartsco-svg/golden_Snitch)** 에 올린다. (로컬 폴더명 `Drone_Robot_Adapter` 와 다를 수 있음.)  
제어 코어(DCF)는 별도 저장소 [Drone_Control_Foundation](https://github.com/qquartsco-svg/Drone_Control_Foundation) — `git remote -v` 로 **어댑터 폴더의 `origin` 이 `golden_Snitch` 인지** 반드시 확인할 것. `Drone_Control_Foundation` 으로 잡혀 있으면 푸시가 꼬인다.

이 패키지는 [Drone_Control_Foundation](https://github.com/qquartsco-svg/Drone_Control_Foundation) 이보내는
`MixerIntent` / actuator intent를 **실제 벤더 FCU/ESC transport 계층**으로 연결하는
드론 도메인 HAL 제품층 스캐폴드다.

DCF 안에는 PX4, MAVLink, PWM, CAN, ArduPilot SDK를 넣지 않는다.
실제 하드웨어 바인딩은 **여기**에서만 붙인다.

---

## 한 줄 정의

`Drone_Robot_Adapter` 는 **제어 코어(DCF)와 실제 드론 FCU/ESC transport 사이의 유일한 권장 제품층 경계**다.

---

## 아키텍처 위치

```text
Drone_Control_Foundation
    -> MixerIntent / build_drone_actuator_intent()
    -> Drone_Robot_Adapter
        -> PX4 command envelope
        -> ArduPilot command envelope
        -> vendor watchdog / heartbeat
    -> vendor FCU / ESC / CAN / PWM
```

---

## 왜 별도 패키지인가

| 이유 | 설명 |
|------|------|
| 책임 분리 | `Drone_Control_Foundation` 는 제어 계산, 여기는 하드웨어/transport 표현 |
| 벤더 교체 | PX4, ArduPilot, PWM, CAN, 커스텀 FCU를 어댑터만 바꿔 교체 |
| 감사/추적 | actuator intent 계약과 실제 transport 바인딩을 분리 |
| 상위 orchestration | `Nexus`는 하위 제어를 직접 계산하지 않고, 이 층이 내는 외부 신호를 읽음 |

---

## 패키지 구조

```text
Drone_Robot_Adapter/
├── drone_robot_adapter/
│   ├── __init__.py
│   ├── contracts.py
│   ├── px4_bridge.py
│   ├── ardupilot_bridge.py
│   ├── nexus_bridge.py
│   └── watchdog.py
├── docs/
│   ├── NEXUS_CONSUMPTION.md
│   └── PX4_ARDUPILOT_MAPPING.md
├── scripts/
│   ├── regenerate_signature.py
│   ├── verify_signature.py
│   ├── cleanup_generated.py
│   └── release_check.py
└── tests/
    └── test_drone_robot_adapter.py
```

---

## 이 패키지가 하는 일

- DCF actuator intent를 벤더 transport envelope로 바꾼다.
- `mission_pause`, `estop`, `step_id`, `flow_id` 같은 운용 필드를 보존한다.
- 상위 orchestration(`Nexus`)가 읽을 수 있는 간단한 drone signal/brief를 만든다.

## 하지 않는 일

- 실제 MAVLink 연결
- 실제 PWM/CAN 전송
- 비행 제어 계산
- 센서 융합 / EKF

---

## 공개 API

- `PX4CommandEnvelope`
- `ArduPilotCommandEnvelope`
- `VendorBindingHealthSnapshot`
- `build_px4_command_envelope()`
- `build_ardupilot_command_envelope()`
- `DroneAdapterNexusSignal`
- `build_nexus_drone_signal()`
- `render_nexus_drone_lines()`
- `BindingWatchdog`

---

## actuator_intent 계약 필드

이 패키지가 읽는 입력은 항상 DCF가 만든 actuator intent다.

| 필드 | 구분 | 의미 |
|------|------|------|
| `schema_version` | 필수 | 현재 intent 계약 버전 |
| `primary_output_0_1` | 필수 | collective/thrust ceiling의 공통 1차 출력 |
| `motor_thrust_0_1` | 필수 | 4축 모터 정규화 추력 |
| `mission_pause` | 필수 | 상위 안전/운용 계층이 미션 정지를 요구하는지 |
| `estop_recommended` | 필수 | 즉시 안전 정지 권고 |
| `step_id` | 보존 | 현재 스텝/시퀀스 식별자 |
| `flow_id` | 보존 | 상위 플로우/세션 식별자 |
| `transport_hint` | 선택 | 하위 제품층이 참고할 transport 힌트 |

정리하면:
- **필수 필드**: 제어/안전 의미를 가진 공통 분모
- **보존 필드**: 운용 추적과 감사에 필요한 흐름 정보
- **선택 필드**: 실제 벤더 바인딩이 참고하는 제품층 힌트

상세 매핑은 [docs/PX4_ARDUPILOT_MAPPING.md](docs/PX4_ARDUPILOT_MAPPING.md) 를 기준으로 본다.

---

## Nexus와의 관계

이 패키지는 `Nexus`를 제어기로 보지 않는다.
`Nexus`는 상위 orchestration이고, 여기서는 **drone runtime 상태를 읽기 좋은 외부 신호로 요약**만 한다.

상세 연결 방향은 [docs/NEXUS_CONSUMPTION.md](docs/NEXUS_CONSUMPTION.md) 를 따른다.

벤더 envelope 매핑 표: [docs/PX4_ARDUPILOT_MAPPING.md](docs/PX4_ARDUPILOT_MAPPING.md)

---

## Watchdog 건강도 기준

`BindingWatchdog` 는 제어 품질을 평가하지 않고,
**벤더 바인딩의 생존성/연속성**만 본다.

권장 해석:

| 상태 | 기준 예시 | 의미 |
|------|-----------|------|
| `healthy` | `link_alive=True`, `driver_fault=False`, `heartbeat_age_s <= stale_after_s` | 바인딩 계층이 정상 응답 중 |
| `stale` | `heartbeat_age_s > stale_after_s` | 하트비트가 늦어져 상위가 주의해야 함 |
| `degraded` | `driver_fault=True` 또는 `link_alive=False` | transport 계층 이상, 상위 pause/estop 판단 필요 |

즉 watchdog은 “기체가 잘 날고 있는가”가 아니라
“**하드웨어 바인딩이 아직 살아 있는가**”를 본다.

---

## 빠른 사용

### DCF actuator intent -> PX4 envelope

```python
from drone_robot_adapter import build_px4_command_envelope

env = build_px4_command_envelope(
    {
        "schema_version": "drone_actuator_intent.v0.1",
        "primary_output_0_1": 0.62,
        "motor_thrust_0_1": (0.60, 0.61, 0.63, 0.64),
        "mission_pause": False,
        "estop_recommended": False,
        "step_id": "hover",
        "flow_id": "demo",
        "transport_hint": "pwm_normalized",
    }
)
print(env.transport)
```

### Watchdog -> Nexus signal

```python
from drone_robot_adapter import BindingWatchdog, build_nexus_drone_signal

watchdog = BindingWatchdog(stale_after_s=1.0)
watchdog.mark_heartbeat(10.0, transport="px4_actuator_controls")
snap = watchdog.snapshot(10.4)
signal = build_nexus_drone_signal(
    mission_pause=False,
    estop_recommended=False,
    binding_health=snap,
    collective_0_1=0.61,
)
```

### Nexus 데모

```bash
python3 examples/run_nexus_drone_brief.py
```

---

## 활용성

이 패키지는 다음 같은 경우에 바로 쓸 수 있다.

- DCF에서 계산된 intent를 PX4/ArduPilot 쪽 제품층 envelope로 넘길 때
- 시뮬레이터/하드웨어랩에서 `mission_pause`, `estop`, `flow_id` 같은 운용 필드를 보존하고 싶을 때
- `Nexus`가 드론 상태를 한 줄 briefing으로 읽어야 할 때
- 추후 private/vendor 패키지에서 실제 MAVLink/PWM/CAN 드라이버를 붙이기 전에 공통 경계를 고정하고 싶을 때

---

## 확장 방향

가장 자연스러운 다음 단계는 이 순서다.

1. `PX4` / `ArduPilot` 실 transport stub 고도화
2. `PWM` / `CAN ESC` envelope 추가
3. watchdog에 link timeout / heartbeat jitter / reconnect 상태 추가
4. `Nexus`에서 읽을 executive brief 포맷 확장
5. private repository에서 실제 벤더 SDK 바인딩 구현

중요한 점은, 이 확장은 **DCF 안이 아니라 이 패키지 위/안에서만** 진행돼야 한다는 것이다.

---

## 무결성

- [BLOCKCHAIN_INFO.md](BLOCKCHAIN_INFO.md)
- [PHAM_BLOCKCHAIN_LOG.md](PHAM_BLOCKCHAIN_LOG.md)
- [SIGNATURE.sha256](SIGNATURE.sha256)

검증:

```bash
python3 scripts/verify_signature.py
```

릴리스 점검:

```bash
python3 scripts/release_check.py
```

---

## 정본 문서

루트 README는 개요다. 실제 제품 판단에는 아래 두 문서를 우선 기준으로 읽는 것이 좋다.

- [docs/PX4_ARDUPILOT_MAPPING.md](docs/PX4_ARDUPILOT_MAPPING.md)
- [docs/NEXUS_CONSUMPTION.md](docs/NEXUS_CONSUMPTION.md)

---

## 테스트

저장소 루트(클론 디렉터리)에서:

```bash
python3 -m pytest tests/ -q
python3 examples/run_nexus_drone_brief.py
```

00_BRAIN 모노레포 안에서만 작업할 때는 `cd _staging/Drone_Robot_Adapter` 후 위와 동일.

---

## 버전

`0.1.4` — `origin` 을 실제 공개 저장소 `golden_Snitch` 로 고정, README·PHAM 정본.
