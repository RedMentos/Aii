"""WP-Z5e: size rule for every arm and preregistered selection verdict (no model)."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import z5_focal_controls as Z
import z5e_selection_recheck as E

def rows(arm,passes,rep=1):
    return [{'rep':rep,'fixture':'t%02d'%i,'kind':'t','arm':arm,'pass':p,'context_hash':arm+str(i),'same_as_live':True} for i,p in enumerate(passes)]
M=[{'capacity_bound':True,'rejected':1,'displaced':1,'salience_interrupt':1,'candidates':5,'reentry':1,'reentry_in_coalition':1,'coalition':2,'source_bound':2,'all_offers_selected':False}]
RET=[{'sessions':1,'slots_saved':2,'slots_restored':2,'slots_source_bound':2}]

class Fit(unittest.TestCase):
    def test_untouched_when_it_fits(self):
        sp=('H',[1,2],['p']);self.assertEqual(Z.fit_spec(sp,lambda s:True),(('H',[1,2],['p']),0))
    def test_cut_order_prior_oldest_first_then_last_items_one_stays(self):
        seen=[]
        def fits(s):seen.append((list(s[1]),list(s[2])));return len(s[1])+len(s[2])<=1
        sp,cuts=Z.fit_spec(('H',['a','b','c'],['new','old']),fits)
        self.assertEqual(sp,('H',['a'],[]));self.assertEqual(cuts,4)
        self.assertEqual(seen[1],(['a','b','c'],['new']))  # oldest earlier hypothesis goes first
    def test_still_too_long_is_none(self):
        self.assertEqual(Z.fit_spec(('H',['a'],[]),lambda s:False),(None,0))
    def test_render_matches_old_blocks(self):
        self.assertEqual(Z.render(('H',[1],['x'])),'H'+Z.dumps([1])+Z.PRIOR_HEAD+Z.dumps(['x']))
        self.assertEqual(Z.render(('',[],[])),'');self.assertIsNone(Z.render(None))

class Seeds(unittest.TestCase):
    def test_fresh_seeds_differ_from_z5c(self):
        old={t for _,t,_,_ in Z.U2.tasks(7)}
        for s in E.TASK_SEEDS:
            fx=E.fixtures(s);self.assertEqual(len(fx),60);self.assertFalse(old&{t for _,t,_,_ in fx})

class Decide(unittest.TestCase):
    def both(self,coal,ctrl,arm='no_hypotheses'):
        r=[]
        for rep in range(1,4):
            r+=rows('coalition_live',coal,rep)+rows('coalition',coal,rep)
            for a in E.SIMPLER:r+=rows(a,ctrl if a==arm else coal,rep)
        return E.decide(Z.analyse(r,M*3,RET))
    def test_worse_than_simpler_is_simplify(self):
        d=self.both([True]*5+[False]*7,[True]*12);self.assertEqual(d['selection'],'SIMPLIFY');self.assertEqual(d['significantly_worse_than'],['no_hypotheses'])
    def test_better_than_none_is_keep(self):
        self.assertEqual(self.both([True]*12,[True]*5+[False]*7)['selection'],'KEEP')
    def test_tie_is_no_gain(self):
        self.assertEqual(self.both([True,False]*6,[True,False]*6)['selection'],'NO_GAIN')

if __name__=='__main__':unittest.main()
