"""Real temporary Git repositories exercise the read-only branch audit."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/branch_content_audit_candidate.py'
spec = importlib.util.spec_from_file_location('branch_audit', SCRIPT)
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Audit Fixture')
        self.git('config', 'user.email', 'audit@example.invalid')
        (self.repo / 'shared.txt').write_text('baseline\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.git('branch', 'baseline')
        self.base = self.pin('baseline')
        (self.repo / 'shared.txt').write_text('candidate\n')
        (self.repo / 'new.txt').write_text('new\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'candidate')
        self.git('branch', 'candidate')
        self.source = self.pin('candidate')
        self.git('checkout', '-q', 'baseline')
        self.plan = {'schema': A.SCHEMA, 'baseline': self.base,
                     'packages': [dict(self.source, owner='K', paths=['shared.txt', 'new.txt'])]}

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], stderr=subprocess.DEVNULL).decode().strip()

    def pin(self, ref):
        return {'ref': ref, 'commit': self.git('rev-parse', ref), 'tree': self.git('rev-parse', ref + '^{tree}')}

    def test_missing_and_different_are_comparisons_not_completion(self):
        before = self.git('status', '--porcelain')
        result = A.audit(self.repo, self.plan)
        self.assertEqual(result['status'], 'CLEAN_SCOPED_COMPARISON')
        self.assertEqual(result['working_counts']['MISSING'], 1)
        self.assertEqual(result['working_counts']['DIFFERENT'], 1)
        self.assertEqual(result['active_thread_state'], 'NOT_OBSERVED')
        self.assertEqual(self.git('status', '--porcelain'), before)
        self.assertEqual(A.audit(self.repo, self.plan), result)

    def test_required_source_path_missing(self):
        self.plan['packages'][0]['paths'].append('absent.txt')
        result = A.audit(self.repo, self.plan)
        self.assertIn('SOURCE_PATH_MISSING', {i['kind'] for i in result['issues']})

    def test_duplicate_owner_conflict_rejected(self):
        self.plan['packages'].append(dict(self.source, owner='L', paths=['shared.txt']))
        with self.assertRaisesRegex(ValueError, 'Ownership conflict'):
            A.audit(self.repo, self.plan)

    def test_dirty_staged_and_untracked_paths_detected(self):
        (self.repo / 'shared.txt').write_text('staged\n')
        self.git('add', 'shared.txt')
        (self.repo / 'shared.txt').write_text('baseline\n')
        (self.repo / 'new.txt').write_text('untracked\n')
        result = A.audit(self.repo, self.plan)
        self.assertEqual({i['path'] for i in result['issues'] if i['kind'] == 'SCOPED_WORKTREE_DIRTY'},
                         {'shared.txt', 'new.txt'})

    def test_moved_ref_does_not_change_pinned_source(self):
        self.git('update-ref', 'refs/heads/candidate', self.base['commit'])
        result = A.audit(self.repo, self.plan)
        self.assertIn('REF_MOVED', {i['kind'] for i in result['issues']})
        self.assertEqual(result['files'][0]['source'], A.entry(self.repo, self.source['commit'], 'new.txt'))

    def test_tree_pin_and_unsafe_path_rejected(self):
        plan = copy.deepcopy(self.plan)
        plan['packages'][0]['tree'] = self.base['tree']
        self.assertIn('TREE_PIN_MISMATCH', {i['kind'] for i in A.audit(self.repo, plan)['issues']})
        plan['packages'][0]['paths'] = ['../escape']
        with self.assertRaisesRegex(ValueError, 'Unsafe scoped path'):
            A.audit(self.repo, plan)

    def test_cli_writes_reproducible_json(self):
        plan_file = self.repo / 'plan.json'
        output = self.repo / 'report.json'
        plan_file.write_text(json.dumps(self.plan))
        self.assertEqual(A.main(['--repo', str(self.repo), '--plan', str(plan_file), '--output', str(output)]), 0)
        first = output.read_bytes()
        A.main(['--repo', str(self.repo), '--plan', str(plan_file), '--output', str(output)])
        self.assertEqual(first, output.read_bytes())


if __name__ == '__main__':
    unittest.main()
