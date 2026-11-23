"""Preregistered disjoint C3 typed-value paired Linux-native diagnostic.

Arms: frozen READ_SYSTEM vs explicit name/number instruction, same model and
schema; deterministic no-model regex control. SHADOW_ONLY, no live tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import threading
import time

from scripts import listarith_de_operator_shadow as operator
from scripts import listarith_de83_native_shadow as original
from v13.agi import listarith
from v13.agi import listarith_de_shadow_pipeline as pipeline
from v13.agi import listarith_de_closedworld_candidate as closedworld
from v13.runners import LlamaRunner

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "specs/c3_typedread_paired109_frozen.json"
FIXTURE_BLOB = "8b27c1dce8b83d7964b56405d3fdd7e8a4eb2181"
SEED = 109
EXPLICIT_SYSTEM = (
    "Read only item-name and integer pairs in the user's German list. "
    "The name is ONLY the word immediately before the integer, never include "
    "the number in the name. The number must be the literal integer "
    "immediately after that name. Do not number items by position. "
    'Return JSON only with values: [{"name":"word","number":integer}, ...]. '
    "Do not calculate anything."
)
PAIR = re.compile(r"(?<![A-Za-zÄÖÜäöüß])([A-Za-zÄÖÜäöüß]+)\s+([+-]?\d+)(?=,|\.)")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def frozen_rows():
    if original.blob_sha(FIXTURE) != FIXTURE_BLOB:
        raise ValueError("FROZEN_109_FIXTURE_CHANGED")
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = data["rows"]
    if (data.get("schema") != "v13.c3.typedread.paired109.v1"
            or data.get("seed") != SEED or len(rows) != 8
            or len({r["id"] for r in rows}) != 8
            or len({r["text"] for r in rows}) != 8):
        raise ValueError("FROZEN_109_SCHEMA_CHANGED")
    original_texts = {r["text"] for r in original.fixtures()}
    original_texts.add(
        "Inventar: Birke 4, Komet 13, Welle 8. Wie hoch ist die Summe?")
    for row in rows:
        if row["text"] in original_texts:
            raise ValueError("COHORT_NOT_DISJOINT")
        values = row["expected_values"]
        if (not 2 <= len(values) <= 8
                or len({v["name"] for v in values}) != len(values)
                or not all(type(v["number"]) is int for v in values)):
            raise ValueError("FROZEN_VALUES_INVALID")
        nums = [v["number"] for v in values]
        op = row["expected_operation"]
        expected = (sum(nums) if op == "total" else
                    max(nums) - min(nums) if op == "difference_max_min" else None)
        if row["expected_answer"] != expected:
            raise ValueError("FROZEN_ANSWER_CHANGED")
        if deterministic_pairs(row["text"]) != values:
            raise ValueError("DETERMINISTIC_BASELINE_NOT_EXACT")
    return rows


def deterministic_pairs(text):
    """Very narrow no-model baseline for this one-sentence list syntax."""
    data = text.split(". ", 1)[0] + "."
    return [{"name": name, "number": int(n)} for name, n in PAIR.findall(data)]


def native_read(home, cfg, model_path, text, system):
    runner = None
    receipt = {"native_attempted": True, "native_final": False,
               "postclose_process_reaped": False, "native_pid": None,
               "native_metrics": None, "release": None,
               "error_type": None, "raw_output": None}
    raw = None
    try:
        runner = LlamaRunner(home, "C3_LANGUAGE", model_path, cfg)
        raw = "".join(runner.generate(
            [{"role": "system", "content": system},
             {"role": "user", "content": text}],
            threading.Event(), time.monotonic() + 75,
            max_tokens=192, schema=listarith.READ_SCHEMA, seed=SEED))
        receipt["native_metrics"] = runner.last_metrics
        receipt["native_pid"] = runner.proc.pid if runner.proc else None
        receipt["native_final"] = bool(
            type(receipt["native_pid"]) is int
            and isinstance(runner.last_metrics, dict)
            and runner.last_metrics.get("status") == "FINAL")
    except BaseException as exc:
        receipt["error_type"] = type(exc).__name__
        receipt["error_message"] = str(exc)[:200]
    finally:
        if runner is not None:
            try:
                receipt["release"] = runner.unload()
                receipt["postclose_process_reaped"] = bool(
                    receipt["release"]["process_reaped"] and runner.proc is None)
            except BaseException as exc:
                receipt["release_error_type"] = type(exc).__name__
    if receipt["native_final"] and receipt["postclose_process_reaped"] and not (
            receipt["error_type"] or receipt.get("release_error_type")):
        receipt["raw_output"] = raw
    receipt["admitted"] = operator._native_receipt_admissible(receipt)
    return receipt


def run(home, out):
    rows = frozen_rows()
    home, cfg, model_path = operator._native_preflight(home)
    report = {
        "schema": "v13.c3.typedread.paired109.result.v1",
        "seed": SEED, "fixture_blob": FIXTURE_BLOB,
        "model_sha256": original.MODEL_SHA256,
        "binary_sha256": original.BINARY_SHA256,
        "arm_a_system_sha256": sha(listarith.READ_SYSTEM.encode()),
        "arm_b_system_sha256": sha(EXPLICIT_SYSTEM.encode()),
        "learning_mode": "RECORD_ONLY", "authority": "SHADOW_ONLY",
        "native_attempted": True, "redmi_measured": False,
        "live_tool_execution": False, "external_action_authority": False,
        "step2_gate_promoted": False, "b3_promoted": False,
        "body_jepa_available": False, "jepa_weight": 0,
        "whole_system_complete": False,
        "rows": [], "counts": {"A_exact": 0, "B_exact": 0,
                               "D_exact": 0, "A_shadow_correct": 0,
                               "B_shadow_correct": 0, "native_admitted": 0},
    }
    for index, row in enumerate(rows):
        record = {"id": row["id"], "source_sha256": sha(row["text"].encode()),
                  "expected_answer": row["expected_answer"],
                  "expected_operation": row["expected_operation"],
                  "D_values": deterministic_pairs(row["text"]), "arms": {}}
        report["counts"]["D_exact"] += int(record["D_values"] == row["expected_values"])
        for arm in ("A", "B") if index % 2 == 0 else ("B", "A"):
            system = listarith.READ_SYSTEM if arm == "A" else EXPLICIT_SYSTEM
            receipt = native_read(home, cfg, model_path, row["text"], system)
            admitted = receipt["admitted"]
            report["counts"]["native_admitted"] += int(admitted)
            if admitted:
                raw = receipt["raw_output"]
                try:
                    values = pipeline.parse_typed(raw)
                    exact = (sorted((v["name"], v["number"]) for v in values)
                             == sorted((v["name"], v["number"])
                                       for v in row["expected_values"]))
                except (ValueError, TypeError, KeyError):
                    exact = False
                baseline = pipeline.evaluate(row["text"], raw)
                closed = closedworld.evaluate(row["text"], raw)
                correct = (closed["status"] == "SHADOW_RESULT"
                           and closed["operation"] == row["expected_operation"]
                           and closed["value"] == row["expected_answer"])
            else:
                exact = False
                baseline = None
                closed = None
                correct = False
            report["counts"][arm + "_exact"] += int(exact)
            report["counts"][arm + "_shadow_correct"] += int(correct)
            record["arms"][arm] = {
                "receipt": receipt, "raw_sha256": (
                    sha(receipt["raw_output"].encode()) if admitted else None),
                "typed_exact": exact, "baseline": baseline,
                "closedworld": closed, "shadow_correct": correct}
        report["rows"].append(record)
    operator._write_private_new(out, report)
    return report["counts"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(args.home, args.out), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
