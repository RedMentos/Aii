"""Run14R preregistered AG6 stage/train/approve holdout revalidation, real SQLite.

Uses authored counting/FakeLora test seams only. Production Age0 remains RECORD_ONLY.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval,build_suite,registered_holdout_digests,normalize
from v13.agi.weights import WeightConsolidation,KEY
from v13.common import digest
from tests.test_ag6_staged_source_revocation_20261029 import CountingTrainer
from tests.test_lora_trainer import FakeLora


class AG6HoldoutUseTime(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled","off")
        self.s=self.r.store
        self.cfg=self.r.cfg|{"learning_mode":"SHADOW_UPDATE"}

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _fact(self,prompt):
        e=self.s.event(self.r.session,prompt)
        self.r.memory.feedback(e["event_id"],"fact","Human-approved answer")
        return e

    def _new_unseen(self,seed=17,lang="en"):
        prior=registered_holdout_digests(self.s)
        for item in build_suite(seed,lang=lang)["items"]:
            if item["split"]=="unseen" and digest(normalize(item["prompt"])) not in prior:
                return item["prompt"]
        self.fail("Need at least one fresh unseen prompt not in prior suite")

    def test_optional_generality_none_cannot_bypass_stage_holdout(self):
        en=GeneralityEval(self.s,lang="en")
        prompt=next(i["prompt"] for i in en.suite["items"] if i["split"]=="unseen")
        self._fact(prompt)
        w=WeightConsolidation(self.s,self.cfg,generality=None,trainer=CountingTrainer())
        with self.assertRaisesRegex(ValueError,"AG12"):
            w.stage(require_replay_pass=False)
        self.assertEqual(w.box.load()[0]["batches"],{})

    def test_english_suite_rotation_after_stage_vetoes_fit_before_trainer(self):
        prompt=self._new_unseen(lang="en")
        self._fact(prompt)
        trainer=CountingTrainer()
        w=WeightConsolidation(self.s,self.cfg,generality=None,trainer=trainer)
        staged=w.stage(require_replay_pass=False)
        self.assertEqual(staged["status"],"STAGED")
        GeneralityEval(self.s,seed=17,lang="en")
        result=w.train(staged["batch_id"])
        self.assertEqual(result["status"],"SOURCE_INVALID")
        self.assertEqual(trainer.calls,[])
        self.assertEqual(self.s.state(KEY)[0]["consolidated"],[])

    def test_german_suite_registration_after_stage_vetoes_fit(self):
        prompt=self._new_unseen(lang="de")
        self._fact(prompt)
        trainer=CountingTrainer()
        w=WeightConsolidation(self.s,self.cfg,trainer=trainer)
        staged=w.stage(require_replay_pass=False)
        self.assertEqual(staged["status"],"STAGED")
        GeneralityEval(self.s,seed=17,lang="de")
        result=w.train(staged["batch_id"])
        self.assertEqual(result["status"],"SOURCE_INVALID")
        self.assertEqual(trainer.calls,[])

    def test_new_holdout_after_measured_gate_vetoes_human_approval(self):
        prompt=self._new_unseen(lang="en")
        self._fact(prompt)
        model=self.home/"model.gguf"
        model.write_bytes(b"authored synthetic model fixture")
        trainer=FakeLora(self.home,model,cand={
            "overall":.8,"unseen":.75,"forgetting":{"rate":0.}})
        w=WeightConsolidation(self.s,self.cfg,trainer=trainer)
        staged=w.stage(require_replay_pass=False)
        self.assertEqual(staged["status"],"STAGED")
        gated=w.train_and_gate(staged["batch_id"])
        self.assertEqual(gated["status"],"PENDING_USER")
        rid=gated["request_id"]
        GeneralityEval(self.s,seed=17,lang="en")
        with self.assertRaisesRegex(ValueError,"AG12|Holdout|Freigabe"):
            w.approve(staged["batch_id"])
        self.assertEqual(w.batch(staged["batch_id"])["status"],"PENDING_USER")
        self.assertEqual(self.s.one("SELECT status FROM requests WHERE id=?",(rid,))["status"],"PENDING")
        self.assertEqual(self.s.state(KEY)[0]["consolidated"],[])

    def test_unrelated_human_item_can_train_with_counting_seam(self):
        self._fact("Independent human preference about a harmless recipe?")
        trainer=CountingTrainer()
        w=WeightConsolidation(self.s,self.cfg,trainer=trainer)
        staged=w.stage(require_replay_pass=False)
        self.assertEqual(staged["status"],"STAGED")
        trained=w.train(staged["batch_id"])
        # CountingTrainer deliberately returns no artifact; AG6 records
        # NO_TRAINER, not TRAINED, while proving the fit seam was invoked.
        self.assertEqual(trained["status"],"NO_TRAINER")
        self.assertEqual(len(trainer.calls),1)


if __name__=="__main__":
    unittest.main()
