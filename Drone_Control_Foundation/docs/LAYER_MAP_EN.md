# Drone control — layer map (extensible)

> **English.** Korean (정본): [LAYER_MAP.md](LAYER_MAP.md)

## 1. Layers inside this package

| Layer | Module | Role |
|-------|--------|------|
| Contracts | `contracts.py` | `DroneState` (NED), `DroneSetpoint`, `DronePlatformSpec`, `GeofenceConfig`, `MixerIntent` |
| Safety | `arbiter.py` | Battery, geofence, tilt → `ControlArbitration` (similar role to Cooking `ArbiterVerdict`) |
| Mixer | `mixer.py` | `quad_x_mix`, normalized motor 0..1 |
| Control loop | `control_tick.py` | `run_control_tick` — reference PID + mixer |
| Plant | `reference_plant.py` | **Replaceable** simplified dynamics |
| Surface | `surface.py` | JSON tick for L4 / embedded gateways |

## 2. Neighbour 00_BRAIN / staging engines

| Engine | Relationship |
|--------|----------------|
| [Morphing_Flight_Foundation](../Morphing_Flight_Foundation/README_EN.md) | Morph-mode lift/drag budgets — can **feed** extended `DronePlatformSpec` |
| [Transformable_Air_Mobility_Stack](../Transformable_Air_Mobility_Stack/README_EN.md) | Platform mode FSM — **upstream mission** maps to `DroneSetpoint.mode` / arbiter policy |
| [Vehicle_Platform_Foundation](../Vehicle_Platform_Foundation/README_EN.md) | Ground / 4WD — keep **taxi** separate from airborne tick |
| Defense `aerial_autonomy` | Point-mass style sim — **high-fidelity sim** reference without hard dependency |
| [Cooking_Process_Foundation](../Cooking_Process_Foundation/README_EN.md) | Pattern reference: tick payload, HAL intent, arbiter |

## 3. Extension checklist

1. **Estimator**: adapter fills `DroneState` from EKF (outside this package).
2. **Mission**: waypoint FSM emits `DroneSetpoint`.
3. **FCU**: map `MixerIntent.motor_thrust_0_1` → PWM / `actuator_controls`.
4. **Simulation**: replace `integrate_vertical_yaw_reference`.

*v0.1 — reference loop; airframe tuning is integrator work.*

## 4. Audit notes (v0.1.1)

- `armed_hover` / `altitude_hold` share the **same** reference path; FCU mode mapping belongs in adapters.
- No `SIGNATURE.sha256` / blockchain bundle (unlike COOKing).
- Checklist: [README_EN.md](../README_EN.md) — *Maintenance checklist*.
