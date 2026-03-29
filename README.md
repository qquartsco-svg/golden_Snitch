# Drone_Robot_Adapter

> **한국어 (정본).**
> **v0.1.1** · Python 3.9+ · 의존: `Robot_Adapter_Core`, `Drone_Control_Foundation`

이 패키지는 [Drone_Control_Foundation](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Control_Foundation/README.md)이 내보내는
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

## Nexus와의 관계

이 패키지는 `Nexus`를 제어기로 보지 않는다.
`Nexus`는 상위 orchestration이고, 여기서는 **drone runtime 상태를 읽기 좋은 외부 신호로 요약**만 한다.

상세 연결 방향은
[NEXUS_CONSUMPTION.md](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Robot_Adapter/docs/NEXUS_CONSUMPTION.md)
를 따른다.

벤더 envelope 매핑 표:
[PX4_ARDUPILOT_MAPPING.md](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Robot_Adapter/docs/PX4_ARDUPILOT_MAPPING.md)

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

## 무결성

- [BLOCKCHAIN_INFO.md](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Robot_Adapter/BLOCKCHAIN_INFO.md)
- [PHAM_BLOCKCHAIN_LOG.md](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Robot_Adapter/PHAM_BLOCKCHAIN_LOG.md)
- [SIGNATURE.sha256](/Users/jazzin/Desktop/00_BRAIN/_staging/Drone_Robot_Adapter/SIGNATURE.sha256)

검증:

```bash
python3 scripts/verify_signature.py
```

릴리스 점검:

```bash
python3 scripts/release_check.py
```

---

## 테스트

```bash
cd _staging/Drone_Robot_Adapter
python3 -m pytest tests/ -q
python3 examples/run_nexus_drone_brief.py
```

---

## 버전

`0.1.1` — 공개 README 상세화, 무결성 번들, release scripts, watchdog/Nexus 데모 마감.
