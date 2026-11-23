"""Independent Run117AA original ZIP adversarial mutation tests, no models."""
import io
import json
import os
from pathlib import Path
import unittest
import zipfile
from hashlib import sha256

from scripts.run117aa_original_real_jef_native_audit import audit

ORIGINAL = Path(os.environ.get('V13_RUN117Z_ORIGINAL_ZIP',
                               '/mnt/data/run117z-original-native.zip'))


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


def mutate_report(raw, change):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        report = json.loads(z.read('NATIVE_CASE/report.json'))
    change(report)
    return repack(raw, {'NATIVE_CASE/report.json': json.dumps(report).encode()})


def rehash_messages(item):
    item['messages_sha256'] = sha256(json.dumps(
        item['messages'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class OriginalRun117Z(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ORIGINAL.read_bytes()

    def assert_red(self, raw, code):
        with self.assertRaisesRegex(ValueError, code):
            audit(raw, pinned=False)

    def test_original_1_vs_6_pass(self):
        result = audit(self.raw)
        self.assertEqual(result['scores'],
                         {'RAW_EXACT_SOURCE': 1, 'REAL_STORE_JEF_TYPED': 6})
        self.assertTrue(result['formatter_gain'])

    def test_original_hash_pin_rejects_repacked_zip(self):
        changed = repack(self.raw, {'NATIVE_EXIT.txt': b'1\n'})
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_ARTIFACT_SHA_RED'):
            audit(changed)
        self.assert_red(changed, 'NATIVE_EXIT_RED')

    def test_forged_score_rejected_even_after_outer_rehash(self):
        def change(r):
            r['rows'][0]['arms'][0]['score']['correct'] = 1
        self.assert_red(mutate_report(self.raw, change), 'SCORE_RED')

    def test_forged_source_ref_rejected_even_after_message_rehash(self):
        def change(r):
            item = r['rows'][0]['arms'][0]
            payload = json.loads(item['messages'][1]['content'])
            payload['policy']['source_ref']['sha256'] = '0' * 64
            item['messages'][1]['content'] = json.dumps(payload)
            rehash_messages(item)
        self.assert_red(mutate_report(self.raw, change), 'SOURCE_REF_RED')

    def test_oracle_leak_into_raw_arm_rejected(self):
        def change(r):
            item = r['rows'][0]['arms'][0]
            payload = json.loads(item['messages'][1]['content'])
            payload['typed_jef_candidate'] = {'choice': 'A', 'remaining': 50}
            item['messages'][1]['content'] = json.dumps(payload)
            rehash_messages(item)
        self.assert_red(mutate_report(self.raw, change), 'BASE_ORACLE_LEAK_RED')

    def test_duplicate_arm_rejected(self):
        def change(r):
            r['rows'][0]['arms'][1]['arm'] = r['rows'][0]['arms'][0]['arm']
        self.assert_red(mutate_report(self.raw, change), 'ARM_ORDER_RED')

    def test_forged_jef_candidate_rejected(self):
        def change(r):
            r['rows'][0]['typed_jef_candidate'] = {'choice': 'NONE', 'remaining': None}
        self.assert_red(mutate_report(self.raw, change), 'ORACLE_JEF_RED')

    def test_fake_native_model_rejected(self):
        def change(r):
            r['rows'][0]['arms'][0]['native_metrics']['actual_model'] = 'fake.gguf'
        self.assert_red(mutate_report(self.raw, change), 'NATIVE_METRICS_RED')

    def test_gate_promotion_rejected(self):
        def change(r):
            r['step2_exit'] = 'PASS'
        self.assert_red(mutate_report(self.raw, change), 'REPORT_GATES_RED')

    def test_nested_phone_zip_mutation_rejected(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            phone = z.read('V13-Phone-Run117Z.zip')
        with zipfile.ZipFile(io.BytesIO(phone)) as z:
            members = {name: z.read(name) for name in z.namelist()}
        members['V13-Phone/README.md'] += b'\nmutated'
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, data in members.items():
                z.writestr(name, data)
        self.assert_red(repack(self.raw, {'V13-Phone-Run117Z.zip': out.getvalue()}),
                        'PHONE_SHA_RED')


if __name__ == '__main__':
    unittest.main()
