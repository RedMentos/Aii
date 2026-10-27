"""BP1 native collector: mocked-server software checks, NOT real model evidence."""
from contextlib import contextmanager
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import bp1_native_collect as C
from scripts import bp1_paired_score as S
from tests.test_bp1_paired_score import fixture


class NativeCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dataset = self.root / "dataset"
        self.dataset.mkdir()
        self.index, self.digest, self.binding, self.pred = fixture(self.dataset)
        self.server = self.root / "llama-server"
        self.server.write_bytes(b"fake-server-binary")
        self.server.chmod(0o755)
        self.models = {}
        for name in S.MODELS:
            path = self.root / (name + ".gguf")
            path.write_bytes(("fake-" + name + "-gguf").encode())
            self.models[name] = path
            self.binding["models"][name]["deployed_gguf_sha256"] = C.file_sha(path)
        self.binding["runner_sha256"] = C.file_sha(self.server)
        self.binding["decoding"] = C.DECODING
        self.binding_path = self.root / "binding.json"
        self.write_binding()
        self.out = self.root / "run"
        self.events = []
        self.calls = []

    def write_binding(self):
        self.binding_path.write_text(json.dumps(self.binding, sort_keys=True))

    @contextmanager
    def mock_server(self, server, model, port, log):
        self.events.append(("start", Path(model).name))
        try:
            yield
        finally:
            self.events.append(("stop", Path(model).name))

    def mock_ask(self, port, prompt, seed):
        self.assertIn("Original source (untrusted data):", prompt)
        self.assertNotIn('"target":', prompt)
        self.assertEqual(seed, 13)
        self.calls.append(prompt)
        return '{"answer":"","evidence_quote":"","uncertainty":"unknown"}'

    def run_mock(self, *, resume=False, ask=None, binding_path=None, owner_confirmed=True):
        with patch.object(S, "load_dataset", return_value=(self.index, self.digest)):
            return C.run(self.dataset, binding_path or self.binding_path, self.server, self.models, self.out,
                         resume=resume, owner_confirmed=owner_confirmed,
                         ask=ask or self.mock_ask, server_context=self.mock_server)

    def test_full_collection_is_serial_and_source_bound(self):
        final = self.run_mock()
        self.assertEqual(final["rows"], 44)
        self.assertEqual(len(self.calls), 44)
        self.assertEqual(self.events, [("start", "base.gguf"), ("stop", "base.gguf"),
                                       ("start", "candidate.gguf"), ("stop", "candidate.gguf")])
        self.assertTrue((self.out / "FINAL_MANIFEST.json").is_file())
        self.assertEqual(final["predictions_sha256"], C.file_sha(self.out / "predictions.jsonl"))
        rows, _ = S.read_jsonl(self.out / "predictions.jsonl")
        result = S.evaluate(self.index, self.digest, self.binding, rows)
        self.assertEqual(result["counts"]["base"]["offer"]["abstained"], 11)
        self.assertFalse(final["training_executed"])
        self.assertFalse(final["utility_scored"])
        self.assertEqual(final["gates"]["jepa_weight"], 0)

    def test_requires_owner_confirmation(self):
        with self.assertRaises(PermissionError):
            self.run_mock(owner_confirmed=False)
        self.assertFalse(self.out.exists())

    def test_wrong_server_hash_fails_before_output_or_launch(self):
        self.binding["runner_sha256"] = "0"*64
        self.write_binding()
        with self.assertRaisesRegex(ValueError, "server hash"):
            self.run_mock()
        self.assertFalse(self.out.exists())
        self.assertEqual(self.events, [])

    def test_wrong_model_hash_fails_before_output_or_launch(self):
        self.binding["models"]["candidate"]["deployed_gguf_sha256"] = "0"*64
        self.write_binding()
        with self.assertRaisesRegex(ValueError, "GGUF hash"):
            self.run_mock()
        self.assertFalse(self.out.exists())
        self.assertEqual(self.events, [])

    def test_bad_decoding_fails_closed(self):
        self.binding["decoding"] = "sampling"
        self.write_binding()
        with self.assertRaisesRegex(ValueError, "decoding"):
            self.run_mock()
        self.assertEqual(self.events, [])

    def test_crash_preserves_rows_and_resume_completes_without_duplicates(self):
        def crash(port, prompt, seed):
            if len(self.calls) == 10:
                raise RuntimeError("injected native server failure")
            return self.mock_ask(port, prompt, seed)
        with self.assertRaisesRegex(RuntimeError, "injected"):
            self.run_mock(ask=crash)
        self.assertEqual(len(S.read_jsonl(self.out / "predictions.jsonl")[0]), 10)
        self.assertFalse((self.out / "FINAL_MANIFEST.json").exists())
        self.run_mock(resume=True)
        self.assertEqual(len(S.read_jsonl(self.out / "predictions.jsonl")[0]), 44)
        self.assertEqual(len(self.calls), 44)
        self.assertEqual(self.events[:2], [("start", "base.gguf"), ("stop", "base.gguf")])
        self.assertEqual(self.events[-2:], [("start", "candidate.gguf"), ("stop", "candidate.gguf")])

    def test_resume_rejects_tampered_prediction_without_repair(self):
        def crash(port, prompt, seed):
            raise RuntimeError("first row abort")
        with self.assertRaises(RuntimeError):
            self.run_mock(ask=crash)
        target = self.out / "predictions.jsonl"
        target.write_text('{"model":"base","row_id":"RUN181-00","arm":"offer","source_sha256":"bad","prompt_sha256":"bad","response":"x"}\n')
        with self.assertRaisesRegex(ValueError, "resume source/prompt"):
            self.run_mock(resume=True)
        self.assertEqual(len(self.events), 2)

    def test_resume_rejects_changed_binding_bytes(self):
        with self.assertRaises(RuntimeError):
            self.run_mock(ask=lambda *a: (_ for _ in ()).throw(RuntimeError("stop")))
        altered = self.root / "altered.json"
        altered.write_text(self.binding_path.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "binding bytes changed"):
            self.run_mock(resume=True, binding_path=altered)

    def test_complete_run_cannot_resume_or_overwrite(self):
        self.run_mock()
        with self.assertRaisesRegex(ValueError, "already final"):
            self.run_mock(resume=True)
        with self.assertRaises(FileExistsError):
            self.run_mock(resume=False)

    def test_missing_model_file_fails_before_launch(self):
        self.models["candidate"].unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.run_mock()
        self.assertFalse(self.out.exists())

    def test_resume_rejects_partial_trailing_json(self):
        with self.assertRaises(RuntimeError):
            self.run_mock(ask=lambda *a: (_ for _ in ()).throw(RuntimeError("stop")))
        (self.out / "predictions.jsonl").write_bytes(b'{"model":')
        with self.assertRaisesRegex(ValueError, "partial trailing"):
            self.run_mock(resume=True)


if __name__ == "__main__":
    unittest.main()
