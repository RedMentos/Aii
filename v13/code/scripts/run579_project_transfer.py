#!/usr/bin/env python3
"""Run579: disjoint exact-source project transfer software ablation (no native models).

Compare an isolated identity-scope baseline with Run576's project-bound scope
through real Runtime SQLite + ToolStep plan/shadow. Designed controls only.
"""
import argparse
from contextlib import nullcontext
import hashlib
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

from v13.runtime import Runtime
from v13.agi import eligibility, hub
from v13.toolstep import ToolStep

OPTIONS = ("Option A: cost 45 euros, duration 7 days, local true. "
           "Option B: cost 55 euros, duration 4 days, local false. "
           "Compute remaining budget and eligibility; choose cheapest eligible.")

# (current_project, earlier_project, budget, deadline, local_only, oracle_action)
CASES = (
    ("Atlas", "Boreal", 61, 8, False, "UNKNOWN"),
    ("Cedar", "Dune", 60, 5, False, "UNKNOWN"),
    ("Ember", "Fjord", 50, 5, False, "UNKNOWN"),
    ("Grove", "Harbor", 60, 8, True, "UNKNOWN"),
    ("Iris", "Juniper", 30, 9, False, "UNKNOWN"),
    ("Kestrel", "Linden", 55, 4, False, "UNKNOWN"),
    ("Maple", "Maple", 61, 8, False, "A"),
    ("Nova", "Nova", 60, 5, False, "B"),
    ("Oak", "Oak", 50, 5, False, "NONE"),
    ("Pine", "Pine", 60, 8, True, "A"),
    ("Quartz", "Quartz", 30, 9, False, "NONE"),
    ("Rowan", "Rowan", 55, 4, False, "B"),
)


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source(case):
    project, earlier, budget, days, local, _ = case
    prior = (f"Project {earlier}. Budget {budget} euros. Deadline {days} days. "
             f"Local-only requirement: {str(local).lower()}.")
    current = f"Project {project}. Apply earlier project rules. " + OPTIONS
    return prior, current


def run_case(case, arm):
    if arm not in ("BASELINE", "SCOPED"):
        raise ValueError("UNKNOWN_ARM")
    prior, current = source(case)
    with tempfile.TemporaryDirectory() as temp:
        runtime = Runtime(Path(temp))
        try:
            runtime.sleep.cycle.set_policy("enabled", "off")
            runtime.cfg["eligibility_reader"] = "fixed"
            runtime.pool.get = Mock(side_effect=AssertionError("NATIVE_MODEL_MUST_NOT_RUN"))
            hub(runtime).tools.enable("eligibility")
            e0 = runtime.store.event(runtime.session, prior)
            with runtime.store.tx() as connection:
                connection.execute(
                    "INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (runtime.session, e0["event_id"], "assistant", "Acknowledged.", "FINAL",
                     json.dumps({"context_source_refs": [e0["source_ref"]]}), 0))
            e1 = runtime.store.event(runtime.session, current)
            scope = (nullcontext() if arm == "SCOPED" else
                     patch.object(eligibility, "scope_earlier",
                                  side_effect=lambda text, history, quotes:
                                      (list(history), list(quotes))))
            with scope:
                step = ToolStep(runtime)
                plan = step.plan(e1, current)
            if plan is None or plan["tool"] != "eligibility":
                raise ValueError("TOOL_PROPOSAL_MISSING")
            shadow = step.shadow(e1, plan)
            if shadow is None or not isinstance(shadow.get("result"), dict):
                raise ValueError("SHADOW_RESULT_MISSING")
            runtime.pool.get.assert_not_called()
            action = shadow["result"]["action"]
            expected = case[-1]
            cross = case[0] != case[1]
            return {"id": case[0], "arm": arm, "cross_project": cross,
                    "history_sha256": sha(prior), "current_sha256": sha(current),
                    "expected": expected, "action": action,
                    "exact": action == expected,
                    "wrong_committed": cross and action in ("A", "B", "NONE")}
        finally:
            runtime.close()


def run_ablation():
    if len(CASES) != 12 or len({c[0] for c in CASES}) != 12:
        raise ValueError("PREREG_CASES_CHANGED")
    rows = [run_case(case, arm) for arm in ("BASELINE", "SCOPED") for case in CASES]
    by_arm = {}
    for arm in ("BASELINE", "SCOPED"):
        subset = [r for r in rows if r["arm"] == arm]
        by_arm[arm] = {
            "n": len(subset), "exact": sum(r["exact"] for r in subset),
            "cross_wrong_committed": sum(r["wrong_committed"] for r in subset),
            "same_project_exact": sum(r["exact"] for r in subset if not r["cross_project"]),
        }
    expected = {"BASELINE": {"n": 12, "exact": 6, "cross_wrong_committed": 6,
                             "same_project_exact": 6},
                "SCOPED": {"n": 12, "exact": 12, "cross_wrong_committed": 0,
                           "same_project_exact": 6}}
    return {"schema": "V13_RUN579_DISJOINT_PROJECT_TRANSFER_SOFTWARE_V1",
            "status": "DESIGNED_CONTROLS_PASS" if by_arm == expected else "DESIGNED_CONTROLS_RED",
            "by_arm": by_arm, "expected_fixed_before_run": expected, "rows": rows,
            "native_executed": False, "model_called": False,
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE", "jepa_weight": 0,
            "redmi_measured": False,
            "claim_limit": "Constructed exact-wording SQLite software ablation only; not native or general semantic transfer"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run_ablation()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.is_symlink():
        raise ValueError("OUTPUT_SYMLINK")
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    print(json.dumps({"status": result["status"], "by_arm": result["by_arm"],
                      "native_executed": False}, sort_keys=True))
    if result["status"] != "DESIGNED_CONTROLS_PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
