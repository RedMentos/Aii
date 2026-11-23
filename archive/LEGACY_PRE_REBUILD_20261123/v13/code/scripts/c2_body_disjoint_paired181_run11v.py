"""Run11V disjoint seed181 C2/C3/Body post-close, observer-isolated native pilot.

This is a review-only Age0 experiment. Frozen scorers swap report slots only; no original cohort, scorer, model or
production gate is changed. Invalid rows are retained and score zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import time
import traceback

from v13.cognition import scaffold_route
from v13.config import initialize, save_config
from v13.models import ModelManager, model_key
from v13.proofs import audit_event
from v13.runtime import Runtime
from scripts.c2_c3_body_source_arithmetic_shadow_run11q import score_option
from scripts.step2_paired_raw_validator_audit_20261030 import semantic_diagnostic
from scripts.step2_expression_diagnostic_20261030 import equation_diagnostic
from scripts.c2_native_route_provenance_20261030 import valid_control_evidence

SCHEMA = "v13.c2_body.disjoint.seed181.v1"
SEED = 181
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "D_DISTINCT_BOTH",
        "E_SHARED_DUAL_COLD", "F_NATIVE_AUTO")
ARM_ORDER = tuple(ARMS[i:] + ARMS[:i] for i in range(4))
FIXTURES = (
    {"project": "Aurora181", "budget": 396, "a": "Fern", "a_cost": 243, "a_days": 7,
     "b": "Slate", "b_cost": 352, "b_days": 3},
    {"project": "Beacon181", "budget": 274, "a": "Aspen", "a_cost": 189, "a_days": 2,
     "b": "Coral", "b_cost": 241, "b_days": 6},
    {"project": "Cobalt181", "budget": 458, "a": "Willow", "a_cost": 317, "a_days": 8,
     "b": "Topaz", "b_cost": 404, "b_days": 4},
    {"project": "Delta181", "budget": 335, "a": "Harbor", "a_cost": 256, "a_days": 5,
     "b": "Quartz", "b_cost": 297, "b_days": 9},
)
FIXTURE_SHA256 = "ae4799f60316cf51412d228547662de8cb4b6523dedffd5fc02b2862d84477e3"
ROUTES = {"A_C3_ONLY": "simple", "B_B1_ONLY": "detail",
          "C_B2_ONLY": "gist", "D_DISTINCT_BOTH": "both",
          "E_SHARED_DUAL_COLD": "both", "F_NATIVE_AUTO": "auto"}
ROLE_BY_ROUTE = {"simple": ("C3_LANGUAGE",), "detail": ("B1_DETAIL",),
                 "gist": ("B2_GIST",), "both": ("B1_DETAIL", "B2_GIST")}
BODY_MODEL = "LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf"
LANGUAGE_MODEL = "LFM2.5-350M-QAD-Q4_0.gguf"
GIST_MODEL = "Qwen3.5-0.8B-Q4_0.gguf"


def fixture_hash():
    return hashlib.sha256(json.dumps(FIXTURES, sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()


def prompt(f):
    """Identical simple-scaffold source in all six arms; no remainder leak."""
    return (f"For {f['project']}, I have a spending ceiling of {f['budget']} Euro. "
            f"{f['a']} uses {f['a_cost']} Euro and needs {f['a_days']} days. "
            f"{f['b']} uses {f['b_cost']} Euro and needs {f['b_days']} days. "
            "Everything stays local on my device; no cloud. How many Euro "
            "would remain after each named choice, and which one finishes sooner?")


def validate_fixtures():
    if fixture_hash() != FIXTURE_SHA256 or len(FIXTURES) != 4:
        raise ValueError("FIXTURE_PIN_CHANGED")
    if len({f["project"] for f in FIXTURES}) != 4:
        raise ValueError("DUPLICATE_PROJECT")
    if len(ARMS) != 6 or len(set(ARMS)) != 6:
        raise ValueError("ARM_IDENTITY_RED")
    for f in FIXTURES:
        if not (0 < f["a_cost"] < f["budget"]
                and 0 < f["b_cost"] < f["budget"]
                and f["a"] != f["b"] and f["a_days"] != f["b_days"]):
            raise ValueError("INVALID_FIXTURE")
        if scaffold_route(prompt(f)) != "simple":
            raise ValueError("SCAFFOLD_NOT_SIMPLE")
        for remainder in (f["budget"] - f["a_cost"], f["budget"] - f["b_cost"]):
            if re.search(rf"(?<!\d){remainder}(?!\d)", prompt(f)):
                raise ValueError("ANSWER_LEAKED_IN_SOURCE")
    return True


def score_pair(fixture, answer):
    """Two source-bound points, with contradiction veto across both frozen parsers."""
    lexical = semantic_diagnostic(fixture, answer)
    equation = equation_diagnostic(fixture, answer)
    scores = {}
    for key in ("a", "b"):
        l = lexical[key]["status"]
        e = equation[key]["status"]
        # A correct equation must not override a contradictory lexical claim;
        # a correct lexical claim must not override a bad equation.
        scores[key] = bool((l == "CORRECT" and e in ("CORRECT", "MISSING"))
                           or (e == "CORRECT" and l in ("CORRECT", "MISSING")))
    return {"a": scores["a"], "b": scores["b"],
            "correct": int(scores["a"]) + int(scores["b"]), "out_of": 2,
            "lexical": lexical, "equation": equation}


def score_primary(fixture, answer):
    """Frozen Run11Q narrow source-bound claim scorer; no authority."""
    scores = {key: score_option(fixture, answer, key) for key in ("a", "b")}
    return {"a": scores["a"]["status"] == "MATCH",
            "b": scores["b"]["status"] == "MATCH",
            "correct": sum(scores[k]["status"] == "MATCH" for k in ("a", "b")),
            "out_of": 2, "source_bound": scores}


def pilot_signal(totals, valid):
    if type(valid) is not bool or type(totals) is not dict or set(totals) != set(ARMS):
        return False
    if any(type(x) is not int or not 0 <= x <= 8 for x in totals.values()):
        return False
    return bool(valid and totals["D_DISTINCT_BOTH"] >=
                max(totals[k] for k in ARMS[:3]) + 2 and
                totals["D_DISTINCT_BOTH"] >= totals["E_SHARED_DUAL_COLD"] + 2)


def expected_roles(route):
    if route not in ROLE_BY_ROUTE:
        raise ValueError("UNKNOWN_ROUTE")
    return set(ROLE_BY_ROUTE[route]) - {"C3_LANGUAGE"}


def row_evidence(audit, arm, releases, native_context=None, native_alive=False,
                 native_reaped=False, native_pid=None, source_exact=False,
                 session=None, event_id=None, source_text=None,
                 release_capture_phase="after_close"):
    """Fail-closed source/role/observer/release check; never C2 authority."""
    if arm not in ARMS:
        raise ValueError("UNKNOWN_ARM")
    meta = audit.get("output_metadata") if isinstance(audit, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    route_info = meta.get("route") if isinstance(meta.get("route"), dict) else {}
    c2 = meta.get("c2_packet") if isinstance(meta.get("c2_packet"), dict) else {}
    route = c2.get("route")
    runner = meta.get("runner") if isinstance(meta.get("runner"), dict) else {}
    checks = audit.get("checks") if isinstance(audit, dict) else None
    checks_valid = bool(isinstance(checks, dict) and checks
                        and all(v is True for v in checks.values())
                        and audit.get("source_errors") == [])
    offers = {p.get("role") for p in audit.get("offers", [])
              if isinstance(p, dict)} if isinstance(audit, dict) else set()
    native = False
    if arm == "F_NATIVE_AUTO" and isinstance(native_context, dict):
        e = {"event_id": event_id, "session_id": session,
             "source_ref": native_context.get("query_ref")}
        metrics = route_info.get("native_control_metrics") or {}
        memory = metrics.get("memory") if isinstance(metrics, dict) else {}
        memory = memory if isinstance(memory, dict) else {}
        native = bool(source_exact and native_alive and native_reaped
                      and type(native_pid) is int and native_pid == memory.get("pid")
                      and valid_control_evidence(e, source_text, route, route_info,
                                                 context_packet=native_context))
    selected = bool(native and route_info.get("source") == "NATIVE_C2_ADVISORY"
                    and route != "simple")
    route_ok = (route == ROUTES[arm]
                and route_info == {"source": "OPERATOR_ROUTE_OVERRIDE"}) if arm != "F_NATIVE_AUTO" else (
                    native and route in ROLE_BY_ROUTE
                    and route_info.get("source") in ("BOOT_SCAFFOLD", "NATIVE_C2_ADVISORY"))
    required = expected_roles(route) if route in ROLE_BY_ROUTE else set()
    # Observer OFF on single-organ arms: zero offers, but the final Body
    # runner must still be the requested native role and be reaped on close.
    single = arm in ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY")
    expected_offers = set() if single else required
    final_role = runner.get("role")
    expected_final = ROLE_BY_ROUTE.get(route, ())
    final_model = runner.get("actual_model")
    expected_model = (LANGUAGE_MODEL if final_role == "C3_LANGUAGE"
                      else GIST_MODEL if final_role == "B2_GIST"
                      and arm != "E_SHARED_DUAL_COLD" else BODY_MODEL)
    role_valid = final_role in expected_final and final_model == expected_model
    runner_releases = [r for r in releases if isinstance(r, dict)
                       and r.get("role") in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST")]
    release_roles = {r["role"] for r in runner_releases}
    # Final C3 must be reaped too; an empty list must NEVER count as proof.
    expected_releases = ({final_role} if single else
                         required | ({"C3_LANGUAGE"} if final_role == "C3_LANGUAGE" else set()))
    released = bool(release_capture_phase == "after_close"
                    and offers == expected_offers
                    and release_roles == expected_releases
                    and len(runner_releases) >= len(expected_releases)
                    and all(r.get("process_reaped") is True for r in runner_releases))
    output = bool(checks_valid and meta.get("model_generated") is True
                  and isinstance(audit.get("output"), str)
                  and audit["output"].strip() and role_valid)
    valid = bool(route_ok and released and output)
    return {"valid_native": valid, "route_valid": bool(route_ok),
            "native_c2_invocation": native, "native_c2_selected": selected,
            "source_exact": bool(source_exact) if arm == "F_NATIVE_AUTO" else checks_valid,
            "body_offer_roles": sorted(offers),
            "expected_offer_roles": sorted(expected_offers),
            "process_release_valid": bool(released),
            "release_capture_phase": release_capture_phase,
            "output_valid": output, "runner_role": final_role,
            "runner_model": final_model, "route": route,
            "route_source": route_info.get("source")}




def fresh_turn(base_home, base_cfg, fixture, arm, index, out):
    text = prompt(fixture)
    with tempfile.TemporaryDirectory(dir=base_home / "tmp", prefix="c2-body-seed181-") as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode="RECORD_ONLY", system_stage=0, user_stage_cap=0,
                   teacher_enabled=False, latents_enabled=False, jepa_weight=0,
                   seed=SEED, history_turns=0, route_override=ROUTES[arm],
                   observer_mode=("off" if arm in ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY")
                                  else "background"),
                   b2_control=("shared_body_dual_state" if arm == "E_SHARED_DUAL_COLD"
                               else "two_body"), control_seconds=20.0)
        save_config(home, cfg)
        for name in ("models", "bin"):
            shutil.rmtree(home / name)
            (home / name).symlink_to(base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / "config/models.json", home / "config/models.json")
        runtime = Runtime(home)
        if runtime.models.b2_control != cfg["b2_control"]:
            runtime.close()
            raise ValueError("B2_CONTROL_CONFIG_MISMATCH")
        b1_key = model_key("B1_DETAIL", runtime.models.b2_control)
        b2_key = model_key("B2_GIST", runtime.models.b2_control)
        if ((arm == "D_DISTINCT_BOTH" and b1_key == b2_key)
                or (arm == "E_SHARED_DUAL_COLD" and b1_key != b2_key)):
            runtime.close()
            raise ValueError("BODY_MODEL_IDENTITY_MISMATCH")
        record = None
        needle_proc = None
        preclose_releases = []
        try:
            if arm == "A_C3_ONLY":
                runtime.models.installed.pop("body", None)
                runtime.models.installed.pop("gist", None)
                runtime.models.save()
            event_id = runtime.submit(text)
            end = time.monotonic() + runtime.cfg["deadline_seconds"] + 2 * runtime.cfg["observer_seconds"] + 15
            while not runtime.idle():
                if time.monotonic() > end:
                    runtime.cancel()
                    raise TimeoutError("NATIVE_CONTROLLED_TURN_DEADLINE")
                time.sleep(.05)
            audit = audit_event(runtime.store, event_id)
            meta = audit.get("output_metadata") or {}
            route_info = meta.get("route") or {}
            context_id = route_info.get("executive_control_context_id")
            row = (runtime.store.one("SELECT payload FROM packets WHERE id=? AND kind='ExecutiveControlContext'",
                                     (context_id,)) if context_id else None)
            context = json.loads(row["payload"]) if row else None
            source_exact = bool(context and runtime.store.read_source(context["query_ref"]) == text)
            needle_proc = runtime.needle.proc
            needle_alive = needle_proc is not None and needle_proc.poll() is None
            preclose_releases = list(runtime.pool.release_history)
            record = {"index": index, "fixture": fixture["project"], "arm": arm,
                      "prompt": text, "event_id": event_id, "session_id": runtime.session,
                      "route_info": route_info, "context_packet": context,
                      "b2_control": runtime.models.b2_control,
                      "b1_model_key": model_key("B1_DETAIL", runtime.models.b2_control),
                      "b2_model_key": model_key("B2_GIST", runtime.models.b2_control),
                      "b1_revision": runtime.models.revision("B1_DETAIL"),
                      "b2_revision": runtime.models.revision("B2_GIST"),
                      "raw_audit": audit,
                      "body_process_releases_before_close": preclose_releases,
                      "final_output": audit.get("output", ""), "learning_mode": "RECORD_ONLY",
                      "jepa_weight": 0, "step2_gate_promoted": False,
                      "b3_promoted": False, "body_jepa_available": False,
                      "redmi_measured": False, "whole_system_complete": False,
                      "native_c2_alive_before_close": needle_alive,
                      "source_exact_before_close": source_exact}
        finally:
            # Persist original pre-close audit before risky finalization.
            # If close raises, run() keeps a RED row and this witness.
            if record is not None:
                (out / "preclose" / f"{index:02d}_{arm}.json").write_text(
                    json.dumps(record, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + "\n")
            runtime.close()
        if record is None:
            raise ValueError("MISSING_NATIVE_ROW")
        # Capture final runner releases only AFTER Runtime.close(), unlike seed59.
        record["body_process_releases"] = list(runtime.pool.release_history)
        record["release_capture_phase"] = "after_close"
        reaped = bool(needle_proc is not None and needle_proc.poll() is not None)
        record["native_c2_process_reaped"] = reaped
        record["native_c2_pid"] = needle_proc.pid if needle_proc is not None else None
        flags = row_evidence(record["raw_audit"], arm, record["body_process_releases"],
                             native_context=record["context_packet"],
                             native_alive=record["native_c2_alive_before_close"],
                             native_reaped=reaped, native_pid=record["native_c2_pid"],
                             source_exact=record["source_exact_before_close"],
                             session=record["session_id"], event_id=record["event_id"],
                             source_text=text,
                             release_capture_phase=record["release_capture_phase"])
        record["flags"] = flags
        record["score"] = (score_pair(fixture, record["final_output"])
                           if flags["valid_native"] else {"a": False, "b": False,
                                                         "correct": 0, "out_of": 2})
        record["secondary_score"] = (score_primary(fixture, record["final_output"])
                                     if flags["valid_native"] else {"a": False, "b": False,
                                                                   "correct": 0, "out_of": 2})
        (out / "raw" / f"{index:02d}_{arm}.json").write_text(
            json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
        return {k: v for k, v in record.items() if k not in ("raw_audit", "context_packet", "prompt", "route_info")}


def run(base_home, out):
    base_home, out = Path(base_home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_DIRECTORY_REQUIRED")
    validate_fixtures()
    out.mkdir(parents=True)
    (out / "raw").mkdir()
    (out / "preclose").mkdir()
    report = {"schema": SCHEMA, "status": "INCOMPLETE", "seed": SEED,
              "fixture_sha256": FIXTURE_SHA256, "fixtures": FIXTURES,
              "arms": ARMS, "arm_order": ARM_ORDER, "rows": [],
              "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
              "step2_gate_promoted": False, "b3_promoted": False,
              "body_jepa_available": False, "redmi_measured": False,
              "whole_system_complete": False, "comparative_utility_proven": False,
              "claim_limit": "24-turn observer-isolated post-close Linux-native pilot; no STEP2 gate"}
    try:
        cfg = initialize(base_home)
        if (cfg["learning_mode"] != "RECORD_ONLY" or cfg["system_stage"] != 0
                or cfg["latents_enabled"] or cfg.get("jepa_weight", 0) != 0):
            raise ValueError("BASE_NOT_AGE0")
        verified = ModelManager(base_home).verify(deep=True)
        roles = ("needle", "language", "body", "gist")
        if not all(verified.get(k, {}).get("ok") is True
                   and verified[k].get("hash_checked") is True for k in roles):
            raise ValueError("MODEL_PINS_UNVERIFIED")
        report["model_verification"] = {
            k: {"ok": verified[k]["ok"], "hash_checked": verified[k]["hash_checked"]}
            for k in roles}
        for i, fixture in enumerate(FIXTURES):
            for arm in ARM_ORDER[i]:
                index = len(report["rows"])
                try:
                    row = fresh_turn(base_home, cfg, fixture, arm, index, out)
                except BaseException as exc:
                    traceback.print_exc()
                    row = {"index": index, "fixture": fixture["project"], "arm": arm,
                           "error_type": type(exc).__name__, "error": str(exc)[:320],
                           "flags": {"valid_native": False, "native_c2_invocation": False,
                                     "native_c2_selected": False},
                           "score": {"a": False, "b": False, "correct": 0, "out_of": 2}}
                    (out / "raw" / f"{index:02d}_{arm}.json").write_text(
                        json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")
                report["rows"].append(row)
                (out / "progress.json").write_text(
                    json.dumps(report, indent=2, sort_keys=True,
                               ensure_ascii=False, allow_nan=False) + "\n")
        totals = {arm: sum(row["score"]["correct"] for row in report["rows"]
                           if row["arm"] == arm) for arm in ARMS}
        valid = len(report["rows"]) == 24 and all(
            row["flags"].get("valid_native") is True for row in report["rows"])
        report["score_totals_out_of_8"] = totals
        report["secondary_totals_out_of_8"] = {arm: sum(row["secondary_score"]["correct"]
            for row in report["rows"] if row["arm"] == arm and "secondary_score" in row)
            for arm in ARMS}
        report["pilot_signal_not_gate"] = pilot_signal(totals, valid)
        report["native_auto_signal_not_gate"] = bool(valid and
            sum(bool(row["flags"].get("native_c2_selected")) for row in report["rows"]
                if row["arm"] == "F_NATIVE_AUTO") >= 1 and
            totals["F_NATIVE_AUTO"] >= totals["A_C3_ONLY"] + 2)
        report["native_c2_invocations"] = sum(
            bool(row["flags"].get("native_c2_invocation")) for row in report["rows"])
        report["native_c2_selected"] = sum(
            bool(row["flags"].get("native_c2_selected")) for row in report["rows"])
        report["status"] = "PILOT_COMPLETE_NO_GATE" if valid else "PILOT_PARTIAL_RED"
    except BaseException as exc:
        traceback.print_exc()
        report.update(status="PILOT_ERROR", error_type=type(exc).__name__,
                      error=str(exc)[:320])
    finally:
        (out / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True,
                       ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"status": report["status"],
                      "score_totals_out_of_8": report.get("score_totals_out_of_8"),
                      "pilot_signal_not_gate": report.get("pilot_signal_not_gate", False),
                      "native_auto_signal_not_gate": report.get("native_auto_signal_not_gate", False),
                      "native_c2_selected": report.get("native_c2_selected", 0)},
                     sort_keys=True))
    return report["status"] == "PILOT_COMPLETE_NO_GATE"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    return 0 if run(args.home, args.out) else 2


if __name__ == "__main__":
    raise SystemExit(main())
