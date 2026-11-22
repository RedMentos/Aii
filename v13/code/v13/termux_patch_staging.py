"""V13 Termux patch intake: signature-verified, review-only staging.

No listener, no SSH server, no downloaded code execution, no live installs.
The trusted keyring must live OUTSIDE any agent-writable checkout; a phone
companion must independently enforce consent before any future apply phase.

Bundle layout: manifest.json (signed exact bytes), manifest.sig (64 raw bytes),
files/<manifest-path>. Each path is confined to approved project source files.
cryptography's Ed25519 verify is the only accepted signing scheme.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time

SCHEMA = "v13.termux.patch-staging/1"
MAX_MANIFEST = 64 * 1024
MAX_FILES = 32
MAX_FILE = 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_ID = re.compile(r"[a-z][a-z0-9_-]{2,39}\Z")
_NONCE = re.compile(r"[0-9a-f]{32}\Z")
_ALLOW_PREFIXES = (
    "v13/code/v13/", "v13/code/tests/", "v13/code/docs/",
)


class PatchDenied(ValueError):
    """Invalid signature, provenance, replay/precondition or source policy."""


def _json_strict(raw):
    def pairs(items):
        obj = {}
        for k, value in items:
            if k in obj:
                raise PatchDenied("duplicate signed JSON field")
            obj[k] = value
        return obj
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(PatchDenied("nonfinite JSON")))
    except PatchDenied:
        raise
    except (ValueError, UnicodeError) as exc:
        raise PatchDenied("invalid JSON") from exc


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _regular(path):
    try:
        st = path.lstat()
    except OSError as exc:
        raise PatchDenied("missing signed bundle material") from exc
    if not stat.S_ISREG(st.st_mode):
        raise PatchDenied("signed bundle member must be regular file")
    return st.st_size


def _safe_path(name):
    if (type(name) is not str or not 1 <= len(name) <= 160 or
            any(ord(c) > 127 for c in name) or
            not re.fullmatch(r"[A-Za-z0-9_./-]+", name) or
            name.startswith("/") or "//" in name or
            any(p in (".", "..", "") for p in name.split("/")) or
            not any(name.startswith(prefix) for prefix in _ALLOW_PREFIXES) or
            not name.endswith((".py", ".md", ".json", ".toml"))):
        raise PatchDenied("path outside reviewed V13 allowlist")
    return Path(name)


def _safe_file(root, relative, *, exists=True):
    """Reject symlink components and escape before opening a root-relative file."""
    if not root.is_dir() or root.is_symlink():
        raise PatchDenied("expected private regular project directory")
    curr = root
    parts = relative.parts
    for i, segment in enumerate(parts):
        curr = curr / segment
        if not curr.exists() and not curr.is_symlink():
            if exists or i < len(parts)-1:
                # A new file may have a directory which does not exist yet.
                # Only for new files are absent parent directories allowed.
                if exists:
                    raise PatchDenied("missing file in signed source tree")
            continue
        if curr.is_symlink():
            raise PatchDenied("symlink in signed path")
        if i < len(parts)-1 and not curr.is_dir():
            raise PatchDenied("non-directory path component")
        if i == len(parts)-1 and not curr.is_file():
            raise PatchDenied("expected regular file")
    if exists and not curr.is_file():
        raise PatchDenied("file does not exist")
    return curr


def verify_and_stage(bundle, trust_file, installed_root, staging_root,
                     *, installed_commit, now=None):
    """Return private staged directory with receipt; never modifies live root.

    Trust file: {"agents":{"agent-id":{"public_key_b64":"<32 raw Ed25519 bytes>",
    "allowed_prefixes":["v13/code/v13/"]}}}. Agent keys are public only.
    The local companion/operator must protect this trust file and control
    whether this verification may be invoked as an unattended service.
    """
    bundle = Path(bundle)
    trust_file = Path(trust_file)
    installed_root = Path(installed_root)
    staging_root = Path(staging_root)
    if any(p.is_symlink() for p in (bundle, installed_root, staging_root)):
        raise PatchDenied("symlink top-level directory")
    if not bundle.is_dir() or not installed_root.is_dir():
        raise PatchDenied("signed bundle and installed root required")
    if not staging_root.is_dir():
        raise PatchDenied("local staging root must already exist")
    if not _COMMIT.fullmatch(installed_commit):
        raise PatchDenied("local installed revision required")
    if _regular(trust_file) > MAX_MANIFEST or _regular(bundle / "manifest.json") > MAX_MANIFEST:
        raise PatchDenied("oversized signed manifest or trust file")
    raw = (bundle / "manifest.json").read_bytes()
    manifest = _json_strict(raw)
    trust = _json_strict(trust_file.read_bytes())
    if (type(manifest) is not dict or set(manifest) !=
        {"schema", "agent", "nonce", "base_commit", "target_commit", "expires_at", "files"}):
        raise PatchDenied("invalid signed manifest schema")
    if manifest["schema"] != SCHEMA:
        raise PatchDenied("wrong patch-staging schema")
    agent = manifest["agent"]
    if type(agent) is not str or not _ID.fullmatch(agent):
        raise PatchDenied("invalid agent identity")
    if (type(trust) is not dict or set(trust) != {"agents"} or
            type(trust["agents"]) is not dict or agent not in trust["agents"]):
        raise PatchDenied("agent key not trusted")
    allowed = trust["agents"][agent]
    if (type(allowed) is not dict or set(allowed) != {"public_key_b64", "allowed_prefixes"}
            or type(allowed["allowed_prefixes"]) is not list or
            not allowed["allowed_prefixes"] or
            any(p not in _ALLOW_PREFIXES for p in allowed["allowed_prefixes"])):
        raise PatchDenied("invalid trusted agent scope")
    if type(allowed["public_key_b64"]) is not str or len(allowed["public_key_b64"]) > 128:
        raise PatchDenied("invalid trusted public key")
    if _regular(bundle / "manifest.sig") != 64:
        raise PatchDenied("invalid Ed25519 signature length")
    sig = (bundle / "manifest.sig").read_bytes()
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        public = base64.b64decode(allowed["public_key_b64"], validate=True)
        Ed25519PublicKey.from_public_bytes(public).verify(sig, raw)
    except (ImportError, InvalidSignature, binascii.Error, ValueError, TypeError) as exc:
        raise PatchDenied("unsigned or invalid agent signature") from exc

    if (type(manifest["base_commit"]) is not str or
        manifest["base_commit"] != installed_commit or
        type(manifest["target_commit"]) is not str or
        not _COMMIT.fullmatch(manifest["target_commit"]) or
        manifest["target_commit"] == installed_commit):
        raise PatchDenied("stale or invalid update revision")
    if (type(manifest["nonce"]) is not str or
            not _NONCE.fullmatch(manifest["nonce"])):
        raise PatchDenied("invalid update nonce")
    ts = manifest["expires_at"]
    clock = time.time() if now is None else now
    if (type(ts) is not int or type(clock) not in (int, float) or
            not 0 < ts-clock <= 3600):
        raise PatchDenied("expired or distant patch window")
    entries = manifest["files"]
    if type(entries) is not list or not 1 <= len(entries) <= MAX_FILES:
        raise PatchDenied("invalid patch file count")
    recorded = set()
    validated = []
    total = 0
    for entry in entries:
        if type(entry) is not dict or set(entry) != {"path", "before_sha256", "after_sha256", "size"}:
            raise PatchDenied("invalid signed patch file description")
        relative = _safe_path(entry["path"])
        if not any(entry["path"].startswith(p) for p in allowed["allowed_prefixes"]):
            raise PatchDenied("agent requested path outside its scope")
        if entry["path"] in recorded:
            raise PatchDenied("duplicate signed patch file")
        recorded.add(entry["path"])
        before = entry["before_sha256"]
        after = entry["after_sha256"]
        size = entry["size"]
        if (before is not None and (type(before) is not str or not _SHA256.fullmatch(before))):
            raise PatchDenied("invalid prior file checksum")
        if type(after) is not str or not _SHA256.fullmatch(after):
            raise PatchDenied("invalid patch checksum")
        if type(size) is not int or not 0 <= size <= MAX_FILE:
            raise PatchDenied("invalid patch file size")
        total += size
        if total > MAX_TOTAL:
            raise PatchDenied("patch budget exceeded")
        source = _safe_file(bundle / "files", relative)
        if _regular(source) != size:
            raise PatchDenied("signed file size mismatch")
        data = source.read_bytes()
        if _sha(data) != after:
            raise PatchDenied("signed file checksum mismatch")
        live = _safe_file(installed_root, relative, exists=False)
        if before is None:
            if live.exists():
                raise PatchDenied("new signed path already exists in installed tree")
        elif not live.is_file() or _sha(live.read_bytes()) != before:
            raise PatchDenied("installed tree differs from signed base")
        validated.append((relative, data, before, after))

    # Stage into fresh private subdirectory; verified content never touches live.
    if staging_root.stat().st_mode & 0o002:
        raise PatchDenied("world-writable staging root")
    dest = Path(tempfile.mkdtemp(prefix="v13-review-", dir=staging_root))
    os.chmod(dest, 0o700)
    for relative, data, _, _ in validated:
        target = dest / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(data)
        os.chmod(target, 0o600)
    receipt = {
        "schema": "v13.termux.patch-review-receipt/1",
        "status": "STAGED_REVIEW_ONLY_NOT_INSTALLED",
        "agent": agent,
        "nonce": manifest["nonce"],
        "base_commit": installed_commit,
        "target_commit": manifest["target_commit"],
        "manifest_sha256": _sha(raw),
        "files": [{"path": str(path), "before_sha256": before,
                   "after_sha256": after} for path, _, before, after in validated],
        "live_runtime_modified": False,
        "android_shell_exposed": False,
        "remote_listener_started": False,
        "operator_approval_obtained": False,
        "patch_applied": False,
    }
    (dest / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True))
    os.chmod(dest / "receipt.json", 0o600)
    return dest, receipt


def main(argv=None):
    p = argparse.ArgumentParser(description="V13 signed patch REVIEW staging only; no install")
    p.add_argument("--bundle", required=True)
    p.add_argument("--trust-file", required=True)
    p.add_argument("--installed-root", required=True)
    p.add_argument("--installed-commit", required=True)
    p.add_argument("--staging-root", required=True)
    args = p.parse_args(argv)
    _, receipt = verify_and_stage(args.bundle, args.trust_file, args.installed_root,
                                  args.staging_root, installed_commit=args.installed_commit)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
