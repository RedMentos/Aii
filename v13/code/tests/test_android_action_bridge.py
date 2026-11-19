import unittest
from v13.android_action_bridge import dispatch_approved


class Broker:
    def __init__(self): self.used = False
    def execute(self, aid, *, dry_run):
        if self.used: raise PermissionError("replay")
        assert dry_run is True
        self.used = True
        return {"action_id": aid, "capability": "back", "args": {}, "status": "DRY_RUN_ONLY"}


class Fake:
    def perform(self, command):
        return {"status": "OBSERVED", "revision": "fake-1", "evidence_ref": "sim:1"}


class Tests(unittest.TestCase):
    def test_no_companion(self):
        p = dispatch_approved(Broker(), "a", source_ref="turn:1")
        self.assertEqual(p.status, "DRY_RUN_ONLY")
        self.assertFalse(p.packet()["model_weight_authority"])

    def test_simulation(self):
        p = dispatch_approved(Broker(), "a", source_ref="turn:1", companion=Fake())
        self.assertEqual(p.status, "SIMULATED_OBSERVED")
        self.assertEqual(p.evidence_ref, "sim:1")

    def test_no_live(self):
        b = Broker()
        with self.assertRaises(PermissionError):
            dispatch_approved(b, "a", source_ref="turn:1", dry_run=False, companion=Fake())
        self.assertFalse(b.used)

    def test_no_replay(self):
        b = Broker()
        dispatch_approved(b, "a", source_ref="turn:1")
        with self.assertRaises(PermissionError):
            dispatch_approved(b, "a", source_ref="turn:1")

    def test_source_required_before_consumption(self):
        b = Broker()
        with self.assertRaises(ValueError):
            dispatch_approved(b, "a", source_ref="")
        self.assertFalse(b.used)

    def test_malformed_companion(self):
        class Bad:
            def perform(self, command): return {"status": "NATIVE_SUCCESS"}
        p = dispatch_approved(Broker(), "a", source_ref="turn:1", companion=Bad())
        self.assertEqual(p.status, "SIMULATED_FAILED")


    def test_real_broker_approval_and_stop(self):
        from v13.android_control import AndroidControlBroker, ControlDenied
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            broker = AndroidControlBroker(Path(d) / "control.sqlite3")
            try:
                broker.start()
                proposal = broker.propose("back", {})
                with self.assertRaises(ControlDenied):
                    dispatch_approved(broker, proposal.action_id, source_ref="turn:1")
                # Failed dispatch does not grant authority. A new explicit
                # local approval is required; no model-generated approval.
                proposal = broker.propose("back", {})
                broker.approve(proposal.action_id, confirmed_by_local_ui=True)
                result = dispatch_approved(broker, proposal.action_id, source_ref="turn:1", companion=Fake())
                self.assertEqual(result.status, "SIMULATED_OBSERVED")
                with self.assertRaises(ControlDenied):
                    dispatch_approved(broker, proposal.action_id, source_ref="turn:1")
                self.assertIn("dry_run", [row[1] for row in broker.events()])
            finally:
                broker.close()

if __name__ == "__main__":
    unittest.main()
