"""Run117BF actual SQLite USER SourceRef span authentication, synthetic text only."""
import json
import tempfile
import unittest
from pathlib import Path

from v13.body_jepa_store_source_binding_shadow import (
    bind_store_rows, recheck_store_rows,
)
from v13.store import Store
from v13.common import dumps


def make_row(event, source, question, answer, view, path="B1_DETAIL"):
    full = event["source_ref"]
    qstart = source.index(question)
    astart = source.index(answer, qstart + len(question))
    context = dict(full, char_start=qstart, char_end=qstart + len(question))
    target = dict(full, char_start=astart, char_end=astart + len(answer))
    return {
        "event_id": event["event_id"], "source_ref": full,
        "context_ref": context, "target_ref": target,
        "path": path, "source_id": full["source_id"],
        "source_sha256": full["sha256"],
        "context_source_sha256": full["sha256"],
        "target_source_sha256": full["sha256"],
        "view_id": view, "eligibility": 1.0,
        "prompt": question, "target": answer,
    }


class StoreSourceBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "data/db").mkdir(parents=True)
        (self.home / "data/blobs").mkdir(parents=True)
        self.store = Store(self.home)
        self.session = self.store.new_session()
        self.a_text = "Question: Avelorn copper key?\nAnswer: Kestrel."
        self.b_text = "Question: Brimora jade key?\nAnswer: Nimbus."
        self.c_text = "Question: Caelith indigo key?\nAnswer: Saffron."
        self.a = self.store.event(self.session, self.a_text)
        self.b = self.store.event(self.session, self.b_text)
        self.c = self.store.event(self.session, self.c_text)
        self.rows = [
            make_row(self.a, self.a_text, "Avelorn copper key?", "Kestrel", "a1"),
            make_row(self.a, self.a_text, "Avelorn copper key?", "Kestrel", "a2"),
            make_row(self.b, self.b_text, "Brimora jade key?", "Nimbus", "b1"),
        ]
        self.heldout = [make_row(self.c, self.c_text, "Caelith indigo key?",
                                 "Saffron", "c1")]

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def bind(self, rows=None, heldout=None):
        return bind_store_rows(self.store, self.session,
                               self.rows if rows is None else rows,
                               heldout_rows=self.heldout if heldout is None else heldout,
                               operator_opt_in=True)

    def test_actual_store_source_spans_and_read_only_receipt(self):
        before = [self.store.one("SELECT COUNT(*) AS n FROM " + table)["n"]
                  for table in ("events", "packets", "actions", "updates", "messages")]
        got = self.bind()
        after = [self.store.one("SELECT COUNT(*) AS n FROM " + table)["n"]
                 for table in ("events", "packets", "actions", "updates", "messages")]
        self.assertEqual(before, after)
        self.assertEqual(got["status"], "SHADOW_STORE_SOURCE_BOUND")
        self.assertEqual((got["source_group_count"], got["repeated_view_count"]), (2, 1))
        self.assertEqual(got["source_authentication"], "EXACT_STORE_USER_EVENT_SPANS")
        self.assertFalse(got["semantic_truth_authority"])
        self.assertEqual((got["native_calls"], got["learning_authority"],
                          got["runtime_jepa_weight"], got["tool_dispatches"]), (0, 0, 0, 0))
        self.assertNotIn("Kestrel", json.dumps(got))
        self.assertEqual(recheck_store_rows(self.store, self.session, self.rows, got,
                                            heldout_rows=self.heldout,
                                            operator_opt_in=True), got)

    def test_off_refuses_without_store_reads(self):
        self.assertEqual(bind_store_rows(None, None, self.rows)["status"], "OFF")
        with self.assertRaisesRegex(ValueError, "PRIOR_STORE_RECEIPT_RED"):
            recheck_store_rows(self.store, self.session, self.rows, {"status": "OFF"})

    def test_forged_context_and_target_span_refused(self):
        forged = [dict(x) for x in self.rows]
        forged[0]["context_ref"] = dict(self.b["source_ref"],
                                        char_start=0, char_end=8)
        with self.assertRaisesRegex(ValueError, "SOURCE_SPAN_ORIGIN_RED"):
            self.bind(forged)
        forged = [dict(x) for x in self.rows]
        forged[0]["target_ref"] = dict(forged[0]["target_ref"], char_start=0, char_end=7)
        with self.assertRaisesRegex(ValueError, "EVENT_CONTEXT_TARGET_TEXT_RED"):
            self.bind(forged)

    def test_foreign_session_refused(self):
        foreign = self.store.new_session()
        with self.assertRaisesRegex(ValueError, "EVENT_SESSION_OR_SOURCE_RED"):
            bind_store_rows(self.store, foreign, self.rows, heldout_rows=self.heldout,
                            operator_opt_in=True)

    def test_deleted_source_revokes_recheck(self):
        receipt = self.bind()
        with self.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (self.a["source_ref"]["source_id"],))
        with self.assertRaises(ValueError):
            recheck_store_rows(self.store, self.session, self.rows, receipt,
                               heldout_rows=self.heldout, operator_opt_in=True)

    def test_blob_tamper_refused(self):
        path = self.home / "data/blobs" / self.a["source_ref"]["sha256"]
        path.write_bytes(b"TAMPERED_TEST_ONLY")
        with self.assertRaises(ValueError):
            self.bind()

    def test_event_packet_tamper_refused(self):
        raw = self.store.one("SELECT packet FROM events WHERE id=?",
                             (self.a["event_id"],))["packet"]
        packet = json.loads(raw)
        packet["authority"] = "MODEL_GENERATED"
        with self.store.tx() as db:
            db.execute("UPDATE events SET packet=? WHERE id=?",
                       (dumps(packet), self.a["event_id"]))
        with self.assertRaisesRegex(ValueError, "EVENT_PACKET_BINDING_RED"):
            self.bind()

    def test_source_kind_spoof_refused(self):
        with self.store.tx() as db:
            db.execute("UPDATE sources SET kind='MODEL' WHERE id=?",
                       (self.a["source_ref"]["source_id"],))
        with self.assertRaisesRegex(ValueError, "EVENT_SESSION_OR_SOURCE_RED"):
            self.bind()

    def test_heldout_leak_refused(self):
        with self.assertRaisesRegex(ValueError, "HELDOUT_SOURCE_LEAK_RED"):
            self.bind(heldout=[dict(self.rows[0], view_id="new")])

    def test_restart_revalidation(self):
        receipt = self.bind()
        self.store.close()
        self.store = Store(self.home)
        self.assertEqual(recheck_store_rows(self.store, self.session, self.rows,
                                            receipt, heldout_rows=self.heldout,
                                            operator_opt_in=True), receipt)

    def test_unicode_offsets_are_character_based(self):
        text = "Question: Äpfel?\nAnswer: Grün."
        e = self.store.event(self.session, text)
        r = make_row(e, text, "Äpfel?", "Grün", "unicode1")
        got = self.bind(rows=[r, self.rows[2]], heldout=[])
        self.assertEqual(got["source_group_count"], 2)

    def test_source_claim_tamper_refused(self):
        forged = [dict(x) for x in self.rows]
        forged[0]["source_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.bind(forged)


if __name__ == "__main__":
    unittest.main()
