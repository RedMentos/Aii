"""Explicit one-click private V13 diagnostic handoff to owner GitHub relay.

Nothing uploads on startup or merely because remote log viewing is enabled.
Only an explicit UI press calls publish(). No database, GGUF, credentials,
settings file, private GitHub token, arbitrary folder or shell is uploaded.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets

SCHEMA = "v13.phone-diagnostics/1"
PRIVATE_RELAY = "RedMentos/Aiiii"
MAX_FILES = 9
MAX_FILE_CHARS = 75000
MAX_TOTAL_CHARS = 420000
PAGE_CHARS = 11000

TOKEN = re.compile(r"(?i)(\b(?:gh[opusr]_[a-z0-9]{12,}|github_pat_[a-z0-9_]{12,})\b)")
BEARER = re.compile(r"(?i)(\b(?:authorization\s*:\s*bearer|bearer)\s+)[A-Za-z0-9._-]{12,}")
PASSWORD = re.compile(r"(?im)(\b(?:password|access_token|api_key|secret)\s*[:=]\s*)\S+")
LOCAL_URL = re.compile(r"http://127\.0\.0\.1:\d+/t/[a-f0-9]{48}/?")


def redact(text):
    text = TOKEN.sub("[REDACTED_CREDENTIAL]", str(text))
    text = BEARER.sub(r"\1[REDACTED_CREDENTIAL]", text)
    text = PASSWORD.sub(r"\1[REDACTED]", text)
    return LOCAL_URL.sub("http://127.0.0.1/[REDACTED_LOCAL_SESSION]", text)


def _read_tail(path, max_chars=MAX_FILE_CHARS):
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
        return None
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - 4 * max_chars))
        raw = stream.read(4 * max_chars)
    value = raw.decode("utf-8", errors="replace")
    if len(value) > max_chars:
        value = "[EARLIER CONTENT TRUNCATED BY SIZE LIMIT]\n" + value[-max_chars:]
    return redact(value)


def _logs(home, private, full):
    sessions = private / "console-logs"
    named = [
        ("ui.log", private / "ui.log"),
        ("ai-service.log", private / "ai-service.log"),
        ("bridge.log", private / "bridge.log"),
        ("v13-ui-last.log", private / "v13-ui-last.log"),
        ("native-probe.json", home / "exports/native-probe.json"),
    ]
    if full and sessions.is_dir() and not sessions.is_symlink():
        named += [(f"session-{idx}.log", p) for idx, p in enumerate(
            sorted(sessions.glob("v13-session-*.log"), reverse=True)[:4])]
    return named[:MAX_FILES]


def collect(*, full=False, home=None, private=None):
    """Build a bounded snapshot of technical status or consented logs.

    The normal mode sends ONLY a structured system summary, pipeline state
    and known error lines. Full mode adds recorded conversation logs.
    """
    if type(full) is not bool:
        raise ValueError("diagnostic mode must be explicit")
    home = Path(home or Path.home() / "v13")
    private = Path(private or Path.home() / ".v13-private")
    if private.is_symlink() or not private.is_dir():
        raise ValueError("private diagnostic directory unavailable")
    from .mobile_dashboard import summary
    from .pipeline_agent import snapshot
    report = {"schema": SCHEMA, "mode": "FULL_WITH_CHAT" if full else "TECHNICAL",
              "created_at": datetime.now(timezone.utc).isoformat(),
              "technical": summary(), "pipeline": snapshot(),
              "files": {}, "truncated": False}
    total = 0
    for name, path in _logs(home, private, full):
        if not full and name != "native-probe.json":
            # Only error lines in technical mode, never arbitrary transcript.
            text = _read_tail(path)
            if text is None:
                continue
            lines = text.splitlines()
            errors = [line for line in lines if re.match(
                r"(?i)^(?:\[V13 Fehler\]|\[Fehler\]|\[V13 exited with code|"
                r".{0,72}(?:Traceback|FileNotFoundError|TimeoutError|"
                r"PermissionError|PIPELINE_ERROR|ERROR:|SMOKE_PARTIAL))", line)]
            text = "\n".join(errors[-100:])
        else:
            text = _read_tail(path)
        if not text:
            continue
        if total + len(text) > MAX_TOTAL_CHARS:
            text = text[-max(0, MAX_TOTAL_CHARS-total):]
            report["truncated"] = True
        report["files"][name] = text
        total += len(text)
        if total >= MAX_TOTAL_CHARS:
            break
    report["total_transmitted_chars"] = total
    return report


def _pages(report):
    raw = json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    # Split on character boundaries after escaping; each payload is independent
    # and reassembled by page/index, not as unauthenticated commands.
    pages = [raw[i:i+PAGE_CHARS] for i in range(0, len(raw), PAGE_CHARS)]
    if len(pages) > 55:
        raise ValueError("diagnostic exceeds private relay bound")
    return pages, hashlib.sha256(raw.encode("ascii")).hexdigest()


def publish(*, full=False, client=None, home=None, private=None):
    """User-initiated only: publish bounded report to distinct PRIVATE repository.

    Client injection is for network-free integration tests. No shell input,
    GitHub command issues or source patch APIs are accepted here.
    """
    report = collect(full=full, home=home, private=private)
    pages, sha = _pages(report)
    if client is None:
        from .remote_maintenance_bridge import GitHub
        from .owner_read_bridge import github_token
        client = GitHub(github_token(), PRIVATE_RELAY)
    if client.repository != PRIVATE_RELAY or client.check_private() is not True:
        raise ValueError("Diagnostic relay must be exact verified PRIVATE repository")
    marker = secrets.token_hex(8)
    issue = client.request("POST", "/repos/" + PRIVATE_RELAY + "/issues", {
        "title": "V13PHONE:" + marker,
        "body": json.dumps({
            "schema": SCHEMA, "status": "IN_PROGRESS", "mode": report["mode"],
            "created_at": report["created_at"], "sha256": sha,
            "pages": len(pages), "total_transmitted_chars": report["total_transmitted_chars"],
            "note": "Explicit user click; passwords/tokens/local session URLs redacted; "
                    "no database or model binaries attached.",
        }, sort_keys=True)
    })
    number = issue.get("number")
    if type(number) is not int or not 1 <= number <= 100000000:
        raise ValueError("GitHub issue creation not confirmed")
    for i, page in enumerate(pages):
        client.request("POST", "/repos/" + PRIVATE_RELAY + f"/issues/{number}/comments", {
            "body": json.dumps({"schema": SCHEMA, "page": i + 1, "pages": len(pages),
                                "sha256": sha, "data": page}, ensure_ascii=True)
        })
    client.request("POST", "/repos/" + PRIVATE_RELAY + f"/issues/{number}/comments", {
        "body": json.dumps({"schema": SCHEMA, "status": "COMPLETE", "sha256": sha,
                            "pages": len(pages)}, sort_keys=True)
    })
    return {"status": "SENT", "issue_number": number,
            "url": f"https://github.com/{PRIVATE_RELAY}/issues/{number}",
            "mode": report["mode"], "pages": len(pages), "truncated": report["truncated"]}
