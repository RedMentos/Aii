"""Fail-closed RAM admission for concurrent mobile MoE benchmark runs.

The gate uses process VmHWM from completed single-body taps plus current
MemAvailable. It is a benchmark guard, not a model-memory predictor or a
production Runtime permission system.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable


def _read_kib_value(line: str, key: str) -> float | None:
    parts = line.split()
    if len(parts) < 3 or parts[0].rstrip(":") != key:
        return None
    try:
        value = float(parts[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0 or parts[2].lower() not in ("kb", "kib"):
        return None
    return value


def read_memavailable_mib(meminfo_path: str | Path = "/proc/meminfo") -> float | None:
    """Return Linux/Termux MemAvailable in MiB; None means unmeasured."""
    try:
        lines = Path(meminfo_path).read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError):
        return None
    for line in lines:
        if line.startswith("MemAvailable:"):
            value_kib = _read_kib_value(line, "MemAvailable")
            return None if value_kib is None else value_kib / 1024.0
    return None


def read_vmhwm_mib(pid: int, proc_root: str | Path = "/proc") -> float | None:
    """Read a process high-water RSS in MiB; inaccessible is never reported as 0."""
    try:
        lines = (Path(proc_root) / str(int(pid)) / "status").read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeError, ValueError):
        return None
    for line in lines:
        if line.startswith("VmHWM:"):
            value_kib = _read_kib_value(line, "VmHWM")
            return None if value_kib is None else value_kib / 1024.0
    return None


def pair_memory_admission(
    single_peak_rss_mib: Iterable[float | int | None],
    available_mib: float | int | None,
    reserve_mib: float | int = 512,
) -> dict:
    """Admit a concurrent pair only with measured peaks and measured headroom.

    Summing single-run VmHWM is deliberately conservative: the pair path is
    optional and can be skipped; a missing measurement must not become 0 MiB.
    """
    if not isinstance(reserve_mib, (int, float)) or not math.isfinite(float(reserve_mib)) or reserve_mib < 0:
        raise ValueError("reserve_mib must be a finite non-negative number")

    peaks = list(single_peak_rss_mib)
    if len(peaks) < 2:
        return {
            "status": "BLOCKED_NEEDS_TWO_MEASURED_BODIES",
            "reason": "pair mode requires at least two single-body measurements",
            "single_peak_rss_mib": peaks,
            "available_mib": available_mib,
            "reserve_mib": float(reserve_mib),
            "required_mib": None,
        }

    normalized: list[float] = []
    for peak in peaks:
        if not isinstance(peak, (int, float)) or not math.isfinite(float(peak)) or peak <= 0:
            return {
                "status": "BLOCKED_UNMEASURED_SINGLE_RUN_PEAK",
                "reason": "every body needs a positive measured VmHWM; missing is not zero",
                "single_peak_rss_mib": peaks,
                "available_mib": available_mib,
                "reserve_mib": float(reserve_mib),
                "required_mib": None,
            }
        normalized.append(float(peak))

    if not isinstance(available_mib, (int, float)) or not math.isfinite(float(available_mib)) or available_mib <= 0:
        return {
            "status": "BLOCKED_MEMAVAILABLE_UNAVAILABLE",
            "reason": "current MemAvailable could not be measured",
            "single_peak_rss_mib": normalized,
            "available_mib": available_mib,
            "reserve_mib": float(reserve_mib),
            "required_mib": None,
        }

    required = sum(normalized) + float(reserve_mib)
    available = float(available_mib)
    return {
        "status": "ADMITTED" if available >= required else "BLOCKED_INSUFFICIENT_MEMORY",
        "reason": "measured single-run peaks plus reserve fit current MemAvailable"
        if available >= required else "measured peaks plus reserve exceed current MemAvailable",
        "single_peak_rss_mib": normalized,
        "available_mib": available,
        "reserve_mib": float(reserve_mib),
        "required_mib": required,
        "headroom_after_required_mib": available - required,
    }
