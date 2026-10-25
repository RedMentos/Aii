#!/usr/bin/env python3
"""Run291 preregistered Linux-native memory source-use prompt diagnostic.

Runs the *unchanged* actual-weight retrieval lifecycle with one ephemeral
system-prompt suffix. Never enables new authority or changes default prompts.
A successful diagnostic process exit is NOT an acceptance-gate PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import atomic_write, file_hash
from v13.prompts import TEXT

SCHEMA = "V13_RUN291_NATIVE_MEMORY_PROMPT_AB_V1"
SUFFIX = (
    " For a matching stored user correction, answer with its exact correction"
    " value first. Do not give a generic explanation instead. If no correction"
    " matches, say you do not know. A user correction is not independently verified."
)
SUFFIX_SHA256 = "e85a1ca602ed5ebcc39272b79edacec7ba591524663eacbd8bc2e0332dcd30b2"
ARMS = ("baseline", "source_first")


def configure_arm(arm: str) -> str:
    if arm not in ARMS:
        raise ValueError("Unregistered Run291 arm")
    if hashlib.sha256(SUFFIX.encode("utf-8")).hexdigest() != SUFFIX_SHA256:
        raise ValueError("Preregistered prompt suffix bytes changed")
    original = TEXT["en"]["system"]
    if arm == "source_first":
        TEXT["en"]["system"] = original + SUFFIX
    return original


def summarize(arm: str, report: dict, integration_exit: int, source_hashes: dict) -> dict:
    calls = [c for c in report.get("native_generation_calls", [])
             if c.get("phase") == "NATIVE_ANSWER" and c.get("role") in ("C3_LANGUAGE", "B1_DETAIL")]
    observed = {}
    for call in calls:
        systems = [m.get("content", "") for m in call.get("messages", [])
                   if isinstance(m, dict) and m.get("role") == "system"]
        observed[call["role"]] = {
            "completed": call.get("completed") is True,
            "suffix_present": any(SUFFIX in s for s in systems),
        }
    expected = arm == "source_first"
    prompt_bound = (set(observed) == {"C3_LANGUAGE", "B1_DETAIL"}
                    and all(row["completed"] and row["suffix_present"] is expected
                            for row in observed.values()))
    checks = report.get("checks", {})
    source_bound = (checks.get("native_language_exact_source_delivery") is True
                    and checks.get("native_detail_exact_source_delivery") is True)
    return {
        "schema": SCHEMA, "arm": arm, "suffix_sha256": SUFFIX_SHA256,
        "integration_status": report.get("status"), "integration_exit": integration_exit,
        "native_roles": observed, "prompt_bound": prompt_bound,
        "source_delivery_bound": source_bound,
        "diagnostic_valid": prompt_bound and source_bound,
        "native_detail_answer_uses_human_source": checks.get("native_detail_answer_uses_human_source"),
        "native_language_answer_uses_human_source": checks.get("native_language_answer_uses_human_source"),
        "same_entity_wrong_topic_rejected": checks.get("same_entity_wrong_topic_rejected"),
        "different_entity_rejected": checks.get("different_entity_rejected"),
        "different_session_rejected": checks.get("different_session_rejected"),
        "all_existing_checks_pass": bool(checks) and all(checks.values()),
        "source_hashes": source_hashes,
        "claim_limits": [
            "One pinned Linux-native fixture, not generalized semantic utility.",
            "Prompt candidate is ephemeral; production prompts and model weights unchanged.",
            "Original STEP2/B3/Body-JEPA/Redmi and full-system gates remain negative.",
        ],
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arm", choices=ARMS, required=True)
    p.add_argument("--installed-home", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    if args.out.exists():
        p.error("Refusing to overwrite an existing native result")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    source_hashes = {
        name: file_hash(root / name) for name in
        ("v13/prompts.py", "v13/runtime.py", "tests/integration_retrieval.py")
    }
    original = configure_arm(args.arm)
    saved_argv = sys.argv[:]
    try:
        from tests import integration_retrieval
        sys.argv = [str(Path(integration_retrieval.__file__)),
                    "--installed-home", args.installed_home, "--out", str(args.out)]
        rc = integration_retrieval.main()
    finally:
        sys.argv = saved_argv
        TEXT["en"]["system"] = original
    if not args.out.is_file():
        raise RuntimeError("Actual native integration report missing")
    report = json.loads(args.out.read_text(encoding="utf-8"))
    summary = summarize(args.arm, report, rc, source_hashes)
    atomic_write(args.out.with_suffix(".summary.json"),
                 json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "source_hashes"}, sort_keys=True))
    return 0 if summary["diagnostic_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
