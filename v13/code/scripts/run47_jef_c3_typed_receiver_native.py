#!/usr/bin/env python3
"""Run47 seed409 real Linux-native C3 receiver fidelity for typed JEF source SHADOW."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from v13.common import atomic_write, dumps
from v13.config import DEFAULTS, initialize, save_config
from v13.runtime import Runtime
from v13.agi.jef_eligibility_source_shadow_run46b import propose
from tests.integration_step2_utility import installed_artifacts, installed_links

FIXTURE_SHA256 = "4015600687c392d7c36d17eeb289ad68fd958222d07bd87b4d7f60df0a8b0fad"
ARMS = ("A_RAW_SOURCES", "B_JEF_TYPED_CANDIDATE")
ORDER = (ARMS, ARMS[::-1], ARMS, ARMS[::-1], ARMS, ARMS[::-1])
SYS_A = ("Use only the exact prior and current user sources. Apply the binding earlier "
         "project rules and select the cheapest eligible option. Return only JSON "
         "with choice and remaining. For NONE or UNKNOWN use null remaining.")
SYS_B = ("You are a JSON formatter, not a decision maker. Copy the supplied "
         "source-verified typed JEF candidate's choice and remaining exactly. "
         "Do not recalculate or change it. Return only those two JSON keys.")
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["choice", "remaining"],
          "properties": {"choice": {"type": "string", "enum": ["A", "B", "NONE", "UNKNOWN"]},
                         "remaining": {"type": ["integer", "null"]}}}
CONFIG = DEFAULTS | {"threads": 2, "temperature": 0., "seed": 13,
                     "observer_mode": "off", "answer_tokens": 96,
                     "deadline_seconds": 120, "observer_seconds": 30,
                     "body_residency_mb": 0, "history_turns": 0,
                     "memory_top_k": 0, "teacher_enabled": False,
                     "learning_mode": "RECORD_ONLY"}
NEGATIVE = {"age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "world_jepa_authority": "SHADOW",
            "redmi_measured": False, "whole_system_complete": False}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_fixture(path):
    raw = Path(path).read_bytes()
    if sha(raw) != FIXTURE_SHA256:
        raise ValueError("RUN47_FROZEN_FIXTURE_SHA")
    data = json.loads(raw)
    if (data.get("schema") != "v13.run47.jef_c3_typed_receiver_seed409.v1"
            or data.get("seed") != 409 or data.get("arms") != list(ARMS)
            or [x["id"] for x in data.get("fixtures", [])]
            != ["Aster", "Birch", "Cobalt", "Dune", "Eclipse", "Fjord"]):
        raise ValueError("RUN47_FROZEN_COHORT")
    for f in data["fixtures"]:
        if (set(f) != {"id", "prior", "current", "oracle"}
                or not f["prior"].startswith("Project " + f["id"] + ".")
                or not f["current"].startswith("Project " + f["id"] + ".")
                or set(f["oracle"]) != {"choice", "remaining"}):
            raise ValueError("RUN47_FIXTURE_SHAPE")
    return data


def messages(arm, fixture, jef=None):
    if arm not in ARMS:
        raise ValueError("RUN47_ARM")
    if arm == ARMS[0]:
        payload = {"prior_source": fixture["prior"], "current_source": fixture["current"]}
        sys = SYS_A
    else:
        if (type(jef) is not dict or jef.get("reason") != "EXACT_USER_SOURCE_RECIPE_SHADOW"
                or jef.get("status") != "SHADOW_NO_AUTHORITY"
                or jef.get("authority") != 0 or jef.get("model_called") is not False
                or type(jef.get("candidate")) is not dict
                or set(jef["candidate"]) != {"choice", "remaining"}
                or len(jef.get("source_ref_sha256", [])) != 2):
            raise ValueError("RUN47_JEF_SOURCE_SHADOW_REQUIRED")
        payload = {"current_source": fixture["current"],
                   "typed_jef_candidate": jef["candidate"],
                   "source_ref_sha256": jef["source_ref_sha256"],
                   "candidate_authority": 0}
        sys = SYS_B
    out = [{"role": "system", "content": sys},
           {"role": "user", "content": dumps(payload)}]
    if '"oracle"' in dumps(out):
        raise ValueError("RUN47_ORACLE_LEAK")
    return out


def _unique(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("RUN47_DUPLICATE_JSON")
        out[key] = value
    return out


def _nonfinite(_):
    raise ValueError("RUN47_NONFINITE")


def score(raw, oracle):
    try:
        v = json.loads(raw, object_pairs_hook=_unique, parse_constant=_nonfinite)
        valid = (type(v) is dict and set(v) == {"choice", "remaining"}
                 and type(v["choice"]) is str
                 and v["choice"] in ("A", "B", "NONE", "UNKNOWN")
                 and (v["remaining"] is None or type(v["remaining"]) is int))
        return {"correct": int(valid and v == oracle), "valid_json": bool(valid),
                "parsed": v if valid else None}
    except (ValueError, TypeError, OverflowError):
        return {"correct": 0, "valid_json": False, "parsed": None}


def summarize(rows):
    out = {arm: {"rows": 0, "correct": 0, "structural": 0} for arm in ARMS}
    for row in rows:
        a = out[row["arm"]]
        a["rows"] += 1
        a["correct"] += row["score"]["correct"]
        a["structural"] += int(row["status"] == "RECORDED")
    return out


def signal(summary):
    return (all(summary[a]["rows"] == 6 and summary[a]["structural"] == 6 for a in ARMS)
            and summary[ARMS[1]]["correct"] >= 5
            and summary[ARMS[1]]["correct"] >= summary[ARMS[0]]["correct"] + 2)


def run_row(home, installed, fixture, arm):
    initialize(home)
    save_config(home, CONFIG)
    installed_links(home, installed)
    r = Runtime(home)
    row = {"fixture": fixture["id"], "arm": arm, "status": "ERROR",
           "prior_sha256": sha(fixture["prior"].encode("utf-8")),
           "current_sha256": sha(fixture["current"].encode("utf-8")),
           "oracle_visible_to_native": False,
           "native_answer": "", "native_c3_final": False,
           "process_releases": [], "processes_reaped": False,
           "score": {"correct": 0, "valid_json": False, "parsed": None}}
    start = time.monotonic()
    try:
        prior = r.store.event(r.session, fixture["prior"])
        current = r.store.event(r.session, fixture["current"])
        row["prior_source_ref"] = prior["source_ref"]
        row["current_source_ref"] = current["source_ref"]
        jef = propose(r.store, prior["source_ref"], current["source_ref"]) if arm == ARMS[1] else None
        if jef is not None:
            row["jef_candidate"] = jef
        msgs = messages(arm, fixture, jef)
        row["native_prompt"] = msgs
        row["native_prompt_sha256"] = sha(dumps(msgs).encode("utf-8"))
        runner = r.pool.get("C3_LANGUAGE")
        row["native_answer"] = "".join(runner.generate(
            msgs, r.cancel_event, time.monotonic() + 90, 96, SCHEMA, seed=13))
        row["native_c3_metrics"] = dict(runner.last_metrics)
        row["native_c3_final"] = runner.last_metrics.get("status") == "FINAL"
        r.pool.unload()
        row["score"] = score(row["native_answer"], fixture["oracle"])
        if arm == ARMS[1]:
            row["jef_matches_oracle"] = jef["candidate"] == fixture["oracle"]
        row["status"] = ("RECORDED" if row["native_c3_final"]
                         and (arm == ARMS[0] or row.get("jef_matches_oracle") is True)
                         else "STRUCTURAL_FAIL")
    except (Exception, KeyboardInterrupt) as exc:
        row["error_type"] = type(exc).__name__
        row["error"] = str(exc)[:500]
        row["status"] = "INTERRUPTED" if isinstance(exc, KeyboardInterrupt) else "ERROR"
    finally:
        try:
            r.close()
        except Exception as exc:
            row["close_error_type"] = type(exc).__name__
            row["status"] = "STRUCTURAL_FAIL"
        row["process_releases"] = list(r.pool.release_history)
        row["processes_reaped"] = bool(row["process_releases"]) and all(
            x.get("process_reaped") is True for x in row["process_releases"])
        if row["status"] == "RECORDED" and not row["processes_reaped"]:
            row["status"] = "STRUCTURAL_FAIL"
        if row["status"] != "RECORDED":
            row["score"]["correct"] = 0
        row["elapsed_seconds"] = round(time.monotonic() - start, 3)
    return row


def run(installed, out, fixture_path):
    fixture = load_fixture(fixture_path)
    if out.exists():
        raise FileExistsError("RUN47_OUTPUT_EXISTS")
    out.mkdir(parents=True)
    binding = installed_artifacts(installed)
    report = {"schema": "v13.run47.jef_c3_native_receiver_result.v1",
              "fixture_sha256": FIXTURE_SHA256, "seed": 409,
              "binding": binding, "registered": True, "rows": [],
              "row_sha256": {}, "status": "RUNNING",
              "negative_gates": NEGATIVE}
    atomic_write(out / "report.json", dumps(report))
    for f, order in zip(fixture["fixtures"], ORDER):
        for arm in order:
            home = out / (f["id"] + "-" + arm)
            if home.exists():
                raise FileExistsError("RUN47_HOME_EXISTS")
            row = run_row(home, installed, f, arm)
            report["rows"].append(row)
            report["row_sha256"][f["id"] + "/" + arm] = sha(dumps(row).encode("utf-8"))
            report["summary"] = summarize(report["rows"])
            atomic_write(out / "report.json", dumps(report))
            print(dumps({"fixture": f["id"], "arm": arm,
                         "status": row["status"], "correct": row["score"]["correct"]}), flush=True)
    report["installed_binding_unchanged"] = installed_artifacts(installed) == binding
    report["receiver_copy_signal"] = signal(report["summary"]) and report["installed_binding_unchanged"]
    report["status"] = ("RECEIVER_COPY_SIGNAL_ONLY" if report["receiver_copy_signal"]
                        else "UTILITY_FAIL" if all(r["status"] == "RECORDED" for r in report["rows"])
                        else "STRUCTURAL_RED")
    atomic_write(out / "report.json", dumps(report))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--fixture", type=Path, required=True)
    args = p.parse_args()
    report = run(args.home, args.out, args.fixture)
    print(dumps({"status": report["status"], "summary": report["summary"],
                 "receiver_copy_signal": report["receiver_copy_signal"]}))


if __name__ == "__main__":
    main()
