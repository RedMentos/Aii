from test_t8_store_authority import FakeStore, verified
from t8_temporal_bridge import TemporalT8Bridge
import pytest

def test_bridge_requires_store_verified_receipt_and_explicit_permission(tmp_path):
    store=FakeStore();good,_=verified(store)
    bridge=TemporalT8Bridge(tmp_path,learning_enabled=True)
    with pytest.raises(PermissionError):
        bridge.consume({"action_id":"forged"},{"expected_outcome":"FINAL","probability":.8,"duration_s":1.})
    result=bridge.consume(good[0],{"expected_outcome":"FINAL","probability":.8,"duration_s":1.})
    assert result["pending_optimizer"] is True
    updated=bridge.consume(good[0],{"expected_outcome":"FINAL","probability":.8,"duration_s":1.},optimizer_permission=True)
    assert updated["updated"] is True

def test_bridge_replay_from_second_instance_is_idempotent(tmp_path):
    store=FakeStore();good,_=verified(store)
    first=TemporalT8Bridge(tmp_path,learning_enabled=True)
    second=TemporalT8Bridge(tmp_path,learning_enabled=True)
    prediction={"expected_outcome":"FINAL","probability":.8,"duration_s":1.}
    assert first.consume(good[0],prediction,optimizer_permission=True)["updated"] is True
    assert second.consume(good[0],prediction,optimizer_permission=True)["duplicate"] is True
