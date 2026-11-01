#!/usr/bin/env python3
"""Run117DG: preregistered 48-call RAW vs normalized-source native C3 pilot.

New EB01–EB12 only, no original DA rescore or production authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import threading
import time

from scripts import run117de_normalized_source_fixture as frozen
from scripts import run117df_paired_source_preflight as pre
from scripts import run117cv_qwen_c3_native as cv
from scripts import jef_c3_schema_fixture_727 as run68
from v13.common import atomic_write, dumps
from v13.runners import LlamaRunner

SEED = 117061
SCHEMA = "v13.run117dg.normalized_source_paired_native.v1"
MODEL_FOR = {"LFM": cv.MODELS[0], "QWEN": cv.MODELS[1]}
BLOBS = {
    "scripts/run117de_normalized_source_fixture.py": "04f79fb713344407c618fe736e94fb8549cc7121",
    "v13/jef_c3_normalized_source_shadow_candidate.py": "b625f989f7c3236652c7f646540f0e99d86cf016",
    "scripts/run117df_paired_source_preflight.py": "280c2f32e5ac707b8c0d3ca22cf9a1cf8d7255d1",
}
CONFIG = cv.CONFIG | {"seed": SEED, "answer_tokens": 128}
NEGATIVE = cv.NEGATIVE | {
    "independent_generalization": False,
    "native_model_weight_updates": 0, "native_b1_calls": 0,
    "native_b2_calls": 0,
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_pins():
    pins = cv.source_pins()
    for path, blob in BLOBS.items():
        if cv._blob(cv.cu.ROOT / path) != blob:
            raise ValueError("RUN117DG_FROZEN_SOURCE_BLOB_RED")
        pins[path] = blob
    return pins


def validate(rows):
    fixture = frozen.fixtures()
    if len(rows) != 12 or len(fixture) != 12:
        raise ValueError("RUN117DG_ROW_COUNT_RED")
    for row, f in zip(rows, fixture):
        if (row["index"] != f["index"] or row["project"] != f["project"]
                or row["source_sha256"] != f["source_sha256"]
                or tuple(row["arm_order"]) != tuple(f["arm_order"])
                or row["source_only"] is not True
                or row["oracle_visible_to_native"] is not False
                or row["typed_jef_action_visible"] is not False
                or row["model_calls"] != 0 or row["native_calls"] != 0
                or row["store_closed"] is not True or row["no_live_output"] is not True):
            raise ValueError("RUN117DG_SOURCE_ENVELOPE_RED")
        for mode in ("raw", "normalized"):
            messages = row[mode + "_messages"]
            if ([m.get("role") for m in messages] != ["system", "user"]
                    or sha(dumps(messages).encode()) != row[mode + "_messages_sha256"]):
                raise ValueError("RUN117DG_MESSAGE_HASH_RED")
        raw = json.loads(row["raw_messages"][1]["content"])
        normalized = json.loads(row["normalized_messages"][1]["content"])
        if (normalized.get("source") != raw
                or normalized.get("typed_jef_action_visible") is not False
                or raw.get("typed_jef_action_visible") is not False
                or raw["current"]["text"] != f["current"]
                or raw["policy"]["text"] != f["policy_source"]
                or raw["sheet"]["text"] != f["sheet_source"]
                or any(k in raw or k in normalized for k in (
                    "oracle", "expected_action", "suggested_action",
                    "typed_jef_action", "wrong_typed_action_synthetic_only"))):
            raise ValueError("RUN117DG_ORACLE_OR_SOURCE_RED")
    return True


def _arm(name):
    model, mode = name.split("_", 1)
    if model not in MODEL_FOR or mode not in ("RAW", "NORMALIZED"):
        raise ValueError("RUN117DG_UNKNOWN_ARM_RED")
    return MODEL_FOR[model], mode


def summarize(report):
    scores = {model: {mode: 0 for mode in ("RAW", "NORMALIZED")}
              for model in cv.MODELS}
    non_none = {model: {mode: 0 for mode in ("RAW", "NORMALIZED")}
                for model in cv.MODELS}
    none_count = {model: {mode: 0 for mode in ("RAW", "NORMALIZED")}
                  for model in cv.MODELS}
    paired = {model: {"normalized_only": 0, "raw_only": 0}
              for model in cv.MODELS}
    finals = reaped = 0
    complete = len(report["rows"]) == 12 and report["model_callback_attempts"] == 48
    for row in report["rows"]:
        arms = row.get("arms", [])
        if (len(arms) != 4 or tuple(a["arm"] for a in arms)
                != tuple(frozen.ARMS[row["index"] % 4:]
                         + frozen.ARMS[:row["index"] % 4])):
            complete = False
        by = {a["arm"]: a for a in arms}
        if len(by) != 4:
            complete = False
        for a in arms:
            model, mode = _arm(a["arm"])
            if (a["model"] != model or a["mode"] != mode
                    or a["messages_sha256"] != row[mode.lower() + "_messages_sha256"]
                    or a["status"] != "RECORDED"):
                complete = False
            finals += int(a["native_final"] is True)
            reaped += int(a["process_reaped"] is True)
            scores[model][mode] += int(a["exact"] is True)
            non_none[model][mode] += int(a["exact"] is True and row["expected"] != "NONE")
            none_count[model][mode] += int(a.get("parsed_action") == "NONE")
        for prefix, model in MODEL_FOR.items():
            a = by.get(prefix + "_RAW", {})
            b = by.get(prefix + "_NORMALIZED", {})
            paired[model]["normalized_only"] += int(
                b.get("exact") is True and a.get("exact") is not True)
            paired[model]["raw_only"] += int(
                a.get("exact") is True and b.get("exact") is not True)
    complete = complete and finals == reaped == 48 and report["pins_unchanged"] is True
    signals = {}
    for model in cv.MODELS:
        net = paired[model]["normalized_only"] - paired[model]["raw_only"]
        signals[model] = (
            scores[model]["NORMALIZED"] >= 7
            and non_none[model]["NORMALIZED"] >= 5
            and net >= 3)
    return {
        "complete_native_receipts": bool(complete),
        "native_final": finals, "process_reaped": reaped,
        "strict_scores": scores, "non_none_correct": non_none,
        "none_output_count": none_count, "paired": paired,
        "normalized_signal_by_model": signals,
    }


def run(installed, qwen_path, out, *, runner_factory=LlamaRunner,
        pin_factory=cv.pinned_paths, preflight_factory=pre.preflight):
    installed, qwen_path, out = Path(installed), Path(qwen_path), Path(out)
    if out.exists() or not out.parent.is_dir() or out.parent.is_symlink():
        raise FileExistsError("RUN117DG_FRESH_OUTPUT_REQUIRED")
    actual_native_factory = (
        runner_factory is LlamaRunner and pin_factory is cv.pinned_paths
        and preflight_factory is pre.preflight)
    pins = source_pins()
    paths = pin_factory(installed, qwen_path)
    admission = preflight_factory()
    if (admission["status"] != pre.STATUS
            or admission["seed"] != SEED
            or admission["table_sha256"] != frozen.TABLE_SHA256
            or admission["planned_serial_native_calls"] != 48
            or admission["native_calls"] != 0
            or admission["jepa_weight"] != 0):
        raise ValueError("RUN117DG_PREFLIGHT_RED")
    validate(admission["rows"])
    out.mkdir(mode=0o700)
    report = {
        "schema": SCHEMA, "status": "INCOMPLETE",
        "evidence_class": ("LINUX_NATIVE_C3_NEW_NORMALIZED_SOURCE_ABLATION"
                           if actual_native_factory else "SYNTHETIC_SOFTWARE_ONLY"),
        "seed": SEED, "table_sha256": frozen.TABLE_SHA256,
        "source_pins": pins, "model_pins": admission["models"],
        "runner_sha256": cv.RUNNER_SHA,
        "model_callback_attempts": 0, "native_calls_verified": 0,
        "native_proof": False, "pins_unchanged": False,
        "rows": [], **NEGATIVE,
    }
    def save():
        atomic_write(out / "report.json", dumps(report))
    save()
    for row in admission["rows"]:
        f = frozen.fixtures()[row["index"]]
        rec = {
            "index": row["index"], "project": row["project"],
            "expected": f["expected_for_offline_scorer_only"],
            "source_sha256": row["source_sha256"],
            "source_ref_sha256": row["source_ref_sha256"],
            "current_source_ref_sha256": row["current_source_ref_sha256"],
            "raw_messages_sha256": row["raw_messages_sha256"],
            "normalized_messages_sha256": row["normalized_messages_sha256"],
            "arm_order": row["arm_order"], "arms": [],
        }
        report["rows"].append(rec)
        save()
        for arm_name in row["arm_order"]:
            model, mode = _arm(arm_name)
            messages = row[mode.lower() + "_messages"]
            arm = {
                "arm": arm_name, "model": model, "mode": mode,
                "status": "INCOMPLETE",
                "messages_sha256": row[mode.lower() + "_messages_sha256"],
                "native_output": "", "native_final": False,
                "process_reaped": False, "exact": False,
                "native_metrics": {}, "error_type": None,
                "parsed_action": None,
            }
            rec["arms"].append(arm)
            save()
            native = None
            try:
                if sha(dumps(messages).encode()) != arm["messages_sha256"]:
                    raise ValueError("RUN117DG_PROMPT_MUTATED_RED")
                native = runner_factory(installed, "C3_LANGUAGE", paths[model], CONFIG)
                report["model_callback_attempts"] += 1
                save()
                for chunk in native.generate(
                    messages, threading.Event(), time.monotonic() + 120,
                    128, run68.SCHEMA, seed=SEED):
                    if type(chunk) is not str:
                        raise TypeError("RUN117DG_NONSTRING_NATIVE_CHUNK_RED")
                    arm["native_output"] += chunk
                    save()
                arm["native_metrics"] = dict(native.last_metrics)
                arm["native_final"] = arm["native_metrics"].get("status") == "FINAL"
            except Exception as exc:
                arm["error_type"] = type(exc).__name__
                arm["error"] = str(exc)[:250]
            finally:
                if native is not None:
                    try:
                        proc = native.proc
                        arm["release"] = native.unload()
                        arm["process_reaped"] = (
                            proc is not None and proc.poll() is not None
                            and arm["release"].get("process_reaped") is True)
                    except Exception as exc:
                        arm["release_error_type"] = type(exc).__name__
                arm["raw_sha256"] = sha(arm["native_output"].encode())
                arm["exact"] = bool(run68.decode_schema(arm["native_output"])
                                    == f["expected_for_offline_scorer_only"])
                arm["parsed_action"] = run68.decode_schema(arm["native_output"])
                arm["status"] = (
                    "RECORDED" if arm["native_final"] and arm["process_reaped"]
                    and arm["native_metrics"].get("actual_model") == paths[model].name
                    and arm["error_type"] is None else "STRUCTURAL_RED")
                save()
    try:
        report["pins_unchanged"] = (
            source_pins() == pins and pin_factory(installed, qwen_path) == paths)
    except Exception:
        report["pins_unchanged"] = False
    report["summary"] = summarize(report)
    complete = report["summary"]["complete_native_receipts"]
    report["native_proof"] = bool(complete and actual_native_factory)
    report["native_calls_verified"] = 48 if report["native_proof"] else 0
    report["status"] = (
        ("EXPLORATORY_NORMALIZED_SOURCE_SIGNAL_NONPROMOTING"
         if any(report["summary"]["normalized_signal_by_model"].values())
         else "NO_EXPLORATORY_NORMALIZED_SOURCE_SIGNAL")
        if report["native_proof"] else (
            "SYNTHETIC_SOFTWARE_ONLY" if complete else "STRUCTURAL_RED"))
    save()
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--installed", type=Path, required=True)
    p.add_argument("--qwen", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    result = run(a.installed, a.qwen, a.out)
    print(dumps({"status": result["status"], "summary": result["summary"],
                 "model_callback_attempts": result["model_callback_attempts"],
                 "native_calls_verified": result["native_calls_verified"]}))
    return 0 if result["status"] != "STRUCTURAL_RED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
