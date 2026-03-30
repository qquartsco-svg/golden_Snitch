from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DCF = ROOT / "Drone_Control_Foundation"
RAC = ROOT.parents[0] / "Robot_Adapter_Core"

for _p in [str(ROOT), str(DCF), str(RAC)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)
