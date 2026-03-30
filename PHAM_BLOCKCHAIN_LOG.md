# PHAM_BLOCKCHAIN_LOG

## 0.1.6

- **DCF→DRA 통합 파이프라인 완성**: 두 레이어가 actuator intent 계약 경계로 연결되어 전 구간 동작 검증 완료.
  - `examples/run_dcf_dra_integration.py`: altitude_hold → PX4, 지오펜스 이탈 → ArduPilot, watchdog → Nexus signal 3시나리오.
  - `tests/test_dcf_dra_integration.py`: 24개 통합 테스트 전 PASS.
- README 전면 개정: 아키텍처 흐름, 계약 경계, 통합 예제, 두 레이어 역할 명확화.
- `SIGNATURE.sha256` 재생성 — 릴리스 무결성 최신화.
- 변경 파일 해시: `examples/run_dcf_dra_integration.py`, `tests/test_dcf_dra_integration.py`, `tests/conftest.py`, `VERSION`, `pyproject.toml`, `CHANGELOG.md`, `README.md`, `drone_robot_adapter/__init__.py`.

## 0.1.5

- `Drone_Control_Foundation/` **커밋·푸시 포함**(이전 README만 수정하고 트리 미추적이던 문제 종료).
- 루트 README: **golden_Snitch** = 합본 정본 명시.

## 0.1.4

- `git` 원격 복구: **`origin` = `qquartsco-svg/golden_Snitch`** (DCF URL로 잡혀 있던 사고 방지 문서화).

## 0.1.3

- README 링크 복구(상대 경로 + GitHub 쌍), `SIGNATURE.sha256` 재생성.

## 0.1.1

- 공개 정본 마감.
- README 상세화.
- 무결성 매니페스트 및 검증 스크립트 도입.
- 공개 원격 저장소는 **`qquartsco-svg/golden_Snitch`** 이다. (`Drone_Robot_Adapter` 로컬 클론의 `origin` 이 실수로 `Drone_Control_Foundation` 을 가리키면 푸시가 전부 엉킨다 — `git remote set-url origin https://github.com/qquartsco-svg/golden_Snitch.git`.)
