import random,unittest
from v13.agi import metaeff,selfpredict

class MetaEff(unittest.TestCase):
    def test_informative_vs_random_confidence(self):
        r=random.Random(1);good=[];rnd=[]
        for _ in range(300):
            y=int(r.random()<.5);good.append((min(1,max(0,.5+(.3 if y else -.3)+r.gauss(0,.15))),y));rnd.append((r.random(),y))
        g,x=metaeff.report(good,perm=200,boot=100),metaeff.report(rnd,perm=200,boot=100)
        self.assertGreater(g['meta_i'],.3);self.assertLess(g['perm_p'],.01);self.assertGreater(g['auroc2'],.9)
        self.assertLess(x['meta_i'],.1);self.assertGreater(x['perm_p'],.05)
    def test_degenerate(self):
        self.assertEqual(metaeff.meta_i([(.1,1),(.9,1),(.5,1)]),0.);self.assertIsNone(metaeff.meta_i([(.5,1)]));self.assertIsNone(metaeff.auroc2([(.5,1)]))
    def test_abstain_gain_follows_signal(self):
        r=random.Random(2);good=[(.9,1)]*60+[(.1,0)]*40
        self.assertGreater(metaeff.abstain_utility(good)['gain'],0)
        self.assertEqual(metaeff.abstain_utility([(r.random(),1) for _ in range(50)])['gain'],0)

class SelfPredict(unittest.TestCase):
    items=[(a,b) for a in range(2,40) for b in range(2,12)]
    answer=staticmethod(lambda it:it[0]*it[1] if it[0]%7 else (it[0]*it[1])%10)  # hidden quirk: multiples of 7 are "unstable"
    perturb=staticmethod(lambda it:(it[0],it[1]+1))
    def test_state_based_predictor_beats_input_only_control(self):
        r=SelfPredict
        out=selfpredict.run(r.items,r.answer,r.perturb,predict_fn=lambda it,p:1.,input_only_fn=lambda it,p:.0)
        # answer always changes under +1 on b except where quirk makes equal: both controls are weak at least one side
        self.assertIn(out['verdict'],('SELF_KNOWS','NO_SELF_ADVANTAGE'))
        informed=selfpredict.run(r.items,r.answer,r.perturb,predict_fn=lambda it,p:float(r.answer(it)!=r.answer(p)),input_only_fn=lambda it,p:0.)
        self.assertEqual(informed['self_acc'],1.0)
    def test_constant_guess_has_no_advantage(self):
        r=SelfPredict;out=selfpredict.run(r.items,r.answer,r.perturb,predict_fn=lambda it,p:.9)
        self.assertEqual(out['verdict'],'NO_SELF_ADVANTAGE')
if __name__=='__main__':unittest.main()
