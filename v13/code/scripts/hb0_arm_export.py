"""HB0b: exact-source matched arm export; software-only, NO native/model proof.

Model-facing prompts are allowlisted strings, not serialized fixture dicts.
The separate answer key must NEVER be supplied to a model. Public synthetic
fixtures are not a blind held-out evaluation cohort.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from scripts import hb0_split_information_cohort as hb0
from scripts import context_option_safe_scope_candidate as safe

SCHEMA = "v13.hb0.arm_export.v1"
ARMS = ("c3_only", "b1_only", "b2_only", "both_exact",
        "single_body_dual", "shuffled_b1")
SYSTEM = (
    "You are deciding between Option A and Option B for the current project. "
    "Use only supplied exact source texts for that project. If a required "
    "rule or option is missing, say UNKNOWN rather than guessing. "
    "Do not treat a foreign project's source as current evidence."
)


def _bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _need(ok, reason):
    if not ok:
        raise ValueError(reason)


def _foreign_sheet(row, rows):
    # Same sheet variant but from the next family; NEVER re-label its header.
    other_family = (row["family"] + 1) % hb0.FAMILIES
    match = [r for r in rows if r["family"] == other_family
             and r["sheet_index"] == row["sheet_index"]
             and r["rule_index"] == row["rule_index"]]
    _need(len(match) == 1 and match[0]["id"] != row["id"],
          "HB0_FOREIGN_MATCH_RED")
    return match[0]["b1_source"]


def _prompt(row, arm, rows):
    _need(arm in ARMS, "HB0_ARM_INVALID")
    current = row["current"]
    rule, sheet = row["b2_source"], row["b1_source"]
    if arm == "c3_only":
        user = "Current request:\n" + current
    elif arm == "b1_only":
        user = "Current request:\n" + current + "\n\nB1_DETAIL exact source:\n" + sheet
    elif arm == "b2_only":
        user = "Current request:\n" + current + "\n\nB2_GIST exact source:\n" + rule
    elif arm == "both_exact":
        user = ("Current request:\n" + current
                + "\n\nB2_GIST exact source:\n" + rule
                + "\n\nB1_DETAIL exact source:\n" + sheet)
    elif arm == "single_body_dual":
        user = ("Current request:\n" + current
                + "\n\nSingle-body combined exact context:\n" + rule + "\n" + sheet)
    else:
        user = ("Current request:\n" + current
                + "\n\nB2_GIST exact source:\n" + rule
                + "\n\nB1_DETAIL foreign control source:\n" + _foreign_sheet(row, rows))
    return {
        "id": row["id"], "arm": arm, "partition": row["partition"],
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
    }


def build(rows, expected_fixture_sha256):
    """Construct 900 matched model-facing inputs and a separate answer key.

    The external expected SHA must come from a separately recorded cohort
    registration. Never auto-rewrite that pin from current fixture bytes.
    """
    _need(type(expected_fixture_sha256) is str
          and len(expected_fixture_sha256) == 64
          and all(c in "0123456789abcdef" for c in expected_fixture_sha256),
          "HB0_EXTERNAL_SHA_REQUIRED")
    _need(hb0._sha(rows) == expected_fixture_sha256, "HB0_COHORT_DRIFT_RED")
    hb0.validate(rows)
    prompts = [_prompt(row, arm, rows) for row in rows for arm in ARMS]
    answers = [
        {"id": row["id"], "oracle_action": row["oracle_action"],
         "partition": row["partition"], "family": row["family"]}
        for row in rows
    ]
    ids = {(p["id"], p["arm"]) for p in prompts}
    _need(len(prompts) == 900 and len(ids) == 900 and len(answers) == 150,
          "HB0_ARM_COVERAGE_RED")
    for p in prompts:
        raw = json.dumps(p, ensure_ascii=False)
        _need("oracle_action" not in raw and "sheet_index" not in raw
              and "rule_index" not in raw, "HB0_MODEL_PAYLOAD_LEAK_RED")
    # Negative control: a foreign B1 sheet is not admissible evidence.
    for row in rows:
        foreign = _foreign_sheet(row, rows)
        got = safe.decide_safe(row["current"], [row["b2_source"], foreign])
        _need(got["action"] == "UNKNOWN", "HB0_SHUFFLED_SOURCE_COMMIT_RED")
    return prompts, answers


def _jsonl(rows):
    return b"".join(_bytes(row) for row in rows)


def export(out_dir, expected_fixture_sha256):
    rows = hb0.fixtures()
    prompts, answers = build(rows, expected_fixture_sha256)
    out_dir = Path(out_dir)
    if out_dir.exists() or out_dir.is_symlink():
        raise FileExistsError("FRESH_HB0_ARM_DIRECTORY_REQUIRED")
    out_dir.mkdir(parents=True, exist_ok=False)
    files = {
        "prompts.jsonl": _jsonl(prompts),
        "answers.jsonl": _jsonl(answers),
    }
    for name, raw in files.items():
        with (out_dir / name).open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    manifest = {
        "schema": SCHEMA,
        "status": "MODEL_INPUT_PREPARED_SOFTWARE_ONLY_NO_GATE",
        "source_fixture_sha256": expected_fixture_sha256,
        "source_git_blob_expected": "329153aaa73df009fdc433523994e372e0fd2c95",
        "arms": list(ARMS), "prompts": 900, "answers": 150,
        "calibration_prompts": 180, "structural_holdout_prompts": 720,
        "sha256": {name: _sha(raw) for name, raw in files.items()},
        "answer_key_is_model_input": False,
        "native_calls": 0, "model_called": False,
        "canonical_gate_pass": False, "step2_status": "UTILITY_FAIL",
        "b3_status": "FAIL", "jepa_weight": 0,
        "redmi_measured": False, "whole_system_complete": False,
        "claim_limit": "Public synthetic arm export; no blind native or model utility",
    }
    with (out_dir / "manifest.json").open("xb") as handle:
        handle.write(_bytes(manifest))
        handle.flush()
        os.fsync(handle.fileno())
    return manifest


def verify(out_dir, expected_fixture_sha256):
    out_dir = Path(out_dir)
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    _need(manifest.get("schema") == SCHEMA
          and manifest.get("source_fixture_sha256") == expected_fixture_sha256
          and manifest.get("arms") == list(ARMS)
          and manifest.get("prompts") == 900 and manifest.get("answers") == 150
          and manifest.get("canonical_gate_pass") is False
          and manifest.get("answer_key_is_model_input") is False,
          "HB0_MANIFEST_RED")
    _need(manifest.get("source_git_blob_expected")
          == "329153aaa73df009fdc433523994e372e0fd2c95",
          "HB0_SOURCE_BLOB_DRIFT_RED")
    # A malicious/accidental edit can rewrite BOTH data and its manifest hash.
    # Compare against the independently regenerated, SHA-pinned cohort too.
    expected_prompts, expected_answers = build(hb0.fixtures(), expected_fixture_sha256)
    expected_bytes = {"prompts.jsonl": _jsonl(expected_prompts),
                      "answers.jsonl": _jsonl(expected_answers)}
    for name in ("prompts.jsonl", "answers.jsonl"):
        raw = (out_dir / name).read_bytes()
        _need(_sha(raw) == manifest["sha256"][name], "HB0_EXPORT_HASH_RED")
        _need(raw == expected_bytes[name], "HB0_EXPORT_CONTENT_DRIFT_RED")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--fixture-sha256", required=True)
    args = parser.parse_args(argv)
    manifest = export(args.out_dir, args.fixture_sha256)
    verify(args.out_dir, args.fixture_sha256)
    print(json.dumps({"status": manifest["status"], "sha256": manifest["sha256"],
                      "prompts": manifest["prompts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
