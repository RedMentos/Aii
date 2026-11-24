"""Run117DF real SQLite paired RAW/NORMALIZED source-only C3 preflight.

No native inference. The fixed reader's expected action stays offline only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from scripts import run117de_normalized_source_fixture as frozen
from scripts import run117cu_qwen_c3_source_only_preflight as cu
from scripts.run115j_typed_jef_role_native import RUNNER_SHA
from v13.common import dumps
from v13.runtime import Runtime
from v13.store import audit_closed
from v13 import jef_c3_source_only_shadow_candidate as raw
from v13 import jef_c3_normalized_source_shadow_candidate as normalized

SEED = frozen.SEED
STATUS = "RUN117DF_PAIRED_REAL_STORE_SOURCE_ONLY_PREFLIGHT_NO_NATIVE"
NEGATIVE = {
    "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
    "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
    "world_jepa": "SHADOW", "jepa_weight": 0,
    "redmi_measured": False, "whole_system_complete": False,
    "native_proof": False, "native_calls_verified": 0,
    "learning_authority": 0, "delivery_authority": 0,
    "tool_dispatches": 0, "output_committed": False,
    "native_body_calls": 0, "native_c2_calls": 0,
    "native_jef_calls": 0, "model_weight_updates": 0,
}


def sha(raw_bytes):
    return hashlib.sha256(raw_bytes).hexdigest()


def _check_pair(f, baseline, candidate):
    if (baseline.get("status") != raw.STATUS
            or candidate.get("status") != normalized.READY
            or baseline.get("oracle_action_visible") is not False
            or candidate.get("oracle_action_visible") is not False
            or baseline.get("model_called") is not False
            or candidate.get("model_called") is not False
            or baseline.get("native_calls") != 0
            or candidate.get("native_calls") != 0
            or candidate.get("original_messages_sha256") != baseline.get("messages_sha256")
            or candidate.get("source_ref_sha256") != baseline.get("source_ref_sha256")
            or candidate.get("current_source_ref_sha256") != baseline.get("current_source_ref_sha256")):
        raise ValueError("RUN117DF_SOURCE_PAIR_BINDING_RED")
    a, b = baseline["messages"], candidate["messages"]
    if ([m.get("role") for m in a] != ["system", "user"]
            or [m.get("role") for m in b] != ["system", "user"]
            or sha(dumps(a).encode()) != baseline["messages_sha256"]
            or sha(dumps(b).encode()) != candidate["messages_sha256"]):
        raise ValueError("RUN117DF_MESSAGE_SHA_OR_ROLE_RED")
    x, y = json.loads(a[1]["content"]), json.loads(b[1]["content"])
    if (y.get("task") != "SOURCE_ONLY_NORMALIZED_DATA_PROBE"
            or x.get("task") != "SOURCE_ONLY_INDEPENDENT_RULE_PROBE"
            or y.get("source") != x
            or y.get("typed_jef_action_visible") is not False
            or x.get("typed_jef_action_visible") is not False
            or x["current"]["text"] != f["current"]
            or x["policy"]["text"] != f["policy_source"]
            or x["sheet"]["text"] != f["sheet_source"]
            or y.get("worksheet_without_eligibility_or_action") != normalized.normalize(
                f["current"], f["policy_source"], f["sheet_source"])):
        raise ValueError("RUN117DF_SOURCE_VALUES_RED")
    forbidden = ("oracle", "expected_action", "suggested_action",
                 "typed_jef_action", "ranked_action", "wrong_typed_action_synthetic_only")
    if any(k in x or k in y or k in y["worksheet_without_eligibility_or_action"]
           for k in forbidden):
        raise ValueError("RUN117DF_ORACLE_LEAK_RED")
    worksheet = y["worksheet_without_eligibility_or_action"]
    if any(k in worksheet for k in ("eligible", "eligibility", "selected", "action", "ranking")):
        raise ValueError("RUN117DF_ELIGIBILITY_LEAK_RED")
    if (baseline.get("delivery_authority") != 0
            or candidate.get("delivery_authority") != 0
            or baseline.get("learning_authority") != 0
            or candidate.get("learning_authority") != 0):
        raise ValueError("RUN117DF_AUTHORITY_RED")
    return True


def build_envelopes():
    rows = []
    for f in frozen.fixtures():
        with tempfile.TemporaryDirectory(prefix="v13-run117df-real-store-") as tmp:
            home = Path(tmp)
            runtime = Runtime(home)
            try:
                mids = []
                domain = frozen.TABLE[f["index"]][1]
                for key, value in (
                    (f"Project {f['project']} archived {domain} policy", f["policy_source"]),
                    (f"Project {f['project']} latest {domain} option sheet", f["sheet_source"]),
                ):
                    event = runtime.store.event(runtime.session, "Record: " + key)
                    mid = runtime.memory.feedback(event["event_id"], "fact", value,
                                                  permission="record", key=key, scope="session")
                    runtime.memory.candidate(mid, runtime.session)
                    mids.append(mid)
                current = runtime.store.event(runtime.session, f["current"])
                args = (runtime.memory, runtime.session, current["event_id"],
                        current["source_ref"], mids)
                a = raw.build(*args, operator_opt_in=True)
                b = normalized.build(*args, operator_opt_in=True)
                _check_pair(f, a, b)
                no_output = (runtime.store.one("SELECT COUNT(*) AS n FROM actions")["n"] == 0
                             and runtime.store.one(
                                 "SELECT COUNT(*) AS n FROM messages WHERE role='assistant'")["n"] == 0)
                if not no_output:
                    raise ValueError("RUN117DF_UNAUTHORIZED_OUTPUT_RED")
                rows.append({
                    "index": f["index"], "project": f["project"],
                    "source_sha256": f["source_sha256"],
                    "source_ref_sha256": a["source_ref_sha256"],
                    "current_source_ref_sha256": a["current_source_ref_sha256"],
                    "raw_messages": a["messages"],
                    "raw_messages_sha256": a["messages_sha256"],
                    "normalized_messages": b["messages"],
                    "normalized_messages_sha256": b["messages_sha256"],
                    "arm_order": f["arm_order"],
                    "source_only": True, "oracle_visible_to_native": False,
                    "typed_jef_action_visible": False,
                    "model_calls": 0, "native_calls": 0,
                    "store_closed": False, "no_live_output": True,
                })
            finally:
                runtime.close()
            rows[-1]["store_closed"] = audit_closed(home)["ok"] is True
            if not rows[-1]["store_closed"]:
                raise ValueError("RUN117DF_STORE_CLOSE_RED")
    if len(rows) != 12:
        raise ValueError("RUN117DF_ROW_COUNT_RED")
    return rows


def preflight():
    rows = build_envelopes()
    if (len(rows) != 12
            or [r["project"] for r in rows] != [f["project"] for f in frozen.fixtures()]
            or not all(r["store_closed"] and r["no_live_output"] for r in rows)):
        raise ValueError("RUN117DF_COHORT_RED")
    return {
        "schema": "v13.run117df.paired_real_store_source_only_preflight.v1",
        "status": STATUS, "seed": SEED,
        "table_sha256": frozen.TABLE_SHA256,
        "models": cu.pinned_models(), "runner_sha256": RUNNER_SHA,
        "planned_serial_native_calls": 48, "native_calls": 0,
        "rows": rows, **NEGATIVE,
    }


if __name__ == "__main__":
    r = preflight()
    print(dumps({"status": r["status"], "seed": r["seed"],
                 "rows": len(r["rows"]),
                 "planned_serial_native_calls": r["planned_serial_native_calls"],
                 "native_calls": r["native_calls"]}))
