# Changelog

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
