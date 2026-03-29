from __future__ import annotations

from dataclasses import dataclass

from .contracts import VendorBindingHealthSnapshot


@dataclass
class BindingWatchdog:
    stale_after_s: float = 1.0
    last_heartbeat_s: float = 0.0
    last_transport: str = ""
    driver_fault: bool = False
    link_alive: bool = True

    def mark_heartbeat(self, timestamp_s: float, *, transport: str = "") -> None:
        self.last_heartbeat_s = max(0.0, float(timestamp_s))
        if transport:
            self.last_transport = transport
        self.link_alive = True

    def mark_fault(self, *, transport: str = "") -> None:
        self.driver_fault = True
        if transport:
            self.last_transport = transport
        self.link_alive = False

    def clear_fault(self) -> None:
        self.driver_fault = False

    def snapshot(self, now_s: float) -> VendorBindingHealthSnapshot:
        age = max(0.0, float(now_s) - self.last_heartbeat_s)
        alive = self.link_alive and age <= self.stale_after_s and not self.driver_fault
        return VendorBindingHealthSnapshot(
            link_alive=alive,
            heartbeat_age_s=age,
            driver_fault=self.driver_fault,
            last_transport=self.last_transport,
        )
