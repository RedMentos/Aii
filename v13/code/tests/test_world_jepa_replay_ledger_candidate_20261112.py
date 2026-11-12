"""Cursor/optimizer receipt crash, CAS, source and restart regressions."""
import hashlib
import pytest
from v13.world_jepa_replay_ledger_candidate import ReplayLedger

SOURCE = hashlib.sha256(b"trusted-t8-fixture").hexdigest()

def test_restart_source_cas_and_checkpoint_integrity(tmp_path):
    path = tmp_path / "cursor.sqlite"
    checkpoint = tmp_path / "optimizer.npz"
    checkpoint.write_bytes(b"trained-weights-1")
    ledger = ReplayLedger(path)
    assert ledger.read("t8", SOURCE, checkpoint) is None
    with pytest.raises(ValueError, match="CHECKPOINT_REQUIRED"):
        ledger.commit("other", SOURCE, 0, 1, tmp_path / "missing")
    assert ledger.read("other", SOURCE, checkpoint) is None
    first = ledger.commit("t8", SOURCE, 0, 4, checkpoint)
    assert first["revision"] == 1
    with pytest.raises(ValueError, match="CURSOR_CAS"):
        ledger.commit("t8", SOURCE, 0, 8, checkpoint)
    ledger.close()
    reopened = ReplayLedger(path)
    assert reopened.read("t8", SOURCE, checkpoint)["cursor"] == 4
    checkpoint.write_bytes(b"trained-weights-2")
    with pytest.raises(ValueError, match="CHECKPOINT_MISMATCH"):
        reopened.read("t8", SOURCE, checkpoint)
    with pytest.raises(ValueError, match="SOURCE"):
        reopened.read("t8", hashlib.sha256(b"other").hexdigest(), checkpoint)
    second = reopened.commit("t8", SOURCE, 4, 8, checkpoint)
    assert second["revision"] == 2
    assert reopened.read("t8", SOURCE, checkpoint)["cursor"] == 8
    reopened.close()

def test_no_advance_on_invalid_checkpoint_or_source(tmp_path):
    checkpoint = tmp_path / "weights.npz"
    checkpoint.write_bytes(b"initial")
    ledger = ReplayLedger(tmp_path / "cursor.sqlite")
    ledger.commit("t8", SOURCE, 0, 2, checkpoint)
    with pytest.raises(ValueError, match="CURSOR_CAS_OR_SOURCE"):
        ledger.commit("t8", hashlib.sha256(b"wrong").hexdigest(), 2, 3, checkpoint)
    with pytest.raises(ValueError, match="INVALID_REPLAY"):
        ledger.commit("t8", SOURCE, 2, 2, checkpoint)
    assert ledger.read("t8", SOURCE, checkpoint)["cursor"] == 2
    ledger.close()
