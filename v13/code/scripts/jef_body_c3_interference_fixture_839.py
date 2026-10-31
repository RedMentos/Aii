"""Run83 immutable disjoint six-case C3 formatter interference fixture, seed839.

Human JEF typed answer visible in both arms. B1/B2 summaries are synthetic
contradictory hypotheses, NOT native body observations or factual evidence.
"""
from __future__ import annotations

import hashlib
import json

from scripts import jef_range_native_fixture_773 as prior
from tests.test_jef_range_policy_shadow import texts

SEED = 839
TABLE = (
    ("Juniper", "harbor cranes", "Minimum", "Maximum", (107, 22, True),
     (127, 20, True), (97, 17, True), "A"),
    ("Kestrel", "museum drones", "Minimum", "Maximum", (107, 22, True),
     (137, 27, True), (147, 20, True), "B"),
    ("Linden", "forest robotics", "Maximum", "Minimum", (107, 22, True),
     (97, 17, True), (117, 27, True), "NONE"),
    ("Mistral", "island cargo", "Maximum", "Minimum", (207, 12, False),
     (157, 14, False), (187, 13, True), "A"),
    ("Nacre", "school bots", "Minimum", "Minimum", (77, 12, True),
     (67, 17, True), (82, 13, True), "B"),
    ("Orchid", "archive gliders", "Maximum", "Maximum", (157, 22, True),
     (127, 12, False), (137, 17, False), "NONE"),
)
TABLE_SHA256 = "be6ce6e8664e7f67bbaaeb18ac8e31b3a7bc1a81d8b903a4f57d06ad3e37ce3d"
MODEL_SHA256 = prior.MODEL_SHA256
RUNNER_SHA256 = prior.RUNNER_SHA256
SCHEMA = prior.SCHEMA
ARMS = ("TYPED_ONLY", "DUAL_SOURCE")
WRONG = {"A": "B", "B": "A", "NONE": "A"}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixtures():
    digest = sha(json.dumps(
        TABLE, sort_keys=True, separators=(",", ":")).encode())
    if digest != TABLE_SHA256:
        raise ValueError("RUN83_TABLE_HASH_RED")
    if [row[-1] for row in TABLE] != ["A", "B", "NONE", "A", "B", "NONE"]:
        raise ValueError("RUN83_BALANCE_RED")
    if any(prior.oracle(row) != row[-1] for row in TABLE):
        raise ValueError("RUN83_ORACLE_RED")
    result = []
    for index, row in enumerate(TABLE):
        current, policy, sheet = texts(row)
        result.append({
            "index": index, "project": row[0], "expected": row[-1],
            "wrong_body_action": WRONG[row[-1]],
            "current": current, "policy_source": policy,
            "sheet_source": sheet,
            "arm_order": ARMS if index % 2 == 0 else ARMS[::-1],
            "source_sha256": {
                "current": sha(current.encode()),
                "policy_source": sha(policy.encode()),
                "sheet_source": sha(sheet.encode()),
            },
        })
    return result


def strict(output, expected):
    return prior.score(output, expected)


def verdict(scores):
    if (type(scores) is not dict or set(scores) != set(ARMS)
            or any(type(v) is not int or not 0 <= v <= 6
                   for v in scores.values())):
        raise ValueError("RUN83_SCORE_SHAPE_RED")
    if scores["TYPED_ONLY"] < 5:
        return "BASELINE_FORMATTER_RED"
    if scores["DUAL_SOURCE"] < scores["TYPED_ONLY"] - 1:
        return "DUAL_INTERFERENCE_RED"
    return "DUAL_FORMATTER_NONINFERIOR_SMALL_SHADOW"
