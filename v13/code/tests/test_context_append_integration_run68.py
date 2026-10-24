"""Actual ContextOS plan shadow/active append reentry; complete checkout required."""
import copy
import unittest
from unittest.mock import patch
from v13.context_os import ContextOS, empty, KEY


class Store:
    generation_id='g1'
    def __init__(self,state):self.data=copy.deepcopy(state);self.version=0;self.packets=[]
    def state(self,key,default=None):return copy.deepcopy(self.data),self.version
    def set_state(self,key,value,expected=None):
        if expected is not None and expected!=self.version:raise ValueError('CAS')
        self.data=copy.deepcopy(value);self.version+=1
    def one(self,sql,args=()):return {'n':0}
    def add_packet(self,kind,p):self.packets.append(p);return p


def hist(eid):
    return [{'event_id':eid,'role':'user','text':'q'+eid},
            {'event_id':eid,'role':'assistant','text':'a'+eid}]


class ContextAppendIntegration(unittest.TestCase):
    def test_shadow_seed_never_reused_as_active(self):
        st=empty();st['layout']='append_only';st['mode']='SHADOW'
        st['capabilities']={'B1_DETAIL':{'consecutive_user':{'value':True}}}
        store=Store(st)
        ctx=ContextOS(store,{'context_tokens':2048,'answer_tokens':128})
        with patch('v13.context_os.packet',side_effect=lambda *a,**kw:dict(packet_id='p'+str(len(store.packets)+1),**kw)):
            first=ctx.plan('e1','B1_DETAIL','SYSTEM',[],[],'qe1')
            self.assertFalse(first['applied'])
            self.assertFalse(store.data['transcripts']['B1_DETAIL']['applied'])
            ctx.set_mode('ACTIVE',authority='EXPLICIT_HUMAN')
            second=ctx.plan('e2','B1_DETAIL','SYSTEM',[],hist('e1'),'qe2')
            self.assertTrue(second['applied'])
            self.assertNotIn('append_reentry',second['plan']['decisions'])
            self.assertTrue(store.data['transcripts']['B1_DETAIL']['applied'])
            third=ctx.plan('e3','B1_DETAIL','SYSTEM',[],hist('e1')+hist('e2'),'qe3')
            self.assertIn('append_reentry',third['plan']['decisions'])


if __name__=='__main__':unittest.main()
