import unittest
from v13.latent_bridge import Projector, receive
from v13.latent_receiver_utility_v14 import Receiver, evaluate

class TestLatentReceiver(unittest.TestCase):
    def test_training_changes_numeric_weights_and_holdout(self):
        p = Projector("A3", "B3", 2, 2, rate=.1)
        r = Receiver("B3", 2, rate=.1)
        train = [([1.,0.],[1.,0.],1), ([0.,1.],[0.,1.],0)]
        baseline = evaluate(p,r,[([1.,0.],"h1",1),([0.,1.],"h2",0)],
                            generation="g1",source_ids={"h1","h2"})
        for _ in range(180):
            for x,y,label in train:
                p.update(x,y,admitted=True,committed=True)
                r.learn(p.project(x,"train","g1")["values"],label,
                        admitted=True,committed=True)
        final = evaluate(p,r,[([1.,0.],"h1",1),([0.,1.],"h2",0)],
                         generation="g1",source_ids={"h1","h2"})
        self.assertLess(final["logloss"], baseline["logloss"])
        self.assertGreater(final["accuracy"],baseline["accuracy"])
        self.assertEqual(Receiver.restore(r.checkpoint()).checkpoint(),r.checkpoint())

    def test_authority_and_lineage(self):
        p = Projector("A3","B3",2,2)
        r = Receiver("B3",2)
        with self.assertRaises(PermissionError):
            r.learn([1,0],1,admitted=False,committed=True)
        with self.assertRaises(PermissionError):
            p.update([1,0],[1,0],admitted=False,committed=True)
        packet=p.project([1,0],"s1","g1")
        with self.assertRaises(PermissionError):
            receive(packet,"B3","g2",{"s1"},p.revision())
        with self.assertRaises(PermissionError):
            receive(packet,"B3","g1",{"s2"},p.revision())
        with self.assertRaises(ValueError):
            evaluate(p,r,[],generation="g1",source_ids={"s1"})
        bad=r.checkpoint();bad["bias"]=1
        with self.assertRaises(ValueError):
            Receiver.restore(bad)

if __name__ == "__main__":
    unittest.main()
