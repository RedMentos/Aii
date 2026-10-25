"""Synthetic adversarial tests; never claim native execution from this fixture."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from verify_run336_artifact import audit, EXPECTED_HEAD, GATES, ARMS


def fake_files():
    arms = {}
    for name, (mode, replay) in ARMS.items():
        arms[name] = {'loss_mode': mode, 'replay': replay, 'native_training_executed': True,
                      'status': 'COMPLETE_NATIVE_DIAGNOSTIC', 'weights_published': False,
                      'weights_retained': False, 'checkpoint_receipts': [{}, {}],
                      'epochs': [{'evaluation': {'summary': {'facts_strict': 0}}},
                                 {'evaluation': {'summary': {'facts_strict': 1}}}],
                      'tensor_audit': {'changes': {'unchanged_nonselected': 144}},
                      'selection_report': {'selection': 'NONE'}}
    report = {'status': 'COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC',
              'evidence_level': 'LINUX_NATIVE_C3_FRESH_COHORT_TRAIN_EVAL',
              'gates': GATES, 'model_activated': False, 'weights_published': False,
              'arms': arms}
    files = {'RUN330_HEAD.txt': EXPECTED_HEAD + '\n',
             'RUN334_GGUF_IMPORT_RAW.log': 'PINNED_B10964_GGUF_IMPORT_OK /tmp/llama.cpp-b10964/gguf-py/gguf/__init__.py\n',
             'run334eval/RUN334_REPORT.json': json.dumps(report),
             'RUN334_INDEPENDENT_AUDIT.json': json.dumps({'status': 'PASS_SOURCE_ONLY_REPORT_AUDIT_NOT_NATIVE_REEXECUTION', 'gates': GATES})}
    for name in ('RUN330_MODEL_EXIT.txt', 'RUN330_COMPILE_EXIT.txt',
                 'RUN334_GGUF_IMPORT_EXIT.txt', 'RUN334_NATIVE_EXIT.txt',
                 'RUN334_AUDIT_EXIT.txt', 'RUN330_PRIVACY_EXIT.txt'):
        files[name] = '0\n'
    return files


def zip_fixture(path, files, *, corrupt_manifest=False):
    manifest = '\n'.join(hashlib.sha256(content.encode()).hexdigest() + '  ./' + name
                         for name, content in sorted(files.items())) + '\n'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr('RUN334_SHA256SUMS.txt', manifest.replace('0', 'f', 1) if corrupt_manifest else manifest)


class IndependentZipGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'raw.zip'
        self.files = fake_files()

    def tearDown(self):
        self.tmp.cleanup()

    def run_case(self, reason=None, *, corrupt_manifest=False):
        zip_fixture(self.path, self.files, corrupt_manifest=corrupt_manifest)
        if reason:
            with self.assertRaisesRegex(ValueError, reason):
                audit(self.path)
        else:
            result = audit(self.path)
            self.assertEqual(result['status'], 'PASS_RAW_ARTIFACT_INTEGRITY_NOT_NATIVE_REEXECUTION')
            self.assertEqual(result['manifest_entries'], len(self.files))

    def test_synthetic_complete_shape_only(self):
        self.run_case()

    def test_manifest_tamper(self):
        self.run_case('raw SHA mismatch', corrupt_manifest=True)

    def test_wrong_head(self):
        self.files['RUN330_HEAD.txt'] = 'not exact\n'
        self.run_case('wrong exact head')

    def test_missing_arm(self):
        row = json.loads(self.files['run334eval/RUN334_REPORT.json'])
        del row['arms']['C_ANSWER_REPLAY']
        self.files['run334eval/RUN334_REPORT.json'] = json.dumps(row)
        self.run_case('missing native arm')

    def test_incomplete_optimizer(self):
        row = json.loads(self.files['run334eval/RUN334_REPORT.json'])
        row['arms']['B_ANSWER_NO_REPLAY']['native_training_executed'] = False
        self.files['run334eval/RUN334_REPORT.json'] = json.dumps(row)
        self.run_case('arm mode, optimizer')

    def test_native_exit_failure(self):
        self.files['RUN334_NATIVE_EXIT.txt'] = '2\n'
        self.run_case('nonzero stage')

    def test_unpinned_reader(self):
        self.files['RUN334_GGUF_IMPORT_RAW.log'] = 'PINNED_B10964_GGUF_IMPORT_OK /usr/lib/python/gguf/__init__.py\n'
        self.run_case('official GGUF reader')

    def test_independent_audit_failure(self):
        self.files['RUN334_INDEPENDENT_AUDIT.json'] = json.dumps({'status': 'FAIL_CLOSED', 'gates': GATES})
        self.run_case('independent raw-score')

    def test_gate_promotion(self):
        row = json.loads(self.files['run334eval/RUN334_REPORT.json'])
        row['gates']['jepa_weight'] = 1
        self.files['run334eval/RUN334_REPORT.json'] = json.dumps(row)
        self.run_case('negative gate drift')

    def test_weights_publication(self):
        self.files['trained.gguf'] = 'fake model'
        self.run_case('model weights published')

    def test_archive_traversal(self):
        self.files['../escape.txt'] = 'evil'
        self.run_case('unsafe archive member')

    def test_selected_only_receipt(self):
        row = json.loads(self.files['run334eval/RUN334_REPORT.json'])
        row['arms']['A_ALL_NO_REPLAY']['tensor_audit']['changes']['unchanged_nonselected'] = 143
        self.files['run334eval/RUN334_REPORT.json'] = json.dumps(row)
        self.run_case('unselected weights changed')


if __name__ == '__main__':
    unittest.main()