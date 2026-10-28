"""Software-only tamper and readback tests; no native model execution."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from scripts import age0_bilingual_native_pair_audit as A
from scripts import age0_bilingual_arith_scorer as S


def bjson(o):
    return (json.dumps(o, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


class PairAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.items = S.fixture()

    def evidence(self, arm="candidate", mutate=None):
        pin = A.ARMS[arm]
        rows, raw_rows, scored = [], [], []
        counts = {"numeric": 0, "numeric_proxy_match": 0,
                  "unsupported": 0, "unsupported_uncertainty_marker": 0}
        for i, item in enumerate(self.items):
            answer = "Answer: " + item["expected"] if item["kind"] == "numeric" else "Not specified."
            role = "B1_DETAIL"
            row = {"id": item["id"], "prompt": item["prompt"], "answer": answer,
                   "status": "FINAL", "runner_role": role,
                   "runner_model_sha256": S.ROLE_MODELS[role], "tool_call": None,
                   "tool_shadow": None, "learning_mode": "RECORD_ONLY", "jepa_weight": 0}
            rows.append(row)
            raw_rows.append({"id": item["id"], "event_id": "evt_" + str(i),
                             "lang": item["lang"], "prompt": item["prompt"],
                             "answer": answer, "answer_sha256": A.digest(answer.encode()),
                             "status": "FINAL", "runner_role": role,
                             "runner_model_sha256": S.ROLE_MODELS[role],
                             "metadata": {"tool_call": None, "tool_shadow": None},
                             "error": None})
            match = (S.numeric_proxy(answer, item) if item["kind"] == "numeric"
                     else bool(S.UNKNOWN.search(answer)))
            if item["kind"] == "numeric":
                counts["numeric"] += 1
                counts["numeric_proxy_match"] += int(match)
            else:
                counts["unsupported"] += 1
                counts["unsupported_uncertainty_marker"] += int(match)
            scored.append({"id": item["id"], "lang": item["lang"],
                           "kind": item["kind"], "lexical_proxy_match": match,
                           "runner_role": role, "answer_sha256": A.digest(answer.encode())})
        manifest = {"schema": "v13.age0.bilingual_numeric_answers.v1",
                    "source_commit": pin["source"], "prompt_git_blob": pin["prompt"],
                    "model_catalog_git_blob": S.CATALOG_BLOB, "rows": rows}
        mb = bjson(manifest)
        rb = b"".join(json.dumps(r, sort_keys=True).encode() + b"\n" for r in raw_rows)
        report = {"schema": "v13.age0.bilingual_numeric_native_capture.v1",
                  "evidence_kind": "LINUX_NATIVE_AGE0_IF_VERIFIED",
                  "source_commit": pin["source"], "prompt_git_blob": pin["prompt"],
                  "catalog_git_blob": S.CATALOG_BLOB, "rows": 16, "final_rows": 16,
                  "raw_sha256": A.digest(rb), "manifest_sha256": A.digest(mb),
                  "phone_measured": False, "whole_system_complete": False,
                  "same_brain_fresh_sessions_not_global_state_isolation": True,
                  "jepa_weight": 0}
        score = {"schema": "v13.age0.bilingual_numeric_offline_score.v1",
                 "evidence_kind": "SOFTWARE_OFFLINE_SCORER_ONLY",
                 "fixture_git_blob": S.FIXTURE_BLOB, "external_native_claims_verified": False,
                 "semantic_grounding_verified": False, "phone_measured": False,
                 "whole_system_complete": False, "step2_utility": "FAIL", "b3_l1": "FAIL",
                 "body_jepa": "UNAVAILABLE", "lp3_heldout": "FAIL",
                 "runs": [{"input_sha256": A.digest(mb), "source_commit": pin["source"],
                           "prompt_git_blob": pin["prompt"], "counts": counts,
                           "items": scored}]}
        blobs = {**A.BLOB_PINS, "v13/code/v13/prompts.py": pin["prompt"]}
        expected = "".join(h + " " + p + "\n" for p, h in blobs.items()).encode()
        observed = "".join(h + " " + h + " " + p + "\n" for p, h in blobs.items()).encode()
        members = {"HEAD.txt": (pin["source"] + "\n").encode(),
                   "EXPECTED_BLOBS.txt": expected, "BLOBS_RAW.log": observed,
                   "native/ANSWERS.json": mb, "native/RAW_ROWS.jsonl": rb,
                   "native/CAPTURE_RESULT.json": bjson(report), "native/SCORE.json": bjson(score)}
        members.update({s + "_EXIT.txt": b"0\n" for s in A.STAGES})
        if mutate:
            mutate(members)
        checks = "".join(A.digest(value) + "  " + name + "\n"
                         for name, value in sorted(members.items())).encode()
        members["SHA256SUMS.txt"] = checks
        path = self.root / (arm + ".zip")
        with ZipFile(path, "w", ZIP_DEFLATED) as z:
            for name, value in members.items():
                z.writestr(name, value)
        return path, A.digest(path.read_bytes())

    def test_valid_closed_synthetic_zip_and_pair(self):
        a, a_sha = self.evidence("candidate")
        b, b_sha = self.evidence("baseline")
        cand = A.verify_archive(a, "candidate", a_sha)
        base = A.verify_archive(b, "baseline", b_sha)
        pair = A.compare(cand, base)
        self.assertEqual(pair["numeric_wins_candidate"], [])
        self.assertFalse(pair["whole_system_complete"])
        self.assertEqual(pair["step2_utility"], "FAIL")
        self.assertEqual(cand["native_stage_exits_zero"], 8)

    def test_original_zip_sha_is_required_by_default(self):
        p, _ = self.evidence()
        with self.assertRaisesRegex(ValueError, "archive SHA256"):
            A.verify_archive(p, "candidate")

    def test_stage_failure_preserved(self):
        p, h = self.evidence(mutate=lambda d: d.update({"CAPTURE_EXIT.txt": b"124\n"}))
        with self.assertRaisesRegex(ValueError, "stage RED"):
            A.verify_archive(p, "candidate", h)

    def test_mismatched_raw_answer_rejected_even_if_all_zip_hashes_resealed(self):
        def tamper(d):
            raw = d["native/RAW_ROWS.jsonl"].splitlines()
            item = json.loads(raw[0]); item["answer"] = "forged answer"
            raw[0] = json.dumps(item, sort_keys=True).encode()
            d["native/RAW_ROWS.jsonl"] = b"\n".join(raw) + b"\n"
            report = json.loads(d["native/CAPTURE_RESULT.json"])
            report["raw_sha256"] = A.digest(d["native/RAW_ROWS.jsonl"])
            d["native/CAPTURE_RESULT.json"] = bjson(report)
        p, h = self.evidence(mutate=tamper)
        with self.assertRaisesRegex(ValueError, "answer/raw hash mismatch"):
            A.verify_archive(p, "candidate", h)

    def test_wrong_pinned_runner_model_rejected(self):
        def tamper(d):
            manifest = json.loads(d["native/ANSWERS.json"])
            manifest["rows"][0]["runner_model_sha256"] = "0" * 64
            d["native/ANSWERS.json"] = bjson(manifest)
            report = json.loads(d["native/CAPTURE_RESULT.json"])
            report["manifest_sha256"] = A.digest(d["native/ANSWERS.json"])
            d["native/CAPTURE_RESULT.json"] = bjson(report)
        p, h = self.evidence(mutate=tamper)
        with self.assertRaisesRegex(ValueError, "final/runner mismatch"):
            A.verify_archive(p, "candidate", h)

    def test_claim_promotion_rejected(self):
        def tamper(d):
            report = json.loads(d["native/CAPTURE_RESULT.json"])
            report["phone_measured"] = True
            d["native/CAPTURE_RESULT.json"] = bjson(report)
        p, h = self.evidence(mutate=tamper)
        with self.assertRaisesRegex(ValueError, "promotion boundary"):
            A.verify_archive(p, "candidate", h)

    def test_scoring_tamper_rejected(self):
        def tamper(d):
            score = json.loads(d["native/SCORE.json"])
            score["runs"][0]["counts"]["numeric_proxy_match"] = 0
            d["native/SCORE.json"] = bjson(score)
        p, h = self.evidence(mutate=tamper)
        with self.assertRaisesRegex(ValueError, "scorer recomputation mismatch"):
            A.verify_archive(p, "candidate", h)

    def test_unsafe_zip_member_rejected(self):
        p, h = self.evidence(mutate=lambda d: d.update({"../escape": b"bad"}))
        with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
            A.verify_archive(p, "candidate", h)

    def test_same_source_or_duplicate_event_rejected(self):
        def tamper(d):
            raw = d["native/RAW_ROWS.jsonl"].splitlines()
            first = json.loads(raw[0]); second = json.loads(raw[1])
            second["event_id"] = first["event_id"]
            raw[1] = json.dumps(second, sort_keys=True).encode()
            d["native/RAW_ROWS.jsonl"] = b"\n".join(raw) + b"\n"
            report = json.loads(d["native/CAPTURE_RESULT.json"])
            report["raw_sha256"] = A.digest(d["native/RAW_ROWS.jsonl"])
            d["native/CAPTURE_RESULT.json"] = bjson(report)
        p, h = self.evidence(mutate=tamper)
        with self.assertRaisesRegex(ValueError, "event collision"):
            A.verify_archive(p, "candidate", h)


if __name__ == "__main__":
    unittest.main()