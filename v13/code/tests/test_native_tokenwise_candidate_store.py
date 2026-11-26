import importlib.util
import json
from pathlib import Path
import stat
import sys
import time
import types

import pytest

from v13.native_tokenwise_candidate_store import CandidateStore, CandidateStoreError


def _pairing_fixture_module():
    path = Path(__file__).with_name("test_native_tokenwise_pairing.py")
    spec = importlib.util.spec_from_file_location("_v14_tokenwise_pairing_fixture", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _candidate():
    pairing = _pairing_fixture_module()
    records = [
        pairing.native_record(i, f"train-session-{i // 2}") for i in range(8)
    ] + [
        pairing.native_record(i, f"holdout-session-{(i - 8) // 2}")
        for i in range(8, 12)
    ]
    fitted = pairing.fit_adapter_from_native_pair_records(
        records,
        train_session_ids=[
            "train-session-0", "train-session-1",
            "train-session-2", "train-session-3",
        ],
        holdout_session_ids=["holdout-session-0", "holdout-session-1"],
        rank=2,
        ridge=1e-5,
        min_relative_improvement=0.0,
    )
    return {
        "adapter": fitted["adapter"],
        "fit_manifest": fitted["fit_manifest"],
        "record": records[8],
    }


def test_candidate_checkpoint_roundtrip_persists_weights_only_and_is_private(tmp_path):
    candidate = _candidate()
    store = CandidateStore(tmp_path)
    saved = store.save(candidate)

    assert saved["status"] == "SAVED"
    assert saved["candidate_id"] == candidate["adapter"]["adapter_sha256"]
    assert saved["record_persisted"] is False
    assert saved["pair_vectors_persisted"] is False
    assert saved["source_text_persisted"] is False
    assert saved["token_ids_persisted"] is False
    assert saved["production_route"] is False
    assert saved["training_authority"] == saved["native_receiver_authority"] == 0

    root = tmp_path / "data" / "callosum" / "tokenwise_candidates"
    directory = root / saved["candidate_id"]
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    assert {item.name for item in directory.iterdir()} == {"adapter.v14lat", "manifest.json"}
    assert stat.S_IMODE((directory / "adapter.v14lat").stat().st_mode) == 0o600
    assert stat.S_IMODE((directory / "manifest.json").stat().st_mode) == 0o600

    manifest = json.loads((directory / "manifest.json").read_text())
    encoded = json.dumps(manifest, sort_keys=True)
    for forbidden in ("source_text", "sender_content_token_pieces", "receiver_content_token_pieces", "vectors", "pairs", "token_ids"):
        assert forbidden not in encoded

    restarted = CandidateStore(tmp_path).load(saved["candidate_id"][:16])
    assert restarted["adapter"]["adapter_sha256"] == saved["candidate_id"]
    assert restarted["fit_manifest"]["manifest_sha256"] == candidate["fit_manifest"]["manifest_sha256"]
    assert "record" not in restarted
    listed = store.list()
    assert len(listed) == 1
    assert listed[0]["candidate_id"] == saved["candidate_id"]
    assert listed[0]["sender_role"] == "B1_DETAIL"
    assert listed[0]["receiver_role"] == "C3_LANGUAGE"
    assert listed[0]["checkpoint_present"] is True


def test_candidate_checkpoint_rejects_manifest_and_weight_tampering(tmp_path):
    candidate = _candidate()
    store = CandidateStore(tmp_path)
    saved = store.save(candidate)
    directory = tmp_path / "data" / "callosum" / "tokenwise_candidates" / saved["candidate_id"]
    manifest_path = directory / "manifest.json"

    manifest = json.loads(manifest_path.read_text())
    manifest["production_route"] = True
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    with pytest.raises(CandidateStoreError, match="manifest digest mismatch"):
        store.load(saved["candidate_id"])

    manifest = json.loads(json.dumps({
        "schema": "v14.native-tokenwise-candidate-checkpoint/1",
        "adapter_sha256": saved["candidate_id"],
        "adapter_file_sha256": saved["adapter_file_sha256"],
        "fit_manifest": candidate["fit_manifest"],
        "sender_role": candidate["adapter"]["sender_role"],
        "receiver_role": candidate["adapter"]["receiver_role"],
        "rank": candidate["adapter"]["rank"],
        "created_at": saved["created_at"],
        "record_persisted": False,
        "pair_vectors_persisted": False,
        "source_text_persisted": False,
        "token_ids_persisted": False,
        "production_route": False,
        "semantic_use_proven": False,
        "training_authority": 0,
        "native_receiver_authority": 0,
    }))
    from v13.native_tokenwise_candidate_store import _canonical_sha
    manifest["manifest_sha256"] = _canonical_sha(manifest)
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    adapter_path = directory / "adapter.v14lat"
    payload = bytearray(adapter_path.read_bytes())
    payload[-1] ^= 0x01
    adapter_path.write_bytes(payload)
    with pytest.raises(CandidateStoreError, match="file digest mismatch"):
        store.load(saved["candidate_id"])


def test_candidate_checkpoint_requires_in_memory_pair_record_to_save(tmp_path):
    candidate = _candidate()
    candidate["record"] = None
    with pytest.raises(CandidateStoreError, match="in-memory held-out record"):
        CandidateStore(tmp_path).save(candidate)


def test_loaded_candidate_requires_fresh_matching_pair_record_before_native_probe(monkeypatch, tmp_path):
    from v13 import callosum, native_probe_approval as approval

    monkeypatch.setattr(approval, "_require_local_tty", lambda: None)
    candidate = _candidate()

    class Store:
        def __init__(self):
            self.values = {}
        def state(self, key, default=None):
            return self.values.get(key, default), 0
        def set_state(self, key, value, expected=None):
            self.values[key] = value
            return 1

    class Runtime:
        def __init__(self):
            self.home = tmp_path
            self.store = Store()
            self.session = candidate["record"]["session_id"]
            self._native_tokenwise_candidate = candidate
            self._native_tokenwise_pair_records = []
        def require_idle(self):
            return True

    runtime = Runtime()
    save_result = json.loads(callosum.operator_command(runtime, ["save-tokenwise-candidate", "--confirm"]))
    assert save_result["status"] == "SAVED"

    runtime._native_tokenwise_candidate = None
    load_result = json.loads(callosum.operator_command(
        runtime, ["load-tokenwise-candidate", save_result["candidate_id"][:16], "--confirm"]
    ))
    assert load_result["status"] == "LOADED_DIAGNOSTIC_CANDIDATE"
    assert runtime._native_tokenwise_candidate["record"] is None

    with pytest.raises(ValueError, match="fresh matching in-memory source-bound pair record"):
        callosum.operator_command(runtime, ["native-tokenwise-probe", "--confirm"])

    record = candidate["record"]
    runtime._native_tokenwise_pair_records = [record]
    runtime.store.values[approval.KEY] = {
        "schema": approval.SCHEMA,
        "status": "PENDING",
        "probe_kind": "NATIVE_RECEIVER",
        "sender_role": record["sender"]["role"],
        "receiver_role": record["receiver"]["role"],
        "session_id": record["session_id"],
        "event_id": record["event_id"],
        "brain_generation_id": record["brain_generation_id"],
        "source_ref": record["source_ref"],
        "expires_at": time.time() + 60,
    }
    observed = {}
    fake_probe = types.ModuleType("v13.native_tokenwise_receiver_probe")
    def probe(runtime_arg, adapter_arg, record_arg):
        observed.update(runtime=runtime_arg, adapter=adapter_arg, record=record_arg)
        return {"status": "DIAGNOSTIC_COMPLETE", "training_authority": 0, "native_receiver_authority": 0}
    fake_probe.probe_native_tokenwise_candidate = probe
    monkeypatch.setitem(sys.modules, "v13.native_tokenwise_receiver_probe", fake_probe)

    result = json.loads(callosum.operator_command(runtime, ["native-tokenwise-probe", "--confirm"]))
    assert result["status"] == "DIAGNOSTIC_COMPLETE"
    assert observed["runtime"] is runtime
    assert observed["record"] is record
    assert observed["adapter"]["adapter_sha256"] == save_result["candidate_id"]
    assert runtime._native_tokenwise_candidate is None
    assert runtime._native_tokenwise_pair_records == []
