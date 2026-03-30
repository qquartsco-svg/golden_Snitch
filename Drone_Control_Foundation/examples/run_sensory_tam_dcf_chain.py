from __future__ import annotations

import os
import sys

_THIS_DIR = os.path.dirname(__file__)
_DCF_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
_STAGING_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
for _path in (
    _DCF_ROOT,
    os.path.join(_STAGING_ROOT, "Transformable_Air_Mobility_Stack"),
    os.path.join(_STAGING_ROOT, "Battery_Dynamics_Engine"),
):
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)

from drone_control_foundation import (
    DroneBatteryBridgeConfig,
    StubDroneDriver,
    advance_battery_from_mixer,
    build_drone_actuator_intent,
    drone_state_from_snapshot,
    patch_drone_state_soc,
    run_control_tick,
)
from transformable_air_mobility import GroundDriveState, PlatformBodyState, PropulsorState
from transformable_air_mobility.adapters.drone_control_adapter import dcf_tick_bundle_from_tam


def main() -> None:
    sensory_snapshot = {
        "timestamp": 0.0,
        "pose": {"north_m": 0.0, "east_m": 0.0, "altitude_m_above_home": 6.0},
        "velocity": {"north_mps": 0.0, "east_mps": 0.0, "climb_rate_mps": 0.0},
        "attitude": {"roll_rad": 0.01, "pitch_rad": -0.02, "heading_rad": 0.15},
        "battery": {"soc": 0.84},
    }
    drone_state = drone_state_from_snapshot(sensory_snapshot)

    body = PlatformBodyState(total_mass_kg=12.0, human_onboard=False)
    ground = GroundDriveState(forward_speed_ms=0.0, brake_hold=True, wheel_speed_ms=0.0)
    prop = PropulsorState(
        total_thrust_max_n=220.0,
        thrust_armed=True,
        battery_energy_wh=520.0,
        hover_power_w=420.0,
    )
    bundle = dcf_tick_bundle_from_tam(
        tam_mode="HOVER",
        body=body,
        ground=ground,
        propulsor=prop,
        drone_state=drone_state,
        target_altitude_m_above_home=8.0,
    )
    tick = run_control_tick(drone_state, bundle.setpoint, bundle.platform_spec, bundle.geofence, 0.02)

    try:
        from battery_dynamics import BatteryState, NMC_EV
    except Exception:
        battery_line = "battery_dynamics unavailable"
        patched_state = tick.state
    else:
        battery_state = BatteryState(soc=drone_state.battery_soc_0_1, v_rc=0.0, temp_k=298.15)
        battery_bridge = advance_battery_from_mixer(
            battery_state,
            NMC_EV,
            tick.mixer,
            bundle.platform_spec,
            0.02,
            DroneBatteryBridgeConfig(),
        )
        patched_state = patch_drone_state_soc(tick.state, battery_bridge)
        battery_line = (
            f"soc={battery_bridge.soc_0_1:.4f}, "
            f"current_a={battery_bridge.estimated_current_a:.2f}, "
            f"terminal_v={battery_bridge.terminal_voltage_v:.2f}"
        )

    driver = StubDroneDriver()
    log = driver.apply_intent(
        build_drone_actuator_intent(
            tick.mixer,
            mission_pause=tick.arbitration.mission_pause,
            estop_recommended=tick.arbitration.disarm_recommended,
        )
    )

    print("tam_mode=", bundle.diagnostics["tam_mode"])
    print("drone_mode=", bundle.drone_mode)
    print("target_altitude=", bundle.setpoint.altitude_m_above_home_target)
    print("hover_margin=", bundle.diagnostics.get("hover_margin"))
    print("air_density_kg_m3=", bundle.diagnostics.get("air_density_kg_m3"))
    print("gravity_mps2=", bundle.diagnostics.get("gravity_mps2"))
    print("collective=", round(log.collective_thrust_0_1, 4))
    print("motors=", tuple(round(x, 4) for x in log.motor_thrust_0_1))
    print("mission_pause=", log.mission_paused)
    print("battery=", battery_line)
    print("next_soc=", round(patched_state.battery_soc_0_1, 4))


if __name__ == "__main__":
    main()
