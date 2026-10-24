"""Actual Callosum/SQLite packet ordering and CAS replay; complete checkout required."""
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch
from v13.callosum import Callosum, KEY


class Store:
    def __init__(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.execute('CREATE TABLE packets(id TEXT,kind TEXT,event_id TEXT,payload TEXT)')
        self.state_value=None;self.version=0
    def state(self,key,default=None):return copy.deepcopy(self.state_value),self.version
    def set_state(self,key,value,expected=None):
        if expected is not None and expected!=self.version:raise ValueError('CAS conflict')
        self.state_value=copy.deepcopy(value);self.version+=1
    def one(self,query,args):
        row=self.db.execute(query,args).fetchone()
        return dict(row) if row else None
    def log(self,*args):pass
    def add(self,id,kind,eid,payload):
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?)',(id,kind,eid,json.dumps(payload)))
        self.db.commit()


class CallosumOutcomeIntegration(unittest.TestCase):
    def test_repeated_outcome_scores_once(self):
        s=Store()
        s.add('msg1','MessagePacket','e1',{'bytes':100})
        s.add('offer1','OfferPacket','e1',{'packet_id':'offer1','role':'B2_GIST',
              'offer':{'needs_reentry':False},'evidence_refs':[{'source_id':'s1'}],
              'native_metrics':{'duration_s':1.}})
        c=Callosum(s)
        c.note('e1','msg1','B1_DETAIL','B2_GIST','SOURCE_EXACT','SOURCE_EXACT',False,0.)
        with patch('v13.callosum.step',return_value=1.):
            a=c.outcome('e1',{'offer1'},'FINAL')
            b=c.outcome('e1',{'offer1'},'FINAL')
        self.assertEqual(a['scored'],1)
        self.assertEqual(b['scored'],0)
        d=s.state_value['dirs']['B1_TO_B2']['u']['SOURCE_EXACT']
        self.assertEqual(d['n'],1)
        self.assertTrue(s.state_value['pending']['e1'][0]['scored'])
        s.db.close()


if __name__=='__main__':unittest.main()
