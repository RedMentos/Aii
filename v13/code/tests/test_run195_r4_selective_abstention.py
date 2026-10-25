"""Run195 WP-DS3 selective risk/coverage prereg and refusal tests (model-free)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import run195_r4_selective_abstention as A


def row(i,ok,score,digit=True):
    return {'fixture':'f%02d'%i,'pass':ok,'answer_stream_matches_output':True,
            'tokens':[{'token':'42' if digit else 'none','logprob':-score}],
            'features':{A.FEATURE:-score}}


class Selective(unittest.TestCase):
    def test_fixed_train_selection_minimizes_risk_subject_to_coverage(self):
        rows=[row(i,True,i/10) for i in range(7)]+[row(i,False,i/10) for i in range(7,10)]
        t,m=A.choose_threshold(rows,min_coverage=.7)
        self.assertEqual(t,.6)
        self.assertEqual((m['answered'],m['wrong_answered'],m['abstained']),(7,0,3))
        self.assertEqual(m['coverage'],.7)

    def test_missing_digit_is_abstention_not_confidence_zero(self):
        self.assertEqual(A.uncertainty(row(1,False,.01,digit=False)),float('inf'))
        m=A.metrics([row(1,False,.01,digit=False),row(2,True,.2)],.3)
        self.assertEqual((m['answered'],m['wrong_answered'],m['wrong_abstained']),(1,0,1))

    def test_refuses_invalid_threshold_and_no_coverage(self):
        rows=[row(i,True,i/10,digit=False) for i in range(10)]
        with self.assertRaisesRegex(ValueError,'NO_THRESHOLD_MEETS_COVERAGE'):
            A.choose_threshold(rows)
        with self.assertRaisesRegex(ValueError,'THRESHOLD_INVALID'):
            A.metrics(rows,float('nan'))

    def test_prereg_script_hash_and_fields_cannot_change(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prereg.json';p.write_text(json.dumps({'schema':A.SCHEMA,'phase':'PREREGISTERED',
                'script_sha256':'bad','feature':A.FEATURE,'fresh_seed':11,'threshold':.3}))
            with self.assertRaisesRegex(ValueError,'PREREGISTRATION_CHANGED'):
                A.evaluate(p,Path(d)/'fresh.json')

    def test_atomic_closed_proof_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report.json';A.write_once(p,{'value':1})
            with self.assertRaisesRegex(ValueError,'REFUSE_OVERWRITE_PROOF'):
                A.write_once(p,{'value':2})
            self.assertEqual(json.loads(p.read_text()),{'value':1})

    def test_retrospective_verdict_keeps_authority_zero(self):
        rows=[row(i,True,.1) for i in range(42)]+[row(i,False,1.0) for i in range(42,60)]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'prereg.json';reg={'schema':A.SCHEMA,'phase':'PREREGISTERED',
                'script_sha256':A.sha(A.__file__),'feature':A.FEATURE,
                'train_capture_sha256':A.TRAIN_SHA,'fresh_capture_sha256':A.FRESH_SHA,
                'fresh_seed':11,'min_coverage':A.MIN_COVERAGE,'decision_rule':A.RULE,
                'threshold':.2};p.write_text(json.dumps(reg))
            with mock.patch.object(A,'load_capture',return_value=rows):
                report=A.evaluate(p,Path(d)/'fresh.json')
            self.assertEqual(report['verdict'],'SELECTIVE_RISK_SUPPORTED_RETROSPECTIVE')
            self.assertEqual(report['production_authority'],0)
            self.assertFalse(report['canonical_gate_pass'])
            self.assertFalse(report['holdout_blind'])


if __name__=='__main__':unittest.main()
