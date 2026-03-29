# BLOCKCHAIN_INFO

이 저장소에서 말하는 `blockchain`은 분산 합의형 네트워크가 아니라,
**릴리스 무결성과 변경 연속성**을 추적하기 위한 문서 패턴이다.

구성:

- `SIGNATURE.sha256`
  - 현재 릴리스에 포함되는 파일들의 SHA-256 매니페스트
- `PHAM_BLOCKCHAIN_LOG.md`
  - 사람이 읽는 릴리스 연속 기록
- `scripts/regenerate_signature.py`
  - 매니페스트 재생성
- `scripts/verify_signature.py`
  - 로컬/CI 검증

검증:

```bash
python3 scripts/verify_signature.py
```

재생성:

```bash
python3 scripts/regenerate_signature.py
python3 scripts/verify_signature.py
```
