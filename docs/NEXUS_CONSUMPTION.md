# Nexus Consumption

> **한국어 (정본)** — `Nexus` 같은 상위 orchestration이 드론 체인을 어떻게 읽어야 하는지 정리한 문서.

## 원칙

`Nexus`는 드론 제어기를 대체하지 않는다.

읽는 순서는 다음과 같다.

1. `Transformable_Air_Mobility_Stack`
   - 상위 mode / readiness / blockers
2. `Drone_Control_Foundation`
   - control arbitration / mixer / state tick
3. `Drone_Robot_Adapter`
   - vendor link / heartbeat / transport 상태

즉 `Nexus`는 **상태공간을 통합 보고**할 뿐, PID/믹서/FCU 제어를 직접 계산하지 않는다.

## 권장 Nexus 입력

- TAM:
  - `mode`
  - `takeoff_possible`
  - `blockers`
  - `evidence.flight_source`
  - `evidence.flight_recommendation`
- DCF:
  - `arbitration.mission_pause`
  - `arbitration.disarm_recommended`
  - `diagnostics.collective_0_1`
- Drone_Robot_Adapter:
  - `vendor_link_ok`
  - `binding_transport`
  - `heartbeat_age_s`

## 보고 예시

```text
TAM: THRUST_ARMED | blockers=hover_margin_low
DCF: mission_pause=False | disarm_recommended=False
Adapter: transport=px4_actuator_controls | vendor_link_ok=True
```

## 한 줄 원칙

TAM은 **비행 readiness**, DCF는 **제어 코어**, Drone_Robot_Adapter는 **제품형 HAL 바인딩**이다.  
`Nexus`는 이 셋을 묶어 읽되, 하위 제어 로직을 직접 침범하지 않는다.
