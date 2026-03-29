from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(__file__)
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from drone_robot_adapter import (
    build_nexus_drone_signal,
    render_nexus_drone_lines,
)
from drone_robot_adapter.watchdog import BindingWatchdog


def main() -> None:
    watchdog = BindingWatchdog(stale_after_s=1.0)
    watchdog.mark_heartbeat(10.0, transport="px4_actuator_controls")
    snap = watchdog.snapshot(10.4)
    signal = build_nexus_drone_signal(
        mission_pause=False,
        estop_recommended=False,
        binding_health=snap,
        collective_0_1=0.61,
    )
    for line in render_nexus_drone_lines(signal):
        print(line)


if __name__ == "__main__":
    main()
