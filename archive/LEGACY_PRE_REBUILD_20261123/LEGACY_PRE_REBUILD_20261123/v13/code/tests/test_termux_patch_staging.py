"""No device/network required; private synthetic agent Ed25519 key lives in tmp."""
import base64
import hashlib
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from v13.termux_patch_staging import PatchDenied, SCHEMA, verify_and_stage


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _compact(v):
    return json.dumps(v, separators=(",", ":"), sort_keys=True).encode()


@pytest.fixture
def env(tmp_path):
    installed = tmp_path / "installed"
    stage = tmp_path / "stage"
    bundle = tmp_path / "bundle"
    for p in (installed, stage, bundle / "files"):
        p.mkdir(parents=True)
    old = installed / "v13/code/v13/demo.py"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"old\n")
    new = b"new\n"
    path = bundle / "files/v13/code/v13/demo.py"
    path.parent.mkdir(parents=True)
    path.write_bytes(new)
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    trust = tmp_path / "trust.json"
    trust.write_text(json.dumps({"agents": {"agent-qa": {
        "public_key_b64": base64.b64encode(public).decode(),
        "allowed_prefixes": ["v13/code/v13/"]}}}))
    manifest = {
        "schema": SCHEMA, "agent": "agent-qa", "nonce": "9" * 32,
        "base_commit": "a" * 40, "target_commit": "b" * 40, "expires_at": 1900,
        "files": [{"path": "v13/code/v13/demo.py",
                   "before_sha256": _sha(b"old\n"),
                   "after_sha256": _sha(new), "size": len(new)}]
    }

    def sign():
        raw = _compact(manifest)
        (bundle / "manifest.json").write_bytes(raw)
        (bundle / "manifest.sig").write_bytes(private.sign(raw))

    def run():
        return verify_and_stage(bundle, trust, installed, stage,
                                installed_commit="a" * 40, now=1000)

    sign()
    return locals()


def test_stages_only_and_writes_verifiable_receipt(env):
    dest, receipt = env["run"]()
    assert receipt["status"] == "STAGED_REVIEW_ONLY_NOT_INSTALLED"
    assert receipt["agent"] == "agent-qa"
    assert receipt["patch_applied"] is False
    assert receipt["remote_listener_started"] is False
    assert receipt["android_shell_exposed"] is False
    assert (dest / "files/v13/code/v13/demo.py").read_bytes() == b"new\n"
    assert (env["installed"] / "v13/code/v13/demo.py").read_bytes() == b"old\n"
    assert json.loads((dest / "receipt.json").read_text()) == receipt
    assert dest.stat().st_mode & 0o777 == 0o700


def test_signed_new_file_supported_but_only_scoped(env):
    m = env["manifest"]
    new = b"# an optional scratch module\n"
    rel = "v13/code/v13/added.py"
    p = env["bundle"] / "files" / rel
    p.write_bytes(new)
    m["files"].append({"path": rel, "before_sha256": None,
                       "after_sha256": _sha(new), "size": len(new)})
    env["sign"]()
    dest, r = env["run"]()
    assert len(r["files"]) == 2
    assert (dest / "files" / rel).read_bytes() == new
    assert not (env["installed"] / rel).exists()


def test_invalid_signature_and_wrong_agent_public_key_rejected(env):
    (env["bundle"] / "manifest.sig").write_bytes(b"0" * 64)
    with pytest.raises(PatchDenied, match="signature"):
        env["run"]()
    env["sign"]()
    env["manifest"]["agent"] = "unauthorized-agent"
    env["sign"]()
    with pytest.raises(PatchDenied, match="not trusted"):
        env["run"]()


@pytest.mark.parametrize("changed,value,match", [
    ("expires_at", 900, "expired"),
    ("expires_at", 9000, "distant"),
    ("base_commit", "f" * 40, "stale"),
    ("target_commit", "a" * 40, "stale"),
    ("nonce", "../../etc/passwd", "nonce"),
    ("files", [], "count"),
])
def test_rejects_invalid_signed_metadata(env, changed, value, match):
    env["manifest"][changed] = value
    env["sign"]()
    with pytest.raises(PatchDenied, match=match):
        env["run"]()


@pytest.mark.parametrize("path", [
    "../escape.py", "v13/code/v13/../../escape.py",
    "v13/code/v13/evil.sh", "/v13/code/v13/evil.py",
    "v13/code/v13/\u00f0.py", "v13/code/v13//bad.py",
    "v13/code/other/demo.py",
])
def test_rejects_signed_nonallowlisted_paths_before_read(env, path):
    env["manifest"]["files"][0]["path"] = path
    env["sign"]()
    with pytest.raises(PatchDenied, match="allowlist"):
        env["run"]()


def test_modified_content_and_installed_preimage_rejected(env):
    p = env["bundle"] / "files/v13/code/v13/demo.py"
    p.write_bytes(b"evil")
    with pytest.raises(PatchDenied, match="checksum mismatch"):
        env["run"]()
    p.write_bytes(b"new\n")
    (env["installed"] / "v13/code/v13/demo.py").write_bytes(b"not-old")
    with pytest.raises(PatchDenied, match="installed tree differs"):
        env["run"]()


def test_symlink_payload_rejected(env):
    p = env["bundle"] / "files/v13/code/v13/demo.py"
    p.unlink()
    p.symlink_to(env["installed"] / "v13/code/v13/demo.py")
    with pytest.raises(PatchDenied, match="symlink"):
        env["run"]()


def test_duplicate_signed_paths_rejected(env):
    env["manifest"]["files"].append(dict(env["manifest"]["files"][0]))
    env["sign"]()
    with pytest.raises(PatchDenied, match="duplicate"):
        env["run"]()


def test_unsigned_keyring_cannot_grant_agent_new_path_scope(env):
    env["manifest"]["files"][0]["path"] = "v13/code/docs/note.md"
    env["sign"]()
    with pytest.raises(PatchDenied, match="outside its scope"):
        env["run"]()


def test_duplicate_json_keys_rejected_even_when_signed(env):
    raw = b'{"schema":"bad","schema":"' + SCHEMA.encode() + b'"}'
    (env["bundle"] / "manifest.json").write_bytes(raw)
    (env["bundle"] / "manifest.sig").write_bytes(env["private"].sign(raw))
    with pytest.raises(PatchDenied, match="duplicate"):
        env["run"]()
