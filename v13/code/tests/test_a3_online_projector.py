"""Host-only A3 numeric learning/holdout/restart tests."""
import tempfile
import unittest
from pathlib import Path
from v13.a3_online_projector import A3Projector

class TestA3Projector(unittest.TestCase):
    def test_training_retention_restart(self):
        p=A3Projector(2,1,.05)
        train=[([1.,0.],[.6]),([0.,1.],[-.4]),([1.,1.],[.2])]
        holdout=[([.5,.5],[.1]),([.8,.2],[.4])]
        mse=lambda: sum((p.predict(x)[0]-y[0])**2 for x,y in holdout)/len(holdout)
        before=mse()
        with self.assertRaises(PermissionError):
            p.train(*train[0])
        for _ in range(250):
            for x,y in train:
                p.train(x,y,trusted=True)
        after=mse()
        self.assertLess(after,before*.05)
        self.assertNotEqual(p.weights,[[0.,0.]])
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"a3.json"
            p.save(f)
            q=A3Projector.load(f)
            self.assertEqual(q.predict([.5,.5]),p.predict([.5,.5]))
            self.assertEqual(q.steps,750)

    def test_invalid_data(self):
        p=A3Projector()
        for x in ([float("nan"),0,0],[True,0,0],[1e6,0,0]):
            with self.assertRaises(ValueError):
                p.predict(x)

if __name__=="__main__":
    unittest.main()
