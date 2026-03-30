from __future__ import annotations

import os
import sys
from dataclasses import replace
from typing import Any, Dict

from .contracts import DronePlatformSpec

_AIR_JORDAN_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Air_Jordan")
if os.path.isdir(_AIR_JORDAN_PATH) and _AIR_JORDAN_PATH not in sys.path:
    sys.path.insert(0, _AIR_JORDAN_PATH)

_MFF_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Morphing_Flight_Foundation")
if os.path.isdir(_MFF_PATH) and _MFF_PATH not in sys.path:
    sys.path.insert(0, _MFF_PATH)


def _import_air_jordan():
    try:
        from Air_Jordan import isa

        return isa
    except Exception:
        try:
            from flight_engine import isa

            return isa
        except Exception:
            return None


def air_jordan_atmosphere_for_altitude(altitude_m_above_home: float) -> Dict[str, float]:
    isa = _import_air_jordan()
    if isa is None:
        raise ImportError("Air_Jordan is not available")
    atm = isa(max(0.0, float(altitude_m_above_home)))
    return {
        "altitude_m": float(atm.altitude_m),
        "air_density_kg_m3": float(atm.rho_kgm3),
        "gravity_mps2": float(atm.gravity_ms2),
        "temperature_k": float(atm.T_K),
        "pressure_pa": float(atm.P_Pa),
    }


def patch_spec_from_air_jordan(
    spec: DronePlatformSpec,
    *,
    altitude_m_above_home: float,
) -> DronePlatformSpec:
    atm = air_jordan_atmosphere_for_altitude(altitude_m_above_home)
    return replace(
        spec,
        gravity_mps2=atm["gravity_mps2"],
        air_density_kg_m3=atm["air_density_kg_m3"],
    )


def patch_spec_from_morphing_assessment(
    spec: DronePlatformSpec,
    assessment: Any,
) -> DronePlatformSpec:
    """
    Pull mass and thrust budget from Morphing_Flight_Foundation assessment.

    The DCF side still remains multicopter-centric; we only import the common
    denominator that can be safely consumed here.
    """

    return replace(
        spec,
        mass_kg=max(0.1, float(getattr(assessment, "mass_kg", spec.mass_kg))),
        max_total_thrust_n=max(1e-6, float(getattr(assessment, "lift_thrust_available_n", spec.max_total_thrust_n))),
        hover_margin_hint=float(getattr(assessment, "hover_margin", spec.hover_margin_hint)),
    )
