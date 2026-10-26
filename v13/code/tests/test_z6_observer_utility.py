"""WP-Z6 §24.25 observer utility bench: fixtures, scoring and verdict logic (no models)."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import z6_observer_utility as Z

class Bench(unittest.TestCase):
    def test_fixtures_are_seeded_and_have_five_kinds(self):
        fx=Z.fixtures(59);self.assertEqual(len(fx),75);self.assertEqual([f[0] for f in fx],[f[0] for f in Z.fixtures(59)])
        self.assertEqual({Z.kind(f[0]) for f in fx},{'summary','long','notes','compare','correction'})
        c=[f for f in fx if f[0]=='correction00'][0];self.assertEqual(len(c[1]),2);self.assertNotIn('remember',c[1][0])
    def test_correction_needs_new_day_and_rejects_old_day(self):
        nums,checks,extra=[37,12],{'qty':r'\b37\b','day':r'\b12\b','x':None},{'old':5,'new':12}
        self.assertTrue(Z.score('c','37 crates go to Graz on 12 May.',nums,checks,extra))
        self.assertFalse(Z.score('c','37 crates go to Graz on 5 May, not 12.',nums,checks,extra))
    def test_verdict(self):
        def rows(arm,passes,t):return [{'fixture':'f%d'%i,'kind':'long','arm':arm,'pass':p,'turn_s':t,'n_offers':0 if arm=='none' else 1,'reentries':0,
                                        'observer_flags_conflict':False,'contested':False,'observer_mentions_new_value':False} for i,p in enumerate(passes)]
        good=[True]*12+[False]*3;bad=[False]*12+[True]*3
        res=Z.analyse(rows('none',bad,2)+rows('A',good,5)+rows('B',good,5)+rows('AB',good,10)+rows('adaptive',good,10))
        self.assertEqual(res['verdict'],'ALWAYS_PASS_JUSTIFIED')
        res=Z.analyse(rows('none',bad,2)+rows('A',good,5)+rows('B',good,5)+rows('AB',good,10)+rows('adaptive',good,5))
        self.assertEqual(res['verdict'],'ADAPTIVE_PREFERRED')
        res=Z.analyse(rows('none',good,2)+rows('A',bad,5)+rows('B',bad,5)+rows('AB',bad,10)+rows('adaptive',bad,10))
        self.assertEqual(res['verdict'],'ALWAYS_PASS_NOT_JUSTIFIED');self.assertFalse(res['criteria']['O3_always_pass_does_not_hurt'])

if __name__=='__main__':unittest.main()
