"""Explicit one-click private V13 diagnostic handoff to owner GitHub relay.

Nothing uploads on startup or merely because remote log viewing is enabled.
Only an explicit UI press calls publish(). No database, GGUF, credentials,
settings file, private GitHub token, arbitrary folder or shell is uploaded.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
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
MAX_PAGES = 55
MAX_REPORT_CHARS = PAGE_CHARS * MAX_PAGES
MAX_PROBE_BYTES = 4 * 1024 * 1024
TRUNCATION_NOTICE = "[EARLIER CONTENT TRUNCATED BY SIZE LIMIT]\n"

TOKEN = re.compile(r"(?i)(\b(?:gh[opusr]_[a-z0-9]{12,}|github_pat_[a-z0-9_]{12,})\b)")
BEARER = re.compile(r"(?i)(\b(?:authorization\s*:\s*bearer|bearer)\s+)[A-Za-z0-9._-]{12,}")
PASSWORD = re.compile(r"(?im)(\b(?:password|access_token|api_key|secret)\s*[:=]\s*)\S+")
LOCAL_URL = re.compile(r"http://127\.0\.0\.1:\d+/t/[a-f0-9]{48}/?")


def redact(text):
    text = TOKEN.sub("[REDACTED_CREDENTIAL]", str(text))
    text = BEARER.sub(r"\1[REDACTED_CREDENTIAL]", text)
    text = PASSWORD.sub(r"\1[REDACTED]", text)
    return LOCAL_URL.sub("http://127.0.0.1/[REDACTED_LOCAL_SESSION]", text)


def _encoded_length(text):
    return len(json.dumps(text, ensure_ascii=True)) - 2


def _limit_tail(text, max_chars, *, max_encoded=None, truncated=False):
    """Include the notice inside both the character and JSON wire bounds."""
    truncated = (truncated or len(text) > max_chars or
                 (max_encoded is not None and _encoded_length(text) > max_encoded))
    if not truncated:
        return text, False
    prefix = TRUNCATION_NOTICE
    if (len(prefix) > max_chars or
            (max_encoded is not None and _encoded_length(prefix) > max_encoded)):
        prefix = ""
    low, high = 0, min(len(text), max(0, max_chars - len(prefix)))
    while low < high:
        count = (low + high + 1) // 2
        candidate = prefix + text[-count:]
        if max_encoded is None or _encoded_length(candidate) <= max_encoded:
            low = count
        else:
            high = count - 1
    return prefix + (text[-low:] if low else ""), True


def _read_tail(path, max_chars=None):
    max_chars = MAX_FILE_CHARS if max_chars is None else max_chars
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
        return None
    with path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        offset = max(0, size - 4 * max_chars)
        stream.seek(offset)
        raw = stream.read(4 * max_chars)
    value = raw.decode("utf-8", errors="replace")
    value, truncated = _limit_tail(redact(value), max_chars,
                                  truncated=offset > 0 or len(value) > max_chars)
    return value, {"source_bytes": size, "truncated": truncated,
                   "representation": "LOG_TAIL"}


def _probe_error(error):
    if re.search(r"Zeitbudget erreicht|TimeoutError|deadline exceeded", error, re.I):
        return "TIME_BUDGET"
    if re.search(r"Abgebrochen|Cancelled|Canceled", error, re.I):
        return "CANCELLED"
    if re.search(r"FileNotFoundError|No such file or directory|Errno 2", error):
        return "MISSING_FILE"
    if re.search(r"MemoryError|out of memory|ENOMEM|\bOOM\b", error, re.I):
        return "OUT_OF_MEMORY"
    if re.search(r"ImportError|ModuleNotFoundError", error):
        return "IMPORT_ERROR"
    if re.search(r"PermissionError|Permission denied", error):
        return "PERMISSION"
    return "REDACTED_ERROR"


def _probe_numbers(source, names):
    return {name: value for name in names
            if type(value := source.get(name)) in (int, float)
            and 0 <= value <= 10**12 and math.isfinite(value)}


def _read_probe(path):
    """Preserve probe results without fragmenting JSON or copying sample arrays."""
    if path.is_symlink() or not path.is_file() or path.stat().st_uid != os.getuid():
        return None
    out = {"schema": "v13.phone-native-probe-summary/1", "summary_only": True,
           "status": "UNVERIFIED", "roles": {}}
    metadata = {"source_bytes": 0, "truncated": True,
                "representation": "NATIVE_PROBE_SUMMARY", "reason": "STRUCTURED_SUMMARY"}
    with path.open("rb") as stream:
        metadata["source_bytes"] = os.fstat(stream.fileno()).st_size
        raw = stream.read(MAX_PROBE_BYTES + 1)
    if len(raw) > MAX_PROBE_BYTES:
        out["source_status"] = "SIZE_LIMIT"
        metadata["reason"] = "SOURCE_SIZE_LIMIT"
    else:
        try:
            probe = json.loads(raw)
        except (ValueError, UnicodeError, RecursionError):
            probe = None
        if not isinstance(probe, dict):
            out["source_status"] = "INVALID_JSON"
            metadata["reason"] = "INVALID_SOURCE"
        else:
            out["source_status"] = "PARSED"
            status = probe.get("status")
            if status in ("SMOKE_PASS", "SMOKE_PARTIAL", "SMOKE_FAIL"):
                out["status"] = status
            for name in ("full_runner_proof", "phone_measured"):
                if type(probe.get(name)) is bool:
                    out[name] = probe[name]
            cfg = probe.get("effective_config")
            if isinstance(cfg, dict):
                out["effective_config"] = _probe_numbers(cfg, (
                    "deadline_seconds", "observer_seconds", "threads", "answer_tokens"))
            roles = probe.get("roles")
            if isinstance(roles, dict):
                for role in ("C3_LANGUAGE", "B1_DETAIL", "B2_GIST", "C2_CONTROL"):
                    source = roles.get(role)
                    if not isinstance(source, dict):
                        continue
                    item = {"ok": source.get("ok") if type(source.get("ok")) is bool else None}
                    item.update(_probe_numbers(source, (
                        "duration_s", "embedding_dim", "embedding_squared_norm")))
                    if isinstance(source.get("error"), str):
                        item.update(error_present=True, error_kind=_probe_error(source["error"]))
                    metrics = source.get("metrics")
                    if isinstance(metrics, dict):
                        item["metrics"] = _probe_numbers(metrics, (
                            "duration_s", "ttft_s", "generated_tokens", "prompt_tokens",
                            "requested_tokens", "resource_sample_count",
                            "sampled_peak_rss_bytes", "sampled_peak_pss_bytes"))
                        if metrics.get("status") in ("FINAL", "ERROR", "DEADLINE", "CANCELLED"):
                            item["metrics"]["status"] = metrics["status"]
                    out["roles"][role] = item
    return json.dumps(out, ensure_ascii=True, sort_keys=True, separators=(",", ":")), metadata


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
              "files": {}, "file_metadata": {}, "truncated": False,
              "total_transmitted_chars": 0}
    total = 0
    for name, path in _logs(home, private, full):
        entry = _read_probe(path) if name == "native-probe.json" else _read_tail(path)
        if entry is None:
            continue
        text, metadata = entry
        if not full and name != "native-probe.json":
            # Only error lines in technical mode, never arbitrary transcript.
            lines = text.splitlines()
            errors = [line for line in lines if re.match(
                r"(?i)^(?:\[V13 Fehler\]|\[Fehler\]|\[V13 exited with code|"
                r".{0,72}(?:Traceback|FileNotFoundError|TimeoutError|"
                r"PermissionError|PIPELINE_ERROR|ERROR:|SMOKE_PARTIAL))", line)]
            text = "\n".join(errors[-100:])
            metadata["truncated"] |= len(errors) > 100
        if not text and not metadata["truncated"]:
            continue
        report["file_metadata"][name] = metadata
        report["files"][name] = ""
        # ensure_ascii can expand one Unicode character to twelve wire
        # characters. Reserve the final counter and metadata before fitting
        # each attachment, so a bounded log cannot make the whole send fail.
        report["total_transmitted_chars"] = MAX_TOTAL_CHARS
        overhead = len(json.dumps(report, ensure_ascii=True, sort_keys=True,
                                  separators=(",", ":")))
        # Leave space for metadata of later attachments even when this one
        # consumes the remaining payload budget.
        wire_budget = MAX_REPORT_CHARS - overhead - 256 * MAX_FILES
        char_budget = min(MAX_FILE_CHARS, max(0, MAX_TOTAL_CHARS - total))
        if name == "native-probe.json":
            # A structured document must stay independently parseable.
            if len(text) > char_budget or _encoded_length(text) > wire_budget:
                text = ""
                metadata["omitted"] = True
        else:
            text, shortened = _limit_tail(text, char_budget,
                                          max_encoded=max(0, wire_budget))
            metadata["truncated"] |= shortened
        if text:
            report["files"][name] = text
        else:
            del report["files"][name]
            metadata["omitted"] = True
            metadata["truncated"] = True
        report["truncated"] |= metadata["truncated"] or metadata.get("omitted", False)
        total += len(text)
    report["total_transmitted_chars"] = total
    if len(json.dumps(report, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"))) > MAX_REPORT_CHARS:
        raise ValueError("diagnostic metadata exceeds private relay bound")
    return report


def _pages(report):
    raw = json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    # Split on character boundaries after escaping; each payload is independent
    # and reassembled by page/index, not as unauthenticated commands.
    pages = [raw[i:i+PAGE_CHARS] for i in range(0, len(raw), PAGE_CHARS)]
    if len(pages) > MAX_PAGES:
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
            "truncated": report["truncated"],
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
