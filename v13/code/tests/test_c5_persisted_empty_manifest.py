"""C5 distinguishes no-manifest software seam from persisted empty native catalog."""
import tempfile
import unittest
from pathlib import Path

from v13.common import Unavailable
from v13.focal import ActionGate, available_model_roles
from v13.runtime import Runtime


class C5PersistedEmptyManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy("enabled", "off")

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def select(self, direct=False):
        source = self.r.store.source("Inspect this plan.", "USER")
        eid = self.r.store.event(self.r.session, "Inspect this plan.")["event_id"]
        event = {"event_id": eid, "brain_generation_id": self.r.store.generation_id,
                 "source_ref": source}
        return ActionGate(self.r.store).select(event, route="detail", direct=direct,
                                                resource_state="NORMAL")

    def test_uninitialized_manifest_preserves_original_software_seam(self):
        self.assertFalse(self.r.models.path.exists())
        self.assertIsNone(available_model_roles(self.r.models))
        self.assertEqual(self.select()["role"], "B1_DETAIL")

    def test_explicitly_persisted_empty_manifest_fails_closed(self):
        self.assertEqual(self.r.models.installed, {})
        self.r.models.save()
        self.assertTrue(self.r.models.path.is_file())
        self.assertEqual(available_model_roles(self.r.models), set())
        with self.assertRaises(Unavailable):
            self.select()
        self.assertEqual(self.select(direct=True)["role"], "SOURCE_COPY")

    def test_persisted_empty_survives_restart_and_recovers_after_c3_install(self):
        self.r.models.save()
        self.r.close()
        self.r = Runtime(self.home)
        self.assertIs(self.r.store._model_manager, self.r.models)
        self.assertEqual(available_model_roles(self.r.models), set())
        with self.assertRaises(Unavailable):
            self.select()
        self.r.models.installed = {"language": {"download_complete": True}}
        self.r.models.save()
        self.assertEqual(available_model_roles(self.r.models), {"C3_LANGUAGE"})
        self.assertEqual(self.select()["role"], "C3_LANGUAGE")

    def test_malformed_in_memory_capability_fails_closed(self):
        self.r.models.installed = ["not a model manifest"]
        self.assertEqual(available_model_roles(self.r.models), set())
        with self.assertRaises(Unavailable):
            self.select()


if __name__ == "__main__":
    unittest.main()
