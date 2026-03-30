from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from .contracts import DroneState


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    return {}


def _pull_float(*sources: Mapping[str, Any], keys: tuple[str, ...], default: float | None = None) -> float | None:
    for source in sources:
        for key in keys:
            if key in source and source[key] is not None:
                return float(source[key])
    return default


def _context_from_stimulus(stimulus: Any) -> dict[str, Any]:
    context = getattr(stimulus, "context", None)
    return _coerce_mapping(context)


def _state_payload(snapshot: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    payload = _coerce_mapping(snapshot)
    nested = _coerce_mapping(payload.get("drone_state"))
    pose = _coerce_mapping(payload.get("pose"))
    velocity = _coerce_mapping(payload.get("velocity"))
    attitude = _coerce_mapping(payload.get("attitude"))
    rates = _coerce_mapping(payload.get("rates"))
    battery = _coerce_mapping(payload.get("battery"))
    return (
        payload | nested,
        pose | nested,
        velocity | nested,
        attitude | nested,
        rates | nested | attitude,
        battery | nested,
    )


def drone_state_from_snapshot(snapshot: Mapping[str, Any], *, base_state: DroneState | None = None) -> DroneState:
    """
    Build a ``DroneState`` from a generic sensor snapshot.

    The adapter stays permissive on purpose: it accepts a flat mapping or nested
    ``pose`` / ``velocity`` / ``attitude`` / ``rates`` / ``battery`` blocks.
    This keeps DCF decoupled from any single estimator or SDK schema.
    """

    state = DroneState(**asdict(base_state)) if base_state is not None else DroneState()
    payload, pose, velocity, attitude, rates, battery = _state_payload(snapshot)

    time_s = _pull_float(payload, keys=("time_s", "timestamp", "timestamp_s"), default=None)
    if time_s is not None:
        state.time_s = time_s

    pn = _pull_float(payload, pose, keys=("pn_m", "north_m", "n_m", "x_north_m"), default=None)
    pe = _pull_float(payload, pose, keys=("pe_m", "east_m", "e_m", "y_east_m"), default=None)
    pd = _pull_float(payload, pose, keys=("pd_m", "down_m", "d_m", "z_down_m"), default=None)
    alt = _pull_float(payload, pose, keys=("altitude_m_above_home", "altitude_m", "height_m"), default=None)

    if pn is not None:
        state.pn_m = pn
    if pe is not None:
        state.pe_m = pe
    if pd is not None:
        state.pd_m = pd
    elif alt is not None:
        state.pd_m = -alt

    vn = _pull_float(payload, velocity, keys=("vn_mps", "north_mps", "north_velocity_mps"), default=None)
    ve = _pull_float(payload, velocity, keys=("ve_mps", "east_mps", "east_velocity_mps"), default=None)
    vd = _pull_float(payload, velocity, keys=("vd_mps", "down_mps", "down_velocity_mps"), default=None)
    vz_up = _pull_float(payload, velocity, keys=("vz_up_mps", "vertical_speed_up_mps", "climb_rate_mps"), default=None)

    if vn is not None:
        state.vn_mps = vn
    if ve is not None:
        state.ve_mps = ve
    if vd is not None:
        state.vd_mps = vd
    elif vz_up is not None:
        state.vd_mps = -vz_up

    roll = _pull_float(payload, attitude, keys=("roll_rad", "roll"), default=None)
    pitch = _pull_float(payload, attitude, keys=("pitch_rad", "pitch"), default=None)
    yaw = _pull_float(payload, attitude, keys=("yaw_rad", "yaw", "heading_rad"), default=None)
    p = _pull_float(payload, rates, keys=("p_rps", "roll_rate_rps", "gx_rps"), default=None)
    q = _pull_float(payload, rates, keys=("q_rps", "pitch_rate_rps", "gy_rps"), default=None)
    r = _pull_float(payload, rates, keys=("r_rps", "yaw_rate_rps", "gz_rps"), default=None)

    if roll is not None:
        state.roll_rad = roll
    if pitch is not None:
        state.pitch_rad = pitch
    if yaw is not None:
        state.yaw_rad = yaw
    if p is not None:
        state.p_rps = p
    if q is not None:
        state.q_rps = q
    if r is not None:
        state.r_rps = r

    soc = _pull_float(payload, battery, keys=("battery_soc_0_1", "battery_soc", "soc"), default=None)
    if soc is not None:
        state.battery_soc_0_1 = max(0.0, min(1.0, soc))

    return state


def drone_state_from_sensory_stimulus(stimulus: Any, *, base_state: DroneState | None = None) -> DroneState:
    """
    Build a ``DroneState`` from a ``SensoryStimulus``-like object.

    The only hard requirement is a ``context`` mapping; if a timestamp exists on
    the stimulus itself and the context omits one, it is used as ``time_s``.
    """

    context = _context_from_stimulus(stimulus)
    if "time_s" not in context and "timestamp" not in context:
        timestamp = getattr(stimulus, "timestamp", None)
        if timestamp is not None:
            context["time_s"] = float(timestamp)
    return drone_state_from_snapshot(context, base_state=base_state)
