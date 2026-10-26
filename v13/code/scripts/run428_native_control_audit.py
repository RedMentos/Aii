#!/usr/bin/env python3
"""Run428: no-model negative-control audit of actual Run418 seed20 native rows.

Checks outer artifact and all declared inner hashes before reading rows.
Reports no raw prompts/answers. Diagnostic only: no native rerun or gate promotion.
"""
import argparse
import hashlib
import json
import math
import stat
import zipfile
from pathlib import Path, PurePosixPath

ARMS = ("O", "P", "S")
FIXTURES = ("Alder", "Beacon", "Cypress", "Delta", "Ember", "Fable")
VARIANTS = ("b1_only", "b2_only", "both_none", "both_exact", "both_control",
            "same_policy_dual", "prompt_only_dual")
COMPARE = ("b1_only", "same_policy_dual", "both_exact")
EXPECTED = {(f, v) for f in FIXTURES for v in VARIANTS}
MANIFEST = "RUN409_EXPORT_MANIFEST.json"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw if isinstance(raw, bytes) else raw.encode()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def safe_name(name):
    p = PurePosixPath(name)
    require(type(name) is str and bool(name) and not p.is_absolute() and
            not any(x in ("", ".", "..") for x in name.split("/")) and
            "\\" not in name and ":" not in name, "UNSAFE_ZIP_MEMBER")
    return name


def verified_archive(path, expected_sha):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and
            path.stat().st_nlink == 1, "ARCHIVE_SOURCE_UNSAFE")
    require(type(expected_sha) is str and len(expected_sha) == 64 and
            all(c in "0123456789abcdef" for c in expected_sha),
            "ARTIFACT_SHA_INVALID")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    require(h.hexdigest() == expected_sha, "OUTER_ARTIFACT_SHA_MISMATCH")
    z = zipfile.ZipFile(path)
    try:
        infos = z.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)) and MANIFEST in names,
                "ZIP_DUPLICATE_OR_MISSING_MANIFEST")
        for item in infos:
            safe_name(item.filename[:-1] if item.is_dir() else item.filename)
            kind = stat.S_IFMT((item.external_attr >> 16) & 0xffff)
            require(kind in ((0, stat.S_IFDIR) if item.is_dir() else
                             (0, stat.S_IFREG)), "ZIP_SPECIAL_FILE")
        manifest_raw = z.read(MANIFEST)
        manifest = json.loads(manifest_raw)
        copied = manifest.get("copied")
        require(manifest.get("schema") == "RUN409_SAFE_NATIVE_EXPORT_V1" and
                manifest.get("canonical_gate_pass") is False and
                manifest.get("step2_exit") == "UTILITY_FAIL" and
                type(copied) is dict and bool(copied), "EXPORT_MANIFEST_INVALID")
        files = {i.filename: i for i in infos if not i.is_dir()}
        require(set(files) == set(copied) | {MANIFEST},
                "ZIP_MANIFEST_INVENTORY_MISMATCH")
        total = 0
        for name, meta in copied.items():
            safe_name(name)
            require(type(meta) is dict and type(meta.get("bytes")) is int and
                    meta["bytes"] == files[name].file_size and
                    meta["bytes"] <= 64 * 1024 * 1024, "FILE_SIZE_INVALID")
            data = z.read(name)
            require(digest(data) == meta.get("sha256"),
                    "INNER_FILE_SHA_MISMATCH:" + name)
            total += len(data)
            require(total <= 256 * 1024 * 1024, "EXPORT_BUDGET_EXCEEDED")
        return z, {"manifest_sha256": digest(manifest_raw),
                   "verified_files": len(copied), "verified_bytes": total,
                   "artifact_sha256": expected_sha}
    except BaseException:
        z.close()
        raise


def checked_rows(report, label):
    rows = report.get("rows")
    hashes = report.get("row_sha256")
    require(type(rows) is list and type(hashes) is dict, "ROWS_MISSING:" + label)
    result = {}
    for row in rows:
        require(type(row) is dict, "ROW_NOT_OBJECT:" + label)
        key = (row.get("fixture"), row.get("variant"))
        require(key in EXPECTED and key not in result, "ROW_DUPLICATE_OR_UNKNOWN:" + label)
        require(hashes.get(":".join(key)) == digest(canonical(row)),
                "ROW_SHA_MISMATCH:" + label)
        require(row.get("status") == "RECORDED", "ROW_INCOMPLETE:" + label)
        result[key] = row
    require(set(result) == EXPECTED and set(hashes) == {":".join(k) for k in EXPECTED},
            "ROW_COVERAGE_MISMATCH:" + label)
    return result


def offer_digest(source_row, role):
    messages = source_row.get("consumer_messages")
    require(type(messages) is list, "CONSUMER_MESSAGES_MISSING")
    users = [m for m in messages if m.get("role") == "user"]
    require(len(users) == 1, "CONSUMER_USER_MESSAGE_INVALID")
    payload = json.loads(users[0]["content"])
    analysts = payload.get("analysts")
    require(type(analysts) is list, "ANALYSTS_MISSING")
    # same_policy_dual intentionally delivers two B1_DETAIL offers. Keep
    # the complete ordered list; collapsing to the first would hide changes.
    selected = [a for a in analysts if a.get("role") == role]
    return digest(canonical(selected)) if selected else None


def compare_rows(source, tool, left, right, variant):
    rows = {}
    for fixture in FIXTURES:
        key = (fixture, variant)
        x, y = tool[left][key], tool[right][key]
        a, b = source[left][key], source[right][key]
        score_x = x.get("score", {}).get("utility")
        score_y = y.get("score", {}).get("utility")
        require(all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1
                    for v in (score_x, score_y)), "INVALID_UTILITY")
        rows[fixture] = {
            "consumer_input_same": x["consumer_messages_sha256"] == y["consumer_messages_sha256"],
            "b1_offer_same": offer_digest(a, "B1_DETAIL") == offer_digest(b, "B1_DETAIL"),
            "b2_offer_same": offer_digest(a, "B2_GIST") == offer_digest(b, "B2_GIST"),
            "answer_same": x.get("answer") == y.get("answer"),
            "utility_delta": score_x - score_y,
        }
    return {
        "by_fixture": rows,
        "same_consumer_inputs": sum(r["consumer_input_same"] for r in rows.values()),
        "same_b1_offers": sum(r["b1_offer_same"] for r in rows.values()),
        "same_b2_offers": sum(r["b2_offer_same"] for r in rows.values()),
        "same_answers": sum(r["answer_same"] for r in rows.values()),
        "nonzero_utility_deltas": sum(r["utility_delta"] != 0 for r in rows.values()),
        "mean_utility_delta": sum(r["utility_delta"] for r in rows.values()) / len(rows),
        "paired_count": len(rows),
    }


def analyze(archive, expected_sha):
    z, evidence = verified_archive(archive, expected_sha)
    try:
        progress = json.loads(z.read("RUN397_PROGRESS.json"))
        require(set(progress.get("completed", {})) ==
                {"O_s20", "P_s20", "S_s20"} and
                progress.get("canonical_gate_pass") is False and
                progress.get("step2_exit") == "UTILITY_FAIL" and
                not progress.get("failures_preserved"), "PROGRESS_NOT_NATIVE126")
        frozen = json.loads(z.read("RUN394_PREREGISTERED_FIXTURES.json"))
        require(frozen.get("stage") == "FULL" and
                frozen.get("fixture_ids") == list(FIXTURES) and
                frozen.get("seeds") == [20, 21, 22] and
                set(frozen.get("arms", {})) == set(ARMS), "FROZEN_COHORT_MISMATCH")
        source, tool, receipts = {}, {}, {}
        for arm in ARMS:
            rid = f"{arm}_s20"
            pointer = progress["completed"][rid]["attempt"]
            safe_name(pointer)
            source_path = pointer + f"/step2_{rid}.json"
            tool_path = pointer + f"/tool_{rid}.json"
            sr, tr = json.loads(z.read(source_path)), json.loads(z.read(tool_path))
            source[arm] = checked_rows(sr, rid + ":source")
            tool[arm] = checked_rows(tr, rid + ":tool")
            for key in EXPECTED:
                srow, trow = source[arm][key], tool[arm][key]
                require(trow.get("consumer_messages_sha256") ==
                        digest(canonical(srow["consumer_messages"])),
                        "SOURCE_TOOL_REPLAY_MISMATCH:" + rid)
                require(trow.get("oracle_visible_to_native") is False,
                        "ORACLE_VISIBLE:" + rid)
            receipts[rid] = {"source_sha256": digest(z.read(source_path)),
                             "tool_sha256": digest(z.read(tool_path))}
        pairs = {}
        for left, right in (("P", "O"), ("P", "S"), ("O", "S")):
            pairs[left + "_minus_" + right] = {
                v: compare_rows(source, tool, left, right, v) for v in COMPARE}
        neg = pairs["P_minus_O"]["b1_only"]
        return {
            "run": "Run428", "status": "NATIVE_SEED20_CONTROL_SOURCE_AUDITED",
            "source": "ACTUAL_LINUX_NATIVE_RUN418_INDEPENDENT_RUN425",
            **evidence, "rows_verified": 126, "receipts": receipts,
            "pairs": pairs,
            "pointer_causal_attribution_supported_by_b1_control":
                neg["same_consumer_inputs"] == len(FIXTURES) and
                neg["nonzero_utility_deltas"] == 0,
            "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
            "redmi_measured": False, "jepa_weight": 0,
            "native_execution_performed": False,
            "claim_limit": "Seed20-only source identity; differences do not establish causal pointer benefit, STEP2/B3/Body-JEPA or Redmi."}
    finally:
        z.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive", type=Path, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = analyze(args.archive, args.expected_sha256)
        code = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError, zipfile.BadZipFile) as exc:
        result = {"run": "Run428", "status": "CONTROL_SOURCE_RED_PRESERVED",
                  "errors": [type(exc).__name__ + ": " + str(exc)[:350]],
                  "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL"}
        code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": result["status"],
                      "rows": result.get("rows_verified", 0),
                      "pointer_control_clean":
                      result.get("pointer_causal_attribution_supported_by_b1_control"),
                      "canonical_gate_pass": False}))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
