"""WP-Z5b: task generator, arm views and layer swap of scripts/z5b_capacity.py (no model)."""
from pathlib import Path
import re
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import z5b_capacity as B

class Tasks(unittest.TestCase):
    def test_sixty_tasks_six_distinct_notes_answer_not_stale(self):
        fx=B.tasks();self.assertEqual(len(fx),60)
        self.assertEqual(sorted({f[0].rstrip('0123456789') for f in fx}),['combine','correction','distract','update'])
        for fid,text,notes,nums,checks,stale in fx:
            self.assertEqual(len(notes),6,fid);self.assertEqual(len({k for k,_ in notes}),6,fid)
            self.assertNotIn(nums[0],stale,fid)
            self.assertTrue(all(re.search(p,str(nums[0])) for p in checks.values()),fid)
    def test_all_notes_pass_lexical_recall(self):
        from v13.config import initialize
        from v13.memory import Memory
        from v13.store import Store
        tmp=Path(tempfile.mkdtemp());cfg=initialize(tmp)|B.CFG;s=Store(tmp)
        class R:store=s;memory=Memory(s,cfg)
        for fid,text,notes,*_ in B.tasks()[::7]:
            sess=s.new_session();B.seed_notes(R,sess,notes)
            self.assertEqual(len(R.memory.recall(text,sess,top_k=6)),6,fid)

class Arms(unittest.TestCase):
    def test_views_from_one_pool(self):
        mem=[{'id':'m%d'%i} for i in range(6)]
        offers=[{'role':'B1_DETAIL','packet_id':'a'},{'role':'B2_GIST','packet_id':'b'},{'role':'B1_DETAIL','packet_id':'c'}]
        coal=[{'item_id':'m3','source_kind':'MEMORY'},{'item_id':'m0','source_kind':'MEMORY'},{'item_id':'c','source_kind':'B1_DETAIL'}]
        v=B.arm_views(mem,offers,[offers[2]],coal,4)
        self.assertEqual([m['id'] for m in v['coalition_gated'][0]],['m0','m3'])
        self.assertEqual(len(v['full_context'][0]),6);self.assertEqual(len(v['full_context'][1]),3)
        self.assertEqual([p['packet_id'] for p in v['fixed_slots'][1]],['c','b']);self.assertEqual(len(v['fixed_slots'][0]),2)
        self.assertEqual(v['retrieval_only'],(mem[:4],[]));self.assertEqual(v['no_context'],([],[]))
    def test_swap_layers(self):
        mem,hyp,anchor='\nNotes: [1]','\nHyp: [2]','\nTask: x'
        s='SYS'+mem+hyp+anchor
        self.assertEqual(B.swap_layers(s,(mem,hyp),'NEW',anchor),'SYSNEW'+anchor)
        self.assertEqual(B.swap_layers('SYS'+mem+anchor,(mem,''),'',anchor),'SYS'+anchor)
        self.assertEqual(B.swap_layers('SYS'+anchor,('',''),'NEW',anchor),'SYSNEW'+anchor)
        with self.assertRaises(ValueError):B.swap_layers('SYS'+mem+'X'+hyp+anchor,(mem,hyp),'',anchor)
    def test_clean(self):
        self.assertTrue(B.clean('budget is 55',[40]));self.assertFalse(B.clean('was 40, now 55',[40]));self.assertTrue(B.clean('140',[40]))

if __name__=='__main__':unittest.main()
