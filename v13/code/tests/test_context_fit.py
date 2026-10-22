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
        out,rep=F.fit('active','rules',vol,[],text,chars,10**6,sure=0)
        self.assertIs(out,vol);self.assertTrue(rep['fits']);self.assertFalse(rep['applied']);self.assertEqual(rep['steps'],{})

    def test_old_questions_go_first_oldest_first(self):
        vol,text=layers()
        full=chars(F.build('rules',vol,[],text))
        out,rep=F.fit('active','rules',vol,[],text,chars,full-500,sure=0)
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
        out,rep=F.fit('active','rules',vol,[],text,chars,1,sure=0)
        self.assertFalse(rep['fits'])
        self.assertEqual(list(rep['steps']),['TASK_DUPLICATE','OLD_QUESTIONS','DIGEST','QUOTES','HYPOTHESES','MEMORIES'])
        hyp=next(b for l,_,b in out if l=='HYPOTHESES')
        self.assertEqual(len(hyp),1);self.assertEqual(len(hyp[0]['verified_quotes']),1);self.assertTrue(hyp[0]['hypothesis']['summary'].startswith('h0'))
        self.assertIsNone(next((b for l,_,b in out if l=='COMPRESSED'),None))
        self.assertEqual(len(next(b for l,_,b in out if l=='ACTIVE_VIEW')),1)

    def test_shadow_reports_but_keeps_view(self):
        vol,text=layers()
        out,rep=F.fit('shadow','rules',vol,[],text,chars,chars(F.build('rules',vol,[],text))-500,sure=0)
        self.assertIs(out,vol);self.assertFalse(rep['applied']);self.assertTrue(rep['fits']);self.assertIn('OLD_QUESTIONS',rep['steps'])

    def test_off_does_nothing(self):
        vol,text=layers()
        out,rep=F.fit('off','rules',vol,[],text,chars,1,sure=0)
        self.assertIs(out,vol);self.assertIsNone(rep['fits'])

    def test_task_request_kept_when_it_is_not_the_current_message(self):
        vol,text=layers(questions=0)
        vol[-1][2]['task_request']['exact_request']='a pinned operator task'
        out,rep=F.fit('active','rules',vol,[],text,chars,chars(F.build('rules',vol,[],text))-10,sure=0)
        self.assertEqual(out[-1][2]['task_request']['exact_request'],'a pinned operator task')
        self.assertNotIn('TASK_DUPLICATE',rep['steps'])

    def test_quick_path_skips_native_count(self):
        calls=[]
        def count(m):calls.append(1);return 10**9
        vol,text=layers(questions=0,hyps=1,quotes=1)
        out,rep=F.fit('active','r',vol,[],text,count,10**4)
        self.assertTrue(rep['quick']);self.assertEqual(calls,[])

    def test_counter_falls_back_to_estimate(self):
        import threading
        class R:
            def prompt_tokens(self,m,c,d):raise OSError('down')
        count,how=F.counter(R(),threading.Event(),0)
        self.assertEqual(how,'EXACT');self.assertEqual(count([{'role':'user','content':'x'*30}]),F.estimate([{'role':'user','content':'x'*30}]))
        self.assertEqual(F.counter(object(),threading.Event(),0)[1],'ESTIMATE')

    def test_budget_matches_runner_rule(self):
        self.assertEqual(F.budget({'context_tokens':2048,'answer_tokens':256}),2048-256-16)


if __name__=='__main__':unittest.main()
