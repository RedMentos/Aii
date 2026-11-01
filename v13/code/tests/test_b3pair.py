import unittest
import numpy as np
from v13 import b3pair as P

def data(n=50,seed=0):
    g=np.random.default_rng(seed);return g.normal(size=(n,8)),g.normal(size=(n,5)),g.integers(0,2,n)

class T(unittest.TestCase):
    def test_roundtrip(self):
        s,r,y=data();m=P.build_manifest(s,r,y,'a','b',1,'t');ok,w=P.verify(m,s,r,y,'a','b');self.assertTrue(ok,w)
    def test_detects_change_order_revision(self):
        s,r,y=data();m=P.build_manifest(s,r,y,'a','b',1,'t')
        s2=s.copy();s2[3,0]+=1;self.assertFalse(P.verify(m,s2,r,y)[0])
        p=np.random.default_rng(1).permutation(len(y));self.assertFalse(P.verify(m,s[p],r[p],y[p])[0])
        self.assertIn('receiver revision differs',P.verify(m,s,r,y,'a','c')[1])
    def test_unpaired_and_nonfinite(self):
        s,r,y=data()
        with self.assertRaises(ValueError):P.build_manifest(s[:-1],r,y,'a','b',1,'t')
        s[0,0]=np.nan
        with self.assertRaises(ValueError):P.build_manifest(s,r,y,'a','b',1,'t')
    def test_disjoint(self):
        s,r,y=data(seed=0);s2,r2,y2=data(seed=9)
        a=P.build_manifest(s,r,y,'a','b',1,'t');b=P.build_manifest(s2,r2,y2,'a','b',2,'t')
        self.assertTrue(P.disjoint(a,b));self.assertFalse(P.disjoint(a,a))
    def test_precheck(self):
        m={'rows':3000};good={'NO_MESSAGE':.69,'SCALAR':.93,'L1':.94,'L2':.82}
        self.assertEqual(P.precheck(good,m)['verdict'],'GO')
        self.assertEqual(P.precheck(dict(good,L2=.93),m)['verdict'],'NO_GO')
        self.assertEqual(P.precheck(dict(good,L1=.70),m)['verdict'],'NO_GO')
        self.assertEqual(P.precheck(good,{'rows':40})['verdict'],'NO_GO')
if __name__=='__main__':unittest.main()
