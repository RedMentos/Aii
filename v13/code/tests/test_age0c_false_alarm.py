"""WP-AGE0c: measuring script for late self-correction false alarms. Variants and the live-parity check; no models."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import age0c_false_alarm as F  # noqa: E402


def pair(summary,reentry,output,source='',role='B2_GIST'):
    return {'role':role,'offer':{'offer':{'summary':summary,'needs_reentry':reentry}},'output':output,'source':source}


class DetectTests(unittest.TestCase):
    def test_v0_fires_on_reentry_alone_v1_does_not(self):
        p=pair('All fine.',True,'10')
        self.assertTrue(F.detect('V0',p['offer'],'10','')[0]);self.assertFalse(F.detect('V1',p['offer'],'10','')[0])

    def test_v2_ignores_numbers_echoed_from_the_question(self):
        p=pair('The user asks for 3 + 7.',False,'10','Compute: 3 + 7 = ?')
        self.assertTrue(F.detect('V1',p['offer'],p['output'],p['source'])[0])
        self.assertFalse(F.detect('V2',p['offer'],p['output'],p['source'])[0])
        alarm,cited=F.detect('V2',pair('Total is 11',False,'')['offer'],'10','Compute: 3 + 7 = ?')
        self.assertTrue(alarm);self.assertEqual(cited,{'11'})

    def test_wilson_bounds(self):
        self.assertEqual(F.wilson(0,0),[None,None]);lo,hi=F.wilson(5,100);self.assertTrue(lo<.05<hi<.12)

    def test_live_code_matches_v0(self):
        ps=[pair('Total is 42.5',False,'Total is 40.'),pair('ok',False,'ok'),pair('x',True,'y'),pair('3,5 left',False,'3.5 left')]
        self.assertEqual(F.live_alarms(ps),[F.detect('V0',p['offer'],p['output'],p['source'])[0] for p in ps])


if __name__=='__main__':unittest.main()
