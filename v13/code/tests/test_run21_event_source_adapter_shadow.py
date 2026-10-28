"""Run21 RED-first real ephemeral Store source-ref integrity adapter tests."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import run17_german_typed_shadow as german
from scripts import run21_event_source_adapter_shadow as adapter
from v13.config import initialize
from v13.store import Store


class EventSourceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        home = Path(self.tmp.name)
        initialize(home)
        self.store = Store(home)
        self.session = self.store.new_session()
        self.old = self.store.event(self.session,
            "Projekt Nerava Auftaktnotiz: Budget 189 Euro. Frist 13 Tage. Lokalpflicht ja. "
            "No later project policy is implied.")
        self.sheet = self.store.event(self.session,
            "Projekt Nerava Lieferantenblatt Revision 4. " + "filler "*45 +
            "Option A: Kosten 166 Euro, Dauer 12 Tage, lokal ja. "
            "Option B: Kosten 176 Euro, Dauer 11 Tage, lokal nein.")
        self.current = self.store.event(self.session,
            "Projekt Nerava. Nutze die früheren verbindlichen Regeln und das aktuelle "
            "Lieferantenblatt für Option A und Option B. Berechne.")
        self.roles = {"old": self.old["event_id"], "sheet": self.sheet["event_id"],
                      "current": self.current["event_id"]}

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def reader(self, roles=None, session=None):
        return adapter.EventSourceReader(self.store, session or self.session,
                                         "Nerava", roles or self.roles)

    def test_real_source_sha_and_temporal_reader_candidate(self):
        reader = self.reader()
        result = german.evaluate("Nerava", self.roles["current"], self.roles["old"],
                                 self.roles["sheet"], "RETAIN_PRIOR_RULES", reader)
        self.assertEqual(result["action"], "A")
        self.assertEqual(result["status"], "SHADOW_ONLY")
        self.assertFalse(result["authority"])
        for ref in self.roles.values():
            row = reader(ref)
            self.assertTrue(row["verified"])
            self.assertFalse(row["authority"])
            self.assertTrue(reader.revalidate(ref, row["sha256"]))

    def test_revoke_and_corrupt_blob_fail_closed(self):
        reader = self.reader()
        row = reader(self.roles["old"])
        with self.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (self.old["source_ref"]["source_id"],))
        with self.assertRaises(adapter.Refusal):
            reader.revalidate(self.roles["old"], row["sha256"])
        # The typed reader intentionally normalizes a failed callback into its
        # own source_unavailable refusal; it never emits a candidate.
        with self.assertRaises(german.Refusal):
            german.evaluate("Nerava", self.roles["current"], self.roles["old"],
                            self.roles["sheet"], "RETAIN_PRIOR_RULES", reader)

    def test_tampered_blob_fails_even_when_db_hash_unchanged(self):
        reader = self.reader()
        digest = self.sheet["source_ref"]["sha256"]
        (self.store.home / "data/blobs" / digest).write_text("tampered")
        with self.assertRaises(adapter.Refusal):
            reader(self.roles["sheet"])

    def test_cross_session_and_unregistered_event_refuse(self):
        other = self.store.new_session()
        e = self.store.event(other, "Projekt Nerava. Budget 1 Euro.")
        roles = dict(self.roles, old=e["event_id"])
        with self.assertRaises(adapter.Refusal):
            self.reader(roles)
        with self.assertRaises(adapter.Refusal):
            self.reader()("evt_unknown")

    def test_role_order_duplicate_and_missing_refuse(self):
        with self.assertRaises(adapter.Refusal):
            self.reader(dict(self.roles, sheet=self.roles["old"]))
        with self.assertRaises(adapter.Refusal):
            self.reader({"old": self.roles["old"], "current": self.roles["current"]})
        with self.assertRaises(adapter.Refusal):
            self.reader({"old": self.roles["sheet"], "sheet": self.roles["old"],
                         "current": self.roles["current"]})

    def test_forged_event_envelope_source_ref_or_authority_refuse(self):
        for change in ("authority", "sha256", "char_start"):
            with self.subTest(change=change):
                row = self.store.one("SELECT packet FROM events WHERE id=?", (self.old["event_id"],))
                packet = json.loads(row["packet"])
                if change == "authority": packet["authority"] = "PROVISIONAL"
                if change == "sha256": packet["source_ref"]["sha256"] = "0"*64
                if change == "char_start": packet["source_ref"]["char_start"] = 1
                with self.store.tx() as c:
                    c.execute("UPDATE events SET packet=? WHERE id=?", (json.dumps(packet), self.old["event_id"]))
                with self.assertRaises(adapter.Refusal):
                    self.reader()
                with self.store.tx() as c:
                    c.execute("UPDATE events SET packet=? WHERE id=?", (row["packet"], self.old["event_id"]))


if __name__ == "__main__":
    unittest.main()
