"""Run117CU real SQLite SOURCE_ONLY C3 model-swap preflight, no native calls.

Frozen Run117CN nine-case cohort; compares pinned LFM350M vs Qwen3.5-0.8B
only after a separate native launch. No typed JEF action or oracle in prompts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile

from scripts import run117cn_c3_source_independence_fixture as frozen
from v13.common import dumps
from v13.runtime import Runtime
from v13.store import audit_closed
from v13 import jef_c3_source_only_shadow_candidate as source_only

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "specs/cloud-candidates.json"
MODELS = {
    "lfm25_350m": (
        "LiquidAI/LFM2.5-350M-GGUF",
        "657e078c94084481950a2d555a941481f715536b",
        "LFM Open License 1.0", 219312832,
        "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"),
    "qwen35_0p8b": (
        "ggml-org/Qwen3.5-0.8B-GGUF",
        "8fea620810c4afa23dd6443f999a48574c1611a3",
        "Apache-2.0", 563036064,
        "57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf"),
}
RUNNER_TAR_SHA256 = "9abf88aea48a55d0f80edb1ee20220b186848cca0b4e919d71518cfd7ca67443"
SCHEMA = "v13.run117cu.c3_model_swap_source_only_preflight.v1"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned_models(spec_path=SPEC_PATH):
    data = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    entries = {c["id"]: c for c in data["candidates"]}
    result = []
    for name, expected in MODELS.items():
        if name not in entries:
            raise ValueError("RUN117CU_MODEL_SPEC_MISSING_RED")
        c = entries[name]
        actual = (c.get("model_id"), c.get("revision"), c.get("license_id"),
                  c.get("size"), c.get("sha256"))
        if actual != expected or c.get("kind") != "chat" or c.get("role") not in ("C3", "B2/C3"):
            raise ValueError("RUN117CU_MODEL_SPEC_CHANGED_RED")
        result.append({
            "id": name, "model_id": expected[0], "revision": expected[1],
            "license_id": expected[2], "size": expected[3], "sha256": expected[4],
            "local_name": c["local_name"],
        })
    return result


def build_envelopes(runtime_factory=Runtime):
    cohort = frozen.fixtures()
    if len(cohort) != 9 or frozen.SEED != 117041:
        raise ValueError("RUN117CU_COHORT_CHANGED_RED")
    rows = []
    for item in cohort:
        with tempfile.TemporaryDirectory(prefix="v13-run117cu-") as tmp:
            home = Path(tmp)
            r = runtime_factory(home)
            try:
                ids = []
                project = item["project"]
                topic = frozen.TABLE[item["index"]][1]
                for key, value in (
                    (f"Project {project} archived {topic} policy", item["policy_source"]),
                    (f"Project {project} latest {topic} option sheet", item["sheet_source"]),
                ):
                    event = r.store.event(r.session, "Record: " + key)
                    mid = r.memory.feedback(
                        event["event_id"], "fact", value, permission="record",
                        key=key, scope="session")
                    r.memory.candidate(mid, r.session)
                    ids.append(mid)
                event = r.store.event(r.session, item["current"])
                kwargs = {
                    "memory": r.memory, "session": r.session,
                    "event_id": event["event_id"],
                    "current_ref": event["source_ref"],
                    "memory_ids": ids, "operator_opt_in": True,
                }
                a = source_only.build(**kwargs)
                b = source_only.build(**dict(kwargs, memory_ids=ids[::-1]))
                if (a.get("status") != source_only.STATUS
                        or b.get("status") != source_only.STATUS
                        or a.get("messages_sha256") != b.get("messages_sha256")
                        or a.get("oracle_action_visible") is not False
                        or a.get("model_called") is not False
                        or a.get("delivery_authority") != 0
                        or a.get("learning_authority") != 0):
                    raise ValueError("RUN117CU_SOURCE_ADMISSION_RED")
                messages = a["messages"]
                if sha(dumps(messages).encode("utf-8")) != a["messages_sha256"]:
                    raise ValueError("RUN117CU_MESSAGE_DIGEST_RED")
                if ([m.get("role") for m in messages] != ["system", "user"]
                        or len(messages) != 2
                        or not all(type(m.get("content")) is str for m in messages)):
                    raise ValueError("RUN117CU_MESSAGE_ROLES_RED")
                payload = json.loads(messages[1]["content"])
                if (payload.get("typed_jef_action_visible") is not False
                        or payload.get("task") != "SOURCE_ONLY_INDEPENDENT_RULE_PROBE"
                        or any(key in payload for key in
                               ("expected_action", "oracle", "suggested_action",
                                "typed_jef_action", "wrong_typed_action_synthetic_only"))):
                    raise ValueError("RUN117CU_ORACLE_LEAK_RED")
                for role, field in (("current", "current"),
                                    ("policy", "policy_source"),
                                    ("sheet", "sheet_source")):
                    if payload[role]["text"] != item[field]:
                        raise ValueError("RUN117CU_SOURCE_TEXT_CHANGED_RED")
                rows.append({
                    "index": item["index"], "project": project,
                    "messages": messages, "messages_sha256": a["messages_sha256"],
                    "source_sha256": item["source_sha256"],
                    "source_only": True, "typed_jef_action_visible": False,
                    "oracle_visible_to_native": False, "model_calls": 0,
                    "native_calls": 0, "authority": 0,
                })
            finally:
                r.close()
            if audit_closed(home)["ok"] is not True:
                raise ValueError("RUN117CU_STORE_AUDIT_RED")
    if [r["project"] for r in rows] != [x["project"] for x in cohort]:
        raise ValueError("RUN117CU_COHORT_ORDER_RED")
    return rows


def preflight():
    models = pinned_models()
    rows = build_envelopes()
    return {
        "schema": SCHEMA, "status": "SOURCE_ONLY_MODEL_SWAP_PREFLIGHT_NO_NATIVE",
        "seed": frozen.SEED, "table_sha256": frozen.TABLE_SHA256,
        "runner_tar_sha256": RUNNER_TAR_SHA256,
        "models": models, "rows": rows,
        "planned_serial_native_calls": len(rows) * len(models),
        "native_calls": 0, "model_calls": 0, "learning_authority": 0,
        "delivery_authority": 0, "tool_dispatches": 0,
        "output_committed": False, "jepa_weight": 0,
        "age0": "RECORD_ONLY", "step2": "UTILITY_FAIL",
        "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
        "world_jepa": "SHADOW", "redmi_measured": False,
        "whole_system_complete": False,
    }


def main():
    print(dumps(preflight()))


if __name__ == "__main__":
    main()
