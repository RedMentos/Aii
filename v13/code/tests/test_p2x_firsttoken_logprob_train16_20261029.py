"""Synthetic source-only top40 first-token scale0/1 replay tests; no native proof."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import p2x_firsttoken_logprob_train16 as M


def command(scale,port):
    return ["/tmp/llama-server","-m","/tmp/c3.gguf","--lora-scaled",
            "/tmp/adapter.gguf:"+str(scale),"--host","127.0.0.1",
            "--port",str(port),"-c","2048","-np","1"]


def request(identifier):
    return {"prompt":identifier+M.PREFIX,"n_predict":1,"n_probs":M.N_PROBS,
            "post_sampling_probs":False,"stream":False,"temperature":0,
            "top_k":50,"repeat_penalty":1.05,"seed":M.scorer.SEED,
            "cache_prompt":False,"id_slot":0,"return_tokens":True}


def response(scale):
    return {"content":"A","completion_probabilities":[{
        "top_logprobs":[{"id":11,"logprob":-.2-.1*scale},
                        {"id":12,"logprob":-1.5+.1*scale}]}]}


def synthetic():
    p,a=M.plan()
    rows=[]
    for x in p:
        s=int(x["arm"][-1])
        rows.append(M.candidate.record_call(
            x,json.dumps(response(s)),.01,
            {"status":"FINAL","lora_scale":s,
             "prob_request":request(x["id"]),
             "launch_argv":command(s,30000+s)},
            M.ADAPTER_SHA))
    return p,a,rows


class FirstTokenLogprobSourceOnly(unittest.TestCase):
    def test_frozen_training_only_plan(self):
        p,a=M.plan()
        self.assertEqual((len(p),len(a)),(32,16))
        self.assertEqual([x["arm"] for x in p],["scale0"]*16+["scale1"]*16)
        self.assertEqual([x["messages"] for x in p[:16]],
                         [x["messages"] for x in p[16:]])

    def test_synthetic_positive_probability_delta_no_gate(self):
        p,a,rows=synthetic()
        result=M.score(rows,p,a)
        self.assertEqual(result["native_calls"],32)
        self.assertEqual(result["top1_token_changes"],0)
        self.assertEqual(result["shared_topk_changed_above_1e_6"],16)
        self.assertEqual(result["step2_status"],"UTILITY_FAIL")
        self.assertFalse(result["whole_system_complete"])
        self.assertEqual(json.loads(json.dumps(result)),result)

    def test_negative_duplicate_and_invalid_logprob(self):
        p,a,rows=synthetic()
        rows[0]["output"]=json.dumps({"completion_probabilities":[{
            "top_logprobs":[{"id":11,"logprob":float("nan")}]}]})
        with self.assertRaisesRegex(ValueError,"TOPK_ENTRY_RED"):
            M.score(rows,p,a)
        p,a,rows=synthetic()
        rows[0]["output"]=json.dumps({"completion_probabilities":[{
            "top_logprobs":[{"id":11,"logprob":-.2},{"id":11,"logprob":-.3}]}]})
        with self.assertRaisesRegex(ValueError,"TOPK_ENTRY_RED"):
            M.score(rows,p,a)

    def test_missing_probabilities_rejected_not_fabricated(self):
        p,a,rows=synthetic()
        rows[0]["output"]=json.dumps({"content":"A"})
        with self.assertRaisesRegex(ValueError,"PROB_SHAPE_RED"):
            M.score(rows,p,a)

    def test_wrong_request_scale_and_frozen_plan_rejected(self):
        p,a,rows=synthetic()
        rows[16]["metrics"]["prob_request"]["n_probs"]=20
        with self.assertRaisesRegex(ValueError,"PROB_REQUEST_RED"):
            M.score(rows,p,a)
        p,a,rows=synthetic()
        rows[16]["metrics"]["lora_scale"]=0
        with self.assertRaisesRegex(ValueError,"RAW_BINDING_RED"):
            M.score(rows,p,a)
        p,a,rows=synthetic()
        p[0]["messages"][0]["content"]+=" target_action:A"
        with self.assertRaisesRegex(ValueError,"FROZEN_PLAN_RED"):
            M.score(rows,p,a)

    def test_missing_native_assets_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            with self.assertRaisesRegex(ValueError,"BINARY_FILE"):
                M.preflight(d/"missing",d/"runtime",d/"model",d/"adapter",d/"new")

    def test_synthetic_replay_and_tamper(self):
        p,a=M.plan()
        class FakeServer:
            def __init__(self,binary,model,adapter,log,scale):
                self.scale=scale;self.proc=None
            def generate(self,messages,timeout):
                ident=next(x["id"] for x in p if x["messages"]==messages)
                return json.dumps(response(self.scale)),{
                    "status":"FINAL","lora_scale":self.scale,
                    "prob_request":request(ident),
                    "launch_argv":command(self.scale,30000+self.scale)}
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
                self.assertEqual(M.verify(d/"out")["shared_topk_changed_above_1e_6"],16)
                rows=json.loads((d/"out"/"RAW.json").read_text())
                rows[0]["metrics"]["prob_request"]["n_probs"]=10
                (d/"out"/"RAW.json").write_text(json.dumps(rows))
                with self.assertRaisesRegex(ValueError,"PROB_REQUEST_RED"):
                    M.verify(d/"out")


if __name__=="__main__":
    unittest.main()
