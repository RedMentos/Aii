"""Native restore path is optional in broad Linux software test runs."""
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests import test_toolforecast as original


class OptionalNativePathPortability(unittest.TestCase):
    def test_inaccessible_optional_native_restore_does_not_fail_software_assertions(self):
        real_exists = Path.exists

        def exists(path):
            if str(path) == '/root/native/restore/round8-note-tool-raw':
                raise PermissionError('runner cannot stat /root')
            return real_exists(path)

        with patch.dict(os.environ, {'V13_NATIVE_RESTORE_ROOT': '/root/native/restore'}):
            with patch.object(Path, 'exists', exists):
                original.CheckpointTests().test_competence_check_scores_states_not_calls()

    def test_explicit_accessible_native_restore_root_reaches_plan(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / 'round8-note-tool-raw').mkdir()
            calls = []
            fake = SimpleNamespace(plan=lambda root: calls.append(root) or {'ok': True})
            with patch.dict(os.environ, {'V13_NATIVE_RESTORE_ROOT': td}):
                result = original.optional_native_plan(fake)
            self.assertEqual(result, {'ok': True})
            self.assertEqual(calls, [td])


if __name__ == '__main__':
    unittest.main()
