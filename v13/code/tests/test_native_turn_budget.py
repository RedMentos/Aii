"""Whole-turn recovery policy using genuine-shaped, content-free Redmi metrics."""
import json
import threading
import time
import unittest
from v13.cognition import Cognition
from v13.common import Limits
from v13 import native_turn_budget as budget


def turn(status="DEADLINE", *, generated=0, phase="prefill", role="C3_LANGUAGE",
         duration_s=29.1):
    return {"status":status,"metadata":json.dumps({
        "runner":{"role":role,"generated_tokens":generated,
                  "last_phase":phase,"duration_s":duration_s},
        "raw_user_prompt":"PRIVATE NEVER SELECT OR RETURN",
    })}


class DummyStore:
    def __init__(self, rows):
        self.proof = rows
        self.query = None
        self.args = None
    def rows(self, query, args):
        self.query = query
        self.args = args
        return self.proof


class NativeTurnBudgetTests(unittest.TestCase):
    def test_two_observed_c3_zero_token_deadlines_reserve_c3_time(self):
        rows=[turn(),turn(),turn("FINAL",generated=21,phase="stream",duration_s=6.5)]
        d=budget.plan(100,130,104.2,recent=rows,background_enabled=True)
        self.assertTrue(d["recovery"])
        self.assertEqual(d["reason"],"RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS")
        self.assertAlmostEqual(d["c3_reserve_estimate_seconds"],9.775)
        self.assertAlmostEqual(d["c3_reserved_seconds"],9.775)
        self.assertEqual(d["c3_reserve_source"],"RECENT_SUCCESS_MAX")
        self.assertLess(d["c3_reserved_seconds"],15)
        self.assertAlmostEqual(d["preanswer_seconds_available"],15.025)
        self.assertFalse(d["postcommit_body_eligible"])
        self.assertFalse(d["age_changed"])
        self.assertFalse(d["memory_or_native_weights_changed"])

    def test_one_failure_keeps_full_synchronous_cognitive_window(self):
        d=budget.plan(100,130,103.5,recent=[turn()])
        self.assertFalse(d["recovery"])
        self.assertAlmostEqual(d["preanswer_end_monotonic"],113.5)
        self.assertEqual(d["reason"],"NORMAL_COGNITIVE_PREANSWER")
        self.assertFalse(d["postcommit_body_eligible"])

    def test_longer_deep_turn_preserves_both_body_roles(self):
        d=budget.plan(100,190,104,recent=[turn(),turn(),turn()])
        self.assertFalse(d["recovery"])
        self.assertAlmostEqual(d["preanswer_end_monotonic"],140.5)

    def test_explicit_foreground_no_background_never_silently_defers(self):
        d=budget.plan(100,130,103.5,recent=[turn(),turn()],
                      background_enabled=False)
        self.assertFalse(d["recovery"])
        self.assertEqual(d["recent_real_prefill_failures"],2)

    def test_two_real_successes_reset_recovery(self):
        d=budget.plan(100,130,104,
            recent=[turn("FINAL",generated=6,phase="stream"),
                    turn("FINAL",generated=13,phase="stream"),
                    turn(),turn(),turn()])
        self.assertFalse(d["recovery"])
        self.assertEqual(d["recent_success_streak"],2)

    def test_untrusted_missing_data_is_not_a_phone_failure(self):
        bad=[
            turn("ERROR",generated=0),
            turn("DEADLINE",generated=1),
            turn("DEADLINE",generated=False),
            turn("DEADLINE",phase="stream"),
            turn("DEADLINE",role="B1_DETAIL"),
            {"status":"DEADLINE","metadata":"PRIVATE MALFORMED JSON"},
            {"status":"DEADLINE","metadata":{"runner":{"role":"C3_LANGUAGE",
                 "generated_tokens":"0","last_phase":"prefill"}}},
        ]
        for row in bad:
            with self.subTest(row=row):
                self.assertFalse(budget.zero_token_prefill_failure(row))
        self.assertFalse(budget.plan(100,130,105,recent=bad)["recovery"])

    def test_direct_source_copy_never_changes_preanswer_budget(self):
        d=budget.plan(100,130,102,recent=[turn(),turn()],direct=True)
        self.assertFalse(d["recovery"])

    def test_recent_proof_selects_only_status_and_metadata(self):
        rows=[{"status":"DEADLINE","metadata":"{}","text":"PRIVATE NEVER EXPORT"}]
        store=DummyStore(rows)
        result=budget.recent_proof(store)
        self.assertEqual(result,[{"status":"DEADLINE","metadata":"{}"}])
        self.assertNotIn("text",store.query.lower())
        self.assertNotIn("PRIVATE",json.dumps(result))
        self.assertEqual(store.args,(budget.MAX_RECENT,))

    def test_real_cognition_uses_fair_slice_and_keeps_postcommit_path(self):
        class LocalStore(DummyStore):
            def __init__(self, rows):
                super().__init__(rows)
                self.logs=[]
                self.source_reads=0
            def log(self,kind,event,metrics):
                self.logs.append((kind,event,metrics))
            def read_source(self,ref):
                self.source_reads+=1
                raise AssertionError("source read reached after budget check")
        class FakeRuntime:
            def __init__(self, cfg, store):
                self.cfg=cfg
                self.store=store
                self.cancel_event=threading.Event()
                self.session="s1"
        store=LocalStore([turn(),turn()])
        runtime=FakeRuntime({"deadline_seconds":30,
                             "observer_mode":"background"},store)
        cognition=Cognition(runtime)
        end=time.monotonic()+30
        with self.assertRaisesRegex(AssertionError,"source read reached"):
            cognition.offer("B1_DETAIL",{"event_id":"e1","source_ref":{}},1,end-18,
                            valid_until=end)
        self.assertEqual(store.source_reads,1)
        self.assertEqual(store.logs[0][0],"native_body_budgeted_for_c3")
        self.assertEqual(store.logs[0][2]["role"],"B1_DETAIL")
        self.assertEqual(store.logs[0][2]["status"],"PREANSWER_BUDGETED")
        self.assertGreaterEqual(store.logs[0][2]["preanswer_seconds_available"],2.0)
        self.assertEqual(store.logs[0][2]["c3_reserved_seconds"],10.0)
        self.assertEqual(store.logs[0][2]["c3_reserve_source"],"FALLBACK_DEFAULT")
        self.assertEqual(store.logs[0][2]["minimum_role_slice_s"],2.0)

        # The same organ remains eligible after the outward answer; the
        # background caller omits valid_until and is not treated as pre-answer.
        with self.assertRaisesRegex(AssertionError,"source read reached"):
            cognition.offer("B1_DETAIL",{"event_id":"e1","source_ref":{}},
                            1,time.monotonic()+20)
        self.assertEqual(store.source_reads,2)

    def test_focal_reentry_is_not_limited_by_initial_preanswer_window(self):
        class LocalStore(DummyStore):
            def __init__(self):
                super().__init__([turn(),turn()])
                self.logs=[]
            def log(self,*args):
                self.logs.append(args)
            def read_source(self,ref):
                raise AssertionError("focal re-entry reached source read")
        class FakeRuntime:
            def __init__(self):
                self.cfg={"deadline_seconds":30,"observer_mode":"background"}
                self.store=LocalStore()
                self.cancel_event=threading.Event()
                self.session="s3"
        runtime=FakeRuntime()
        end=time.monotonic()+30
        with self.assertRaisesRegex(AssertionError,"focal re-entry reached"):
            Cognition(runtime).offer(
                "B1_DETAIL",{"event_id":"e3","source_ref":{}},1,end-18,
                valid_until=end,preanswer_budgeted=False)
        self.assertEqual(runtime.store.logs,[])

    def test_cognition_does_not_defer_with_owner_background_disabled(self):
        class LocalStore(DummyStore):
            def read_source(self,ref):
                raise AssertionError("native attempt was NOT deferred")
            def log(self,*args):
                raise AssertionError("unexpected observer deferral")
        class FakeRuntime:
            def __init__(self):
                self.cfg={"deadline_seconds":30,"observer_mode":"off"}
                self.store=LocalStore([turn(),turn()])
                self.cancel_event=threading.Event()
                self.session="s2"
        end=time.monotonic()+30
        with self.assertRaisesRegex(AssertionError,"NOT deferred"):
            Cognition(FakeRuntime()).offer(
                "B1_DETAIL",{"event_id":"e2","source_ref":{}},
                1,end-18,valid_until=end)

    def test_recovery_reserves_focal_selection_after_body_passes(self):
        d=budget.plan(100,130,100,recent=[turn(),turn()])
        self.assertTrue(d["recovery"])
        self.assertAlmostEqual(d["preanswer_end_monotonic"],120.0)
        self.assertAlmostEqual(d["body_preanswer_end_monotonic"],119.0)
        self.assertEqual(d["focal_reserved_seconds"],1.0)
        self.assertEqual(d["preanswer_seconds_available"],19.0)
        self.assertEqual(d["c3_reserved_seconds"],10.0)
        self.assertEqual(d["c3_reserve_source"],"FALLBACK_DEFAULT")
        self.assertEqual(d["minimum_role_slice_s"],2.0)

    def test_observer_deadline_caps_a_role_slice_without_releasing_c3_reserve(self):
        d=budget.plan(100,130,100,recent=[turn(),turn()],
                      observer_deadline=101.5)
        self.assertTrue(d["recovery"])
        self.assertAlmostEqual(d["preanswer_seconds_available"],1.5)
        self.assertEqual(d["focal_reserved_seconds"],1.0)
        self.assertEqual(d["c3_reserved_seconds"],10.0)
        self.assertTrue(d["postcommit_body_eligible"])
        self.assertEqual(d["minimum_role_slice_s"],2.0)

        exhausted=budget.plan(100,130,103.9,recent=[turn(),turn()],
                              observer_deadline=103.8)
        self.assertEqual(exhausted["preanswer_seconds_available"],0)
        self.assertTrue(exhausted["postcommit_body_eligible"])

    def test_final_without_positive_native_tokens_does_not_reset_recovery(self):
        rows=[turn("FINAL",generated=0,phase="stream"),turn(),turn()]
        d=budget.plan(100,130,100,recent=rows)
        self.assertTrue(d["recovery"])
        self.assertEqual(d["recent_success_streak"],0)

    def test_budget_telemetry_is_registered_without_store_source_changes(self):
        from v13 import store

        budget.register_store_telemetry()
        metrics = store.telemetry_metrics({
            "kind": "native_turn_budget_plan",
            "preanswer_seconds_available": 1.25,
            "focal_reserved_seconds": 1.0,
            "c3_reserved_seconds": 10.0,
            "recent_real_prefill_failures": 2,
            "minimum_role_slice_s": 2.0,
            "c3_reserve_estimate_seconds": 9.775,
            "c3_reserve_source": "RECENT_SUCCESS_MAX",
            "c3_reserve_capped": False,
            "status": "PREANSWER_BUDGETED",
        })
        self.assertEqual(metrics["kind"], "native_turn_budget_plan")
        self.assertEqual(metrics["preanswer_seconds_available"], 1.25)
        self.assertEqual(metrics["focal_reserved_seconds"], 1.0)
        self.assertEqual(metrics["c3_reserved_seconds"], 10.0)
        self.assertEqual(metrics["recent_real_prefill_failures"], 2)
        self.assertEqual(metrics["minimum_role_slice_s"], 2.0)
        self.assertEqual(metrics["c3_reserve_estimate_seconds"], 9.775)
        self.assertEqual(metrics["c3_reserve_source"], "RECENT_SUCCESS_MAX")
        self.assertFalse(metrics["c3_reserve_capped"])
        self.assertEqual(metrics["status"], "PREANSWER_BUDGETED")

    def test_bound_monotonic_inputs_and_conflicting_clock_rejected(self):
        with self.assertRaises(ValueError):
            budget.plan(100,float("nan"),102)
        with self.assertRaises(ValueError):
            budget.plan(100,99,100)
        with self.assertRaises(ValueError):
            budget.plan(100,130,100,observer_deadline=float("nan"))


    def test_recovery_falls_back_to_ten_seconds_without_recent_c3_success(self):
        d=budget.plan(100,130,100,recent=[turn(),turn()])
        self.assertTrue(d["recovery"])
        self.assertEqual(d["c3_reserve_source"],"FALLBACK_DEFAULT")
        self.assertEqual(d["c3_reserve_estimate_seconds"],10.0)
        self.assertEqual(d["c3_reserved_seconds"],10.0)
        self.assertEqual(d["preanswer_seconds_available"],19.0)

    def test_recovery_caps_slow_c3_estimate_to_preserve_two_body_slices(self):
        d=budget.plan(100,130,100,recent=[
            turn("FINAL",generated=8,phase="stream",duration_s=100),
            turn(),turn()])
        self.assertTrue(d["recovery"])
        self.assertTrue(d["c3_reserve_capped"])
        self.assertEqual(d["c3_reserved_seconds"],21.0)
        self.assertEqual(d["preanswer_seconds_available"],8.0)
        self.assertEqual(d["minimum_role_slice_s"],2.0)

    def test_short_turn_does_not_enter_recovery_without_two_body_slices(self):
        d=budget.plan(100,110,100,recent=[turn(),turn()])
        self.assertFalse(d["recovery"])
        self.assertEqual(d["reason"],"NORMAL_COGNITIVE_PREANSWER")
        self.assertAlmostEqual(d["preanswer_end_monotonic"],104.5)

    def test_invalid_c3_duration_is_ignored_for_reserve_estimation(self):
        rows=[
            turn(),
            turn("FINAL",generated=5,phase="stream",duration_s=float("nan")),
            turn(),
            turn("FINAL",generated=5,phase="stream",duration_s=0),
            turn("FINAL",generated=5,phase="stream",duration_s=10**1000)]
        d=budget.plan(100,130,100,recent=rows)
        self.assertTrue(d["recovery"])
        self.assertEqual(d["c3_reserve_source"],"FALLBACK_DEFAULT")
        self.assertEqual(d["c3_reserved_seconds"],10.0)


if __name__=="__main__":
    unittest.main()
