from __future__ import annotations

from typing import Iterable

from .contracts import DroneAdapterNexusSignal, VendorBindingHealthSnapshot


def build_nexus_drone_signal(
    *,
    mission_pause: bool,
    estop_recommended: bool,
    binding_health: VendorBindingHealthSnapshot,
    collective_0_1: float,
) -> DroneAdapterNexusSignal:
    omega = max(0.0, min(1.0, 1.0 - 0.45 * float(estop_recommended) - 0.25 * float(mission_pause)))
    if not binding_health.link_alive or binding_health.driver_fault:
        omega = min(omega, 0.35)
    flags = {
        "mission_pause": bool(mission_pause),
        "estop_recommended": bool(estop_recommended),
        "vendor_link_ok": bool(binding_health.link_alive and not binding_health.driver_fault),
        "heartbeat_stale": bool(binding_health.heartbeat_age_s > 1.0),
    }
    notes = [
        f"transport={binding_health.last_transport or 'unknown'}",
        f"collective={collective_0_1:.3f}",
    ]
    if binding_health.heartbeat_age_s > 1.0:
        notes.append(f"heartbeat_age_s={binding_health.heartbeat_age_s:.2f}")
    return DroneAdapterNexusSignal(
        omega_control=omega,
        mission_pause=bool(mission_pause),
        estop_recommended=bool(estop_recommended),
        vendor_link_ok=flags["vendor_link_ok"],
        binding_transport=binding_health.last_transport or "unknown",
        flags=flags,
        notes=tuple(notes),
    )


def render_nexus_drone_lines(signal: DroneAdapterNexusSignal) -> tuple[str, ...]:
    lines = [
        f"drone_control Ω={signal.omega_control:.3f} | transport={signal.binding_transport}",
        f"pause={signal.mission_pause} | estop={signal.estop_recommended} | vendor_link_ok={signal.vendor_link_ok}",
    ]
    if signal.notes:
        lines.append("notes: " + " | ".join(signal.notes[:3]))
    return tuple(lines)
