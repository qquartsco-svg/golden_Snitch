# Changelog

## 0.1.5

- README / docs: HAL 공개 저장소 링크를 실제 GitHub 이름 **`qquartsco-svg/golden_Snitch`** 로 수정 (존재하지 않는 `Drone_Robot_Adapter` 저장소 URL 제거).

## 0.1.4

- `drone_control_foundation.__version__` 를 `VERSION` · `pyproject.toml` 과 재정렬 (`0.2.0` 표기 오류 제거).
- README / `docs/DYNAMICS_INTEGRATION_MAP.md` / `docs/VENDOR_BINDING_SLOTS.md`: 로컬 머신 절대 경로 제거, GitHub 공개 쌍(`Drone_Control_Foundation` · `Drone_Robot_Adapter`) 링크 및 단독 클론용 테스트 안내.
- 영문 README 동기화(버전·테스트 수).

## 0.1.3

- `flight_bridges`: `patch_spec_from_morphing_assessment()` 가 `hover_margin_hint` 도 `DronePlatformSpec` 으로 전달.
- `arbiter`: 낮은 `hover_margin_hint` 에 대해 thrust를 보존한 recoverable `mission_pause + torque_scale` safety mode 추가.
- 예제 추가: `examples/run_sensor_dcf_battery_stub.py` — `Sensory -> DCF -> Battery -> StubDriver` end-to-end 스모크 경로.
- 테스트 확장: low hover margin safety, morphing hover margin patching.

## 0.1.2

- `reference_plant`: 수평 N/E 가속이 `yaw`를 반영하도록 보수해 `position_hold` 참조 시뮬레이션 프레임 일치.
- `control_tick`: roll/pitch 참조 필터 계수 보수 (`0.4 + 0.60`) 및 `p_rps`, `q_rps` propagation 추가.
- `arbiter`: 지오펜스 이탈을 즉시 thrust cut이 아닌 `mission_pause + torque_scale` recoverable mode로 변경.
- `arbiter`: `max_horizontal_speed_mps`, `max_vertical_speed_mps` soft speed gate 추가.
- 테스트 확장: geofence recoverable mode, yaw-aware position hold, speed soft gate, attitude/rate boundedness.

## 0.1.1

- README / LAYER_MAP: **점검 체크리스트**, `DroneFlightMode` 참조 루프 동작 표, 기대 `pytest` 출력(7 tests).
- 테스트: `disarmed` 틱 시 모터 0·`idle` 진단.

## 0.1.0

- Altitude PD: derivative uses **`+ kd * vd`** with `e = h_target - h` and `de/dt = vd` in NED (`h = -pd`).
- Initial **Drone_Control_Foundation**: `DroneState` / `DroneSetpoint` / `DronePlatformSpec`, `GeofenceConfig`.
- `ControlArbitration` (thrust allow, torque scale, pause, disarm recommendation).
- `quad_x_mix` + `MixerIntent` (`drone_mixer_intent.v0.1`).
- `run_control_tick` reference loop (altitude–yaw, simple vertical plant).
- `surface.run_drone_tick` / `validate_drone_tick_payload` for JSON hosts.
- Docs: `docs/LAYER_MAP.md` + EN — links to MFF, TAM, Defense aerial, VPF.
