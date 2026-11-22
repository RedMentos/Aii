"""Run117DA preregistered 12 disjoint source-only C3 schema-ablation rows.

Frozen seed117053, table hash; scorer-only expected never sent to native.
"""
import hashlib
import json

from scripts import jef_range_native_fixture_773 as prior
from scripts import jef_body_c3_interference_fixture_839 as run83
from scripts import run117cn_c3_source_independence_fixture as run117cn
from tests.test_jef_range_policy_shadow import TABLE as RUN73_TABLE, texts

SEED = 117053
TABLE = (
 ("DA01","harbor buoys","Minimum","Maximum",(100,20,True),(120,15,True),(90,10,True),"A"),
 ("DA02","canal tugs","Minimum","Maximum",(80,15,True),(70,12,True),(90,14,True),"B"),
 ("DA03","cliff beacons","Maximum","Minimum",(120,20,True),(100,15,True),(130,25,True),"NONE"),
 ("DA04","wind probes","Maximum","Minimum",(200,10,False),(150,12,False),(180,11,True),"A"),
 ("DA05","river gauges","Minimum","Minimum",(70,10,True),(60,15,True),(75,11,True),"B"),
 ("DA06","lab samplers","Maximum","Maximum",(150,20,True),(120,10,False),(130,15,False),"NONE"),
 ("DA07","forest sensors","Minimum","Minimum",(100,15,False),(105,16,False),(115,18,False),"A"),
 ("DA08","archive skiffs","Maximum","Maximum",(140,25,False),(130,30,True),(135,20,False),"B"),
 ("DA09","polar monitors","Minimum","Maximum",(200,10,True),(210,12,True),(190,9,True),"NONE"),
 ("DA10","urban relays","Maximum","Maximum",(160,30,True),(140,25,True),(150,20,True),"A"),
 ("DA11","desert robots","Maximum","Minimum",(90,18,False),(100,25,True),(85,19,False),"B"),
 ("DA12","island rovers","Minimum","Minimum",(120,30,True),(125,25,True),(115,35,True),"NONE"),
)
TABLE_SHA256 = "78ec82002dafa54bcd9bb09456a0351123d2974bf12222fa6b20794d44f2edfb"
ARMS = ("LFM_SCHEMA", "QWEN_UNCONSTRAINED", "LFM_UNCONSTRAINED", "QWEN_SCHEMA")
MODELS = ("lfm25_350m", "qwen35_0p8b")
SCHEMA_MODES = ("SCHEMA", "UNCONSTRAINED")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fixtures():
    if sha(json.dumps(TABLE, sort_keys=True, separators=(",", ":")).encode()) != TABLE_SHA256:
        raise ValueError("RUN117DA_TABLE_HASH_RED")
    if len(TABLE) != 12 or [r[-1] for r in TABLE] != ["A", "B", "NONE"] * 4:
        raise ValueError("RUN117DA_BALANCE_RED")
    projects = [r[0] for r in TABLE]
    old = {r[0] for group in (
        RUN73_TABLE, prior.TABLE, run83.TABLE, run117cn.TABLE)
        for r in group}
    if len(set(projects)) != 12 or set(projects) & old:
        raise ValueError("RUN117DA_DISJOINTNESS_RED")
    if any(prior.oracle(r) != r[-1] for r in TABLE):
        raise ValueError("RUN117DA_ORACLE_RED")
    result = []
    for i, row in enumerate(TABLE):
        current, policy, sheet = texts(row)
        order = ARMS[i % 4:] + ARMS[:i % 4]
        result.append({
            "index": i, "project": row[0],
            "expected_for_offline_scorer_only": row[-1],
            "current": current, "policy_source": policy,
            "sheet_source": sheet, "arm_order": order,
            "source_sha256": {
                "current": sha(current.encode()),
                "policy_source": sha(policy.encode()),
                "sheet_source": sha(sheet.encode()),
            },
            "seed": SEED, "authority": 0,
            "model_calls": 0, "native_calls": 0,
            "jepa_weight": 0, "whole_system_complete": False,
        })
    return result


def strict(raw, expected):
    return prior.score(raw, expected)
