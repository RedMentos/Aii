"""Archive policy and executable extracted-package regressions."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.package_source import PHONE_REQUIRED_FIXTURES

ROOT=Path(__file__).resolve().parents[1]


class PackageSource(unittest.TestCase):
    def make_app(self,root):
        app=root/'app'
        (app/'scripts').mkdir(parents=True)
        shutil.copyfile(ROOT/'scripts/package_source.py',app/'scripts/package_source.py')
        items={'v13/main.py':'# runtime\n','tests/test_stub.py':'# test\n',
               'docs/proofs/report.json':'{"status":"RUNNING"}',
               'docs/proofs/report.checkpoint/data/db/brain.sqlite3':'OPEN_SQLITE',
               'docs/proofs/report.checkpoint/data/db/brain.sqlite3-wal':'OPEN_WAL',
               'docs/proofs/report.checkpoint.previous-123/data/db/brain.sqlite3':'ROTATED_SQLITE',
               'docs/proofs/closed-checkpoints/base.closed.zip':'SEALED_CHECKPOINT',
               'v13/__pycache__/compiled.pyc':'CACHE',
               'WORKSPACE_FILES.json':'OLD_MANIFEST'}
        items.update({path:'# immutable baseline fixture\n' if path.endswith('.py') else '{"schema":"fixture"}'
                      for path in PHONE_REQUIRED_FIXTURES})
        for name,data in items.items():
            path=app/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
        return app

    def package(self,app,out,phone=False):
        args=[sys.executable,str(app/'scripts/package_source.py'),'--out',str(out)]
        if phone:args.append('--phone-install')
        return subprocess.run(args,capture_output=True,text=True,timeout=30)

    def inspect(self,out):
        with zipfile.ZipFile(out) as archive:
            self.assertIsNone(archive.testzip())
            manifest=json.loads(archive.read('V13-Phone/WORKSPACE_FILES.json'))
            names=set(archive.namelist())
            self.assertEqual(names,{'V13-Phone/WORKSPACE_FILES.json'}|{'V13-Phone/'+p for p in manifest['files']})
            for path,sha in manifest['files'].items():
                self.assertEqual(hashlib.sha256(archive.read('V13-Phone/'+path)).hexdigest(),sha)
            return manifest['files']

    def test_source_excludes_live_and_rotated_sqlite_but_keeps_sealed_checkpoint(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);app=self.make_app(root);out=root/'source.zip'
            completed=self.package(app,out)
            self.assertEqual(completed.returncode,0,completed.stderr)
            files=self.inspect(out)
            self.assertFalse(any('.checkpoint/' in p or '.checkpoint.previous-' in p for p in files))
            self.assertIn('docs/proofs/closed-checkpoints/base.closed.zip',files)
            self.assertIn('docs/proofs/report.json',files)
            self.assertTrue(PHONE_REQUIRED_FIXTURES<=set(files))

    def test_phone_includes_only_required_baseline_and_does_not_rewrite_source_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);app=self.make_app(root);out=root/'phone.zip'
            completed=self.package(app,out,phone=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            files=self.inspect(out)
            self.assertTrue(PHONE_REQUIRED_FIXTURES<=set(files))
            self.assertNotIn('docs/proofs/report.json',files)
            self.assertNotIn('docs/proofs/closed-checkpoints/base.closed.zip',files)
            self.assertFalse(any('.checkpoint/' in p or '.checkpoint.previous-' in p for p in files))
            self.assertEqual((app/'WORKSPACE_FILES.json').read_text(),'OLD_MANIFEST')

    def test_missing_phone_dependency_fails_before_creating_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);app=self.make_app(root);out=root/'phone.zip'
            (app/sorted(PHONE_REQUIRED_FIXTURES)[0]).unlink()
            completed=self.package(app,out,phone=True)
            self.assertNotEqual(completed.returncode,0)
            self.assertIn('required fixture missing',completed.stderr)
            self.assertFalse(out.exists())
            self.assertFalse(out.with_suffix('.partial').exists())

    def native_firing_applicable(self, app):
        """Only run historical firing tests when their exact source binding holds.

        Newer reviewed Runtime sources are not that frozen candidate. A stale
        candidate must refuse; corruption/missing fixtures must still FAIL.
        """
        probe=subprocess.run([sys.executable,'-c',
            'from scripts.native_firing_runtime_candidate import sources; sources()'],
            cwd=app,capture_output=True,text=True,timeout=30)
        if probe.returncode==0:return True
        self.assertEqual(probe.returncode,1,probe.stderr)
        self.assertEqual(probe.stderr.strip().splitlines()[-1],
            'ValueError: Live sources differ from complete baseline/candidate')
        return False

    def assert_stale_firing_refused(self,app,*,merged=False):
        command=('from scripts.native_firing_candidate_smoke import merged_sources; merged_sources()'
                 if merged else
                 'from scripts.native_firing_runtime_candidate import load_candidate; load_candidate("runtime")')
        probe=subprocess.run([sys.executable,'-c',command],
            cwd=app,capture_output=True,text=True,timeout=30)
        self.assertEqual(probe.returncode,1,probe.stdout+'\n'+probe.stderr)
        self.assertEqual(probe.stderr.strip().splitlines()[-1],
            'ValueError: Live sources differ from complete baseline/candidate')

    def source_handoff_applicable(self,app):
        """Only execute the 2026-10-11 frozen cohort against its exact source.

        Stale live Runtime is not the original experiment. A damaged archived
        baseline is a different error and must never be silently skipped.
        """
        probe=subprocess.run([sys.executable,'-c',
            'from scripts.source_handoff_candidate import sources; sources()'],
            cwd=app,capture_output=True,text=True,timeout=30)
        if probe.returncode==0:return True
        self.assertEqual(probe.returncode,1,probe.stdout+'\n'+probe.stderr)
        self.assertEqual(probe.stderr.strip().splitlines()[-1],
            'ValueError: Runtime is neither exact frozen baseline nor complete reviewed candidate')
        return False

    def assert_stale_source_handoff_refused(self,app):
        for command in (
            'from scripts.source_handoff_candidate import load_candidate; load_candidate("cognition")',
            'from scripts.source_handoff_ablation import arm_sources; arm_sources()',
        ):
            probe=subprocess.run([sys.executable,'-c',command],
                cwd=app,capture_output=True,text=True,timeout=30)
            self.assertEqual(probe.returncode,1,probe.stdout+'\n'+probe.stderr)
            self.assertEqual(probe.stderr.strip().splitlines()[-1],
                'ValueError: Runtime is neither exact frozen baseline nor complete reviewed candidate')

    def test_actual_phone_zip_runs_source_handoff_regressions_after_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'phone.zip'
            completed=self.package(ROOT,out,phone=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.inspect(out)
            with zipfile.ZipFile(out) as archive:archive.extractall(root/'extracted')
            app=root/'extracted/V13-Phone'
            if self.source_handoff_applicable(app):
                tested=subprocess.run([sys.executable,'-m','unittest',
                    'tests.test_source_handoff_candidate',
                    'tests.test_source_handoff_ablation'],
                    cwd=app,capture_output=True,text=True,timeout=30)
                self.assertEqual(tested.returncode,0,tested.stdout+'\n'+tested.stderr)
                self.assertRegex(tested.stderr,r'Ran [1-9][0-9]* tests')
            else:
                # Preserve the original historical failure as a verified
                # refusal, rather than weakening the exact-source guard.
                self.assert_stale_source_handoff_refused(app)

    def test_historical_source_handoff_corrupt_fixture_is_not_stale(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'phone.zip'
            completed=self.package(ROOT,out,phone=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            with zipfile.ZipFile(out) as archive:archive.extractall(root/'extracted')
            app=root/'extracted/V13-Phone'
            fixture=app/'docs/proofs/continuation-20261011/source-handoff-baseline/bodyview.py'
            fixture.write_bytes(fixture.read_bytes()+b'\n# corrupted historical baseline')
            with self.assertRaises(AssertionError):
                self.source_handoff_applicable(app)

    def test_actual_phone_zip_runs_isolated_native_firing_candidate_after_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'phone.zip'
            completed=self.package(ROOT,out,phone=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.inspect(out)
            with zipfile.ZipFile(out) as archive:archive.extractall(root/'extracted')
            app=root/'extracted/V13-Phone'
            if self.native_firing_applicable(app):
                tested=subprocess.run([sys.executable,'-m','unittest',
                    'tests.test_native_firing_runtime_candidate'],cwd=app,
                    capture_output=True,text=True,timeout=30)
                self.assertEqual(tested.returncode,0,tested.stdout+'\n'+tested.stderr)
                self.assertRegex(tested.stderr,r'Ran [1-9][0-9]* tests')
            else:
                # Never run historical candidate tests against unrelated live
                # Runtime revisions; verify the original fail-closed contract.
                self.assert_stale_firing_refused(app)

    def test_actual_phone_zip_runs_approval_reader_and_merged_firing_after_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'phone.zip'
            completed=self.package(ROOT,out,phone=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            self.inspect(out)
            with zipfile.ZipFile(out) as archive:archive.extractall(root/'extracted')
            app=root/'extracted/V13-Phone'
            # Approval reader is independently fixture-bound and remains
            # runnable even when the historical merged firing path is stale.
            tested=subprocess.run([sys.executable,'-m','unittest',
                'tests.test_approval_reader_runtime_candidate'],cwd=app,
                capture_output=True,text=True,timeout=30)
            self.assertEqual(tested.returncode,0,tested.stdout+'\n'+tested.stderr)
            self.assertRegex(tested.stderr,r'Ran [1-9][0-9]* tests')
            if self.native_firing_applicable(app):
                merged=subprocess.run([sys.executable,'-m','unittest',
                    'tests.test_native_firing_merged_candidate'],cwd=app,
                    capture_output=True,text=True,timeout=30)
                self.assertEqual(merged.returncode,0,merged.stdout+'\n'+merged.stderr)
                self.assertRegex(merged.stderr,r'Ran [1-9][0-9]* tests')
            else:
                self.assert_stale_firing_refused(app,merged=True)


    def test_historical_candidate_corrupt_fixture_is_not_misclassified_as_stale(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);out=root/'phone.zip'
            completed=self.package(ROOT,out,phone=True)
            self.assertEqual(completed.returncode,0,completed.stderr)
            with zipfile.ZipFile(out) as archive:archive.extractall(root/'extracted')
            app=root/'extracted/V13-Phone'
            fixture=app/'docs/proofs/continuation-20261011/native-firing-runtime-baseline/runners.py'
            fixture.write_bytes(fixture.read_bytes()+b'\n# corruption')
            with self.assertRaises(AssertionError):
                self.native_firing_applicable(app)



if __name__=='__main__':unittest.main()
