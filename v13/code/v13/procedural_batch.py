"""V13 compiled-procedure fast lane: deterministic output without any LLM forward pass.

Cerebellar fast path for known *pure* repetition. Unlike fastforward.py (which
optimises route/wake), this module emits output bytes. It never executes shell,
Python, tools, network requests or model calls. Plans are local-operator
proposals and require an explicit digest-bound activation.

Each output checkpoint records a committed row cursor, byte count and SHA-256
of the committed prefix. On resume, valid extra bytes from an interrupted
append are truncated; an altered committed prefix is rejected. All files stay
under the private V13 home. This is NOT evidence of learned reasoning or AGI.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import fcntl
import stat
from contextlib import contextmanager
import string
import tempfile
import time
from pathlib import Path

REVISION = "v13-procedural-batch-v1"
MAX_ROWS = 1_000_000
MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_TEMPLATE_BYTES = 4096
MAX_VALUE_BYTES = 1024
CHUNK_ROWS = 2048
MAX_SECONDS_PER_CALL = 12.0
_NAME = re.compile(r"[a-z][a-z0-9_]{1,39}\Z")
_FIELDS = {"i", "value"}


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(obj):
    return hashlib.sha256(_canonical(obj)).hexdigest()


def _check_path(path: Path):
    if path.is_symlink():
        raise ValueError("symbolic links are not allowed in procedural storage")


@contextmanager
def _job_guard(state_file: Path):
    """One same-job writer or reader at a time; different jobs stay parallel.

    A second concurrent operation fails promptly rather than blocking a
    terminal or corrupting the checkpoint after a replay/write crash.
    POSIX advisory locks are supported by Linux and Android Termux.
    """
    lock = state_file.with_suffix(".lock")
    _check_path(lock)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(lock, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("unsafe fastbatch job lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("fastbatch job busy; retry after checkpoint") from exc
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _save(path: Path, payload):
    """Durable atomic JSON replacement, not one state-file write per row."""
    _check_path(path)
    encoded = _canonical(payload)
    fd, tmp = tempfile.mkstemp(prefix="._fastbatch_", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(encoded)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _read(path: Path):
    _check_path(path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    if path.stat().st_size > 16384:
        raise ValueError("oversized fastbatch metadata")
    data = json.loads(path.read_text("utf-8"))
    if type(data) is not dict:
        raise ValueError("invalid fastbatch metadata")
    return data


def _name(name):
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValueError("fastbatch names: [a-z][a-z0-9_]{1,39}")
    return name


def _parts(template):
    """Compile a literal template: only {i}, {value}, {{ and }}.

    The parser does not evaluate attributes, indexing, expressions, code or
    format strings. Compile once per run, never reparse for each output row.
    """
    if not isinstance(template, str) or not template:
        raise ValueError("nonempty text template required")
    if len(template.encode("utf-8")) > MAX_TEMPLATE_BYTES:
        raise ValueError("template too long")
    out = []
    try:
        for literal, field, spec, conversion in string.Formatter().parse(template):
            if field is not None and (field not in _FIELDS or spec or conversion):
                raise ValueError("only {i} and {value} are allowed")
            out.append((literal, field))
    except ValueError as exc:
        raise ValueError("invalid deterministic template") from exc
    return out


def _render(parts, index, value):
    number = str(index)
    return "".join(a + (number if b == "i" else value if b == "value" else "")
                   for a, b in parts) + "\n"


class ProceduralBatch:
    """Local, reviewable, bounded and resumable compiled text batch executor."""

    def __init__(self, home, store=None):
        self.store = store  # current authoritative V13 Store; optional for manual plans
        self.root = Path(home) / "procedures" / "fastbatch"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        _check_path(self.root)
        self.plans = self.root / "plans"
        self.jobs = self.root / "jobs"
        for path in (self.plans, self.jobs):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)
            _check_path(path)

    def _plan_path(self, name):
        return self.plans / (_name(name) + ".json")

    def propose(self, name, template, evidence=None):
        _parts(template)
        if evidence is not None:
            # Exact source hashes and ids, not private chat text, bind this
            # inferred candidate to the completed source traces.
            if type(evidence) is not dict or set(evidence) != {
                "method", "kind", "source_event_ids", "source_output_sha256",
                "observed_rows", "validation", "scope"
            }:
                raise ValueError("invalid source-trace evidence")
            ids, digests, counts = (evidence["source_event_ids"],
                                    evidence["source_output_sha256"],
                                    evidence["observed_rows"])
            if (evidence["method"] != "EXACT_FINAL_HISTORY_REPLAY_V1"
                    or evidence["kind"] not in (
                        "LITERAL_NUMBERED_REPEAT", "PARAMETRIC_NUMBERED_REPEAT")
                    or evidence["validation"] != "BYTE_EXACT_BEFORE_PROPOSE"
                    or evidence["scope"] != "CURRENT_SESSION_ONLY"
                    or type(ids) is not list or not 1 <= len(ids) <= 3
                    or len(set(ids)) != len(ids)
                    or any(type(x) is not str or not re.fullmatch(
                        r"[A-Za-z0-9_-]{1,96}", x) for x in ids)
                    or type(digests) is not list or len(digests) != len(ids)
                    or any(type(x) is not str or not re.fullmatch(
                        r"[0-9a-f]{64}", x) for x in digests)
                    or type(counts) is not list or len(counts) != len(ids)
                    or any(type(n) is not int or not 4 <= n <= 64 for n in counts)):
                raise ValueError("invalid or unbound source-trace evidence")
        path = self._plan_path(name)
        if path.exists() or path.is_symlink():
            raise ValueError("plan exists; use a new revision name")
        code = {"revision": REVISION, "name": name, "kind": "PURE_TEXT_REPEAT",
                "template": template}
        if evidence is not None:
            code["source_evidence"] = evidence  # digest-bound to plan activation
        plan = {"code": code, "sha256": _sha(code), "stage": "CANDIDATE",
                "authority": "LOCAL_OPERATOR_ONLY"}
        _save(path, plan)
        return {"name": name, "stage": plan["stage"], "sha256": plan["sha256"],
                "variables": sorted(_FIELDS), "model_calls": 0}

    def plan(self, name):
        plan = _read(self._plan_path(name))
        code = plan.get("code")
        if (not isinstance(code, dict) or code.get("name") != name
                or code.get("revision") != REVISION
                or code.get("kind") != "PURE_TEXT_REPEAT"
                or _sha(code) != plan.get("sha256")
                or plan.get("stage") not in ("CANDIDATE", "ACTIVE", "RETIRED")):
            raise ValueError("tampered or unsupported compiled plan")
        _parts(code.get("template"))
        return plan

    def _verify_evidence(self, plan):
        """Recheck FINAL source state before using a learned plan.

        Deleted sources, replaced outputs and revoked final status must never
        survive as executable learned habits. The check is per invocation,
        never inside the per-row hot loop. Manually approved literal plans
        have no Store evidence and retain the original low-latency path.
        """
        evidence = plan["code"].get("source_evidence")
        if evidence is None:
            return
        if self.store is None:
            raise PermissionError("source-discovered plans require the live V13 Store")
        for event_id, sha256 in zip(evidence["source_event_ids"],
                                    evidence["source_output_sha256"]):
            rows = self.store.rows(
                "SELECT m.text,m.status,s.deleted FROM messages m "
                "JOIN events e ON e.id=m.event_id "
                "JOIN sources s ON s.id=e.source_id "
                "WHERE m.event_id=? AND m.role='assistant' "
                "ORDER BY m.id DESC LIMIT 1", (event_id,))
            if (len(rows) != 1 or rows[0]["status"] != "FINAL"
                    or rows[0]["deleted"] != 0):
                raise ValueError("learned procedure source is no longer FINAL/authoritative")
            if hashlib.sha256(rows[0]["text"].encode("utf-8")).hexdigest() != sha256:
                raise ValueError("learned procedure source changed since review")

    def activate(self, name, digest_prefix):
        plan = self.plan(name)
        if (not isinstance(digest_prefix, str) or len(digest_prefix) < 12
                or not plan["sha256"].startswith(digest_prefix)):
            raise ValueError("activation requires matching plan SHA256 prefix (12+ chars)")
        if plan["stage"] == "RETIRED":
            raise ValueError("retired plan cannot reactivate")
        self._verify_evidence(plan)
        plan["stage"] = "ACTIVE"
        _save(self._plan_path(name), plan)
        return {"name": name, "stage": "ACTIVE", "sha256": plan["sha256"]}

    def retire(self, name):
        plan = self.plan(name)
        plan["stage"] = "RETIRED"
        _save(self._plan_path(name), plan)
        return {"name": name, "stage": "RETIRED"}

    def _job_files(self, plan, count, value):
        if type(count) is not int or not 1 <= count <= MAX_ROWS:
            raise ValueError("count must be 1..1000000")
        if not isinstance(value, str) or len(value.encode("utf-8")) > MAX_VALUE_BYTES:
            raise ValueError("value too long")
        job_id = _sha([plan["sha256"], count, value])[:24]
        stem = plan["code"]["name"] + "_" + job_id
        return self.jobs / (stem + ".json"), self.jobs / (stem + ".txt"), job_id

    def _load_or_start(self, plan, count, value):
        state_file, output_file, jid = self._job_files(plan, count, value)
        _check_path(state_file)
        _check_path(output_file)
        if state_file.exists():
            state = _read(state_file)
            required = {"revision": REVISION, "plan_sha256": plan["sha256"],
                        "job_id": jid, "count": count, "value": value}
            if any(state.get(key) != expected for key, expected in required.items()):
                raise ValueError("job source or parameters changed")
            rows, size = state.get("rows"), state.get("bytes")
            if (type(rows) is not int or not 0 <= rows <= count
                    or type(size) is not int or not 0 <= size <= MAX_OUTPUT_BYTES
                    or not re.fullmatch(r"[0-9a-f]{64}", str(state.get("sha256")))):
                raise ValueError("corrupt job checkpoint")
        else:
            if output_file.exists() or output_file.is_symlink():
                raise ValueError("orphan output file; will not overwrite")
            state = {"revision": REVISION, "plan_sha256": plan["sha256"], "job_id": jid,
                     "count": count, "value": value, "rows": 0, "bytes": 0,
                     "sha256": hashlib.sha256(b"").hexdigest(), "status": "PAUSED"}
            _save(state_file, state)
        return state_file, output_file, state

    @staticmethod
    def _verify_prefix(output_file, state):
        """Read the committed prefix just once per *invocation*, not per row."""
        _check_path(output_file)
        expected = state["bytes"]
        digest = hashlib.sha256()
        if not output_file.exists():
            if expected:
                raise ValueError("missing committed output")
            return digest
        with output_file.open("r+b") as f:
            available = f.seek(0, os.SEEK_END)
            if available < expected:
                raise ValueError("truncated committed output")
            f.seek(0)
            remaining = expected
            while remaining:
                data = f.read(min(1024 * 1024, remaining))
                if not data:
                    raise ValueError("truncated checkpoint")
                digest.update(data)
                remaining -= len(data)
            if digest.hexdigest() != state["sha256"]:
                raise ValueError("committed output hash mismatch")
            if available > expected:
                # Crash after append+fsync but before durable JSON commit:
                # discard ONLY the uncommitted tail.
                f.truncate(expected)
                f.flush()
                os.fsync(f.fileno())
        return digest

    def run(self, name, count, value="", max_rows=None, max_seconds=MAX_SECONDS_PER_CALL):
        plan = self.plan(name)
        state_file, _, _ = self._job_files(plan, count, value)
        with _job_guard(state_file):
            return self._run_locked(name, count, value, max_rows, max_seconds)

    def _run_locked(self, name, count, value="", max_rows=None, max_seconds=MAX_SECONDS_PER_CALL):
        plan = self.plan(name)
        if plan["stage"] != "ACTIVE":
            raise PermissionError("compiled plan requires explicit local activation")
        self._verify_evidence(plan)
        max_rows = MAX_ROWS if max_rows is None else max_rows
        if type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS:
            raise ValueError("max_rows must be a positive integer")
        if type(max_seconds) not in (int, float) or not 0 < max_seconds <= 120:
            raise ValueError("max_seconds must be in (0,120]")
        parts = _parts(plan["code"]["template"])
        state_file, output_file, state = self._load_or_start(plan, count, value)
        digest = self._verify_prefix(output_file, state)
        started = time.monotonic()
        until = min(count, state["rows"] + max_rows)
        rows_before = state["rows"]
        bytes_before = state["bytes"]
        while state["rows"] < until and time.monotonic() - started < max_seconds:
            # Revocation may arrive while a long learned habit is running.
            # Revalidate at checkpoint/chunk boundaries, NEVER every row;
            # manual literal plans stay on the original zero-DB hot path.
            if plan["code"].get("source_evidence"):
                self._verify_evidence(plan)
            end = min(until, state["rows"] + CHUNK_ROWS)
            # One in-memory chunk and one durable write per ~2K rows.
            chunk = "".join(_render(parts, i, value)
                            for i in range(state["rows"] + 1, end + 1)).encode("utf-8")
            if state["bytes"] + len(chunk) > MAX_OUTPUT_BYTES:
                raise ValueError("max 64MiB output; split into smaller jobs")
            _check_path(output_file)
            with output_file.open("ab") as out:
                out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            digest.update(chunk)
            state["rows"], state["bytes"] = end, state["bytes"] + len(chunk)
            state["sha256"] = digest.hexdigest()
            state["status"] = "DONE" if end == count else "PAUSED"
            _save(state_file, state)
        seconds = max(1e-9, time.monotonic() - started)
        generated = state["rows"] - rows_before
        return {"status": state["status"], "name": name, "job_id": state["job_id"],
                "rows": state["rows"], "total_rows": count,
                "rows_this_call": generated, "bytes": state["bytes"],
                "bytes_this_call": state["bytes"] - bytes_before,
                "rows_per_second": round(generated / seconds, 1),
                "bytes_per_second": round((state["bytes"] - bytes_before) / seconds, 1),
                "sha256": state["sha256"], "output_path": str(output_file),
                "model_calls": 0, "claim_limit": "Pure compiled output; not LLM tokens or general reasoning"}

    def preview(self, name, count, value="", max_chars=256):
        plan = self.plan(name)
        state_file, _, _ = self._job_files(plan, count, value)
        with _job_guard(state_file):
            return self._preview_locked(name, count, value, max_chars)

    def _preview_locked(self, name, count, value="", max_chars=256):
        plan = self.plan(name)
        self._verify_evidence(plan)
        state_file, output_file, state = self._load_or_start(plan, count, value)
        self._verify_prefix(output_file, state)
        if type(max_chars) is not int or not 0 <= max_chars <= 4096:
            raise ValueError("preview cap 0..4096")
        if not output_file.exists():
            return {"rows": 0, "preview": ""}
        with output_file.open("rb") as f:
            raw = f.read(min(state["bytes"], max_chars * 4))
        return {"rows": state["rows"], "preview": raw.decode("utf-8", errors="ignore")[:max_chars],
                "truncated": state["bytes"] > len(raw)}

    def read(self, name, count, value="", cursor=0, max_bytes=16384):
        plan = self.plan(name)
        state_file, _, _ = self._job_files(plan, count, value)
        with _job_guard(state_file):
            return self._read_locked(name, count, value, cursor, max_bytes)

    def _read_locked(self, name, count, value="", cursor=0, max_bytes=16384):
        """Read a verified UTF-8 slice of *committed* output, not draft bytes.

        This is the bounded operator/GUI pull interface. It never runs a
        model, generates additional rows, or advances a persisted cursor.
        For high-throughput consumers, iter_output() below hashes once per
        stream instead of rescanning the whole output on every slice.
        """
        if type(cursor) is not int or cursor < 0:
            raise ValueError("cursor must be a nonnegative byte offset")
        if type(max_bytes) is not int or not 4 <= max_bytes <= 65536:
            raise ValueError("read bytes must be 4..65536")
        plan = self.plan(name)
        if plan["stage"] != "ACTIVE":
            raise PermissionError("compiled plan requires explicit local activation")
        self._verify_evidence(plan)
        state_file, output_file, jid = self._job_files(plan, count, value)
        _check_path(state_file)
        if not state_file.is_file():
            raise FileNotFoundError("run procedure before reading its output")
        _, output_file, state = self._load_or_start(plan, count, value)
        self._verify_prefix(output_file, state)
        if cursor > state["bytes"]:
            raise ValueError("cursor beyond committed output")
        if not output_file.exists():
            raw = b""
        else:
            with output_file.open("rb") as f:
                f.seek(cursor)
                first = f.read(1)
                if first and first[0] & 0xC0 == 0x80:
                    raise ValueError("cursor splits a UTF-8 code point")
                f.seek(cursor)
                raw = f.read(min(max_bytes, state["bytes"] - cursor))
        if raw:
            try:
                output = raw.decode("utf-8")
            except UnicodeDecodeError as err:
                if err.reason != "unexpected end of data" or err.end != len(raw):
                    raise ValueError("corrupt committed UTF-8 output") from err
                raw = raw[:err.start]
                if not raw:
                    raise ValueError("read window cannot hold one UTF-8 code point")
                output = raw.decode("utf-8")
        else:
            output = ""
        next_cursor = cursor + len(raw)
        return {
            "status": state["status"], "job_id": jid, "name": name,
            "cursor_bytes": cursor, "next_cursor_bytes": next_cursor,
            "committed_bytes": state["bytes"],
            "more_committed": next_cursor < state["bytes"],
            "needs_run": next_cursor == state["bytes"] and state["status"] != "DONE",
            "text": output, "model_calls": 0,
            "sha256": state["sha256"],
        }

    def iter_output(self, name, count, value="", chunk_bytes=16384):
        plan = self.plan(name)
        state_file, _, _ = self._job_files(plan, count, value)
        with _job_guard(state_file):
            yield from self._iter_output_locked(name, count, value, chunk_bytes)

    def _iter_output_locked(self, name, count, value="", chunk_bytes=16384):
        """Yield all committed output with one initial prefix verification.

        The generator cannot execute models or tools. Underlying file bytes
        are checked against the saved SHA-256 before first yield. Clients
        should not use this as authorization to continue if source is revoked
        mid-stream; it is a snapshot of the committed prefix at entry.
        """
        if type(chunk_bytes) is not int or not 4 <= chunk_bytes <= 65536:
            raise ValueError("chunk bytes must be 4..65536")
        plan = self.plan(name)
        if plan["stage"] != "ACTIVE":
            raise PermissionError("compiled plan requires explicit local activation")
        self._verify_evidence(plan)
        state_file, output_file, _ = self._job_files(plan, count, value)
        _check_path(state_file)
        if not state_file.is_file():
            raise FileNotFoundError("run procedure before reading its output")
        _, output_file, state = self._load_or_start(plan, count, value)
        self._verify_prefix(output_file, state)
        expected = state["bytes"]
        if not expected:
            return
        with output_file.open("rb") as f:
            pending = b""
            read_total = 0
            while read_total < expected:
                block = f.read(min(chunk_bytes, expected - read_total))
                if not block:
                    raise ValueError("committed output truncated during streaming")
                read_total += len(block)
                pending += block
                try:
                    value_text = pending.decode("utf-8")
                    pending = b""
                except UnicodeDecodeError as exc:
                    if exc.reason != "unexpected end of data" or exc.end != len(pending):
                        raise ValueError("invalid committed UTF-8 during streaming") from exc
                    value_text = pending[:exc.start].decode("utf-8")
                    pending = pending[exc.start:]
                if value_text:
                    # A long-lived consumer may pause between chunks while
                    # the originating chat source is deleted. Never stream
                    # another chunk from a learned habit after revocation.
                    # Manual explicitly authored plans incur zero DB reads.
                    if plan["code"].get("source_evidence"):
                        self._verify_evidence(plan)
                    yield value_text
            if pending:
                raise ValueError("trailing invalid UTF-8 in committed output")

    def status(self, name=None):
        if name is not None:
            p = self.plan(name)
            return {"name": name, "stage": p["stage"], "sha256": p["sha256"],
                    "kind": p["code"]["kind"]}
        out = []
        for path in sorted(self.plans.glob("*.json"))[:256]:
            _check_path(path)
            plan = self.plan(path.stem)
            out.append({"name": path.stem, "stage": plan["stage"],
                        "sha256_prefix": plan["sha256"][:12]})
        return {"revision": REVISION, "plans": out, "model_calls": 0,
                "limits": {"rows": MAX_ROWS, "output_bytes": MAX_OUTPUT_BYTES}}


def operator_command(runtime, args):
    """:fastbatch propose NAME 'text {i}: {value}' | discover NAME [--history=N] | activate NAME SHA |
    run NAME COUNT [VALUE] [--rows=N] | read NAME COUNT [VALUE] [--cursor=OFFSET] [--bytes=SIZE] |
    peek NAME COUNT [VALUE] | status [NAME] | retire NAME. Only local operator dispatch can reach here.
    """
    runner = ProceduralBatch(runtime.home, store=runtime.store)
    if not args or args[0] == "status":
        if len(args) > 2:
            raise ValueError(":fastbatch status [NAME]")
        return runner.status(args[1] if len(args) == 2 else None)
    cmd = args[0]
    if cmd == "propose" and len(args) == 3:
        return runner.propose(args[1], args[2])
    if cmd == "discover" and len(args) in (2, 3):
        from .procedural_habits import discover
        limit = 16
        if len(args) == 3:
            if not re.fullmatch(r"--history=[1-9][0-9]?", args[2]):
                raise ValueError(":fastbatch discover NAME [--history=1..64]")
            limit = int(args[2].split("=", 1)[1])
        return discover(runtime, args[1], limit)
    if cmd == "activate" and len(args) == 3:
        return runner.activate(args[1], args[2])
    if cmd == "retire" and len(args) == 2:
        return runner.retire(args[1])
    if cmd == "read" and 3 <= len(args) <= 6:
        name, count = args[1], int(args[2])
        opts = args[3:]
        positions = [x for x in opts if not x.startswith("--")]
        cursor_opts = [x for x in opts if x.startswith("--cursor=")]
        bytes_opts = [x for x in opts if x.startswith("--bytes=")]
        if (len(positions) > 1 or len(cursor_opts) > 1 or len(bytes_opts) > 1
                or len(opts) != len(positions) + len(cursor_opts) + len(bytes_opts)):
            raise ValueError("read NAME COUNT [VALUE] [--cursor=OFFSET] [--bytes=SIZE]")
        value = positions[0] if positions else ""
        cursor = int(cursor_opts[0].split("=", 1)[1]) if cursor_opts else 0
        amount = int(bytes_opts[0].split("=", 1)[1]) if bytes_opts else 16384
        return runner.read(name, count, value, cursor, amount)
    if cmd in ("run", "peek") and 3 <= len(args) <= 5:
        name = args[1]
        count = int(args[2])
        others = args[3:]
        opts = [s for s in others if s.startswith("--rows=")]
        values = [s for s in others if not s.startswith("--rows=")]
        if len(opts) > 1 or len(values) > 1:
            raise ValueError("one value and at most one --rows=N")
        value = values[0] if values else ""
        if cmd == "peek":
            if opts:
                raise ValueError("peek does not take --rows")
            return runner.preview(name, count, value)
        limit = int(opts[0].split("=", 1)[1]) if opts else None
        return runner.run(name, count, value, max_rows=limit)
    raise ValueError(":fastbatch propose NAME TEMPLATE | discover NAME [--history=N] | activate NAME SHA | run NAME COUNT [VALUE] [--rows=N] | read NAME COUNT [VALUE] [--cursor=OFFSET] [--bytes=SIZE] | peek NAME COUNT [VALUE] | status [NAME] | retire NAME")
