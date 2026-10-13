"""Release audit regressions using real tiny ZIPs and extracted test processes."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import time
import unittest
import warnings
import zipfile

from scripts import phone_release_audit_candidate as audit


class PhoneReleaseAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.zip = self.root / 'phone.zip'

    def package(self, files=None, *, manifest=None, extras=()):
        files = files if files is not None else {'tests/test_stub.py':
            'import unittest\nclass Stub(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n'}
        if manifest is None:
            manifest = {'schema_version': 1, 'files': {
                path: hashlib.sha256(content.encode()).hexdigest() for path, content in files.items()}}
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.zip, 'w') as archive:
                for path, content in files.items():
                    archive.writestr(audit.PREFIX + path, content)
                archive.writestr(audit.MANIFEST, manifest if isinstance(manifest, str) else json.dumps(manifest))
                for name, content in extras:
                    archive.writestr(name, content)
        return self.zip

    def test_real_full_discovery_pass_preserves_claim_limits_and_proof(self):
        self.package({'tests/test_one.py': 'import unittest\nclass One(unittest.TestCase):\n def test_one(self): pass\n',
                      'tests/test_two.py': 'import unittest\nclass Two(unittest.TestCase):\n def test_two(self): pass\n'})
        report = audit.audit(self.zip, self.root / 'proof')
        self.assertEqual(report['status'], 'EXTRACTED_SOFTWARE_PASS', report)
        self.assertEqual(report['suite']['tests'], 2)
        self.assertEqual(report['suite']['passed'], 2)
        self.assertTrue(report['release_complete'])
        self.assertTrue(report['manifest_unchanged_after_tests'])
        self.assertEqual(report['zip_sha256'], audit.sha256(self.zip))
        self.assertFalse(report['phone_measured'])
        self.assertFalse(report['canonical_gate_pass'])
        self.assertFalse(report['learned_utility_proven'])
        self.assertFalse(report['native_model_runs_requested'])
        self.assertEqual(json.loads((self.root / 'proof/audit.json').read_text()), report)
        self.assertIn('Ran 2 tests', (self.root / 'proof/suite.log').read_text())

    def test_failed_suite_is_failure_with_case_ids(self):
        self.package({'tests/test_bad.py': 'import unittest\nclass Bad(unittest.TestCase):\n def test_bad(self): self.fail("real failure")\n'})
        report = audit.audit(self.zip, self.root / 'proof')
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['suite']['failures'], 1)
        self.assertIn('test_bad.Bad.test_bad', report['suite']['failure_ids'])

    def test_skipped_suite_records_software_success_and_incomplete_release(self):
        self.package({'tests/test_skip.py': 'import unittest\nclass Skip(unittest.TestCase):\n @unittest.skip("missing prerequisite")\n def test_skip(self): pass\n'})
        report = audit.audit(self.zip, self.root / 'proof')
        self.assertEqual(report['status'], 'SOFTWARE_PASS_WITH_SKIPS')
        self.assertEqual(report['suite']['skips'], 1)
        self.assertEqual(report['suite']['passed'], 0)
        self.assertTrue(report['software_tests_successful'])
        self.assertFalse(report['release_complete'])
        self.assertEqual(report['suite']['skipped_cases'][0]['reason'], 'missing prerequisite')

    def test_empty_suite_never_promoted(self):
        self.package({'tests/test_empty.py': '# zero tests\n'})
        report = audit.audit(self.zip, self.root / 'proof')
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['suite']['tests'], 0)

    def test_test_source_mutation_never_promoted(self):
        self.package({'tests/test_mutate.py': 'import pathlib, unittest\nclass Mutate(unittest.TestCase):\n def test_mutate(self): pathlib.Path(__file__).write_text("changed")\n'})
        report = audit.audit(self.zip, self.root / 'proof')
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['suite']['failures'], 0)
        self.assertFalse(report['manifest_unchanged_after_tests'])

    def test_manifest_mutation_never_promoted(self):
        self.package({'tests/test_mutate.py': 'import pathlib, unittest\nclass Mutate(unittest.TestCase):\n def test_mutate(self): pathlib.Path("WORKSPACE_FILES.json").write_text("changed")\n'})
        report = audit.audit(self.zip, self.root / 'proof')
        self.assertEqual(report['status'], 'FAIL')
        self.assertFalse(report['manifest_unchanged_after_tests'])

    def test_timeout_is_retained_failure(self):
        self.package({'tests/test_wait.py': 'import time, unittest\nclass Wait(unittest.TestCase):\n def test_wait(self): time.sleep(2)\n'})
        report = audit.audit(self.zip, self.root / 'proof', timeout=0.1)
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(report['suite_timed_out'])
        self.assertTrue((self.root / 'proof/suite.log').is_file())

    def test_timeout_stops_term_resistant_test_descendant(self):
        marker = self.root / 'leaked-child-marker'
        child = ('import signal,time,pathlib; signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                 'time.sleep(0.8); pathlib.Path(' + repr(str(marker)) + ').write_text("leaked")')
        self.package({'tests/test_spawn.py':
            'import subprocess,sys,time,unittest\nclass Spawn(unittest.TestCase):\n'
            ' def test_spawn(self):\n'
            '  subprocess.Popen([sys.executable,"-c",' + repr(child) + '])\n'
            '  time.sleep(4)\n'})
        report = audit.audit(self.zip, self.root / 'proof', timeout=0.2)
        self.assertTrue(report['suite_timed_out'])
        self.assertTrue(report['suite_timeout_cleanup']['leader_reaped'])
        self.assertEqual(report['suite_timeout_cleanup']['signals_sent'], ['SIGTERM', 'SIGKILL'])
        time.sleep(1)
        self.assertFalse(marker.exists(), 'Audit timeout left a live test descendant')

    def test_invalid_timeout_rejected_before_creating_proof(self):
        self.package()
        for timeout in (0, -1, float('nan'), float('inf'), float('-inf')):
            with self.subTest(timeout=timeout):
                proof = self.root / 'invalid-timeout-proof'
                with self.assertRaisesRegex(ValueError, 'finite and positive'):
                    audit.audit(self.zip, proof, timeout=timeout)
                self.assertFalse(proof.exists())

    def test_output_is_never_replaced(self):
        self.package()
        proof = self.root / 'proof'
        proof.mkdir()
        (proof / 'sentinel').write_text('preserved')
        with self.assertRaises(FileExistsError): audit.audit(self.zip, proof)
        self.assertEqual((proof / 'sentinel').read_text(), 'preserved')

    def test_bad_archive_is_recorded_before_test_launch(self):
        self.zip.write_bytes(b'not zip')
        report = audit.audit(self.zip, self.root / 'proof')
        self.assertEqual(report['status'], 'FAIL')
        self.assertFalse(report['archive_verified'])
        self.assertNotIn('suite', report)

    def test_manifest_checksum_mismatch(self):
        self.package(manifest={'schema_version': 1, 'files': {'tests/test_stub.py': '0' * 64}})
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'): audit.verify_archive(self.zip)

    def test_zip_duplicate_paths(self):
        self.package(extras=[(audit.PREFIX + 'tests/test_stub.py', 'duplicate')])
        with self.assertRaisesRegex(ValueError, 'Duplicate ZIP'): audit.verify_archive(self.zip)

    def test_duplicate_manifest_keys(self):
        self.package(manifest='{"schema_version":1,"files":{"a":"' + '0' * 64 + '","a":"' + '1' * 64 + '"}}')
        with self.assertRaisesRegex(ValueError, 'Duplicate manifest key'): audit.verify_archive(self.zip)

    def test_zip_and_manifest_membership_must_match(self):
        self.package(extras=[(audit.PREFIX + 'unlisted.py', 'unlisted')])
        with self.assertRaisesRegex(ValueError, 'membership'): audit.verify_archive(self.zip)

    def test_missing_manifested_entry(self):
        self.package(manifest={'schema_version': 1, 'files': {'missing.py': '0' * 64}})
        with self.assertRaisesRegex(ValueError, 'membership'): audit.verify_archive(self.zip)

    def test_nonportable_or_escaping_paths_rejected_before_extraction(self):
        for relative in ('../outside.py', '/absolute.py', 'a/../b.py', 'a//b.py',
                         'a/./b.py', 'a\\b.py', 'C:/file.py', 'a/', ''):
            with self.subTest(relative=relative):
                self.package(extras=[(audit.PREFIX + relative, 'bad')])
                with self.assertRaisesRegex(ValueError, 'Invalid archive path'): audit.verify_archive(self.zip)

    def test_other_root_rejected(self):
        self.package(extras=[('Other/file.py', 'bad')])
        with self.assertRaisesRegex(ValueError, 'outside'): audit.verify_archive(self.zip)

    def test_symlink_entry_rejected(self):
        self.package()
        with zipfile.ZipFile(self.zip, 'a') as archive:
            info = zipfile.ZipInfo(audit.PREFIX + 'link')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, '../outside')
        with self.assertRaisesRegex(ValueError, 'regular file'): audit.verify_archive(self.zip)

    def test_invalid_manifest_schemas(self):
        for value in ([], {'schema_version': True, 'files': {'a': '0' * 64}},
                      {'schema_version': 2, 'files': {'a': '0' * 64}},
                      {'schema_version': 1, 'files': []}, {'schema_version': 1, 'files': {}}):
            with self.subTest(value=value):
                self.package(manifest=value)
                with self.assertRaisesRegex(ValueError, 'schema'): audit.verify_archive(self.zip)

    def test_invalid_manifest_digest(self):
        for value in ('0' * 63, 'G' * 64, None, 7):
            with self.subTest(value=value):
                self.package(manifest={'schema_version': 1, 'files': {'tests/test_stub.py': value}})
                with self.assertRaisesRegex(ValueError, 'entry'): audit.verify_archive(self.zip)

    def test_manifest_self_reference_rejected(self):
        self.package(manifest={'schema_version': 1, 'files': {'WORKSPACE_FILES.json': '0' * 64}})
        with self.assertRaisesRegex(ValueError, 'entry'): audit.verify_archive(self.zip)


if __name__ == '__main__':
    unittest.main()
