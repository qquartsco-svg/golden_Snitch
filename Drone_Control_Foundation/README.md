# Drone_Control_Foundation

> **한국어 (정본).** English: [README_EN.md](README_EN.md)

> 지금 보는 경로가 **`golden_Snitch` 클론의 `Drone_Control_Foundation/`** 이면, 제어+HAL 이 **같은 저장소**에 있다.

**정본 번들:** 제어(DCF) + HAL(**Drone_Robot_Adapter**)은 저장소 **[golden_Snitch](https://github.com/qquartsco-svg/golden_Snitch)** 에 함께 올린다. 이 레포는 분리 클론·CI용일 수 있음.

**00_BRAIN** 스테이징 — **멀티콥터 제어의 확장형 골격**: 상태·세트포인트 계약, 안전 아비터, 쿼드-X 믹서 출력(`MixerIntent`), 단순 참조 플랜트, JSON 틱 표면.

## 무엇을 하지 않는가

- 실제 FCU(PX4/ArduPilot) 바인딩, RC 프로토콜, RTK, 캘리브레이션 UI.
- 인증·항공법 준수(통합사 책임).

## 무엇을 하는가

- **한 틱 파이프라인**: 아비터 → (고도·요·수평 프록시) → `quad_x_mix` → `integrate_vertical_yaw_reference`.
- **안전 보수 (v0.1.2)**: 지오펜스 이탈은 즉시 모터 차단이 아니라 `mission_pause + torque_scale`로 처리해 호버/복구 권한을 남김.
- **참조 플랜트 보수 (v0.1.2)**: 수평 가속이 `yaw`를 반영해 `position_hold` 참조 시뮬레이션과 프레임 일치.
- **센서 브리지 (v0.1.2)**: `drone_state_from_snapshot()` / `drone_state_from_sensory_stimulus()` 로 `Sensory_Input_Kernel` 류 snapshot·context를 `DroneState`로 정규화.
- **로봇 어댑터 스텁 (v0.1.2)**: `build_drone_actuator_intent()` / `StubDroneDriver` 로 `MixerIntent` 를 HAL actuator intent / tick log 경계로 내린다.
- **비행 물리 브리지 (v0.1.3)**: `patch_spec_from_morphing_assessment()` 로 morphing thrust budget과 `hover_margin_hint`를, `patch_spec_from_air_jordan()` 으로 대기 밀도·중력을 `DronePlatformSpec` 에 반영한다.
- **통합 예제 (v0.1.3)**: `run_sensor_dcf_battery_stub.py` 로 `Sensory -> DCF -> Battery -> HAL stub` 흐름을 한 번에 점검할 수 있다.
- **HAL**: `MixerIntent` (`drone_mixer_intent.v0.1`) — 모터 0..1 + 토크 명령 진단 필드.
- **교체 지점**: `reference_plant.py`를 6-DOF/로터 CFD 어댑터로 바꿔도 계약은 유지.

## 빠른 사용

```python
from drone_control_foundation import (
    DroneState, DroneSetpoint, DronePlatformSpec, GeofenceConfig,
    run_control_tick,
)

st = DroneState(pd_m=-5.0, battery_soc_0_1=1.0)
sp = DroneSetpoint(mode="altitude_hold", altitude_m_above_home_target=8.0)
res = run_control_tick(st, sp, DronePlatformSpec(), GeofenceConfig(), 0.02)
```

JSON 호스트: `surface.run_drone_tick` / `validate_drone_tick_payload`.

센서 입력 브리지:

```python
from drone_control_foundation import drone_state_from_snapshot

state = drone_state_from_snapshot(
    {
        "pose": {"north_m": 4.0, "east_m": -2.0, "altitude_m_above_home": 15.0},
        "velocity": {"north_mps": 1.2, "east_mps": -0.4, "climb_rate_mps": 0.8},
        "attitude": {"roll_rad": 0.1, "pitch_rad": -0.05, "heading_rad": 1.57},
        "battery": {"soc": 0.76},
    }
)
```

어댑터 스텁:

```python
from drone_control_foundation import StubDroneDriver, build_drone_actuator_intent

driver = StubDroneDriver()
actuator_intent = build_drone_actuator_intent(res.mixer, mission_pause=res.arbitration.mission_pause)
tick_log = driver.apply_intent(actuator_intent)
```

비행 물리 브리지:

```python
from drone_control_foundation import patch_spec_from_air_jordan

spec = patch_spec_from_air_jordan(DronePlatformSpec(), altitude_m_above_home=1500.0)
```

센서→제어→배터리→HAL 스텁 예제:

```bash
python3 examples/run_sensor_dcf_battery_stub.py
```

## 레이어 맵 (인접 엔진)

[docs/LAYER_MAP.md](docs/LAYER_MAP.md)
[docs/DYNAMICS_INTEGRATION_MAP.md](docs/DYNAMICS_INTEGRATION_MAP.md)
[docs/VENDOR_BINDING_SLOTS.md](docs/VENDOR_BINDING_SLOTS.md)
[golden_Snitch (Drone_Robot_Adapter)](https://github.com/qquartsco-svg/golden_Snitch)

## 비행 모드 (`DroneSetpoint.mode`) — v0.1 참조 루프

| 모드 | 참조 `run_control_tick` 동작 |
|------|-------------------------------|
| `disarmed` | 추력 차단, `diagnostics["idle"]`, 아비터도 `allow_thrust=False`. |
| `armed_hover` | (예약명) `altitude_hold` 와 **동일 경로** — 고도 목표 + 요 추종. |
| `altitude_hold` | 고도·요·수직 감쇠; 수평 위치는 `reference_plant` 만으로 천천히 이동. |
| `position_hold` | N/E 목표가 있을 때 소각도 롤·피치 명령으로 **수평 오차 감소** 시도. |

제품 FCU 모드와 1:1 대응은 **아님**; 계약·틱 형태만 맞추고 매핑은 어댑터에서 확장한다.

## 점검 체크리스트 (유지보수)

- **버전 삼중고**: `VERSION` · `pyproject.toml` `[project].version` · `drone_control_foundation.__version__` 일치.  
- **테스트**: 패키지 루트에서 `python3 -m pytest tests/ -q` → **29 passed** (현재).  
- **스테이징 일괄**: `_staging/scripts/verify_staging_stacks.sh` 에 본 패키지 포함 여부.  
- **HAL**: `MixerIntent.schema_version` = `drone_mixer_intent.v0.1` — JSON 스키마 파일은 아직 없음(필요 시 `schemas/` 추가).

## 버전

`0.1.5` — HAL 저장소 링크를 `golden_Snitch` 로 정정.

## 테스트

저장소 루트에서:

```bash
python3 -m pytest tests/ -q   # 기대: 29 passed
```

선택 예제(환경에 TAM 등이 있을 때):

```bash
python3 examples/run_tam_dcf_stub_adapter.py
python3 examples/run_sensor_dcf_battery_stub.py
python3 examples/run_sensory_tam_dcf_chain.py
```

00_BRAIN 모노레포 안에서는 `cd _staging/Drone_Control_Foundation` 후 동일.

## 변경 이력

[CHANGELOG.md](CHANGELOG.md)
