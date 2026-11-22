"""Seed83 preregistered isolated native German C3 -> arithmetic SHADOW pilot.

No live ToolStep/C5 consumer, no learning or age override. Original raw retained.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import threading
import time
import traceback

from v13.agi import listarith
from v13.agi import listarith_de_shadow_v2_candidate as german
from v13.agi import listarith_de_shadow_pipeline as pipeline
from v13.common import file_hash
from v13.config import initialize
from v13.models import ModelManager
from v13.runners import LlamaRunner

CODE = Path(__file__).resolve().parents[1]
FIXTURE = CODE / "specs/listarith_de83_native_shadow_frozen.json"
PINS = {
    "fixture": "cc052aa9eaecd213124f9c79df15f30637c5a80c",
    "pipeline": "25cacd7388e5464dd814f4b18c545e2ec2f78b54",
    "german": "f9791c84846db660e9bde0e002defa55321f47b3",
    "listarith": "35893e9f829a591ffb9a792a73cef9bce986b3c4",
    "runners": "efda7aa1aa5729e974d0d641870d4da05d21c961",
    "models": "7af05962af41d0bc3f7dd18ef01d4eba55eabf99",
}
MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REVISION = "657e078c94084481950a2d555a941481f715536b"
BINARY_SHA256 = "79e312188dc1d75c28201771f106e91de470b5cebdd838d31bb4db25eecf5d39"
GATES = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
         "redmi_measured", "whole_system_complete")


def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fixtures():
    paths = {
        "fixture": FIXTURE,
        "pipeline": Path(pipeline.__file__),
        "german": Path(german.__file__),
        "listarith": Path(listarith.__file__),
        "runners": CODE / "v13/runners.py",
        "models": CODE / "specs/models.json",
    }
    for name, path in paths.items():
        if blob_sha(path) != PINS[name]:
            raise ValueError("FROZEN_SOURCE_CHANGED:" + name)
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = data["rows"]
    if (data.get("schema") != "v13.de83.native_shadow.v1"
            or data.get("seed") != 83 or len(rows) != 24
            or [data.get(k) for k in
                ("supported_total", "supported_difference", "unsupported")] != [12, 4, 8]):
        raise ValueError("FIXTURE_SCHEMA_CHANGED")
    if len({r["id"] for r in rows}) != 24 or len({r["text"] for r in rows}) != 24:
        raise ValueError("FIXTURE_DUPLICATE_ID_OR_TEXT")
    for row in rows:
        op = row["expected_operation"]
        vals = row["values"]
        if (not isinstance(row["text"], str) or not row["text"].strip()
                or len(row["text"]) > listarith.MAX_TEXT
                or not 2 <= len(vals) <= 8
                or not all(isinstance(v["name"], str) and v["name"]
                           and type(v["number"]) is int for v in vals)
                or op not in ("total", "difference_max_min", None)):
            raise ValueError("FIXTURE_ROW_INVALID")
        nums = [v["number"] for v in vals]
        expected = (sum(nums) if op == "total" else
                    max(nums) - min(nums) if op == "difference_max_min" else None)
        if row["expected_answer"] != expected:
            raise ValueError("FIXTURE_ANSWER_MISMATCH")
    return rows


def invented_numbers(values, text):
    """Read-only occurrence guard; source name binding is separately stricter."""
    tokens = Counter(s.replace("−", "-").lstrip("+")
                     for s in listarith._INT.findall(text))
    got = Counter(str(v["number"]) for v in values
                  if not listarith.AGGREGATE.fullmatch(v["name"]))
    return sum(max(0, count - tokens[number]) for number, count in got.items())


def score(row, shadow):
    """Preregistered supported/unsupported exact outcome, no partial credit."""
    op = row["expected_operation"]
    emitted = shadow["status"] == "SHADOW_RESULT"
    if op is None:
        return {"supported": False, "correct": not emitted,
                "wrong_emitted": False, "unsupported_false_positive": emitted,
                "abstain_supported": False}
    correct = emitted and shadow["operation"] == op and shadow["value"] == row["expected_answer"]
    return {"supported": True, "correct": bool(correct),
            "wrong_emitted": bool(emitted and not correct),
            "unsupported_false_positive": False,
            "abstain_supported": not emitted}


def outcome(rows, all_reaped):
    complete = sum(r["status"] == "NATIVE_ROW_COMPLETE" for r in rows)
    supported_correct = sum(r["score"]["correct"] for r in rows
                            if r.get("score", {}).get("supported"))
    supported_wrong = sum(r["score"]["wrong_emitted"] for r in rows
                          if r.get("score", {}).get("supported"))
    unsupported_fp = sum(r["score"]["unsupported_false_positive"] for r in rows
                         if r.get("score", {}).get("supported") is False)
    invented = sum(r.get("invented_nonaggregate", 0) for r in rows)
    if complete != 24 or not all_reaped:
        status = "PILOT_PARTIAL_RED"
    elif supported_correct >= 12 and supported_wrong <= 1 and unsupported_fp == 0 and invented == 0:
        status = "NATIVE_DE83_SHADOW_PILOT_SIGNAL"
    else:
        status = "NATIVE_DE83_SHADOW_NOT_SUPPORTED"
    return {"status": status, "native_completed": complete,
            "supported_correct": supported_correct, "supported_wrong_emitted": supported_wrong,
            "unsupported_false_positive": unsupported_fp,
            "invented_nonaggregate": invented, "all_processes_reaped": all_reaped}


def native_capture(home, out):
    home, out = Path(home), Path(out)
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    raw_dir = out / "raw"
    raw_dir.mkdir()
    rows = fixtures()
    cfg = initialize(home)
    if (cfg["learning_mode"] != "RECORD_ONLY"
            or cfg["system_stage"] != 0 or cfg["latents_enabled"]
            or cfg.get("jepa_weight", 0) != 0):
        raise ValueError("AGE_OR_JEPA_CONFIG_CHANGED")
    mm = ModelManager(home)
    verified = mm.verify(deep=True)
    if ("language" not in verified or not verified["language"]["ok"]
            or not verified["language"]["hash_checked"]):
        raise ValueError("LANGUAGE_MODEL_NOT_HASH_VERIFIED")
    if mm.revision("C3_LANGUAGE") != MODEL_REVISION:
        raise ValueError("C3_REVISION_CHANGED")
    model_path = mm.path_for("C3_LANGUAGE")
    if file_hash(model_path) != MODEL_SHA256:
        raise ValueError("MODEL_SHA256_CHANGED")
    runner_manifest = json.loads((home / "config/runner.json").read_text())
    if (runner_manifest.get("binary_sha256") != BINARY_SHA256
            or file_hash(home / "bin/llama-server") != BINARY_SHA256):
        raise ValueError("NATIVE_BINARY_SHA256_CHANGED")
    report_rows = []
    for index, row in enumerate(rows):
        record = {"index": index, "id": row["id"], "text": row["text"],
                  "expected": row["values"],
                  "expected_operation": row["expected_operation"],
                  "expected_answer": row["expected_answer"],
                  "native_model": model_path.name,
                  "model_sha256": MODEL_SHA256, "source_exact": True,
                  "learning_mode": "RECORD_ONLY", "jepa_weight": 0,
                  "step2_gate_promoted": False, "b3_promoted": False,
                  "body_jepa_available": False, "redmi_measured": False,
                  "whole_system_complete": False}
        runner = LlamaRunner(home, "C3_LANGUAGE", model_path, cfg)
        started = time.monotonic()
        try:
            cancel = threading.Event()
            deadline = time.monotonic() + 75
            messages = [{"role": "system", "content": listarith.READ_SYSTEM},
                        {"role": "user", "content": row["text"]}]
            raw = "".join(runner.generate(messages, cancel, deadline,
                                          max_tokens=192, schema=listarith.READ_SCHEMA,
                                          seed=83))
            record["raw_output"] = raw
            parsed = pipeline.parse_typed(raw)
            record["parsed"] = parsed
            record["invented_nonaggregate"] = invented_numbers(parsed, row["text"])
            record["shadow"] = pipeline.evaluate(row["text"], raw)
            record["score"] = score(row, record["shadow"])
            record["native_metrics"] = runner.last_metrics
            record["native_pid"] = runner.proc.pid if runner.proc else None
            if (record["native_pid"] is None
                    or runner.last_metrics.get("status") != "FINAL"):
                raise ValueError("NATIVE_FINAL_OR_PID_MISSING")
            record["status"] = "NATIVE_ROW_COMPLETE"
        except BaseException as exc:
            record["status"] = "NATIVE_ROW_RED"
            record["error_type"] = type(exc).__name__
            record["error_message"] = str(exc)[:400]
            record["traceback"] = traceback.format_exc()[-1800:]
            record["native_metrics"] = runner.last_metrics
            record["native_pid"] = runner.proc.pid if runner.proc else None
        finally:
            record["release"] = runner.unload()
            record["postclose_process_reaped"] = bool(
                record["release"]["process_reaped"] and runner.proc is None)
            record["elapsed_s"] = time.monotonic() - started
            (raw_dir / ("%02d_%s.json" % (index, row["id"]))).write_text(
                json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                encoding="utf-8")
        report_rows.append({k: record[k] for k in (
            "index", "id", "status", "score", "shadow", "native_pid",
            "invented_nonaggregate", "postclose_process_reaped", "elapsed_s")
            if k in record})
    all_reaped = len(report_rows) == 24 and all(r["postclose_process_reaped"] for r in report_rows)
    result = outcome(report_rows, all_reaped)
    result.update(schema="v13.de83.native_shadow.report.v1", seed=83,
                  fixture_blob=PINS["fixture"], source_blobs=PINS,
                  model_revision=MODEL_REVISION, model_sha256=MODEL_SHA256,
                  native_binary_sha256=BINARY_SHA256, model_verification=verified,
                  rows=report_rows, evidence_level="LINUX_NATIVE_NOT_REDMI",
                  live_tool_execution=False, external_action_authority=False,
                  learning_mode="RECORD_ONLY", jepa_weight=0,
                  step2_gate_promoted=False, b3_promoted=False,
                  body_jepa_available=False, redmi_measured=False,
                  whole_system_complete=False)
    (out / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps({k: result[k] for k in
                      ("status", "native_completed", "supported_correct",
                       "supported_wrong_emitted", "unsupported_false_positive",
                       "invented_nonaggregate", "all_processes_reaped")}))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    native_capture(args.home, args.out)


if __name__ == "__main__":
    main()
