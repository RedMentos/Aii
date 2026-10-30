"""JEF self-outcome training rows require live exact source and decision identity."""
import tempfile
import unittest
from pathlib import Path

from v13 import fastpolicy as fp
from v13 import jefoutcome as jo
from v13.runtime import Runtime


class SelfOutcomeSourceAdmission(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")
        jo.set_mode(self.r.store, "learn")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def label(self, text):
        e = self.r.store.event(self.r.session, text)
        fp.head(self.r, "skill", e, "skill")
        self.r.store.message(self.r.session, e["event_id"], "assistant",
                             "Synthetic final", status="FINAL")
        self.assertEqual(jo.after_turn(
            self.r, e, {"skill": {"name": "synthetic_skill"}},
            "FINAL", {"coalition": []}), {"skill": "skill"})
        d = jo._decision(self.r.store, e["event_id"], "skill")
        st = self.r.store.state(jo.KEY)[0]
        x = next(x for x in st["labels"]
                 if x["event_id"] == e["event_id"]
                 and x["component"] == "skill")
        return e, d, x

    def rows(self, d):
        return jo.training_rows(self.r.store, "skill",
                                d["context_revision"], set())

    def replace_field(self, event_id, field, value):
        st, version = self.r.store.state(jo.KEY)
        for x in st["labels"]:
            if x["event_id"] == event_id and x["component"] == "skill":
                x[field] = value
        self.r.store.set_state(jo.KEY, st, expected=version)

    def test_live_exact_self_label_remains_trainable_candidate(self):
        _, d, x = self.label("first synthetic outcome context")
        rows = self.rows(d)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1]["source_id"], x["source_id"])
        self.assertEqual(rows[0][1]["value"], "skill")
        self.assertEqual(rows[0][2]["packet_id"], d["packet_id"])
        self.assertEqual(self.r.pool.pids(), [])

    def test_tombstoned_self_label_is_skipped_even_after_restart(self):
        _, d, x = self.label("revoked synthetic outcome context")
        self.assertEqual(len(self.rows(d)), 1)
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",
                      (x["source_id"],))
        self.assertEqual(self.rows(d), [])
        self.assertEqual(len(self.r.store.state(jo.KEY)[0]["labels"]), 1)
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(self.rows(d), [])

    def test_substituted_live_source_with_wrong_value_is_not_a_label(self):
        e, d, _ = self.label("substituted synthetic outcome context")
        foreign = self.r.store.source("none", jo.AUTHORITY)["source_id"]
        self.replace_field(e["event_id"], "source_id", foreign)
        self.assertEqual(self.rows(d), [])

    def test_other_event_decision_id_cannot_supply_a_training_row(self):
        e1, d1, _ = self.label("first unrelated decision context")
        _, d2, _ = self.label("second unrelated decision context")
        self.assertNotEqual(d1["context_ref"]["sha256"],
                            d2["context_ref"]["sha256"])
        self.replace_field(e1["event_id"], "decision_packet_id",
                           d2["packet_id"])
        rows = self.rows(d1)
        self.assertFalse(any(x[1]["event_id"] == e1["event_id"]
                             for x in rows))


if __name__ == "__main__":
    unittest.main()
