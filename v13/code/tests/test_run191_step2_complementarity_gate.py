"""Run191: STEP2 must not turn GREEN from row-integrity checks alone.

The existing Linux-native timescale ablation says complementarity_proven=False.
Keep that immutable negative evidence in the gate graph; no test creates a
positive native result or changes the original STEP2 cohort.
"""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from v13 import gates
from v13.common import APP


class Step2ComplementarityGate(unittest.TestCase):
    def setUp(self):
        self.gate=gates.spec()['gates']['STEP2']
        self.native='../bench-results/timescale-gate-20261009/two_body.analysis.json'
        self.original='docs/proofs/step2-final-full-audit-20261009.json'

    def test_original_row_integrity_gate_is_preserved(self):
        verdict=self.gate['verdict']
        self.assertIn({'file':self.original,'path':'all70_rowchecks_pass',
                       'op':'==','value':True},verdict)
        self.assertIn({'file':self.native,'path':'complementarity_proven',
                       'op':'==','value':True},verdict)
        self.assertIn(self.original,self.gate['real_data'])
        self.assertIn('docs/proofs/step2-ablations-linux.json',self.gate['ablation'])

    def test_immutable_native_negative_or_missing_evidence_is_not_green(self):
        # The model-free Phone source ZIP intentionally excludes sibling
        # bench-results. Missing evidence must fail shut rather than turning
        # the original native negative into a fabricated positive.
        path=APP/self.native
        failures=gates.verdicts(self.gate)
        if path.is_file():
            raw=json.loads(path.read_text())
            self.assertIs(raw['complementarity_proven'],False)
            self.assertFalse(raw['gate_promotion'])
            actual=False
        else:
            actual='FileNotFoundError'
        self.assertTrue(any(x['path']=='complementarity_proven' and x['actual']==actual
                            for x in failures),failures)
        self.assertNotEqual(gates.evaluate()['STEP2']['status'],'GREEN')

    def test_rowcheck_true_native_false_and_missing_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            app=Path(d)/'code';row=app/self.original;row.parent.mkdir(parents=True)
            row.write_text(json.dumps({'all70_rowchecks_pass':True}))
            native=app/self.native;native.parent.mkdir(parents=True)
            with mock.patch.object(gates,'APP',app):
                native.write_text(json.dumps({'complementarity_proven':False}))
                self.assertEqual([f['path'] for f in gates.verdicts(self.gate)],
                                 ['complementarity_proven'])
                native.unlink()
                self.assertEqual([f['path'] for f in gates.verdicts(self.gate)],
                                 ['complementarity_proven'])
                native.write_text(json.dumps({'complementarity_proven':'true'}))
                self.assertEqual([f['path'] for f in gates.verdicts(self.gate)],
                                 ['complementarity_proven'])

    def test_both_verdicts_must_pass_not_just_one(self):
        with tempfile.TemporaryDirectory() as d:
            app=Path(d)/'code';row=app/self.original;row.parent.mkdir(parents=True)
            native=app/self.native;native.parent.mkdir(parents=True)
            with mock.patch.object(gates,'APP',app):
                row.write_text(json.dumps({'all70_rowchecks_pass':False}))
                native.write_text(json.dumps({'complementarity_proven':True}))
                self.assertEqual([f['path'] for f in gates.verdicts(self.gate)],
                                 ['all70_rowchecks_pass'])
                row.write_text(json.dumps({'all70_rowchecks_pass':True}))
                self.assertEqual(gates.verdicts(self.gate),[])


if __name__=='__main__':
    unittest.main()
