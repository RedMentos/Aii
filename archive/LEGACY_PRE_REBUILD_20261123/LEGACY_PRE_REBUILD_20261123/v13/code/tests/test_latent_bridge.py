import unittest
from v13.latent_bridge import Projector,receive
class TestLatent(unittest.TestCase):
 def test_learning_and_receiver(self):
  p=Projector("A_PERCEPTION","B3_CALLOSUM",2,2)
  for _ in range(100):p.update([1,0],[1,-1],admitted=True,committed=True)
  z=p.project([1,0],"e","g")
  v=receive(z,"B3_CALLOSUM","g",{"e"},p.revision())
  self.assertLess(sum((a-b)**2 for a,b in zip(v,[1,-1])),.1)
 def test_uncommitted(self):
  p=Projector("A","B",2,1)
  with self.assertRaises(PermissionError):p.update([1,0],[1],admitted=True)
  self.assertEqual(p.steps,0)
 def test_provenance(self):
  p=Projector("A","B",2,1);z=p.project([1,0],"e","g")
  with self.assertRaises(PermissionError):receive(z,"B","g",{"other"},p.revision())
  with self.assertRaises(ValueError):receive(z,"B","g",{"e"},"stale")
 def test_restart_integrity(self):
  p=Projector("A","B",2,1);p.update([1,0],[1],True,True)
  cp=p.checkpoint();self.assertEqual(Projector.restore(cp).revision(),p.revision())
  cp["w"][0][0]=999
  with self.assertRaises(ValueError):Projector.restore(cp)
 def test_nonfinite(self):
  p=Projector("A","B",2,1)
  with self.assertRaises(ValueError):p.project([float("nan"),0],"e","g")
