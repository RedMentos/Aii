"""Seed79: isolated pinned native C3 German typed-value reading; NO TOOL AUTHORITY.

One fresh native C3 process per synthetic row. Retain original raw and errors.
This is not a STEP2, B3, Body-JEPA, Redmi or whole-system gate.
"""
from __future__ import annotations
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import threading
import time
import traceback

from v13.agi import listarith
from v13.common import file_hash
from v13.config import initialize
from v13.models import ModelManager
from v13.runners import LlamaRunner

CODE = Path(__file__).resolve().parents[1]
FIXTURE = CODE / "specs" / "c3_de_native_typed_read_seed79.json"
PINS = {
    "fixture": "d0a840c9546fd87c3f7ef15f450b4650aaa06863",
    "listarith": "35893e9f829a591ffb9a792a73cef9bce986b3c4",
    "runners": "efda7aa1aa5729e974d0d641870d4da05d21c961",
    "models": "7af05962af41d0bc3f7dd18ef01d4eba55eabf99",
}
MODEL_SHA256 = "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d"
MODEL_REVISION = "657e078c94084481950a2d555a941481f715536b"
SCHEMA = "v13.c3.de.typed_read.seed79.v1"
GATES = ("step2_gate_promoted", "b3_promoted", "body_jepa_available",
         "redmi_measured", "whole_system_complete")


def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fixtures():
    paths = {"fixture": FIXTURE,
             "listarith": Path(listarith.__file__),
             "runners": CODE / "v13" / "runners.py",
             "models": CODE / "specs" / "models.json"}
    for name, path in paths.items():
        if blob_sha(path) != PINS[name]:
            raise ValueError("FROZEN_SOURCE_CHANGED:" + name)
    d = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = d["rows"]
    if d.get("schema") != SCHEMA or d.get("seed") != 79 or len(rows) != 12:
        raise ValueError("FIXTURE_SCHEMA_CHANGED")
    if len({r["id"] for r in rows}) != 12 or len({r["text"] for r in rows}) != 12:
        raise ValueError("FIXTURE_ID_COLLISION")
    for row in rows:
        if not (isinstance(row["text"], str) and row["text"].strip()
                and 2 <= len(row["values"]) <= 4
                and all(type(v["number"]) is int and v["name"] for v in row["values"])):
            raise ValueError("FIXTURE_ROW_INVALID")
    return rows


def parse_raw(raw):
    obj = json.loads(raw)
    if not isinstance(obj, dict) or set(obj) != {"values"} or not isinstance(obj["values"], list):
        raise ValueError("SCHEMA_VALUES_INVALID")
    if len(obj["values"]) > 8:
        raise ValueError("SCHEMA_VALUES_TOO_LONG")
    values = []
    for item in obj["values"]:
        if (not isinstance(item, dict) or set(item) != {"name", "number"}
                or not isinstance(item["name"], str)
                or not item["name"].strip() or len(item["name"]) > 40
                or type(item["number"]) is not int):
            raise ValueError("SCHEMA_ITEM_INVALID")
        values.append({"name": item["name"], "number": item["number"]})
    return values


def measure(values, row):
    """Exact name/number set with multiplicity, original text number guard."""
    filtered = [v for v in values if not listarith.AGGREGATE.match(v["name"])]
    aggregate = len(values) - len(filtered)
    want = Counter((v["name"].strip().casefold(), v["number"]) for v in row["values"])
    got = Counter((v["name"].strip().casefold(), v["number"]) for v in filtered)
    # Reuse frozen source-number occurrence guard, not just set membership.
    source_numbers = Counter(s.replace("−", "-").lstrip("+")
                             for s in listarith._INT.findall(row["text"]))
    got_numbers = Counter(str(v["number"]) for v in filtered)
    invented = sum(max(0, count - source_numbers[n])
                   for n, count in got_numbers.items())
    return {"exact": got == want, "aggregate_read": aggregate,
            "invented_nonaggregate": invented,
            "expected": row["values"], "filtered": filtered,
            "raw_values": values}


def native_capture(home, out):
    home, out = Path(home), Path(out)
    if out.exists():
        raise FileExistsError("FRESH_OUTPUT_REQUIRED")
    out.mkdir(parents=True)
    raw_dir = out / "raw"
    raw_dir.mkdir()
    rows = fixtures()
    cfg = initialize(home)
    if cfg["learning_mode"] != "RECORD_ONLY" or cfg.get("jepa_weight", 0) != 0:
        raise ValueError("AGE_OR_JEPA_CONFIG_CHANGED")
    mm = ModelManager(home)
    verified = mm.verify(deep=True)
    if "language" not in verified or not verified["language"]["ok"] or not verified["language"]["hash_checked"]:
        raise ValueError("LANGUAGE_MODEL_NOT_HASH_VERIFIED")
    if mm.revision("C3_LANGUAGE") != MODEL_REVISION:
        raise ValueError("C3_REVISION_CHANGED")
    model_path = mm.path_for("C3_LANGUAGE")
    if file_hash(model_path) != MODEL_SHA256:
        raise ValueError("C3_MODEL_SHA256_CHANGED")
    runner_manifest = json.loads((home / "config/runner.json").read_text())
    native_binary = home / "bin/llama-server"
    if file_hash(native_binary) != runner_manifest["binary_sha256"]:
        raise ValueError("NATIVE_BINARY_HASH_CHANGED")
    report_rows = []
    for index, row in enumerate(rows):
        record = {"index": index, "id": row["id"], "text": row["text"],
                  "expected": row["values"], "native_model": model_path.name,
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
            raw = "".join(runner.generate(messages, cancel, deadline, max_tokens=192,
                                          schema=listarith.READ_SCHEMA, seed=79))
            record["raw_output"] = raw
            record["parsed"] = parse_raw(raw)
            record["score"] = measure(record["parsed"], row)
            record["native_metrics"] = runner.last_metrics
            record["native_pid"] = runner.proc.pid if runner.proc else None
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
            (raw_dir / f'{index:02d}_{row["id"]}.json').write_text(
                json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8")
        report_rows.append({k: record[k] for k in
                            ("index", "id", "status", "score", "native_pid",
                             "postclose_process_reaped", "elapsed_s")
                            if k in record})
    completed = sum(r["status"] == "NATIVE_ROW_COMPLETE" for r in report_rows)
    exact = sum(r.get("score", {}).get("exact") is True for r in report_rows)
    invented = sum(r.get("score", {}).get("invented_nonaggregate", 0) for r in report_rows)
    aggregate = sum(r.get("score", {}).get("aggregate_read", 0) for r in report_rows)
    reaped = all(r["postclose_process_reaped"] for r in report_rows)
    status = ("PILOT_PARTIAL_RED" if completed != 12 or not reaped else
              "NATIVE_C3_DE_READ_SUPPORTED" if exact >= 9 and invented == 0 else
              "NATIVE_C3_DE_READ_NOT_SUPPORTED")
    result = {"schema": "v13.c3.de.native_typed_read.seed79.report.v1",
              "seed": 79, "fixture_blob": PINS["fixture"], "source_blobs": PINS,
              "model_revision": MODEL_REVISION, "model_sha256": MODEL_SHA256,
              "native_binary_sha256": runner_manifest["binary_sha256"],
              "model_verification": verified, "rows": report_rows,
              "completed": completed, "exact": exact,
              "invented_nonaggregate": invented, "aggregate_read": aggregate,
              "all_processes_reaped": reaped, "status": status,
              "evidence_level": "LINUX_NATIVE_NOT_REDMI", "live_tool_execution": False,
              "external_action_authority": False, "learning_mode": "RECORD_ONLY",
              "jepa_weight": 0, "step2_gate_promoted": False,
              "b3_promoted": False, "body_jepa_available": False,
              "redmi_measured": False, "whole_system_complete": False}
    (out / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    print(json.dumps({"status": status, "completed": completed,
                      "exact": exact, "invented_nonaggregate": invented,
                      "aggregate_read": aggregate, "all_processes_reaped": reaped}))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--home", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    native_capture(args.home, args.out)


if __name__ == "__main__":
    main()
