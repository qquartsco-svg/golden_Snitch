from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "SIGNATURE.sha256"
SKIP_NAMES = {
    "SIGNATURE.sha256",
    ".DS_Store",
}
SKIP_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
}


def iter_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if path.name in SKIP_NAMES:
            continue
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    lines = []
    for path in iter_files():
        rel = path.relative_to(ROOT).as_posix()
        lines.append(f"{sha256_file(path)}  {rel}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(lines)} files)")


if __name__ == "__main__":
    main()
