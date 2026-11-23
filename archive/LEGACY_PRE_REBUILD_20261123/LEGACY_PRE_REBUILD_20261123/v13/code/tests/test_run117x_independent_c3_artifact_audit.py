"""Adversarial read-only original artifact tests; no model calls."""
import io
import os
import json
from pathlib import Path
import unittest
import zipfile
from hashlib import sha256

from scripts.run117x_independent_c3_artifact_audit import audit

ORIGINAL = Path(os.environ.get('V13_RUN117W_ORIGINAL_ZIP', '/mnt/data/run117w-original.zip'))


def repack(raw, replacements):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members = {name: z.read(name) for name in z.namelist()}
    members.update(replacements)
    if 'SHA256SUMS' in members:
        members['SHA256SUMS'] = ''.join(
            sha256(members[name]).hexdigest() + '  ./' + name + '\n'
            for name in sorted(members) if name != 'SHA256SUMS').encode()
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return out.getvalue()


def tamper_report(raw, modify):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        report = json.loads(z.read('NATIVE_CASE/report.json'))
    modify(report)
    return repack(raw, {'NATIVE_CASE/report.json': json.dumps(report).encode()})


class OriginalNativeAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ORIGINAL.read_bytes()

    def assert_red(self, raw, code):
        with self.assertRaisesRegex(ValueError, code):
            audit(raw, pinned=False)

    def test_original_pass(self):
        self.assertEqual(audit(self.raw)['scores']['TYPED_JEF_FORMATTER'], 6)

    def test_original_byte_tamper_even_when_outer_valid(self):
        changed = repack(self.raw, {'NATIVE_EXIT.txt': b'1\n'})
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_ARTIFACT_SHA_RED'):
            audit(changed)
        self.assert_red(changed, 'NATIVE_EXIT_RED')

    def test_score_forgery_with_rehashed_archive(self):
        def change(r):
            r['rows'][0]['arms'][0]['score']['correct'] = 1
        self.assert_red(tamper_report(self.raw, change), 'SCORE_RECALC_RED')

    def test_wrong_source_ref_with_rehashed_archive(self):
        def change(r):
            item = r['rows'][0]['arms'][0]
            payload = json.loads(item['messages'][1]['content'])
            payload['policy']['source_ref']['sha256'] = '0' * 64
            item['messages'][1]['content'] = json.dumps(payload)
            item['messages_sha256'] = sha256(json.dumps(item['messages'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assert_red(tamper_report(self.raw, change), 'SOURCE_REF_RED')

    def test_hidden_oracle_in_base_arm(self):
        def change(r):
            item = r['rows'][0]['arms'][0]
            payload = json.loads(item['messages'][1]['content'])
            payload['typed_jef_candidate'] = {'choice': 'A', 'remaining': 50}
            item['messages'][1]['content'] = json.dumps(payload)
            item['messages_sha256'] = sha256(json.dumps(item['messages'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assert_red(tamper_report(self.raw, change), 'ORACLE_LEAK_RED')

    def test_duplicate_arm_instead_of_real_control(self):
        def change(r):
            r['rows'][0]['arms'][2]['arm'] = r['rows'][0]['arms'][0]['arm']
        self.assert_red(tamper_report(self.raw, change), 'ARM_COVERAGE_RED')

    def test_gate_promotion_rejected(self):
        def change(r):
            r['step2_exit'] = 'PASS'
        self.assert_red(tamper_report(self.raw, change), 'REPORT_GATE_RED')

    def test_fake_native_model_rejected(self):
        def change(r):
            r['rows'][0]['arms'][0]['native_metrics']['actual_model'] = 'fake.gguf'
        self.assert_red(tamper_report(self.raw, change), 'NATIVE_METRIC_RED')

    def test_nested_phone_file_tamper_rejected(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            phone = z.read('V13-Phone-Run117W.zip')
        with zipfile.ZipFile(io.BytesIO(phone)) as z:
            names = z.namelist()
            entries = {name: z.read(name) for name in names}
        entries['V13-Phone/README.md'] += b'\nmutated'
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, data in entries.items():
                z.writestr(name, data)
        changed = repack(self.raw, {'V13-Phone-Run117W.zip': out.getvalue()})
        self.assert_red(changed, 'PHONE_SHA_RED')


if __name__ == '__main__':
    unittest.main()