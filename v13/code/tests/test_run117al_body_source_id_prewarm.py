"""Run117AL real-SQLite model-free prewarm lifecycle regression."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from tests.test_run117ah_body_source_id_candidate import rows, choose
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.b1b2_source_id_quote_candidate import KIND, select
from v13.body_source_id_prewarm_candidate import select_prewarmed


class PrewarmBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.row = rows()[0]  # Frozen seed1069: software regression ONLY.
        self.r = QuoteRuntime(Path(self.tmp.name) / "home", self.row)
        self.prior = self.r.store.event(self.r.session, self.row["prior"])
        self.trace = []

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def acquire(self, role):
        self.trace.append("acquire")
        self.r.store.set_state("run117al_bodyport", {"state": "ASSIGNED"})
        return SimpleNamespace(role=role)

    def generate(self, runner, messages):
        self.trace.append("generate")
        return choose(runner.role)(messages)

    def release(self, runner):
        self.trace.append("release")
        self.r.store.set_state("run117al_bodyport", {"state": "RELEASED"})

    def call(self, **kw):
        return select_prewarmed(
            self.r, self.prior, "B2_GIST",
            kw.pop("acquire", self.acquire),
            kw.pop("generate", self.generate),
            kw.pop("release", self.release),
            operator_opt_in=kw.pop("operator_opt_in", True),
            callback_opt_in=kw.pop("callback_opt_in", True),
            **kw,
        )

    def assert_nonpromoting(self, result):
        self.assertFalse(result["output_committed"])
        self.assertEqual(result["tool_dispatches"], 0)
        self.assertEqual(result["learning_authority"], 0)
        self.assertEqual(result["delivery_authority"], 0)
        self.assertEqual(result["jepa_weight"], 0)
        self.assertFalse(result["native_model_proven"])
        self.assertFalse(result["whole_system_complete"])

    def test_original_inside_callback_bodyport_write_remains_red(self):
        def old_callback(messages):
            runner = self.acquire("B2_GIST")
            return self.generate(runner, messages)
        result = select(self.r, self.prior, "B2_GIST", old_callback,
                        operator_opt_in=True, callback_opt_in=True)
        self.assertEqual(result["status"], "CALLBACK_STORE_CHANGED_RED")
        self.assertEqual(self.r.store.one(
            "SELECT COUNT(*) AS n FROM packets WHERE kind=?", (KIND,))["n"], 0)
        self.assert_nonpromoting(result)

    def test_prewarm_outside_epoch_preserves_source_and_zero_authority(self):
        result = self.call()
        self.assertEqual(result["status"], "SHADOW_SOURCE_ID_SELECTED", result)
        self.assertEqual(self.trace, ["acquire", "generate", "release"])
        packet = json.loads(self.r.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind=?",
            (result["packet_id"], KIND))["payload"])
        self.assertEqual(packet["selected_span"]["text"], self.row["policy_span"])
        self.assertEqual(self.r.store.read_source(
            packet["selected_span"]["source_ref"]), self.row["policy_span"])
        self.assertEqual(self.r.store.state("run117al_bodyport")[0]["state"],
                         "RELEASED")
        self.assert_nonpromoting(result)

    def test_callback_store_mutation_after_prewarm_still_red(self):
        def bad(runner, messages):
            self.r.store.set_state("run117al_after_epoch", {"changed": True})
            return self.generate(runner, messages)
        result = self.call(generate=bad)
        self.assertEqual(result["status"], "CALLBACK_STORE_CHANGED_RED")
        self.assertEqual(self.trace, ["acquire", "generate", "release"])
        self.assert_nonpromoting(result)

    def test_source_replaced_during_acquisition_is_rejected(self):
        def change(role):
            runner = self.acquire(role)
            self.r.store.event(self.r.session, "Project Auric newer instruction.")
            return runner
        result = self.call(acquire=change)
        self.assertEqual(result["status"], "SOURCE_PREFLIGHT_RED")
        self.assertEqual(self.trace, ["acquire", "release"])
        self.assert_nonpromoting(result)

    def test_wrong_role_runner_never_generates(self):
        def wrong(role):
            runner = self.acquire(role)
            runner.role = "B1_DETAIL"
            return runner
        result = self.call(acquire=wrong)
        self.assertEqual(result["status"], "PREWARM_ROLE_RED")
        self.assertEqual(self.trace, ["acquire", "release"])
        self.assert_nonpromoting(result)

    def test_off_and_approval_never_acquire(self):
        result = self.call(operator_opt_in=False)
        self.assertEqual(result["status"], "OFF")
        self.assertEqual(self.trace, [])
        self.assert_nonpromoting(result)
        result = self.call(approval_receipt={"approved": True})
        self.assertEqual(result["status"], "REAL_TTY_APPROVAL_UNSUPPORTED_RED")
        self.assertEqual(self.trace, [])
        self.assert_nonpromoting(result)

    def test_stale_source_rejected_before_acquisition(self):
        self.r.store.event(self.r.session, self.row["current"])
        result = self.call()
        self.assertEqual(result["status"], "SOURCE_PREFLIGHT_RED")
        self.assertEqual(self.trace, [])
        self.assert_nonpromoting(result)

    def test_generator_exception_still_releases(self):
        def error(runner, messages):
            self.trace.append("generate")
            raise RuntimeError("synthetic")
        result = self.call(generate=error)
        self.assertEqual(result["status"], "CALLBACK_EXCEPTION_RED")
        self.assertEqual(self.trace, ["acquire", "generate", "release"])
        self.assert_nonpromoting(result)

    def test_release_failure_overrides_success(self):
        def fail(runner):
            self.trace.append("release")
            raise RuntimeError("cannot reap")
        result = self.call(release=fail)
        self.assertEqual(result["status"], "RELEASE_EXCEPTION_RED")
        self.assertEqual(self.trace, ["acquire", "generate", "release"])
        self.assert_nonpromoting(result)

    def test_acquisition_failure_cannot_be_mistaken_for_model_call(self):
        def fail(role):
            raise RuntimeError("no runner")
        result = self.call(acquire=fail)
        self.assertEqual(result["status"], "PREWARM_EXCEPTION_RED")
        self.assertEqual(self.trace, [])
        self.assert_nonpromoting(result)


if __name__ == "__main__":
    unittest.main()
