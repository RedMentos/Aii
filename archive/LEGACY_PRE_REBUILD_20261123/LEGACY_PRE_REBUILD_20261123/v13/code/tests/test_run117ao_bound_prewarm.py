"""Run117AO real-SQLite authenticated SourceRef + prewarm composition."""
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from scripts.run117am_body_source_id_native import fixture
from tests.test_run117ah_body_source_id_candidate import choose
from tests.test_run117s_b2_salient_source_shadow import QuoteRuntime
from v13.body_source_id_bound_prewarm_candidate import select_bound_prewarmed

FIXTURE = Path(__file__).resolve().parents[1]/(
    "docs/fixtures/RUN117AM_BODY_SOURCE_ID_SEED1073.json")


class BoundPrewarmTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.row=fixture(FIXTURE)[0]
        self.r=QuoteRuntime(Path(self.tmp.name)/"home",self.row)
        self.prior=self.r.store.event(self.r.session,self.row["prior"])
        self.trace=[]

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def acquire(self,role):
        self.trace.append("acquire")
        self.r.store.set_state("run117ao_bodyport",{"role":role,"state":"ASSIGNED"})
        return SimpleNamespace(role=role)

    def generate(self,runner,messages):
        self.trace.append("generate")
        return choose(runner.role)(messages)

    def release(self,runner):
        self.trace.append("release")
        self.r.store.set_state("run117ao_bodyport",{"role":runner.role,"state":"RELEASED"})

    def call(self,event=None,role="B2_GIST",**kwargs):
        return select_bound_prewarmed(
            self.r,event if event is not None else self.prior,role,
            kwargs.pop("acquire",self.acquire),
            kwargs.pop("generate",self.generate),
            kwargs.pop("release",self.release),
            operator_opt_in=kwargs.pop("operator_opt_in",True),
            callback_opt_in=kwargs.pop("callback_opt_in",True),
            **kwargs)

    def assert_safe(self,r):
        self.assertFalse(r["output_committed"])
        self.assertFalse(r["native_model_proven"])
        self.assertFalse(r["source_semantic_truth_authority"])
        self.assertTrue(r["model_hypothesis_not_fact"])
        self.assertEqual(r["learning_authority"],0)
        self.assertEqual(r["delivery_authority"],0)
        self.assertEqual(r["tool_dispatches"],0)
        self.assertEqual(r["jepa_weight"],0)
        self.assertFalse(r["whole_system_complete"])

    def test_six_fresh_rows_both_roles_source_bound(self):
        for row in fixture(FIXTURE):
            with self.subTest(project=row["id"]):
                with tempfile.TemporaryDirectory() as d:
                    runtime=QuoteRuntime(Path(d)/"home",row)
                    try:
                        def acquire(role):
                            runtime.store.set_state("run117ao_port",{"role":role})
                            return SimpleNamespace(role=role)
                        def release(runner):
                            runtime.store.set_state("run117ao_port",{"released":True})
                        for role,source in (
                            ("B2_GIST",row["prior"]),
                            ("B1_DETAIL",row["current"])):
                            event=runtime.store.event(runtime.session,source)
                            r=select_bound_prewarmed(
                                runtime,event,role,acquire,
                                lambda runner,messages:choose(runner.role)(messages),
                                release,operator_opt_in=True,callback_opt_in=True)
                            self.assertEqual(r["status"],
                                "SHADOW_EVENT_SOURCE_BOUND_CORRECT",r)
                            self.assertTrue(r["authoritative_event_source_verified"])
                            self.assertEqual(r["source_ref"],event["source_ref"])
                            self.assert_safe(r)
                    finally:
                        runtime.close()

    def test_forged_latest_event_with_prior_source_ref_rejected_before_acquire(self):
        current=self.r.store.event(self.r.session,self.row["current"])
        forged=dict(current,source_ref=self.prior["source_ref"])
        r=self.call(event=forged,role="B2_GIST")
        self.assertEqual(r["status"],"EVENT_SOURCE_PREFLIGHT_RED")
        self.assertEqual(self.trace,[])
        self.assert_safe(r)

    def test_forged_generation_rejected(self):
        forged=dict(self.prior,brain_generation_id="FORGED")
        r=self.call(event=forged)
        self.assertEqual(r["status"],"EVENT_SOURCE_PREFLIGHT_RED")
        self.assertEqual(self.trace,[])
        self.assert_safe(r)

    def test_late_user_during_prewarm_rejected_before_generator(self):
        def acquire(role):
            runner=self.acquire(role)
            self.r.store.event(self.r.session,self.row["current"])
            return runner
        r=self.call(acquire=acquire)
        self.assertEqual(r["status"],"EVENT_SOURCE_PREFLIGHT_RED")
        self.assertEqual(self.trace,["acquire","release"])
        self.assert_safe(r)

    def test_store_mutation_inside_callback_still_red(self):
        def mutate(runner,messages):
            self.r.store.set_state("run117ao_late",{"changed":True})
            return self.generate(runner,messages)
        r=self.call(generate=mutate)
        self.assertEqual(r["status"],"FROZEN_SELECTOR_RED")
        self.assertEqual(r["component_status"],"CALLBACK_STORE_CHANGED_RED")
        self.assertEqual(self.trace,["acquire","generate","release"])
        self.assert_safe(r)

    def test_wrong_role_never_generates(self):
        def acquire(role):
            runner=self.acquire(role)
            runner.role="B1_DETAIL"
            return runner
        r=self.call(acquire=acquire)
        self.assertEqual(r["status"],"PREWARM_ROLE_RED")
        self.assertEqual(self.trace,["acquire","release"])
        self.assert_safe(r)

    def test_off_and_approval_do_not_acquire(self):
        for kw,status in (
            ({"operator_opt_in":False},"OFF"),
            ({"callback_opt_in":False},"OFF"),
            ({"approval_receipt":{"approved":True}},
             "REAL_TTY_APPROVAL_UNSUPPORTED_RED")):
            r=self.call(**kw)
            self.assertEqual(r["status"],status)
            self.assert_safe(r)
        self.assertEqual(self.trace,[])

    def test_release_exception_never_reports_success(self):
        def fail(runner):
            self.trace.append("release")
            raise RuntimeError("not reaped")
        r=self.call(release=fail)
        self.assertEqual(r["status"],"RELEASE_EXCEPTION_RED")
        self.assertEqual(self.trace,["acquire","generate","release"])
        self.assert_safe(r)

    def test_wrong_model_id_remains_fallible(self):
        def wrong(runner,messages):
            data=json.loads(messages[1]["content"])
            other=next(x["span_id"] for x in data["candidates"]
                       if "Binding policy:" not in x["text"])
            return json.dumps({"span_id":other})
        r=self.call(generate=wrong)
        self.assertEqual(r["status"],"SHADOW_EVENT_SOURCE_BOUND_WRONG")
        self.assertFalse(r["model_selection_correct_shadow"])
        self.assert_safe(r)


if __name__=="__main__":
    unittest.main()
