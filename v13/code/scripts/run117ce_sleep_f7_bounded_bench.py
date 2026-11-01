#!/usr/bin/env python3
"""Run117CE bounded F7 Sleep fairness overhead diagnostic, Linux software only.

Synthetic real Store/ContextOS digest data; no native model, weights, or Redmi.
Never prints or exports source text. No latency/energy acceptance gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import resource
import statistics
import tempfile
import time
from pathlib import Path

from v13.config import initialize
from v13.store import Store, audit_closed
from v13 import sleep_offline as S

REVISION = "run117ce-sleep-f7-bounded-bench-v1"
MAX_SESSIONS = 256
MAX_TURNS = 70


def benchmark(session_count, turns_per_session):
    if (type(session_count) is not int or not 1 <= session_count <= MAX_SESSIONS
            or type(turns_per_session) is not int or not 1 <= turns_per_session <= MAX_TURNS):
        raise ValueError("BOUNDED_BENCH_INPUT_RED")
    started = time.monotonic()
    cycle_ms = []
    processed = []
    with tempfile.TemporaryDirectory(prefix="v13-run117ce-") as td:
        home = Path(td)
        initialize(home)
        store = Store(home)
        sessions = []
        try:
            for i in range(session_count):
                session = store.new_session()
                sessions.append(session)
                for j in range(turns_per_session):
                    event = store.event(session, f"BENCH_SYNTHETIC_{i:04d}_{j:03d}")
                    store.message(session, event["event_id"], "assistant",
                                  f"synthetic response {i:04d}/{j:03d}",
                                  "FINAL", {"direct_source_copy": True})
            build_s = time.monotonic() - started
            # Bounded by per-session 64-turn pages and the eight-session
            # scheduler; an extra cycle confirms no pending work remains.
            max_cycles = math.ceil(session_count / S.SESSIONS_MAX) * (
                math.ceil(turns_per_session / S.TURNS_MAX) + 1) + 2
            for _ in range(max_cycles):
                t0 = time.monotonic()
                rep = S.digest(store)
                cycle_ms.append(round((time.monotonic() - t0) * 1000, 3))
                processed.append({k: rep[k] for k in
                                  ("sessions", "turns", "backlog_sessions", "deferred_sessions")})
                if rep["sessions"] == 0:
                    break
            else:
                raise AssertionError("FAIR_SCHEDULER_DID_NOT_CONVERGE_RED")
            state, _ = store.state(S.KEY, None)
            if len(state["sessions"]) != session_count:
                raise AssertionError("MISSING_SESSION_DIGEST_RED")
            for session in sessions:
                d = state["sessions"][session]
                if len(d["entries"]) != turns_per_session:
                    raise AssertionError("MISSING_OR_DUPLICATE_TURN_RED")
                last = store.one(
                    "SELECT MAX(id) AS last FROM messages WHERE session_id=? "
                    "AND role='assistant' AND status='FINAL'", (session,))["last"]
                if d["until"] != last:
                    raise AssertionError("DIGEST_CURSOR_NOT_CAUGHT_UP_RED")
            total = sum(x["turns"] for x in processed)
            if total != session_count * turns_per_session:
                raise AssertionError("TOTAL_TURN_COUNT_RED")
            if S.view(store, sessions[-1], cap=10000)["fact_authority"] != 0:
                raise AssertionError("DIGEST_FACT_AUTHORITY_RED")
        finally:
            store.close()
        closed = audit_closed(home)
        if closed.get("ok") is not True:
            raise AssertionError("CLOSED_STORE_AUDIT_RED")
    elapsed_s = time.monotonic() - started
    # ru_maxrss is KiB on this Linux runner, NOT a Redmi measurement.
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return {
        "revision": REVISION, "status": "INTEGRITY_PASS",
        "evidence_class": "LINUX_SOFTWARE_STORE_ONLY",
        "platform": platform.system(), "redmi_measured": False,
        "session_count": session_count, "turns_per_session": turns_per_session,
        "total_turns": session_count * turns_per_session,
        "cycles_including_empty": len(processed),
        "cycle_counts": processed,
        "build_seconds": round(build_s, 4),
        "digest_ms_median": round(statistics.median(cycle_ms), 3),
        "digest_ms_max": max(cycle_ms),
        "elapsed_seconds": round(elapsed_s, 4),
        "process_peak_rss_mb_linux": round(rss_mb, 2),
        "closed_store_ok": True,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "learning_authority": 0,
        "native_model_calls": 0, "whole_system_complete": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions", type=int, required=True)
    ap.add_argument("--turns", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError("OUTPUT_EXISTS_RED")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    result = benchmark(args.sessions, args.turns)
    result["script_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    from v13.common import atomic_write
    atomic_write(args.out, json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "sessions": result["session_count"],
                      "turns": result["total_turns"], "redmi_measured": False}))


if __name__ == "__main__":
    main()
