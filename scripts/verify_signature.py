from __future__ import annotations

import hashlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "SIGNATURE.sha256"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not MANIFEST.exists():
        print("missing SIGNATURE.sha256")
        return 1

    ok = 0
    bad = 0
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        path = ROOT / rel
        if not path.exists():
            print(f"MISSING {rel}")
            bad += 1
            continue
        actual = sha256_file(path)
        if actual != digest:
            print(f"BAD {rel}")
            bad += 1
            continue
        ok += 1

    if bad:
        print(f"FAILED ({ok} ok, {bad} bad)")
        return 1
    print(f"OK ({ok} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
