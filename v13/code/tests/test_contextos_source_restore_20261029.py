"""WP-N7 exact source restoration through Context OS operator; source-only."""
import json
from pathlib import Path
import tempfile
import unittest

from v13.runtime import Runtime
from v13.operator import Operator
from v13 import context_os as C


class ExactSourceRestore(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.r=Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy("enabled","off")
        self.c=C.ContextOS(self.r.store,self.r.cfg)
    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()
    def event(self,text,session=None):
        return self.r.store.event(session or self.r.session,text)

    def test_exact_unicode_code_and_numbers_roundtrip_read_only(self):
        original='Wörtlich: „Äpfel“ 1,234.50 EUR; `a=b+1`\n\n😀\n'
        e=self.event(original)
        before=self.r.store.state(C.KEY)[1]
        packets=self.r.store.one("SELECT COUNT(*) AS n FROM packets")["n"]
        out=self.c.source(e["event_id"],self.r.session)
        self.assertEqual(out["text"],original)
        self.assertEqual(out["event_id"],e["event_id"])
        self.assertEqual(out["source_ref"],e["source_ref"])
        self.assertEqual(out["authority"],"SOURCE_EXACT_READ_ONLY")
        self.assertFalse(out["context_applied"])
        self.assertEqual(self.r.store.state(C.KEY)[1],before)
        self.assertEqual(self.r.store.one("SELECT COUNT(*) AS n FROM packets")["n"],packets)

    def test_operator_restores_compressed_old_turn_without_promoting(self):
        first=None;history=[]
        for i in range(10):
            text="Old discussion %d about context. "%i+"Many details about plants. "*25
            e=self.event(text)
            if i==0:first=e
            self.r.store.message(self.r.session,e["event_id"],"assistant","Answer. "+"More details. "*15,status="FINAL")
            history.append({"event_id":e["event_id"],"role":"user","text":text})
            history.append({"event_id":e["event_id"],"role":"assistant","text":"Answer. "+"More details. "*15})
        p=self.c.plan(self.event("next")["event_id"],"C3_LANGUAGE","SYS",[],history,"next")
        self.assertFalse(p["applied"])
        self.assertIn("COMPRESSED",[x["form"] for x in p["plan"]["items"]])
        reply=Operator(self.r).run(":ctxos source "+first["event_id"])
        data=json.loads(reply)
        self.assertEqual(data["text"],"Old discussion 0 about context. "+"Many details about plants. "*25)
        self.assertEqual(self.c.report()["mode"],"SHADOW")

    def test_foreign_session_and_unknown_event_are_denied(self):
        other=self.r.store.new_session("other")
        foreign=self.event("foreign private text",other)
        with self.assertRaisesRegex(ValueError,"CTXOS_SOURCE"):
            self.c.source(foreign["event_id"],self.r.session)
        with self.assertRaisesRegex(ValueError,"CTXOS_SOURCE"):
            self.c.source("evt_"+("f"*32),self.r.session)

    def test_tombstoned_source_is_never_restored(self):
        e=self.event("erase this")
        with self.r.store.tx() as cur:
            cur.execute("UPDATE sources SET deleted=1 WHERE id=?",(e["source_ref"]["source_id"],))
        with self.assertRaisesRegex(ValueError,"SourceRef|CTXOS_SOURCE"):
            self.c.source(e["event_id"],self.r.session)

    def test_corrupted_blob_does_not_fallback_to_message_table(self):
        e=self.event("literal source before tampering")
        blob=self.r.store.home/"data/blobs"/e["source_ref"]["sha256"]
        blob.write_text("different bytes",encoding="utf-8")
        with self.assertRaisesRegex(ValueError,"Source-Hash|CTXOS_SOURCE"):
            self.c.source(e["event_id"],self.r.session)

    def test_rejects_missing_source_ref_without_guessing(self):
        e=self.event("original")
        with self.r.store.tx() as cur:
            row=cur.execute("SELECT packet FROM events WHERE id=?",(e["event_id"],)).fetchone()
            packet=json.loads(row[0]);packet.pop("source_ref")
            cur.execute("UPDATE events SET packet=? WHERE id=?",(json.dumps(packet),e["event_id"]))
        with self.assertRaisesRegex(ValueError,"CTXOS_SOURCE"):
            self.c.source(e["event_id"],self.r.session)


if __name__=="__main__":
    unittest.main()
