"""WP-FS9: scout probes pick the body (synthetic data only)."""
import unittest
import numpy as np
from v13 import scoutroute as S

def data(n,seed):
    r=np.random.default_rng(seed);X=r.normal(size=(n,12))
    # B2 is right on "easy" rows (feature 0 high), B1 on "detail" rows (feature 1 high), teacher almost always
    pb2=1/(1+np.exp(-3*X[:,0]));pb1=1/(1+np.exp(-3*X[:,1]))
    L={'B2_GIST':(r.random(n)<pb2).astype(int),'B1_DETAIL':(r.random(n)<pb1).astype(int),'TEACHER':(r.random(n)<.97).astype(int)}
    conf=np.clip(.5+.15*r.normal(size=n),0,1)                 # scout's own confidence carries no information
    return X,L,conf

class Scout(unittest.TestCase):
    def test_probe_beats_uninformative_confidence_and_is_calibrated(self):
        X,L,_=data(600,1);Xt,Lt,conf=data(600,2);route=S.ScoutRoute().fit(X,L);rep=S.compare(route,Xt,Lt,conf)
        for t in ('B2_GIST','B1_DETAIL'):
            d=rep['targets'][t];self.assertLess(d['logloss_probe'],d['logloss_confidence']-.1);self.assertLess(d['ece_probe'],.1)
    def test_policy_cheaper_than_teacher_and_more_accurate_than_cheapest(self):
        X,L,_=data(600,3);Xt,Lt,conf=data(600,4);rep=S.compare(S.ScoutRoute().fit(X,L),Xt,Lt,conf);p=rep['policy']
        self.assertLess(p['scout']['cost'],p['always_teacher']['cost']);self.assertGreater(p['scout']['accuracy'],p['always_cheapest']['accuracy'])
    def test_too_little_or_constant_labels_use_prior_and_choice_never_blind(self):
        route=S.ScoutRoute().fit(np.zeros((4,3)),{'B2_GIST':[1,1,1,1]});pr=route.probabilities(np.zeros(3))
        self.assertEqual(pr['B2_GIST'],1.);self.assertIn(route.choose(np.zeros(3))['target'],S.TARGETS)
        r2=S.ScoutRoute({'B2_GIST':2,'B1_DETAIL':2,'TEACHER':2});c=r2.choose(np.zeros(3));self.assertIn('best estimate',c['reason'])
    def test_ece_perfect_and_worst(self):
        self.assertAlmostEqual(S.ece([0,1,0,1],[0,1,0,1]),0.);self.assertGreater(S.ece([1,1],[0,0]),.9)

if __name__=='__main__':unittest.main()
