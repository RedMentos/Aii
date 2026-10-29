"""Run97: explicit deterministic SOURCE_EXACT answer from verified Age0 F1/F5 memory.

This is NOT model inference, general question answering or production Runtime._turn.
It does not change the existing :verified preflight or grant learning authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.ask_verified_budget import BudgetContext, _preflight
from v13.source_consumer import TOPIC, BUDGET_VALUE


def query_exact(r, question, session=None):
    session = r.session if session is None else session
    first, packet = _preflight(r, question, session)
    if packet is None:
        return dict(first, mode="SOURCE_EXACT", model_called=False, native_calls=0)
    source = packet["decision"]["source"]
    if (not isinstance(source, dict)
            or not isinstance(source.get("topic"), str)
            or not isinstance(source.get("value"), str)
            or not TOPIC.fullmatch(source["topic"])
            or not BUDGET_VALUE.fullmatch(source["value"])):
        return {"status": "CLARIFY", "reason": "SOURCE_EXACT_GRAMMAR_REFUSED",
                "mode": "SOURCE_EXACT", "model_called": False, "native_calls": 0}

    # A source may be revoked or superseded after the first read. Refuse
    # before returning text unless the entire live admission is unchanged.
    second, new_packet = _preflight(r, question, session)
    same = (new_packet is not None and second.get("status") == "READY"
            and second.get("memory_id") == first.get("memory_id")
            and second.get("source_ref") == first.get("source_ref")
            and second.get("messages_sha256") == first.get("messages_sha256")
            and new_packet["decision"]["source"] == source)
    if not same:
        return {"status": "CLARIFY", "reason": "SOURCE_CHANGED_BEFORE_EGRESS",
                "mode": "SOURCE_EXACT", "model_called": False, "native_calls": 0}

    return {"status": "FINAL", "answer": source["topic"] + ": " + source["value"] + ".",
            "mode": "SOURCE_EXACT", "memory_id": first["memory_id"],
            "source_ref": first["source_ref"], "messages_sha256": first["messages_sha256"],
            "model_called": False, "native_calls": 0,
            "learning_weight_commit": False, "age_promotion": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--query", required=True)
    parser.add_argument("--session")
    args = parser.parse_args(argv)
    home = args.home.expanduser().resolve()
    if not (home / "config/settings.json").is_file():
        print(json.dumps({"status": "ERROR", "reason": "EXISTING_HOME_REQUIRED"}))
        return 2
    context = None
    try:
        context = BudgetContext(home)
        result = query_exact(context, args.query, args.session)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] in {"FINAL", "CLARIFY", "NOT_APPLICABLE"} else 2
    except Exception as exc:
        print(json.dumps({"status": "ERROR", "reason": type(exc).__name__}, sort_keys=True))
        return 2
    finally:
        if context is not None:
            context.close()


if __name__ == "__main__":
    raise SystemExit(main())
