import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from v13.public_probe import public_probe_error, public_probe_summary


def load_overlay():
    path = Path(__file__).resolve().parents[1] / "scripts" / "integrated_public_probe_privacy_candidate_20261124.py"
    spec = importlib.util.spec_from_file_location("v14_public_probe_privacy_overlay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PublicProbePrivacyTests(unittest.TestCase):
    def test_raw_model_outputs_offers_and_control_payloads_are_redacted(self):
        report = {
            "proof_kind": "NATIVE_SMOKE",
            "status": "SMOKE_PARTIAL",
            "phone_measured": True,
            "full_runner_proof": False,
            "model_revisions": {"C3_LANGUAGE": "a" * 64},
            "effective_config": {"threads": 6, "private_path": "SECRET_PATH"},
            "missing_proofs": ["long-term retention"],
            "roles": {
                "C3_LANGUAGE": {
                    "ok": True,
                    "actual_output": "SECRET_C3_OUTPUT",
                    "metrics": {"status": "FINAL", "generated_tokens": 7, "prompt_preview": "SECRET_PROMPT"},
                },
                "B1_DETAIL": {
                    "structured_offer": {
                        "verified_quote_count": 2,
                        "rejected_quote_count": 1,
                        "actual": {"summary": "SECRET_B1_HYPOTHESIS"},
                    },
                },
                "B2_GIST": {
                    "structured_offer": {
                        "verified_quote_count": 1,
                        "rejected_quote_count": 0,
                        "actual": {"summary": "SECRET_B2_HYPOTHESIS"},
                    },
                },
                "C2_CONTROL": {
                    "actual_control": {"answer": "SECRET_CONTROL"},
                    "embedding_dim": 3072,
                },
            },
        }
        rendered = json.dumps(public_probe_summary(report), sort_keys=True)
        for secret in ("SECRET_C3_OUTPUT", "SECRET_PROMPT", "SECRET_PATH",
                       "SECRET_B1_HYPOTHESIS", "SECRET_B2_HYPOTHESIS", "SECRET_CONTROL"):
            self.assertNotIn(secret, rendered)
        summary = json.loads(rendered)
        self.assertEqual(summary["roles"]["C3_LANGUAGE"]["metrics"]["generated_tokens"], 7)
        self.assertEqual(summary["roles"]["B1_DETAIL"]["offer"]["verified_quote_count"], 2)
        self.assertTrue(summary["redaction"]["raw_artifact_retained_locally"])

    def test_closed_vocabulary_and_unhashable_values_fail_closed(self):
        secret = "SECRET_PROMPT_PATH"
        summary = public_probe_summary({
            "proof_kind": "NATIVE_SMOKE",
            "status": secret,
            "phone_measured": "true",
            "model_revisions": {"C3_LANGUAGE": secret, "B1_DETAIL": "b" * 64},
            "missing_proofs": [[], {}, secret, "long-term retention"],
            "roles": {
                "C3_LANGUAGE": {
                    "metrics": {
                        "status": secret,
                        "role": {},
                        "last_phase": [],
                        "error_kind": secret,
                        "stage_durations_s": {secret: 1.0, "prefill_to_first_token_s": 2.0},
                        "generated_tokens": True,
                    },
                    "structured_offer": {"verified_quote_count": True, "rejected_quote_count": 1, "actual": secret},
                },
            },
        })
        rendered = json.dumps(summary, sort_keys=True)
        self.assertNotIn(secret, rendered)
        self.assertEqual(summary["status"], "UNKNOWN")
        self.assertFalse(summary["phone_measured"])
        self.assertEqual(summary["model_revisions"], {"B1_DETAIL": "b" * 64})
        self.assertEqual(summary["missing_proofs"], ["LONG_TERM_RETENTION"])
        self.assertEqual(summary["roles"]["C3_LANGUAGE"]["metrics"]["stage_durations_s"],
                         {"prefill_to_first_token_s": 2.0})
        self.assertEqual(summary["roles"]["C3_LANGUAGE"]["offer"]["verified_quote_count"], 0)

    def test_non_native_report_rejected_and_error_receipt_is_fixed(self):
        with self.assertRaises(ValueError):
            public_probe_summary({"proof_kind": "OTHER", "roles": {"C3_LANGUAGE": {"actual_output": "SECRET"}}})
        rendered = json.dumps(public_probe_error(), sort_keys=True)
        self.assertIn("SMOKE_ERROR", rendered)
        self.assertIn("PROBE_EXECUTION_ERROR", rendered)
        self.assertNotIn("Traceback", rendered)

    def test_staged_overlay_patches_interactive_and_one_shot_consumers(self):
        overlay = load_overlay()
        runtime = b"""                elif kind=='probe':
                    if payload=='sustained':
                        self.notice('bounded')
                    else:
                        from .verification import probe
                        self.notice(dumps(probe(self)))
                else:raise ValueError('Job unbekannt')
            except BaseException as exc:
                self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')
                if kind=='turn':self._rejected(payload,str(exc))
"""
        main = b"""            if a.command=='probe':
                from .verification import probe
                else:result=probe(r)
            print(json.dumps(result,ensure_ascii=False,indent=2))
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "v13").mkdir()
            helper = Path(__file__).resolve().parents[1] / "v13" / "public_probe.py"
            (root / "v13" / "public_probe.py").write_bytes(helper.read_bytes())
            (root / "v13" / "runtime.py").write_bytes(runtime)
            (root / "v13" / "__main__.py").write_bytes(main)
            changed = overlay.apply_staged_probe_privacy(root)
            self.assertEqual(set(changed), {"v13/runtime.py", "v13/__main__.py"})
            runtime_after = (root / "v13" / "runtime.py").read_text()
            main_after = (root / "v13" / "__main__.py").read_text()
            self.assertIn("public_probe_summary(probe(self))", runtime_after)
            self.assertIn("if kind == 'probe':", runtime_after)
            self.assertIn("PROBE_ERROR", runtime_after)
            self.assertIn("public_probe_summary(probe(r))", main_after)
            self.assertIn("public_probe_error()", main_after)
            with self.assertRaises(ValueError):
                overlay.apply_staged_probe_privacy(root)

    def test_staged_overlay_rejects_symlinked_runtime(self):
        overlay = load_overlay()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "v13").mkdir()
            helper = Path(__file__).resolve().parents[1] / "v13" / "public_probe.py"
            (root / "v13" / "public_probe.py").write_bytes(helper.read_bytes())
            (root / "outside.py").write_text("safe")
            (root / "v13" / "runtime.py").symlink_to(root / "outside.py")
            (root / "v13" / "__main__.py").write_text("else:result=probe(r)\n")
            with self.assertRaises(ValueError):
                overlay.apply_staged_probe_privacy(root)


if __name__ == "__main__":
    unittest.main()
