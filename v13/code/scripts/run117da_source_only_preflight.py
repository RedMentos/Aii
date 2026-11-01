"""Run117DA real SQLite source-only 12-case preflight, no native calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from scripts import run117da_disjoint_schema_fixture as frozen
from scripts import run117cu_qwen_c3_source_only_preflight as cu
from scripts.run115j_typed_jef_role_native import RUNNER_SHA
from v13.runtime import Runtime
from v13.common import dumps
from v13.store import audit_closed
from v13 import jef_c3_source_only_shadow_candidate as source

ROOT = cu.ROOT
SEED = frozen.SEED
STATUS = "RUN117DA_SOURCE_ONLY_SCHEMA_PREFLIGHT_NO_NATIVE"
NEGATIVE = {
    "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
    "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
    "world_jepa": "SHADOW", "jepa_weight": 0,
    "redmi_measured": False, "whole_system_complete": False,
    "learning_authority": 0,
    "delivery_authority": 0, "tool_dispatches": 0,
    "native_body_calls": 0, "native_c2_calls": 0,
    "native_jef_calls": 0, "output_committed": False,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def build_envelopes():
    rows = []
    for f in frozen.fixtures():
        with tempfile.TemporaryDirectory(prefix="v13-run117da-store-") as tmp:
            home = Path(tmp)
            runtime = Runtime(home)
            try:
                ids = []
                topic = frozen.TABLE[f["index"]][1]
                for key, value in (
                    (f"Project {f['project']} archived {topic} policy",
                     f["policy_source"]),
                    (f"Project {f['project']} latest {topic} option sheet",
                     f["sheet_source"]),
                ):
                    event = runtime.store.event(runtime.session, "Record: " + key)
                    mid = runtime.memory.feedback(
                        event["event_id"], "fact", value, permission="record",
                        key=key, scope="session")
                    runtime.memory.candidate(mid, runtime.session)
                    ids.append(mid)
                current = runtime.store.event(runtime.session, f["current"])
                envelope = source.build(
                    runtime.memory, runtime.session, current["event_id"],
                    current["source_ref"], ids, operator_opt_in=True)
                if (envelope["status"] != source.STATUS
                        or envelope["oracle_action_visible"] is not False
                        or envelope["model_called"] is not False
                        or envelope["native_calls"] != 0
                        or envelope["jepa_weight"] != 0):
                    raise ValueError("RUN117DA_SOURCE_ADMISSION_RED")
                messages = envelope["messages"]
                payload = json.loads(messages[1]["content"])
                if (payload["typed_jef_action_visible"] is not False
                        or payload["policy"]["text"] != f["policy_source"]
                        or payload["sheet"]["text"] != f["sheet_source"]
                        or payload["current"]["text"] != f["current"]
                        or any(k in payload for k in (
                            "oracle", "expected_action", "suggested_action",
                            "typed_jef_action", "wrong_typed_action_synthetic_only"))):
                    raise ValueError("RUN117DA_ORACLE_OR_SOURCE_RED")
                rows.append({
                    "index": f["index"], "project": f["project"],
                    "messages": messages,
                    "messages_sha256": sha(dumps(messages).encode()),
                    "source_sha256": f["source_sha256"],
                    "source_ref_sha256": envelope["source_ref_sha256"],
                    "current_source_ref_sha256": envelope["current_source_ref_sha256"],
                    "arm_order": f["arm_order"],
                    "source_only": True, "oracle_visible_to_native": False,
                    "typed_jef_action_visible": False,
                    "native_calls": 0, "model_calls": 0,
                    "store_closed": False,
                })
            finally:
                runtime.close()
            rows[-1]["store_closed"] = audit_closed(home)["ok"] is True
            if not rows[-1]["store_closed"]:
                raise ValueError("RUN117DA_STORE_CLOSE_RED")
    if len(rows) != 12:
        raise ValueError("RUN117DA_ROW_COUNT_RED")
    return rows


def preflight():
    rows = build_envelopes()
    if (len(rows) != 12
            or [r["project"] for r in rows] != [f["project"] for f in frozen.fixtures()]
            or not all(r["store_closed"] for r in rows)):
        raise ValueError("RUN117DA_COHORT_RED")
    return {
        "schema": "v13.run117da.source_only_schema_preflight.v1",
        "status": STATUS, "seed": SEED,
        "table_sha256": frozen.TABLE_SHA256,
        "models": cu.pinned_models(),
        "runner_sha256": RUNNER_SHA,
        "planned_serial_native_calls": 48,
        "native_calls": 0, "rows": rows, **NEGATIVE,
    }


if __name__ == "__main__":
    result = preflight()
    print(dumps({"status": result["status"], "seed": result["seed"],
                 "rows": len(result["rows"]),
                 "planned_serial_native_calls": result["planned_serial_native_calls"],
                 "native_calls": result["native_calls"]}))
