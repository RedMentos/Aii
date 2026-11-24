"""Verify source-bound ContextOS in the real staged V13 tree."""
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CODE = Path(__file__).resolve().parents[1]
EXPECTED_CONTEXT = 'e4962d932294490b8f4b63a79115212a7000285290444484ec3bf7e50b243cad'


class ContextStageComposition(unittest.TestCase):
    def test_real_stage_rebinds_recall_and_preserves_sources(self):
        source = CODE / 'v13/context_os.py'
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        path = CODE / 'scripts/stage_integrated_candidate.py'
        spec = importlib.util.spec_from_file_location('context_composition_stager', path)
        stager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(stager)
        with tempfile.TemporaryDirectory(prefix='v13-context-composition-') as tmp:
            dest = Path(tmp) / 'candidate'
            manifest = stager.stage(CODE, dest)
            context = (dest / 'v13/context_os.py').read_bytes()
            recall = (dest / 'v13/context_source_recall_candidate.py').read_bytes()
            self.assertEqual(hashlib.sha256(context).hexdigest(), EXPECTED_CONTEXT)
            self.assertEqual(manifest['files_sha256']['v13/context_os.py'], EXPECTED_CONTEXT)
            self.assertEqual(recall.count(EXPECTED_CONTEXT.encode('ascii')), 1)
            env = dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1')
            checked = subprocess.run(
                [sys.executable, '-c',
                 'from v13.context_source_recall_candidate import _check_sources; _check_sources()'],
                cwd=dest, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)


if __name__ == '__main__':
    unittest.main()
