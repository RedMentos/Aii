"""Run55 corrected native wrapper: persisted packet and model identity tests."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import run55_b1b2_topic_native_corrective as run55
from scripts import run55_b1b2_topic_native_verify as verify55
from scripts.run52_b1b2_cross_turn_native import load_fixture, OVERRIDES
from tests.test_run52_b1b2_cross_turn import FakeRuntime
from v13.b1b2_topic_partition_candidate import TopicPartitionOfferConsumer

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/run52_b1b2_cross_turn_seed479.json"


class Run55CorrectiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.r = FakeRuntime(self.home)
        self.r.cfg.update(OVERRIDES)
        self.consumer = TopicPartitionOfferConsumer(self.r)
        self.f = {x["id"]:x for x in load_fixture(FIXTURE)["fixtures"]}

    def tearDown(self):
        self.r.close()
        self.temp.cleanup()

    def offered(self, role="B1_DETAIL"):
        event = self.r.store.event(self.r.session, self.f["Harbor"]["prior"])
        result = self.consumer.guarded_offer(
            role, event, 0, time.monotonic()+30, operator_opt_in=True)
        self.assertEqual(result["status"], "SHADOW_OFFER_PRODUCED")
        return event, result

    def test_real_persisted_offer_and_query_are_recovered_by_ids(self):
        for role in ("B1_DETAIL", "B2_GIST"):
            with self.subTest(role=role):
                event, result = self.offered(role)
                offer, query = run55.persisted_offer(
                    self.r.store, result, role, event, self.r.models.revision(role))
                self.assertEqual(offer["packet_id"], result["offer_packet_id"])
                self.assertEqual(offer["query_packet_id"], query["packet_id"])
                self.assertEqual(query["target_role"], role)
                self.assertEqual(offer["provenance"][0], event["source_ref"])
                self.assertIsInstance(offer["offer"]["summary"], str)

    def test_wrong_offer_or_query_id_refused(self):
        event, result = self.offered()
        for field in ("offer_packet_id", "query_packet_id"):
            with self.subTest(field=field):
                bad = dict(result, **{field: "pkt_not_present"})
                with self.assertRaises(ValueError):
                    run55.persisted_offer(
                        self.r.store, bad, "B1_DETAIL", event,
                        self.r.models.revision("B1_DETAIL"))

    def test_wrong_role_revision_and_event_refused(self):
        event, result = self.offered()
        for role, revision, source in (
            ("B2_GIST", self.r.models.revision("B1_DETAIL"), event),
            ("B1_DETAIL", "wrong-revision", event),
            ("B1_DETAIL", self.r.models.revision("B1_DETAIL"),
             dict(event, event_id="evt_forged")),
        ):
            with self.subTest(role=role,revision=revision):
                with self.assertRaises(ValueError):
                    run55.persisted_offer(self.r.store, result, role, source, revision)

    def test_tampered_persisted_offer_binding_refused(self):
        event, result = self.offered()
        row = self.r.store.one(
            "SELECT payload FROM packets WHERE id=?", (result["offer_packet_id"],))
        original = row["payload"]
        for field, replacement in (
            ("role", "B2_GIST"),
            ("query_packet_id", "pkt_other"),
            ("provenance", []),
        ):
            with self.subTest(field=field):
                modified = json.loads(original)
                modified[field] = replacement
                with self.r.store.tx() as db:
                    db.execute("UPDATE packets SET payload=? WHERE id=?",
                               (json.dumps(modified), result["offer_packet_id"]))
                with self.assertRaises(ValueError):
                    run55.persisted_offer(
                        self.r.store, result, "B1_DETAIL", event,
                        self.r.models.revision("B1_DETAIL"))
                with self.r.store.tx() as db:
                    db.execute("UPDATE packets SET payload=? WHERE id=?",
                               (original, result["offer_packet_id"]))

    def test_distinct_b2_pin_is_not_b1(self):
        self.assertNotEqual(verify55.B1_SHA, verify55.B2_SHA)
        self.assertEqual(verify55.ROLE_FILES["B2_GIST"], "Qwen3.5-0.8B-Q4_0.gguf")

    def test_fake_runner_never_promotes_native(self):
        with tempfile.TemporaryDirectory() as d, \
                patch.object(run55,"Runtime",FakeRuntime), \
                patch.object(run55,"installed_links",lambda *a:None):
            row = run55.run_row(Path(d)/"home", Path(d)/"installed", self.f)
            self.assertNotEqual(row["status"], "RECORDED")
            self.assertFalse(row["native_model"])
            self.assertEqual(row["native_process_count"], 0)


if __name__ == "__main__":
    unittest.main()
