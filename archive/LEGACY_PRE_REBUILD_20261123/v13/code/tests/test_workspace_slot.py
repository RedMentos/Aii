"""§8.2 / §8.2A / §93 slot minimum on FocalItem and WorkspaceSlot: self_generated, timestamp/age, expiry, exact
fallback, scale, covered range, compression, boundary confidence, cross-scale links. No model needed."""
from pathlib import Path
import tempfile
import unittest
from v13 import focal
from v13.contracts import packet,validate,SLOT_FIELDS
from v13.store import Store
from v13.config import initialize

def ref(sid,a,b,sha='h'):return {'source_id':sid,'sha256':sha,'char_start':a,'char_end':b,'modality':'text'}

class Pure(unittest.TestCase):
    def test_item_carries_slot_minimum(self):
        x=focal.item('B2_GIST','p1',[ref('s',0,40),ref('s',30,60),ref('t',5,9)],'short gist','evt',uncertainty=.2,salience=0.,goal=.5,utility=.5,sq=1.,created=100.)
        self.assertTrue(set(SLOT_FIELDS)<=set(x))
        self.assertTrue(x['self_generated']);self.assertEqual(x['scale'],'gist');self.assertGreater(x['age_ms'],0)
        self.assertEqual(x['covered_range'],[{'source_id':'s','char_start':0,'char_end':60},{'source_id':'t','char_start':5,'char_end':9}])
        self.assertEqual(x['compression_ratio'],round(64/len('short gist'),4))
        self.assertEqual(x['exact_fallback'],'SOURCE_REF');self.assertEqual(len(x['exact_fallback_refs']),3)
        self.assertEqual(x['expiry']['turns_left'],5)  # .6^5=.078 ≥ .05 > .6^6
        self.assertEqual(x['boundary_source'],'NONE');self.assertIsNone(x['boundary_confidence'])
        m=focal.item('MEMORY','m1',[],'v','evt',uncertainty=.2,salience=0.,goal=0.,utility=.4,sq=1.,self_generated=False,decay=.04)
        self.assertFalse(m['self_generated']);self.assertEqual(m['exact_fallback'],'NONE');self.assertIsNone(m['compression_ratio']);self.assertEqual(m['expiry']['turns_left'],0)

    def test_schema_rejects_incomplete_or_inconsistent_slots(self):
        x=focal.item('B1_DETAIL','p',[ref('s',0,4)],'t','evt',uncertainty=.1,salience=0.,goal=0.,utility=0.,sq=1.)
        body={k:v for k,v in x.items() if k!='text'}
        validate('FocalItem',packet('FocalItem','C4_FOCAL','evt','gen',x['source_refs'],**body))
        for bad in ({'scale':'paragraphs'},{'exact_fallback':'NONE'},{'boundary_confidence':.5},{'self_generated':False},
                    {'compression_ratio':0},{'expiry':{'policy':'X','turns_left':-1}},{'covered_range':[{'source_id':'s','char_start':5,'char_end':1}]}):
            with self.assertRaises(ValueError):packet('FocalItem','C4_FOCAL','evt','gen',[],**(body|bad))
        with self.assertRaises(ValueError):packet('FocalItem','C4_FOCAL','evt','gen',[],**{k:v for k,v in body.items() if k!='age_ms'})
        legacy={k:body[k] for k in ('item_id','source_kind','source_refs','fact_hypothesis_status','state_type','salience','uncertainty','priority')}
        packet('FocalItem','C4_FOCAL','evt','gen',[],**legacy,admission='LEGACY_FIRST_N')  # frozen single-pass proof API stays valid
        with self.assertRaises(ValueError):packet('FocalItem','C4_FOCAL','evt','gen',[],**legacy,admission='PRIORITY')
        content={'payload_ref':'p','state_type':'ACTIVE','fact_hypothesis_status':'HYPOTHESIS',**{k:x[k] for k in SLOT_FIELDS}}
        packet('WorkspaceSlot','B4_WORKSPACE','evt','gen',[],owner='B1_DETAIL',source_refs=x['source_refs'],content=content)
        with self.assertRaises(ValueError):packet('WorkspaceSlot','B4_WORKSPACE','evt','gen',[],owner='B1_DETAIL',source_refs=[],content={'payload_ref':'p','state_type':'ACTIVE','fact_hypothesis_status':'H','scale':'fine'})
        with self.assertRaises(ValueError):packet('WorkspaceSlot','B4_WORKSPACE','evt','gen',[],owner='B1_DETAIL',source_refs=[],content=content|{'state_type':'DROPPED'})

class Boundary(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();home=Path(self.tmp.name);initialize(home);self.s=Store(home)
        self.src=self.s.source('Rent is 120. Food costs 271 per month. Total unclear','TEST')
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def test_lexical_alignment_proxy(self):
        r=self.src;t='Rent is 120. Food costs 271 per month. Total unclear'
        a=t.index('Food');b=t.index('month.')+len('month.')
        self.assertEqual(focal.boundary(self.s,[dict(r,char_start=a,char_end=b)]),{'boundary_confidence':1.,'boundary_source':'LEXICAL_ALIGNMENT_PROXY'})
        self.assertEqual(focal.boundary(self.s,[dict(r,char_start=t.index('costs'),char_end=t.index(' per'))])['boundary_confidence'],0.)
        self.assertEqual(focal.boundary(self.s,[dict(r,char_start=t.index('Total'),char_end=len(t))])['boundary_confidence'],1.)
        self.assertEqual(focal.boundary(self.s,[dict(r,sha256='wrong')]),{'boundary_confidence':None,'boundary_source':'NONE'})

if __name__=='__main__':unittest.main()
