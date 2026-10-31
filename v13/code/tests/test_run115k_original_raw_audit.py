"""Synthetic adversarial validator tests; these are NOT native evidence."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.run115k_original_raw_audit import audit, ARMS, EXIT_NAMES, FIXTURE, HEAD

FROZEN = Path(__file__).parents[1] / "docs/fixtures/RUN115J_TYPED_JEF_ROLE_SEED997.json"


def _dumps(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"))


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, value in files.items():
            z.writestr(name, value)
    return buffer.getvalue()


def synthetic_artifact(change=None):
    fixture = json.loads(FROZEN.read_bytes())
    rows = []
    for source in fixture["rows"]:
        refs = [{"sha256": hashlib.sha256(t.encode()).hexdigest(),
                 "char_start": 0, "char_end": len(t), "source_id": "synthetic"}
                for t in (source["prior"], source["current"])]
        data = {"body_model_quote_verified": False, "source_transport_only": True,
                "sources": [{"text": t, "source_ref": ref} for t, ref in
                            zip((source["prior"], source["current"]), refs)]}
        arms = []
        for name in ARMS:
            payload = dict(data)
            if name == ARMS[1]:
                payload.update(typed_jef_candidate=source["oracle"], typed_candidate_authority=0)
            output = source["oracle"] if name == ARMS[1] else {"choice": "NONE", "remaining": None}
            if name == ARMS[0] and source["oracle"]["choice"] == "NONE":
                output = {"choice": "A", "remaining": 1}
            arms.append({"arm": name, "status": "RECORDED", "native_final": True,
                         "process_reaped": True, "native_metrics": {"status": "FINAL",
                         "actual_model": "LFM2.5-350M-QAD-Q4_0.gguf"},
                         "messages": [{"role": "system", "content": "Synthetic trusted system"},
                                      {"role": "user", "content": _dumps(payload)}],
                         "output": _dumps(output), "score": {"parsed": output,
                         "correct": int(output == source["oracle"])}})
        rows.append({"id": source["id"], "status": "RECORDED", "closed_store_ok": True,
                     "no_live_output": True, "source_refs": refs,
                     "typed_jef_candidate": source["oracle"], "arms": arms})
    report = {"fixture_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
              "native": True, "native_c3_calls": 12, "rows": rows,
              "native_b1_calls": 0, "native_b2_calls": 0, "native_jef_calls": 0,
              "delivery_authority": 0, "learning_authority": 0,
              "tool_dispatches": 0, "jepa_weight": 0, "native_c2": False,
              "native_jef": False, "output_committed": False,
              "redmi_measured": False, "whole_system_complete": False,
              "age0": "RECORD_ONLY", "scores": {ARMS[0]: 0, ARMS[1]: 6},
              "exploratory_role_signal": True, "status": "NATIVE_COMPLETE_TYPED_SIGNAL"}
    if change:
        change(report, fixture)
    phone = _zip({FIXTURE: FROZEN.read_bytes()})
    result = {"head": HEAD, "exits": {s: 0 for s in EXIT_NAMES},
              **{k: False for k in ("step2_promoted", "b3_promoted",
                 "body_jepa_promoted", "redmi_measured", "native_b1_executed",
                 "native_b2_executed", "native_c2_executed", "native_jef_executed")}}
    files = {"HEAD.txt": HEAD.encode(), "RESULT.json": _dumps(result).encode(),
             "NATIVE_CASE/report.json": _dumps(report).encode(),
             "V13-Phone-Run115J-Native.zip": phone}
    files.update({s + "_EXIT.txt": b"0\n" for s in EXIT_NAMES})
    manifest = "".join(hashlib.sha256(b).hexdigest() + "  ./" + n + "\n"
                       for n, b in sorted(files.items()))
    files["SHA256SUMS"] = manifest.encode()
    return _zip(files)


class IndependentAuditTests(unittest.TestCase):
    def check(self, change=None):
        b = synthetic_artifact(change)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "artifact.zip"
            path.write_bytes(b)
            return audit(path, expected_sha=hashlib.sha256(b).hexdigest())

    def test_synthetic_structure_only_passes(self):
        self.assertEqual(self.check()["scores"], {ARMS[0]: 0, ARMS[1]: 6})

    def test_source_in_system_role_refused(self):
        def change(r, f):
            r["rows"][0]["arms"][0]["messages"][0]["content"] += f["rows"][0]["prior"]
        with self.assertRaisesRegex(ValueError, "SYSTEM_SOURCE_LEAK"):
            self.check(change)

    def test_forged_source_ref_refused(self):
        def change(r, f):
            r["rows"][0]["source_refs"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_REFS"):
            self.check(change)

    def test_missing_process_reap_refused(self):
        def change(r, f):
            r["rows"][2]["arms"][1]["process_reaped"] = False
        with self.assertRaisesRegex(ValueError, "NATIVE_LIFECYCLE"):
            self.check(change)

    def test_report_score_tamper_refused(self):
        def change(r, f):
            r["scores"][ARMS[0]] = 6
        with self.assertRaisesRegex(ValueError, "REPORT_SCORES"):
            self.check(change)

    def test_control_arm_contamination_refused(self):
        def change(r, f):
            msg = r["rows"][0]["arms"][0]["messages"][1]
            data = json.loads(msg["content"])
            data["typed_jef_candidate"] = f["rows"][0]["oracle"]
            msg["content"] = _dumps(data)
        with self.assertRaisesRegex(ValueError, "CONTROL_CONTAMINATION"):
            self.check(change)

    def test_wrong_outer_hash_refused(self):
        b = synthetic_artifact()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "artifact.zip"
            path.write_bytes(b)
            with self.assertRaisesRegex(ValueError, "OUTER_SHA"):
                audit(path)


if __name__ == "__main__":
    unittest.main()
