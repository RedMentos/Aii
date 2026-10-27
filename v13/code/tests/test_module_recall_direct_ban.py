"""WP-BP11b direct recall must respect the same typed module_recall ban as ToolRegistry.
Synthetic local module, no network/model/native/Redmi. Tests committed before fix.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from v13.runtime import Runtime
from v13 import modules_gate as M, module_learn, prohibitions as P

H=M.HUMAN
DATA=json.dumps({
    "format":M.FORMAT,"name":"Synthetic","version":"1",
    "license":"Apache-2.0","source":"test-only",
    "items":[{"title":"Planets","text":"The synthetic planet of Andara has exactly four moons."}],
}).encode("utf-8")


class DirectModuleRecallBanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled","off")
        self.s=self.r.store
        M.set_enabled(self.s,True,authority=H)
        mid=M.propose(self.s,"https://example.org/andara.json","Synthetic",origin="USER",clock=lambda:1000.)
        M.fetch(self.s,mid,authority=H,fetcher=lambda _:DATA,clock=lambda:1000.)
        code=M.state(self.s)["mods"][mid]["sha256"][:8]
        M.activate(self.s,mid,code,authority=H,clock=lambda:1100.)
        M.set_learn(self.s,True,authority=H)
        self.query="How many moons does Andara have?"
        self.assertTrue(module_learn.recall(self.s,self.query))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_exact_typed_module_recall_ban_blocks_direct_reader(self):
        P.add(self.s,"tool","module_recall",authority=H)
        self.assertEqual(module_learn.recall(self.s,self.query),[])
        P.remove(self.s,"V1",authority=H)
        self.assertTrue(module_learn.recall(self.s,self.query))

    def test_operator_frage_cannot_bypass_typed_module_recall_ban(self):
        P.add(self.s,"tool","module_recall",authority=H)
        result=M.operator_command(self.r,["frage","How","many","moons","does","Andara","have?"])
        self.assertIn("Nichts Passendes",result)
        self.assertNotIn("four moons",result)

    def test_ban_added_during_corpus_read_does_not_emit_stale_hit(self):
        original=M.corpus
        def banned_corpus(store):
            items=original(store)
            P.add(self.s,"tool","module_recall",authority=H)
            return items
        with patch.object(M,"corpus",side_effect=banned_corpus):
            self.assertEqual(module_learn.recall(self.s,self.query),[])

    def test_broad_read_local_ban_blocks_direct_recall(self):
        P.add(self.s,"risk","READ_LOCAL",authority=H)
        self.assertEqual(module_learn.recall(self.s,self.query),[])


if __name__=="__main__":
    unittest.main()
