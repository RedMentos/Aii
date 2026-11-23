"""Run117V read-only auditor adversarial synthetic ZIP/score checks."""
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

from scripts import run117v_original_native_readonly_audit as audit
from scripts.run47_jef_c3_typed_receiver_native import score
from scripts.run117s_body_complementarity_preflight import _messages
from v13.common import dumps

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs/fixtures/RUN117S_BODY_COMPLEMENTARITY_SEED1061.json"


def ref(source, exact):
    start = source.index(exact)
    return {"source_id": "synthetic-source", "sha256": sha256(source.encode()).hexdigest(),
            "char_start": start, "char_end": start + len(exact), "modality": "text"}


def arm(row, name):
    if name == audit.ARMS[0]:
        payload = {"sources": [{"text": s, "source_ref": ref(s, s)}
                               for s in (row["prior"], row["current"])]}
    elif name == audit.ARMS[1]:
        payload = {"spans": [{"text": t, "source_ref": ref(s, t)}
                             for s, t in ((row["prior"], row["policy_span"]),
                                          (row["current"], row["option_span"]))]}
    else:
        payload = {"verified_quotes": [
            {"text": t, "source_ref": ref(s, t),
             "semantic_truth_authority": False}
            for s, t in ((row["prior"], row["policy_span"]),
                         (row["current"], row["option_span"]))],
            "body_hypotheses_are_facts": False,
            "quote_semantic_truth_authority": False,
            "body_hypotheses_not_forwarded": True}
    messages = _messages(payload)["messages"]
    output = dumps(row["oracle"])
    return {"arm": name, "status": "RECORDED", "native_final": True,
            "process_reaped": True,
            "native_metrics": {"status": "FINAL", "actual_model": audit.C3_NAME},
            "messages": messages,
            "messages_sha256": sha256(dumps(messages).encode()).hexdigest(),
            "output": output, "score": score(output, row["oracle"])}


def zip_bytes(files, *, tamper_hash=False, duplicate=False):
    entries = dict(files)
    lines = [sha256(value).hexdigest() + "  ./" + name
             for name, value in sorted(entries.items())]
    if tamper_hash:
        lines[0] = "0" * 64 + lines[0][64:]
    entries["SHA256SUMS"] = ("\n".join(lines) + "\n").encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name, value in entries.items():
            z.writestr(name, value)
        if duplicate:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                z.writestr("RESULT.json", entries.get("RESULT.json", b"{}"))
    return stream.getvalue()


class OriginalNativeAuditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row = audit.fixture(FIXTURE)[0]

    def test_all_three_exact_source_arms_and_strict_native_output(self):
        for name in audit.ARMS:
            with self.subTest(arm=name):
                item = arm(self.row, name)
                self.assertTrue(audit._arm_check(item, self.row, name))

    def test_oracle_injection_in_user_role_refused(self):
        item = arm(self.row, audit.ARMS[0])
        item["messages"][1]["content"] += ' "typed_jef_candidate"'
        item["messages_sha256"] = sha256(dumps(item["messages"]).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "ANSWER_LEAK_RED"):
            audit._arm_check(item, self.row, audit.ARMS[0])

    def test_fake_native_model_or_reap_refused(self):
        item = arm(self.row, audit.ARMS[1])
        item["native_metrics"]["actual_model"] = "fake-model.gguf"
        with self.assertRaisesRegex(ValueError, "NATIVE_RECEIPT_RED"):
            audit._arm_check(item, self.row, audit.ARMS[1])
        item = arm(self.row, audit.ARMS[2])
        item["process_reaped"] = False
        with self.assertRaisesRegex(ValueError, "NATIVE_RECEIPT_RED"):
            audit._arm_check(item, self.row, audit.ARMS[2])

    def test_forged_body_source_ref_refused(self):
        item = arm(self.row, audit.ARMS[2])
        payload = json.loads(item["messages"][1]["content"])
        payload["verified_quotes"][0]["source_ref"]["sha256"] = "0" * 64
        item["messages"][1]["content"] = dumps(payload)
        item["messages_sha256"] = sha256(dumps(item["messages"]).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, "FOREIGN_SOURCE_RED"):
            audit._arm_check(item, self.row, audit.ARMS[2])

    def test_original_output_rescore_detects_report_tamper(self):
        item = arm(self.row, audit.ARMS[0])
        item["score"]["correct"] = 0
        with self.assertRaisesRegex(ValueError, "SCORE_MISMATCH_RED"):
            audit._arm_check(item, self.row, audit.ARMS[0])

    def test_zip_crc_hash_duplicate_and_traversal_guards(self):
        raw = zip_bytes({"RESULT.json": b"{}"})
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.assertEqual(audit._zip_check(z), 1)
        for raw in (zip_bytes({"RESULT.json": b"{}"}, tamper_hash=True),
                    zip_bytes({"RESULT.json": b"{}"}, duplicate=True),
                    zip_bytes({"../RESULT.json": b"{}"})):
            with self.subTest(raw_sha=sha256(raw).hexdigest()):
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    with self.assertRaises(ValueError):
                        audit._zip_check(z)

    def test_outer_sha_tamper_rejected_before_zip_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "original.zip"
            p.write_bytes(zip_bytes({"RESULT.json": b"{}"}))
            with self.assertRaisesRegex(ValueError, "OUTER_SHA_RED"):
                audit.audit(p, "0" * 64, FIXTURE)

    def test_original_negative_gates_refuse_promotion(self):
        r = {"schema": audit.SCHEMA_NAME, "seed": 1061,
             "fixture_sha256": audit.FIXTURE_SHA,
             "native": True, "synthetic_body_observers": False,
             "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
             "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
             "jepa_weight": 1, "redmi_measured": False,
             "whole_system_complete": False, "output_committed": False,
             "tool_dispatches": 0, "learning_authority": 0,
             "delivery_authority": 0, "native_jef_calls": 0,
             "native_c2_calls": 0, "status": audit.STRUCTURAL_RED}
        with self.assertRaisesRegex(ValueError, "NEGATIVE_GATES_RED"):
            audit._report_check(r, audit.fixture(FIXTURE))


    def test_complete_report_requires_all_three_actual_body_receipts(self):
        rows = audit.fixture(FIXTURE)
        cases = []
        for row in rows:
            offers = [
                {"role": role, "phase": phase, "status": "RECORDED",
                 "source_ref": ref(
                     row["prior"] if phase == "prior" else row["current"],
                     row["prior"] if phase == "prior" else row["current"]),
                 "process_reaped": True,
                 "native_metrics": {"status": "FINAL",
                                    "actual_model": audit.MODEL_NAMES[role][0]},
                 "model_revision": audit.MODEL_NAMES[role][1]}
                for role, phase in (("B2_GIST", "prior"),
                                    ("B1_DETAIL", "current"),
                                    ("B2_GIST", "current"))]
            cases.append({
                "id": row["id"], "status": "RECORDED",
                "closed_store_ok": True, "no_live_output": True,
                "prior_source_ref": ref(row["prior"], row["prior"]),
                "current_source_ref": ref(row["current"], row["current"]),
                "offers": offers,
                "arms": [arm(row, name) for name in audit.ARMS]})
        report = {
            "schema": audit.SCHEMA_NAME, "seed": 1061,
            "fixture_sha256": audit.FIXTURE_SHA,
            "native": True, "synthetic_body_observers": False,
            "age0": "RECORD_ONLY", "step2_exit": "EVIDENCE_NOT_PASSING",
            "b3": "NO_PROMOTION", "body_jepa": "UNAVAILABLE",
            "jepa_weight": 0, "redmi_measured": False,
            "whole_system_complete": False, "output_committed": False,
            "tool_dispatches": 0, "learning_authority": 0,
            "delivery_authority": 0, "native_jef_calls": 0,
            "native_c2_calls": 0, "status": audit.GOOD[1],
            "native_body_calls": 18, "native_c3_calls": 18,
            "scores": {name: 6 for name in audit.ARMS},
            "recorded_by_arm": {name: 6 for name in audit.ARMS},
            "exploratory_body_selection_signal": False,
            "rows": cases}
        self.assertTrue(audit._report_check(report, rows)["native_complete"])
        original = list(report["rows"][0]["offers"])
        report["rows"][0]["offers"] = []
        with self.assertRaisesRegex(ValueError, "BODY_OFFER_RECEIPT_RED"):
            audit._report_check(report, rows)
        report["rows"][0]["offers"] = list(original)
        report["rows"][0]["offers"][0] = dict(original[0], phase="current")
        with self.assertRaisesRegex(ValueError, "BODY_OFFER_RECEIPT_RED"):
            audit._report_check(report, rows)
        report["rows"][0]["offers"] = list(original)
        report["rows"][0]["offers"][0] = dict(
            original[0], source_ref=ref(rows[0]["current"], rows[0]["current"]))
        with self.assertRaisesRegex(ValueError, "BODY_OFFER_RECEIPT_RED"):
            audit._report_check(report, rows)


if __name__ == "__main__":
    unittest.main()
