"""Opt-in, bounded existing-home F1/F5 Memory.recall -> C3 budget query.

Separate operator CLI candidate, NOT wired into the frozen Runtime._turn path.
No autonomous tools, age promotion or background learning.
"""
import argparse
import hashlib
import json
import re
import threading
import time
from pathlib import Path

from v13.common import dumps
from v13.runtime import Runtime
from v13.source_consumer import verified_recall_messages, BUDGET_VALUE


def _digest(messages):
    return hashlib.sha256(dumps(messages).encode("utf-8")).hexdigest()


def _age0_only(r):
    if (r.cfg.get("system_stage") != 0
            or r.cfg.get("learning_mode") != "RECORD_ONLY"
            or r.cfg.get("latents_enabled") is not False
            or r.cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE0_RECORD_ONLY_REQUIRED")
    if not r.idle() or r.paused:
        raise ValueError("RUNTIME_NOT_IDLE")


def _session_exists(r, session):
    return (isinstance(session, str) and bool(session)
            and r.store.one("SELECT id FROM sessions WHERE id=?", (session,)) is not None)


def _preflight(r, query, session):
    _age0_only(r)
    if not _session_exists(r, session):
        return {"status": "CLARIFY", "reason": "SESSION_NOT_FOUND",
                "model_called": False, "native_calls": 0}, None
    packet = verified_recall_messages(r.cfg, query, session, r.memory)
    decision = packet["decision"]
    if decision["status"] != "ADMITTED" or packet["messages"] is None:
        return {"status": decision["status"], "reason": decision.get("reason"),
                "answer": decision.get("answer", ""),
                "model_called": False, "native_calls": 0}, None
    source = decision["source"]
    return {"status": "READY", "reason": "VERIFIED_RECALL",
            "memory_id": source["memory_id"], "source_ref": source["source_ref"],
            "messages_sha256": _digest(packet["messages"]),
            "model_called": False, "native_calls": 0}, packet


def _answer_uses_euro_source(answer, source):
    match = BUDGET_VALUE.fullmatch(source["value"])
    if not match or not isinstance(answer, str):
        return False
    amount = source["value"].split(" ", 1)[0]
    # Fail closed on wrong currency, grouping, decimal extensions or unquoted amounts.
    return bool(re.search(r"(?<!\\d)" + re.escape(amount)
                          + r"(?!\\d|[.,]\\d)\\s*(?:Euro(?:s)?|EUR|€)(?!\\w)",
                          answer, flags=re.I))


def query(r, text, session=None, *, native=False, timeout_s=120, max_tokens=64):
    """Return a bounded decision; native execution requires explicit opt-in."""
    session = r.session if session is None else session
    preflight, packet = _preflight(r, text, session)
    if packet is None or not native:
        return preflight
    if not (1 <= int(max_tokens) <= 128 and 1 <= float(timeout_s) <= 120):
        raise ValueError("BOUNDED_NATIVE_LIMIT_REQUIRED")
    verified = r.models.verify(deep=True)
    language = verified.get("language")
    if not language or not language.get("ok") or language.get("hash_checked") is not True:
        return dict(preflight, status="C3_MODEL_NOT_VERIFIED", reason="C3_DEEP_HASH_REQUIRED")
    r.models.path_for("C3_LANGUAGE")
    runner = None
    calls = 0
    released = None
    output = None
    metrics = {}
    try:
        runner = r.pool.get("C3_LANGUAGE")
        # Loading can take time. Re-read F1/F5, active corrections and SourceRef
        # after model acquisition, immediately before the one native call.
        _age0_only(r)
        current, second = _preflight(r, text, session)
        if (second is None or current["status"] != "READY"
                or current["memory_id"] != preflight["memory_id"]
                or current["source_ref"] != preflight["source_ref"]
                or current["messages_sha256"] != preflight["messages_sha256"]):
            return {"status": "CLARIFY", "reason": "SOURCE_CHANGED_BEFORE_DISPATCH",
                    "model_called": False, "native_calls": 0}
        calls = 1
        output = "".join(runner.generate(second["messages"], threading.Event(),
                                         time.monotonic() + float(timeout_s),
                                         max_tokens=int(max_tokens), seed=13))
        metrics = dict(runner.last_metrics)
    finally:
        if runner is not None:
            released = r.pool.unload("C3_LANGUAGE")
    if not released or released.get("process_reaped") is not True:
        return {"status": "NATIVE_RELEASE_NOT_PROVEN", "model_called": bool(calls),
                "native_calls": calls}
    if metrics.get("status") != "FINAL" or not _answer_uses_euro_source(output, packet["decision"]["source"]):
        return {"status": "UNVERIFIED_NATIVE_ANSWER", "reason": "NO_EXACT_EURO_SOURCE_MATCH",
                "model_called": True, "native_calls": 1}
    return {"status": "FINAL", "answer": output,
            "source_ref": preflight["source_ref"],
            "model_revision": r.models.revision("C3_LANGUAGE"),
            "native_status": metrics["status"], "process_reaped": True,
            "model_called": True, "native_calls": 1}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--session", default=None)
    p.add_argument("--native", action="store_true",
                   help="explicitly invoke one pinned C3 native generation")
    p.add_argument("--timeout", type=float, default=120)
    p.add_argument("--max-tokens", type=int, default=64)
    args = p.parse_args(argv)
    home = Path(args.home).expanduser().resolve()
    if not home.is_dir() or not (home / "config/settings.json").is_file():
        print(json.dumps({"status": "ERROR", "reason": "EXISTING_HOME_REQUIRED"}))
        return 2
    r = None
    try:
        r = Runtime(home)
        r.sleep.cycle.set_policy("enabled", "off")
        result = query(r, args.query, args.session, native=args.native,
                       timeout_s=args.timeout, max_tokens=args.max_tokens)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] in {"READY", "FINAL", "CLARIFY", "NOT_APPLICABLE"} else 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "reason": type(exc).__name__}, sort_keys=True))
        return 2
    finally:
        if r is not None:
            r.close()


if __name__ == "__main__":
    raise SystemExit(main())
