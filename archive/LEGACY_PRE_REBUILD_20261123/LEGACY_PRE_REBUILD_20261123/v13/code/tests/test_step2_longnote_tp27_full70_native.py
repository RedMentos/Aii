"""Software-only fail-closed TP27 70+70 native report guards; no model execution."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import step2_longnote_tp27_full70_native as full
from v13.common import digest, dumps


class TP27Full70Guards(unittest.TestCase):
    def test_frozen_cohort_and_alias(self):
        dry = full.prereg()
        self.assertEqual(full.FIXTURE_IDS, full.EXPECTED_IDS)
        self.assertEqual(dry["registered"]["fixture_sha256"], full.FIXTURE_SHA256)
        self.assertIs(full.z2b.z2, full.pilot.z2)

    def fake_reports(self):
        model = {"B1_DETAIL": "a" * 64, "B2_GIST": "b" * 64,
                 "C3_LANGUAGE": "c" * 64}
        artifacts = {"model_sha256": model,
                     "runner_sha256": full.RUNNER_SHA256,
                     "runner_runtime_libraries_sha256": {"libllama.so": "d" * 64}}
        settings = full.pre.candidate_settings(full.ARM, full.SEED)
        src = {
            "fixture_sha256": full.FIXTURE_SHA256,
            "fixtures": [{"id": f} for f in full.EXPECTED_IDS],
            "status": "UTILITY_FAIL", "all_structural_checks_passed": True,
            "source_unchanged": True, "installed_artifacts_unchanged": True,
            "installed_artifacts": artifacts, "distinct_bodies": True,
            "canonical_gate_pass": False, "phone_measured": False,
            "scoped_utility_gate_pass": False,
            "paired": {"complete": True, "mean_utility": {}},
            "config": settings, "z2b_run": {"arm": full.ARM, "seed": full.SEED,
                                          "enable": settings},
            "z2b_queried_offers": {"offers": 120, "with_question": 120},
            "rows": [], "row_sha256": {},
        }
        tool = {
            "status": "TOOL_UTILITY_FAIL", "installed_artifacts_unchanged": True,
            "canonical_gate_pass": False, "phone_measured": False,
            "paired_tool": {"complete": True, "scoped_utility_gate_pass": False},
            "rows": [], "row_sha256": {},
        }
        prereg = {"fixture_sha256": full.FIXTURE_SHA256, "seed": 13,
                  "consumer_messages_sha256": {}}
        for fixture in full.EXPECTED_IDS:
            for variant in full.VARIANTS:
                key = fixture + ":" + variant
                messages = [{"role": "user", "content": fixture + variant}]
                row = {"fixture": fixture, "variant": variant,
                       "status": "RECORDED", "processes_reaped": True,
                       "restart_state_identical": True,
                       "oracle_visible_to_native": False,
                       "native_consumer_metrics": {"status": "FINAL"},
                       "consumer_messages": messages}
                other = {"fixture": fixture, "variant": variant,
                         "status": "RECORDED", "oracle_visible_to_native": False,
                         "consumer_metrics": {"status": "FINAL"},
                         "consumer_messages_sha256": digest(dumps(messages))}
                src["rows"].append(row)
                tool["rows"].append(other)
                src["row_sha256"][key] = digest(dumps(row))
                tool["row_sha256"][key] = digest(dumps(other))
                prereg["consumer_messages_sha256"][key] = digest(dumps(messages))
        summary = {"arm": full.ARM, "seed": full.SEED, "enable": settings,
                   "query": True, "queried_offers": src["z2b_queried_offers"],
                   "step2_status": src["status"], "tool_status": tool["status"]}
        prereg["source_report"] = {"sha256": digest(dumps(src))}
        return src, tool, artifacts, summary, prereg

    def check(self, src, tool, artifacts, summary, prereg):
        raw_src, raw_tool = dumps(src).encode(), dumps(tool).encode()
        return full.verify_pair(raw_src, raw_tool, artifacts, summary, prereg)

    def test_valid_synthetic_structure_never_promotes_gate(self):
        s, t, a, m, p = self.fake_reports()
        source, tool = self.check(s, t, a, m, p)
        self.assertEqual(len(source["rows"]), 70)
        self.assertEqual(len(tool["rows"]), 70)
        self.assertFalse(source["canonical_gate_pass"])

    def test_tampered_native_row_digest_fails(self):
        s, t, a, m, p = self.fake_reports()
        s["rows"][0]["status"] = "ERROR"
        with self.assertRaises(ValueError):
            self.check(s, t, a, m, p)

    def test_tool_message_mismatch_fails_even_with_rehashed_row(self):
        s, t, a, m, p = self.fake_reports()
        row = t["rows"][0]
        row["consumer_messages_sha256"] = "0" * 64
        t["row_sha256"][row["fixture"] + ":" + row["variant"]] = digest(dumps(row))
        with self.assertRaises(ValueError):
            self.check(s, t, a, m, p)

    def test_missing_or_duplicate_tool_row_fails(self):
        s, t, a, m, p = self.fake_reports()
        t["rows"].pop()
        with self.assertRaises(ValueError):
            self.check(s, t, a, m, p)

    def test_gate_or_question_or_fixture_spoof_fails(self):
        for mutate in (
            lambda s, t, a, m, p: s.update(canonical_gate_pass=True),
            lambda s, t, a, m, p: s["z2b_queried_offers"].update(with_question=119),
            lambda s, t, a, m, p: s["fixtures"][0].update(id="Kestrel"),
            lambda s, t, a, m, p: m.update(seed=28),
            lambda s, t, a, m, p: p["source_report"].update(sha256="f" * 64),
            lambda s, t, a, m, p: s["config"].update(b2_quote_select="off"),
        ):
            s, t, a, m, p = self.fake_reports()
            mutate(s, t, a, m, p)
            with self.subTest(mutate=repr(mutate)):
                with self.assertRaises(ValueError):
                    self.check(s, t, a, m, p)

    def test_missing_installed_home_fails_before_evidence_created(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "evidence"
            with self.assertRaises(ValueError):
                full.run(root / "missing", out)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
