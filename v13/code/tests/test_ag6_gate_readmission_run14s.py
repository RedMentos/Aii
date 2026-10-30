"""Run14S test-first: AG6 gate must not request approval of newly invalid data.

SQLite and FakeLora only; no model weights trained or promoted.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v13.runtime import Runtime
from v13.agi.generality import GeneralityEval,build_suite,registered_holdout_digests,normalize
from v13.agi.weights import WeightConsolidation,KEY
from v13.common import digest
from tests.test_lora_trainer import FakeLora


class AG6GateReadmission(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled","off")
        self.s=self.r.store
        self.cfg=self.r.cfg|{"learning_mode":"SHADOW_UPDATE"}
        model=self.home/"synthetic.gguf"
        model.write_bytes(b"synthetic model fixture, not a real model")
        self.trainer=FakeLora(self.home,model,cand={
            "overall":.8,"unseen":.75,"forgetting":{"rate":0.}})
        self.w=WeightConsolidation(self.s,self.cfg,trainer=self.trainer)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _fresh_unseen(self,lang):
        prior=registered_holdout_digests(self.s)
        for item in build_suite(17,lang=lang)["items"]:
            if item["split"]=="unseen" and digest(normalize(item["prompt"])) not in prior:
                return item["prompt"]
        self.fail("No fresh unseen prompt for seed17")

    def _fit(self,prompt):
        e=self.s.event(self.r.session,prompt)
        self.r.memory.feedback(e["event_id"],"fact","A human-supported answer")
        staged=self.w.stage(require_replay_pass=False)
        self.assertEqual(staged["status"],"STAGED")
        bid=staged["batch_id"]
        self.assertEqual(self.w.train(bid)["status"],"TRAINED")
        return bid,self.w.batch(bid)["items"][0]["source_ref"]

    def _gate(self,bid):
        return self.w.gate(bid,
            {"overall":.8,"unseen":.75,"near_miss_leak":0.},
            {"overall":.8,"unseen":.75,"forgetting":{"rate":0.},"near_miss_leak":0.},
            learned_recall=1.)

    def _assert_invalid_without_request(self,bid):
        out=self._gate(bid)
        self.assertEqual(out["status"],"SOURCE_INVALID")
        self.assertIsNone(out["request_id"])
        self.assertEqual(self.s.one("SELECT COUNT(*) AS n FROM requests WHERE kind='WEIGHT_CONSOLIDATION'")["n"],0)
        self.assertEqual(self.s.state(KEY)[0]["consolidated"],[])

    def test_english_seed17_new_holdout_after_fit_blocks_request(self):
        prompt=self._fresh_unseen("en")
        bid,_=self._fit(prompt)
        GeneralityEval(self.s,seed=17,lang="en")
        self._assert_invalid_without_request(bid)

    def test_german_seed17_new_holdout_after_fit_blocks_request(self):
        prompt=self._fresh_unseen("de")
        bid,_=self._fit(prompt)
        GeneralityEval(self.s,seed=17,lang="de")
        self._assert_invalid_without_request(bid)

    def test_revoked_source_after_fit_blocks_request(self):
        bid,ref=self._fit("Ordinary human fact for revocation at gate?")
        with self.s.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",(ref["source_id"],))
        self._assert_invalid_without_request(bid)

    def test_corrupted_historical_registry_after_fit_blocks_request(self):
        bid,_=self._fit("Ordinary human fact for integrity at gate?")
        en=GeneralityEval(self.s,lang="en")
        en.box.mutate(lambda st: st.update(holdout=[]))
        self._assert_invalid_without_request(bid)

    def test_valid_measured_gate_still_requests_human_not_auto_activation(self):
        bid,_=self._fit("Independent valid human fact for gate?")
        out=self._gate(bid)
        self.assertEqual(out["status"],"PENDING_USER")
        self.assertTrue(out["request_id"])
        self.assertEqual(self.s.one("SELECT COUNT(*) AS n FROM requests WHERE kind='WEIGHT_CONSOLIDATION'")["n"],1)
        self.assertEqual(self.s.state(KEY)[0]["consolidated"],[])


if __name__=="__main__":
    unittest.main()
