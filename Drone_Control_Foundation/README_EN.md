# Drone_Control_Foundation

> **English.** Korean (정본): [README.md](README.md)

**00_BRAIN** staging — **extensible multicopter control skeleton**: state/setpoint contracts, safety arbitration, quad-X mixer output (`MixerIntent`), lightweight reference plant, JSON tick surface.

## Non-goals

- Real FCU bindings (PX4/ArduPilot), RC protocols, RTK, calibration UX.
- Certification / aviation compliance (integrator responsibility).

## What it does

- **One-tick pipeline**: arbiter → (altitude / yaw / coarse position) → `quad_x_mix` → `integrate_vertical_yaw_reference`.
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

## Flight modes (`DroneSetpoint.mode`) — v0.1 reference loop

| Mode | `run_control_tick` behaviour |
|------|------------------------------|
| `disarmed` | Thrust blocked, `diagnostics["idle"]`, arbiter `allow_thrust=False`. |
| `armed_hover` | **Same path as** `altitude_hold` (reserved name) — altitude + yaw. |
| `altitude_hold` | Altitude + yaw + vertical damping; horizontal drift via `reference_plant` only. |
| `position_hold` | When N/E targets set, small roll/pitch commands to **reduce horizontal error**. |

Not a 1:1 map to product FCU modes; extend mapping in adapters.

## Maintenance checklist

- **Version triplet**: `VERSION` · `pyproject.toml` `[project].version` · `drone_control_foundation.__version__` match.
- **Tests**: from package root, `python3 -m pytest tests/ -q` → **7 passed** (current).
- **Staging batch**: `_staging/scripts/verify_staging_stacks.sh` includes this stack.
- **HAL**: `MixerIntent.schema_version` = `drone_mixer_intent.v0.1` — no JSON schema file yet (add `schemas/` if needed).

## Version

`0.1.1` — aligned with `VERSION`, `pyproject.toml`, `drone_control_foundation.__version__`.

## Tests

```bash
cd _staging/Drone_Control_Foundation   # from 00_BRAIN monorepo root
python3 -m pytest tests/ -q            # expect: 7 passed
```

## Changelog

[CHANGELOG.md](CHANGELOG.md)
