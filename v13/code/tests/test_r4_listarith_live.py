"""R4 part 6 live measurement script: task rewording keeps checks, measurement policy only replaces the Age verdict. No models."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import r4_listarith_live as M
from v13.agi import hub,listarith
from v13.runtime import Runtime

class Live(unittest.TestCase):
    def test_reworded_sets_keep_checks_and_rule_split(self):
        s=M.task_sets(7);self.assertEqual(len(s['orig']),60);self.assertEqual(len(s['match']),30);self.assertEqual(len(s['nomatch']),15)
        for row in s['match']:self.assertIsNotNone(listarith.operation(row[1]),row[1])
        import r4_rule_question_only as Q  # sets were split under the part-6 rule (R0); R3 now also catches 'exceed'
        for row in s['nomatch']:self.assertIsNone(Q.r0(row[1]),row[1])
        orig={r[0]:r for r in s['orig']};self.assertTrue(all(r[2:]==orig[r[0]][2:] for r in s['match']+s['nomatch']))
        self.assertTrue(all(listarith.operation(t) is None for f,t,_,_ in s['orig'] if f.startswith(('long','notes'))))
    def test_measurement_policy_replaces_only_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Runtime(Path(tmp))
            try:
                r.sleep.cycle.set_policy('enabled','off');reg=hub(r).tools;spec=reg.tools['list_arith']
                args={'operation':'total','text':'a 1, b 2.','values':'a=1\nb=2'}
                M.approve_measurement(reg,True);self.assertEqual(reg._policy(spec,'SYSTEM',args)[1],'TOOL_NOT_ENABLED_BY_USER')
                reg.enable('list_arith');self.assertEqual(reg._policy(spec,'SYSTEM',args)[:2],('APPROVED','AGE_RIGHT_MEASUREMENT'))
                self.assertEqual(reg._policy(reg.tools['calc'],'SYSTEM',{'expression':'1+1'})[0],'DENIED')  # other tools keep Age 0
                self.assertEqual(reg._policy(spec,'SYSTEM',dict(args,extra=1))[0],'DENIED')  # schema still decides
                M.approve_measurement(reg,False);self.assertEqual(reg._policy(spec,'SYSTEM',args)[0],'DENIED')
            finally:r.close()

if __name__=='__main__':unittest.main()
