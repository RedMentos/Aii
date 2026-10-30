"""Software-only guards for the separate real Runtime native two-turn probe."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import current_runtime_native_two_turn_20261030 as m
from scripts.step2_current_catalog_artifact_probe import git_blob_sha
from v13.common import APP


class RuntimeNativeTwoTurnGuards(unittest.TestCase):
    def test_catalog_manager_tool_schema_pins_are_exact(self):
        for name, expected in (
            ("specs/models.json", m.CATALOG_BLOB),
            ("v13/models.py", m.MANAGER_BLOB),
            ("specs/control_tools.json", m.TOOLS_BLOB),
        ):
            self.assertEqual(git_blob_sha((APP / name).read_bytes()), expected)
        self.assertEqual(set(m.PINS), {"needle", "language", "body", "gist"})
        self.assertEqual(len(set(m.PINS.values())), 4)

    def test_existing_scratch_or_evidence_rejected_before_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(FileExistsError):
                m.preflight(root, root / "new-evidence")
            with self.assertRaises(FileExistsError):
                m.preflight(root / "new-scratch", root)

    def test_non_linux_target_refused(self):
        with patch.object(m.platform, "system", return_value="Windows"):
            with self.assertRaises(ValueError):
                m.preflight(Path("/tmp/fresh-native-scratch"), Path("/tmp/fresh-native-evidence"))

    def test_source_bound_packet_and_native_metrics_summary(self):
        packets = [
            {"kind": "OfferPacket", "payload": json.dumps(
                {"role": role, "native_metrics": {"status": "FINAL"}})}
            for role in ("B1_DETAIL", "B2_GIST")
        ]
        store = SimpleNamespace(rows=lambda *_args: packets)
        runtime = SimpleNamespace(store=store)
        metadata = {
            "model_generated": True,
            "route": {"source": "NATIVE_C2_ADVISORY",
                      "native_control": {"function_calls": [{"name": "select_processing"}]},
                      "native_control_metrics": {"status": "FINAL"}},
            "runner": {"role": "B1_DETAIL", "status": "FINAL"},
        }
        result = m._summary(runtime, "synthetic-event", {
            "status": "FINAL", "text": "synthetic output",
            "metadata": json.dumps(metadata),
        })
        self.assertTrue(result["native_c2_seen"])
        self.assertEqual(result["offer_roles"], ["B1_DETAIL", "B2_GIST"])
        self.assertEqual(result["output_runner_role"], "B1_DETAIL")
        self.assertEqual(result["answer_sha256"],
                         hashlib.sha256(b"synthetic output").hexdigest())
        self.assertFalse(result["tool_executed"])


if __name__ == "__main__":
    unittest.main()
