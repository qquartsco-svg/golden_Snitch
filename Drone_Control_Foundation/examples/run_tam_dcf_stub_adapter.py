from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(__file__)
_PACKAGE_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_TAM_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "Transformable_Air_Mobility_Stack"))
for _path in (_PACKAGE_ROOT, _TAM_ROOT):
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)

from drone_control_foundation import (
    DroneState,
    StubDroneDriver,
    build_drone_actuator_intent,
    run_control_tick,
)
from transformable_air_mobility import dcf_tick_bundle_from_tam


class _Body:
    total_mass_kg = 12.0


class _Ground:
    wheel_speed_ms = 0.0
    brake_hold = True


class _Propulsor:
    total_thrust_max_n = 220.0
    thrust_armed = True


def main() -> None:
    state = DroneState(pd_m=-8.0, battery_soc_0_1=0.92)
    bundle = dcf_tick_bundle_from_tam(
        tam_mode="HOVER",
        body=_Body(),
        ground=_Ground(),
        propulsor=_Propulsor(),
        drone_state=state,
        target_altitude_m_above_home=10.0,
    )
    tick = run_control_tick(state, bundle.setpoint, bundle.platform_spec, bundle.geofence, 0.02)
    driver = StubDroneDriver()
    actuator_intent = build_drone_actuator_intent(
        tick.mixer,
        mission_pause=tick.arbitration.mission_pause,
        estop_recommended=tick.arbitration.disarm_recommended,
    )
    log = driver.apply_intent(actuator_intent)
    print("tam_mode=", bundle.diagnostics["tam_mode"])
    print("drone_mode=", bundle.drone_mode)
    print("collective=", round(log.collective_thrust_0_1, 4))
    print("motors=", tuple(round(x, 4) for x in log.motor_thrust_0_1))
    print("paused=", log.mission_paused)


if __name__ == "__main__":
    main()
