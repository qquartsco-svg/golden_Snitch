# PX4 / ArduPilot Mapping

> **한국어 (정본)** — `Drone_Robot_Adapter` 가 DCF actuator intent를 어떤 공통 분모로 벤더 envelope에 내리는지 정리한 표.

## 입력 원천

원천은 항상 DCF actuator intent다.

```text
build_drone_actuator_intent()
  -> schema_version
  -> primary_output_0_1
  -> motor_thrust_0_1[4]
  -> mission_pause
  -> estop_recommended
  -> step_id
  -> flow_id
  -> transport_hint
```

## PX4 envelope

| DCF intent 필드 | PX4CommandEnvelope |
|----------------|--------------------|
| `schema_version` | `schema_version` |
| `motor_thrust_0_1` | `actuator_controls_0_1` |
| `primary_output_0_1` | `thrust_sp_0_1` |
| `mission_pause` | `mission_pause` |
| `estop_recommended` | `estop_recommended` |
| `step_id` | `step_id` |
| `flow_id` | `flow_id` |
| `transport_hint` | `metadata["transport_hint"]` |

## ArduPilot envelope

| DCF intent 필드 | ArduPilotCommandEnvelope |
|----------------|---------------------------|
| `schema_version` | `schema_version` |
| `motor_thrust_0_1` | `motor_outputs_0_1` |
| `primary_output_0_1` | `collective_0_1` |
| `mission_pause` | `mission_pause` |
| `estop_recommended` | `estop_recommended` |
| `step_id` | `step_id` |
| `flow_id` | `flow_id` |
| `transport_hint` | `metadata["transport_hint"]` |

## 원칙

- 아직 실제 MAVLink 필드/메시지 id를 박지 않는다.
- 먼저 **제품층 envelope 계약**을 고정하고,
- 그 다음 비공개 혹은 하드웨어 특화 패키지에서 실제 SDK 필드 매핑을 붙인다.

## 한 줄 요약

DCF는 제어 계산까지,
`Drone_Robot_Adapter`는 벤더 envelope까지,
실제 PX4/ArduPilot SDK 바인딩은 그 다음 층이다.
