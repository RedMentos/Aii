import unittest

from v13 import context_fit as F
from v13.config import DEFAULTS,validate


def layers(questions=8,quotes=3,hyps=3,digest=0,memories=0,text='Expense report. Items: postage 55 euros. Give the total.'):
    vol=[]
    if memories:vol.append(('ACTIVE_VIEW','\nMemories: ',[{'value':'m%d '%i+'x'*80} for i in range(memories)]))
    vol.append(('HYPOTHESES','\nInternal hypotheses: ',[{'role':'B1_DETAIL','hypothesis':{'summary':'h%d '%i+'y'*120},
        'verified_quotes':[{'text':'q%d-%d '%(i,j)+'z'*60} for j in range(quotes)]} for i in range(hyps)]))
    if digest:vol.append(('COMPRESSED','\nDigest: ',['d%d '%i+'w'*80 for i in range(digest)]))
    vol.append(('LATENT_STATE','\nTask context: ',{'task_request':{'exact_request':text[:320],'origin':'SOURCE_USER_REQUEST'},
        'unresolved_observer_hypotheses':[{'source_request':'old task %d '%i+'v'*200,'uncertainty':'u'*100} for i in range(questions)]}))
    return vol,text

def chars(messages):return sum(len(m['content']) for m in messages)


class ContextFitTests(unittest.TestCase):
    def test_default_is_active_and_validated(self):
        self.assertEqual(DEFAULTS['context_fit'],'active')
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,context_fit='maybe'))

    def test_fitting_prompt_is_untouched(self):
        vol,text=layers(questions=1)
        out,rep=F.fit('active','rules',vol,[],text,chars,10**6)
        self.assertIs(out,vol);self.assertTrue(rep['fits']);self.assertFalse(rep['applied']);self.assertEqual(rep['steps'],{})

    def test_old_questions_go_first_oldest_first(self):
        vol,text=layers()
        full=chars(F.build('rules',vol,[],text))
        out,rep=F.fit('active','rules',vol,[],text,chars,full-500)
        self.assertTrue(rep['fits'] and rep['applied'])
        self.assertEqual(set(rep['steps']),{'TASK_DUPLICATE','OLD_QUESTIONS'})
        qs=out[-1][2]['unresolved_observer_hypotheses']
        self.assertTrue(qs and qs[-1]['source_request'].startswith('old task 7'))  # newest kept
        self.assertFalse(any(q['source_request'].startswith('old task 0') for q in qs))
        self.assertEqual(out[-1][2]['task_request']['exact_request'],F.TASK_POINTER)
        # hypotheses untouched, the input layers were not mutated
        self.assertEqual(out[0][2],vol[0][2]);self.assertEqual(len(vol[-1][2]['unresolved_observer_hypotheses']),8)
        self.assertNotEqual(vol[-1][2]['task_request']['exact_request'],F.TASK_POINTER)

    def test_order_then_quotes_then_hypotheses_one_stays(self):
        vol,text=layers(digest=3,memories=2)
        out,rep=F.fit('active','rules',vol,[],text,chars,1)
        self.assertFalse(rep['fits'])
        self.assertEqual(list(rep['steps']),['TASK_DUPLICATE','OLD_QUESTIONS','DIGEST','QUOTES','HYPOTHESES','MEMORIES'])
        hyp=next(b for l,_,b in out if l=='HYPOTHESES')
        self.assertEqual(len(hyp),1);self.assertEqual(len(hyp[0]['verified_quotes']),1);self.assertTrue(hyp[0]['hypothesis']['summary'].startswith('h0'))
        self.assertIsNone(next((b for l,_,b in out if l=='COMPRESSED'),None))
        self.assertEqual(len(next(b for l,_,b in out if l=='ACTIVE_VIEW')),1)

    def test_shadow_reports_but_keeps_view(self):
        vol,text=layers()
        out,rep=F.fit('shadow','rules',vol,[],text,chars,chars(F.build('rules',vol,[],text))-500)
        self.assertIs(out,vol);self.assertFalse(rep['applied']);self.assertTrue(rep['fits']);self.assertIn('OLD_QUESTIONS',rep['steps'])

    def test_off_does_nothing(self):
        vol,text=layers()
        out,rep=F.fit('off','rules',vol,[],text,chars,1)
        self.assertIs(out,vol);self.assertIsNone(rep['fits'])

    def test_task_request_kept_when_it_is_not_the_current_message(self):
        vol,text=layers(questions=0)
        vol[-1][2]['task_request']['exact_request']='a pinned operator task'
        out,rep=F.fit('active','rules',vol,[],text,chars,chars(F.build('rules',vol,[],text))-10)
        self.assertEqual(out[-1][2]['task_request']['exact_request'],'a pinned operator task')
        self.assertNotIn('TASK_DUPLICATE',rep['steps'])

    def test_quick_path_skips_native_count_only_under_byte_bound(self):
        calls=[]
        def count(m):calls.append(1);return 10**9
        vol,text=layers(questions=0,hyps=1,quotes=1)
        out,rep=F.fit('active','r',vol,[],text,count,10**4)
        self.assertTrue(rep['quick']);self.assertEqual(rep['count_source'],'UPPER_BOUND');self.assertEqual(calls,[])

    def test_dense_unicode_is_counted_not_assumed(self):
        """Review 2026-10-26: 100 chars may tokenize to >100 tokens; the old 1.5 chars/token shortcut skipped the count."""
        text='\U0001F600'*100  # 100 chars, 400 UTF-8 bytes
        calls=[]
        def dense(m):calls.append(1);return sum(len(x['content']) for x in m)*2  # a tokenizer denser than 1 token/char
        out,rep=F.fit('active','',[],[],text,dense,100)
        self.assertTrue(calls);self.assertNotIn('quick',rep);self.assertFalse(rep['fits'])
        self.assertGreater(F.upper_bound(F.build('',[],[],text)),100)
        # byte bound really bounds: never below chars, counts each emoji as 4
        self.assertGreaterEqual(F.upper_bound([{'role':'user','content':text}]),400)

    def test_count_provenance_measured_vs_estimated(self):
        import threading
        class Ok:
            def prompt_tokens(self,m,c,d):return sum(len(x['content']) for x in m)
        class Flaky:
            n=0
            def prompt_tokens(self,m,c,d):
                Flaky.n+=1
                if Flaky.n>1:raise OSError('down')
                return sum(len(x['content']) for x in m)
        vol,text=layers()
        lim=sum(len(x['content']) for x in F.build('rules',vol,[],text))-500
        for runner,want in ((Ok(),'MEASURED'),(Flaky(),'ESTIMATED')):
            count,how=F.counter(runner,threading.Event(),0)
            self.assertEqual(how,'EXACT')
            out,rep=F.fit('shadow','rules',vol,[],text,count,lim)
            self.assertEqual(rep['count_source'],want,rep)
        count,how=F.counter(object(),threading.Event(),0)
        self.assertEqual(how,'ESTIMATE');count([{'role':'user','content':'x'}]);self.assertEqual(count.sources,['ESTIMATE'])

    def test_exact_count_optin_is_validated_and_legacy_default_unchanged(self):
        self.assertEqual(DEFAULTS['context_fit_exact_count'],0)
        validate(dict(DEFAULTS,context_fit_exact_count=1))
        with self.assertRaises(ValueError):
            validate(dict(DEFAULTS,context_fit_exact_count=2))

    def test_exact_count_optin_disables_quick_accept_even_under_byte_bound(self):
        calls=[]
        def native(messages):
            calls.append(messages)
            return 100000
        vol,text=layers(questions=0,hyps=1,quotes=1)
        _,legacy=F.fit('active','r',vol,[],text,native,10000)
        self.assertTrue(legacy['quick'])
        self.assertEqual(calls,[])
        _,strict=F.fit('active','r',vol,[],text,native,10000,force_exact=True)
        self.assertTrue(calls)
        self.assertNotIn('quick',strict)
        self.assertFalse(strict['fits'])

    def test_exact_count_optin_refuses_unavailable_native_counter(self):
        import threading
        with self.assertRaisesRegex(ValueError,'EXACT_TOKEN_COUNTER_UNAVAILABLE'):
            F.counter(object(),threading.Event(),0,strict=True)
        class Broken:
            def prompt_tokens(self,m,c,d):raise OSError('native tokenizer unavailable')
        count,how=F.counter(Broken(),threading.Event(),0,strict=True)
        self.assertEqual(how,'EXACT')
        with self.assertRaises(OSError):
            count([{'role':'user','content':'example'}])
        self.assertEqual(count.sources,[])

    def test_legacy_counter_fallback_stays_labelled_estimate(self):
        import threading
        class Broken:
            def prompt_tokens(self,m,c,d):raise OSError('native tokenizer unavailable')
        count,_=F.counter(Broken(),threading.Event(),0)
        self.assertGreater(count([{'role':'user','content':'example'}]),0)
        self.assertEqual(count.sources,['ESTIMATE'])

    def test_operator_can_persist_exact_count_optin_without_age_change(self):
        import tempfile
        from pathlib import Path
        from v13.runtime import Runtime
        from v13.operator import Operator
        with tempfile.TemporaryDirectory() as td:
            first=Runtime(Path(td))
            try:
                self.assertEqual(first.cfg['context_fit_exact_count'],0)
                self.assertIn('context_fit_exact_count = 1',
                              Operator(first).run(':budget context_fit_exact_count 1'))
                self.assertEqual(first.cfg['system_stage'],0)
                self.assertEqual(first.cfg['context_fit_exact_count'],1)
            finally:
                first.close()
            second=Runtime(Path(td))
            try:
                self.assertEqual(second.cfg['context_fit_exact_count'],1)
                self.assertEqual(second.cfg['system_stage'],0)
                Operator(second).run(':budget context_fit_exact_count 0')
            finally:
                second.close()

    def test_final_planner_view_cannot_escape_exact_budget(self):
        vol,text=layers(questions=0,hyps=1,quotes=1)
        calls=[]
        def native(messages):
            calls.append(messages)
            return 9000 if messages[0]["content"].startswith("planner-expanded") else 100
        _,fitted=F.fit("active","rules",vol,[],text,native,200,force_exact=True)
        self.assertTrue(fitted["fits"])
        final=[{"role":"system","content":"planner-expanded with additional volatile state"},
               {"role":"user","content":text}]
        with self.assertRaisesRegex(ValueError,"EXACT_FINAL_CONTEXT_OVERFLOW"):
            F.require_final_exact(final,native,200)
        self.assertEqual(len(calls),2)

    def test_final_exact_refuses_counter_error_and_invalid_counts(self):
        messages=[{"role":"user","content":"test"}]
        def unavailable(_):raise OSError("native tokenizer disconnected")
        with self.assertRaises(OSError):
            F.require_final_exact(messages,unavailable,100)
        for bad in (-1,float("nan"),"5",True):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError,"EXACT_FINAL_COUNT_INVALID"):
                    F.require_final_exact(messages,lambda _:bad,100)
        self.assertEqual(F.require_final_exact(messages,lambda _:100,100),100)

    def test_exact_mode_rejects_unverified_causal_decoder_budget(self):
        self.assertIsNone(F.require_native_count_compatible("C3_LANGUAGE","server"))
        self.assertIsNone(F.require_native_count_compatible("B1_DETAIL","same_causal_zero"))
        for mode in ("same_causal_zero","same_causal"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError,"EXACT_COUNT_CAUSAL_MODE_UNVERIFIED"):
                    F.require_native_count_compatible("C3_LANGUAGE",mode)

    def test_budget_matches_runner_rule(self):
        self.assertEqual(F.budget({'context_tokens':2048,'answer_tokens':256}),2048-256-16)


if __name__=='__main__':unittest.main()
