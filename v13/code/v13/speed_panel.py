"""V13 speed panel: per-organ observed evidence vs synthetic compiled fastlane.

This is not a model selection authority or an experimental promotion gate.
The diagnostics never feed their metrics back into training. Pure benchmark
runs only after explicit idle local operator command, in a disposable folder.
"""
from __future__ import annotations

import json
import math

ROLES = ("B1_DETAIL", "B2_GIST", "C2_CONTROL", "C3_LANGUAGE")
DISPLAY = {
    "B1_DETAIL": "Detail-Gehirnhälfte",
    "B2_GIST": "Überblick-Gehirnhälfte",
    "C2_CONTROL": "Leitstelle",
    "C3_LANGUAGE": "Sprachzentrum",
}
MAX_ROWS = 250
MAX_BENCH_ROWS = 50000


def _num(value, positive=False):
    if type(value) not in (int, float):
        return None
    try:
        result = float(value)
    except (ValueError, OverflowError):
        return None
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        return None
    return result


def _record(value):
    try:
        data = json.loads(value)
        return data if type(data) is dict else {}
    except (ValueError, TypeError):
        return {}


def observed_models(store, session):
    """Summarise current-session host telemetry without reading raw text.

    A row with just a model name is not evidence of native inference.
    Empty evidence remains UNKNOWN, never an invented measurement or zero.
    """
    if type(session) is not str or not session:
        raise ValueError("active session required for model speed")
    rows = store.rows(
        "SELECT t.kind,t.metrics FROM telemetry t JOIN events e "
        "ON e.id=t.event_id WHERE e.session_id=? "
        "ORDER BY t.id DESC LIMIT ?", (session, MAX_ROWS))
    samples = {role: [] for role in ROLES}
    for row in rows:
        metrics = _record(row.get("metrics"))
        role = metrics.get("role")
        if role not in samples:
            continue
        rate = _num(metrics.get("predicted_per_second"), positive=True)
        tokens = _num(metrics.get("predicted_n"))
        stream_s = _num(metrics.get("stream_s"), positive=True)
        if rate is None and tokens is not None and stream_s:
            rate = tokens / stream_s
        ttft = _num(metrics.get("ttft_s"))
        if ttft is None:
            ttft = _num(metrics.get("prefill_to_first_token_s"))
        if rate is None and ttft is None:
            continue
        samples[role].append({
            "rate": round(rate, 2) if rate is not None else None,
            "time_to_first_token_s": round(ttft, 4) if ttft is not None else None,
            "kind": str(row.get("kind", ""))[:60],
        })
    organs = []
    for role in ROLES:
        values = samples[role]
        first = values[0] if values else None
        organs.append({
            "role": role, "organ": DISPLAY[role],
            "status": "HOST_TELEMETRY_ONLY" if first else "NO_CURRENT_SESSION_MEASUREMENT",
            "samples": len(values),
            "latest_decoded_tokens_per_s": first["rate"] if first else None,
            "latest_ttft_s": first["time_to_first_token_s"] if first else None,
            # Even a plausible "kind" is not verifiable native provenance.
            "native_phone_verified": False,
        })
    return {
        "revision": "v13-speed-panel-v1",
        "kind": "READ_ONLY_PER_ORGAN_TELEMETRY",
        "scope": "CURRENT_SESSION",
        "organs": organs,
        "claim_limit": (
            "Sanitised host telemetry, not an independently verified pinned "
            "Redmi benchmark, model utility result or permission to change models."
        ),
        "model_calls": 0,
        "state_mutation": False,
    }


def benchmark_fastpath(runtime, rows):
    if type(rows) is not int or not 1 <= rows <= MAX_BENCH_ROWS:
        raise ValueError(":speed fastbatch [1..50000]")
    # Do not benchmark the disk/CPU alongside a live model turn or while a
    # queued user request is waiting. This is a LOCAL explicit command only.
    require_idle = getattr(runtime, "require_idle", None)
    if not callable(require_idle):
        raise ValueError("verified idle Runtime required for speed test")
    require_idle()
    from scripts.benchmark_procedural_fastpath import run_benchmark
    result = run_benchmark(rows=rows)
    result["command"] = "LOCAL_OPERATOR_ONLY"
    result["organ"] = "compiled_fast_output"
    return result


def operator_command(runtime, args):
    if not args or args == ["models"]:
        return observed_models(runtime.store, runtime.session)
    if args[0] == "fastbatch" and len(args) in (1, 2):
        try:
            rows = int(args[1]) if len(args) == 2 else 10000
        except ValueError as exc:
            raise ValueError(":speed fastbatch [1..50000]") from exc
        return benchmark_fastpath(runtime, rows)
    raise ValueError(":speed [models|fastbatch [1..50000]]")
