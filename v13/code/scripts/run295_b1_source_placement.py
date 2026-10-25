#!/usr/bin/env python3
"""Run295: frozen Run288 B1 prompt, alternative source placement, genuine native negatives.

This is a *diagnostic* on registered pinned weights, never a production prompt
change, memory-gate promotion or permission grant.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import APP, atomic_write, dumps, file_hash
from v13.prompts import TEXT

SCHEMA = "V13_RUN295_B1_SOURCE_PLACEMENT_NATIVE_V1"
MATCH = "Projekt Kelmo16: Finanzrahmen?"
WRONG_TOPIC = "Projekt Kelmo16: Wer leitet das Team?"
WRONG_ENTITY = "Projekt Kelmo17: Finanzrahmen?"
QUESTIONS = (MATCH, WRONG_TOPIC, WRONG_ENTITY)
ARMS = ("baseline", "user_source", "system_plain")
FROZEN_HASH = "54f859ca3667028b4ea83fbd91b46b4c5c85627868f795d1da3ed0e4c70d333c"
USER_SOURCE = ("Earlier you corrected the financial framework of Projekt Kelmo16 to 400 Euro. "
               "This is your statement, not independently verified. Apply it only to that "
               "exact project and financial topic.")
SYSTEM_PLAIN = ("For Projekt Kelmo16's financial framework only, the saved operator correction "
                "says 400 Euro; this is not independently verified. Do not use it for other "
                "topics or projects.")


def original_messages(question=MATCH):
    t = TEXT["en"]
    source = [{"correction": "400 Euro", "matched_query": MATCH,
               "relevance": "approved learned query-topic association; correction supplied by operator",
               "topic": "Projekt Kelmo16 Budget"}]
    task = {"action_type": "LOCAL_TEXT_REPORT", "external_tool_execution": False,
            "task_request": {"authority": "REQUEST_NOT_FACT", "exact_request": question,
                             "origin": "SOURCE_USER_REQUEST"},
            "unresolved_observer_hypotheses": []}
    system = (t["system"] + " " + t["conduct"] + " " + t["answer_rules"] +
              "\n" + t["memories"] + dumps(source) +
              "\n" + t["task_context"] + dumps(task))
    return [{"role": "system", "content": system}, {"role": "user", "content": question}]


def messages_for(arm, question):
    if arm not in ARMS or question not in QUESTIONS:
        raise ValueError("Unregistered native diagnostic arm/question")
    baseline = original_messages()
    if hashlib.sha256(dumps(baseline).encode("utf-8")).hexdigest() != FROZEN_HASH:
        raise ValueError("Frozen Run288 B1 native prompt changed")
    messages = original_messages(question)
    if arm == "user_source":
        messages.insert(-1, {"role": "user", "content": USER_SOURCE})
    elif arm == "system_plain":
        messages[0]["content"] += "\n" + SYSTEM_PLAIN
    return messages


def evaluate(rows):
    """Diagnostic signal only. Leakage on either negative makes an arm unsafe."""
    out = {}
    for arm in ARMS:
        subset = {r["question"]: r for r in rows if r.get("arm") == arm}
        complete = len(subset) == len(QUESTIONS) and all(
            subset[q].get("status") == "FINAL" and subset[q].get("native_completed") is True
            for q in QUESTIONS if q in subset)
        uses = bool(complete and "400 Euro" in subset[MATCH]["output"])
        leaks = [q for q in QUESTIONS[1:] if q in subset and "400 Euro" in subset[q].get("output", "")]
        out[arm] = {"native_complete": complete, "matched_source_used": uses,
                    "negative_leaks": leaks, "candidate_signal_only": uses and not leaks}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error("Refusing to overwrite existing native evidence")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Fail before any native launch if the frozen original prompt is not exact.
    messages_for("baseline", MATCH)
    source_hashes = {path: file_hash(APP / path) for path in
                     ("v13/prompts.py", "v13/runners.py", "v13/runtime.py",
                      "scripts/run295_b1_source_placement.py")}
    report = {"schema": SCHEMA, "status": "RUNNING", "source_hashes": source_hashes,
              "frozen_original_messages_sha256": FROZEN_HASH, "seed": 13,
              "answer_tokens": 64, "role": "B1_DETAIL", "rows": [],
              "claim_limit": "One synthetic frozen Run288 native prompt, new placement arms; not a registered memory gate or Redmi proof.",
              "canonical_architecture_complete": False,
              "STEP2": "UTILITY_FAIL", "B3_L1": "FAIL",
              "Body_JEPA": "UNAVAILABLE", "jepa_weight": 0, "Redmi_measured": False}
    def save():
        atomic_write(args.out, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    save()
    from v13.config import initialize
    from v13.runtime import Runtime
    installed = args.installed_home.resolve()
    try:
        with tempfile.TemporaryDirectory(prefix="v13-run295-") as td:
            home = Path(td)
            initialize(home)
            for name in ("models", "bin"):
                shutil.rmtree(home / name)
                (home / name).symlink_to(installed / name, target_is_directory=True)
            shutil.copyfile(installed / "config/models.json", home / "config/models.json")
            r = Runtime(home)
            try:
                r.cfg.update(answer_tokens=64, history_turns=0, observer_mode="off",
                             body_residency_mb=0)
                report["model_sha256"] = file_hash(r.models.path_for("B1_DETAIL"))
                report["model_revision"] = r.models.revision("B1_DETAIL")
                report["runner_sha256"] = file_hash(home / "bin/llama-server")
                save()
                for arm in ARMS:
                    for question in QUESTIONS:
                        msgs = messages_for(arm, question)
                        row = {"arm": arm, "question": question,
                               "messages_sha256": hashlib.sha256(dumps(msgs).encode()).hexdigest(),
                               "status": "RUNNING", "output": "", "native_completed": False}
                        report["rows"].append(row)
                        save()
                        try:
                            runner = r.pool.get("B1_DETAIL")
                            deadline = time.monotonic() + 150
                            chunks = list(runner.generate(msgs, threading.Event(), deadline,
                                                          max_tokens=64, seed=13))
                            row.update(status=runner.last_metrics.get("status", "UNKNOWN"),
                                       output="".join(chunks), metrics=runner.last_metrics,
                                       native_completed=bool(chunks) and
                                       runner.last_metrics.get("status") == "FINAL")
                        except Exception as exc:
                            row.update(status="ERROR", error=type(exc).__name__ + ": " + str(exc))
                        finally:
                            row["unload"] = r.pool.unload()
                            save()
            finally:
                r.close()
    except Exception as exc:
        report["fatal_error"] = type(exc).__name__ + ": " + str(exc)
    report["diagnostics"] = evaluate(report["rows"])
    report["native_valid"] = (len(report["rows"]) == len(ARMS) * len(QUESTIONS)
                              and all(v["native_complete"] for v in report["diagnostics"].values())
                              and bool(report.get("model_sha256")) and bool(report.get("runner_sha256")))
    report["status"] = ("B1_NATIVE_PROMPT_SIGNAL_ONLY"
                        if report["native_valid"] and any(v["candidate_signal_only"]
                                                          for v in report["diagnostics"].values())
                        else "B1_NATIVE_PROMPT_NOT_SUPPORTED" if report["native_valid"]
                        else "B1_NATIVE_DIAGNOSTIC_INVALID")
    save()
    print(dumps({"status": report["status"], "diagnostics": report["diagnostics"],
                 "native_valid": report["native_valid"]}))
    return 0 if report["native_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
