"""Frozen Run117DE 12-case source-only presentation ablation fixture.

Registered before implementation: seed117061, table SHA256, no model oracle.
"""
from __future__ import annotations

import hashlib
import json

from scripts import run117da_disjoint_schema_fixture as da
from scripts import run117cn_c3_source_independence_fixture as cn
from scripts import jef_range_native_fixture_773 as run75
from scripts import jef_body_c3_interference_fixture_839 as run83
from tests.test_jef_range_policy_shadow import TABLE as run73_table, texts

SEED = 117061
TABLE_SHA256 = "81af85fb4a93baf8ea32c925f41548c6e9380ccd6025df43f2d4c346caad2e64"
ARMS = ("LFM_RAW", "QWEN_NORMALIZED", "LFM_NORMALIZED", "QWEN_RAW")
TABLE = (
 ('EB01','mesa turbines','Maximum','Minimum',(135,30,False),(130,36,True),(146,22,False),'A'),
 ('EB02','glacier telemetry','Minimum','Maximum',(215,15,True),(197,22,False),(217,14,True),'B'),
 ('EB03','port cranes','Maximum','Maximum',(165,25,True),(180,26,False),(171,32,False),'NONE'),
 ('EB04','reef surveyors','Minimum','Minimum',(125,30,False),(130,35,True),(140,40,False),'A'),
 ('EB05','rail beacons','Maximum','Minimum',(90,35,True),(104,34,False),(86,40,True),'B'),
 ('EB06','desert pumps','Minimum','Maximum',(205,25,True),(197,28,False),(194,29,False),'NONE'),
 ('EB07','marsh buoys','Maximum','Maximum',(95,25,False),(92,24,True),(107,32,False),'A'),
 ('EB08','solar trackers','Minimum','Minimum',(115,15,True),(140,25,True),(127,18,True),'B'),
 ('EB09','tunnel drones','Maximum','Minimum',(80,30,True),(94,29,False),(88,24,False),'NONE'),
 ('EB10','ridge relays','Minimum','Maximum',(185,15,False),(191,13,True),(191,15,False),'A'),
 ('EB11','orchard probes','Maximum','Maximum',(215,30,True),(199,29,True),(199,28,True),'B'),
 ('EB12','cave monitors','Minimum','Minimum',(80,15,True),(76,13,False),(62,9,False),'NONE'),
)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def oracle(row):
    _, _, op1, op2, rule, a, b, _ = row
    eligible = []
    for label, opt in (("A", a), ("B", b)):
        bounds = all(opt[i] >= rule[i] if op == "Minimum" else opt[i] <= rule[i]
                     for i, op in enumerate((op1, op2)))
        if bounds and (not rule[2] or opt[2]):
            eligible.append((opt[0], opt[1], label))
    return min(eligible)[2] if eligible else "NONE"


def fixtures():
    if _sha(json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode()) != TABLE_SHA256:
        raise ValueError("RUN117DE_FROZEN_TABLE_RED")
    if len(TABLE) != 12 or [r[-1] for r in TABLE] != ["A", "B", "NONE"] * 4:
        raise ValueError("RUN117DE_BALANCE_RED")
    old = {r[0] for cohort in (da.TABLE, cn.TABLE, run75.TABLE, run83.TABLE, run73_table)
           for r in cohort}
    if len({r[0] for r in TABLE}) != 12 or old & {r[0] for r in TABLE}:
        raise ValueError("RUN117DE_DISJOINT_RED")
    if any(oracle(row) != row[-1] for row in TABLE):
        raise ValueError("RUN117DE_ORACLE_RED")
    result = []
    for i, row in enumerate(TABLE):
        current, policy, sheet = texts(row)
        result.append({
            "index": i, "project": row[0],
            "expected_for_offline_scorer_only": row[-1],
            "current": current, "policy_source": policy, "sheet_source": sheet,
            "source_sha256": {"current": _sha(current.encode()),
                              "policy_source": _sha(policy.encode()),
                              "sheet_source": _sha(sheet.encode())},
            "arm_order": ARMS[i % 4:] + ARMS[:i % 4],
            "seed": SEED, "native_calls": 0, "model_calls": 0,
            "jepa_weight": 0, "whole_system_complete": False,
        })
    return result
