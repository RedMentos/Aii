#!/usr/bin/env python3
"""Run115B fresh six-case replication of unchanged Run114B source pipeline.

Scoped module SEED patch only inside run(); original Run114B source, seed947,
scorer and raw evidence remain untouched. Native uses real pinned B1/B2/C3.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from unittest.mock import patch

from v13.common import atomic_write, dumps
from scripts import run114b_jef_b1b2_c3_native as base

FIXTURE_SHA = "21617baf735436af9a388c9be596bf763dc46f8bb394548daa961ad5ec1f57fd"
PARENT_PIPELINE_SHA = "f51ea8745c31082ee87aab98741ddacb01082827bfb00d406958b535131be7d1"
SEED = 971
IDS = ("Lumen", "Boreal", "Coral", "Delta", "Helios", "Nimbus")
ORACLES = (("A", 2), ("B", 10), ("NONE", None),
           ("B", 10), ("A", 20), ("NONE", None))
ARMS = base.ARMS


def fixture(path):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != FIXTURE_SHA:
        raise ValueError("RUN115B_FROZEN_FIXTURE_SHA_RED")
    data = json.loads(raw)
    if (set(data) != {"schema", "seed", "arms", "rows"}
            or data["schema"] != "v13.run115b.jef_b1b2_c3_seed971.v1"
            or type(data["seed"]) is not int or data["seed"] != SEED
            or data["arms"] != list(ARMS)
            or [r.get("id") for r in data["rows"]] != list(IDS)
            or [(r.get("oracle", {}).get("choice"),
                 r.get("oracle", {}).get("remaining"))
                for r in data["rows"]] != list(ORACLES)):
        raise ValueError("RUN115B_FROZEN_COHORT_RED")
    for row in data["rows"]:
        if (set(row) != {"id", "prior", "current", "prior_quote",
                         "current_quote", "oracle"}
                or row["prior_quote"] not in row["prior"]
                or row["current_quote"] not in row["current"]
                or not row["prior"].startswith("Project " + row["id"] + ". ")
                or not row["current"].startswith("Project " + row["id"] + ". ")):
            raise ValueError("RUN115B_FROZEN_SOURCE_RED")
    return data["rows"]


def run(fixture_path, work, out, *, installed=None):
    rows = fixture(fixture_path)
    if sha256(Path(base.__file__).read_bytes()).hexdigest() != PARENT_PIPELINE_SHA:
        raise ValueError("RUN115B_PARENT_PIPELINE_DRIFT_RED")
    work, out = Path(work), Path(out)
    if work.exists() or out.exists():
        raise FileExistsError("RUN115B_FRESH_WORK_AND_REPORT_REQUIRED")
    work.mkdir(parents=True)
    out.mkdir(parents=True)
    native = installed is not None
    installed = Path(installed).resolve() if native else None
    report = {
        "schema": "v13.run115b.jef_replication_native.v1",
        "seed": SEED, "fixture_sha256": FIXTURE_SHA,
        "parent_pipeline_sha256": PARENT_PIPELINE_SHA,
        "status": "INCOMPLETE", "rows": [], "native": native,
        "native_c2": False, "native_jef_model": False,
        "synthetic_body_observers": not native,
        "native_body_calls": 0, "native_c3_calls": 0,
        "scores": {arm: 0 for arm in ARMS},
        "exploratory_replication_signal": False,
        "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "output_committed": False, "tool_dispatches": 0,
        "learning_authority": 0, "delivery_authority": 0,
    }
    path = out / "report.json"
    def save():
        atomic_write(path, dumps(report))
    save()
    try:
        if native:
            base._pin_models(installed)
        with patch.object(base, "SEED", SEED):
            for i, row in enumerate(rows):
                base._run_row(row, i, work, report, save, installed=installed)
        structural = len(report["rows"]) == 6 and all(
            r["status"] == ("RECORDED" if native else "MODEL_FREE_PREFLIGHT_PASS")
            and r["b1_current_verified"] and r["b2_prior_verified"]
            and r["jef_matches_oracle"] is True
            and r["closed_store_ok"] and r["no_live_output"]
            and len(r["offers"]) == 3 and len(r["arms"]) == 2
            for r in report["rows"])
        if not structural:
            report["status"] = "STRUCTURAL_RED"
        elif not native:
            report["status"] = "MODEL_FREE_SIX_PROJECT_PREFLIGHT_PASS"
        else:
            for row in report["rows"]:
                for arm in row["arms"]:
                    report["scores"][arm["arm"]] += arm["score"]["correct"]
            report["exploratory_replication_signal"] = (
                report["scores"]["TYPED_JEF"] >= 5 and
                report["scores"]["TYPED_JEF"] >=
                report["scores"]["RAW_BODY"] + 2)
            report["status"] = (
                "NATIVE_COMPLETE_REPLICATION_SIGNAL"
                if report["exploratory_replication_signal"]
                else "NATIVE_COMPLETE_NO_REPLICATION_SIGNAL")
    except Exception as exc:
        report["status"] = "STRUCTURAL_RED"
        report["error_type"] = type(exc).__name__
        report["error"] = str(exc)[:320]
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fixture", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--installed", type=Path)
    a = p.parse_args()
    r = run(a.fixture, a.work, a.out, installed=a.installed)
    print(dumps({"status": r["status"], "rows": len(r["rows"]),
                 "native_body_calls": r["native_body_calls"],
                 "native_c3_calls": r["native_c3_calls"],
                 "scores": r["scores"],
                 "replication_signal": r["exploratory_replication_signal"]}))
    return 0 if r["status"] in (
        "MODEL_FREE_SIX_PROJECT_PREFLIGHT_PASS",
        "NATIVE_COMPLETE_REPLICATION_SIGNAL",
        "NATIVE_COMPLETE_NO_REPLICATION_SIGNAL") else 2


if __name__ == "__main__":
    raise SystemExit(main())
