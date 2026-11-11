"""Outbound-only PRIVATE GitHub Issues bridge for V13 Android/Termux.

The public source repository is NOT a command relay. A distinct PRIVATE GitHub
repository, token and per-agent HMAC keys are required. No HTTP listener,
arbitrary shell, remote paths, external URL fetches or private text exports.

PATCH_STAGE reuses the separate Ed25519 verifier. PATCH_APPLY additionally
requires a locally enabled exact-file allowlist, signed patch and Git blob
provenance; applies one source file with a rollback backup, not a hot model
reload, Android OS command or permission change.
"""
from __future__ import annotations

import argparse
import ast
import base64
import binascii
from contextlib import contextmanager
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

SCHEMA = "v13.private-relay.command/1"
RECEIPT_SCHEMA = "v13.private-relay.receipt/1"
REPO = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
ID = re.compile(r"[0-9a-f]{32}\Z")
KEY = re.compile(r"[0-9a-f]{64}\Z")
AGENT = re.compile(r"[a-z][a-z0-9_-]{2,39}\Z")
COMMANDS = {"HEALTH", "LEARNING_STATUS", "DIAGNOSTICS", "PATCH_STAGE", "PATCH_APPLY"}
MAX_COMMAND = 8192
MAX_REPLY = 12000
MAX_STATUS = 8192
DEFAULT_INTERVAL = 45


class Denied(ValueError):
    """Invalid authentication, permission or unsafe operation."""


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Denied("duplicate JSON field")
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Denied("nonfinite JSON")))
    except (ValueError, UnicodeError) as exc:
        raise Denied("invalid JSON") from exc


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_command(obj, keys, permissions, authors, *, author, now=None):
    if not isinstance(obj, dict) or set(obj) != {
            "schema", "id", "agent", "command", "expires_at", "args", "mac"}:
        raise Denied("invalid command schema")
    ident, agent, cmd = obj["id"], obj["agent"], obj["command"]
    if not isinstance(ident, str) or not ID.fullmatch(ident):
        raise Denied("invalid command ID")
    if not isinstance(agent, str) or not AGENT.fullmatch(agent):
        raise Denied("invalid agent")
    if cmd not in COMMANDS or cmd not in permissions.get(agent, ()):
        raise Denied("command outside agent permissions")
    if author not in authors.get(agent, ()):
        raise Denied("untrusted GitHub issue author")
    args = obj["args"]
    if not isinstance(args, dict):
        raise Denied("invalid args")
    if cmd in ("HEALTH", "LEARNING_STATUS", "DIAGNOSTICS") and args:
        raise Denied("read-only command has no parameters")
    if cmd in ("PATCH_STAGE", "PATCH_APPLY") and (
            set(args) != {"patch_commit", "patch_id"} or
            not isinstance(args["patch_commit"], str) or
            not SHA.fullmatch(args["patch_commit"]) or
            not isinstance(args["patch_id"], str) or
            not ID.fullmatch(args["patch_id"])):
        raise Denied("invalid patch reference")
    expiry = obj["expires_at"]
    clock = int(time.time() if now is None else now)
    if type(expiry) is not int or not 0 < expiry - clock <= 900:
        raise Denied("expired or overlong command")
    provided = obj["mac"]
    secret = keys.get(agent)
    if (not isinstance(provided, str) or not KEY.fullmatch(provided) or
            not isinstance(secret, str) or not KEY.fullmatch(secret)):
        raise Denied("invalid MAC/key")
    body = {k: v for k, v in obj.items() if k != "mac"}
    expected = hmac.new(bytes.fromhex(secret), canonical(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        raise Denied("bad MAC")
    return body


def make_command(agent, command, args, secret, *, now=None, request_id=None):
    if (not AGENT.fullmatch(agent) or command not in COMMANDS or
            not KEY.fullmatch(secret)):
        raise Denied("invalid agent, command or key")
    body = {"schema": SCHEMA, "id": request_id or secrets.token_hex(16),
            "agent": agent, "command": command, "expires_at":
            int(time.time() if now is None else now) + 600, "args": args}
    body["mac"] = hmac.new(bytes.fromhex(secret), canonical(body), hashlib.sha256).hexdigest()
    return body


def private_config(path):
    path = Path(path)
    st = path.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or
            st.st_uid != os.getuid()):
        raise Denied("config must be user-owned, regular and chmod 600")
    if st.st_size > 32000:
        raise Denied("oversized config")
    cfg = strict_json(path.read_bytes())
    if not isinstance(cfg, dict):
        raise Denied("invalid config")
    repo = cfg.get("relay_repo")
    if not isinstance(repo, str) or not REPO.fullmatch(repo):
        raise Denied("private owner/repo required")
    src = cfg.get("source_repo", "RedMentos/Aii")
    if not isinstance(src, str) or not REPO.fullmatch(src):
        raise Denied("invalid trusted source repository")
    if repo.lower() == src.lower():
        raise Denied("public developer source cannot be its own private command relay")
    for fld in ("installed_root", "state_dir", "staging_root"):
        if not isinstance(cfg.get(fld), str) or not Path(cfg[fld]).is_absolute():
            raise Denied("local absolute paths required")
    for field in ("keys", "permissions", "authors"):
        if not isinstance(cfg.get(field), dict):
            raise Denied("missing per-agent security policy")
    for agent, key in cfg["keys"].items():
        if not AGENT.fullmatch(agent) or not isinstance(key, str) or not KEY.fullmatch(key):
            raise Denied("invalid per-agent secret")
        p = cfg["permissions"].get(agent)
        a = cfg["authors"].get(agent)
        if (not isinstance(p, list) or not p or any(x not in COMMANDS for x in p)
                or not isinstance(a, list) or not a or
                any(not isinstance(x, str) or not x or len(x) > 60 for x in a)):
            raise Denied("invalid agent policy")
    if type(cfg.get("remote_apply_enabled", False)) is not bool:
        raise Denied("invalid apply toggle")
    paths = cfg.get("apply_paths", [])
    if (not isinstance(paths, list) or len(paths) > 32 or
            any(not isinstance(x, str) or not x.startswith("v13/code/v13/")
                or not x.endswith(".py") or ".." in x or "//" in x
                or not re.fullmatch(r"[A-Za-z0-9_./-]+", x) or
                x.rsplit("/", 1)[-1] in
                ("remote_maintenance_bridge.py", "termux_patch_staging.py") for x in paths)):
        raise Denied("invalid exact-file apply allowlist")
    if cfg.get("remote_apply_enabled", False) and not paths:
        raise Denied("remote apply enabled without exact-file allowlist")
    return cfg


class GitHub:
    """Fixed-host GitHub REST client. Only configured repo endpoints are used."""
    def __init__(self, token, repository):
        if not token or any(c.isspace() for c in token) or len(token) > 512:
            raise Denied("GitHub token missing/invalid")
        if not REPO.fullmatch(repository):
            raise Denied("invalid repo")
        self.repository, self.token = repository, token

    def request(self, method, path, payload=None, *, limit=256_000):
        if not path.startswith("/") or "//" in path or ".." in path:
            raise Denied("invalid fixed API path")
        url = "https://api.github.com" + path
        raw = None if payload is None else canonical(payload)
        headers = {"Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "V13-Private-Bridge/1"}
        # Private relay token is NEVER forwarded when reading the PUBLIC source
        # repo, even if the caller's fine-grained token cannot access it.
        own = "/repos/" + self.repository
        if path == own or path.startswith(own + "/"):
            headers["Authorization"] = "Bearer " + self.token
        elif method != "GET" or not path.startswith("/repos/"):
            raise Denied("cross-repository write/credential forwarding forbidden")
        if raw is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=raw, headers=headers, method=method)
        # GitHub endpoint responses should not be redirected to other hosts.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                raise Denied("unexpected API redirect")
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(req, timeout=20) as response:
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > limit:
                raise Denied("oversized GitHub response")
            data = response.read(limit + 1)
            if len(data) > limit:
                raise Denied("oversized GitHub response")
            return strict_json(data)

    def check_private(self):
        obj = self.request("GET", "/repos/" + self.repository)
        if obj.get("private") is not True or obj.get("full_name", "").lower() != self.repository.lower():
            raise Denied("relay MUST be a distinct PRIVATE repository")
        return True

    def issues(self):
        result = self.request("GET", "/repos/" + self.repository +
                              "/issues?state=open&sort=created&direction=desc&per_page=30")
        if not isinstance(result, list):
            raise Denied("malformed issue list")
        return result

    def comment(self, issue, receipt):
        return self.request("POST", f"/repos/{self.repository}/issues/{issue}/comments",
                            {"body": canonical(receipt).decode("ascii")})

    def close(self, issue):
        return self.request("PATCH", f"/repos/{self.repository}/issues/{issue}",
                            {"state": "closed"})

    def create_command(self, cmd):
        return self.request("POST", "/repos/" + self.repository + "/issues",
                            {"title": "V13CMD:" + cmd["id"],
                             "body": canonical(cmd).decode("ascii")})

    def put_content(self, path, data, message):
        if (not re.fullmatch(r"patches/[0-9a-f]{32}/(?:manifest\.json|manifest\.sig|files/v13/code/v13/[A-Za-z0-9_./-]+\.py)", path)
                or ".." in path or "//" in path or len(data) > 1_048_576):
            raise Denied("invalid private patch destination")
        obj = self.request("PUT", f"/repos/{self.repository}/contents/{path}",
                           {"message": message, "content": base64.b64encode(data).decode()})
        commit = (obj.get("commit") or {}).get("sha")
        if not isinstance(commit, str) or not SHA.fullmatch(commit):
            raise Denied("GitHub did not confirm published patch commit")
        return commit

    def get_issue(self, issue):
        return self.request("GET", f"/repos/{self.repository}/issues/{issue}")

    def comments(self, issue):
        return self.request("GET", f"/repos/{self.repository}/issues/{issue}/comments?per_page=100")

    def content(self, repo, commit, path):
        if (not REPO.fullmatch(repo) or not SHA.fullmatch(commit) or
                not re.fullmatch(r"[A-Za-z0-9_./-]{1,220}", path) or
                path.startswith("/") or ".." in path or "//" in path):
            raise Denied("invalid pinned source path")
        raw = self.request("GET", f"/repos/{repo}/contents/{path}?ref={commit}", limit=2_000_000)
        if (not isinstance(raw, dict) or raw.get("type") != "file" or
                raw.get("encoding") != "base64" or not isinstance(raw.get("content"), str)):
            raise Denied("invalid GitHub content response")
        try:
            blob = base64.b64decode(raw["content"], validate=False)
        except (ValueError, binascii.Error) as exc:
            raise Denied("invalid base64 content") from exc
        if len(blob) > 1_048_576:
            raise Denied("oversized patch blob")
        if raw.get("size") != len(blob):
            raise Denied("GitHub blob size mismatch")
        # GitHub contents API blob sha uses Git's SHA1, not SHA256.
        git_blob = hashlib.sha1(b"blob " + str(len(blob)).encode() + b"\0" + blob).hexdigest()
        if not hmac.compare_digest(raw.get("sha", ""), git_blob):
            raise Denied("GitHub blob SHA mismatch")
        return blob

    def commit_exists(self, repo, commit):
        obj = self.request("GET", f"/repos/{repo}/commits/{commit}", limit=180_000)
        if obj.get("sha") != commit:
            raise Denied("pinned source commit does not match")


def _trusted_status(path):
    if not path:
        return {"state": "UNINSTRUMENTED"}
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_STATUS:
        return {"state": "UNAVAILABLE"}
    # A status file can survive the V13 process that produced it.
    if not 0 <= time.time() - p.stat().st_mtime <= 180:
        return {"state": "STALE_NO_LIVE_PROOF"}
    try:
        data = strict_json(p.read_bytes())
    except (OSError, Denied):
        return {"state": "INVALID"}
    if not isinstance(data, dict):
        return {"state": "INVALID"}
    out = {"state": "REPORTED_BY_LOCAL_RUNTIME"}
    for field in ("learning_mode", "runtime_mode", "last_error_code", "world_status"):
        value = data.get(field)
        if type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,60}", value):
            out[field] = value
    for field in ("queue_depth", "world_steps", "c3_steps", "body_b1_steps", "body_b2_steps"):
        value = data.get(field)
        if type(value) is int and 0 <= value <= 10**12:
            out[field] = value
    organs = data.get("organ_status")
    if isinstance(organs, dict):
        out["organ_status"] = {k: v for k, v in organs.items() if
                               k in ("B1", "B2", "C2", "C3", "WORLD", "JEF", "A5") and
                               type(v) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,40}", v)}
    return out


def health(cfg):
    root = Path(cfg["installed_root"])
    res = {"source": "LOCAL_OS_SNAPSHOT", "runtime": _trusted_status(cfg.get("status_file"))}
    try:
        disk = shutil.disk_usage(root)
        res["disk_total_mib"] = disk.total // (1024 * 1024)
        res["disk_free_mib"] = disk.free // (1024 * 1024)
    except OSError:
        res["disk_state"] = "UNAVAILABLE"
    try:
        lines = Path("/proc/meminfo").read_text()[:4096]
        for label in ("MemTotal", "MemAvailable"):
            match = re.search(r"^" + label + r":\s*(\d+)\s*kB", lines, re.M)
            if match:
                res[label.lower() + "_mib"] = int(match.group(1)) // 1024
    except OSError:
        pass
    try:
        # Android/Termux Python builds may omit os.getloadavg entirely.
        # System load is optional telemetry, not a reason to reject HEALTH.
        res["load_average"] = [round(float(x), 2) for x in os.getloadavg()]
    except (OSError, AttributeError, ValueError):
        res["load_average_state"] = "UNAVAILABLE"

    return res


def installed_revision(root, cfg):
    git = Path(root) / ".git"
    if git.exists():
        try:
            run = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                                 capture_output=True, text=True, timeout=5, check=True,
                                 env={"PATH": os.environ.get("PATH", ""), "GIT_CONFIG_NOSYSTEM": "1"})
            found = run.stdout.strip()
            if SHA.fullmatch(found):
                return found
        except (subprocess.SubprocessError, OSError):
            pass
        raise Denied("installed Git revision cannot be independently verified")
    pinned = cfg.get("installed_commit")
    if not isinstance(pinned, str) or not SHA.fullmatch(pinned):
        raise Denied("source ZIP install requires locally pinned installed_commit")
    return pinned


def download_and_stage(client, cfg, args):
    from v13.termux_patch_staging import verify_and_stage, _json_strict, _safe_path
    repo = cfg["relay_repo"]
    commit, patch_id = args["patch_commit"], args["patch_id"]
    client.commit_exists(repo, commit)
    prefix = "patches/" + patch_id
    manifest = client.content(repo, commit, prefix + "/manifest.json")
    if len(manifest) > 65536:
        raise Denied("oversized signed manifest")
    parsed = _json_strict(manifest)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("files"), list) or len(parsed["files"]) > 32:
        raise Denied("bad manifest file list")
    sig = client.content(repo, commit, prefix + "/manifest.sig")
    if len(sig) != 64:
        raise Denied("bad signature length")
    root = Path(cfg["installed_root"])
    stage = Path(cfg["staging_root"])
    if not root.is_dir() or root.is_symlink() or not stage.is_dir() or stage.is_symlink():
        raise Denied("unavailable local source/staging roots")
    if not cfg.get("trust_file") or not Path(cfg["trust_file"]).is_file():
        raise Denied("trusted public patch keyring not configured")
    local_commit = installed_revision(root, cfg)
    target = parsed.get("target_commit")
    if type(target) is not str or not SHA.fullmatch(target):
        raise Denied("missing signed source commit")
    client.commit_exists(cfg.get("source_repo", "RedMentos/Aii"), target)
    with tempfile.TemporaryDirectory(dir=stage, prefix="incoming-") as tmp:
        incoming = Path(tmp)
        (incoming / "files").mkdir()
        (incoming / "manifest.json").write_bytes(manifest)
        (incoming / "manifest.sig").write_bytes(sig)
        for entry in parsed["files"]:
            if not isinstance(entry, dict) or "path" not in entry:
                raise Denied("bad patch entry")
            rel = _safe_path(entry["path"])
            path = rel.as_posix()
            code = client.content(repo, commit, prefix + "/files/" + path)
            # Independently confirm exact after-bytes at developer commit.
            expected = client.content(cfg.get("source_repo", "RedMentos/Aii"), target, path)
            if code != expected:
                raise Denied("private bundle disagrees with pinned developer source")
            out = incoming / "files" / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(code)
        dest, receipt = verify_and_stage(incoming, cfg["trust_file"], root, stage,
                                         installed_commit=local_commit)
    return dest, receipt


def _validate_source(path, raw):
    if path.endswith(".py"):
        ast.parse(raw.decode("utf-8"), filename="<signed-updated-source>")
    elif path.endswith(".json"):
        strict_json(raw)
    elif path.endswith(".toml"):
        import tomllib
        tomllib.loads(raw.decode("utf-8"))
    # Markdown gets exact-byte validation; no active execution.


def apply_one_staged(cfg, stage, receipt, request_id):
    """Explicitly opted-in exact ONE-FILE source replace; no process restart.

    Writes a rollback copy BEFORE an os.replace; cannot promise process-wide
    atomicity or secure boundary if other code has full same-UID write access.
    """
    if not cfg.get("remote_apply_enabled", False):
        raise Denied("remote apply disabled locally")
    files = receipt.get("files", [])
    if len(files) != 1:
        raise Denied("automatic apply supports exactly one existing source file")
    item = files[0]
    rel = item["path"]
    if rel not in cfg.get("apply_paths", ()) or not rel.endswith(".py"):
        raise Denied("patch path not explicitly approved")
    root = Path(cfg["installed_root"])
    live = root / rel
    new = Path(stage) / "files" / rel
    if live.is_symlink() or new.is_symlink() or not live.is_file() or not new.is_file():
        raise Denied("unsafe source file type")
    before = live.read_bytes()
    after = new.read_bytes()
    if sha(before) != item["before_sha256"] or sha(after) != item["after_sha256"]:
        raise Denied("source changed after staging")
    _validate_source(rel, after)
    backup_root = Path(cfg["state_dir"]) / "backups"
    backup_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if backup_root.is_symlink() or backup_root.stat().st_mode & 0o077:
        raise Denied("backup directory must be private and nonsymlink")
    backup = backup_root / (request_id + ".original")
    if backup.exists() or backup.is_symlink():
        raise Denied("backup collision")
    # Restrict the target to a regular path beneath installed root, no symlink parent.
    cur = root
    for part in Path(rel).parts[:-1]:
        cur = cur / part
        if cur.is_symlink() or not cur.is_dir():
            raise Denied("unsafe installed source path")
    with backup.open("xb") as fp:
        fp.write(before)
        fp.flush()
        os.fsync(fp.fileno())
    os.chmod(backup, 0o600)
    metadata = backup_root / (request_id + ".json")
    with metadata.open("xb") as fp:
        fp.write(canonical({"schema": "v13.local-source-backup/1", "path": rel,
                            "before_sha256": sha(before), "after_sha256": sha(after)}))
        fp.flush()
        os.fsync(fp.fileno())
    os.chmod(metadata, 0o600)
    draft = None
    try:
        with tempfile.NamedTemporaryFile(dir=live.parent, prefix=".v13-patch-", delete=False) as fp:
            draft = Path(fp.name)
            fp.write(after)
            fp.flush()
            os.fsync(fp.fileno())
        os.chmod(draft, stat.S_IMODE(live.stat().st_mode) & 0o700)
        if sha(live.read_bytes()) != item["before_sha256"]:
            raise Denied("concurrent source modification")
        os.replace(draft, live)
        # fsync containing directory where supported.
        try:
            fd = os.open(str(live.parent), os.O_RDONLY)
            try: os.fsync(fd)
            finally: os.close(fd)
        except OSError:
            pass
    finally:
        if draft is not None:
            draft.unlink(missing_ok=True)
    return {"status": "APPLIED_SOURCE_RESTART_REQUIRED", "path": rel,
            "source_sha256": sha(after), "backup_id": request_id,
            "live_process_reloaded": False, "native_android_verified": False}


def publish_one_patch(client, source_repo, agent, base_commit, target_commit, path,
                      private_key_file, *, now=None, patch_id=None):
    """Developer-side private bundle publication from exact source Git commits.

    Uses per-agent raw 32-byte Ed25519 private key in a mode-600 local file.
    GitHub contents API writes only into the configured PRIVATE relay.
    """
    from v13.termux_patch_staging import SCHEMA as PATCH_SCHEMA, _safe_path
    if (not REPO.fullmatch(source_repo) or not AGENT.fullmatch(agent) or
            not SHA.fullmatch(base_commit) or not SHA.fullmatch(target_commit)
            or base_commit == target_commit):
        raise Denied("invalid patch publication source pins")
    _safe_path(path)
    if not path.startswith("v13/code/v13/") or not path.endswith(".py") or path.rsplit("/", 1)[-1] in (
            "remote_maintenance_bridge.py", "termux_patch_staging.py"):
        raise Denied("publisher requires an ordinary source Python file")
    client.check_private()
    client.commit_exists(source_repo, base_commit)
    client.commit_exists(source_repo, target_commit)
    old = client.content(source_repo, base_commit, path)
    new = client.content(source_repo, target_commit, path)
    if old == new:
        raise Denied("no code difference to publish")
    _validate_source(path, new)
    file = Path(private_key_file)
    mode = file.lstat()
    if not stat.S_ISREG(mode.st_mode) or mode.st_mode & 0o077 or mode.st_uid != os.getuid():
        raise Denied("Ed25519 private key must be a user-owned chmod-600 regular file")
    if mode.st_size != 32:
        raise Denied("expected 32 raw Ed25519 private key bytes")
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    signing_key = Ed25519PrivateKey.from_private_bytes(file.read_bytes())
    ident = patch_id or secrets.token_hex(16)
    if not ID.fullmatch(ident):
        raise Denied("invalid patch ID")
    manifest = {"schema": PATCH_SCHEMA, "agent": agent, "nonce": secrets.token_hex(16),
                "base_commit": base_commit, "target_commit": target_commit,
                "expires_at": int(time.time() if now is None else now) + 1800,
                "files": [{"path": path, "before_sha256": sha(old), "after_sha256": sha(new),
                           "size": len(new)}]}
    signed = canonical(manifest)
    signature = signing_key.sign(signed)
    prefix = "patches/" + ident
    message = "V13 private signed patch " + ident
    client.put_content(prefix + "/files/" + path, new, message)
    client.put_content(prefix + "/manifest.json", signed, message)
    final_commit = client.put_content(prefix + "/manifest.sig", signature, message)
    return {"patch_id": ident, "patch_commit": final_commit,
            "manifest_sha256": sha(signed), "target_commit": target_commit,
            "path": path, "expires_at": manifest["expires_at"],
            "private_bundle_published": True, "device_updated": False}


def rollback_local_source(cfg, request_id):
    """Local operator-initiated restore, never a remote-issued command."""
    if not ID.fullmatch(request_id):
        raise Denied("invalid backup ID")
    backup_root = Path(cfg["state_dir"]) / "backups"
    if backup_root.is_symlink() or not backup_root.is_dir():
        raise Denied("missing trusted backup storage")
    metadata = backup_root / (request_id + ".json")
    backup = backup_root / (request_id + ".original")
    if (metadata.is_symlink() or backup.is_symlink() or not metadata.is_file() or
            not backup.is_file() or metadata.stat().st_size > 2048):
        raise Denied("missing or unsafe backup")
    rec = strict_json(metadata.read_bytes())
    if (not isinstance(rec, dict) or set(rec) != {
            "schema", "path", "before_sha256", "after_sha256"} or
            rec["schema"] != "v13.local-source-backup/1"):
        raise Denied("bad backup metadata")
    rel = rec["path"]
    if rel not in cfg.get("apply_paths", ()) or not rel.startswith("v13/code/v13/"):
        raise Denied("backup path no longer locally authorized")
    root = Path(cfg["installed_root"])
    cur = root
    for part in Path(rel).parts[:-1]:
        cur = cur / part
        if cur.is_symlink() or not cur.is_dir():
            raise Denied("unsafe installed source path")
    live = root / rel
    if live.is_symlink() or not live.is_file():
        raise Denied("unsafe installed source")
    original = backup.read_bytes()
    if (sha(original) != rec["before_sha256"] or
            sha(live.read_bytes()) != rec["after_sha256"]):
        raise Denied("live version or backup has changed; no blind rollback")
    with tempfile.NamedTemporaryFile(dir=live.parent, prefix=".v13-rollback-", delete=False) as fp:
        temp = Path(fp.name)
        fp.write(original)
        fp.flush()
        os.fsync(fp.fileno())
    try:
        os.chmod(temp, stat.S_IMODE(live.stat().st_mode) & 0o700)
        if sha(live.read_bytes()) != rec["after_sha256"]:
            raise Denied("concurrent rollback source modification")
        os.replace(temp, live)
    finally:
        temp.unlink(missing_ok=True)
    return {"status": "ROLLED_BACK_SOURCE_RESTART_REQUIRED", "path": rel,
            "restored_sha256": sha(original), "live_process_reloaded": False}


@contextmanager
def local_lock(state_dir):
    directory = Path(state_dir)
    if directory.is_symlink():
        raise Denied("symlink state directory")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.stat().st_mode & 0o077:
        raise Denied("state directory must not be shared")
    lockfile = directory / "bridge.lock"
    with lockfile.open("a+b") as fp:
        os.chmod(lockfile, 0o600)
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield directory
        finally:
            fcntl.flock(fp, fcntl.LOCK_UN)


def database(state):
    db = sqlite3.connect(str(state / "bridge.sqlite"))
    db.execute("PRAGMA busy_timeout=3000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS events (issue INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, receipt TEXT, posted INTEGER NOT NULL DEFAULT 0)")
    db.commit()
    os.chmod(state / "bridge.sqlite", 0o600)
    return db


def safe_receipt(cmd, result):
    rec = {"schema": RECEIPT_SCHEMA, "request_id": cmd["id"],
           "command": cmd["command"], "device_status": result}
    if len(canonical(rec)) > MAX_REPLY:
        raise Denied("oversized sanitized receipt")
    return rec


def execute(client, cfg, cmd):
    name = cmd["command"]
    if name == "HEALTH":
        return {"status": "OK", **health(cfg)}
    if name == "LEARNING_STATUS":
        return {"status": "OK", "learning": _trusted_status(cfg.get("status_file"))}
    if name == "DIAGNOSTICS":
        from .mobile_dashboard import summary, remote_console_excerpt, remote_full_console
        return {"status": "OK", "technical_diagnostics": summary(),
                "console_errors": remote_console_excerpt(),
                "console_excerpt": remote_full_console()}
    dest, receipt = download_and_stage(client, cfg, cmd["args"])
    if name == "PATCH_STAGE":
        return {"status": "SIGNED_PATCH_STAGED_NOT_APPLIED", "manifest_sha256":
                receipt["manifest_sha256"], "paths": [f["path"] for f in receipt["files"]],
                "apply_allowed": bool(cfg.get("remote_apply_enabled", False))}
    return apply_one_staged(cfg, dest, receipt, cmd["id"])


def process_issue(client, cfg, db, issue, *, now=None):
    if "pull_request" in issue or not str(issue.get("title", "")).startswith("V13CMD:"):
        return False
    number = issue.get("number")
    if type(number) is not int or number <= 0:
        return False
    body = issue.get("body")
    if not isinstance(body, str) or len(body.encode("utf-8")) > MAX_COMMAND:
        return False
    try:
        obj = strict_json(body)
        cmd = verify_command(obj, cfg["keys"], cfg["permissions"], cfg["authors"],
                             author=(issue.get("user") or {}).get("login"), now=now)
        if issue.get("title") != "V13CMD:" + cmd["id"]:
            return False
    except (Denied, TypeError, KeyError):
        return False  # No receipt/oracle for unauthenticated issues.
    row = db.execute("SELECT request_id,receipt,posted FROM events WHERE issue=?", (number,)).fetchone()
    if row is None:
        try:
            db.execute("INSERT INTO events(issue,request_id) VALUES(?,?)", (number, cmd["id"]))
            db.commit()  # durable before any mutation; an interrupted APPLY never retries
        except sqlite3.IntegrityError:
            return False  # reused authenticated request ID at another issue
        try:
            status = execute(client, cfg, cmd)
        except Exception as exc:
            status = {"status": "REJECTED_OR_FAILED", "error_code":
                      type(exc).__name__[:48]}  # do NOT leak paths/tokens/logs
        receipt = safe_receipt(cmd, status)
        db.execute("UPDATE events SET receipt=? WHERE issue=?", (canonical(receipt).decode(), number))
        db.commit()
        posted = 0
    else:
        if row[0] != cmd["id"]:
            return False
        if row[1] is None:
            receipt = safe_receipt(cmd, {"status": "INTERRUPTED_NO_RETRY"})
            db.execute("UPDATE events SET receipt=? WHERE issue=?", (canonical(receipt).decode(), number))
            db.commit()
        else:
            receipt = strict_json(row[1])
        posted = row[2]
    if not posted:
        client.comment(number, receipt)
        db.execute("UPDATE events SET posted=1 WHERE issue=?", (number,))
        db.commit()
    client.close(number)
    return True


def poll_once(client, cfg):
    client.check_private()  # every poll, before any private data leaves device
    if (Path(cfg["state_dir"]) / "STOP").exists():
        return {"status": "STOPPED_LOCALLY", "processed": 0}
    with local_lock(cfg["state_dir"]) as state:
        if (state / "STOP").exists():
            return {"status": "STOPPED_LOCALLY", "processed": 0}
        with database(state) as db:
            processed = 0
            for issue in client.issues():
                if processed >= 20:
                    break
                if process_issue(client, cfg, db, issue):
                    processed += 1
            return {"status": "POLL_OK", "processed": processed}


def cli(argv=None):
    parser = argparse.ArgumentParser(description="V13 private outbound maintenance bridge")
    sub = parser.add_subparsers(dest="mode", required=True)
    for command in ("once", "serve", "stop", "resume", "rollback"):
        p = sub.add_parser(command)
        p.add_argument("--config", required=True)
        if command == "rollback":
            p.add_argument("--request-id", required=True)
    send = sub.add_parser("send", help="remote authorized developer CLI")
    send.add_argument("--repo", required=True)
    send.add_argument("--agent", required=True)
    send.add_argument("--command", choices=sorted(COMMANDS), required=True)
    send.add_argument("--patch-commit")
    send.add_argument("--patch-id")
    send.add_argument("--key-env", default="V13_AGENT_KEY")
    send.add_argument("--token-env", default="V13_RELAY_TOKEN")
    keygen = sub.add_parser("keygen", help="generate a private signing key; print public key only")
    keygen.add_argument("--out", required=True)
    pub = sub.add_parser("publish", help="private Ed25519-signed source patch bundle")
    pub.add_argument("--repo", required=True)
    pub.add_argument("--source-repo", default="RedMentos/Aii")
    pub.add_argument("--agent", required=True)
    pub.add_argument("--base-commit", required=True)
    pub.add_argument("--target-commit", required=True)
    pub.add_argument("--path", required=True)
    pub.add_argument("--signing-key-file", required=True)
    pub.add_argument("--token-env", default="V13_RELAY_TOKEN")
    read = sub.add_parser("read", help="fetch private reply from issue URL/number")
    read.add_argument("--repo", required=True)
    read.add_argument("--issue", type=int, required=True)
    read.add_argument("--token-env", default="V13_RELAY_TOKEN")
    args = parser.parse_args(argv)
    if args.mode == "keygen":
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        private = Ed25519PrivateKey.generate()
        raw = private.private_bytes(serialization.Encoding.Raw,
                                    serialization.PrivateFormat.Raw,
                                    serialization.NoEncryption())
        path = Path(args.out)
        if path.is_symlink():
            raise Denied("refuse to write private signing key through symlink")
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fp:
            fp.write(raw)
            fp.flush()
            os.fsync(fp.fileno())
        public = private.public_key().public_bytes(serialization.Encoding.Raw,
                                                  serialization.PublicFormat.Raw)
        print(json.dumps({"private_key_written": str(path),
                          "public_key_b64": base64.b64encode(public).decode()}))
        return
    if args.mode in ("send", "read", "publish"):
        client = GitHub(os.environ.get(args.token_env), args.repo)
        client.check_private()
        if args.mode == "publish":
            print(json.dumps(publish_one_patch(client, args.source_repo, args.agent,
                                               args.base_commit, args.target_commit,
                                               args.path, args.signing_key_file), sort_keys=True))
            return
        if args.mode == "read":
            issue = client.get_issue(args.issue)
            if not str(issue.get("title", "")).startswith("V13CMD:"):
                raise Denied("not a V13 command")
            replies = [strict_json(c["body"]) for c in client.comments(args.issue)
                       if isinstance(c.get("body"), str) and len(c["body"]) <= MAX_REPLY]
            print(json.dumps([r for r in replies if isinstance(r, dict)
                              and r.get("schema") == RECEIPT_SCHEMA], sort_keys=True))
            return
        payload = {}
        if args.command.startswith("PATCH_"):
            payload = {"patch_commit": args.patch_commit, "patch_id": args.patch_id}
            if (not isinstance(args.patch_commit, str) or not SHA.fullmatch(args.patch_commit)
                    or not isinstance(args.patch_id, str) or not ID.fullmatch(args.patch_id)):
                raise Denied("patch command needs pinned commit + patch ID")
        cmd = make_command(args.agent, args.command, payload, os.environ.get(args.key_env, ""))
        response = client.create_command(cmd)
        print(json.dumps({"issue": response.get("number"), "url": response.get("html_url"),
                          "request_id": cmd["id"]}))
        return
    cfg = private_config(args.config)
    stop = Path(cfg["state_dir"]) / "STOP"
    if args.mode == "rollback":
        with local_lock(cfg["state_dir"]):
            print(json.dumps(rollback_local_source(cfg, args.request_id)))
        return
    if args.mode in ("stop", "resume"):
        with local_lock(cfg["state_dir"]):
            if args.mode == "stop":
                stop.touch(mode=0o600)
            else:
                stop.unlink(missing_ok=True)
        print(args.mode.upper())
        return
    client = GitHub(os.environ.get("V13_RELAY_TOKEN"), cfg["relay_repo"])
    if args.mode == "once":
        print(json.dumps(poll_once(client, cfg)))
        return
    interval = cfg.get("poll_seconds", DEFAULT_INTERVAL)
    if type(interval) is not int or not 15 <= interval <= 3600:
        raise Denied("poll interval outside 15..3600 seconds")
    # Explicit foreground process; Termux may suspend/kick the process in background.
    while True:
        try:
            print(json.dumps(poll_once(client, cfg)), flush=True)
        except (OSError, urllib.error.URLError, ValueError) as exc:
            print(json.dumps({"status": "TRANSIENT_POLL_ERROR", "error_code":
                              type(exc).__name__}), flush=True)
        time.sleep(interval)


if __name__ == "__main__":
    cli()