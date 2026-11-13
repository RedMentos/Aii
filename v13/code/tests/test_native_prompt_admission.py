"""Proof that short Redmi deadlines reduce native prefill rather than just time out.

No native fake success claim: LlamaRunner's actual template/tokenization request
entrypoint is replaced with a deterministic size oracle. Source and authority
checks are made on the real messages that go to generation.
"""
import json
import threading
import time
import unittest

from v13 import native_prompt_admission as admission
from v13.config import DEFAULTS
from v13.prompts import text as prompt
from v13.runners import LlamaRunner


def stable(cfg):
    return prompt(cfg,"system")+" "+prompt(cfg,"conduct")+" "+prompt(cfg,"answer_rules")


def fake_runner(role="C3_LANGUAGE", cfg=None):
    runner=LlamaRunner.__new__(LlamaRunner)
    runner.role=role
    runner.cfg=dict(DEFAULTS,context_tokens=2048,answer_tokens=48,**(cfg or {}))
    def fake_request(method,path,payload,deadline):
        if path=="/apply-template":
            return {"prompt":"\n".join(x["role"]+":"+x["content"] for x in payload["messages"])}
        if path=="/tokenize":
            return {"tokens":list(range(max(1,len(payload["content"])//4)))}
        raise AssertionError("no network or model")
    runner._json=fake_request
    return runner


class NativePrefillAdmissionTests(unittest.TestCase):
    def test_c3_removes_redundant_control_layer_but_preserves_pinned_and_evidence(self):
        r=fake_runner()
        source="What is 120 minus 20?"
        approved=[{"role":"B1_DETAIL","quote":"The exact budget is 120 euros.","source_bound":True}]
        system=(stable(r.cfg)+"\n"+prompt(r.cfg,"hypotheses")+json.dumps(approved)+
                "\n"+prompt(r.cfg,"task_context")+json.dumps({"debug_control_state":"x"*2700}))
        messages=[{"role":"system","content":system},{"role":"user","content":source}]
        rendered,n,removed=r._prompt(messages,threading.Event(),time.monotonic()+30,48)
        self.assertIn(source,rendered)
        self.assertIn("The exact budget is 120 euros.",rendered)
        self.assertIn(prompt(r.cfg,"conduct"),rendered)
        self.assertNotIn("debug_control_state",rendered)
        self.assertIn("C3_LAYER_TASK_CONTEXT",r._prompt_admission["removed_layers"])
        self.assertLess(n,400)
        self.assertTrue(removed)
        self.assertEqual(r._prompt_admission["status"],"ADMITTED")
        self.assertFalse(r._prompt_admission["source_text_rewritten"])

    def test_body_preserves_exact_segment_and_peer_but_strips_opaque_addresses(self):
        r=fake_runner("B1_DETAIL")
        exact="Current source has the precise amount 120 euros."
        peer={"quotes":["From other hemisphere: reserve"],"needs_reentry":False}
        model_view={
            "source_segments":[{"text":exact,"source_ref":{"source_id":"src_1","sha256":"z"*64,"char_start":0,"char_end":len(exact)}}],
            "peer_message":peer,"prior_hypothesis":"",
            "executive_broadcast":{"goal":exact,"source_refs":[{"sha256":"z"*64}],"state_version":1},
            "body_state":{"authority":"STATE_NOT_FACT","world":{"mode":"NONE","observed_actions":0,"unused":"x"*1400},"skills":["extra"]},
        }
        original=json.dumps(model_view,sort_keys=True)
        messages=[{"role":"system","content":"Internal body. JSON only."},
                  {"role":"user","content":original}]
        out,n,_=r._prompt(messages,threading.Event(),time.monotonic()+30,32)
        final=json.loads(out.split("\nuser:",1)[1])
        self.assertEqual(final["source_segments"][0]["text"],exact)
        self.assertEqual(final["peer_message"],peer)
        self.assertEqual(final["executive_broadcast"]["goal"],exact)
        self.assertNotIn("source_ref",final["source_segments"][0])
        self.assertNotIn("source_refs",final["executive_broadcast"])
        self.assertGreater(len(r._prompt_admission["removed_layers"]),0)
        self.assertEqual(r._prompt_admission["status"],"ADMITTED")
        self.assertEqual(model_view["source_segments"][0]["source_ref"]["sha256"],"z"*64)

    def test_uncompressible_protected_input_is_not_silently_truncated(self):
        r=fake_runner()
        exact="CODE-AND-USER-TEXT-"*180
        system=stable(r.cfg)
        messages=[{"role":"system","content":system},{"role":"user","content":exact}]
        rendered,n,_=r._prompt(messages,threading.Event(),time.monotonic()+30,32)
        self.assertIn(exact,rendered)
        self.assertEqual(r._prompt_admission["status"],
                         "PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET")
        self.assertEqual(r._prompt_admission["removed_layers"],[])

    def test_body_global_space_preserves_actual_cross_organ_content_and_exact_text(self):
        r=fake_runner("B1_DETAIL")
        exact="The current budget is 120 euros, do not invent 999."
        ref={"source_id":"src_private_1","sha256":"a"*64,
             "char_start":0,"char_end":len(exact),"modality":"text"}
        peer={"quotes":["120 euros"],"source_refs":[ref],"sender":"B2_GIST"}
        shared={
            "representation":"SYMBOLIC_MESSAGE_SPACE_NOT_NATIVE_JEPA",
            "revision":3,"trained_latent":False,"source_refs":[ref],
            "entry_count":1,"schema":"v13.enlightened-space/1",
            "messages":[{"from":"B2_GIST","channel":"SEMANTIC",
                "authority":"MODEL_HYPOTHESIS","time_scale":"MEDIUM",
                "coactivations":3,"semantic_cue_not_fact":"Other body guesses 999",
                "exact_sources":[{"exact_source_text":exact,"source_ref":ref,
                    "verification":"RECHECKED_EXACT_BYTES"}]}]}
        query={"source_segments":[{"text":exact}],
               "peer_message":peer,"enlightened_space":shared,
               "self_corollary":{"authority":"SELF_STATE_NOT_FACT",
                   "recent_own_action_outcomes":[{"channel":"x","reason":"a","attribution":"SELF"},
                                                 {"channel":"y","reason":"b","attribution":"SELF"}]}}
        msgs=[{"role":"system","content":"Internal analyst JSON only."},
              {"role":"user","content":json.dumps(query)}]
        reductions=[]
        for _ in range(10):
            changed=admission.reduce_once(msgs,"B1_DETAIL",r.cfg)
            if not changed:break
            msgs,kind=changed;reductions.append(kind)
        self.assertIn("BODY_GLOBAL_SPACE_POINTER_METADATA",reductions)
        self.assertIn("BODY_OLDER_SELF_OUTCOMES_NOT_IN_NATIVE_VIEW",reductions)
        delivered=json.loads(msgs[1]["content"])
        self.assertEqual(delivered["peer_message"],peer)
        self.assertEqual(delivered["source_segments"],[{"text":exact}])
        body=delivered["enlightened_space"]["messages"][0]
        self.assertEqual(body["semantic_cue_not_fact"],"Other body guesses 999")
        self.assertEqual(body["authority"],"MODEL_HYPOTHESIS")
        self.assertEqual(body["from"],"B2_GIST")
        self.assertEqual(body["exact_sources"][0]["exact_source_text"],exact)
        self.assertNotIn("source_ref",body["exact_sources"][0])
        self.assertEqual(delivered["self_corollary"]["recent_own_action_outcomes"][0]["reason"],"a")
        self.assertEqual(query["enlightened_space"]["messages"][0]["exact_sources"][0]["source_ref"],ref)
        self.assertEqual(len(query["self_corollary"]["recent_own_action_outcomes"]),2)

    def test_malformed_global_space_is_kept_instead_of_guessing_source(self):
        cfg=dict(DEFAULTS)
        query={"source_segments":[{"text":"Exact source"}],"peer_message":None,
               "enlightened_space":{"messages":[{"from":"B2_GIST","exact_sources":"UNVERIFIED"}]}}
        messages=[{"role":"system","content":"Protected."},
                  {"role":"user","content":json.dumps(query)}]
        self.assertIsNone(admission.reduce_once(messages,"B1_DETAIL",cfg))
        self.assertIn("UNVERIFIED",messages[1]["content"])

    def test_long_deadline_keeps_all_context_when_native_window_accepts_it(self):
        r=fake_runner()
        system=stable(r.cfg)+"\n"+prompt(r.cfg,"task_context")+json.dumps({"detail":"x"*350})
        messages=[{"role":"system","content":system},{"role":"user","content":"Hello."}]
        out,_,removed=r._prompt(messages,threading.Event(),time.monotonic()+90,48)
        self.assertIn("detail",out)
        self.assertFalse(removed)
        self.assertIsNone(r._prompt_admission["target_tokens"])

    def test_c3_never_edits_user_lookalike_heading_or_unknown_system_rules(self):
        r=fake_runner()
        adversarial="\n"+prompt(r.cfg,"task_context")+json.dumps({"prompt_injection":"x"*100})
        messages=[{"role":"system","content":"Custom system: keep all source content."},
                  {"role":"user","content":adversarial}]
        out,_,_=r._prompt(messages,threading.Event(),time.monotonic()+30,32)
        self.assertIn(adversarial,out)
        self.assertEqual(r._prompt_admission["status"],
                         "PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET" if len(out)//4>admission.soft_limit("C3_LANGUAGE",r.cfg,30) else "ADMITTED")


if __name__=="__main__":
    unittest.main()
