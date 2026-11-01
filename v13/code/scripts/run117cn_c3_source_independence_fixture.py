"""Run117CN frozen nine-case source-independence fixture, seed117041.

No model call or native launch. Expected labels and counterfactual wrong typed
actions are SCORER-ONLY, never part of the SOURCE_ONLY C3 prompt.
"""
from __future__ import annotations

import hashlib
import json

from scripts import jef_range_native_fixture_773 as prior
from scripts import jef_body_c3_interference_fixture_839 as run83
from tests.test_jef_range_policy_shadow import TABLE as RUN73_TABLE, texts

SEED = 117041
TABLE = (
    ("Saffron", "coastal sensors", "Minimum", "Maximum", (90, 25, True),
     (105, 18, True), (115, 21, True), "A"),
    ("Vega", "polar gliders", "Minimum", "Minimum", (120, 14, False),
     (119, 18, True), (140, 20, False), "B"),
    ("Quartz", "orchard robots", "Maximum", "Minimum", (160, 30, True),
     (145, 28, True), (155, 29, True), "NONE"),
    ("Boreal", "bridge probes", "Maximum", "Maximum", (200, 18, False),
     (170, 14, False), (185, 13, True), "A"),
    ("Nimbus", "river skimmers", "Minimum", "Maximum", (75, 11, True),
     (90, 12, True), (95, 10, True), "B"),
    ("Cedar", "archive crawlers", "Maximum", "Maximum", (135, 16, True),
     (120, 14, False), (130, 17, True), "NONE"),
    ("Tangent", "warehouse optics", "Minimum", "Minimum", (110, 20, False),
     (130, 23, False), (130, 24, True), "A"),
    ("Peregrine", "mountain relays", "Maximum", "Minimum", (145, 10, True),
     (120, 9, True), (125, 11, True), "B"),
    ("Zephyr", "harvest drones", "Minimum", "Minimum", (50, 8, True),
     (70, 9, False), (55, 10, False), "NONE"),
)
TABLE_SHA256 = "fb5708c82f4d62338eb080264ec6c2cbf8234fc9b5845abc3c0e53e513597335"
MODEL_SHA256 = prior.MODEL_SHA256
RUNNER_SHA256 = prior.RUNNER_SHA256
SCHEMA = prior.SCHEMA
ARMS = ("SOURCE_ONLY", "TYPED_CORRECT", "TYPED_WRONG")
WRONG = {"A": "B", "B": "NONE", "NONE": "A"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixtures():
    digest = sha(json.dumps(
        TABLE, sort_keys=True, separators=(",", ":")).encode())
    if digest != TABLE_SHA256:
        raise ValueError("RUN117CN_TABLE_HASH_RED")
    if [row[-1] for row in TABLE] != ["A", "B", "NONE"] * 3:
        raise ValueError("RUN117CN_BALANCE_RED")
    projects = [row[0] for row in TABLE]
    old_projects = {r[0] for cohort in (RUN73_TABLE, prior.TABLE, run83.TABLE)
                    for r in cohort}
    if len(set(projects)) != len(TABLE) or set(projects) & old_projects:
        raise ValueError("RUN117CN_DISJOINTNESS_RED")
    if any(prior.oracle(row) != row[-1] for row in TABLE):
        raise ValueError("RUN117CN_ORACLE_RED")
    results = []
    for index, row in enumerate(TABLE):
        current, policy, sheet = texts(row)
        order = ARMS[index % 3:] + ARMS[:index % 3]
        results.append({
            "index": index,
            "project": row[0],
            "expected_for_offline_scorer_only": row[-1],
            "wrong_typed_action_synthetic_only": WRONG[row[-1]],
            "current": current,
            "policy_source": policy,
            "sheet_source": sheet,
            "arm_order": order,
            "source_sha256": {
                "current": sha(current.encode()),
                "policy_source": sha(policy.encode()),
                "sheet_source": sha(sheet.encode()),
            },
            "research_only": True,
            "authority": 0, "native_calls": 0,
            "jepa_weight": 0, "whole_system_complete": False,
        })
    return results


def strict(output, expected):
    return prior.score(output, expected)
