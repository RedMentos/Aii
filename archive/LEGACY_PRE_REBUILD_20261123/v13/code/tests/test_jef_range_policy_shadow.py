"""Run73 mixed range JEF real-Store SHADOW tests, not model/native evidence."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import jef_c3_c5_c6_operator_cli as cli
from v13 import jef_range_policy_shadow as rng
from v13 import jef_typed_source_shadow as old
from v13.common import dumps

# Preregistered labels A,B,NONE,A,B,NONE; no oracle text is sent to the reader.
TABLE = (
    ("R73A", "harbor drones", "Minimum", "Maximum", (100, 20, True),
     (120, 18, True), (90, 15, True), "A"),
    ("R73B", "museum drones", "Minimum", "Maximum", (100, 20, True),
     (130, 25, True), (140, 18, True), "B"),
    ("R73C", "forest drones", "Maximum", "Minimum", (100, 20, True),
     (90, 15, True), (110, 25, True), "NONE"),
    ("R73D", "island drones", "Maximum", "Minimum", (200, 10, False),
     (150, 12, False), (180, 11, True), "A"),
    ("R73E", "school drones", "Minimum", "Minimum", (70, 10, True),
     (60, 15, True), (75, 11, True), "B"),
    ("R73F", "archive drones", "Maximum", "Maximum", (150, 20, True),
     (120, 10, False), (130, 15, False), "NONE"),
)


def texts(row):
    project, domain, op1, op2, rule, a, b, _ = row
    tf = lambda value: "true" if value else "false"
    current = (f"Project {project}. Choose Option A or Option B using the "
               f"archived {domain} policy and latest option sheet. "
               "If neither qualifies, choose NONE.")
    policy = (f"Project {project} archived {domain} policy. "
              f"{op1} battery quota: {rule[0]} units. "
              f"{op2} start window: {rule[1]} ticks. "
              f"Required sealed: {tf(rule[2])}.")
    option = lambda label, x: (f"Option {label}: battery quota {x[0]} units; "
                                f"start window {x[1]} ticks; sealed {tf(x[2])}.")
    sheet = (f"Project {project} latest {domain} option sheet. "
             + option("A", a) + " " + option("B", b))
    return current, policy, sheet


class FixedRangeRealStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = cli.Runtime(Path(self.tmp.name))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def refs(self, row):
        current, policy, sheet = texts(row)
        return (self.r.store.source(current), [
            self.r.store.source(policy), self.r.store.source(sheet)])

    def decide(self, row, *, current_ref=None, source_refs=None, opt=True):
        cref, refs = self.refs(row)
        return rng.decide(self.r.store,
                          cref if current_ref is None else current_ref,
                          refs if source_refs is None else source_refs,
                          operator_opt_in=opt)

    def assert_no_authority(self, result):
        self.assertEqual(result["status"], "SHADOW_NO_AUTHORITY")
        self.assertEqual(result["authority"], 0)
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertFalse(result["human_source_lineage_verified"])
        self.assertFalse(result["model_called"])
        self.assertFalse(result["output_committed"])
        self.assertFalse(result["real_tty_approved"])
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["whole_system_complete"])
        self.assertNotIn("policy_source", result)
        self.assertNotIn("sheet_source", result)

    def test_six_mixed_bound_real_store_sources_and_no_model(self):
        self.assertEqual([row[-1] for row in TABLE],
                         ["A", "B", "NONE", "A", "B", "NONE"])
        with patch.object(self.r.pool, "get",
                          side_effect=AssertionError("NATIVE_CALLED")):
            for row in TABLE:
                with self.subTest(project=row[0]):
                    cref, refs = self.refs(row)
                    counts_before = [
                        self.r.store.one("SELECT COUNT(*) AS n FROM " + table)["n"]
                        for table in ("messages", "actions", "packets")]
                    result = rng.decide(self.r.store, cref, refs,
                                        operator_opt_in=True)
                    self.assertEqual(result["suggested_action"], row[-1])
                    self.assertEqual(result["reason"],
                                     "FULL_SOURCE_FIXED_RANGE_DECISION")
                    self.assertEqual(len(result["source_ref_sha256"]), 2)
                    self.assertEqual(counts_before, [
                        self.r.store.one("SELECT COUNT(*) AS n FROM " + table)["n"]
                        for table in ("messages", "actions", "packets")])
                    self.assert_no_authority(result)

    def test_old_maximum_only_reader_abstains_on_new_grammar(self):
        for row in TABLE[:5]:
            cref, refs = self.refs(row)
            self.assertEqual(old.decide(self.r.store, cref, refs)
                             ["suggested_action"], "UNKNOWN")
            self.assertEqual(rng.decide(self.r.store, cref, refs,
                                        operator_opt_in=True)
                             ["suggested_action"], row[-1])

    def test_default_off_and_nonboolean_optin(self):
        cref, refs = self.refs(TABLE[0])
        for opt in (False, 0, 1, None):
            result = rng.decide(self.r.store, cref, refs,
                                operator_opt_in=opt)
            self.assertEqual(result["suggested_action"], "UNKNOWN")
            self.assertEqual(result["reason"], "OFF")
            self.assert_no_authority(result)

    def test_duplicate_partial_and_swapped_sources(self):
        cref, refs = self.refs(TABLE[1])
        for source_refs in ([refs[0]], [refs[0], refs[0]], []):
            result = rng.decide(self.r.store, cref, source_refs,
                                operator_opt_in=True)
            self.assertEqual(result["suggested_action"], "UNKNOWN")
            self.assert_no_authority(result)
        swapped = rng.decide(self.r.store, cref, refs[::-1],
                             operator_opt_in=True)
        self.assertEqual(swapped["suggested_action"], "B")
        self.assert_no_authority(swapped)

    def test_revoked_and_partial_source_ref_fail_closed(self):
        cref, refs = self.refs(TABLE[0])
        partial = dict(refs[0], char_end=refs[0]["char_end"] - 1)
        self.assertEqual(rng.decide(self.r.store, cref, [partial, refs[1]],
                                    operator_opt_in=True)["suggested_action"],
                         "UNKNOWN")
        with self.r.store.tx() as db:
            db.execute("UPDATE sources SET deleted=1 WHERE id=?",
                       (refs[1]["source_id"],))
        result = rng.decide(self.r.store, cref, refs,
                            operator_opt_in=True)
        self.assertEqual(result["suggested_action"], "UNKNOWN")
        self.assert_no_authority(result)

    def test_wrong_project_and_unsupported_rule_wording_refused(self):
        cref, refs = self.refs(TABLE[0])
        current, policy, sheet = texts(TABLE[0])
        wrong = self.r.store.source(policy.replace("Project R73A", "Project R73Z"))
        unsupported = self.r.store.source(policy.replace("Minimum", "At least"))
        for bad in (wrong, unsupported):
            result = rng.decide(self.r.store, cref, [bad, refs[1]],
                                operator_opt_in=True)
            self.assertEqual(result["suggested_action"], "UNKNOWN")
            self.assert_no_authority(result)

    def test_field_unit_and_boolean_ambiguity_refused(self):
        cref, refs = self.refs(TABLE[0])
        current, policy, sheet = texts(TABLE[0])
        bads = (sheet.replace("units; start window", "ticks; start window"),
                policy.replace("Required sealed", "Required battery quota"),
                sheet.replace("sealed true", "sealed yes"))
        for i, value in enumerate(bads):
            with self.subTest(i=i):
                ref = self.r.store.source(value)
                source_refs = ([refs[0], ref] if i != 1
                               else [ref, refs[1]])
                result = rng.decide(self.r.store, cref, source_refs,
                                    operator_opt_in=True)
                self.assertEqual(result["suggested_action"], "UNKNOWN")
                self.assert_no_authority(result)

    def test_tie_break_is_smaller_first_then_second_then_a(self):
        row = ("R73G", "garden drones", "Minimum", "Maximum",
               (100, 20, False), (120, 15, True), (120, 15, False), "A")
        cref, refs = self.refs(row)
        result = rng.decide(self.r.store, cref, refs,
                            operator_opt_in=True)
        self.assertEqual(result["suggested_action"], "A")
        self.assert_no_authority(result)


if __name__ == "__main__":
    unittest.main()
