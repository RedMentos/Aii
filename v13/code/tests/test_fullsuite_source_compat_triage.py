"""Adversarial stdlib controls for non-promoting original full-suite triage."""
import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts import fullsuite_source_compat_triage as audit


class Triage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'original.zip'
        self.log = ('='*70+'\nERROR: test_a (pkg.Test)\n'+'-'*70+'\n'
                    'Traceback\nValueError: Runtime is neither exact frozen baseline nor complete reviewed candidate\n'
                    '\n----------------------------------------------------------------------\n'
                    'Ran 4612 tests in 330.247s\nFAILED (failures=4, errors=66, skipped=28)\n')

    def build(self, log=None, overrides=None):
        files = {'FULL_RAW.log': (self.log if log is None else log).encode(),
                 'FULL_EXIT.txt': b'1', 'HEAD.txt': b'611724bee6b6511826c36af64421d96d1b276016\n'}
        files.update(overrides or {})
        files['SHA256SUMS'] = ''.join(hashlib.sha256(data).hexdigest()+'  ./'+name+'\n'
                                   for name,data in sorted(files.items())).encode()
        with zipfile.ZipFile(self.path,'w') as z:
            for name, data in files.items():
                z.writestr(name, data)
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_valid_original_fixture_preserves_top_level_counts(self):
        sha=self.build(); log, code, got=audit.evidence(self.path,sha)
        self.assertEqual(code,'1'); self.assertEqual(got,sha)
        r=audit.parse(log)
        self.assertEqual(r['top_level_unittest'],{'tests':4612,'failures':4,'errors':66,'skipped':28})
        self.assertEqual(r['trace_header_occurrences'],{'ERROR':1})
        self.assertTrue(r['trace_counts_not_top_level'])

    def test_zip_digest_refusal(self):
        self.build()
        with self.assertRaisesRegex(ValueError,'SHA256_MISMATCH'):
            audit.evidence(self.path,'0'*64)

    def test_manifest_coverage_refusal(self):
        self.build()
        with zipfile.ZipFile(self.path,'a') as z:
            z.writestr('NEW.txt','not manifested')
        sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'COVERAGE_RED'):
            audit.evidence(self.path,sha)

    def test_duplicate_member_refusal(self):
        self.build()
        with zipfile.ZipFile(self.path,'a') as z:
            z.writestr('FULL_RAW.log',self.log)
        sha=hashlib.sha256(self.path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'MEMBER_NAMES_INVALID'):
            audit.evidence(self.path,sha)

    def test_path_traversal_refusal(self):
        sha=self.build(overrides={'../bad':b'evil'})
        with self.assertRaisesRegex(ValueError,'MEMBER_NAMES_INVALID'):
            audit.evidence(self.path,sha)

    def test_truncated_terminal_refusal(self):
        with self.assertRaisesRegex(ValueError,'SUMMARY_MISSING'):
            audit.parse(self.log.split('Ran 4612')[0])

    def test_nested_trace_count_does_not_rewrite_final_summary(self):
        inner='='*70+'\nERROR: nested (subprocess.Test)\n'+'-'*70+'\nValueError: nested source drift\n'
        result=audit.parse(self.log.replace('Ran 4612',inner+'Ran 4612'))
        self.assertEqual(result['trace_header_occurrences']['ERROR'],2)
        self.assertEqual(result['top_level_unittest']['errors'],66)

    def test_reject_malformed_summary(self):
        with self.assertRaisesRegex(ValueError,'SUMMARY_INVALID'):
            audit.parse(self.log.replace('errors=66','errors=sixty'))

    def test_output_exclusive_no_overwrite(self):
        sha=self.build(); target=Path(self.tmp.name)/'report.json'
        audit.main(['--zip',str(self.path),'--sha256',sha,'--out',str(target)])
        with self.assertRaises(FileExistsError):
            audit.main(['--zip',str(self.path),'--sha256',sha,'--out',str(target)])

    def test_no_zip_mutation(self):
        sha=self.build()
        audit.main(['--zip',str(self.path),'--sha256',sha])
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),sha)


if __name__=='__main__': unittest.main()
