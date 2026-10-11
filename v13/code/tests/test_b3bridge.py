"""WP-J B3-H2/H7/H8/H10 + L1 gate: learned message subspace bridge (numpy)."""
import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from v13 import b3bridge as BB

def toy(n=240,T=6,d=12,seed=0):
    """Label lives in one random token of the sender sequence; the receiver's own state carries nothing about it."""
    g=np.random.default_rng(seed);H=g.normal(size=(n,T,d));mask=np.ones((n,T));mask[:n//3,-2:]=0
    y=g.integers(0,2,n);pos=g.integers(0,T-2,n);key=np.zeros(d);key[0]=1.
    H[np.arange(n),pos]+=np.outer(2*y-1,np.ones(d))*0+np.outer(2*y-1,key)*3+np.outer(np.ones(n),np.eye(d)[1])*3  # marker + label on the key token
    Xr=g.normal(size=(n,5));return H,mask,Xr,y

class MathTests(unittest.TestCase):
    def test_bf16_rounding(self):
        x=np.array([1.,1.00390625,3.14159,-2.5e-3],dtype=np.float32);b=BB.to_bf16(x)
        self.assertEqual(b[0],1.);self.assertTrue(np.all(np.abs(b-x)<=np.abs(x)*2**-8))
        self.assertTrue(np.all((b.view(np.uint32)&0xFFFF)==0))
    def test_gradients_match_finite_differences(self):
        H,mask,Xr,y=toy(n=10,T=5,d=6);b=BB.Bridge(6,K=3,r=2,h=3,classes=2,seed=1)
        b.fit_head(Xr,y,steps=5);b.in_mu=H.reshape(-1,6).mean(0);b.in_sd=H.reshape(-1,6).std(0)
        b.p['Wu']=np.random.default_rng(2).normal(size=b.p['Wu'].shape);b.p['gamma']=np.array([.3])
        kw=dict(lam_var=.3,lam_cov=.2,lam_slot=.4,l2=1e-3);_,gr,_=b.loss_and_grads(H,mask,Xr,y,**kw)
        for k in b.p:
            flat=b.p[k].reshape(-1)
            for i in range(min(4,flat.size)):
                old=flat[i];flat[i]=old+1e-5;lp=b.loss_and_grads(H,mask,Xr,y,**kw)[0];flat[i]=old-1e-5;lm=b.loss_and_grads(H,mask,Xr,y,**kw)[0];flat[i]=old
                self.assertAlmostEqual(gr[k].reshape(-1)[i],(lp-lm)/2e-5,places=4,msg=k)
    def test_cka(self):
        X=np.random.default_rng(0).normal(size=(50,4));self.assertAlmostEqual(BB.linear_cka(X,X@np.diag([2,1,3,1])),BB.linear_cka(X,X@np.diag([2,1,3,1])))
        self.assertAlmostEqual(BB.linear_cka(X,X),1.,places=6);self.assertLess(BB.linear_cka(X,np.random.default_rng(1).normal(size=(50,4))),.3)

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.H,self.mask,self.Xr,self.y=toy();self.tr,self.te=np.arange(180),np.arange(180,240)
        self.b=BB.Bridge(12,K=2,r=4,h=4,classes=2,seed=0).fit_head(self.Xr[self.tr],self.y[self.tr])
    def acc(self,**kw):return float((self.b.logits(self.H[self.te],self.mask[self.te],self.Xr[self.te],**kw).argmax(1)==self.y[self.te]).mean())
    def test_message_carries_sender_only_information_and_gate_closed_is_old_task(self):
        base=self.acc(gate_open=False);self.b.fit(self.H[self.tr],self.mask[self.tr],self.Xr[self.tr],self.y[self.tr],epochs=40,batch=32,lr=1e-2)
        self.assertLess(base,.7);self.assertGreater(self.acc(),.9)
        W,b=self.b.head;self.assertTrue(np.array_equal(self.b.logits(self.H,self.mask,self.Xr,gate_open=False),self.Xr@W+b))
        rep=BB.diversity_report(self.b,self.H,self.mask,self.H.mean(1),self.Xr,self.Xr)
        self.assertTrue(rep['old_task_identical_when_gate_closed']);self.assertGreater(rep['message_dim_std_min'],0.)
    def test_calibration_closes_gate_on_ood_and_reload_is_identical(self):
        self.b.fit(self.H[self.tr],self.mask[self.tr],self.Xr[self.tr],self.y[self.tr],epochs=20,batch=32,lr=1e-2)
        self.b.calibrate(self.H[self.tr],self.mask[self.tr])
        far=self.H[self.te]*50;out=self.b.logits(far,self.mask[self.te],self.Xr[self.te]);W,b=self.b.head
        self.assertTrue(np.allclose(out,self.Xr[self.te]@W+b))  # OOD message -> gate closed -> NO_MESSAGE readout
        with tempfile.TemporaryDirectory() as t:
            man=self.b.save(Path(t)/'b3'/'B1_TO_B2','s1','r1',{'l1_gate':{'verdict':'FAIL'}})
            c=BB.Bridge.load(Path(t)/'b3'/'B1_TO_B2','s1','r1')
            self.assertTrue(np.array_equal(c.logits(self.H,self.mask,self.Xr),self.b.logits(self.H,self.mask,self.Xr)))
            with self.assertRaises(ValueError):BB.Bridge.load(Path(t)/'b3'/'B1_TO_B2','s1','r2')
            f=BB.doctor_fields(t,'B1_TO_B2','r1');self.assertEqual(f['latent_level'],'unavailable');self.assertEqual(f['slot_budget'],2)
            self.assertEqual(f['latent_read_authority'],0);self.assertEqual(f['bridge']['sha256'],man['sha256'])
            self.assertTrue(BB.doctor_fields(t,'B1_TO_B2','r9')['bridge']['stale_receiver_revision'])
            self.assertIsNone(BB.doctor_fields(t,'B2_TO_B1')['bridge'])

class BudgetGateTests(unittest.TestCase):
    def test_h7_budget(self):
        b=BB.budget(768,K=16,r=32,h=32,classes=3)
        self.assertEqual(b['message_bf16_bytes'],16*32*2);self.assertTrue(b['age0_ok']);self.assertLess(b['weights_bf16_bytes'],256*1024)
        self.assertFalse(BB.budget(4096,K=64,r=512,h=1024)['age0_ok'])
    def test_l1_gate(self):
        good={'acc':{'NO_MESSAGE':[.6]*5,'LATENT':[.9,.91,.9,.92,.9],'LATENT_SHUFFLED':[.6]*5,'EXACT':[.95]*5,'SYMBOLIC':[.7]*5},
              'bytes':{'LATENT':64,'EXACT':3900,'SYMBOLIC':60},'role_drop':0.,'ood_rate':.01,'reload_identical':True}
        g=BB.l1_gate(good);self.assertEqual(g['verdict'],'PASS',g);self.assertEqual(g['missing_baselines'],['CONTROL'])
        bad=json.loads(json.dumps(good));bad['bytes']['EXACT']=40
        self.assertEqual(BB.l1_gate(bad)['verdict'],'FAIL')  # exact detail is cheap -> latent loses on utility
        bad2=json.loads(json.dumps(good));bad2['role_drop']=.05;self.assertEqual(BB.l1_gate(bad2)['verdict'],'FAIL')

if __name__=='__main__':unittest.main()
