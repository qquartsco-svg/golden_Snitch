from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .arbiter import ControlArbitration
from .contracts import ControlGains, DronePlatformSpec, DroneSetpoint, DroneState, GeofenceConfig
from .control_tick import run_control_tick


def validate_drone_tick_payload(payload: Any) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if not isinstance(payload, dict):
        return False, ["payload must be a JSON object"]
    if isinstance(payload.get("dt_s"), bool) or not isinstance(payload.get("dt_s"), (int, float)):
        errs.append("dt_s must be a number")
    elif float(payload["dt_s"]) <= 0:
        errs.append("dt_s must be positive")
    st = payload.get("state")
    if not isinstance(st, dict):
        errs.append("state must be an object")
    sp = payload.get("setpoint")
    if not isinstance(sp, dict):
        errs.append("setpoint must be an object")
    return (len(errs) == 0, errs)


def _state_from_dict(d: Dict[str, Any]) -> DroneState:
    return DroneState(
        time_s=float(d.get("time_s") or 0.0),
        pn_m=float(d.get("pn_m") or 0.0),
        pe_m=float(d.get("pe_m") or 0.0),
        pd_m=float(d.get("pd_m") or 0.0),
        vn_mps=float(d.get("vn_mps") or 0.0),
        ve_mps=float(d.get("ve_mps") or 0.0),
        vd_mps=float(d.get("vd_mps") or 0.0),
        roll_rad=float(d.get("roll_rad") or 0.0),
        pitch_rad=float(d.get("pitch_rad") or 0.0),
        yaw_rad=float(d.get("yaw_rad") or 0.0),
        p_rps=float(d.get("p_rps") or 0.0),
        q_rps=float(d.get("q_rps") or 0.0),
        r_rps=float(d.get("r_rps") or 0.0),
        battery_soc_0_1=float(d.get("battery_soc_0_1") or 1.0),
    )


def _state_to_dict(s: DroneState) -> Dict[str, Any]:
    return {
        "time_s": s.time_s,
        "pn_m": s.pn_m,
        "pe_m": s.pe_m,
        "pd_m": s.pd_m,
        "vn_mps": s.vn_mps,
        "ve_mps": s.ve_mps,
        "vd_mps": s.vd_mps,
        "roll_rad": s.roll_rad,
        "pitch_rad": s.pitch_rad,
        "yaw_rad": s.yaw_rad,
        "p_rps": s.p_rps,
        "q_rps": s.q_rps,
        "r_rps": s.r_rps,
        "battery_soc_0_1": s.battery_soc_0_1,
    }


def _setpoint_from_dict(d: Dict[str, Any]) -> DroneSetpoint:
    mode = str(d.get("mode") or "disarmed")
    if mode not in ("disarmed", "armed_hover", "altitude_hold", "position_hold"):
        mode = "disarmed"
    pn_t = d.get("pn_m_target")
    pe_t = d.get("pe_m_target")
    return DroneSetpoint(
        mode=mode,  # type: ignore[arg-type]
        altitude_m_above_home_target=float(d.get("altitude_m_above_home_target") or 0.0),
        yaw_rad_target=float(d.get("yaw_rad_target") or 0.0),
        pn_m_target=float(pn_t) if pn_t is not None else None,
        pe_m_target=float(pe_t) if pe_t is not None else None,
    )


def _spec_from_dict(d: Dict[str, Any]) -> DronePlatformSpec:
    return DronePlatformSpec(
        mass_kg=float(d.get("mass_kg") or 1.5),
        gravity_mps2=float(d.get("gravity_mps2") or 9.80665),
        max_total_thrust_n=float(d.get("max_total_thrust_n") or 30.0),
        arm_m=float(d.get("arm_m") or 0.12),
        max_tilt_rad=float(d.get("max_tilt_rad") or 0.52),
        low_battery_soc=float(d.get("low_battery_soc") or 0.18),
        critical_battery_soc=float(d.get("critical_battery_soc") or 0.10),
    )


def _fence_from_dict(d: Dict[str, Any]) -> GeofenceConfig:
    return GeofenceConfig(
        enabled=bool(d.get("enabled", True)),
        max_horizontal_m=float(d.get("max_horizontal_m") or 80.0),
        min_altitude_m_above_home=float(d.get("min_altitude_m_above_home") or -5.0),
        max_altitude_m_above_home=float(d.get("max_altitude_m_above_home") or 120.0),
    )


def _arb_to_dict(a: ControlArbitration) -> Dict[str, Any]:
    return {
        "allow_thrust": a.allow_thrust,
        "torque_scale_0_1": a.torque_scale_0_1,
        "mission_pause": a.mission_pause,
        "disarm_recommended": a.disarm_recommended,
        "reasons": list(a.reasons),
    }


def run_drone_tick(payload: Dict[str, Any]) -> Dict[str, Any]:
    ok, errs = validate_drone_tick_payload(payload)
    if not ok:
        raise ValueError("; ".join(errs))
    dt = float(payload["dt_s"])
    state = _state_from_dict(payload["state"])
    setpoint = _setpoint_from_dict(payload["setpoint"])
    spec = _spec_from_dict(payload.get("platform_spec") or {})
    fence = _fence_from_dict(payload.get("geofence") or {})
    gains = None
    if isinstance(payload.get("gains"), dict):
        g = payload["gains"]
        gains = ControlGains(
            alt_kp=float(g.get("alt_kp", 0.12)),
            alt_kd=float(g.get("alt_kd", 0.35)),
            yaw_kp=float(g.get("yaw_kp", 1.6)),
            pos_kp=float(g.get("pos_kp", 0.08)),
            max_tilt_cmd_rad=float(g.get("max_tilt_cmd_rad", 0.22)),
        )
    res = run_control_tick(state, setpoint, spec, fence, dt, gains=gains)
    return {
        "state": _state_to_dict(res.state),
        "mixer_intent": {
            "schema_version": res.mixer.schema_version,
            "motor_thrust_0_1": list(res.mixer.motor_thrust_0_1),
            "collective_thrust_0_1": res.mixer.collective_thrust_0_1,
            "roll_torque_cmd_0_1": res.mixer.roll_torque_cmd_0_1,
            "pitch_torque_cmd_0_1": res.mixer.pitch_torque_cmd_0_1,
            "yaw_torque_cmd_0_1": res.mixer.yaw_torque_cmd_0_1,
        },
        "arbitration": _arb_to_dict(res.arbitration),
        "diagnostics": dict(res.diagnostics),
    }
