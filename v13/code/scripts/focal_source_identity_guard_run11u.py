"""Run11U independent source-key/value consistency guard; SHADOW ONLY.

Never changes frozen Run11S, original WP-Z5b, Runtime, or FocalLoop.
A matching key/value grammar is not proof of factual truth or model utility.
"""
from __future__ import annotations

import hashlib
import json
import re

from scripts import focal_replacement_shadow_run11s as frozen

SCHEMA = "v13.focal.source_identity.seed173.shadow.v1"
SEED = 173
PER_KIND = 15
CAPACITY = 4
MONTHS = "|".join(frozen.MONTHS)
_BUDGET_KEY = re.compile(rf"^Project ([A-Za-z]+) budget ({MONTHS})$", re.I)
_SPEND_KEY = re.compile(r"^Project ([A-Za-z]+) budget spending$", re.I)
_CORRECTION_KEY = re.compile(
    r"^Project ([A-Za-z]+) survey bicycles correction$", re.I)


def _abstain(previous, reason):
    """Keep first-four as a diagnostic, never as admitted source authority."""
    return {**previous, "abstain": True, "reason": reason,
            "selected_keys": [], "key_value_consistent": False,
            "identity_scope": "SYNTACTIC_KEY_VALUE_ONLY"}


def _consistent(kind, project, key, value):
    """Selected key must agree with its value's project, month and kind."""
    if kind in ("update", "combine"):
        budget_key = _BUDGET_KEY.fullmatch(key)
        budget_value = frozen._BUDGET.fullmatch(value)
        if budget_key and budget_value:
            return (budget_key.group(1).lower() == project
                    and budget_value.group(2).lower() == project
                    and budget_key.group(2).lower() ==
                    budget_value.group(1).lower())
        if kind == "combine":
            spending_key = _SPEND_KEY.fullmatch(key)
            spending_value = frozen._SPEND.fullmatch(value)
            return bool(spending_key and spending_value
                        and spending_key.group(1).lower() == project
                        and spending_value.group(2).lower() == project)
        return False
    if kind == "correction":
        correction_key = _CORRECTION_KEY.fullmatch(key)
        correction_value = frozen._CORRECTION.fullmatch(value)
        return bool(correction_key and correction_value
                    and correction_key.group(1).lower() == project
                    and correction_value.group(1).lower() == project)
    return False


def propose_bound(query, notes, capacity=CAPACITY):
    """Source-only guard around frozen Run11S; no answer or runtime authority."""
    prior = frozen.propose(query, notes, capacity=capacity)
    if prior["abstain"]:
        return _abstain(prior, "UPSTREAM_ABSTAIN:" + prior["reason"])
    projects = {match.lower() for match in frozen._PROJECT.findall(query)}
    if len(projects) != 1:
        return _abstain(prior, "QUERY_PROJECT_AMBIGUOUS")
    project = next(iter(projects))
    if prior["kind"] == "distract":
        if prior["selected_keys"]:
            return _abstain(prior, "UNEXPECTED_DISTRACT_SOURCES")
        return {**prior, "key_value_consistent": True,
                "identity_scope": "NO_STORED_SOURCE_REQUIRED"}
    keys = {key: value for key, value in notes}
    if len(keys) != len(notes):
        return _abstain(prior, "SOURCE_KEY_DUPLICATE")
    selected = prior["selected_keys"]
    if not selected or len(selected) > capacity:
        return _abstain(prior, "SOURCE_SELECTION_INVALID")
    if any(key not in keys or not _consistent(prior["kind"], project,
                                               key, keys[key])
           for key in selected):
        return _abstain(prior, "SOURCE_KEY_VALUE_MISMATCH")
    return {**prior, "key_value_consistent": True,
            "identity_scope": "SYNTACTIC_KEY_VALUE_ONLY"}


def evaluate(seed=SEED):
    """Fresh disjoint software-only source-key selection; not model utility."""
    if type(seed) is not int or seed in (11, frozen.SEED):
        raise ValueError("DISJOINT_SEED_REQUIRED")
    fixtures = frozen.tasks(seed=seed, per_kind=PER_KIND)
    if len(fixtures) != 60:
        raise ValueError("FIXTURE_COUNT_CHANGED")
    rows = []
    for fid, query, notes, _answers, _checks, _stale in fixtures:
        original = frozen.propose(query, notes, capacity=CAPACITY)
        candidate = propose_bound(query, notes, capacity=CAPACITY)
        required = frozen.required_keys(fid, notes)
        if required is None:
            raise ValueError("ORACLE_SOURCE_SHAPE:" + fid)
        source_keys = {key for key, _ in notes}
        chosen = candidate["selected_keys"]
        if not set(chosen) <= source_keys or len(chosen) > CAPACITY:
            raise ValueError("SOURCE_OR_CAPACITY_INVALID:" + fid)
        rows.append({
            "fixture": fid, "kind": candidate["kind"],
            "required_keys": required,
            "original_selected": original["selected_keys"],
            "candidate_selected": chosen,
            "abstain": candidate["abstain"],
            "reason": candidate["reason"],
            "key_value_consistent": candidate["key_value_consistent"],
            "exact_required": set(chosen) == set(required),
            "original_exact_required": set(original["selected_keys"]) == set(required),
            "required_included": set(required) <= set(chosen),
            "original_required_included": set(required) <= set(original["selected_keys"]),
            "source_key_sha256": hashlib.sha256(json.dumps(
                [key for key, _ in notes], sort_keys=True).encode()).hexdigest(),
        })
    summary = {
        "exact_required": sum(row["exact_required"] for row in rows),
        "original_exact_required": sum(row["original_exact_required"] for row in rows),
        "required_included": sum(row["required_included"] for row in rows),
        "original_required_included": sum(row["original_required_included"] for row in rows),
        "abstentions": sum(row["abstain"] for row in rows),
        "by_kind": {kind: sum(row["exact_required"] for row in rows
                              if row["kind"] == kind)
                    for kind in ("update", "combine", "correction", "distract")},
    }
    return {
        "schema": SCHEMA, "seed": seed,
        "frozen_run11s_blob": "bf9c7d8ee75bbe82a82c0c2d3dc4cefed4036bce",
        "source_generator_blob": "9d61acdd8f8aa47435ed682ac4b7013fd3e02df8",
        "status": "SYNTHETIC_SOURCE_IDENTITY_ONLY_NO_MODEL_UTILITY",
        "summary": summary, "rows": rows,
        "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "redmi_measured": False,
        "whole_system_complete": False,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
