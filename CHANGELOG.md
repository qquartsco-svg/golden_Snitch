# Changelog

## 0.1.6

- **DCF→DRA 통합 파이프라인 완성**: `examples/run_dcf_dra_integration.py` — DroneState → DCF 틱 → actuator intent → PX4/ArduPilot/Nexus 3시나리오 완전 동작.
- **통합 테스트 24개 추가**: `tests/test_dcf_dra_integration.py` — §1 계약 경계, §2 PX4, §3 ArduPilot, §4 지오펜스→mission_pause 전파, §5 Nexus/Watchdog, §6 disarmed 전구간 검증.
- `tests/conftest.py`: Robot_Adapter_Core 경로 자동 주입으로 통합 환경 완전 지원.
- SIGNATURE.sha256 재생성 (0.1.6 릴리스 무결성 반영).
- README 전면 개정: 두 레이어 통합 아키텍처, 계약 경계, 통합 예제 실행 방법 명시.

## 0.1.5

- **golden_Snitch = DCF + Drone_Robot_Adapter**: `Drone_Control_Foundation/` 트리를 **Git에 포함**해 한 저장소로 푸시 (이전엔 로컬만 있고 커밋 안 된 상태였음).
- 루트 README 를 **`# golden_Snitch`** 정본으로 재정리; 별도 레포 안내 제거.
- `.gitignore`: DCF 하위 `pytest` 캐시 제외.

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
