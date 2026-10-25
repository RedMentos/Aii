"""Run192: isolated B3-H4/H5/H9 calibration and paired utility authority guard.

No production latent authority, no new native/Redmi evidence.
"""
import math
import unittest
import numpy as np
from v13 import b3calibration as B
from scripts import run192_b3_calibration_guard_candidate as G

rng=np.random.default_rng(192)
NATIVE=rng.normal(size=(80,8))
KW={'body_pair_id':'B1->B2','sender_revision':'s1','receiver_revision':'r1',
    'target_tap_id':'receiver.l8'}


def packet(kind='dense'):
    return B.compute(NATIVE,NATIVE[rng.permutation(80)],receiver_kind=kind,
                     downstream_utility=.5,latency_cost=.1,memory_cost=.1,
                     router_kl=.01 if kind=='moe' else None,
                     expert_flip_rate=.02 if kind=='moe' else None,
                     residual_norm_shift=.01 if kind=='moe' else None,**KW)


def call(cal,kind='dense',**kw):
    args={'receiver_revision':'r1','sender_revision':'s1','expected_receiver_kind':kind,
          'ood_ok':True,'latent_utility':.8,'fallback_utility':.3}
    if kind=='moe':
        args['thresholds']={'B3.max_router_kl':.1,
                            'B3.max_expert_flip_rate':.1,
                            'B3.max_residual_norm_shift':.1}
    args.update(kw)
    return G.safe_gate(cal,**args)


class CalibrationGuard(unittest.TestCase):
    def test_baseline_nan_geometry_is_observed_fail_open_but_candidate_closes(self):
        c=packet();c['geometry_error']=float('nan')
        self.assertTrue(B.gate(c,'r1',sender_revision='s1',ood_ok=True,
                               latent_utility=.8,fallback_utility=.3)['authority_may_increase'])
        self.assertEqual(call(c)['latent'],'OFF')
        self.assertFalse(call(c)['authority_may_increase'])

    def test_valid_dense_candidate_is_not_claimed_production_activation(self):
        r=call(packet())
        self.assertEqual(r['latent'],'ON')
        self.assertTrue(r['authority_may_increase'])
        self.assertTrue(r['candidate_only'])
        self.assertFalse(r['production_activation_authorized'])

    def test_nonfinite_negative_malformed_and_missing_packet_values_close(self):
        changes=[('geometry_error',float('inf')),('mean_shift',float('nan')),
                 ('mean_shift',-1.),('norm_ratio',float('nan')),
                 ('sample_count','80'),('sample_count',80.0),
                 ('calibration_confidence',float('nan')),
                 ('receiver_kind',None),('receiver_kind','unknown')]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                c=packet();c[key]=value
                r=call(c)
                self.assertEqual(r['latent'],'OFF',r)
                self.assertFalse(r['authority_may_increase'])

    def test_receiver_kind_must_be_bound_outside_untrusted_packet(self):
        c=packet()
        self.assertEqual(call(c,kind='moe')['latent'],'OFF')
        self.assertEqual(call(c,kind='other')['latent'],'OFF')

    def test_moe_router_nonfinite_and_thresholds_fail_closed(self):
        c=packet('moe')
        self.assertEqual(call(c,kind='moe')['latent'],'ON')
        for key in ('router_kl','expert_flip_rate','residual_norm_shift'):
            x=dict(c);x[key]=float('nan')
            self.assertEqual(call(x,kind='moe')['latent'],'OFF',key)
        self.assertEqual(call(c,kind='moe',thresholds={'B3.max_router_kl':float('nan')})['latent'],'OFF')
        self.assertEqual(call(c,kind='moe',thresholds=None)['latent'],'OFF')

    def test_nonfinite_unmeasured_utility_and_ood_never_authorize(self):
        c=packet()
        for kwargs in ({'latent_utility':float('inf')},{'fallback_utility':float('nan')},
                       {'latent_utility':None},{'fallback_utility':None},
                       {'ood_ok':None},{'fallback':'UNREGISTERED'}):
            with self.subTest(kwargs=kwargs):
                self.assertEqual(call(c,**kwargs)['latent'],'OFF')

    def test_nonmapping_packet_never_crashes(self):
        for c in ('invalid',[1,2,3],True,12):
            r=call(c)
            self.assertEqual(r['latent'],'OFF')
            self.assertFalse(r['authority_may_increase'])


class PairedWindow(unittest.TestCase):
    def rows(self,n=20):
        return [{'event_id':'e%03d'%i,
                 'utility':{'LATENT':.8,'NO_MESSAGE':.1,'SOURCE_EXACT':.2,
                            'CONTROL':.3,'SYMBOLIC':.4}} for i in range(n)]

    def test_all_four_simpler_channels_must_be_present_and_paired(self):
        rows=self.rows()
        self.assertTrue(G.paired_preference(rows)['preferred'])
        for channel in ('NO_MESSAGE','SOURCE_EXACT','CONTROL','SYMBOLIC'):
            r=self.rows();del r[3]['utility'][channel]
            self.assertFalse(G.paired_preference(r)['preferred'],channel)

    def test_short_duplicate_nonfinite_and_misaligned_are_refused(self):
        self.assertFalse(G.paired_preference(self.rows(19))['preferred'])
        dup=self.rows();dup[4]['event_id']=dup[3]['event_id']
        self.assertFalse(G.paired_preference(dup)['preferred'])
        nan=self.rows();nan[7]['utility']['LATENT']=float('nan')
        self.assertFalse(G.paired_preference(nan)['preferred'])
        broken=self.rows();broken[0]['utility']['CONTROL']='0.3'
        self.assertFalse(G.paired_preference(broken)['preferred'])

    def test_old_preferred_does_not_require_four_baselines(self):
        old=B.latent_preferred({'LATENT':[.8]*20,'NO_MESSAGE':[.1]*20})
        self.assertTrue(old['preferred'])
        self.assertFalse(G.paired_preference([
            {'event_id':str(i),'utility':{'LATENT':.8,'NO_MESSAGE':.1}}
            for i in range(20)])['preferred'])

    def test_constant_or_tied_latent_does_not_win(self):
        rows=self.rows()
        for row in rows:row['utility']['SOURCE_EXACT']=.8
        self.assertFalse(G.paired_preference(rows)['preferred'])


if __name__=='__main__':
    unittest.main()
