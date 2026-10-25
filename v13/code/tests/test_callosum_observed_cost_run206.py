"""Run206: B3-H9 utility cannot fabricate missing native time or message byte cost.

Actual Callosum.outcome with synthetic source-valid SQLite packets, no native B3.
"""
import unittest
from unittest.mock import patch

from tests.test_callosum_outcome_integration_run66 import Store
from v13.callosum import Callosum


class CallosumObservedCostRun206(unittest.TestCase):
    def trial(self, metrics, nbytes, include_metrics=True, include_bytes=True):
        s=Store()
        try:
            s.db.execute('INSERT INTO events VALUES (?,?)',('e1','g1'))
            msg={'packet_id':'msg1','event_id':'e1','brain_generation_id':'g1',
                 'sender':'B1_DETAIL','receiver':'B2_GIST','channel':'SOURCE_EXACT',
                 'source_refs':[],'provenance':[]}
            if include_bytes:msg['bytes']=nbytes
            offer={'packet_id':'offer1','event_id':'e1','brain_generation_id':'g1',
                   'role':'B2_GIST','provenance':[],'peer_message_packet_id':'msg1',
                   'offer':{'needs_reentry':False},'evidence_refs':[]}
            if include_metrics:offer['native_metrics']=metrics
            s.add('msg1','MessagePacket','e1',msg)
            s.add('offer1','OfferPacket','e1',offer)
            c=Callosum(s)
            c.note('e1','msg1','B1_DETAIL','B2_GIST','SOURCE_EXACT','SOURCE_EXACT',False,0.)
            with patch('v13.callosum.step',return_value=1.):
                result=c.outcome('e1',{'offer1'},'FINAL')
            return result['scored']
        finally:s.db.close()

    def test_missing_or_invalid_native_duration_cannot_earn_utility(self):
        for label,metrics,include in (
            ('no_native_metrics',None,False),('empty_metrics',{},True),
            ('null_duration',{'duration_s':None},True),
            ('nan_duration',{'duration_s':float('nan')},True),
            ('negative_duration',{'duration_s':-1.},True),
        ):
            with self.subTest(case=label):
                self.assertEqual(self.trial(metrics,100,include_metrics=include),0)

    def test_missing_or_invalid_message_bytes_cannot_earn_utility(self):
        for label,value,include in (
            ('missing',None,False),('null',None,True),('boolean',False,True),
            ('fractional',.5,True),('negative',-1,True),
        ):
            with self.subTest(case=label):
                self.assertEqual(self.trial({'duration_s':1.},value,include_bytes=include),0)

    def test_explicit_zero_and_positive_observed_costs_are_valid(self):
        self.assertEqual(self.trial({'duration_s':0.},0),1)
        self.assertEqual(self.trial({'duration_s':1.5},100),1)


if __name__=='__main__':unittest.main()
