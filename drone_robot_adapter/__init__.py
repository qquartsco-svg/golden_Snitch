"""Drone_Robot_Adapter — vendor HAL scaffold for DCF actuator intents."""

from .contracts import (
    ArduPilotCommandEnvelope,
    DroneAdapterNexusSignal,
    PX4CommandEnvelope,
    VendorBindingHealthSnapshot,
)
from .ardupilot_bridge import build_ardupilot_command_envelope
from .nexus_bridge import build_nexus_drone_signal, render_nexus_drone_lines
from .px4_bridge import build_px4_command_envelope
from .watchdog import BindingWatchdog
from .health_bridge import dcf_omega_or_fallback, omega_verdict

__all__ = [
    "ArduPilotCommandEnvelope",
    "DroneAdapterNexusSignal",
    "PX4CommandEnvelope",
    "VendorBindingHealthSnapshot",
    "BindingWatchdog",
    "build_ardupilot_command_envelope",
    "build_nexus_drone_signal",
    "build_px4_command_envelope",
    "render_nexus_drone_lines",
    "dcf_omega_or_fallback",
    "omega_verdict",
]

__version__ = "0.2.0"
