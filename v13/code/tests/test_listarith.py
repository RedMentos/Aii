"""R4 part 6: list_arith tool (BOOT wording rule, typed values, number guard, recipe) and its live proposal. No models."""
import json,tempfile,unittest
from pathlib import Path
from v13.runtime import Runtime
from v13 import toolstep as T
from v13.agi import hub,listarith as L

RAIN='Monthly rainfall in millimetres: Lyon 644, Brno 255, Bremen 636. Which city had the most rain, and how many millimetres more than the city with the least?'
VALUES=[{'name':'Lyon','number':644},{'name':'Brno','number':255},{'name':'Bremen','number':636}]

class FakeC3:
    def __init__(self,values):self.values=values;self.calls=[]
    def generate(self,messages,cancel,deadline,max_tokens=None,schema=None,**kw):
        self.calls.append(schema);yield json.dumps({'values':self.values})

class Recipe(unittest.TestCase):
    def test_rule_recipe_guard_and_codec(self):
        self.assertEqual(L.operation(RAIN),'difference_max_min');self.assertEqual(L.operation('Give the correct total.'),'total')
        self.assertIsNone(L.operation('Which note is the most recent one?'))
        self.assertEqual(L.compute('difference_max_min',VALUES,RAIN),(389,'largest Lyon 644 - smallest Brno 255'))
        self.assertEqual(L.decode(L.encode(VALUES)),VALUES);self.assertEqual(L.tool('total',RAIN,L.encode(VALUES)),1535)
        with self.assertRaises(ValueError):L.compute('total',VALUES+[{'name':'Pisa','number':12}],RAIN)  # invented value
        with self.assertRaises(ValueError):L.compute('total',VALUES[:1],RAIN)
        self.assertIsNone(L.label({'operation':'total','text':'a 1, b 2.','values':'a=1\nb=3'}))
    def test_rule_r3_question_only_and_r4_tasks_unchanged(self):
        import sys;sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'));import utility_bench2 as U2,r4_rule_r3 as R
        for seed in (7,11,13,17,19,23):
            for fid,text,_,_ in U2.tasks(seed):self.assertEqual(L.operation(text),R.Q.r0(text),fid)
        for row in R.family_e()+R.Q.family_d():self.assertEqual(L.operation(row['text']),R.r3(row['text']))
        self.assertIsNone(L.operation('Items: a 12 euros, b 30 euros. Summary line: "Total: 52 euros." Which item is the smallest?'))
        self.assertIsNone(L.operation('Points: Mira 4, Omar 9. What is the total number of entries?'))
    def test_stated_total_line_is_not_an_item(self):
        text='Items: coffee beans 49 euros, cleaning service 33 euros, a projector 71 euros. Summary line: "Total: 173 euros." Give the correct total.'
        read=[{'name':'coffee beans','number':49},{'name':'cleaning service','number':33},{'name':'projector','number':71},{'name':'total','number':173}]
        self.assertEqual(L.compute('total',read,text)[0],153);self.assertEqual(L.compute('difference_max_min',read,text)[0],38)
        self.assertEqual(L.compute('total',[{'name':'total hours','number':49},{'name':'Grand Total','number':33},{'name':'b','number':71}],text)[0],120)
        with self.assertRaises(ValueError):L.compute('total',[{'name':'a','number':49},{'name':'Sum','number':173}],text)

class Live(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.c3=FakeC3(VALUES);self.r.pool.get=lambda role:self.c3
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def test_disabled_tool_costs_no_model_call(self):
        e=self.r.store.event(self.r.session,RAIN);self.assertIsNone(T.ToolStep(self.r).plan(e,RAIN));self.assertEqual(self.c3.calls,[])
    def test_enabled_tool_proposes_shadows_and_layers_recipe(self):
        g=hub(self.r);g.tools.enable('list_arith');e=self.r.store.event(self.r.session,RAIN);ts=T.ToolStep(self.r)
        p=ts.plan(e,RAIN);self.assertEqual(p['tool'],'list_arith');self.assertEqual(p['proposer'],T.LIST_PROPOSER);self.assertNotEqual(p['status'],'APPROVED')  # Age 0
        self.assertEqual(self.c3.calls,[L.READ_SCHEMA])
        sh=ts.shadow(e,p);self.assertEqual(sh['result'],389);self.assertTrue(ts.compare(e,sh,'Lyon, 389 mm more.'))
        g.tools._policy=lambda spec,origin,args,confirmed=False:('APPROVED','POLICY',[])
        res=ts.execute(e,p);self.assertEqual(res['result'],389)
        lay=ts.layer(res);self.assertEqual((lay['exact_result'],lay['recipe']),(389,'largest Lyon 644 - smallest Brno 255 = 389'));self.assertNotIn('input',lay)
    def test_guard_refuses_invented_value_before_proposing(self):
        hub(self.r).tools.enable('list_arith');self.c3.values=VALUES[:2]+[{'name':'Bremen','number':637}]
        e=self.r.store.event(self.r.session,RAIN);self.assertIsNone(T.ToolStep(self.r).plan(e,RAIN))
        self.assertIsNotNone(self.r.store.one("SELECT id FROM telemetry WHERE kind='tool_step_unavailable'"))

if __name__=='__main__':unittest.main()
