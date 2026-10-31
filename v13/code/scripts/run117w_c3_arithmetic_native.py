#!/usr/bin/env python3
"""Run117W seed1063 pinned native C3 arithmetic definition vs typed JEF copy.

Disjoint frozen cohort; actual native C3 only. No native Body/JEF/C2,
learning, tool dispatch, output authority or STEP2 promotion.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import time

from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import _reaped
from scripts.run115j_typed_jef_role_native import (
    C3_FILE, C3_SHA, C3_REV, RUNNER_SHA, SCHEMA, CONFIG as BASE_CONFIG,
)
from scripts.run47_jef_c3_typed_receiver_native import score
from scripts.run117s_body_complementarity_preflight import (
    SYSTEM as BASE_SYSTEM, _span,
)
from v13.agi.jef_eligibility_source_shadow_run46b import recipe
from v13.common import atomic_write, dumps, file_hash
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import audit_closed

SEED = 1063
FIXTURE_SHA = "2b62fd13c81201c23574fa42ad87176f4386c9ec9c608ed9"
IDS = ("Arbor", "Brisa", "Cyra", "Doran", "Elyra", "Fenix")
ARMS = ("BASE_SOURCE_SYSTEM", "EXPLICIT_ARITHMETIC_SYSTEM",
        "TYPED_JEF_FORMATTER")
SYSTEMS = {
    ARMS[0]: BASE_SYSTEM,
    ARMS[1]: BASE_SYSTEM + (
        " For a selected eligible option, remaining is the binding budget "
        "in euros MINUS the selected option cost in euros. For NONE, remaining "
        "is null. Never use 0 unless that subtraction is exactly 0."),
    ARMS[2]: (
        "You are C3_LANGUAGE, a JSON formatter in a non-delivering SHADOW "
        "experiment. Copy the exact typed_jef_candidate choice and remaining "
        "from the USER payload. Do not calculate, override, approve, dispatch "
        "tools, learn or deliver output. Return only JSON with exactly choice "
        "A/B/NONE and remaining integer or null."),
}
CONFIG = BASE_CONFIG | {
    "seed": SEED, "temperature": 0.0, "answer_tokens": 96,
    "observer_mode": "off", "learning_mode": "RECORD_ONLY",
    "history_turns": 0, "memory_top_k": 0, "teacher_enabled": False,
}
POLICY = re.compile(
    r"Binding policy: budget ([1-9][0-9]*) euros; "
    r"deadline ([1-9][0-9]*) days; local-only (true|false)\."
)
OPTION = re.compile(
    r"Option (?P<id>[AB]): cost (?P<cost>[1-9][0-9]*) euros, "
    r"duration (?P<days>[1-9][0-9]*) days, local (?P<local>true|false)\."
)
GOOD = ("NATIVE_COMPLETE_EXPLORATORY_ARITHMETIC_SIGNAL",
        "NATIVE_COMPLETE_NO_ARITHMETIC_GAIN")
RED = "STRUCTURAL_RED"


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN117W_FROZEN_FIXTURE_SHA_RED")
    data = json.loads(raw)
    if (set(data) != {"schema", "seed", "arms", "rows"}
            or data["schema"] != "v13.run117w.c3_arithmetic_seed1063.v1"
            or type(data["seed"]) is not int or data["seed"] != SEED
            or data["arms"] != list(ARMS)
            or [r.get("id") for r in data["rows"]] != list(IDS)):
        raise ValueError("RUN117W_FROZEN_COHORT_RED")
    expected = (("A", 50), ("B", 60), ("NONE", None),
                ("B", 70), ("B", 85), ("NONE", None))
    for row, oracle in zip(data["rows"], expected):
        if (set(row) != {"id", "prior", "current", "policy_span",
                        "option_span", "oracle"}
                or row["prior"].count(row["policy_span"]) != 1
                or row["current"].count(row["option_span"]) != 1
                or not row["prior"].startswith("Project " + row["id"])
                or not row["current"].startswith("Project " + row["id"])
                or (row["oracle"]["choice"], row["oracle"]["remaining"])
                != oracle):
            raise ValueError("RUN117W_FROZEN_SOURCE_RED")
        m = POLICY.fullmatch(row["policy_span"])
        opts = list(OPTION.finditer(row["option_span"]))
        if (m is None or len(opts) != 2
                or [o["id"] for o in opts] != ["A", "B"]):
            raise ValueError("RUN117W_POLICY_OR_OPTION_RED")
        choices = [{"entity": o["id"], "cost": int(o["cost"]),
                    "days": int(o["days"]), "local": o["local"] == "true"}
                   for o in opts]
        chosen, evaluated = recipe(
            int(m[1]), int(m[2]), m[3] == "true", choices)
        remaining = next((o["remaining"] for o in evaluated
                          if o["entity"] == chosen), None)
        if row["oracle"] != {"choice": chosen, "remaining": remaining}:
            raise ValueError("RUN117W_ORACLE_RECIPE_RED")
    return data["rows"]


def _prompts(runtime, prior, current, row):
    policy = _span(runtime.store, prior["source_ref"],
                   row["prior"], row["policy_span"])
    options = _span(runtime.store, current["source_ref"],
                    row["current"], row["option_span"])
    m = POLICY.fullmatch(row["policy_span"])
    opts = list(OPTION.finditer(row["option_span"]))
    choices = [{"entity": o["id"], "cost": int(o["cost"]),
                "days": int(o["days"]), "local": o["local"] == "true"}
               for o in opts]
    selected, evaluated = recipe(int(m[1]), int(m[2]),
                                 m[3] == "true", choices)
    remaining = next((o["remaining"] for o in evaluated
                      if o["entity"] == selected), None)
    typed = {"choice": selected, "remaining": remaining}
    if typed != row["oracle"]:
        raise ValueError("TYPED_SOURCE_RECIPE_MISMATCH_RED")
    common = {"schema": "v13.run117w.two_source_spans.v1",
              "policy": policy, "options": options,
              "source_role": "UNTRUSTED_EXACT_USER"}
    payloads = {
        ARMS[0]: common,
        ARMS[1]: common,
        ARMS[2]: dict(common, typed_jef_candidate=typed,
                      candidate_authority=0,
                      candidate_origin="DETERMINISTIC_SOURCE_RECIPE_NOT_NATIVE_JEF"),
    }
    out = {}
    for arm in ARMS:
        messages = [{"role": "system", "content": SYSTEMS[arm]},
                    {"role": "user", "content": dumps(payloads[arm])}]
        if (row["policy_span"] in SYSTEMS[arm]
                or row["option_span"] in SYSTEMS[arm]
                or '"oracle"' in messages[1]["content"]
                or (arm != ARMS[2]
                    and "typed_jef_candidate" in messages[1]["content"])):
            raise ValueError("C3_SOURCE_OR_ORACLE_ROLE_LEAK_RED")
        out[arm] = messages
    return out


def _pin(installed):
    m = ModelManager(installed)
    if (file_hash(m.path_for("C3_LANGUAGE")) != C3_SHA
            or m.revision("C3_LANGUAGE") != C3_REV
            or file_hash(installed / "bin/llama-server") != RUNNER_SHA):
        raise ValueError("RUN117W_PINNED_NATIVE_C3_RED")


def _summarize(report):
    scores = {arm: 0 for arm in ARMS}
    counts = {arm: 0 for arm in ARMS}
    closed = len(report["rows"]) == 6
    for row in report["rows"]:
        closed &= row.get("closed_store_ok") is True
        closed &= row.get("no_live_output") is True
        if len(row.get("arms", [])) != 3:
            closed = False
        for item in row.get("arms", []):
            arm = item.get("arm")
            if arm not in ARMS:
                closed = False
                continue
            if (item.get("status") == "RECORDED"
                    and item.get("native_final") is True
                    and item.get("process_reaped") is True):
                counts[arm] += 1
                scores[arm] += item["score"]["correct"]
    report["scores"] = scores
    report["recorded_by_arm"] = counts
    if (not closed or report["native_c3_calls"] != 18
            or any(counts[a] != 6 for a in ARMS)):
        return RED
    signal = (scores[ARMS[1]] >= scores[ARMS[0]] + 2
              and scores[ARMS[1]] >= 4
              and scores[ARMS[2]] >= 5)
    report["exploratory_arithmetic_signal"] = signal
    return GOOD[0] if signal else GOOD[1]


def run(fixture_path, installed, work, out):
    rows = fixture(fixture_path)
    installed, work, out = Path(installed).resolve(), Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN117W_FRESH_WORK_OUT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run117w.c3_arithmetic_native.v1",
        "seed": SEED, "fixture_sha256": FIXTURE_SHA,
        "status": "INCOMPLETE", "native_c3": True,
        "native_c3_calls": 0, "native_body_calls": 0,
        "native_jef_calls": 0, "native_c2_calls": 0,
        "typed_candidate_precomputed": True,
        "scores": {a: 0 for a in ARMS}, "recorded_by_arm": {},
        "exploratory_arithmetic_signal": False,
        "rows": [], "age0": "RECORD_ONLY",
        "step2_exit": "EVIDENCE_NOT_PASSING", "b3": "NO_PROMOTION",
        "body_jepa": "UNAVAILABLE", "world_jepa": "SHADOW",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_system_complete": False, "output_committed": False,
        "tool_dispatches": 0, "learning_authority": 0,
        "delivery_authority": 0,
    }
    def save():
        atomic_write(out / "report.json", dumps(report))
    save()
    try:
        _pin(installed)
        for index, row in enumerate(rows):
            home = work / row["id"]
            _prepare_home(home, installed, CONFIG)
            runtime = Runtime(home)
            entry = {"id": row["id"], "status": "INCOMPLETE",
                     "arms": [], "closed_store_ok": False,
                     "no_live_output": False}
            report["rows"].append(entry)
            save()
            try:
                prior = runtime.store.event(runtime.session, row["prior"])
                current = runtime.store.event(runtime.session, row["current"])
                entry["prior_source_ref"] = prior["source_ref"]
                entry["current_source_ref"] = current["source_ref"]
                prompts = _prompts(runtime, prior, current, row)
                order = ARMS[index % 3:] + ARMS[:index % 3]
                for arm in order:
                    messages = prompts[arm]
                    item = {"arm": arm, "status": "INCOMPLETE",
                            "messages": messages,
                            "messages_sha256": sha256(
                                dumps(messages).encode()).hexdigest(),
                            "native_final": False, "process_reaped": False,
                            "score": None}
                    entry["arms"].append(item)
                    save()
                    before = len(runtime.pool.release_history)
                    try:
                        runner = runtime.pool.get("C3_LANGUAGE")
                        report["native_c3_calls"] += 1
                        save()
                        output = "".join(runner.generate(
                            messages, runtime.cancel_event,
                            time.monotonic() + 120, 96, SCHEMA, seed=SEED))
                        item["output"] = output
                        item["native_metrics"] = dict(runner.last_metrics)
                        item["native_final"] = (
                            item["native_metrics"].get("status") == "FINAL")
                        item["score"] = score(output, row["oracle"])
                    except Exception as exc:
                        item["error_type"] = type(exc).__name__
                        item["error"] = str(exc)[:280]
                    finally:
                        runtime.pool.unload()
                        item["process_reaped"] = _reaped(
                            runtime.pool.release_history[before:])
                        item["status"] = (
                            "RECORDED" if item["native_final"]
                            and item["process_reaped"]
                            and item.get("native_metrics", {}).get("actual_model")
                            == C3_FILE else RED)
                        save()
                entry["status"] = (
                    "RECORDED" if all(a["status"] == "RECORDED"
                                      for a in entry["arms"]) else RED)
            except Exception as exc:
                entry["status"] = RED
                entry["error_type"] = type(exc).__name__
                entry["error"] = str(exc)[:280]
            finally:
                try:
                    entry["no_live_output"] = (
                        runtime.store.one(
                            "SELECT COUNT(*) AS n FROM actions")["n"] == 0
                        and runtime.store.one(
                            "SELECT COUNT(*) AS n FROM messages "
                            "WHERE role='assistant'")["n"] == 0)
                except Exception:
                    entry["no_live_output"] = False
                runtime.close()
                try:
                    entry["closed_store_ok"] = bool(audit_closed(home)["ok"])
                except Exception:
                    entry["closed_store_ok"] = False
                if not entry["closed_store_ok"] or not entry["no_live_output"]:
                    entry["status"] = RED
                save()
        report["status"] = _summarize(report)
    except Exception as exc:
        report["status"] = RED
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:280]
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--installed", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    report = run(args.fixture, args.installed, args.work, args.out)
    print(dumps({"status": report["status"],
                 "scores": report["scores"],
                 "native_c3_calls": report["native_c3_calls"]}))
    return 0 if report["status"] in GOOD else 2


if __name__ == "__main__":
    raise SystemExit(main())
