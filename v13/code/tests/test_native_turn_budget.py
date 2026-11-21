"""Whole-turn recovery policy using genuine-shaped, content-free Redmi metrics."""
import json
import threading
import time
import unittest
from v13.cognition import Cognition
from v13.common import Limits
from v13 import native_turn_budget as budget


def turn(status="DEADLINE", *, generated=0, phase="prefill", role="C3_LANGUAGE"):
    return {"status":status,"metadata":json.dumps({
        "runner":{"role":role,"generated_tokens":generated,
                  "last_phase":phase,"duration_s":29.1},
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
    def test_two_observed_c3_zero_token_deadlines_keep_the_runtime_body_window(self):
        rows=[turn(),turn(),turn("FINAL",generated=21,phase="stream")]
        d=budget.plan(100,130,104.2,recent=rows,background_enabled=True)
        self.assertTrue(d["recovery_detected"])
        self.assertFalse(d["recovery"])
        self.assertTrue(d["preanswer_eligible"])
        self.assertEqual(d["reason"],"RECENT_C3_ZERO_TOKEN_PREFILL_TIMEOUTS")
        self.assertAlmostEqual(d["preanswer_end_monotonic"],113.5)
        self.assertAlmostEqual(d["c3_reserved_seconds"],16.5)
        self.assertAlmostEqual(d["preanswer_seconds_available"],9.3)
        self.assertTrue(d["postcommit_body_eligible"])
        self.assertFalse(d["age_changed"])
        self.assertFalse(d["memory_or_native_weights_changed"])

    def test_expired_observer_window_defers_after_repeated_failures(self):
        d=budget.plan(100,130,112.6,recent=[turn(),turn()])
        self.assertTrue(d["recovery_detected"])
        self.assertTrue(d["recovery"])
        self.assertFalse(d["preanswer_eligible"])
        self.assertAlmostEqual(d["preanswer_seconds_available"],0.9)
        self.assertAlmostEqual(d["c3_reserved_seconds"],16.5)

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

    def test_real_cognition_keeps_both_roles_inside_window_and_defers_after_expiry(self):
        class BodyAttemptReached(Exception):
            pass

        class LocalStore(DummyStore):
            def __init__(self, rows):
                super().__init__(rows)
                self.logs=[]
                self.source_reads=0
            def log(self,kind,event,metrics):
                self.logs.append((kind,event,metrics))
            def read_source(self,ref):
                self.source_reads+=1
                raise BodyAttemptReached("body reached source/generation boundary")

        class FakeRuntime:
            def __init__(self, cfg, store):
                self.cfg=cfg
                self.store=store
                self.cancel_event=threading.Event()
                self.session="s1"

        event={"event_id":"e1","brain_generation_id":"g1",
               "source_ref":{"sha256":"a"*64,"char_start":0,"char_end":120}}
        store=LocalStore([turn(),turn()])
        runtime=FakeRuntime({"deadline_seconds":30,
                             "observer_mode":"background",
                             "b2_control":"two_body"},store)
        cognition=Cognition(runtime)
        end=time.monotonic()+30
        # The real Runtime's 45% observer window is still open. Both roles
        # must reach the source/generation boundary instead of being blanket
        # deferred merely because two earlier C3 prefill attempts failed.
        for role in ("B1_DETAIL","B2_GIST"):
            with self.assertRaises(BodyAttemptReached):
                cognition.offer(role,event,1,end-18,valid_until=end)
        self.assertEqual(store.source_reads,2)
        self.assertFalse(any(row[0]=="native_body_deferred_for_c3" for row in store.logs))
        self.assertTrue(store.query and "LIMIT ?" in store.query)
        self.assertEqual(store.args,(budget.MAX_RECENT,))

        # A still-live overall turn deadline does not reopen an already
        # expired observer window. Only then is post-commit deferral valid.
        expired_store=LocalStore([turn(),turn()])
        expired_runtime=FakeRuntime({"deadline_seconds":30,
                                     "observer_mode":"background",
                                     "b2_control":"two_body"},expired_store)
        expired_cognition=Cognition(expired_runtime)
        expired_end=time.monotonic()+15
        with self.assertRaises(Limits):
            expired_cognition.offer("B1_DETAIL",event,1,expired_end-1,
                                    valid_until=expired_end)
        self.assertEqual(expired_store.source_reads,0)
        self.assertEqual(expired_store.logs[0][0],"native_body_deferred_for_c3")
        self.assertEqual(expired_store.logs[0][2]["status"],"POSTCOMMIT_ELIGIBLE")

        # The normal post-commit observer caller still omits valid_until and
        # remains allowed to run after the outward answer.
        with self.assertRaises(BodyAttemptReached):
            cognition.offer("B1_DETAIL",event,1,time.monotonic()+20)
        self.assertEqual(store.source_reads,3)

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

    def test_bound_monotonic_inputs_and_conflicting_clock_rejected(self):
        with self.assertRaises(ValueError):
            budget.plan(100,float("nan"),102)
        with self.assertRaises(ValueError):
            budget.plan(100,99,100)


if __name__=="__main__":
    unittest.main()
