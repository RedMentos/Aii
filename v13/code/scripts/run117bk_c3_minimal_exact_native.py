#!/usr/bin/env python3
"""Run117BK preregistered seed1091 C3 exact-source minimal-vs-verbose pilot.

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

SEED = 1091
FIXTURE_SHA = "8d004fc2a0b6c80bac103e675b2012b33f1d078451a916a715ff47b0d1db81e4"
IDS = ("Astra1091", "Beryl1091", "Cedar1091", "Dahlia1091", "Ember1091", "Fjord1091")
ARMS = ("FULL_SOURCE_PACKET", "MINIMAL_EXACT_SPANS", "CURRENT_ONLY")
CONFIG = BASE_CONFIG | {"seed": SEED, "learning_mode": "RECORD_ONLY",
                        "observer_mode": "off", "teacher_enabled": False}
GOOD = ("NATIVE_COMPLETE_EXPLORATORY_MINIMAL_SOURCE_SIGNAL",
        "NATIVE_COMPLETE_NO_MINIMAL_SOURCE_SIGNAL")
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
        raise ValueError("RUN117BK_FIXTURE_SHA_RED")
    data = json.loads(raw)
    if (set(data) != {"schema", "seed", "arms", "rows"}
            or data["schema"] != "v13.run117bk.c3_minimal_exact_seed1091.v1"
            or type(data["seed"]) is not int or data["seed"] != SEED
            or data["arms"] != list(ARMS)
            or [r.get("id") for r in data["rows"]] != list(IDS)):
        raise ValueError("RUN117BK_FIXTURE_SHAPE_RED")
    for row in data["rows"]:
        if set(row) != {"id", "prior", "current", "policy_span", "option_span", "oracle"}:
            raise ValueError("RUN117BK_FIXTURE_FIELDS_RED")
        p = POLICY.fullmatch(row["policy_span"])
        opts = list(OPTION.finditer(row["option_span"]))
        if (p is None or len(opts) != 2
                or [o[1] for o in opts] != ["A", "B"]
                or row["prior"].count(row["policy_span"]) != 1
                or row["current"].count(row["option_span"]) != 1
                or not row["prior"].startswith("Project " + row["id"])
                or not row["current"].startswith("Project " + row["id"])):
            raise ValueError("RUN117BK_SOURCE_GRAMMAR_RED")
        options = [{"entity": o[1], "cost": int(o[2]), "days": int(o[3]),
                    "local": o[4] == "true"} for o in opts]
        chosen, evaluated = recipe(int(p[1]), int(p[2]), p[3] == "true", options)
        remaining = next((x["remaining"] for x in evaluated
                          if x["entity"] == chosen), None)
        if row["oracle"] != {"choice": chosen, "remaining": remaining}:
            raise ValueError("RUN117BK_ORACLE_RECIPE_RED")
    return data["rows"]


def _pin(installed):
    m = ModelManager(installed)
    if (file_hash(m.path_for("C3_LANGUAGE")) != C3_SHA
            or m.revision("C3_LANGUAGE") != C3_REV
            or file_hash(installed / "bin/llama-server") != RUNNER_SHA):
        raise ValueError("RUN117BK_PINNED_NATIVE_C3_RED")


def _trusted_source_id(runtime, event, role):
    """Deterministic synthetic selector, never a native Body model or oracle prompt."""
    prefix = "Binding policy:" if role == "B2_GIST" else "Option A:"
    def choose(messages):
        if [m["role"] for m in messages] != ["system", "user"]:
            raise ValueError("RUN117BK_SELECTOR_ROLE_RED")
        payload = json.loads(messages[1]["content"])
        candidates = payload["candidates"]
        matched = [c for c in candidates if c["text"].startswith(prefix)]
        if len(matched) != 1:
            raise ValueError("RUN117BK_SELECTOR_AMBIGUOUS_RED")
        return dumps({"span_id": matched[0]["span_id"]})
    result = select(runtime, event, role, choose,
                    operator_opt_in=True, callback_opt_in=True)
    if (result.get("status") != "SHADOW_SOURCE_ID_SELECTED"
            or result.get("selection_correct_shadow") is not True
            or type(result.get("packet_id")) is not str):
        raise ValueError("RUN117BK_TRUSTED_SELECTOR_RED")
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
        raise ValueError("RUN117BK_SOURCE_BRIDGE_RED")
    full = bridge["messages"]
    payload = json.loads(full[1]["content"])
    obs = payload["body_observations"]
    if ([x["role"] for x in obs] != ["B2_GIST", "B1_DETAIL"]
            or obs[0]["exact_source_excerpt"] != row["policy_span"]
            or obs[1]["exact_source_excerpt"] != row["option_span"]
            or payload["typed_jef_candidate"] is not None
            or payload["typed_candidate_authority"] != 0):
        raise ValueError("RUN117BK_SOURCE_OR_TYPED_LEAK_RED")
    system = dict(full[0])
    minimal_text = (
        "Binding policy (exact source):\n" + row["policy_span"]
        + "\nCurrent options (exact source):\n" + row["option_span"]
        + "\nApply only the binding policy. Choose the cheapest eligible "
          "option and give remaining euros. Return only the required JSON.")
    current_text = (
        "Current options (exact source):\n" + row["option_span"]
        + "\nNo binding policy was provided. Do not invent missing "
          "constraints. If insufficient, return NONE with null. Return JSON.")
    minimal = [dict(system), {"role": "user", "content": minimal_text}]
    current_only = [dict(system), {"role": "user", "content": current_text}]
    for messages in (full, minimal, current_only):
        if (len(messages) != 2
                or [m["role"] for m in messages] != ["system", "user"]
                or row["policy_span"] in messages[0]["content"]
                or row["option_span"] in messages[0]["content"]
                or '"oracle"' in messages[1]["content"]
                or '"typed_jef_candidate":{' in messages[1]["content"]):
            raise ValueError("RUN117BK_PROMPT_LEAK_RED")
    if (row["policy_span"] not in minimal_text
            or row["option_span"] not in minimal_text
            or row["policy_span"] in current_text
            or row["option_span"] not in current_text):
        raise ValueError("RUN117BK_MINIMAL_OR_NO_PRIOR_RED")
    return {ARMS[0]: full, ARMS[1]: minimal, ARMS[2]: current_only}, bridge


def _summarize(report):
    scores = {a: 0 for a in ARMS}
    counts = {a: 0 for a in ARMS}
    paired_minimal_correct_full_wrong = 0
    if len(report["rows"]) != 6 or report["native_c3_calls"] != 18:
        return RED
    for i, row in enumerate(report["rows"]):
        if (row["id"] != IDS[i] or row["status"] != "RECORDED"
                or not row["closed_store_ok"] or not row["no_live_output"]
                or len(row["arms"]) != 3):
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
        paired_minimal_correct_full_wrong += int(
            per["MINIMAL_EXACT_SPANS"]["score"]["correct"] == 1
            and per["FULL_SOURCE_PACKET"]["score"]["correct"] == 0)
    report["scores"] = scores
    report["recorded_by_arm"] = counts
    report["paired_minimal_correct_full_wrong"] = paired_minimal_correct_full_wrong
    if any(counts[a] != 6 for a in ARMS):
        return RED
    signal = (scores["MINIMAL_EXACT_SPANS"] >= 4
              and scores["MINIMAL_EXACT_SPANS"] >= scores["FULL_SOURCE_PACKET"] + 2
              and scores["CURRENT_ONLY"] >= 4)
    report["exploratory_minimal_source_signal"] = signal
    return GOOD[0] if signal else GOOD[1]


def run(fixture_path, installed, work, out):
    rows = fixture(fixture_path)
    installed, work, out = Path(installed).resolve(), Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN117BK_FRESH_WORK_OUT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    report = {
        "schema": "v13.run117bk.c3_minimal_exact_native.v1",
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
                order = ARMS[index % 3:] + ARMS[:index % 3]
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
                        expected = row["oracle"] if arm != "CURRENT_ONLY" else {
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
