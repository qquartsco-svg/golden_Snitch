from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    removed = []
    for path in ROOT.rglob("__pycache__"):
        if path.is_dir():
            shutil.rmtree(path)
            removed.append(path.relative_to(ROOT).as_posix())
    for name in (".pytest_cache", ".DS_Store"):
        for path in ROOT.rglob(name):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
            removed.append(path.relative_to(ROOT).as_posix())
    for item in removed:
        print(f"removed {item}")
    if not removed:
        print("nothing to clean")


if __name__ == "__main__":
    main()
