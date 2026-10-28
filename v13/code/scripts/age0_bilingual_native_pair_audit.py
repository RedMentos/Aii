"""Verify two frozen Age0 Linux-native ZIPs and compare their lexical heldout scores.

Read-only, no model execution, no inference authority, no raw answer publication.
This is a posthoc integrity audit, not a blinded experiment or semantic gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from scripts import age0_bilingual_arith_scorer as scorer

ARMS = {
    "candidate": {
        "artifact": 12794815033,
        "sha256": "b64235b1adf9d1cf90139123790c887b4308d7ea6538aafc99fceab690fbc173",
        "source": "1cd099d0aa856dbca3205460affa613bd3780813",
        "prompt": scorer.CANDIDATE_PROMPT,
    },
    "baseline": {
        "artifact": 12794187079,
        "sha256": "2efe9bd177f8366626873da452041bd15ffcdc71ee96eb9567fed6d93fdf42ce",
        "source": "f7eb46206bf2f80fe6c81008095d376021a34920",
        "prompt": scorer.BASELINE_PROMPT,
    },
}
STAGES = ("BLOBS", "INSTALL", "BOOTSTRAP", "AGE0_PREFLIGHT", "CAPTURE",
          "REPORT_CHECK", "PRIVACY", "DIFF")
BLOB_PINS = {
    "v13/code/v13/runtime.py": "68e7ed1352800174972558f1e0b0683a42c8689a",
    "v13/code/v13/runners.py": "efda7aa1aa5729e974d0d641870d4da05d21c961",
    "v13/code/v13/models.py": "bd035cf8029850cce00b179edf533e53bf24358a",
    "v13/code/v13/toolstep.py": "9640b2ce9abfc08cb82f7b550e18d856d9513f08",
    "v13/code/specs/models.json": scorer.CATALOG_BLOB,
    "v13/code/specs/control_tools.json": "954a3f468f10195fbce12d27f68585ee7edee2c9",
    "v13/code/specs/age0-bilingual-arith-heldout-20261028.json": scorer.FIXTURE_BLOB,
    "v13/code/scripts/age0_bilingual_arith_scorer.py": "0348b17dedc0e4142a73a8ad8c93a57a2c7d6491",
    "v13/code/scripts/age0_bilingual_arith_native_collector.py": "a0a94ce08983b0621990c5b9c2f4712463e146bb",
}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require(ok, reason):
    if not ok:
        raise ValueError(reason)


def _load_json(z, name):
    return json.loads(z.read(name))


def verify_archive(path: Path, arm: str, expected_sha: str | None = None):
    """Check archive, embedded raw, model/age/score binding, then return no raw answers."""
    pin = ARMS[arm]
    _require(digest(Path(path).read_bytes()) == (expected_sha or pin["sha256"]),
             arm + ": archive SHA256 mismatch")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        _require(len(names) == len(set(names)), arm + ": duplicate ZIP member")
        _require(all(not n.startswith("/") and ".." not in Path(n).parts and "\\" not in n
                     for n in names), arm + ": unsafe ZIP member")
        _require(z.testzip() is None, arm + ": ZIP CRC mismatch")
        checks = z.read("SHA256SUMS.txt").decode().splitlines()
        seen = set()
        for line in checks:
            parts = line.split(maxsplit=1)
            _require(len(parts) == 2, arm + ": malformed SHA256SUMS")
            want, name = parts
            name = name.removeprefix("*").removeprefix("./")
            _require(name in names and name != "SHA256SUMS.txt" and name not in seen,
                     arm + ": missing/duplicate hash entry")
            seen.add(name)
            _require(digest(z.read(name)) == want, arm + ": internal SHA256 mismatch: " + name)
        _require(seen == set(names) - {"SHA256SUMS.txt"}, arm + ": unhashed ZIP member")
        for stage in STAGES:
            _require(z.read(stage + "_EXIT.txt").decode().strip() == "0",
                     arm + ": native stage RED: " + stage)
        _require(z.read("HEAD.txt").decode().strip() == pin["source"],
                 arm + ": HEAD drift")
        blob_lines = z.read("EXPECTED_BLOBS.txt").decode().splitlines()
        got_lines = z.read("BLOBS_RAW.log").decode().splitlines()
        _require(len(blob_lines) == len(got_lines), arm + ": blob readback count")
        observed = {}
        for a, b in zip(blob_lines, got_lines):
            want, name = a.split(maxsplit=1)
            parts = b.split(maxsplit=2)
            _require(len(parts) == 3 and parts == [want, want, name],
                     arm + ": blob readback mismatch")
            _require(name not in observed, arm + ": duplicate blob path")
            observed[name] = want
        _require(observed == {**BLOB_PINS, "v13/code/v13/prompts.py": pin["prompt"]},
                 arm + ": pinned source blobs differ")
        manifest_bytes = z.read("native/ANSWERS.json")
        raw_bytes = z.read("native/RAW_ROWS.jsonl")
        manifest = json.loads(manifest_bytes)
        report = _load_json(z, "native/CAPTURE_RESULT.json")
        recorded_score = _load_json(z, "native/SCORE.json")
        _require(manifest.get("source_commit") == report.get("source_commit") == pin["source"],
                 arm + ": source binding")
        _require(manifest.get("prompt_git_blob") == report.get("prompt_git_blob") == pin["prompt"],
                 arm + ": prompt binding")
        _require(manifest.get("model_catalog_git_blob") == report.get("catalog_git_blob")
                 == scorer.CATALOG_BLOB, arm + ": catalog binding")
        _require(report.get("raw_sha256") == digest(raw_bytes)
                 and report.get("manifest_sha256") == digest(manifest_bytes),
                 arm + ": raw/manifest digest mismatch")
        _require(report.get("schema") == "v13.age0.bilingual_numeric_native_capture.v1"
                 and report.get("evidence_kind") == "LINUX_NATIVE_AGE0_IF_VERIFIED"
                 and report.get("rows") == report.get("final_rows") == 16,
                 arm + ": capture status mismatch")
        _require(report.get("phone_measured") is False
                 and report.get("whole_system_complete") is False
                 and report.get("same_brain_fresh_sessions_not_global_state_isolation") is True
                 and type(report.get("jepa_weight")) is int and report["jepa_weight"] == 0,
                 arm + ": promotion boundary")
        items = scorer.fixture()
        rows = manifest.get("rows")
        raw_lines = raw_bytes.decode().splitlines()
        _require(isinstance(rows, list) and len(rows) == len(raw_lines) == len(items),
                 arm + ": row count mismatch")
        raw_rows = [json.loads(line) for line in raw_lines]
        event_ids = set()
        for item, row, raw in zip(items, rows, raw_rows):
            _require(row.get("id") == raw.get("id") == item["id"]
                     and row.get("prompt") == raw.get("prompt") == item["prompt"]
                     and raw.get("lang") == item["lang"], arm + ": ordered identity mismatch")
            _require(row.get("answer") == raw.get("answer")
                     and raw.get("answer_sha256") == digest(row["answer"].encode()),
                     arm + ": answer/raw hash mismatch")
            _require(row.get("status") == raw.get("status") == "FINAL"
                     and row.get("runner_role") == raw.get("runner_role")
                     and row.get("runner_model_sha256") == raw.get("runner_model_sha256"),
                     arm + ": final/runner mismatch")
            _require(row.get("runner_model_sha256") == scorer.ROLE_MODELS.get(row["runner_role"]),
                     arm + ": actual runner model identity")
            _require(raw.get("error") is None and isinstance(raw.get("event_id"), str)
                     and raw["event_id"] not in event_ids, arm + ": native error/event collision")
            event_ids.add(raw["event_id"])
            meta = raw.get("metadata")
            _require(isinstance(meta, dict) and meta.get("tool_call") == row.get("tool_call")
                     and meta.get("tool_shadow") == row.get("tool_shadow"),
                     arm + ": raw tool metadata mismatch")
            _require(row.get("tool_call") is None and row.get("learning_mode") == "RECORD_ONLY"
                     and type(row.get("jepa_weight")) is int and row["jepa_weight"] == 0,
                     arm + ": Age0 authority drift")
        # The frozen scorer is re-run independently on the byte-exact supplied manifest.
        # Reproduce it in memory without publishing any raw answer text.
        expected_items = []
        counts = {"numeric": 0, "numeric_proxy_match": 0,
                  "unsupported": 0, "unsupported_uncertainty_marker": 0}
        for item, row in zip(items, rows):
            if item["kind"] == "numeric":
                match = scorer.numeric_proxy(row["answer"], item)
                counts["numeric"] += 1
                counts["numeric_proxy_match"] += int(match)
            else:
                _require(item["kind"] == "unsupported", arm + ": invalid fixture kind")
                match = bool(scorer.UNKNOWN.search(row["answer"]))
                counts["unsupported"] += 1
                counts["unsupported_uncertainty_marker"] += int(match)
            expected_items.append({"id": item["id"], "lang": item["lang"],
                                   "kind": item["kind"], "lexical_proxy_match": match,
                                   "runner_role": row["runner_role"],
                                   "answer_sha256": digest(row["answer"].encode())})
        _require(recorded_score.get("schema") == "v13.age0.bilingual_numeric_offline_score.v1"
                 and recorded_score.get("evidence_kind") == "SOFTWARE_OFFLINE_SCORER_ONLY"
                 and recorded_score.get("fixture_git_blob") == scorer.FIXTURE_BLOB
                 and recorded_score.get("external_native_claims_verified") is False
                 and recorded_score.get("semantic_grounding_verified") is False
                 and recorded_score.get("phone_measured") is False
                 and recorded_score.get("whole_system_complete") is False
                 and recorded_score.get("step2_utility") == "FAIL"
                 and recorded_score.get("b3_l1") == "FAIL"
                 and recorded_score.get("body_jepa") == "UNAVAILABLE"
                 and recorded_score.get("lp3_heldout") == "FAIL", arm + ": score claim drift")
        _require(len(recorded_score.get("runs", [])) == 1, arm + ": unexpected scorer arms")
        scored = recorded_score["runs"][0]
        _require(scored.get("input_sha256") == digest(manifest_bytes)
                 and scored.get("source_commit") == pin["source"]
                 and scored.get("prompt_git_blob") == pin["prompt"]
                 and scored.get("counts") == counts
                 and scored.get("items") == expected_items, arm + ": scorer recomputation mismatch")
        return {"arm": arm, "artifact_id": pin["artifact"], "zip_sha256": digest(Path(path).read_bytes()),
                "source_commit": pin["source"], "prompt_git_blob": pin["prompt"],
                "raw_sha256": digest(raw_bytes), "manifest_sha256": digest(manifest_bytes),
                "internal_sha256_verified": len(seen), "native_stage_exits_zero": len(STAGES),
                "counts": counts, "items": expected_items,
                "claim_limit": "Linux-native source-bound lexical scoring only"}


def compare(candidate, baseline):
    a = {x["id"]: x for x in candidate["items"]}
    b = {x["id"]: x for x in baseline["items"]}
    _require(set(a) == set(b), "paired ID mismatch")
    numeric_wins = [k for k in a if a[k]["kind"] == "numeric" and a[k]["lexical_proxy_match"]
                    and not b[k]["lexical_proxy_match"]]
    numeric_losses = [k for k in a if a[k]["kind"] == "numeric" and b[k]["lexical_proxy_match"]
                      and not a[k]["lexical_proxy_match"]]
    return {"schema": "v13.age0.bilingual_paired_native_integrity_audit.v1",
            "evidence_kind": "LINUX_NATIVE_ARCHIVE_INTEGRITY_PLUS_LEXICAL_PROXY",
            "candidate": {k: v for k, v in candidate.items() if k != "items"},
            "baseline": {k: v for k, v in baseline.items() if k != "items"},
            "numeric_wins_candidate": numeric_wins,
            "numeric_losses_candidate": numeric_losses,
            "paired_route_changed_ids": [k for k in a if a[k]["runner_role"] != b[k]["runner_role"]],
            "unsupported_marker_changes": [k for k in a if a[k]["kind"] == "unsupported"
                                           and a[k]["lexical_proxy_match"] != b[k]["lexical_proxy_match"]],
            "frozen_scorer_not_modified": True, "human_semantic_review": "NOT_AUTOMATED",
            "phone_measured": False, "step2_utility": "FAIL", "b3_l1": "FAIL",
            "body_jepa": "UNAVAILABLE", "lp3_heldout": "FAIL", "jepa_weight": 0,
            "age0_learning_mode": "RECORD_ONLY", "whole_system_complete": False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--candidate", required=True, type=Path)
    ap.add_argument("--baseline", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)
    result = compare(verify_archive(args.candidate, "candidate"),
                     verify_archive(args.baseline, "baseline"))
    if args.out.exists():
        raise FileExistsError("Refuse to overwrite existing audit")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, sort_keys=True, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({"candidate": result["candidate"]["counts"],
                      "baseline": result["baseline"]["counts"],
                      "numeric_wins_candidate": result["numeric_wins_candidate"],
                      "numeric_losses_candidate": result["numeric_losses_candidate"],
                      "paired_route_changed_ids": result["paired_route_changed_ids"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())