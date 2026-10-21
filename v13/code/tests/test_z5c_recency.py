"""WP-Z5c: note recency switch in v13/focal.py and the task order / counterfactual admission of scripts/z5c_recency.py (no model)."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from v13 import focal as F
import z5c_recency as C

def mem(i,key,created,goal=.5):
    c=F.item('MEMORY','m%d'%i,[{'source_id':'s%d'%i,'char_start':0,'char_end':10}],'note %d'%i,'e',uncertainty=.2,salience=0.,goal=goal,
             utility=.4,sq=1.,cost=.05,state_type='EPISODIC_POINTER',status='MEMORY_SOURCE',created=created)
    return c,{'id':'m%d'%i,'key_text':key,'created':created}

class Slot(unittest.TestCase):
    def test_slot_ignores_entity_calendar_numbers(self):
        self.assertEqual(F.note_slot('Project Kestrel budget March'),F.note_slot('Project Kestrel budget June'))
        self.assertEqual(F.note_slot('Projekt Alder Budget Mai 2026'),F.note_slot('Projekt Alder Budget Oktober'))
        self.assertNotEqual(F.note_slot('Project Kestrel budget March'),F.note_slot('Project Kestrel travel budget'))
        self.assertNotEqual(F.note_slot('Project Kestrel survey bicycles correction'),F.note_slot('Project Kestrel survey bicycles last year'))
    def test_newest_version_wins_older_superseded(self):
        (a,ma),(b,mb),(c,mc)=mem(1,'Project K budget March',1.),mem(2,'Project K budget June',3.),mem(3,'Project K travel budget',5.)
        F.note_versions([a,b,c],[ma,mb,mc])
        self.assertEqual(b['priority_terms'].get('recency'),1.);self.assertEqual(a['priority_terms'].get('superseded'),1.)
        self.assertNotIn('recency',c['priority_terms']);self.assertNotIn('superseded',c['priority_terms'])
        self.assertEqual(a['superseded_by'],'m2')
        self.assertGreater(F.priority(b['priority_terms']),F.priority(a['priority_terms']))
    def test_off_leaves_priority_unchanged(self):
        (a,_),=[mem(1,'Project K budget March',1.)]
        self.assertEqual(F.priority(a['priority_terms']),a['priority'])  # new weights have no effect without the terms
    def test_switch_default_off(self):
        from v13.config import DEFAULTS
        self.assertEqual(DEFAULTS['focal_note_recency'],0)

class Bench(unittest.TestCase):
    def test_chrono_order_and_needed(self):
        for seed in (11,12,13):
            for fid,text,notes,nums,checks,stale in C.tasks(seed):
                self.assertEqual(len(notes),6)
                dated=[C.month(k) for k,_ in notes if C.month(k) is not None]
                self.assertEqual(dated,sorted(dated),fid)
                keys=[k for k,_ in notes]
                if fid.startswith('correction'):
                    self.assertLess(next(i for i,k in enumerate(keys) if k.endswith('last year')),next(i for i,k in enumerate(keys) if k.endswith('correction')))
                for k in C.needed(fid,notes):self.assertIn(k,keys)
                self.assertFalse(set(C.needed(fid,notes))&set(C.stale_keys(fid,notes)))
    def test_seed11_same_contents_as_z5b(self):
        import z5b_capacity as B
        for x,y in zip(B.tasks(11),C.tasks(11)):
            self.assertEqual(x[0],y[0]);self.assertEqual(x[1],y[1]);self.assertEqual(sorted(x[2]),sorted(y[2]));self.assertEqual(x[3],y[3])
    def test_readmit_off_drops_terms(self):
        cands=[];mems=[]
        for i,(k,t) in enumerate([('Project K budget March',1.),('Project K budget June',2.),('Project K budget July',3.),('Project K travel budget',4.)]):
            c,m=mem(i,k,t,goal=.9);cands.append(c);mems.append(m)
        F.note_versions(cands,mems)
        for c in cands:c['priority']=F.priority(c['priority_terms'])*c['decay']
        on=C.readmit(F,cands,2,.3,True);off=C.readmit(F,cands,2,.3,False)
        self.assertIn('m2',[x['item_id'] for x in on]);self.assertNotIn('m0',[x['item_id'] for x in on])
        self.assertTrue(all('superseded' not in x['priority_terms'] for x in off))
        self.assertIn('superseded',cands[0]['priority_terms'])  # originals untouched
    def test_all_notes_recalled_in_chrono_order(self):
        from v13.config import initialize
        from v13.memory import Memory
        from v13.store import Store
        tmp=Path(tempfile.mkdtemp());cfg=initialize(tmp)|C.CFG;s=Store(tmp)
        class R:store=s;memory=Memory(s,cfg)
        for fid,text,notes,*_ in C.tasks(12)[::7]:
            sess=s.new_session();C.seed_notes(R,sess,notes)
            got=R.memory.recall(text,sess,top_k=6);self.assertEqual(len(got),6,fid)
            ts={m['key_text']:m['created'] for m in got};order=[ts[k] for k,_ in notes]
            self.assertEqual(order,sorted(order),fid)
    def test_paired_and_band(self):
        rows=[]
        for rep,(x,y,l) in enumerate([(1,0,1),(1,0,0),(1,1,1)],1):
            for arm,p in (('coalition_recency',x),('full_context',y),('shipped_live',l)):rows.append({'seed':11,'rep':rep,'fixture':'f','arm':arm,'pass':bool(p)})
        p=C.paired(rows,'coalition_recency','full_context');self.assertEqual((p['x_only'],p['y_only']),(2,0));self.assertEqual(C.noise_band(rows),1)

if __name__=='__main__':unittest.main()
