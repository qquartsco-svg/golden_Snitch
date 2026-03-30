from __future__ import annotations

import math

from .contracts import DronePlatformSpec, DroneState, MixerIntent
from .mixer import total_thrust_n


def integrate_vertical_yaw_reference(
    state: DroneState,
    mixer: MixerIntent,
    spec: DronePlatformSpec,
    dt_s: float,
) -> DroneState:
    """
    Replaceable reference plant: dominant vertical NED dynamics + light horizontal damping.

    Swap this module for a full rigid-body / rotor adapter without changing contracts.
    """
    dt = max(0.0, float(dt_s))
    T = total_thrust_n(mixer.motor_thrust_0_1, spec)
    m = max(spec.mass_kg, 1e-6)
    phi, th, psi = state.roll_rad, state.pitch_rad, state.yaw_rad

    ad = spec.gravity_mps2 - (T / m) * math.cos(phi) * math.cos(th)
    vd = state.vd_mps + ad * dt
    pd = state.pd_m + vd * dt

    cphi = math.cos(phi)
    sphi = math.sin(phi)
    sth = math.sin(th)
    cpsi = math.cos(psi)
    spsi = math.sin(psi)
    an = (T / m) * (cphi * sth * cpsi + sphi * spsi)
    ae = (T / m) * (cphi * sth * spsi - sphi * cpsi)
    vn = state.vn_mps + an * dt
    ve = state.ve_mps + ae * dt
    pn = state.pn_m + vn * dt
    pe = state.pe_m + ve * dt

    rho_ratio = max(0.05, min(3.0, spec.air_density_kg_m3 / 1.225))
    damp = math.exp(-max(0.0, spec.horizontal_drag_coeff_1ps) * rho_ratio * dt)
    vn *= damp
    ve *= damp

    return DroneState(
        time_s=state.time_s,
        pn_m=pn,
        pe_m=pe,
        pd_m=pd,
        vn_mps=vn,
        ve_mps=ve,
        vd_mps=vd,
        roll_rad=state.roll_rad,
        pitch_rad=state.pitch_rad,
        yaw_rad=state.yaw_rad,
        p_rps=state.p_rps,
        q_rps=state.q_rps,
        r_rps=state.r_rps,
        battery_soc_0_1=state.battery_soc_0_1,
    )
