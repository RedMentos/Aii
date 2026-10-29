"""Adversarial source-only tests for P2X native 360-call scorer."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p2x_native_receiver_eval_scorer.py"
spec = importlib.util.spec_from_file_location("p2x_native_eval", SCRIPT)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def fixture(adapter=None):
    answers = [{"id": "P2X" + format(i + 1, "016X"),
                "oracle_action": ("A", "B", "NONE")[i % 3]} for i in range(72)]
    plan, raw = [], []
    for a in answers:
        for arm in s.ARMS:
            p = {"id": a["id"], "arm": arm,
                 "messages": [{"role": "user", "content": a["id"] + " " + arm}]}
            plan.append(p)
            expected = a["oracle_action"] if arm == "both_exact" else "UNKNOWN"
            raw.append({"id": a["id"], "arm": arm, "status": "FINAL",
                        "model_called": True, "native_calls": 1, "seed": 13,
                        "model_sha256": s.MODEL_SHA, "runtime_sha256": s.RUNTIME_SHA,
                        "adapter_sha256": adapter, "input_sha256": s.sha(s.canonical(p["messages"])),
                        "duration_s": 0.5, "output": json.dumps({"action": expected})})
    return plan, answers, raw


class NativeEvalTests(unittest.TestCase):
    def test_strict_json_only(self):
        self.assertEqual(s.strict_action('{"action":"A"}'), "A")
        self.assertEqual(s.strict_action('{"action":"A","reason":"x"}'), "UNPARSEABLE")
        self.assertEqual(s.strict_action("A"), "UNPARSEABLE")
        self.assertEqual(s.strict_action('{"action":"WRONG"}'), "UNPARSEABLE")

    def test_full_base_raw_score_descriptive(self):
        p,a,r=fixture()
        x=s.score(r,p,a)
        self.assertEqual(x["native_calls"], 360)
        self.assertEqual(x["per_arm"]["both_exact"]["exact"], 72)
        self.assertEqual(x["per_arm"]["shuffled"]["wrong_committed"], 0)
        self.assertEqual(x["step2_status"], "UTILITY_FAIL")

    def test_adapter_exact_binding(self):
        h="a"*64
        p,a,r=fixture(h)
        self.assertEqual(s.score(r,p,a,h)["adapter_sha256"], h)
        with self.assertRaisesRegex(ValueError, "binding"):
            s.score(r,p,a,"b"*64)

    def test_reordered_raw_red(self):
        p,a,r=fixture()
        r[0],r[1]=r[1],r[0]
        with self.assertRaisesRegex(ValueError, "order"):
            s.score(r,p,a)

    def test_missing_call_red(self):
        p,a,r=fixture()
        with self.assertRaisesRegex(ValueError, "coverage"):
            s.score(r[:-1],p,a)

    def test_input_hash_tamper_red(self):
        p,a,r=fixture()
        r[0]["input_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError, "binding"):
            s.score(r,p,a)

    def test_nonfinite_duration_red(self):
        p,a,r=fixture()
        r[0]["duration_s"]=float("nan")
        with self.assertRaisesRegex(ValueError, "binding"):
            s.score(r,p,a)

    def test_foreign_wrong_commit_is_counted(self):
        p,a,r=fixture()
        idx=4
        self.assertEqual(r[idx]["arm"], "shuffled")
        r[idx]["output"]='{"action":"A"}'
        x=s.score(r,p,a)
        self.assertEqual(x["per_arm"]["shuffled"]["wrong_committed"], 1)

    def test_paired_delta_no_promotion(self):
        p,a,r=fixture()
        base=s.score(r,p,a)
        h="c"*64
        p2,a2,r2=fixture(h)
        r2[3]["output"]='{"action":"UNKNOWN"}'
        cand=s.score(r2,p2,a2,h)
        x=s.compare(base,cand)
        self.assertEqual(x["both_exact_delta"], -1)
        self.assertEqual(x["step2_status"], "UTILITY_FAIL")

    def test_paired_fabricated_adapter_red(self):
        p,a,r=fixture()
        base=s.score(r,p,a)
        cand=dict(base,adapter_sha256="bad")
        with self.assertRaisesRegex(ValueError, "identity"):
            s.compare(base,cand)

    def test_main_fail_closed_and_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"score.json"
            args=["--validation-dir",d,"--raw",str(Path(d)/"raw.json"),"--output",str(out)]
            self.assertEqual(s.main(args),2)
            self.assertEqual(json.loads(out.read_text())["status"],"P2X_RAW_RED_PRESERVED")
            with self.assertRaises(FileExistsError):
                s.main(args)


if __name__ == "__main__":
    unittest.main()
