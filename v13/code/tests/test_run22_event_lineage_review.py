"""Run22 RED-first: persisted EventEnvelope lineage must bind the real Store row.

Software-only, ephemeral SQLite + real Store blobs. No native/model/Runtime use.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import run17_german_typed_shadow as german
from scripts import run21_event_source_adapter_shadow as adapter
from v13.config import initialize
from v13.store import Store


class EventLineageReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        home = Path(self.temp.name)
        initialize(home)
        self.store = Store(home)
        self.session = self.store.new_session()
        old = self.store.event(
            self.session, "Projekt Nerava Auftaktnotiz: Budget 189 Euro. "
            "Frist 13 Tage. Lokalpflicht ja.")
        sheet = self.store.event(
            self.session, "Projekt Nerava Lieferantenblatt. "
            "Option A: Kosten 166 Euro, Dauer 12 Tage, lokal ja. "
            "Option B: Kosten 176 Euro, Dauer 11 Tage, lokal nein.")
        current = self.store.event(
            self.session, "Projekt Nerava. Nutze die früheren verbindlichen Regeln "
            "und das aktuelle Lieferantenblatt für Option A und Option B. Berechne.")
        self.refs = {"old": old["event_id"], "sheet": sheet["event_id"],
                     "current": current["event_id"]}

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def reader(self):
        return adapter.EventSourceReader(self.store, self.session, "Nerava", self.refs)

    def patch_packet(self, ref, change):
        original = self.store.one("SELECT packet FROM events WHERE id=?", (ref,))["packet"]
        packet = json.loads(original)
        change(packet)
        with self.store.tx() as db:
            db.execute("UPDATE events SET packet=? WHERE id=?",
                       (json.dumps(packet), ref))
        return original

    def test_clean_historical_events_remain_shadow_only(self):
        reader = self.reader()
        result = german.evaluate("Nerava", self.refs["current"],
                                 self.refs["old"], self.refs["sheet"],
                                 "RETAIN_PRIOR_RULES", reader)
        self.assertEqual(result["action"], "A")
        self.assertFalse(result["authority"])
        self.assertEqual(reader(self.refs["old"])["verification_scope"],
                         "EVENT_SOURCE_INTEGRITY_ONLY")

    def test_forged_envelope_identity_and_lineage_refuse(self):
        old = self.refs["old"]
        attacks = {
            "schema": lambda p: p.update(schema_version="9.9"),
            "producer": lambda p: p.update(producer_component="C3_LANGUAGE"),
            "generation": lambda p: p.update(brain_generation_id="gen_forged"),
            "experience": lambda p: p.update(experience_id="exp_forged"),
            "provenance_missing": lambda p: p.update(provenance=[]),
            "provenance_extra": lambda p: p["provenance"].append(
                copy.deepcopy(p["source_ref"])),
            "provenance_wrong": lambda p: p["provenance"][0].update(
                sha256="0" * 64),
            "source_ref_extra": lambda p: p["source_ref"].update(
                verified=True),
        }
        for label, change in attacks.items():
            with self.subTest(label=label):
                original = self.patch_packet(old, change)
                try:
                    with self.assertRaises(adapter.Refusal):
                        self.reader()
                finally:
                    with self.store.tx() as db:
                        db.execute("UPDATE events SET packet=? WHERE id=?",
                                   (original, old))

    def test_source_row_byte_and_char_count_refuse(self):
        old = self.refs["old"]
        source_id = json.loads(self.store.one(
            "SELECT packet FROM events WHERE id=?", (old,))["packet"]
        )["source_ref"]["source_id"]
        for field in ("bytes", "chars"):
            with self.subTest(field=field):
                with self.store.tx() as db:
                    db.execute(f"UPDATE sources SET {field}={field}+1 WHERE id=?",
                               (source_id,))
                try:
                    with self.assertRaises(adapter.Refusal):
                        self.reader()
                finally:
                    with self.store.tx() as db:
                        db.execute(f"UPDATE sources SET {field}={field}-1 WHERE id=?",
                                   (source_id,))


if __name__ == "__main__":
    unittest.main()
