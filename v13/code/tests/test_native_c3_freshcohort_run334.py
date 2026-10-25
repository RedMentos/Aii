"""Run334 source-only tests for fresh-cohort C3 training; never native proof."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import native_c3_freshcohort_run334 as A


class DummyServer:
    pass


def fake_turn(_server,q,a):
    return "<P>"+q+"</P>","<A>"+a+"</A>","<END>"


def evaluation(*,facts=4,para=2,leak=0.0,forget=False,invalid=0):
    probes=[{"q":"probe"+str(i),"ok":not(forget and i==0)} for i in range(12)]
    return {"facts":[{} for _ in range(8)],
            "paraphrases":[{} for _ in range(6)],
            "near_miss":[{} for _ in range(5)],
            "probes":probes,
            "invalid_outputs":invalid,
            "summary":{"facts_strict":facts,"paraphrases_strict":para,
                       "near_miss_leak_strict":leak}}


class Run334FreshSourceOnly(unittest.TestCase):
    def test_frozen_cohort_sha_and_denominators(self):
        data=A.cohort()
        self.assertEqual(len(data["facts"]),8)
        self.assertEqual(len(data["paraphrases"]),6)
        self.assertEqual(len(data["near_miss"]),5)
        self.assertEqual(len(A.PROBES),12)
        self.assertEqual(A.COHORT_SHA,"0bcc0fe92de2bd740b4f2b27b47b325c94827c67f32e519360c6e548cb2b94fb")

    def test_fresh_near_miss_questions_never_contain_leak_key(self):
        data=A.cohort()
        for row in data["near_miss"]:
            self.assertNotIn(row["leak_keys"][0],row["q"].lower())

    def test_original_train_source_pins_preserved(self):
        self.assertEqual(A.MASTER_SHA,"5d200c19f13483e66b39d9feb3353032581882f3eb10cc8752f027d4688d6e6f")
        self.assertEqual(A.HF_REVISION,"9e6c6ccf47cd318696e137d381a7ded8fe4df09f")
        self.assertEqual(A.TRAIN["seed"],47)
        self.assertEqual(A.TRAIN["epochs"],2)
        self.assertEqual(A.TRAIN["lr"],1e-5)
        self.assertEqual(A.TRAIN["reps"],12)

    def test_three_fixed_arms_no_posthoc_variant(self):
        self.assertEqual(A.ARMS,{"A_ALL_NO_REPLAY":("all",False),
                                 "B_ANSWER_NO_REPLAY":("answer",False),
                                 "C_ANSWER_REPLAY":("answer",True)})

    def test_all_token_stream_has_no_answer_mask(self):
        with patch.object(A,"turn",side_effect=fake_turn):
            stream=A.make_stream(DummyServer(),A.cohort()["facts"],"all",[])
        self.assertEqual(stream.count("<END>"),96)
        self.assertNotIn("\x01",stream)
        self.assertNotIn("\x02",stream)

    def test_answer_only_stream_marks_all_96_answers(self):
        with patch.object(A,"turn",side_effect=fake_turn):
            stream=A.make_stream(DummyServer(),A.cohort()["facts"],"answer",[])
        self.assertEqual(stream.count("<END>"),96)
        self.assertEqual(stream.count("\x01"),96)
        self.assertEqual(stream.count("\x02"),96)

    def test_replay_adds_one_disjoint_anchor_per_rep(self):
        anchors=[("anchor "+str(i),"baseline "+str(i)) for i in range(6)]
        with patch.object(A,"turn",side_effect=fake_turn):
            stream=A.make_stream(DummyServer(),A.cohort()["facts"],"answer",anchors)
        self.assertEqual(stream.count("<END>"),108)
        self.assertEqual(stream.count("\x01"),108)
        for q,_ in anchors:
            self.assertEqual(stream.count("<P>"+q+"</P>"),2)

    def test_seeded_stream_deterministic(self):
        with patch.object(A,"turn",side_effect=fake_turn):
            a=A.make_stream(DummyServer(),A.cohort()["facts"],"answer",[])
            b=A.make_stream(DummyServer(),A.cohort()["facts"],"answer",[])
        self.assertEqual(a,b)

    def test_unregistered_mode_and_anchor_count_rejected(self):
        with self.assertRaisesRegex(ValueError,"unregistered"):
            A.make_stream(DummyServer(),A.cohort()["facts"],"other",[])
        with self.assertRaisesRegex(ValueError,"unregistered"):
            A.make_stream(DummyServer(),A.cohort()["facts"],"answer",[("x","y")])

    def test_earliest_passing_epoch_selected_candidate_only(self):
        base=evaluation()
        r=A.select(base,[evaluation(),evaluation(facts=6,para=4)])
        self.assertEqual(r["selected_epoch"],1)
        self.assertEqual(r["selection"],"CANDIDATE_ONLY_NO_ACTIVATION")
        self.assertFalse(r["AG6_promoted"])
        self.assertFalse(r["Body_JEPA_promoted"])

    def test_forgetting_rejects_otherwise_passing_epoch(self):
        r=A.select(evaluation(),[evaluation(forget=True),evaluation(forget=True)])
        self.assertIsNone(r["selected_epoch"])
        self.assertEqual(r["selection"],"NONE")

    def test_near_miss_leak_and_invalid_outputs_reject(self):
        r=A.select(evaluation(),[evaluation(leak=0.4),evaluation(invalid=1)])
        self.assertIsNone(r["selected_epoch"])

    def test_facts_and_paraphrase_thresholds_are_both_required(self):
        r=A.select(evaluation(),[evaluation(facts=3),evaluation(para=1)])
        self.assertIsNone(r["selected_epoch"])

    def test_epoch_denominator_rejected(self):
        bad=evaluation()
        bad["facts"].pop()
        with self.assertRaisesRegex(ValueError,"denominator"):
            A.select(evaluation(),[bad,evaluation()])

    def test_no_overwrite_even_without_model(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FileExistsError):
                A.run("tools","server","master","manifest",td)

    def test_negative_gates_immutable(self):
        self.assertEqual(A.GATES,{"STEP2":"UTILITY_FAIL","B3_L1":"FAIL",
                                  "Body_JEPA":"UNAVAILABLE","jepa_weight":0,
                                  "V13":"INCOMPLETE"})
        self.assertEqual(A.CRITERIA["facts_strict_min"],4)
        self.assertEqual(A.CRITERIA["paraphrases_strict_min"],2)
        self.assertEqual(A.CRITERIA["forgotten_baseline_probes_max"],0)


if __name__=="__main__":
    unittest.main()
