"""Software-only staged STEP2 12-arm source/tool/manifest guards, no models."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts import step2_longnote_staged12_native as stage
from scripts import step2_longnote_fourarm_analysis as analysis
from v13.common import digest, dumps


class Staged12Guards(unittest.TestCase):
    def base_artifacts(self):
        return {
            "model_sha256": {"B1_DETAIL": "a" * 64, "B2_GIST": "b" * 64,
                             "C3_LANGUAGE": "c" * 64},
            "model_revisions": {"B1_DETAIL": "1" * 40, "B2_GIST": "2" * 40,
                                "C3_LANGUAGE": "3" * 40},
            "runner_sha256": stage.RUNNER_SHA256,
            "runner_runtime_libraries_sha256": {"libllama.so": "d" * 64},
        }

    def fake(self, arm, seed):
        base = self.base_artifacts()
        expected = copy.deepcopy(base)
        expected["model_sha256"] = stage.expected_models(arm, base["model_sha256"])
        if arm.startswith("S"):
            expected["model_revisions"]["B2_GIST"] = expected["model_revisions"]["B1_DETAIL"]
        settings = stage.pre.candidate_settings(arm, seed)
        source = {
            "fixture_sha256": stage.FIXTURE_SHA256,
            "fixtures": [{"id": x} for x in stage.FIXTURE_IDS],
            "status": "UTILITY_FAIL", "all_structural_checks_passed": True,
            "source_unchanged": True, "installed_artifacts_unchanged": True,
            "installed_artifacts": expected,
            "distinct_bodies": arm.startswith("T"),
            "canonical_gate_pass": False, "phone_measured": False,
            "paired": {"complete": True}, "config": settings,
            "z2b_run": {"arm": arm, "seed": seed, "enable": settings},
            "z2b_queried_offers": {"offers": 120, "with_question": 120},
            "rows": [], "row_sha256": {},
        }
        tool = {
            "status": "TOOL_UTILITY_FAIL", "installed_artifacts_unchanged": True,
            "canonical_gate_pass": False, "phone_measured": False,
            "paired_tool": {"complete": True}, "rows": [], "row_sha256": {},
        }
        prereg = {"fixture_sha256": stage.FIXTURE_SHA256, "seed": 13,
                  "consumer_messages_sha256": {}}
        for fid in stage.FIXTURE_IDS:
            for variant in stage.VARIANTS:
                key = fid + ":" + variant
                messages = [{"role": "user", "content": arm + str(seed) + key}]
                row = {"fixture": fid, "variant": variant,
                       "status": "RECORDED", "processes_reaped": True,
                       "restart_state_identical": True,
                       "oracle_visible_to_native": False,
                       "native_consumer_metrics": {"status": "FINAL"},
                       "consumer_messages": messages}
                other = {"fixture": fid, "variant": variant,
                         "status": "RECORDED", "oracle_visible_to_native": False,
                         "consumer_metrics": {"status": "FINAL"},
                         "consumer_messages_sha256": digest(dumps(messages))}
                source["rows"].append(row)
                tool["rows"].append(other)
                source["row_sha256"][key] = digest(dumps(row))
                tool["row_sha256"][key] = digest(dumps(other))
                prereg["consumer_messages_sha256"][key] = digest(dumps(messages))
        prereg["source_report"] = {"sha256": digest(dumps(source))}
        summary = {
            "arm": arm, "seed": seed, "enable": settings, "query": True,
            "queried_offers": source["z2b_queried_offers"],
            "step2_status": source["status"], "tool_status": tool["status"],
            "episode_utility_tool": {
                fid + ":" + v: 0.5
                for fid in stage.FIXTURE_IDS for v in stage.VARIANTS},
            "error_profile_tool": {
                v: {"rule_fields_correct": 0.5, "option_fields_correct": 0.5}
                for v in ("b1_only", "b2_only")},
        }
        return source, tool, prereg, summary, base

    def check(self, arm, seed, source, tool, prereg, summary, base):
        return stage.verify_pair(dumps(source).encode(), dumps(tool).encode(),
                                 prereg, summary, arm, seed, base)

    def test_frozen_registration_and_reject_unknown_arm_seed(self):
        for arm in stage.ARMS:
            for seed in stage.SEEDS:
                dry = stage.prereg(arm, seed)
                self.assertEqual(dry["registration_sha256"], stage.REGISTRATION_SHA256)
        for arm, seed in (("C", 27), ("TP", 13), ("SP", 30), ("TP", True)):
            with self.assertRaises(ValueError):
                stage.prereg(arm, seed)

    def test_all_12_synthetic_arm_seed_seals_are_only_diagnostic(self):
        records = []
        sources = {k: c * 64 for k, c in zip(("pre", "fixture", "runner", "tool"),
                                              ("a", "b", "c", "d"))}
        for arm in stage.ARMS:
            for seed in stage.SEEDS:
                src, tool, prereg, summary, base = self.fake(arm, seed)
                source, replay, expected = self.check(
                    arm, seed, src, tool, prereg, summary, base)
                self.assertEqual(len(source["rows"]), 70)
                self.assertEqual(len(replay["rows"]), 70)
                raw, sealed = stage.sealed_summary(
                    summary, dumps(src).encode(), dumps(tool).encode(),
                    arm, seed, expected["model_sha256"], sources)
                self.assertEqual(sealed["raw_sha256"], hashlib.sha256(raw).hexdigest())
                self.assertFalse(sealed["canonical_gate_pass"])
                records.append(sealed)
        result = analysis.analyze(records, stage.FIXTURE_IDS)
        self.assertFalse(result["candidate_supported"])
        self.assertFalse(result["canonical_gate_pass"])
        self.assertFalse(result["step2_gate_promoted"])

    def test_shared_body_revision_and_weights_must_both_match(self):
        s, t, p, m, b = self.fake("SP", 28)
        self.check("SP", 28, s, t, p, m, b)
        s["installed_artifacts"]["model_revisions"]["B2_GIST"] = "2" * 40
        with self.assertRaises(ValueError):
            self.check("SP", 28, s, t, p, m, b)

    def test_tampered_row_message_seed_and_gate_fail(self):
        for mutate in (
            lambda s, t, p, m, b: s["rows"][0].update(status="ERROR"),
            lambda s, t, p, m, b: t["rows"].pop(),
            lambda s, t, p, m, b: p["source_report"].update(sha256="0" * 64),
            lambda s, t, p, m, b: s["z2b_queried_offers"].update(with_question=119),
            lambda s, t, p, m, b: s.update(canonical_gate_pass=True),
            lambda s, t, p, m, b: s["config"].update(seed=29),
            lambda s, t, p, m, b: s["fixtures"][0].update(id="Kestrel"),
            lambda s, t, p, m, b: s["installed_artifacts"].update(runner_sha256="0" * 64),
        ):
            s, t, p, m, b = self.fake("TC", 27)
            mutate(s, t, p, m, b)
            with self.subTest(mutate=repr(mutate)):
                with self.assertRaises(ValueError):
                    self.check("TC", 27, s, t, p, m, b)

    def test_missing_installed_home_fails_before_creating_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            out = root / "evidence"
            with self.assertRaises(ValueError):
                stage.run(root / "missing", out, "TC", 27)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
