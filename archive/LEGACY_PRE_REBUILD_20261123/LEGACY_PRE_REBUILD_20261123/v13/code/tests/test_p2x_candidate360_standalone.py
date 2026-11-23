"""No-model source-only tests for isolated P2X candidate360 LoRA native diagnostic."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import p2x_candidate360_standalone as M


def synthetic_cohort():
    answers = [{"id": f"P2X{i+1:016X}", "oracle_action": ("A", "B", "NONE")[i % 3]}
               for i in range(72)]
    plan = []
    raw = []
    for answer in answers:
        for arm in M.scorer.ARMS:
            p = {"id": answer["id"], "arm": arm,
                 "messages": [{"role": "user",
                               "content": "Synthetic project " + answer["id"] + " " + arm}]}
            plan.append(p)
            action = answer["oracle_action"] if arm == "both_exact" else "UNKNOWN"
            raw.append({"id": p["id"], "arm": arm, "status": "FINAL",
                        "model_called": True, "native_calls": 1,
                        "seed": M.scorer.SEED, "model_sha256": M.scorer.MODEL_SHA,
                        "runtime_sha256": M.scorer.RUNTIME_SHA,
                        "adapter_sha256": None,
                        "input_sha256": M.scorer.sha(M.scorer.canonical(p["messages"])),
                        "duration_s": .1, "output": json.dumps({"action": action})})
    return plan, answers, M.scorer.score(raw, plan, answers)


class Candidate360Tests(unittest.TestCase):
    def test_bad_adapter_sha_rejected_before_files_or_calls(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "ADAPTER_HASH"):
                M.preflight(d, d, d, d, "not-a-hash", d, d, Path(d) / "out")

    def test_record_call_exact_binding_and_fail_closed(self):
        prompt = {"id": "P2X001", "arm": "both_exact",
                  "messages": [{"role": "user", "content": "synthetic"}]}
        r = M.record_call(prompt, '{"action":"A"}', .3,
                          {"status": "FINAL"}, "a" * 64)
        self.assertEqual(r["adapter_sha256"], "a" * 64)
        self.assertEqual(r["input_sha256"],
                         M.scorer.sha(M.scorer.canonical(prompt["messages"])))
        for duration in (float("nan"), -1, 91, True):
            with self.assertRaisesRegex(ValueError, "NONFINAL"):
                M.record_call(prompt, "{}", duration, {"status": "FINAL"}, "a" * 64)
        with self.assertRaisesRegex(ValueError, "NONFINAL"):
            M.record_call(prompt, "{}", .1, {"status": "RUNNING"}, "a" * 64)

    def test_local_request_uses_only_exact_user_message_and_json_schema(self):
        server = object.__new__(M.LocalServer)
        requests = []
        def fake_request(method, path, data=None, timeout=90):
            requests.append((path, data))
            if path == "/apply-template":
                return {"prompt": "rendered synthetic"}
            if path == "/tokenize":
                return {"tokens": [1, 2, 3]}
            return {"content": '{"action":"UNKNOWN"}'}
        server.request = fake_request
        message = [{"role": "user", "content": "synthetic source"}]
        text, metrics = server.generate(message, 10)
        self.assertEqual(text, '{"action":"UNKNOWN"}')
        self.assertEqual(metrics["status"], "FINAL")
        self.assertEqual([r[0] for r in requests],
                         ["/apply-template", "/tokenize", "/completion"])
        self.assertEqual(requests[0][1]["messages"], message)
        self.assertEqual(requests[0][1]["chat_template_kwargs"],
                         {"enable_thinking": False})
        completion = requests[-1][1]
        self.assertEqual(completion["json_schema"], M.hb1.C3_SCHEMA)
        self.assertEqual(completion["seed"], 13)
        self.assertEqual(completion["n_predict"], 48)
        self.assertIs(completion["stream"], False)
        self.assertNotIn("oracle_action", json.dumps(requests))

    def test_mocked_360_calls_persist_and_never_promote(self):
        plan, answers, base_score = synthetic_cohort()
        class FakeServer:
            calls = 0
            closed = False
            def __init__(self, *args):
                self.args = args
            def generate(self, messages, timeout):
                FakeServer.calls += 1
                return '{"action":"UNKNOWN"}', {"status": "FINAL", "synthetic": True}
            def close(self):
                FakeServer.closed = True
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base = root / "base"
            base.mkdir()
            (base / "SCORE.json").write_text(json.dumps(base_score))
            out = root / "candidate"
            with (patch.object(M, "admit_file", side_effect=lambda path, sha, label: Path(path)),
                  patch.object(M.scorer, "load_validation", return_value=(plan, answers)),
                  patch.object(M.base_verify, "verify",
                               return_value={"status": "VERIFIED_BASE_ONLY_LINUX_NATIVE_NO_GATE"}),
                  patch.object(M.P, "resource_admission",
                               return_value={"disk_free_bytes": 6_000_000_000,
                                             "memory_available_bytes": 6_000_000_000})):
                result = M.run_native(root / "binary", root / "archive", root / "model",
                                      root / "adapter", "a" * 64, root, base, out,
                                      server_factory=FakeServer)
            self.assertEqual(FakeServer.calls, 360)
            self.assertTrue(FakeServer.closed)
            self.assertEqual(result["recorded_calls"], 360)
            self.assertEqual(result["status"], "P2X_CANDIDATE360_NATIVE_DIAGNOSTIC_NO_GATE")
            self.assertFalse(result["ag6_approved"])
            self.assertFalse(result["production_activation"])
            self.assertFalse(result["canonical_gate_pass"])
            self.assertEqual(result["jepa_weight"], 0)
            self.assertEqual(len(json.loads((out / "RAW.json").read_text())), 360)
            score = json.loads((out / "SCORE.json").read_text())
            self.assertEqual(score["per_arm"]["both_exact"]["unknown"], 72)
            paired = json.loads((out / "PAIRED.json").read_text())
            self.assertEqual(paired["candidate_exact_both"], 0)
            self.assertEqual(paired["step2_status"], "UTILITY_FAIL")
            with self.assertRaisesRegex(ValueError, "FRESH_OUTPUT"):
                M.preflight(root, root, root, root, "a" * 64, root, base, out)

    def test_owned_launch_matches_baseline_cache_and_loopback(self):
        class FakeProc:
            terminated = False
            def poll(self):
                return None
            def terminate(self):
                self.terminated = True
            def wait(self, timeout):
                return 0
        proc = FakeProc()
        with tempfile.TemporaryDirectory() as d:
            with (patch.object(M.subprocess, "Popen", return_value=proc) as popen,
                  patch.object(M.LocalServer, "request",
                               return_value={"status": "ok"})):
                server = M.LocalServer("pinned-binary", "pinned-model",
                                       "synthetic-adapter", Path(d) / "server.log")
            args = popen.call_args.args[0]
            self.assertEqual(args[0], "pinned-binary")
            self.assertEqual(args[args.index("--host") + 1], "127.0.0.1")
            self.assertEqual(args[args.index("--cache-ram") + 1], "128")
            self.assertEqual(args[args.index("--ctx-checkpoints") + 1], "6")
            self.assertEqual(args[args.index("--lora-scaled") + 1],
                             "synthetic-adapter:1")
            self.assertEqual(args[args.index("--lora-scaled") + 2], "--host")
            server.close()
            self.assertTrue(proc.terminated)

    def test_unowned_server_is_never_killed(self):
        server = object.__new__(M.LocalServer)
        server.proc = None
        server.log_file = None
        server.close()


if __name__ == "__main__":
    unittest.main()
