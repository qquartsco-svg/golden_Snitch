"""
Drone_Control_Foundation — Ω 건강도 옵저버 (Robot_Adapter_Core 확장)

RAC의 safety/motion/flow 3축 공통 베이스 위에 drone 전용 4축을 extra_axes로 주입:
  power       : 배터리 SOC 건강 (임계·저전압 감지)
  navigation  : 지오펜스·속도 제한 준수 상태
  authority   : 토크 권한 여백 (arb.torque_scale 기반)
  motor_sat   : 모터 포화(飽和) 비율 (운용 마진 측정)

최종 omega_total = weighted(safety + motion + flow + power + nav + authority + motor_sat)
verdict:
  >= 0.75 → "healthy"
  >= 0.45 → "degraded"
  <  0.45 → "critical"
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .contracts import DronePlatformSpec, DroneState
from .robot_adapter import DroneTickLog

_RAC_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "Robot_Adapter_Core")
if os.path.isdir(_RAC_PATH) and _RAC_PATH not in sys.path:
    sys.path.insert(0, _RAC_PATH)

from robot_adapter_core.health import observe_base_health, BaseHealthReport  # type: ignore


@dataclass
class DroneHealthReport:
    """
    Ω 건강도 보고서 — Drone_Control_Foundation 전용.

    base_report: RAC 공통 3축(safety/motion/flow) + omega_total + verdict
    extra_axes : drone 전용 4축 점수 dict (power/navigation/authority/motor_sat)
    omega_total: 7축 가중 합산 최종값
    verdict    : "healthy" | "degraded" | "critical"
    notes      : 경보 문자열 목록
    """

    base_report: BaseHealthReport
    extra_axes: Dict[str, float]
    omega_total: float
    verdict: str
    tick_count: int
    notes: List[str] = field(default_factory=list)

    def __str__(self) -> str:
        axes = " | ".join(f"{k}={v:.3f}" for k, v in sorted(self.extra_axes.items()))
        base = (
            f"safety={self.base_report.omega_safety:.3f} "
            f"motion={self.base_report.omega_motion:.3f} "
            f"flow={self.base_report.omega_flow:.3f}"
        )
        return (
            f"[DroneHealth] Ω={self.omega_total:.3f} verdict={self.verdict} "
            f"ticks={self.tick_count} | {base} | {axes}"
        )


# ─── 스코어 계산 헬퍼 ──────────────────────────────────────────────────────────

def _score_power(logs: Sequence[DroneTickLog], spec: Optional[DronePlatformSpec]) -> tuple[float, str]:
    """배터리 SOC 기반 동력 건강도 (0→1)."""
    if not logs:
        return 0.0, "no_data"
    latest_soc = None
    for log in reversed(logs):
        raw = log.raw_intent
        if isinstance(raw, dict) and "battery_soc_0_1" in raw:
            latest_soc = float(raw["battery_soc_0_1"])
            break
    if latest_soc is None:
        # DroneTickLog의 domain_extra에서 SOC 추출 시도
        for log in reversed(logs):
            soc = log.domain_extra.get("battery_soc_0_1") or log.domain_extra.get("soc")
            if soc is not None:
                latest_soc = float(soc)
                break
    if latest_soc is None:
        return 1.0, "soc_unknown"

    crit = getattr(spec, "critical_battery_soc", 0.10) if spec else 0.10
    low = getattr(spec, "low_battery_soc", 0.18) if spec else 0.18

    if latest_soc <= crit:
        return 0.0, f"soc_critical={latest_soc:.2f}"
    if latest_soc <= low:
        score = (latest_soc - crit) / max(low - crit, 1e-6) * 0.4
        return score, f"soc_low={latest_soc:.2f}"
    score = 0.4 + (latest_soc - low) / max(1.0 - low, 1e-6) * 0.6
    return min(1.0, score), "soc_ok"


def _score_navigation(logs: Sequence[DroneTickLog]) -> tuple[float, str]:
    """지오펜스·속도제한 위반 비율 기반 항법 건강도."""
    if not logs:
        return 0.0, "no_data"
    pause_count = sum(1 for l in logs if l.mission_paused)
    pause_rate = pause_count / len(logs)
    # 위반이 없으면 1.0, 전부 위반이면 0.2 (항법이 붕괴해도 최소 점수는 남김)
    score = max(0.2, 1.0 - 0.8 * pause_rate)
    note = f"pause_rate={pause_rate:.2f}"
    return score, note


def _score_authority(logs: Sequence[DroneTickLog]) -> tuple[float, str]:
    """토크 권한 여백 — yaw_torque 절대값 평균이 낮을수록 여유 있음."""
    if not logs:
        return 0.0, "no_data"
    avg_yaw_cmd = sum(abs(l.yaw_torque_cmd_0_1) for l in logs) / len(logs)
    avg_roll_cmd = sum(abs(l.roll_torque_cmd_0_1) for l in logs) / len(logs)
    avg_pitch_cmd = sum(abs(l.pitch_torque_cmd_0_1) for l in logs) / len(logs)
    cmd_load = (avg_roll_cmd + avg_pitch_cmd + 0.5 * avg_yaw_cmd) / 2.5
    score = max(0.0, 1.0 - cmd_load)
    return score, f"cmd_load={cmd_load:.3f}"


def _score_motor_saturation(logs: Sequence[DroneTickLog]) -> tuple[float, str]:
    """모터 포화 비율 — any motor ≥ 0.97 인 틱 비율을 패널티로."""
    if not logs:
        return 0.0, "no_data"
    sat_count = sum(1 for l in logs if any(m >= 0.97 for m in l.motor_thrust_0_1))
    sat_rate = sat_count / len(logs)
    score = max(0.0, 1.0 - 1.5 * sat_rate)  # 포화가 잦으면 크게 감점
    return score, f"sat_rate={sat_rate:.2f}"


# ─── 공개 API ────────────────────────────────────────────────────────────────

def observe_drone_health(
    logs: Sequence[DroneTickLog],
    *,
    spec: Optional[DronePlatformSpec] = None,
    healthy_threshold: float = 0.75,
    degraded_threshold: float = 0.45,
) -> DroneHealthReport:
    """
    DroneTickLog 시퀀스에서 Ω 건강도 보고서를 생성한다.

    RAC 베이스(safety/motion/flow) 가중치 합계 = 0.50
    Drone 전용 4축 가중치 합계 = 0.50:
      power      = 0.20
      navigation = 0.15
      authority  = 0.10
      motor_sat  = 0.05
    """
    power_score, power_note = _score_power(logs, spec)
    nav_score, nav_note = _score_navigation(logs)
    auth_score, auth_note = _score_authority(logs)
    msat_score, msat_note = _score_motor_saturation(logs)

    extra_axes = {
        "power": power_score,
        "navigation": nav_score,
        "authority": auth_score,
        "motor_sat": msat_score,
    }
    extra_weights = {
        "power": 0.20,
        "navigation": 0.15,
        "authority": 0.10,
        "motor_sat": 0.05,
    }
    base_weights = {
        "safety": 0.25,
        "motion": 0.15,
        "flow": 0.10,
    }

    base = observe_base_health(
        logs,
        domain_tag="drone",
        extra_axes=extra_axes,
        extra_weights=extra_weights,
        base_weights=base_weights,
        healthy_threshold=healthy_threshold,
        degraded_threshold=degraded_threshold,
    )

    # 최종 omega는 RAC가 이미 7축 합산해서 반환
    notes: List[str] = list(base.notes)
    for note in [power_note, nav_note, auth_note, msat_note]:
        if note and "ok" not in note and "unknown" not in note:
            notes.append(note)

    return DroneHealthReport(
        base_report=base,
        extra_axes=extra_axes,
        omega_total=base.omega_total,
        verdict=base.verdict,
        tick_count=len(logs),
        notes=notes,
    )
