"""Synthetic adversarial tests for Run116 original-native artifact auditor.

The fabricated artifacts here are NOT native/model/Redmi evidence.
"""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.run116_original_raw_audit import (
    audit, ARMS, BODY_MODELS, C3_MODEL, EXITS, FIXTURE, HEAD, PHONE_ZIP,
)

FROZEN = (Path(__file__).resolve().parents[1] /
          "docs/fixtures/RUN116_B1B2_JEF_C3_SEED1019.json")


def _dumps(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":")).encode()


def _zip(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return b.getvalue()


def _ref(text, label):
    return {"source_id": "synthetic-" + label,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "char_start": 0, "char_end": len(text), "modality": "text"}


def synthetic_artifact(change=None, stage=None):
    fixture = json.loads(FROZEN.read_bytes())
    rows = []
    for source in fixture["rows"]:
        refs = [_ref(source["prior"], source["id"] + "-prior"),
                _ref(source["current"], source["id"] + "-current")]
        offers = []
        for role, phase, ref in (
            ("B2_GIST", "prior", refs[0]),
            ("B1_DETAIL", "current", refs[1]),
            ("B2_GIST", "current", refs[1]),
        ):
            model, revision = BODY_MODELS[role]
            offers.append({"role": role, "phase": phase, "source_ref": ref,
                           "status": "RECORDED", "process_reaped": True,
                           "model_revision": revision,
                           "native_metrics": {"status": "FINAL",
                                              "actual_model": model}})
        arms = []
        for name in ARMS:
            payload = {"body_model_quote_verified": False,
                       "sources": [{"text": t, "source_ref": ref}
                                   for t, ref in zip(
                                       (source["prior"], source["current"]), refs)]}
            if name != ARMS[0]:
                payload.update(typed_jef_candidate=source["oracle"],
                               typed_candidate_authority=0)
            if name == ARMS[2]:
                payload.update(body_hypotheses_are_facts=False,
                               body_observations=[
                                   {"role": role,
                                    "hypothesis_authority": "MODEL_HYPOTHESIS_NOT_FACT",
                                    "verified_quotes": []}
                                   for role in ("B1_DETAIL", "B2_GIST")])
            output = (source["oracle"] if name != ARMS[0] else
                      {"choice": "A", "remaining": 1})
            correct = int(output == source["oracle"])
            arms.append({"arm": name, "status": "RECORDED",
                         "native_final": True, "process_reaped": True,
                         "native_metrics": {"status": "FINAL",
                                            "actual_model": C3_MODEL},
                         "messages": [{"role": "system", "content": "Synthetic control"},
                                      {"role": "user", "content": _dumps(payload).decode()}],
                         "output": _dumps(output).decode(),
                         "score": {"parsed": output, "valid_json": True,
                                   "correct": correct}})
        rows.append({"id": source["id"], "status": "RECORDED",
                     "closed_store_ok": True, "no_live_output": True,
                     "prior_source_ref": refs[0], "current_source_ref": refs[1],
                     "verified_quote_count": 0,
                     "offers": offers, "arms": arms})
    report = {"schema": "v13.run116.b1b2_jef_c3_native.v1",
              "fixture_sha256": hashlib.sha256(FROZEN.read_bytes()).hexdigest(),
              "seed": 1019, "native": True,
              "synthetic_body_observers": False,
              "native_body_calls": 18, "native_c3_calls": 18,
              "native_c2_calls": 0, "native_jef_calls": 0,
              "rows": rows, "scores": {ARMS[0]: 0, ARMS[1]: 6, ARMS[2]: 6},
              "exploratory_noninterference_signal": True,
              "status": "NATIVE_COMPLETE_NONINTERFERENCE_SIGNAL",
              "delivery_authority": 0, "learning_authority": 0,
              "tool_dispatches": 0, "jepa_weight": 0,
              "output_committed": False, "redmi_measured": False,
              "whole_system_complete": False,
              "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
              "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE"}
    if change:
        change(report, fixture)
    frozen = FROZEN.read_bytes()  # preserve registered fixture bytes
    phone_files = {FIXTURE: frozen}
    phone_manifest = {"schema_version": 1, "files": {
        name.removeprefix("V13-Phone/"): hashlib.sha256(data).hexdigest()
        for name, data in phone_files.items()}}
    phone_files["V13-Phone/WORKSPACE_FILES.json"] = _dumps(phone_manifest)
    phone = _zip(phone_files)
    result = {"head": HEAD, "exits": {name: 0 for name in EXITS},
              "native_attempted": True,
              **{k: False for k in ("native_c2_executed",
                  "native_jef_executed", "redmi_measured", "step2_promoted",
                  "b3_promoted", "body_jepa_promoted")}}
    files = {"HEAD.txt": HEAD.encode(), "RESULT.json": _dumps(result),
             "NATIVE_CASE/report.json": _dumps(report), PHONE_ZIP: phone}
    files.update({name + "_EXIT.txt": (b"1\n" if name == stage else b"0\n")
                  for name in EXITS})
    manifest = "".join(hashlib.sha256(data).hexdigest() + "  ./" + name + "\n"
                       for name, data in sorted(files.items()))
    files["SHA256SUMS"] = manifest.encode()
    return _zip(files)


class Run116IndependentAuditTests(unittest.TestCase):
    def check(self, change=None, stage=None):
        raw = synthetic_artifact(change, stage)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "synthetic.zip"
            path.write_bytes(raw)
            return audit(path, expected_sha=hashlib.sha256(raw).hexdigest())

    def test_synthetic_structure_only_passes(self):
        result = self.check()
        self.assertEqual(result["scores"],
                         {ARMS[0]: 0, ARMS[1]: 6, ARMS[2]: 6})
        self.assertEqual(result["native_body_final_reaped"], 18)
        self.assertTrue(result["noninterference_exploratory_only"])

    def test_forged_source_ref_refused(self):
        def change(report, fixture):
            report["rows"][0]["prior_source_ref"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_REFS"):
            self.check(change)

    def test_source_in_system_role_refused(self):
        def change(report, fixture):
            report["rows"][0]["arms"][0]["messages"][0]["content"] += fixture["rows"][0]["prior"]
        with self.assertRaisesRegex(ValueError, "SYSTEM_SOURCE_OR_ORACLE_LEAK"):
            self.check(change)

    def test_body_hypothesis_authority_escalation_refused(self):
        def change(report, fixture):
            report["rows"][0]["arms"][2]["messages"][1]["content"] = _dumps({
                **json.loads(report["rows"][0]["arms"][2]["messages"][1]["content"]),
                "body_hypotheses_are_facts": True}).decode()
        with self.assertRaisesRegex(ValueError, "BODY_HYPOTHESIS_AUTHORITY"):
            self.check(change)

    def test_original_score_tamper_refused(self):
        def change(report, fixture):
            report["rows"][0]["arms"][1]["score"]["correct"] = 0
        with self.assertRaisesRegex(ValueError, "ORIGINAL_SCORE_DISAGREES"):
            self.check(change)

    def test_missing_native_reap_refused(self):
        def change(report, fixture):
            report["rows"][2]["offers"][0]["process_reaped"] = False
        with self.assertRaisesRegex(ValueError, "BODY_NATIVE_LIFECYCLE"):
            self.check(change)

    def test_nonzero_stage_exit_refused(self):
        with self.assertRaisesRegex(ValueError, "STAGE_NATIVE"):
            self.check(stage="NATIVE")

    def test_wrong_outer_sha_refused(self):
        raw = synthetic_artifact()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "synthetic.zip"
            p.write_bytes(raw)
            with self.assertRaisesRegex(ValueError, "OUTER_SHA"):
                audit(p, expected_sha="0" * 64)


if __name__ == "__main__":
    unittest.main()
