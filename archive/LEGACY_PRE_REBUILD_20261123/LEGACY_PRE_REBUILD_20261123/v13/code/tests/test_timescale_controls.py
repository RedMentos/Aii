"""WP-V4: B2 is its own body; §85.1 controls stay selectable for measurement."""
import json
import tempfile
import unittest
from pathlib import Path
from v13.config import DEFAULTS,validate
from v13.models import ModelManager,model_key,catalog,B2_CONTROLS,ROLES

class TwoBodyDefault(unittest.TestCase):
    def test_b2_has_its_own_pinned_model(self):
        self.assertEqual(ROLES['B2_GIST'],'gist');self.assertEqual(DEFAULTS['b2_control'],'two_body')
        gist=catalog()['models']['gist'];body=catalog()['models']['body']
        self.assertNotEqual(gist['model_id'],body['model_id']);self.assertRegex(gist['files'][0]['sha256'],r'^[0-9a-f]{64}$')
        self.assertIn(gist['revision'],gist['files'][0]['url'])
    def test_controls_reuse_b1_body_only_when_selected(self):
        self.assertEqual(model_key('B2_GIST'),'gist')
        for control in B2_CONTROLS[1:]:self.assertEqual(model_key('B2_GIST',control),'body')
        self.assertEqual(model_key('B1_DETAIL','same_model_same_policy'),'body')
        with self.assertRaises(ValueError):validate(dict(DEFAULTS,b2_control='one_body'))
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);(home/'config').mkdir()
            (home/'config/models.json').write_text(json.dumps({'body':{'exact_revision':'b'},'gist':{'exact_revision':'g'}}))
            self.assertEqual(ModelManager(home).revision('B2_GIST'),'g')
            self.assertEqual(ModelManager(home,'shared_body_dual_state').revision('B2_GIST'),'b')

class GateSummary(unittest.TestCase):
    def test_gate_needs_combination_and_two_body_win(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('tg',Path(__file__).resolve().parents[1]/'scripts/timescale_gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        fx=lambda single,both:{'fixtures':[{'id':'f','best_single_task_fraction':single,'best_both_task_fraction':both,'task_bound_positive_combination_signal':both>single}]}
        good=m.summarize({'two_body':fx(.5,1.),'shared_body_dual_state':fx(.5,.75),'same_model_prompt_only':fx(.5,.5),'same_model_same_policy':fx(.5,.5)})
        self.assertTrue(good['diagnostic_signal']);self.assertFalse(good['gate_promotion']);self.assertFalse(good['cheaper_shared_body_is_enough'])
        tie=m.summarize({'two_body':fx(.5,.75),'shared_body_dual_state':fx(.5,.75)})
        self.assertFalse(tie['two_body_beats_all_controls']);self.assertTrue(tie['cheaper_shared_body_is_enough'])

class KnobAndBridgeKeys(unittest.TestCase):
    def test_every_knob_has_a_declared_kind(self):
        from v13.config import knob_specs,KNOB_KINDS
        specs=knob_specs();self.assertTrue(specs)
        for k in specs:self.assertIn(k['kind'],KNOB_KINDS,k['id']);self.assertFalse(k['learned_allowed'])
    def test_body_swap_drops_bridge_authority(self):
        from v13.models import bridge_key,bridge_authority
        with tempfile.TemporaryDirectory() as td:
            home=Path(td);(home/'config').mkdir()
            (home/'config/models.json').write_text(json.dumps({'body':{'exact_revision':'b'},'gist':{'exact_revision':'g1'}}))
            old=bridge_key(ModelManager(home),'B1_DETAIL','B2_GIST','t1','t2')
            self.assertEqual(bridge_authority(old,old)['authority'],'AS_CALIBRATED')
            (home/'config/models.json').write_text(json.dumps({'body':{'exact_revision':'b'},'gist':{'exact_revision':'g2'}}))
            new=bridge_key(ModelManager(home),'B1_DETAIL','B2_GIST','t1','t2')
            self.assertEqual(bridge_authority(old,new),{'authority':0,'mode':'SHADOW','fallback':'SOURCE_EXACT','recalibrate':True})

if __name__=='__main__':unittest.main()
