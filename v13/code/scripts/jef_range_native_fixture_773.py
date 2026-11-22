"""Run75 pinned six-case mixed-range JEF/C3 native formatter fixture, seed773.

Reuses preregistered Run73 source cases without changing their bytes or
Run68/70 native cohorts. Typed action is intentionally visible to C3.
"""
import hashlib
import json

from tests.test_jef_range_policy_shadow import TABLE, texts
from scripts import jef_c3_schema_fixture_727 as run68

SEED = 773
MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
RUNNER_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
TABLE_SHA256 = "b43365b3f84570f6dad9a9e2d99285d5b5c445c8044740532588ef20c8ef60ba"
SCHEMA = run68.SCHEMA


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def oracle(row):
    _, _, op1, op2, rule, a, b, _ = row
    eligible = []
    for name, opt in (("A", a), ("B", b)):
        bounds = all((opt[i] >= rule[i] if op == "Minimum"
                      else opt[i] <= rule[i])
                     for i, op in enumerate((op1, op2)))
        if bounds and (not rule[2] or opt[2]):
            eligible.append((opt[0], opt[1], name))
    return min(eligible)[2] if eligible else "NONE"


def fixtures():
    raw = json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode()
    if sha(raw) != TABLE_SHA256:
        raise ValueError("RUN75_TABLE_CHANGED")
    if [row[-1] for row in TABLE] != ["A", "B", "NONE", "A", "B", "NONE"]:
        raise ValueError("RUN75_BALANCE_CHANGED")
    if any(oracle(row) != row[-1] for row in TABLE):
        raise ValueError("RUN75_ORACLE_CHANGED")
    result = []
    for index, row in enumerate(TABLE):
        current, policy, sheet = texts(row)
        result.append({
            "index": index, "project": row[0], "expected": row[-1],
            "current": current, "policy_source": policy, "sheet_source": sheet,
        })
    return result


def score(output, expected):
    return int(run68.decode_schema(output) == expected)
