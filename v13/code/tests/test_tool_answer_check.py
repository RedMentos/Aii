"""WP-DS3b: cfg tool_answer_check (off|shadow|note), fixed cross-check of the answer against an executed list_arith recipe.
Default off must leave the turn unchanged. No models."""
import tempfile,unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import toolstep as T
from v13.config import DEFAULTS,validate
from v13.agi import listarith as L

ROOT=Path(__file__).resolve().parents[1]
CMP='Monthly rainfall in millimetres: Cork 300, Lyon 700, Graz 450. Which city had the most rain, and how many millimetres more than the city with the least?'
SUM='Expense report. Items: cables 20 euros, snacks 30 euros. Summary line at the bottom: "Total: 60 euros." Is the summary line correct? Give the correct total.'
def args(text,op,vals):return {'operation':op,'text':text,'values':L.encode([{'name':n,'number':v} for n,v in vals])}
CA=args(CMP,'difference_max_min',[('Cork',300),('Lyon',700),('Graz',450)])
SA=args(SUM,'total',[('cables',20),('snacks',30),('Total',60)])  # a read summary line is dropped like in compute()

class Check(unittest.TestCase):
    def test_right_city_and_value(self):
        self.assertEqual(L.answer_check(CA,400,'Lyon had the most rain with 700 mm. That is 400 mm more than Cork.'),(True,'ok'))
    def test_wrong_city_with_right_number(self):
        self.assertEqual(L.answer_check(CA,400,'Graz had the most rain. The difference is 400 mm.'),(False,'wrong_largest'))
    def test_missing_value(self):
        self.assertEqual(L.answer_check(CA,400,'Lyon had the most rain, 250 mm more.'),(False,'value_missing'))
    def test_stated_wrong_total_must_be_called_wrong(self):
        self.assertEqual(L.answer_check(SA,50,'The correct total is 50 euros.'),(False,'stated_number_not_flagged'))
        self.assertEqual(L.answer_check(SA,50,'No, the total is 50 euros, not 60.'),(True,'ok'))
    def test_note_names_recipe_and_value(self):
        self.assertEqual(L.check_note(CA,400),'Check: this answer does not match the exact local calculation (largest Lyon 700 - smallest Cork 300 = 400). Treat the answer above as unsure.')

class Config(unittest.TestCase):
    def test_default_off_and_validation(self):
        self.assertEqual(DEFAULTS['tool_answer_check'],'off')
        for ok in ('off','shadow','note'):validate(dict(DEFAULTS,tool_answer_check=ok))
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,tool_answer_check='abstain'))
    def test_chain_link_is_live(self):
        from scripts.integrated_candidates import INTEGRATED,integrated_sources
        self.assertIn('tool_answer_check',INTEGRATED)
        live=(ROOT/'v13/runtime.py').read_text();self.assertEqual(integrated_sources()['v13/runtime.py'],live)
        self.assertIn("output+=toolctl.ToolStep(self).check_answer(e,tool_result,output,mid)",live)

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.e=self.r.store.event(self.r.session,CMP);self.ts=T.ToolStep(self.r)
        self.res={'tool':'list_arith','args':CA,'result':400,'tx':'t1','action_tx':None}
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def run_check(self,mode,answer):
        self.r.cfg['tool_answer_check']=mode;mid=self.r.store.message(self.r.session,self.e['event_id'],'assistant')
        self.r.store.append_message(mid,answer);added=self.ts.check_answer(self.e,self.res,answer,mid)
        text=self.r.store.one('SELECT text FROM messages WHERE id=?',(mid,))['text']
        return added,text,self.r.store.state(T.CHECK_KEY)[0]
    def test_off_changes_nothing(self):
        wrong='Graz had the most rain. The difference is 400 mm.'
        self.assertEqual(self.run_check('off',wrong),('',wrong,None))
    def test_off_is_the_default(self):
        self.assertEqual(self.r.cfg.get('tool_answer_check'),'off')
    def test_shadow_counts_without_touching_the_answer(self):
        wrong='Graz had the most rain. The difference is 400 mm.'
        added,text,st=self.run_check('shadow',wrong)
        self.assertEqual((added,text),('',wrong));self.assertEqual(st,{'checked':1,'failed':1,'noted':0,'reasons':{'wrong_largest':1}})
    def test_note_appends_only_on_failure(self):
        right='Lyon had the most rain. The difference is 400 mm.'
        self.assertEqual(self.run_check('note',right)[:2],('',right))
        wrong='Graz had the most rain. The difference is 400 mm.'
        added,text,st=self.run_check('note',wrong)
        self.assertEqual(added,' '+L.check_note(CA,400));self.assertTrue(text.endswith(added));self.assertEqual((st['checked'],st['noted']),(2,1))
    def test_other_tools_and_missing_results_are_ignored(self):
        self.r.cfg['tool_answer_check']='note'
        self.assertEqual(self.ts.check_answer(self.e,dict(self.res,tool='eligibility'),'x',None),'')
        self.assertEqual(self.ts.check_answer(self.e,dict(self.res,result=None),'x',None),'')
        self.assertEqual(self.ts.check_answer(self.e,None,'x',None),'')

if __name__=='__main__':unittest.main()
