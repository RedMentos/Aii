import unittest
from unittest.mock import patch
from pathlib import Path

from tests.test_toolforecast import optional_restored_round8_available


class TestRun80OptionalRestoreProbe(unittest.TestCase):
    def test_permission_denied_means_optional_evidence_unavailable(self):
        with patch.object(Path, "exists", side_effect=PermissionError("root inaccessible")):
            self.assertFalse(optional_restored_round8_available())

    def test_accessible_path_retains_original_check(self):
        with patch.object(Path, "exists", return_value=True) as exists:
            self.assertTrue(optional_restored_round8_available())
            self.assertEqual(exists.call_count, 1)
        with patch.object(Path, "exists", return_value=False):
            self.assertFalse(optional_restored_round8_available())


if __name__ == "__main__":
    unittest.main()
