"""Run527 synthetic strict safe-artifact input tests; never claim native."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run527_b2_artifact_score as run527


def make_stage(root, index):
    stage, run, *_ = run527.STAGES[index]
    path = root / stage
    path.mkdir()
    fixture_pairs = (
        ("Arbor", "Bracken"), ("Cobalt", "Dahlia"),
        ("Eclipse", "Fjord"), ("Garnet", "Harbor"),
        ("Iris", "Juniper"),
    )
    names = {
        "RUN511_STAGE_PLAN.json", "RUN511_INSTALLED_PREFLIGHT.json",
        "RUN511_PROGRESS.jsonl", "RUN511_OBSERVATIONS_RAW.jsonl",
        "RUN511_STAGE_RESULT.json",
    }
    names |= {
        f"RUN511_PREP_{name}_s{seed}.json"
        for name in fixture_pairs[index] for seed in (41, 42, 43)
    }
    if index:
        names |= {"RUN513_POSTFLIGHT.json",
                  "RUN513_VERIFIED_METRIC_ROWS.json"}
    copied = {}
    for name in sorted(names):
        data = (b'{"row":1}\n' if name.endswith(".jsonl")
                else b'{"ok":true}\n')
        (path / name).write_bytes(data)
        copied[name] = {"sha256": hashlib.sha256(data).hexdigest(),
                        "bytes": len(data)}
    manifest = {
        "status": "SAFE_NO_MODEL_COPY_NOT_NATIVE_PROOF",
        "copied": copied,
        "total_bytes": sum(v["bytes"] for v in copied.values()),
        "canonical_gate_pass": False,
        "step2_exit": "UTILITY_FAIL",
        "redmi_measured": False,
    }
    manifest_path = path / f"RUN{run}_SAFE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    return path, manifest_path


class Run527SafeArtifactContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_all_five_exact_safe_stage_contracts(self):
        for index in range(5):
            path, _ = make_stage(self.root, index)
            record = run527.validate_safe_stage(path, index)
            self.assertEqual(record["stage_id"], f"p{index:02d}")
            self.assertEqual(record["member_count"], 11 if index == 0 else 13)
            self.assertEqual(record["original_conclusion"],
                             "FAILURE" if index == 0 else "SUCCESS")

    def test_modified_member_refused(self):
        path, _ = make_stage(self.root, 0)
        (path / "RUN511_STAGE_PLAN.json").write_text('{"ok":null}\n')
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            run527.validate_safe_stage(path, 0)

    def test_symlink_refused(self):
        path, _ = make_stage(self.root, 1)
        target = path / "RUN511_STAGE_PLAN.json"
        target.unlink()
        target.symlink_to(path / "RUN511_STAGE_RESULT.json")
        with self.assertRaisesRegex(ValueError, "NOT_REGULAR"):
            run527.validate_safe_stage(path, 1)

    def test_unlisted_member_refused(self):
        path, _ = make_stage(self.root, 2)
        (path / "extra.txt").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "UNLISTED"):
            run527.validate_safe_stage(path, 2)

    def test_bad_negative_gate_refused(self):
        path, manifest_path = make_stage(self.root, 3)
        d = json.loads(manifest_path.read_text())
        d["canonical_gate_pass"] = True
        manifest_path.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError, "GATE_DRIFT"):
            run527.validate_safe_stage(path, 3)

    def test_missing_original_red_row_refused(self):
        path, _ = make_stage(self.root, 0)
        (path / "RUN511_OBSERVATIONS_RAW.jsonl").unlink()
        with self.assertRaisesRegex(ValueError, "UNLISTED_OR_MISSING"):
            run527.validate_safe_stage(path, 0)

    def test_nonfinite_and_duplicate_json_refused(self):
        with self.assertRaisesRegex(ValueError, "NONFINITE"):
            run527.decode_json(b'{"x":NaN}')
        with self.assertRaisesRegex(ValueError, "DUPLICATE"):
            run527.decode_json(b'{"x":1,"x":2}')

    def test_p00_cannot_be_forged_green(self):
        self.assertEqual(run527.STAGES[0][4], "FAILURE")
        self.assertNotEqual(run527.STAGES[0][4], run527.STAGES[1][4])


if __name__ == "__main__":
    unittest.main()
