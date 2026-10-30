"""Run12L read-only C2 route-label proxy scorer.

Reference labels are synthetic role proxies, NOT answer truth or semantic utility.
No learner, runtime mutation, C3/Body call, or gate promotion.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

SCHEMA = "v13.c2.route_agreement_proxy.run12l.v1"
FIXTURE_SCHEMA = "v13.c2.route_agreement_proxy.run12l.fixture.v1"
FIXTURE_SHA256 = "9d65d64ffeca0291b27809b572696c27c74c45ac0df9975e3aceda4ee24181dd"
PROMPTS_SHA256 = "ecf13d17b7be4f8516d4c193d2e8bef05f6d0c5e5577985f64e73cd9f2252655"
ROUTES = frozenset(("simple", "detail", "gist", "both"))


def canonical_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_fixture(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (canonical_sha(data) != FIXTURE_SHA256
            or data.get("schema") != FIXTURE_SCHEMA
            or data.get("seed") != 43
            or type(data.get("cases")) is not list
            or len(data["cases"]) != 15):
        raise ValueError("RUN12L_FROZEN_FIXTURE_MISMATCH")
    cases = data["cases"]
    if (any(type(c) is not dict or type(c.get("prompt")) is not str
            or not c["prompt"] or c.get("reference_route") not in ROUTES
            or c.get("expected_scaffold") not in ROUTES for c in cases)
            or len({c["prompt"] for c in cases}) != 15
            or canonical_sha(tuple(c["prompt"] for c in cases)) != PROMPTS_SHA256
            or any(c["expected_scaffold"] != "simple" for c in cases[:12])
            or [c["expected_scaffold"] for c in cases[12:]]
               != ["detail", "gist", "both"]):
        raise ValueError("RUN12L_FROZEN_CASES_MISMATCH")
    return data


def score(fixture, rows):
    """Conservative complete-case scorer; missing/failed raw never passes."""
    cases = fixture["cases"]
    records = []
    for i, case in enumerate(cases):
        row = rows[i] if i < len(rows) and type(rows[i]) is dict else {}
        info = row.get("route_info")
        info = info if type(info) is dict else {}
        strict = row.get("strict_admission")
        strict = strict if type(strict) is dict else {}
        prompt_ok = (row.get("index") == i and
                     row.get("prompt") == case["prompt"])
        scaffold_ok = info.get("scaffold") == case["expected_scaffold"]
        source_ok = (row.get("source_exact") is True and
                     row.get("no_live_answer") is True and
                     row.get("c3_called") is False and
                     row.get("body_called") is False and
                     row.get("jepa_weight") == 0)
        native_ok = (row.get("native_c2_invocation_valid_before_release") is True
                     and row.get("needle_process_reaped") is True)
        strict_ok = (strict.get("matches") is True
                     and strict.get("scaffold") == case["expected_scaffold"]
                     and strict.get("selected") is
                         (info.get("source") == "NATIVE_C2_ADVISORY"))
        selected = info.get("source") == "NATIVE_C2_ADVISORY"
        candidate = row.get("route")
        final_route = candidate if type(candidate) is str and candidate in ROUTES else None
        # No silent acceptance of an invalid or unbound source as utility.
        valid = bool(prompt_ok and scaffold_ok and source_ok and
                     native_ok and strict_ok and final_route is not None)
        records.append({
            "index": i, "prompt": case["prompt"],
            "reference_route": case["reference_route"],
            "scaffold": case["expected_scaffold"],
            "final_route": final_route, "native_selected": selected,
            "source_exact": source_ok, "prompt_bound": prompt_ok,
            "native_proven": native_ok,
            "strict_match": strict_ok, "case_valid": valid,
            "scaffold_correct": case["expected_scaffold"] == case["reference_route"],
            "final_correct": bool(valid and final_route == case["reference_route"]),
        })
    native_proven = (len(rows) == 15 and all(
        r["native_proven"] and r["source_exact"] and r["prompt_bound"]
        for r in records))
    strict_compatibility = (native_proven and all(
        r["case_valid"] for r in records))
    non_simple_preserved = (strict_compatibility and all(
        not r["native_selected"] and r["final_route"] == r["scaffold"]
        for r in records[12:]))
    structural = native_proven and strict_compatibility and non_simple_preserved
    first = records[:12]
    scaffold_correct = sum(r["scaffold_correct"] for r in first)
    final_correct = sum(r["final_correct"] for r in first)
    native_admissions = sum(r["native_selected"] for r in first)
    greeting_regressions = sum(r["scaffold_correct"] and not r["final_correct"]
                               for r in first[:4])
    net_gain = final_correct - scaffold_correct
    proxy_threshold = bool(structural and native_admissions >= 3
                           and net_gain >= 2 and greeting_regressions == 0)
    return {
        "schema": SCHEMA, "status": (
            "NATIVE_ROUTE_PROXY_THRESHOLD_MET_NO_UTILITY_PROOF" if proxy_threshold
            else "NATIVE_ROUTE_PROXY_RED_NO_UTILITY_PROOF"),
        "case_count": len(rows), "native_c2_proven": bool(native_proven),
        "strict_compatibility": bool(strict_compatibility),
        "non_simple_scaffold_preserved": bool(non_simple_preserved),
        "scaffold_correct_first12": scaffold_correct,
        "final_correct_first12": final_correct,
        "net_correct_gain_first12": net_gain,
        "native_admissions_first12": native_admissions,
        "greeting_regressions": greeting_regressions,
        "proxy_threshold_met": proxy_threshold,
        "route_semantic_utility_proven": False,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False, "cases": records,
    }
