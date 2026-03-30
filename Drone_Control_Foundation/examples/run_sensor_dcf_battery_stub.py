from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(__file__)
_PACKAGE_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
for _path in (
    _PACKAGE_ROOT,
    os.path.abspath(os.path.join(_THIS_DIR, "..", "..", "Battery_Dynamics_Engine")),
):
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)

from drone_control_foundation import (
    DroneBatteryBridgeConfig,
    DronePlatformSpec,
    DroneSetpoint,
    GeofenceConfig,
    StubDroneDriver,
    advance_battery_from_mixer,
    build_drone_actuator_intent,
    drone_state_from_snapshot,
    patch_drone_state_soc,
    run_control_tick,
)


def main() -> None:
    state = drone_state_from_snapshot(
        {
            "timestamp": 0.0,
            "pose": {"north_m": 0.0, "east_m": 0.0, "altitude_m_above_home": 6.0},
            "velocity": {"north_mps": 0.1, "east_mps": 0.0, "climb_rate_mps": 0.0},
            "attitude": {"roll_rad": 0.01, "pitch_rad": -0.02, "heading_rad": 0.2},
            "battery": {"soc": 0.82},
        }
    )
    setpoint = DroneSetpoint(
        mode="altitude_hold",
        altitude_m_above_home_target=8.0,
        yaw_rad_target=0.2,
    )
    spec = DronePlatformSpec(mass_kg=4.0, max_total_thrust_n=95.0)
    tick = run_control_tick(state, setpoint, spec, GeofenceConfig(), 0.02)

    try:
        from battery_dynamics import BatteryState, NMC_EV
    except Exception:
        battery_info = "battery_dynamics unavailable"
        next_state = tick.state
    else:
        battery = BatteryState(soc=state.battery_soc_0_1, v_rc=0.0, temp_k=298.15)
        battery_bridge = advance_battery_from_mixer(
            battery,
            NMC_EV,
            tick.mixer,
            spec,
            0.02,
            DroneBatteryBridgeConfig(),
        )
        next_state = patch_drone_state_soc(tick.state, battery_bridge)
        battery_info = (
            f"soc={battery_bridge.soc_0_1:.4f}, "
            f"current_a={battery_bridge.estimated_current_a:.2f}, "
            f"terminal_v={battery_bridge.terminal_voltage_v:.2f}"
        )

    driver = StubDroneDriver()
    actuator_intent = build_drone_actuator_intent(
        tick.mixer,
        mission_pause=tick.arbitration.mission_pause,
        estop_recommended=tick.arbitration.disarm_recommended,
    )
    log = driver.apply_intent(actuator_intent)

    print("mode=", setpoint.mode)
    print("altitude_target=", setpoint.altitude_m_above_home_target)
    print("collective=", round(log.collective_thrust_0_1, 4))
    print("motors=", tuple(round(x, 4) for x in log.motor_thrust_0_1))
    print("mission_pause=", log.mission_paused)
    print("battery=", battery_info)
    print("next_soc=", round(next_state.battery_soc_0_1, 4))


if __name__ == "__main__":
    main()
