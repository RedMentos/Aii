"""Artifact hash evidence is weaker than proof of weight learning or retention."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.brain_artifact_audit import inspect
from v13.operator import Operator
from v13.store import Store


class FakeStore:
    def __init__(self, manifest, status="COMMITTED"):
        self.manifest = manifest
        self.status = status

    def generation(self):
        return self.manifest

    def one(self, sql, args):
        assert "updates" in sql and len(args) == 1
        return {"status": self.status} if args[0] == "verified-update" else None


def setup_component(tmp_path, name="output_adapter", payload=b"ADAPTER WEIGHTS 1234"):
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir(exist_ok=True)
    file = checkpoints / "private_master_abc.bin"
    file.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    rel = str(file.relative_to(tmp_path))
    entry = {"path": rel, "sha256": digest, "update_id": "verified-update"}
    return file, {"hashes": {rel: digest}, "components": {name: entry}}


def op(runtime):
    return Operator(runtime)


def dummy_runtime(tmp_path, manifest, status="COMMITTED"):
    calls = []
    def idle():
        calls.append("idle")
    return (SimpleNamespace(home=tmp_path, store=FakeStore(manifest, status=status),
                            session="chat_1", require_idle=idle), calls)


def test_hash_matched_active_artifact_does_not_prove_model_improvement(tmp_path):
    file, manifest = setup_component(tmp_path)
    rt, calls = dummy_runtime(tmp_path, manifest)
    report = json.loads(op(rt).run(":brain audit 1"))
    assert calls == ["idle"]
    assert report["sha_match_count"] == 1
    assert report["all_artifact_hashes_verified"] is True
    assert report["failed_count"] == 0
    assert report["bytes_read"] == len(file.read_bytes())
    assert report["training_retention_and_redmi_proven"] is False
    assert report["model_calls"] == 0 and report["state_mutation"] is False
    assert "private_master_abc" not in json.dumps(report)


def test_corrupted_and_uncommitted_artifacts_fail_closed(tmp_path):
    file, manifest = setup_component(tmp_path)
    rt, _ = dummy_runtime(tmp_path, manifest)
    file.write_bytes(b"ALTERED BUT VALID FILE")
    r = inspect(rt, 1)
    assert r["components"][0]["status"] == "SHA_MISMATCH"
    assert r["all_artifact_hashes_verified"] is False
    rt.store.status = "PENDING_APPROVAL"
    assert inspect(rt, 1)["components"][0]["status"] == "UPDATE_NOT_COMMITTED"


def test_path_escape_symlink_and_hardlink_do_not_read_artifacts(tmp_path):
    file, manifest = setup_component(tmp_path)
    rt, _ = dummy_runtime(tmp_path, manifest)
    external = tmp_path.parent / "outside-private-data"
    external.write_text("PRIVATE SECRET")
    file.unlink()
    file.symlink_to(external)
    report = inspect(rt, 1)
    assert report["components"][0]["status"] == "UNSAFE_PATH"
    assert "SECRET" not in json.dumps(report)
    file.unlink()
    file.hardlink_to(external)
    assert inspect(rt, 1)["components"][0]["status"] == "UNSAFE_INODE"


def test_large_artifact_is_skipped_under_budget_without_false_success(tmp_path):
    file, manifest = setup_component(tmp_path, payload=b"X" * (1024 * 1024 + 1))
    rt, _ = dummy_runtime(tmp_path, manifest)
    result = inspect(rt, budget_mib=1)
    assert result["components"][0]["status"] == "SKIPPED_BUDGET"
    assert result["skipped_count"] == 1
    assert result["sha_match_count"] == 0
    assert result["all_artifact_hashes_verified"] is False
    assert result["bytes_read"] == 0


def test_broken_binding_manifest_is_rejected_without_reading_file(tmp_path):
    file, manifest = setup_component(tmp_path)
    entry = manifest["components"]["output_adapter"]
    entry["sha256"] = "0" * 64
    rt, _ = dummy_runtime(tmp_path, manifest)
    result = inspect(rt, 1)
    assert result["components"][0]["status"] == "INVALID_BINDING"
    assert result["bytes_read"] == 0


def test_read_only_audit_real_store_and_no_promoted_components(tmp_path):
    for path in ("data", "data/db", "data/blobs"):
        (tmp_path / path).mkdir(parents=True, exist_ok=True)
    st = Store(tmp_path)
    try:
        session = st.new_session()
        calls = []
        rt = SimpleNamespace(home=tmp_path, store=st, session=session,
                             require_idle=lambda: calls.append("idle"))
        before = {table: st.rows("SELECT * FROM " + table)
                  for table in ("updates", "states", "generations", "requests")}
        result = json.loads(op(rt).run(":brain audit"))
        assert calls == ["idle"]
        assert result["sha_match_count"] == 0
        assert result["all_artifact_hashes_verified"] is False
        for table, saved in before.items():
            assert st.rows("SELECT * FROM " + table) == saved
    finally:
        st.close()


@pytest.mark.parametrize("arg", [
    ":brain audit 0", ":brain audit 129", ":brain audit wat",
    ":brain audit 1 2", ":brain audit 1.5"
])
def test_audit_validation_rejects_unbounded_or_untrusted_entry(tmp_path, arg):
    _, manifest = setup_component(tmp_path)
    rt, calls = dummy_runtime(tmp_path, manifest)
    with pytest.raises(ValueError):
        op(rt).run(arg)
    assert not calls


def test_busy_model_and_model_origin_never_trigger_disk_scan(tmp_path):
    _, manifest = setup_component(tmp_path)
    rt, calls = dummy_runtime(tmp_path, manifest)
    with pytest.raises(ValueError, match="lokale Operator"):
        op(rt).run(":brain audit 1", origin="MODEL")
    assert calls == []
    def busy():
        calls.append("busy")
        raise ValueError("native work in progress")
    rt.require_idle = busy
    with pytest.raises(ValueError, match="native work"):
        op(rt).run(":brain audit 1")
    assert calls == ["busy"]
