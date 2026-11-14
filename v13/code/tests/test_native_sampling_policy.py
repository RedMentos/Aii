"""Native sampling policy is an operator contract, not an ignored UI knob."""
import unittest
from v13.config import DEFAULTS
from v13.guards import C3_DECODER
from v13.runners import native_sampling_policy


class NativeSamplingControl(unittest.TestCase):
    def test_c3_ant_echo_never_overrides_explicit_temperature(self):
        for temperature in (0.,.1,.35,.6,1.):
            with self.subTest(t=temperature):
                cfg=dict(DEFAULTS,temperature=temperature,c3_sampling='anti_echo')
                p=native_sampling_policy('C3_LANGUAGE',cfg)
                self.assertEqual(p['temperature'],temperature)
                for name,value in C3_DECODER.items():
                    if name!='temperature':self.assertEqual(p[name],value)
        self.assertEqual(C3_DECODER['temperature'],.6,
                         'the calibrated legacy preset may remain unchanged but not override the knob')

    def test_body_schema_and_non_ant_echo_do_not_inherit_c3_preset(self):
        cfg=dict(DEFAULTS,temperature=.02,c3_sampling='anti_echo')
        for role,schema in [('B1_DETAIL',None),('B2_GIST',{'type':'object'}),
                            ('C3_LANGUAGE',{'type':'object'})]:
            with self.subTest(role=role):
                p=native_sampling_policy(role,cfg,schema)
                self.assertEqual(p,{'temperature':.02,'top_k':50,'repeat_penalty':1.05})
        cfg['c3_sampling']='off'
        self.assertEqual(native_sampling_policy('C3_LANGUAGE',cfg),
                         {'temperature':.02,'top_k':50,'repeat_penalty':1.05})

    def test_no_temperature_setting_fallback_can_hide_unvalidated_configuration(self):
        cfg=dict(DEFAULTS)
        del cfg['temperature']
        with self.assertRaises(KeyError):
            native_sampling_policy('C3_LANGUAGE',cfg)


if __name__=="__main__":unittest.main()
