#!/usr/bin/env python3
"""Run582: fail-closed future native stage-source retention; no model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

ROOT_FILES = ("RUN500_STAGE_MAP.json", "RUN504_SCHEDULE.json",
              "RUN558_BATCH_PLAN.json", "RUN558_BATCH_PROGRESS.jsonl",
              "RUN558_BATCH_RESULT.json", "RUN558_INSTALLED_PREFLIGHT.json")
STAGE_FILES = ("RUN500_STAGE_PREREG.json", "RUN500_INSTALLED_PREFLIGHT.json",
               "RUN500_STAGE_RESULT.json")
STAGE_ID = re.compile(r"[A-E]_s([0-9]+)_p[0-9]{2}\Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def required_stage_names(stage_id, seed):
    match = STAGE_ID.fullmatch(stage_id)
    if match is None or type(seed) is not int or seed < 0 or int(match.group(1)) != seed:
        raise ValueError("STAGE_ID_SEED_MISMATCH")
    return STAGE_FILES + (f"step2_{stage_id[0]}_s{seed}.json",
                          f"tool_{stage_id[0]}_s{seed}.json",
                          f"summary_{stage_id[0]}_s{seed}.json")


def read_regular(root, relative):
    parts = Path(relative).parts
    if any((root / Path(*parts[:i])).is_symlink() for i in range(1, len(parts))):
        raise ValueError("UNSAFE_STAGE_PARENT:" + relative)
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ValueError("MISSING_STAGE_SOURCE:" + relative)
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > 12_000_000:
        raise ValueError("UNSAFE_STAGE_SOURCE:" + relative)
    return path.read_bytes()



def canonical_digest(value):
    """Match Run500/504 canonical JSON hash without importing native dependencies."""
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8"))


def exact_row_coverage(rows, stage, source):
    """Require all and only the registered fixture x variant keys; count alone is insufficient."""
    expected = stage.get("row_keys")
    if (type(expected) is not list or len(expected) != 14
            or any(type(k) is not list or len(k) != 4
                   or k[:2] != [stage["arm"], stage["seed"]]
                   or type(k[2]) is not str or type(k[3]) is not str for k in expected)):
        raise ValueError("STAGE_PREREG_ROW_KEYS_INVALID:" + stage["id"])
    required = [(key[2], key[3]) for key in expected]
    if (len(set(required)) != 14 or type(rows) is not list or len(rows) != 14
            or any(type(r) is not dict or type(r.get("fixture")) is not str
                   or type(r.get("variant")) is not str for r in rows)):
        raise ValueError("STAGE_ROW_COVERAGE_INVALID:" + source)
    observed = [(row["fixture"], row["variant"]) for row in rows]
    if len(set(observed)) != 14 or set(observed) != set(required):
        raise ValueError("STAGE_ROW_COVERAGE_INVALID:" + source)


def collect(work):
    work = Path(work)
    if not work.is_dir() or work.is_symlink():
        raise ValueError("BATCH_WORK_MISSING")
    files = {name: read_regular(work, name) for name in ROOT_FILES}
    def load(name):
        return json.loads(files[name])
    full, plan, batch = load("RUN500_STAGE_MAP.json"), load("RUN558_BATCH_PLAN.json"), load("RUN558_BATCH_RESULT.json")
    schedule = load("RUN504_SCHEDULE.json")
    stage_ids = plan["stage_ids"]
    if (plan.get("full_stage_map_sha256") != canonical_digest(full)
            or plan.get("source_schedule_sha256") != canonical_digest(schedule)
            or schedule.get("full_stage_map_sha256") != canonical_digest(full)
            or plan.get("batch_id") != batch.get("batch_id")):
        raise ValueError("FROZEN_BATCH_SOURCE_BINDING_CHANGED")
    scheduled = next((item for item in schedule.get("batches", [])
                      if item.get("id") == plan["batch_id"]), None)
    if scheduled is None or scheduled.get("stage_ids") != stage_ids:
        raise ValueError("FROZEN_BATCH_SCHEDULE_CHANGED")
    selected = [next((stage for stage in full["stages"] if stage["id"] == sid), None)
                for sid in stage_ids]
    if any(stage is None for stage in selected):
        raise ValueError("STAGE_NOT_REGISTERED")
    keys = [key for stage in selected for key in stage["row_keys"]]
    if (plan.get("fixture_pairs") != [stage["fixture_ids"] for stage in selected]
            or scheduled.get("fixture_pairs") != plan["fixture_pairs"]
            or plan.get("expected_rows") != 14 * len(stage_ids)
            or scheduled.get("expected_rows") != plan["expected_rows"]
            or plan.get("row_keys_sha256") != canonical_digest(keys)
            or scheduled.get("row_keys_sha256") != plan["row_keys_sha256"]):
        raise ValueError("FROZEN_BATCH_ROW_KEYS_CHANGED")
    if (type(stage_ids) is not list or not 1 <= len(stage_ids) <= 3
            or len(stage_ids) != len(set(stage_ids)) or batch["stage_ids"] != stage_ids
            or batch["rows_verified"] != 14 * len(stage_ids)
            or batch["canonical_gate_pass"] is not False
            or batch["step2_exit"] != "UTILITY_FAIL"):
        raise ValueError("FROZEN_BATCH_CHANGED")
    receipt_map = {r["stage_id"]: r for r in batch["stage_receipts"]}
    if len(receipt_map) != len(batch["stage_receipts"]) or set(receipt_map) != set(stage_ids):
        raise ValueError("STAGE_RECEIPT_SET_CHANGED")
    for stage_id in stage_ids:
        registered = next((s for s in full["stages"] if s["id"] == stage_id), None)
        if registered is None:
            raise ValueError("STAGE_NOT_REGISTERED")
        seed = registered["seed"]
        names = required_stage_names(stage_id, seed)
        folder = "stage_" + stage_id + "/"
        for name in names:
            relative = folder + name
            files[relative] = read_regular(work, relative)
        prereg = json.loads(files[folder + "RUN500_STAGE_PREREG.json"])
        result = json.loads(files[folder + "RUN500_STAGE_RESULT.json"])
        tool = json.loads(files[folder + f"tool_{stage_id[0]}_s{seed}.json"])
        report = json.loads(files[folder + f"step2_{stage_id[0]}_s{seed}.json"])
        summary = json.loads(files[folder + f"summary_{stage_id[0]}_s{seed}.json"])
        exact_row_coverage(tool.get("rows"), registered, stage_id + ":tool")
        exact_row_coverage(report.get("rows"), registered, stage_id + ":step2")
        if (prereg != registered or result["stage_id"] != stage_id
                or result["rows_verified"] != 14
                or result["canonical_gate_pass"] is not False
                or result["step2_exit"] != "UTILITY_FAIL"
                or len(tool["rows"]) != 14 or len(report["rows"]) != 14
                or summary["seed"] != seed
                or receipt_map[stage_id]["receipt_sha256"] != sha(files[folder + "RUN500_STAGE_RESULT.json"])
                or result["tool_sha256"] != sha(files[folder + f"tool_{stage_id[0]}_s{seed}.json"])
                or result["summary_sha256"] != sha(files[folder + f"summary_{stage_id[0]}_s{seed}.json"])):
            raise ValueError("STAGE_SOURCE_BINDING_CHANGED:" + stage_id)
    if sum(len(value) for value in files.values()) > 40_000_000:
        raise ValueError("BUNDLE_TOO_LARGE")
    for name, data in files.items():
        if name.endswith(".jsonl"):
            for line in data.splitlines():
                json.loads(line)
        else:
            json.loads(data)
    return files, stage_ids


def bundle(work, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("REFUSE_EXISTING_BUNDLE")
    files, stages = collect(work)
    output.mkdir(parents=True, exist_ok=False)
    copied = {}
    for relative, data in sorted(files.items()):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as f:
            f.write(data)
        copied[relative] = {"bytes": len(data), "sha256": sha(data)}
    manifest = {"schema": "V13_RUN582_FUTURE_STAGE_SOURCE_BUNDLE_V1",
                "status": "COMPLETE_STAGE_SOURCE_BUNDLE_ONLY",
                "stage_ids": stages, "stage_count": len(stages),
                "expected_raw_files": len(ROOT_FILES) + len(stages) * 6,
                "copied": copied,
                "native_execution_independently_verified": False,
                "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
                "body_jepa": "UNAVAILABLE", "b3_l1": "FAIL",
                "jepa_weight": 0, "redmi_measured": False}
    with (output / "RUN582_SAFE_MANIFEST.json").open("x", encoding="utf-8") as f:
        json.dump(manifest, f, sort_keys=True, indent=2)
        f.write("\n")
    return manifest


def inspect_safe_zip(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("SAFE_ZIP_MISSING")
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        names = [info.filename for info in infos]
        if (len(names) != len(set(names)) or z.testzip() is not None or
                any(info.is_dir() or stat.S_ISLNK(info.external_attr >> 16)
                    or name.startswith("/") or "\\" in name
                    or any(part in ("", ".", "..") for part in name.split("/"))
                    for name, info in zip(names, infos))):
            raise ValueError("SAFE_ZIP_INVALID")
        plan = json.loads(z.read("RUN558_BATCH_PLAN.json"))
        full = json.loads(z.read("RUN500_STAGE_MAP.json"))
        for stage_id in plan["stage_ids"]:
            stage = next(s for s in full["stages"] if s["id"] == stage_id)
            for name in required_stage_names(stage_id, stage["seed"]):
                relative = "stage_" + stage_id + "/" + name
                if relative not in names:
                    raise ValueError("MISSING_STAGE_SOURCE:" + relative)
        return {"status": "ALL_REGISTERED_STAGE_SOURCE_FILES_PRESENT",
                "stages": len(plan["stage_ids"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--work", type=Path)
    mode.add_argument("--inspect-safe-zip", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.work is not None:
        if args.out is None:
            raise ValueError("OUTPUT_REQUIRED")
        result = bundle(args.work, args.out)
    else:
        if args.out is not None:
            raise ValueError("INSPECT_IS_READ_ONLY")
        result = inspect_safe_zip(args.inspect_safe_zip)
    print(json.dumps({"status": result["status"],
                      "stage_count": result.get("stage_count", result.get("stages"))},
                     sort_keys=True))


if __name__ == "__main__":
    main()
