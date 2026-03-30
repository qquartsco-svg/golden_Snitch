# golden_Snitch

**Repository:** [`qquartsco-svg/golden_Snitch`](https://github.com/qquartsco-svg/golden_Snitch)
**Version:** 0.1.7
**Composition:** `Drone_Control_Foundation` (control core) + `Drone_Robot_Adapter` (HAL)
**Korean canonical README:** [`README.md`](README.md)

> **One repository, two layers.**
> `golden_Snitch` separates control computation from hardware binding through a strict contract boundary.
> DCF decides **what the drone should do**.
> DRA decides **how that intent is expressed to vendor transports**.

---

## Core Idea

This repository is not a monolithic drone stack. It intentionally keeps two layers side by side:

1. **Drone_Control_Foundation (DCF)**
   - the control core that computes thrust and torque intent from state and setpoints
2. **Drone_Robot_Adapter (DRA)**
   - the product-facing HAL that translates that intent into PX4, ArduPilot, PWM, or CAN style envelopes

This separation matters because it:

- prevents vendor SDKs from contaminating the control core
- allows FCU transport swaps without rewriting control math
- preserves a clean audit trail between control intent and transport binding
- gives upper orchestration (`TAM`, `Nexus`) a stable boundary to consume

---

## Layer Layout

| Layer | Path | Responsibility |
|------|------|----------------|
| **Drone_Control_Foundation (DCF)** | [`Drone_Control_Foundation/`](Drone_Control_Foundation/README.md) | Control core: state, setpoints, safety arbiter, quad-X mixer, reference plant, health observer |
| **Drone_Robot_Adapter (DRA)** | `drone_robot_adapter/` | HAL: DCF actuator intent → PX4 / ArduPilot envelopes, watchdog, Nexus signal |

---

## Contract Boundary

DCF and DRA share exactly one recommended product boundary: the **actuator intent dict**.

| Field | Type | Meaning |
|------|------|---------|
| `schema_version` | required | contract version (`drone_actuator_intent.v0.1`) |
| `primary_output_0_1` | required | normalized collective / thrust output |
| `motor_thrust_0_1` | required | normalized 4-motor thrust tuple |
| `allow_motion` | required | whether physical motion is allowed |
| `mission_pause` | required | mission authority should pause |
| `estop_recommended` | required | emergency stop recommendation |
| `step_id` | preserved | step / sequence tracking id |
| `flow_id` | preserved | flow / session tracking id |
| `transport_hint` | optional | downstream transport hint |

DCF is responsible **up to this dict**.
DRA is responsible **from this dict downward**.

---

## Watchdog Health Semantics

| Status | Rule | Meaning |
|------|------|---------|
| `healthy` | heartbeat within `stale_after_s`, no driver fault | binding alive and fresh |
| `stale` | heartbeat age exceeded | link existed, but freshness is no longer guaranteed |
| `degraded` | driver fault or transport inconsistency | adapter is alive enough to report, but not healthy enough to trust |

These states are designed for orchestration and operations reporting, not for replacing low-level FCU safety logic.

---

## What This Repository Is Good For

- **Civil / research drone productization**
  - keep control math and vendor integration separated
- **Vendor portability**
  - switch from PX4 to ArduPilot without rewriting DCF
- **Simulation-to-product continuity**
  - DCF always emits the same contract, while DRA changes per transport
- **Upper-layer integration**
  - connect cleanly with `Transformable_Air_Mobility_Stack`, `Nexus`, battery/sensory/flight bridges
- **Auditability**
  - mission pause, estop recommendations, step ids, and flow ids remain visible across the pipeline

---

## Expansion Path

The current repository closes the loop around **control core + HAL contract + product scaffolding**.
The natural next steps are:

1. **real vendor binding**
   - PX4 MAVLink field binding
   - ArduPilot motor / servo binding
   - PWM / CAN ESC transport stubs
2. **binding health enrichment**
   - richer fault taxonomy
   - watchdog plus transport diagnostics
3. **ops-layer growth**
   - stronger Nexus executive briefs
   - adapter fault → mission blocker propagation
4. **hardware validation**
   - SIL / HIL
   - FCU SITL
   - transport replay / audit traces

So `golden_Snitch` should be read as a **stable product-facing boundary**, not as a finished FCU integration package.

---

## Recommended Reading Order

- architecture and role split: [`README.md`](README.md)
- control core details: [`Drone_Control_Foundation/README.md`](Drone_Control_Foundation/README.md)
- PX4 / ArduPilot field mapping: [`docs/PX4_ARDUPILOT_MAPPING.md`](docs/PX4_ARDUPILOT_MAPPING.md)
- Nexus consumption model: [`docs/NEXUS_CONSUMPTION.md`](docs/NEXUS_CONSUMPTION.md)

In practice, the root README is the overview, while the two `docs/` files plus the DCF README are the more operational references.
