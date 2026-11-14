"""Model-free V13 private remote bridge security/recovery tests."""
import json
import os
from pathlib import Path
import hashlib
import stat

import pytest

from v13 import remote_maintenance_bridge as m


@pytest.fixture
def env(tmp_path):
    source = tmp_path / "source"
    state = tmp_path / "state"
    stage = tmp_path / "stage"
    source.mkdir()
    stage.mkdir()
    status = tmp_path / "live-status.json"
    cfg = {
        "relay_repo": "Example/private-v13-relay",
        "source_repo": "RedMentos/Aii",
        "installed_root": str(source),
        "installed_commit": "a" * 40,
        "staging_root": str(stage),
        "state_dir": str(state),
        "status_file": str(status),
        "keys": {"agent-qa": "2a" * 32},
        "permissions": {"agent-qa": ["HEALTH", "LEARNING_STATUS", "PATCH_STAGE", "PATCH_APPLY"]},
        "authors": {"agent-qa": ["TrustedUser"]},
        "apply_paths": ["v13/code/v13/demo.py"],
        "remote_apply_enabled": False,
        "poll_seconds": 60,
    }
    cfgfile = tmp_path / "bridge-config.json"
    cfgfile.write_text(json.dumps(cfg))
    cfgfile.chmod(0o600)
    return locals()


class FakeGitHub:
    def __init__(self, issues):
        self.queue = issues
        self.comments_sent = []
        self.closed = []
        self.checks = 0

    def check_private(self):
        self.checks += 1
        return True

    def issues(self):
        return [i for i in self.queue if i["number"] not in self.closed]

    def comment(self, number, receipt):
        self.comments_sent.append((number, receipt))

    def close(self, number):
        self.closed.append(number)


def issue(cmd, number=1, author="TrustedUser"):
    return {"number": number, "title": "V13CMD:" + cmd["id"], "body": m.canonical(cmd).decode(),
            "user": {"login": author}}


def command(e, command="HEALTH", request_id="c" * 32, args=None):
    return m.make_command("agent-qa", command, args or {}, e["cfg"]["keys"]["agent-qa"],
                          now=1000, request_id=request_id)


def test_command_auth_integrity_scope_and_expiry(env):
    c = command(env)
    p = env["cfg"]
    assert m.verify_command(c, p["keys"], p["permissions"], p["authors"],
                            author="TrustedUser", now=1002)["command"] == "HEALTH"
    for bad in (dict(c, command="PATCH_STAGE"), dict(c, id="e" * 32),
                dict(c, args={"shell": "echo hi"}), dict(c, mac="0" * 64)):
        with pytest.raises(m.Denied):
            m.verify_command(bad, p["keys"], p["permissions"], p["authors"],
                             author="TrustedUser", now=1002)
    with pytest.raises(m.Denied):
        m.verify_command(c, p["keys"], p["permissions"], p["authors"],
                         author="OtherUser", now=1002)
    with pytest.raises(m.Denied):
        m.verify_command(c, p["keys"], p["permissions"], p["authors"],
                         author="TrustedUser", now=1900)


def test_config_permission_and_no_remote_apply_by_default(env):
    assert m.private_config(env["cfgfile"])["remote_apply_enabled"] is False
    env["cfgfile"].chmod(0o644)
    with pytest.raises(m.Denied, match="chmod 600"):
        m.private_config(env["cfgfile"])
    env["cfgfile"].chmod(0o600)
    env["cfg"]["remote_apply_enabled"] = True
    env["cfg"]["apply_paths"] = []
    env["cfgfile"].write_text(json.dumps(env["cfg"]))
    with pytest.raises(m.Denied, match="allowlist"):
        m.private_config(env["cfgfile"])


def test_process_private_command_receipt_and_persistent_replay(env, monkeypatch):
    cmd = command(env)
    github = FakeGitHub([issue(cmd)])
    monkeypatch.setattr(m.time, "time", lambda: 1001)
    first = m.poll_once(github, env["cfg"])
    assert first == {"status": "POLL_OK", "processed": 1}
    assert github.checks == 1
    assert github.comments_sent[0][1]["device_status"]["status"] == "OK"
    assert github.closed == [1]
    github.closed.clear()  # emulate failed closing after receipt committed
    second = m.poll_once(github, env["cfg"])
    assert second["processed"] == 1
    assert len(github.comments_sent) == 1  # not resent


def test_bad_commands_not_responded_to(env, monkeypatch):
    cmd = command(env)
    issues = [issue(cmd, 1, "Impostor"), issue(dict(cmd, mac="0" * 64), 2),
              {**issue(cmd, 3), "body": "{nope}"}]
    github = FakeGitHub(issues)
    monkeypatch.setattr(m.time, "time", lambda: 1001)
    assert m.poll_once(github, env["cfg"])["processed"] == 0
    assert not github.comments_sent


def test_stop_marker_is_local_and_survives_restart(env, monkeypatch):
    github = FakeGitHub([issue(command(env))])
    monkeypatch.setattr(m.time, "time", lambda: 1001)
    Path(env["cfg"]["state_dir"]).mkdir(mode=0o700)
    (Path(env["cfg"]["state_dir"]) / "STOP").touch()
    assert m.poll_once(github, env["cfg"])["status"] == "STOPPED_LOCALLY"
    assert not github.comments_sent


def test_interrupted_job_never_reexecutes(env, monkeypatch):
    cmd = command(env, "HEALTH")
    gh = FakeGitHub([issue(cmd)])
    monkeypatch.setattr(m.time, "time", lambda: 1001)
    with m.local_lock(env["cfg"]["state_dir"]) as state:
        with m.database(state) as db:
            db.execute("INSERT INTO events(issue,request_id) VALUES(?,?)", (1, cmd["id"]))
            db.commit()
    monkeypatch.setattr(m, "execute", lambda *a: (_ for _ in ()).throw(AssertionError("replayed")))
    assert m.poll_once(gh, env["cfg"])["processed"] == 1
    assert gh.comments_sent[0][1]["device_status"]["status"] == "INTERRUPTED_NO_RETRY"


def test_trusted_live_status_filters_unstructured_private_text(env):
    env["status"].write_text(json.dumps({
        "learning_mode": "RECORD_ONLY", "runtime_mode": "ACTIVE", "queue_depth": 2,
        "world_steps": 7, "last_error_code": "C3_TIMEOUT",
        "private_chat": "sensitive user content", "password": "secret123",
        "organ_status": {"B1": "OK", "malicious": "secret", "C3": "UNAVAILABLE"}}))
    data = m._trusted_status(str(env["status"]))
    assert data["learning_mode"] == "RECORD_ONLY"
    assert data["organ_status"] == {"B1": "OK", "C3": "UNAVAILABLE"}
    assert "sensitive" not in json.dumps(data)
    assert "password" not in json.dumps(data)


def test_no_status_is_not_faked_learning_proof(env):
    assert m._trusted_status(str(env["status"])) == {"state": "UNAVAILABLE"}
    assert m._trusted_status(None) == {"state": "UNINSTRUMENTED"}


def test_patch_strict_scope_and_static_syntax(env):
    e = env
    cfg = e["cfg"]
    path = "v13/code/v13/demo.py"
    live = e["source"] / path
    live.parent.mkdir(parents=True)
    live.write_bytes(b"x=1\n")
    new = e["stage"] / "staged/files" / path
    new.parent.mkdir(parents=True)
    new.write_bytes(b"x=2\n")
    rec = {"files": [{"path": path, "before_sha256": m.sha(b"x=1\n"),
                      "after_sha256": m.sha(b"x=2\n")} ]}
    with pytest.raises(m.Denied, match="disabled"):
        m.apply_one_staged(cfg, e["stage"] / "staged", rec, "d" * 32)
    cfg["remote_apply_enabled"] = True
    result = m.apply_one_staged(cfg, e["stage"] / "staged", rec, "d" * 32)
    assert result["status"] == "APPLIED_SOURCE_RESTART_REQUIRED"
    assert live.read_bytes() == b"x=2\n"
    assert (e["state"] / "backups" / ("d" * 32 + ".original")).read_bytes() == b"x=1\n"
    assert result["live_process_reloaded"] is False
    # Replay cannot apply because preimage differs (and backup collides).
    with pytest.raises(m.Denied):
        m.apply_one_staged(cfg, e["stage"] / "staged", rec, "d" * 32)


def test_reject_syntax_bad_patch(env):
    cfg = env["cfg"]
    cfg["remote_apply_enabled"] = True
    path = "v13/code/v13/demo.py"
    live = env["source"] / path
    live.parent.mkdir(parents=True)
    live.write_bytes(b"x=1\n")
    new = env["stage"] / "staged/files" / path
    new.parent.mkdir(parents=True)
    new.write_bytes(b"this is syntax error !\n")
    rec = {"files": [{"path": path, "before_sha256": m.sha(live.read_bytes()),
                      "after_sha256": m.sha(new.read_bytes())}]}
    with pytest.raises(SyntaxError):
        m.apply_one_staged(cfg, env["stage"] / "staged", rec, "e" * 32)
    assert live.read_bytes() == b"x=1\n"


def test_patch_fetched_from_exact_private_commit_and_public_source(env, monkeypatch):
    # Integration contract without network or private keys.
    from v13 import termux_patch_staging as stager
    cfg = env["cfg"]
    cfg["trust_file"] = str(env["stage"] / "trust.json")
    Path(cfg["trust_file"]).write_text("{}")
    source_path = "v13/code/v13/demo.py"
    old, new = b"v=1\n", b"v=2\n"
    installed = env["source"] / source_path
    installed.parent.mkdir(parents=True)
    installed.write_bytes(old)
    manifest = {"schema": stager.SCHEMA, "agent": "agent-qa", "nonce": "9" * 32,
                "base_commit": "a" * 40, "target_commit": "b" * 40,
                "expires_at": int(m.time.time()) + 600,
                "files": [{"path": source_path, "before_sha256": m.sha(old),
                           "after_sha256": m.sha(new), "size": len(new)}]}
    class FakeContents:
        def __init__(self, incompatible=False):
            self.incompatible = incompatible
            self.commits = []
        def commit_exists(self, repo, commit):
            self.commits.append((repo, commit))
        def content(self, repo, commit, path):
            if path.endswith("manifest.json"):
                return m.canonical(manifest)
            if path.endswith("manifest.sig"):
                return b"0" * 64
            if repo == "RedMentos/Aii" and self.incompatible:
                return b"malicious\n"
            return new
    monkeypatch.setattr(stager, "verify_and_stage", lambda *args, **kwargs:
                        (env["stage"] / "record", {"manifest_sha256": m.sha(m.canonical(manifest)),
                                                     "files": [{"path": source_path}]}))
    mock = FakeContents()
    dest, receipt = m.download_and_stage(mock, cfg, {"patch_commit": "c" * 40,
                                                      "patch_id": "d" * 32})
    assert mock.commits == [(cfg["relay_repo"], "c" * 40), (cfg["source_repo"], "b" * 40)]
    assert receipt["files"] == [{"path": source_path}]
    with pytest.raises(m.Denied, match="disagrees"):
        m.download_and_stage(FakeContents(incompatible=True), cfg,
                             {"patch_commit": "c" * 40, "patch_id": "d" * 32})


def test_duplicate_json_and_random_path_invalid():
    with pytest.raises(m.Denied):
        m.strict_json(b'{"a":1,"a":2}')
    with pytest.raises(m.Denied):
        m.make_command("agent-qa", "SHELL", {}, "2a" * 32)
    gh = m.GitHub("mock-token", "x/private")
    with pytest.raises(m.Denied):
        gh.content("x/private", "a" * 40, "../secrets")


def test_local_rollback_exact_source_only(env):
    cfg = env["cfg"]
    cfg["remote_apply_enabled"] = True
    path = "v13/code/v13/demo.py"
    live = env["source"] / path
    live.parent.mkdir(parents=True)
    live.write_bytes(b"x = 1\n")
    changed = env["stage"] / "staged/files" / path
    changed.parent.mkdir(parents=True)
    changed.write_bytes(b"x = 2\n")
    r = {"files": [{"path": path, "before_sha256": m.sha(live.read_bytes()),
                    "after_sha256": m.sha(changed.read_bytes())}]}
    req = "4" * 32
    m.apply_one_staged(cfg, env["stage"] / "staged", r, req)
    out = m.rollback_local_source(cfg, req)
    assert out["status"] == "ROLLED_BACK_SOURCE_RESTART_REQUIRED"
    assert live.read_bytes() == b"x = 1\n"
    with pytest.raises(m.Denied):
        m.rollback_local_source(cfg, req)  # can't rollback a now-changed postimage


def test_publisher_uses_pinned_base_target_and_ed25519_signature(env, tmp_path, monkeypatch):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from v13 import termux_patch_staging as stager
    from cryptography.hazmat.primitives import serialization
    key = Ed25519PrivateKey.generate()
    path = tmp_path / "private.raw"
    path.write_bytes(key.private_bytes(serialization.Encoding.Raw,
                                      serialization.PrivateFormat.Raw,
                                      serialization.NoEncryption()))
    path.chmod(0o600)
    source_path = "v13/code/v13/example.py"
    class FakeClient:
        def __init__(self):
            self.stored = {}
            self.checks = []
        def check_private(self):
            self.checks.append("private")
        def commit_exists(self, repo, sha):
            self.checks.append((repo, sha))
        def content(self, repo, ref, rel):
            return b"x = 1\n" if ref == "a" * 40 else b"x = 2\n"
        def put_content(self, path, data, msg):
            self.stored[path] = data
            return "c" * 40
    gh = FakeClient()
    result = m.publish_one_patch(gh, "RedMentos/Aii", "agent-qa",
                                 "a" * 40, "b" * 40, source_path, str(path),
                                 now=1000, patch_id="f" * 32)
    assert result["patch_commit"] == "c" * 40
    assert result["device_updated"] is False
    manifest = gh.stored["patches/" + "f" * 32 + "/manifest.json"]
    signature = gh.stored["patches/" + "f" * 32 + "/manifest.sig"]
    key.public_key().verify(signature, manifest)
    obj = m.strict_json(manifest)
    assert obj["base_commit"] == "a" * 40
    assert obj["target_commit"] == "b" * 40
    assert obj["files"][0]["after_sha256"] == m.sha(b"x = 2\n")


def test_stale_status_file_not_advertised_as_live(env):
    env["status"].write_text('{"learning_mode":"ACTIVE","world_steps":999}')
    os.utime(env["status"], (m.time.time() - 500, m.time.time() - 500))
    assert m._trusted_status(str(env["status"])) == {"state": "STALE_NO_LIVE_PROOF"}


def test_repository_privacy_rejection_cannot_be_bypassed():
    gh = m.GitHub("opaque-dev-token", "Owner/remote")
    gh.request = lambda *a, **k: {"private": False, "full_name": "Owner/remote"}
    with pytest.raises(m.Denied, match="PRIVATE"):
        gh.check_private()
    gh.request = lambda *a, **k: {"private": True, "full_name": "Owner/remote"}
    assert gh.check_private() is True


def test_keygen_private_key_not_printed(tmp_path, capsys):
    keypath = tmp_path / "developer.key"
    m.cli(["keygen", "--out", str(keypath)])
    result = json.loads(capsys.readouterr().out)
    assert result["private_key_written"] == str(keypath)
    assert len(keypath.read_bytes()) == 32
    assert keypath.stat().st_mode & 0o077 == 0
    assert "private_key_b64" not in result
    with pytest.raises(FileExistsError):
        m.cli(["keygen", "--out", str(keypath)])


def test_private_relay_token_not_forwarded_to_public_source(monkeypatch):
    gh = m.GitHub("private-secret-token", "Owner/private")
    requests = []
    class Response:
        headers = {"Content-Length": "2"}
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def read(self, n): return b"{}"
    class Opener:
        def open(self, req, timeout=None):
            requests.append(req)
            return Response()
    monkeypatch.setattr(m.urllib.request, "build_opener", lambda *a: Opener())
    gh.request("GET", "/repos/RedMentos/Aii/commits/" + "a" * 40)
    gh.request("GET", "/repos/Owner/private")
    assert "Authorization" not in requests[0].headers
    assert requests[1].get_header("Authorization") == "Bearer private-secret-token"
    with pytest.raises(m.Denied):
        gh.request("POST", "/repos/Other/repo/issues", {"title": "no"})