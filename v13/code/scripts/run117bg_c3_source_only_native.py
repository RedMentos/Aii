#!/usr/bin/env python3
"""Run117BG preregistered seed1081 native C3 causal-prior source-only pilot.

Deterministic synthetic Body source-ID packets, NOT native Body/JEF/C2.
Native C3 is measured only on exact Store USER source spans. No delivery.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import time

from scripts.run111_c3_b2_context_native import _prepare_home
from scripts.run113b_b1b2_c3_native import _reaped
from scripts.run115j_typed_jef_role_native import C3_FILE, C3_SHA, C3_REV, RUNNER_SHA, SCHEMA
from scripts.run117w_c3_arithmetic_native import CONFIG as BASE_CONFIG
from scripts.run47_jef_c3_typed_receiver_native import score
from v13.agi.eligibility import recipe
from v13.body_source_id_c3_evidence_bridge_candidate import build_source_id_c3_bridge
from v13.b1b2_source_id_quote_candidate import select
from v13.common import atomic_write, dumps, file_hash
from v13.jef_span_budget_shadow_candidate import POLICY, OPTION
from v13.models import ModelManager
from v13.runtime import Runtime
from v13.store import audit_closed

SEED = 1081
FIXTURE_SHA = "aeea2b0cec9bdca9a8fa8133eec4072a0e16587addf4887068e5b64d1e184d5f"
IDS = ("Sirius", "Vela", "Wren", "Xenia", "Yarrow", "Zephyr")
ARMS = ("BOTH_EXACT_SOURCES", "CURRENT_ONLY")
CONFIG = BASE_CONFIG | {"seed": SEED, "learning_mode": "RECORD_ONLY",
                        "observer_mode": "off", "teacher_enabled": False}
GOOD = ("NATIVE_COMPLETE_EXPLORATORY_CAUSAL_PRIOR_SIGNAL",
        "NATIVE_COMPLETE_NO_CAUSAL_PRIOR_SIGNAL")
RED = "STRUCTURAL_RED"
SYNTHETIC_BODY_REVISION = "RUN117BG_DETERMINISTIC_SELECTOR_NO_BODY_MODEL"


class _SyntheticBodyModelRevisions:
    """Only Body source-ID packets use a declared synthetic revision.

    The installed C3 model and the actual pool remain unchanged. Never claim
    this marker represents real B1/B2 model weights or native inference.
    """
    def __init__(self, models):
        self._models = models

    def revision(self, role):
        if role in ("B1_DETAIL", "B2_GIST"):
            return SYNTHETIC_BODY_REVISION
        return self._models.revision(role)

    def __getattr__(self, name):
        return getattr(self._models, name)


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN117BG_FIXTURE_SHA_RED")
    data = json.loads(raw)
    if (set(data) != {"schema", "seed", "arms", "rows"}
            or data["schema"] != "v13.run117bg.c3_source_only_seed1081.v1"
            or type(data["seed"]) is not int or data["seed"] != SEED
            or data["arms"] != list(ARMS)
            or [r.get("id") for r in data["rows"]] != list(IDS)):
        raise ValueError("RUN117BG_FIXTURE_SHAPE_RED")
    for row in data["rows"]:
        if set(row) != {"id", "prior", "current", "policy_span", "option_span", "oracle"}:
            raise ValueError("RUN117BG_FIXTURE_FIELDS_RED")
        p = POLICY.fullmatch(row["policy_span"])
        opts = list(OPTION.finditer(row["option_span"]))
        if (p is None or len(opts) != 2
                or [o[1] for o in opts] != ["A", "B"]
                or row["prior"].count(row["policy_span"]) != 1
                or row["current"].count(row["option_span"]) != 1
                or not row["prior"].startswith("Project " + row["id"])
                or not row["current"].startswith("Project " + row["id"])):
            raise ValueError("RUN117BG_SOURCE_GRAMMAR_RED")
        options = [{"entity": o[1], "cost": int(o[2]), "days": int(o[3]),
                    "local": o[4] == "true"} for o in opts]
        chosen, evaluated = recipe(int(p[1]), int(p[2]), p[3] == "true", options)
        remaining = next((x["remaining"] for x in evaluated
                          if x["entity"] == chosen), None)
        if row["oracle"] != {"choice": chosen, "remaining": remaining}:
            raise ValueError("RUN117BG_ORACLE_RECIPE_RED")
    return data["rows"]


def _pin(installed):
    m = ModelManager(installed)
    if (file_hash(m.path_for("C3_LANGUAGE")) != C3_SHA
            or m.revision("C3_LANGUAGE") != C3_REV
            or file_hash(installed / "bin/llama-server") != RUNNER_SHA):
        raise ValueError("RUN117BG_PINNED_NATIVE_C3_RED")


def _trusted_source_id(runtime, event, role):
    """Deterministic synthetic selector, never a native Body model or oracle prompt."""
    prefix = "Binding policy:" if role == "B2_GIST" else "Option A:"
    def choose(messages):
        if [m["role"] for m in messages] != ["system", "user"]:
            raise ValueError("RUN117BG_SELECTOR_ROLE_RED")
        payload = json.loads(messages[1]["content"])
        candidates = payload["candidates"]
        matched = [c for c in candidates if c["text"].startswith(prefix)]
        if len(matched) != 1:
            raise ValueError("RUN117BG_SELECTOR_AMBIGUOUS_RED")
        return dumps({"span_id": matched[0]["span_id"]})
    result = select(runtime, event, role, choose,
                    operator_opt_in=True, callback_opt_in=True)
    if (result.get("status") != "SHADOW_SOURCE_ID_SELECTED"
            or result.get("selection_correct_shadow") is not True
            or type(result.get("packet_id")) is not str):
        raise ValueError("RUN117BG_TRUSTED_SELECTOR_RED")
    return result["packet_id"]


def _prompts(runtime, prior, current, row, b2):
    b1 = _trusted_source_id(runtime, current, "B1_DETAIL")
    bridge = build_source_id_c3_bridge(
        runtime, prior, current, {"B2_GIST": b2, "B1_DETAIL": b1},
        operator_opt_in=True)
    if (bridge.get("status") != "SHADOW_C3_SOURCE_ID_EVIDENCE_READY"
            or bridge.get("model_called") is not False
            or bridge.get("answer_computed") is not False
            or bridge.get("output_committed") is not False
            or bridge.get("learning_authority") != 0):
        raise ValueError("RUN117BG_SOURCE_BRIDGE_RED")
    both = bridge["messages"]
    payload = json.loads(both[1]["content"])
    obs = payload["body_observations"]
    if ([x["role"] for x in obs] != ["B2_GIST", "B1_DETAIL"]
            or obs[0]["exact_source_excerpt"] != row["policy_span"]
            or obs[1]["exact_source_excerpt"] != row["option_span"]
            or payload["typed_jef_candidate"] is not None
            or payload["typed_candidate_authority"] != 0):
        raise ValueError("RUN117BG_SOURCE_OR_TYPED_LEAK_RED")
    current_only = [dict(both[0]), {"role": "user", "content": dumps({
        "task": payload["task"],
        "body_observations": [obs[1]],
        "typed_jef_candidate": None,
        "typed_candidate_authority": 0,
    })}]
    for messages in (both, current_only):
        if (len(messages) != 2
                or [m["role"] for m in messages] != ["system", "user"]
                or row["policy_span"] in messages[0]["content"]
                or row["option_span"] in messages[0]["content"]
                or '"oracle"' in messages[1]["content"]):
            raise ValueError("RUN117BG_PROMPT_LEAK_RED")
    if row["policy_span"] in dumps(current_only):
        raise ValueError("RUN117BG_NO_PRIOR_LEAK_RED")
    return {ARMS[0]: both, ARMS[1]: current_only}, bridge


def _summarize(report):
    scores = {a: 0 for a in ARMS}
    counts = {a: 0 for a in ARMS}
    paired = 0
    if len(report["rows"]) != 6 or report["native_c3_calls"] != 12:
        return RED
    for i, row in enumerate(report["rows"]):
        if (row["id"] != IDS[i] or row["status"] != "RECORDED"
                or not row["closed_store_ok"] or not row["no_live_output"]
                or len(row["arms"]) != 2):
            return RED
        per = {}
        for item in row["arms"]:
            a = item["arm"]
            if (a not in ARMS or a in per or item["status"] != "RECORDED"
                    or item["native_final"] is not True
                    or item["process_reaped"] is not True
                    or item["native_metrics"]["actual_model"] != C3_FILE
                    or type(item["score"]["correct"]) is not int):
                return RED
            per[a] = item
            counts[a] += 1
            scores[a] += item["score"]["correct"]
        paired += int(per[ARMS[0]]["score"]["correct"] == 1
                      and per[ARMS[1]]["score"]["correct"] == 1)
    report["scores"] = scores
    report["recorded_by_arm"] = counts
    report["paired_both_correct_current_abstains"] = paired
    if any(counts[a] != 6 for a in ARMS):
        return RED
    signal = scores[ARMS[0]] >= 4 and scores[ARMS[1]] >= 4 and paired >= 2
    report["exploratory_causal_prior_signal"] = signal
    return GOOD[0] if signal else GOOD[1]


def run(fixture_path, installed, work, out):
    rows = fixture(fixture_path)
    installed, work, out = Path(installed).resolve(), Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN117BG_FRESH_WORK_OUT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run117bg.c3_source_only_native.v1",
        "seed": SEED, "fixture_sha256": FIXTURE_SHA,
        "status": "INCOMPLETE", "native_c3_calls": 0,
        "native_body_calls": 0, "native_jef_calls": 0,
        "native_c2_calls": 0, "deterministic_source_selectors": 0,
        "scores": {a: 0 for a in ARMS}, "rows": [],
        "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "output_committed": False, "tool_dispatches": 0,
        "learning_authority": 0, "delivery_authority": 0,
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
            runtime.models = _SyntheticBodyModelRevisions(runtime.models)
            entry = {"id": row["id"], "status": "INCOMPLETE", "arms": [],
                     "closed_store_ok": False, "no_live_output": False}
            report["rows"].append(entry)
            save()
            try:
                prior = runtime.store.event(runtime.session, row["prior"])
                b2 = _trusted_source_id(runtime, prior, "B2_GIST")
                current = runtime.store.event(runtime.session, row["current"])
                prompts, bridge = _prompts(runtime, prior, current, row, b2)
                report["deterministic_source_selectors"] += 2
                entry["source_refs"] = bridge["source_refs"]
                entry["messages_sha256"] = bridge["messages_sha256"]
                save()
                order = ARMS[index % 2:] + ARMS[:index % 2]
                for arm in order:
                    messages = prompts[arm]
                    item = {"arm": arm, "status": "INCOMPLETE",
                            "messages": messages,
                            "messages_sha256": sha256(dumps(messages).encode()).hexdigest(),
                            "native_final": False, "process_reaped": False, "score": None}
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
                        item["native_final"] = item["native_metrics"].get("status") == "FINAL"
                        expected = row["oracle"] if arm == ARMS[0] else {
                            "choice": "NONE", "remaining": None}
                        item["score"] = score(output, expected)
                    except Exception as exc:
                        item["error_type"] = type(exc).__name__
                        item["error"] = str(exc)[:280]
                    finally:
                        runtime.pool.unload()
                        item["process_reaped"] = _reaped(runtime.pool.release_history[before:])
                        item["status"] = ("RECORDED" if item["native_final"]
                            and item["process_reaped"]
                            and item.get("native_metrics", {}).get("actual_model") == C3_FILE
                            else RED)
                        save()
                entry["status"] = ("RECORDED" if all(a["status"] == "RECORDED"
                                    for a in entry["arms"]) else RED)
            except Exception as exc:
                entry["status"] = RED
                entry["error_type"] = type(exc).__name__
                entry["error"] = str(exc)[:280]
            finally:
                try:
                    entry["no_live_output"] = (
                        runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0
                        and runtime.store.one("SELECT COUNT(*) AS n FROM messages "
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
    a = p.parse_args()
    r = run(a.fixture, a.installed, a.work, a.out)
    print(dumps({"status": r["status"], "scores": r["scores"],
                 "native_c3_calls": r["native_c3_calls"],
                 "deterministic_source_selectors": r["deterministic_source_selectors"]}))
    return 0 if r["status"] in GOOD else 2


if __name__ == "__main__":
    raise SystemExit(main())
