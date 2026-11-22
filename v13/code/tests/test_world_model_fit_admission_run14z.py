"""Run14Z: real SQLite T8 source provenance and non-migrating fitted-state admission."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from v13.runtime import Runtime
from v13.contracts import packet
from v13 import world_model as WM
from tests.test_world_model import synthetic

MARKER = "T8_JSON_UNIQUE_KEYS_V1"


class WorldModelFitAdmissionRun14Z(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def test_fit_marker_and_restart_preserve_new_state(self):
        with mock.patch.object(WM, "transitions", return_value=synthetic(n=48)):
            fitted = WM.fit(self.r.store, rng_seed=17)
        self.assertEqual(fitted["status"], "FITTED")
        self.assertEqual(fitted["source_admission"], MARKER)
        self.assertEqual(WM.load(self.r.store)["source_admission"], MARKER)
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual(WM.load(self.r.store)["forward"], fitted["forward"])
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")

    def test_unmarked_or_unknown_old_fit_never_gains_counterfactual_authority(self):
        data = synthetic(n=48)
        with mock.patch.object(WM, "transitions", return_value=data):
            fitted = WM.fit(self.r.store, rng_seed=17)
        self.assertIsNotNone(WM.counterfactual(self.r.store, data[4]["s"], "detail")["prediction"])
        for marker in (None, "T8_UNVERIFIED_SOURCE"):
            with self.subTest(marker=marker):
                old = dict(fitted)
                if marker is None:
                    old.pop("source_admission", None)
                else:
                    old["source_admission"] = marker
                self.r.store.set_state(WM.KEY, old)
                self.assertIsNone(WM.load(self.r.store))
                cf = WM.counterfactual(self.r.store, data[4]["s"], "detail", st=old)
                self.assertEqual((cf["reason"], cf["confidence"], cf["authority"]),
                                 ("NO_WORLD_MODEL", 0., "HYPOTHESIS"))
        self.r.store.set_state(WM.KEY, fitted)
        self.assertIsNotNone(WM.load(self.r.store))

    def test_too_few_fit_also_declares_source_admission(self):
        st = WM.fit(self.r.store)
        self.assertEqual(st["status"], "TOO_FEW_TRANSITIONS")
        self.assertEqual(st["source_admission"], MARKER)

    def test_real_sqlite_expected_outcome_and_selection_duplicate_keys_are_excluded(self):
        e = self.r.store.event(self.r.session, "Observed own digital action")
        p = packet("ActionSelection", "C5_ACTION_GATE", e["event_id"],
                   e["brain_generation_id"], [e["source_ref"]],
                   selected={"action_id": "TEXT_REPORT", "action_type": "TEXT_REPORT",
                             "score": 0., "permission_class": "local_text_only",
                             "focal_support": 0.},
                   candidates=[], suppressed=[], permission_class="local_text_only",
                   route_hint="detail", stage="COMMIT")
        self.r.store.add_packet("ActionSelection", p)
        aid = self.r.store.start_action(
            e["event_id"], e["brain_generation_id"],
            forecast={"input_chars": 100, "resource_state": "NORMAL"})
        self.r.store.finish_action(aid, "FINAL", {"action_duration_s": 1.5, "characters": 30})
        original = self.r.store.one("SELECT expected,outcome FROM actions WHERE id=?", (aid,))
        packet_raw = self.r.store.one("SELECT payload FROM packets WHERE id=?", (p["packet_id"],))["payload"]
        with self.r.store.tx() as c:
            c.execute("UPDATE packets SET created=? WHERE id=?", (
                self.r.store.one("SELECT created FROM actions WHERE id=?", (aid,))["created"] - 1,
                p["packet_id"]))
        self.assertEqual([t["action_id"] for t in WM.transitions(self.r.store)], [aid])

        cases = [
            ("actions", "expected", '{"forecast":{"input_chars":100,"input_chars":200,"resource_state":"NORMAL"}}'),
            ("actions", "outcome", '{"action_duration_s":1.5,"characters":30,"characters":31}'),
            ("packets", "payload", packet_raw.replace('"route_hint":"detail"',
                                                       '"route_hint":"detail","route_hint":"gist"')),
        ]
        self.assertNotEqual(cases[2][2], packet_raw)
        for table, column, bad in cases:
            with self.subTest(column=column):
                key = aid if table == "actions" else p["packet_id"]
                good = original[column] if table == "actions" else packet_raw
                with self.r.store.tx() as c:
                    c.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (bad, key))
                self.assertEqual(WM.transitions(self.r.store), [])
                if column == "expected":
                    cf = WM.for_event(self.r.store, e["event_id"], "detail")
                    self.assertEqual((cf["reason"], cf["confidence"]),
                                     ("INVALID_OBSERVED_STATE", 0.))
                with self.r.store.tx() as c:
                    c.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (good, key))
                self.assertEqual([t["action_id"] for t in WM.transitions(self.r.store)], [aid])
        self.r.close()
        self.r = Runtime(self.home)
        self.assertEqual([t["action_id"] for t in WM.transitions(self.r.store)], [aid])
        self.assertEqual(self.r.cfg["learning_mode"], "RECORD_ONLY")


if __name__ == "__main__":
    unittest.main()
