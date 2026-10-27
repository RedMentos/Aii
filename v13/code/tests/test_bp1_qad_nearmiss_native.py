"""Software-only counterexamples for 48-row QAD native collector; no model or network."""
import json
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import bp1_qad_nearmiss_retention as D
from scripts import bp1_qad_nearmiss_native as N


class Native48Software(unittest.TestCase):
    def setUp(self):
        self.near, self.ret = D.build_rows()
        self.requests = N.plan(self.near, self.ret)

    def test_only_registered_prompt_metadata_reaches_model(self):
        self.assertEqual(len(self.requests), 48)
        self.assertEqual({r["model"] for r in self.requests}, {"base", "candidate"})
        self.assertEqual({r["scale"] for r in self.requests}, {0.0, 1.0})
        for r in self.requests:
            self.assertFalse({"target", "expected", "answer_keys", "false_b2_hint"} & set(r))
            self.assertEqual(N.S.sha(r["prompt"].encode()), r["prompt_sha256"])
            self.assertEqual(r["scale"], N.SCALES[r["model"]])
            saved = N.public_record(r, "answer")
            self.assertNotIn("prompt", saved)
            self.assertNotIn("scale", saved)
            self.assertEqual(saved["response"], "answer")
        with self.assertRaises(ValueError):
            N.plan(self.near[:15], self.ret)

    def test_incremental_fsync_resume_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "proof"
            binding = b'{"schema":"fixture"}\n'
            n = [0]
            def fail_after_five(req):
                n[0] += 1
                if n[0] == 6:
                    raise RuntimeError("native interruption")
                return "0"
            with self.assertRaises(RuntimeError):
                N.collect(self.requests, binding, out, fail_after_five)
            self.assertEqual(len(N.existing(out / "predictions.jsonl", self.requests)), 5)
            N.collect(self.requests, binding, out, lambda req: "0", resume=True)
            self.assertEqual(len(N.existing(out / "predictions.jsonl", self.requests)), 48)
            with self.assertRaises(ValueError):
                N.collect(self.requests, binding + b"changed", out, lambda req: "0", resume=True)
            rows = (out / "predictions.jsonl").read_text().splitlines()
            rows.append(rows[0])
            (out / "predictions.jsonl").write_text("\n".join(rows) + "\n")
            with self.assertRaises(ValueError):
                N.existing(out / "predictions.jsonl", self.requests)

    def test_tampered_binding_or_response_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "proof"
            N.collect(self.requests, b"proof", out, lambda req: "0")
            path = out / "predictions.jsonl"
            rows = [json.loads(x) for x in path.read_text().splitlines()]
            rows[0]["prompt_sha256"] = "0" * 64
            path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            with self.assertRaises(ValueError):
                N.existing(path, self.requests)
            with self.assertRaises(ValueError):
                N.public_record(self.requests[0], None)

    def test_retention_request_is_plain_not_json_schema(self):
        observed = []
        def fake_http(port, method, path, payload):
            observed.append((port, method, path, payload))
            return {"choices": [{"message": {"content": "12\n"}}]}
        with patch.object(N.E, "_http_json", side_effect=fake_http):
            self.assertEqual(N.retention_request(8833, "7+5", 13, 0.0), "12")
        payload = observed[0][3]
        self.assertEqual(payload["lora"], [{"id": 0, "scale": 0.0}])
        self.assertNotIn("response_format", payload)
        self.assertEqual(payload["temperature"], 0)
        with self.assertRaises(ValueError):
            N.retention_request(8833, "7+5", 13, 0.5)

    def test_end_to_end_fake_native_boundary_and_serial_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            D.write(root / "controls")
            v2 = root / "v2.json"
            v2.write_text(json.dumps({"train_proof_sha256": "a" * 64,
                                      "base_gguf_sha256": "b" * 64,
                                      "adapter_gguf_sha256": "c" * 64,
                                      "runner_sha256": "d" * 64, "seed": 13}))
            out = root / "native"
            with self.assertRaises(PermissionError):
                N.run(root / "controls", v2, "proof", "server", "base", "adapter", out)
            @contextmanager
            def fake_server(server, base, adapter, port, log):
                self.assertTrue(log.parent.is_dir())  # journal before server
                yield
            def fake_ask(req):
                return ('{"answer":"","evidence_quote":"","uncertainty":"unknown"}'
                        if req["kind"] == "near_miss" else "0")
            with patch.object(N.E, "validate_binding", return_value=True), \
                 patch.object(N.E, "verify_train_proof", return_value=True), \
                 patch.object(N.E, "validate_native_files", return_value={"fixture": "verified"}):
                result = N.run(root / "controls", v2, "proof", "server", "base", "adapter",
                               out, serial_owner_confirmed=True,
                               ask=fake_ask, server_context=fake_server)
            self.assertEqual(result["rows"], 48)
            self.assertFalse(result["model_utility_proven"])
            self.assertEqual(result["gates"]["STEP2"], "UTILITY_FAIL")
            self.assertTrue((out / "FINAL_MANIFEST.json").is_file())
            self.assertEqual(len(N.existing(out / "predictions.jsonl", self.requests)), 48)
            with self.assertRaises(ValueError):
                N.collect(self.requests, (out / "RUN_BINDING.json").read_bytes(),
                          out, fake_ask, resume=True)


if __name__ == "__main__":
    unittest.main()
