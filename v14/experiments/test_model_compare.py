import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import model_compare
from model_compare import compare, TASKS, read_candidate_manifest


class FakeModels:
    def __init__(self, home, b2_control="two_body"):
        self.home = Path(home)
    def revision(self, role):
        return "base-rev"
    def path_for(self, role):
        return self.home / "models" / "language" / "base.gguf"


class FakeRunner:
    active = 0
    max_active = 0
    generate_calls = 0
    outputs = {"p0_arithmetic_2_plus_2": "4", "source_exact_extraction": "Q7-19",
               "missing_information_abstention": "UNKNOWN", "constraint_reasoning": "A"}
    def __init__(self, home, role, model, cfg, purpose="generate"):
        type(self).active += 1
        type(self).max_active = max(type(self).max_active, type(self).active)
        self.binary = os.environ.get("V13_LLAMA_SERVER", str(Path(home) / "bin" / "llama-server"))
        self._loaded_binary = None
        self.last_metrics = {}
    def generate(self, messages, cancel, deadline, max_tokens=None, seed=13):
        type(self).generate_calls += 1
        self._loaded_binary = self.binary
        task = next(t for t in TASKS if t["prompt"] == messages[-1]["content"])
        self.last_metrics = {"status": "FINAL", "duration_s": 1.0, "ttft_s": 0.2,
                             "generated_tokens": 1, "prompt_tokens": 12,
                             "sampled_peak_rss_bytes": 1000, "sampled_peak_pss_bytes": 800,
                             "stage_durations_s": {"load_s": 0.3, "prefill_to_first_token_s": 0.2, "stream_s": 0.1},
                             "timings": {"prompt_ms": 100, "predicted_ms": 100}}
        yield self.outputs[task["id"]]
    def unload(self):
        type(self).active -= 1
        return {"process_reaped": True}


class ModelCompareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        (self.home / "config").mkdir(parents=True)
        (self.home / "data").mkdir()
        (self.home / "bin").mkdir()
        (self.home / "models" / "language").mkdir(parents=True)
        (self.home / "data" / "coordinator.lock").write_text("")
        (self.home / "config" / "settings.json").write_text(json.dumps({"c3_decode_mode": "server", "seed": 13}))
        self.base = self.home / "models" / "language" / "base.gguf"
        self.candidate = self.home / "models" / "language" / "candidate.gguf"
        self.base.write_bytes(b"GGUF" + b"base-model")
        self.candidate.write_bytes(b"GGUF" + b"candidate-model")
        self.binary = self.home / "bin" / "llama-server"
        self.binary.write_text("#!/bin/sh\nexit 0\n")
        self.binary.chmod(0o755)
        self.base_spec = {"local_name": "base.gguf", "size": self.base.stat().st_size,
                          "sha256": hashlib.sha256(self.base.read_bytes()).hexdigest()}
        self.candidate_spec = {"local_name": "candidate.gguf", "size": self.candidate.stat().st_size,
                               "sha256": hashlib.sha256(self.candidate.read_bytes()).hexdigest()}
        self.manifest = Path(self.tmp.name) / "manifest.json"
        self.license_snapshot = Path(self.tmp.name) / "licenses" / "test-license.txt"
        self.license_snapshot.parent.mkdir(parents=True)
        self.license_snapshot.write_text("synthetic license snapshot for tests", encoding="utf-8")
        license_sha = hashlib.sha256(self.license_snapshot.read_bytes()).hexdigest()
        self.manifest.write_text(json.dumps({"schema": "v14.model-candidates/1", "candidates": [{
            "id": "candidate", "role": "C3_LANGUAGE", "model_id": "candidate/model",
            "revision": "a" * 40, "license_id": "Apache-2.0",
            "license_url": "https://huggingface.co/candidate/model/blob/" + ("a" * 40) + "/LICENSE",
            "license_snapshot_path": "licenses/test-license.txt",
            "license_snapshot_sha256": license_sha,
            "license_snapshot_source": "https://example.test/snapshot/LICENSE",
            "file": self.candidate_spec
        }]}))
        self.registry = {"models": {"language": {"model_id": "base/model", "revision": "base-rev",
            "license_id": "Apache-2.0", "license_url": "https://example.test/LICENSE",
            "quant_format": "Q4", "main_file": "base.gguf", "files": [self.base_spec]}}}
        FakeRunner.active = 0
        FakeRunner.max_active = 0
        FakeRunner.generate_calls = 0

    def tearDown(self):
        self.tmp.cleanup()

    def deps(self):
        return {"model_manager_cls": FakeModels, "runner_cls": FakeRunner,
                "defaults": {"c3_decode_mode": "server", "seed": 13},
                "config_validator": lambda cfg: None, "catalog_fn": lambda: self.registry}

    def run_compare(self, **kwargs):
        return compare(self.home, "candidate", manifest_path=self.manifest, **(self.deps() | kwargs))

    def test_sequential_runner_contract_and_metrics(self):
        result = self.run_compare()
        self.assertEqual(result["status"], "COMPARISON_COMPLETE")
        self.assertEqual(result["results"]["baseline"]["quality"]["exact_matches"], 4)
        self.assertEqual(result["results"]["candidate"]["summary"]["median_ttft_s"], 0.2)
        self.assertEqual(FakeRunner.max_active, 1)
        self.assertEqual(FakeRunner.active, 0)
        self.assertFalse(result["safety"]["production_swap"])
        self.assertFalse(result["safety"]["manifest_mutated"])

    def test_wrong_arithmetic_and_verbose_answer_fail_exact_grade(self):
        for output in ("2", "24", "The answer is 4"):
            FakeRunner.outputs["p0_arithmetic_2_plus_2"] = output
            result = self.run_compare()
            self.assertFalse(result["results"]["baseline"]["tasks"][0]["exact_match"])
        FakeRunner.outputs["p0_arithmetic_2_plus_2"] = "4"

    def test_license_snapshot_tampering_blocks_inference(self):
        self.license_snapshot.write_text("tampered license text", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "license snapshot SHA256 mismatch"):
            self.run_compare()
        self.assertEqual(FakeRunner.generate_calls, 0)
        self.assertEqual(FakeRunner.active, 0)

    def test_missing_license_snapshot_blocks_inference_even_if_candidate_missing(self):
        self.candidate.unlink()
        self.license_snapshot.unlink()
        with self.assertRaisesRegex(ValueError, "license snapshot missing"):
            self.run_compare()
        self.assertEqual(FakeRunner.generate_calls, 0)
        self.assertEqual(FakeRunner.active, 0)

    def test_license_snapshot_path_traversal_is_rejected(self):
        value = json.loads(self.manifest.read_text())
        value["candidates"][0]["license_snapshot_path"] = "../outside-license.txt"
        self.manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "traversal-free"):
            self.run_compare()
        self.assertEqual(FakeRunner.generate_calls, 0)

    def test_candidate_not_installed_never_downloads(self):
        self.candidate.unlink()
        result = self.run_compare()
        self.assertEqual(result["status"], "CANDIDATE_NOT_INSTALLED")
        self.assertFalse(result["download_performed"])
        self.assertEqual(FakeRunner.max_active, 0)

    def test_candidate_hash_mismatch_blocks_inference(self):
        self.candidate.write_bytes(b"GGUFtampered")
        with self.assertRaisesRegex(ValueError, "size mismatch|SHA256"):
            self.run_compare()
        self.assertEqual(FakeRunner.max_active, 0)

    def test_baseline_revision_mismatch_blocks_inference(self):
        class WrongRevision(FakeModels):
            def revision(self, role):
                return "wrong-rev"
        with self.assertRaisesRegex(RuntimeError, "revision differs"):
            self.run_compare(model_manager_cls=WrongRevision)
        self.assertEqual(FakeRunner.max_active, 0)

    def test_busy_coordinator_blocks_native_run(self):
        import fcntl
        handle = (self.home / "data" / "coordinator.lock").open("r+")
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            with self.assertRaisesRegex(RuntimeError, "already using"):
                self.run_compare()
            self.assertEqual(FakeRunner.max_active, 0)
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
            handle.close()

    def test_symlink_candidate_rejected(self):
        real = self.candidate.with_suffix(".real")
        self.candidate.rename(real)
        self.candidate.symlink_to(real)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.run_compare()
        self.assertEqual(FakeRunner.max_active, 0)

    def test_wrong_role_and_invalid_order_rejected(self):
        value = json.loads(self.manifest.read_text())
        value["candidates"][0]["role"] = "B2_GIST"
        self.manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "C3_LANGUAGE only"):
            self.run_compare()
        value["candidates"][0]["role"] = "C3_LANGUAGE"
        self.manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "order"):
            self.run_compare(order="random")

    def test_native_runner_error_is_partial_and_reaped(self):
        class BrokenRunner(FakeRunner):
            def generate(self, *args, **kwargs):
                raise TimeoutError()
                yield ""
        result = self.run_compare(runner_cls=BrokenRunner)
        self.assertEqual(result["status"], "COMPARISON_PARTIAL")
        self.assertEqual(result["results"]["baseline"]["status"], "INFERENCE_PARTIAL")
        self.assertEqual(result["results"]["baseline"]["tasks"][0]["status"], "ERROR")
        self.assertEqual(BrokenRunner.active, 0)

    def test_report_excludes_raw_output_and_absolute_paths(self):
        result = self.run_compare()
        encoded = json.dumps(result)
        self.assertNotIn("Q7-19", encoded)
        self.assertNotIn(str(self.home), encoded)
        self.assertIn("output_sha256", encoded)

    def test_same_artifact_cannot_be_candidate(self):
        self.candidate.write_bytes(self.base.read_bytes())
        value = json.loads(self.manifest.read_text())
        value["candidates"][0]["file"] = {"local_name": "candidate.gguf", "size": self.candidate.stat().st_size,
            "sha256": hashlib.sha256(self.candidate.read_bytes()).hexdigest()}
        self.manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "same artifact"):
            self.run_compare()
        self.assertEqual(FakeRunner.max_active, 0)

    def test_candidate_first_order_is_supported(self):
        result = self.run_compare(order="candidate-first")
        self.assertEqual(result["status"], "COMPARISON_COMPLETE")
        self.assertEqual(result["order"], "candidate-first")
        self.assertEqual(FakeRunner.max_active, 1)


    def test_environment_override_to_different_binary_fails_closed(self):
        other = self.home / "bin" / "other-llama-server"
        other.write_text("#!/bin/sh\\nexit 0\\n")
        other.chmod(0o755)
        with patch.dict(os.environ, {"V13_LLAMA_SERVER": str(other)}):
            with self.assertRaisesRegex(RuntimeError, "differs from verified installed binary"):
                self.run_compare()
        self.assertEqual(FakeRunner.generate_calls, 0)
        self.assertEqual(FakeRunner.active, 0)

    def test_environment_override_to_same_installed_binary_is_verified(self):
        with patch.dict(os.environ, {"V13_LLAMA_SERVER": str(self.binary)}):
            result = self.run_compare()
        self.assertEqual(result["status"], "COMPARISON_COMPLETE")
        self.assertEqual(result["runner"]["identity"], "MATCHED_INSTALLED_BINARY")
        self.assertTrue(result["runner"]["launch_verified"])
        self.assertEqual(result["runner"]["sha256"], hashlib.sha256(self.binary.read_bytes()).hexdigest())

    def test_loaded_executable_change_aborts_comparison(self):
        other = self.home / "bin" / "other-llama-server"
        other.write_text("#!/bin/sh\\nexit 0\\n")
        other.chmod(0o755)

        class ChangedLoadedRunner(FakeRunner):
            def generate(self, *args, **kwargs):
                for token in super().generate(*args, **kwargs):
                    self._loaded_binary = str(other)
                    yield token

        with self.assertRaisesRegex(RuntimeError, "differs from verified installed binary"):
            self.run_compare(runner_cls=ChangedLoadedRunner)
        self.assertEqual(ChangedLoadedRunner.generate_calls, 1)
        self.assertEqual(ChangedLoadedRunner.active, 0)

    def test_invalid_limits_rejected(self):
        with self.assertRaisesRegex(ValueError, "timeout"):
            compare(self.home, "candidate", timeout_s=1, manifest_path=self.manifest, **self.deps())
        with self.assertRaisesRegex(ValueError, "max_tokens"):
            compare(self.home, "candidate", max_tokens=256, manifest_path=self.manifest, **self.deps())


    def test_candidate_replaced_before_lock_is_revalidated(self):
        original_lock = model_compare.acquire_home_lock

        def replace_before_lock(home):
            self.candidate.write_bytes(b"GGUFtampered-candidate")
            return original_lock(home)

        with patch.object(model_compare, "acquire_home_lock", side_effect=replace_before_lock):
            with self.assertRaisesRegex(ValueError, "model size mismatch|model SHA256 mismatch"):
                self.run_compare()
        self.assertEqual(FakeRunner.generate_calls, 0)
        self.assertEqual(FakeRunner.active, 0)

    def test_models_are_staged_read_only_and_source_replacement_after_stage_is_ignored(self):
        original_run = model_compare.run_model
        seen = []

        def inspect_staged(runner_cls, lab_home, model_path, cfg, timeout_s, max_tokens,
                           expected_binary, expected_binary_info):
            if not seen:
                self.base.write_bytes(b"GGUFreplacement-base")
                self.candidate.write_bytes(b"GGUFreplacement-candidate")
            expected = self.base_spec if model_path.name == "baseline.gguf" else self.candidate_spec
            self.assertEqual(lab_home.parent, self.home / "data")
            self.assertFalse(model_path.is_symlink())
            self.assertEqual(stat.S_IMODE(model_path.stat().st_mode), 0o400)
            self.assertEqual(model_compare.sha256_file(model_path), expected["sha256"])
            seen.append(model_path)
            return original_run(runner_cls, lab_home, model_path, cfg, timeout_s, max_tokens,
                                expected_binary, expected_binary_info)

        with patch.object(model_compare, "run_model", side_effect=inspect_staged):
            result = self.run_compare()
        self.assertEqual(result["status"], "COMPARISON_COMPLETE")
        self.assertEqual(len(seen), 2)
        self.assertTrue(result["safety"]["model_files_staged"])
        self.assertTrue(result["safety"]["staged_model_files_read_only"])
        self.assertEqual(FakeRunner.max_active, 1)

    def test_installed_runner_binary_replacement_after_preflight_fails_closed(self):
        original_run = model_compare.run_model
        calls = []

        def replace_binary_then_run(runner_cls, lab_home, model_path, cfg, timeout_s, max_tokens,
                                    expected_binary, expected_binary_info):
            if not calls:
                self.binary.write_text("#!/bin/sh\nexit 1\n")
            calls.append(model_path)
            return original_run(runner_cls, lab_home, model_path, cfg, timeout_s, max_tokens,
                                expected_binary, expected_binary_info)

        with patch.object(model_compare, "run_model", side_effect=replace_binary_then_run):
            with self.assertRaisesRegex(RuntimeError, "runner executable digest"):
                self.run_compare()
        self.assertEqual(FakeRunner.generate_calls, 0)
        self.assertEqual(FakeRunner.active, 0)

    def test_repository_candidate_license_url_and_snapshot_are_pinned(self):
        rows = read_candidate_manifest(model_compare.MANIFEST_PATH)
        row = rows["lfm25-230m-c3"]
        self.assertIn(f"/blob/{row['revision']}/LICENSE", row["license_url"])
        snapshot = Path(__file__).with_name("licenses") / "LFM-OPEN-LICENSE-v1.0.txt"
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), row["license_snapshot_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
