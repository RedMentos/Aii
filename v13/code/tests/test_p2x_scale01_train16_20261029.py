"""Synthetic training-only LoRA scale0/1 admission; never native evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_scale01_train16 as M


def command(scale, port):
    return ["/tmp/llama-server", "-m", "/tmp/c3.gguf", "--lora-scaled",
            "/tmp/adapter.gguf:" + str(scale), "--host", "127.0.0.1",
            "--port", str(port), "-c", "2048", "-np", "1", "-t", "2",
            "-tb", "2", "-b", "128", "-ub", "128", "-ngl", "0",
            "--cache-ram", "128", "--ctx-checkpoints", "6",
            "--no-warmup", "--no-webui", "--log-disable"]


def request(identifier):
    return {"prompt": identifier, "n_predict": M.candidate.MAX_TOKENS,
            "stream": False, "temperature": .1, "top_k": 50,
            "repeat_penalty": 1.05, "seed": M.scorer.SEED,
            "cache_prompt": True, "id_slot": 0, "return_tokens": True,
            "json_schema": M.candidate.hb1.C3_SCHEMA}


def synthetic():
    prompts, answers = M.plan()
    oracle = {a["id"]: a["target_action"] for a in answers}
    rows = []
    for p in prompts:
        scale = int(p["arm"][-1])
        rows.append(M.candidate.record_call(
            p, json.dumps({"action": oracle[p["id"]]}), .01,
            {"status": "FINAL", "lora_scale": scale,
             "launch_argv": command(scale, 32000 + scale),
             "completion_request": request(p["id"])},
            M.ADAPTER_SHA))
    return prompts, answers, rows


class Scale01TrainingOnly(unittest.TestCase):
    def test_frozen_balanced_training_only(self):
        p, a = M.plan()
        self.assertEqual((len(p), len(a)), (32, 16))
        self.assertEqual([x["arm"] for x in p], ["scale0"]*16 + ["scale1"]*16)
        self.assertEqual([x["messages"] for x in p[:16]],
                         [x["messages"] for x in p[16:]])
        self.assertEqual({v: sum(x["target_action"] == v for x in a)
                          for v in M.parent.base.resources.LABELS},
                         dict.fromkeys(M.parent.base.resources.LABELS, 4))

    def test_positive_synthetic_score_no_gate(self):
        p, a, rows = synthetic()
        result = M.score(rows, p, a)
        self.assertEqual(result["correct_strict_in_sample"], {"0":16,"1":16})
        self.assertEqual(result["paired_action_changes"], 0)
        self.assertEqual(result["native_calls"], 32)
        self.assertEqual(result["step2_status"], "UTILITY_FAIL")
        self.assertFalse(result["whole_system_complete"])

    def test_scale_only_argv_normalization_and_veto(self):
        self.assertEqual(M.normalized_argv(command(0,1234),0),
                         M.normalized_argv(command(1,5678),1))
        with self.assertRaisesRegex(ValueError, "SCALE_ARG_RED"):
            M.normalized_argv(command(1,5678),0)
        with self.assertRaisesRegex(ValueError, "PORT_RED"):
            M.normalized_argv(command(0,0),0)

    def test_request_or_non_scale_argv_mutation_rejected(self):
        p, a, rows = synthetic()
        rows[16]["metrics"]["completion_request"]["temperature"] = .5
        with self.assertRaisesRegex(ValueError, "REQUEST_SETTINGS_RED"):
            M.score(rows,p,a)
        p, a, rows = synthetic()
        rows[16]["metrics"]["launch_argv"][-1] = "--other"
        with self.assertRaisesRegex(ValueError, "NON_SCALE_ARGV_DIFF_RED"):
            M.score(rows,p,a)

    def test_wrong_adapter_and_duplicate_rejected(self):
        p,a,rows=synthetic()
        rows[0]["adapter_sha256"] = "f"*64
        with self.assertRaisesRegex(ValueError,"RAW_BINDING_RED"):
            M.score(rows,p,a)
        p,a,rows=synthetic()
        rows[1] = rows[0].copy()
        with self.assertRaisesRegex(ValueError,"RAW_BINDING_RED"):
            M.score(rows,p,a)

    def test_missing_native_assets_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            with self.assertRaisesRegex(ValueError,"BINARY_FILE"):
                M.preflight(d/"missing",d/"runtime",d/"model",d/"adapter",d/"new")

    def test_synthetic_loopback_replay_and_tamper(self):
        p,a=M.plan()
        oracle={x["id"]:x["target_action"] for x in a}
        class FakeServer:
            def __init__(self,binary,model,adapter,log,scale):
                self.scale=scale;self.proc=None
            def generate(self,messages,timeout):
                ident=next(x["id"] for x in p if x["messages"]==messages)
                return json.dumps({"action":oracle[ident]}),{
                    "status":"FINAL","lora_scale":self.scale,
                    "launch_argv":command(self.scale,32000+self.scale),
                    "completion_request":request(ident)}
            def close(self):
                pass
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            with patch.object(M,"preflight",return_value=(
                d/"binary",d/"model",d/"adapter",p,a,{"synthetic":True}
            )),patch.object(M.candidate,"admit_file",side_effect=lambda path,*args:Path(path)):
                receipt=M.run_native(d/"binary",d/"runtime",d/"model",
                                     d/"adapter",d/"out",server_factory=FakeServer)
                self.assertEqual(receipt["recorded_calls"],32)
                self.assertEqual(M.verify(d/"out")["correct_strict_in_sample"],
                                 {"0":16,"1":16})
                rows=json.loads((d/"out"/"RAW.json").read_text())
                rows[0]["metrics"]["lora_scale"]=1
                (d/"out"/"RAW.json").write_text(json.dumps(rows))
                with self.assertRaisesRegex(ValueError,"RAW_BINDING_RED"):
                    M.verify(d/"out")


if __name__=="__main__":
    unittest.main()
