# Changelog

## 0.1.4

- **중요:** 로컬 `git` 원격 `origin` 이 실수로 `Drone_Control_Foundation` 을 가리키면 어댑터 커밋이 DCF로 푸시되어 GitHub에 반영되지 않는다. 공개 저장소는 **`qquartsco-svg/golden_Snitch`** — `git remote set-url origin https://github.com/qquartsco-svg/golden_Snitch.git`.
- README / PHAM: 위 정본 반영.

## 0.1.3

- README: 로컬 절대 경로(`/Users/...`) 제거 → 저장소 상대 링크 + GitHub 공개 쌍(`Drone_Control_Foundation` · `Drone_Robot_Adapter`) 안내.
- `PHAM_BLOCKCHAIN_LOG`: 공개 원격을 **`qquartsco-svg/Drone_Robot_Adapter`** 로 명시(과거 `golden_Snitch` 오연결 복구 안내).
- 로컬 `git` 권장: `origin` = `https://github.com/qquartsco-svg/Drone_Robot_Adapter.git` (제어 코어와 저장소 분리).

## 0.1.2

- README 보강:
  - actuator intent 계약 필드 표
  - watchdog 건강도 기준
  - 활용성 / 확장 방향
  - 정본 문서 위치 강조
- 문서 기준으로 `Drone_Robot_Adapter`의 정체성을 더 명확화:
  - DCF 밖의 제품형 HAL 경계
  - Nexus는 소비자/보고 계층
  - 실제 MAVLink/PWM/CAN 바인딩은 후속 제품층

## 0.1.1

- README를 공개 레포 수준으로 상세화: 아키텍처, 역할 경계, 공개 API, 벤더 바인딩 위치, Nexus 소비 방향, 무결성 절차 정리.
- 무결성 번들 추가:
  - `BLOCKCHAIN_INFO.md`
  - `PHAM_BLOCKCHAIN_LOG.md`
  - `SIGNATURE.sha256`
  - `scripts/regenerate_signature.py`
  - `scripts/verify_signature.py`
  - `scripts/release_check.py`
- release hygiene:
  - `.gitignore`
  - `scripts/cleanup_generated.py`
- 버전 정렬:
  - `VERSION`
  - `pyproject.toml`
  - `drone_robot_adapter.__version__`

## 0.1.0

- 초기 `Drone_Robot_Adapter` 스캐폴드.
- `PX4CommandEnvelope`, `ArduPilotCommandEnvelope`.
- `build_px4_command_envelope()`, `build_ardupilot_command_envelope()`.
- `DroneAdapterNexusSignal`, `build_nexus_drone_signal()`.
- `BindingWatchdog`.
