# Drone_Control_Foundation

> **English.** Korean (정본): [README.md](README.md)

**Public GitHub pair:** [Drone_Control_Foundation](https://github.com/qquartsco-svg/Drone_Control_Foundation) · HAL adapter package lives in **[golden_Snitch](https://github.com/qquartsco-svg/golden_Snitch)** (same codebase as folder `Drone_Robot_Adapter`).

**00_BRAIN** staging — **extensible multicopter control skeleton**: state/setpoint contracts, safety arbitration, quad-X mixer output (`MixerIntent`), lightweight reference plant, JSON tick surface.

## Non-goals

- Real FCU bindings (PX4/ArduPilot), RC protocols, RTK, calibration UX.
- Certification / aviation compliance (integrator responsibility).

## What it does

- **One-tick pipeline**: arbiter → (altitude / yaw / coarse position) → `quad_x_mix` → `integrate_vertical_yaw_reference`.
- **Safety (v0.1.2+)**: geofence exit uses recoverable `mission_pause + torque_scale` (not immediate motor cut); soft speed gates; low `hover_margin_hint` handling.
- **Reference plant (v0.1.2+)**: horizontal acceleration respects `yaw` for coherent `position_hold`.
- **Sensor bridge (v0.1.2+)**: `drone_state_from_snapshot()` / `drone_state_from_sensory_stimulus()` normalize snapshots into `DroneState`.
- **Robot adapter stub (v0.1.2+)**: `build_drone_actuator_intent()` / `StubDroneDriver` — `MixerIntent` → HAL actuator intent / tick log.
- **Flight bridges (v0.1.3+)**: `patch_spec_from_morphing_assessment()`, `patch_spec_from_air_jordan()` patch `DronePlatformSpec`.
- **Integration examples**: `examples/run_sensor_dcf_battery_stub.py`, TAM/DCF stubs where dependencies exist.
- **HAL**: `MixerIntent` (`drone_mixer_intent.v0.1`) — per-motor 0..1 thrust plus torque diagnostic scalars.
- **Swap point**: replace `reference_plant.py` with a 6-DOF / rotor-resolved adapter without breaking contracts.

## Quick use

```python
from drone_control_foundation import (
    DroneState, DroneSetpoint, DronePlatformSpec, GeofenceConfig,
    run_control_tick,
)

st = DroneState(pd_m=-5.0, battery_soc_0_1=1.0)
sp = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=8.0)
res = run_control_tick(st, sp, DronePlatformSpec(), GeofenceConfig(), 0.02)
```

JSON hosts: `surface.run_drone_tick` / `validate_drone_tick_payload`.

## Layer map (neighbour engines)

[docs/LAYER_MAP_EN.md](docs/LAYER_MAP_EN.md)  
[docs/DYNAMICS_INTEGRATION_MAP.md](docs/DYNAMICS_INTEGRATION_MAP.md)  
[docs/VENDOR_BINDING_SLOTS.md](docs/VENDOR_BINDING_SLOTS.md)  
[golden_Snitch (Drone_Robot_Adapter)](https://github.com/qquartsco-svg/golden_Snitch)

## Flight modes (`DroneSetpoint.mode`) — v0.1 reference loop

| Mode | `run_control_tick` behaviour |
|------|------------------------------|
| `disarmed` | Thrust blocked, `diagnostics["idle"]`, arbiter `allow_thrust=False`. |
| `armed_hover` | **Same path as** `altitude_hold` (reserved name) — altitude + yaw. |
| `altitude_hold` | Altitude + yaw + vertical damping; horizontal drift via `reference_plant` only. |
| `position_hold` | When N/E targets set, small roll/pitch commands to **reduce horizontal error**. |

Not a 1:1 map to product FCU modes; extend mapping in adapters.

## Maintenance checklist

- **Version triplet**: `VERSION` · `pyproject.toml` `[project].version` · `drone_control_foundation.__version__` match (currently **0.1.5**).
- **Tests**: from package root, `python3 -m pytest tests/ -q` → **29 passed** (current).
- **Staging batch**: `_staging/scripts/verify_staging_stacks.sh` includes this stack (monorepo).
- **HAL**: `MixerIntent.schema_version` = `drone_mixer_intent.v0.1` — no JSON schema file yet (add `schemas/` if needed).

## Version

`0.1.5` — HAL repo links point to `golden_Snitch` (actual GitHub name).

## Tests

From repository root:

```bash
python3 -m pytest tests/ -q   # expect: 29 passed
```

Optional examples (when TAM etc. are installed):

```bash
python3 examples/run_tam_dcf_stub_adapter.py
python3 examples/run_sensor_dcf_battery_stub.py
python3 examples/run_sensory_tam_dcf_chain.py
```

Inside the 00_BRAIN monorepo: `cd _staging/Drone_Control_Foundation` then the same commands.

## Changelog

[CHANGELOG.md](CHANGELOG.md)
