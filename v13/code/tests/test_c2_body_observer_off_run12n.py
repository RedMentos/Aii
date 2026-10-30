"""Run12N prospective observer-OFF source-only and zero-offer witness tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import c2_body_observer_off_run12n as m
from scripts import c2_body_disjoint_paired181_run11v as frozen

FIXTURE = Path(__file__).resolve().parents[1] / "docs/fixtures/c2_body_observer_off_run12n_20261030.json"


def base_flags(offers=None, route="simple"):
    return {
        "route": route, "body_offer_roles": [] if offers is None else offers,
        "native_c2_invocation": True, "native_c2_selected": route != "simple",
        "route_valid": True, "output_valid": True, "source_exact": True,
        "process_release_valid": False, "valid_native": False,
    }


def witness(flags, releases=None, **overrides):
    releases = releases if releases is not None else [
        {"role": frozen.ROLE_BY_ROUTE[flags["route"]], "process_reaped": True}]
    args = {
        "native_context": {}, "native_alive": True, "native_reaped": True,
        "native_pid": 321, "source_exact": True, "session": "s",
        "event_id": "e", "source_text": "source",
        "release_capture_phase": "after_close",
    }
    args.update(overrides)
    with patch.object(frozen, "row_evidence", return_value=dict(flags)):
        return m.zero_offer_witness({}, "F_NATIVE_AUTO", releases, **args)


def fake_rows():
    rows = []
    for i in range(4):
        for arm in m.ARM_ORDER[i]:
            flags = {"valid_native": True, "body_offer_roles": [],
                     "expected_offer_roles": [], "observer_mode": "off",
                     "native_c2_invocation": arm == "F_NATIVE_AUTO",
                     "native_c2_selected": arm == "F_NATIVE_AUTO"}
            row = {"arm": arm, "flags": flags,
                   "score": {"correct": 1 if arm == "F_NATIVE_AUTO" else 0},
                   "secondary_score": {"correct": 0}}
            if arm == "F_NATIVE_AUTO":
                row["strict_admission"] = {"matches": True, "selected": True}
            rows.append(row)
    return rows


class Run12NTests(unittest.TestCase):
    def test_frozen_new_disjoint_seed_and_four_sources(self):
        f = m.load_fixture(FIXTURE)
        self.assertEqual(f["seed"], 197)
        self.assertEqual(m.fixture_hash(f["cases"]), m.FIXTURE_SHA256)
        self.assertEqual(len(f["cases"]), 4)
        self.assertFalse({frozen.prompt(c) for c in f["cases"]} &
                         {frozen.prompt(c) for c in frozen.FIXTURES})

    def test_fixture_tamper_rejected(self):
        with TemporaryDirectory() as td:
            p = Path(td) / "changed.json"
            data = json.loads(FIXTURE.read_text())
            data["cases"][0]["budget"] += 1
            p.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "FROZEN_FIXTURE"):
                m.load_fixture(p)

    def test_zero_offer_fallback_simple_valid(self):
        flags = witness(base_flags(route="simple"))
        self.assertEqual(flags["expected_offer_roles"], [])
        self.assertTrue(flags["process_release_valid"])
        self.assertTrue(flags["valid_native"])
        self.assertEqual(flags["observer_mode"], "off")

    def test_zero_offer_native_detail_valid(self):
        flags = witness(base_flags(route="detail"))
        self.assertTrue(flags["valid_native"])
        self.assertEqual(flags["expected_offer_roles"], [])

    def test_unexpected_background_offer_fails_closed(self):
        flags = witness(base_flags(offers=["B1_DETAIL"], route="simple"))
        self.assertFalse(flags["process_release_valid"])
        self.assertFalse(flags["valid_native"])

    def test_missing_native_reap_fails_closed(self):
        flags = witness(base_flags(route="simple"), native_reaped=False)
        self.assertFalse(flags["valid_native"])

    def test_missing_final_release_fails_closed(self):
        flags = witness(base_flags(route="detail"),
                        releases=[{"role": "C3_LANGUAGE", "process_reaped": True}])
        self.assertFalse(flags["valid_native"])

    def test_source_invalid_fails_closed(self):
        flags = base_flags(route="detail")
        flags["source_exact"] = False
        self.assertFalse(witness(flags)["valid_native"])

    def test_valid_synthetic_signal_never_promotes(self):
        r = m.summarize(fake_rows())
        self.assertTrue(r["all_native_structurally_valid"])
        self.assertTrue(r["native_auto_utility_pilot_signal_not_gate"])
        self.assertEqual(r["native_c2_changed_routes"], 4)
        for k in ("step2_gate_promoted", "b3_promoted",
                  "body_jepa_available", "redmi_measured",
                  "whole_system_complete", "comparative_utility_proven"):
            self.assertFalse(r[k], k)

    def test_extra_offer_invalidates_structural(self):
        rows = fake_rows()
        rows[0]["flags"]["body_offer_roles"] = ["B1_DETAIL"]
        self.assertFalse(m.summarize(rows)["all_native_structurally_valid"])

    def test_missing_strict_admission_invalidates(self):
        rows = fake_rows()
        next(x for x in rows if x["arm"] == "F_NATIVE_AUTO")[
            "strict_admission"]["matches"] = False
        self.assertFalse(m.summarize(rows)["all_native_structurally_valid"])

    def test_missing_turn_invalidates(self):
        self.assertFalse(m.summarize(fake_rows()[:15])["all_native_structurally_valid"])


if __name__ == "__main__":
    unittest.main()
