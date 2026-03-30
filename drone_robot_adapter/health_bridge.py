"""
golden_Snitch — DCF Ω 건강도 브리지

Drone_Control_Foundation v0.2.0의 observe_drone_health()를 golden_Snitch
넥서스 신호(DroneAdapterNexusSignal.omega_control)에 연결한다.

DCF가 설치되어 있으면 7축 가중 Ω를 사용하고,
없으면 nexus_bridge 기본 로직(estop/pause/link 기반)으로 폴백한다.

사용 예:
    from drone_robot_adapter.health_bridge import dcf_omega_or_fallback

    omega = dcf_omega_or_fallback(
        tick_logs=driver.tick_logs,
        mission_pause=arb.mission_pause,
        estop_recommended=arb.disarm_recommended,
        binding_health=watchdog.snapshot(now),
    )
"""
from __future__ import annotations

import os
import sys
from typing import Optional, Sequence, Any

from .contracts import VendorBindingHealthSnapshot

_DCF_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Drone_Control_Foundation")
if os.path.isdir(_DCF_PATH) and _DCF_PATH not in sys.path:
    sys.path.insert(0, _DCF_PATH)


def _try_dcf_health(tick_logs: Sequence[Any]) -> Optional[float]:
    """DCF observe_drone_health() 호출 시도. 실패 시 None 반환."""
    try:
        from drone_control_foundation.health import observe_drone_health
        report = observe_drone_health(tick_logs)
        return float(report.omega_total)
    except Exception:
        return None


def _fallback_omega(
    *,
    mission_pause: bool,
    estop_recommended: bool,
    binding_health: VendorBindingHealthSnapshot,
) -> float:
    """DCF 없을 때 사용하는 단순 Ω (nexus_bridge 기존 로직)."""
    omega = max(0.0, min(1.0,
        1.0
        - 0.45 * float(estop_recommended)
        - 0.25 * float(mission_pause)
    ))
    if not binding_health.link_alive or binding_health.driver_fault:
        omega = min(omega, 0.35)
    return omega


def dcf_omega_or_fallback(
    tick_logs: Sequence[Any],
    *,
    mission_pause: bool,
    estop_recommended: bool,
    binding_health: VendorBindingHealthSnapshot,
) -> float:
    """
    DCF DroneTickLog 시퀀스에서 Ω를 계산한다.

    - tick_logs가 있고 DCF가 설치된 경우: observe_drone_health() 7축 Ω
    - 그 외: estop/pause/link 기반 폴백 Ω

    vendor_link 이상은 항상 최종 omega에 cap을 걸어 반영한다.
    """
    if tick_logs:
        dcf_omega = _try_dcf_health(tick_logs)
        if dcf_omega is not None:
            omega = dcf_omega
            if not binding_health.link_alive or binding_health.driver_fault:
                omega = min(omega, 0.35)
            return max(0.0, min(1.0, omega))

    return _fallback_omega(
        mission_pause=mission_pause,
        estop_recommended=estop_recommended,
        binding_health=binding_health,
    )


def omega_verdict(omega: float) -> str:
    """Ω → 문자열 판정 (healthy / degraded / critical)."""
    if omega >= 0.75:
        return "healthy"
    if omega >= 0.45:
        return "degraded"
    return "critical"
