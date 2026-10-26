#!/usr/bin/env python3
"""Run527: offline, fail-closed Run509 five-stage safe-artifact source score.

This cannot independently prove native execution. The workflow pins GitHub
Actions artifact IDs, run heads, conclusions and ZIP metadata digests before
calling this script. Never import model files or silently repair source rows.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

import run513_b2_receipt_postflight as postflight
import run516_b2_aggregate as aggregate

STAGES = (
    ("p00", 515, 40313344309, 12646720408, "FAILURE",
     "24f5f802b700c82f9e57f59bd3345dd6dd1e4f53",
     "4e7b53a2b6438562693b441c648338463df7d10258bb657f3ef821f696a3f534"),
    ("p01", 519, 40316152651, 12646924065, "SUCCESS",
     "0e193755a446f837b848d143fcce582fa486979f",
     "95a72b76dba6a2f439ed149cba6073ea52de42490d48de91e006880821462cba"),
    ("p02", 522, 40317501670, 12648010609, "SUCCESS",
     "1ae99e718d2ac0e6c9710622086c3966be48c703",
     "c2e8c93c013ef08d98a23756b37b076b5d2be3ac1b09fcea4af03b87797eda97"),
    ("p03", 525, 40318195227, 12648610677, "SUCCESS",
     "9292d2874e31c08b2572ef19f38e07273c15770b",
     "007299f558f98e45971dbd33cce5ab023428f9eab59d13faa4e3af8781518fc2"),
    ("p04", 526, 40318794946, 12648581506, "SUCCESS",
     "5d9dd6277be8a25000e7e0709bf188850c0e0ece",
     "2e1511ebf8fba9737aa3eb3a02ac5580755ff1df33e815db2df221b1466a1663"),
)


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def no_constant(value):
    raise ValueError("NONFINITE_JSON_" + value)


def no_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def decode_json(data):
    return json.loads(data.decode("utf-8"), parse_constant=no_constant,
                      object_pairs_hook=no_duplicate_keys)


def validate_safe_stage(path, index):
    stage_id, run_number, _, _, _, _, _ = STAGES[index]
    root = Path(path)
    require(root.is_dir() and not root.is_symlink() and
            root.name == stage_id, "SAFE_STAGE_DIR_INVALID")
    manifest_name = f"RUN{run_number}_SAFE_MANIFEST.json"
    manifest_path = root / manifest_name
    require(manifest_path.is_file() and not manifest_path.is_symlink(),
            "SAFE_MANIFEST_MISSING")
    manifest = decode_json(manifest_path.read_bytes())
    require(type(manifest) is dict and
            manifest.get("status") == "SAFE_NO_MODEL_COPY_NOT_NATIVE_PROOF" and
            type(manifest.get("copied")) is dict and
            manifest.get("canonical_gate_pass") is False and
            manifest.get("step2_exit") == "UTILITY_FAIL" and
            manifest.get("redmi_measured") is False,
            "SAFE_MANIFEST_SCHEMA_OR_GATE_DRIFT")
    copied = manifest["copied"]
    require(len(copied) == (11 if index == 0 else 13),
            "SAFE_FILE_COUNT_DRIFT")
    expected_names = {
        "RUN511_STAGE_PLAN.json", "RUN511_INSTALLED_PREFLIGHT.json",
        "RUN511_PROGRESS.jsonl", "RUN511_OBSERVATIONS_RAW.jsonl",
        "RUN511_STAGE_RESULT.json",
    }
    expected_names |= {
        f"RUN511_PREP_{fixture}_s{seed}.json"
        for fixture in (("Arbor", "Bracken") if index == 0 else
                        ("Cobalt", "Dahlia") if index == 1 else
                        ("Eclipse", "Fjord") if index == 2 else
                        ("Garnet", "Harbor") if index == 3 else
                        ("Iris", "Juniper"))
        for seed in (41, 42, 43)
    }
    if index:
        expected_names |= {"RUN513_POSTFLIGHT.json",
                           "RUN513_VERIFIED_METRIC_ROWS.json"}
    require(set(copied) == expected_names,
            "SAFE_REQUIRED_FILES_OR_STAGE_FIXTURES_DRIFT")
    require({p.name for p in root.iterdir()} == expected_names | {manifest_name},
            "SAFE_UNLISTED_OR_MISSING_FILE")
    total = 0
    bindings = {}
    for name, metadata in copied.items():
        require(type(name) is str and "/" not in name and "\\" not in name and
                name not in (".", "..") and
                type(metadata) is dict and
                set(metadata) == {"sha256", "bytes"} and
                type(metadata["bytes"]) is int and 0 < metadata["bytes"] <= 10_000_000 and
                type(metadata["sha256"]) is str and
                len(metadata["sha256"]) == 64,
                "SAFE_MEMBER_METADATA_INVALID")
        path = root / name
        info = path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
                info.st_size == metadata["bytes"], "SAFE_MEMBER_NOT_REGULAR")
        data = path.read_bytes()
        require(sha(data) == metadata["sha256"], "SAFE_MEMBER_HASH_MISMATCH")
        if name.endswith(".jsonl"):
            require(data.endswith(b"\n") and bool(data),
                    "SAFE_INCOMPLETE_JSONL")
            for line in data.splitlines():
                require(bool(line), "SAFE_BLANK_JSONL")
                decode_json(line)
        else:
            decode_json(data)
        total += len(data)
        require(total <= 25_000_000, "SAFE_TOTAL_TOO_LARGE")
        bindings[name] = metadata["sha256"]
    require(manifest.get("total_bytes") == total,
            "SAFE_TOTAL_BYTES_DRIFT")
    return {"stage_id": stage_id, "source_run": STAGES[index][2],
            "original_conclusion": STAGES[index][4],
            "safe_artifact_id": STAGES[index][3],
            "safe_zip_metadata_sha256": STAGES[index][6],
            "manifest_sha256": sha(manifest_path.read_bytes()),
            "member_count": len(copied), "member_sha256": bindings}


def replay_and_score(root, output_dir):
    root = Path(root)
    output_dir = Path(output_dir)
    require(root.is_dir() and not root.is_symlink() and
            output_dir.is_dir() and not output_dir.is_symlink(),
            "ROOT_OR_OUTPUT_INVALID")
    dirs = [root / stage[0] for stage in STAGES]
    safe = [validate_safe_stage(path, i) for i, path in enumerate(dirs)]
    # p00's original native workflow was RED at the historical schema auditor.
    # Never mutate the original artifact; these are new files in the temporary
    # downloaded copy, with original FAILURE provenance retained in the report.
    report, rows = postflight.audit(dirs[0], 0)
    postflight.write_exclusive(dirs[0] / "RUN513_POSTFLIGHT.json", report)
    postflight.write_exclusive(dirs[0] / "RUN513_VERIFIED_METRIC_ROWS.json", rows)
    summary, metric_rows, scored = aggregate.aggregate(dirs)
    require(summary["observation_count"] == 60 and
            summary["paired_primary_count"] == 24 and
            summary["native_execution_independently_confirmed"] is False and
            summary["canonical_gate_pass"] is False and
            scored["native_evidence_verified"] is False and
            scored["step2_exit"] == "UTILITY_FAIL",
            "OFFLINE_SCORE_CLAIM_DRIFT")
    output = {
        "schema": "V13_RUN527_FROZEN_FIVE_NATIVE_SAFE_ARTIFACT_OFFLINE_SCORE_V1",
        "status": "OFFLINE_FIVE_STAGE_60_ROW_SOURCE_QUOTE_DIAGNOSTIC_ONLY",
        "safe_artifacts": safe,
        "original_p00_actions_conclusion": "FAILURE",
        "original_p00_postflight_replayed_only": True,
        "source_bound_rows": 60,
        "paired_primary_rows": 24,
        "primary_focus_minus_base_rows": scored["primary_focus_minus_base_rows"],
        "preregistered_descriptive_gain_reached":
            scored["preregistered_descriptive_gain_reached"],
        "run516_summary_sha256": sha(aggregate.canonical(summary)),
        "run510_metric_sha256": sha(aggregate.canonical(scored)),
        "native_execution_independently_confirmed": False,
        "false_prior_rule_assertions_in_summaries_evaluated": False,
        "canonical_gate_pass": False, "step2_exit": "UTILITY_FAIL",
        "b3_l1": "FAIL", "body_jepa": "UNAVAILABLE",
        "jepa_weight": 0, "redmi_measured": False,
        "whole_v13_complete": False,
        "claim_limit": "Five exact GitHub safe artifact metadata pins and source-ref receipt replay; not independent raw ZIP/native proof, no C3 summary or STEP2 semantic utility.",
    }
    for name, value in (
        ("RUN527_AGGREGATE.json", output),
        ("RUN527_RUN516_SUMMARY.json", summary),
        ("RUN527_RUN510_METRIC.json", scored),
        ("RUN527_REDUCED_ROWS.json", metric_rows),
    ):
        postflight.write_exclusive(output_dir / name, value)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(replay_and_score(args.stage_root, args.output_dir),
                     sort_keys=True, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
