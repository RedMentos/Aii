"""SHA-bound UTF-8 line inputs for reviewed zero-LLM V13 procedures.

Local operator explicitly imports a known file (requires its exact SHA-256).
Rows are stored privately, read only with prechecked provenance, and repeated
through an explicitly activated pure {i}/{value} template. No model, shell,
external tools, Python eval, or automatic learned-task activation.

The per-job input/output prefix hashes, byte offsets and row cursor checkpoint
together, allowing a stopped stream to resume without duplicating any rows.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
import time

from .procedural_batch import (
    MAX_OUTPUT_BYTES, MAX_ROWS, MAX_SECONDS_PER_CALL, MAX_VALUE_BYTES,
    CHUNK_ROWS, ProceduralBatch, _canonical, _check_path, _job_guard,
    _name, _parts, _read, _render, _save, _sha, _utf8_slice, _iter_utf8_chunks,
)

REVISION = "v13-procedural-input-lines-v1"
MAX_INPUT_BYTES = 64 * 1024 * 1024
HASH = re.compile(r"[0-9a-f]{64}\Z")


def _line(raw):
    if not raw or len(raw) > MAX_VALUE_BYTES + 1 or not raw.endswith(b"\n"):
        raise ValueError("input requires bounded newline-terminated UTF-8 rows")
    try:
        value = raw[:-1].decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("input contains invalid UTF-8") from exc
    if not value or "\r" in value or "\x00" in value:
        raise ValueError("empty/CR/NUL input row")
    return value


def _verify_fd(source, metadata, offset=0, prefix_sha=None):
    """Bind the SAME open source descriptor to full+committed prefix hashes."""
    source.seek(0)
    total = 0
    digest = hashlib.sha256()
    prefix = hashlib.sha256()
    remain = offset
    while True:
        block = source.read(1024 * 1024)
        if not block:
            break
        total += len(block)
        if total > MAX_INPUT_BYTES:
            raise ValueError("input exceeds 64MiB cap")
        digest.update(block)
        if remain:
            portion = block[:remain]
            prefix.update(portion)
            remain -= len(portion)
    if total != metadata["bytes"] or digest.hexdigest() != metadata["sha256"]:
        raise ValueError("imported source bytes changed")
    if remain or (prefix_sha is not None and prefix.hexdigest() != prefix_sha):
        raise ValueError("input checkpoint cursor or prefix hash mismatch")
    source.seek(offset)
    return prefix


class ProceduralInputs:
    """Private input bank with source-bound, checkpointable fast transforms."""

    def __init__(self, home, store=None):
        self.batch = ProceduralBatch(home, store=store)
        self.root = self.batch.root / "inputs"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        _check_path(self.root)

    def _meta_path(self, name):
        return self.root / (_name(name) + ".json")

    def _input_path(self, name):
        return self.root / (_name(name) + ".txt")

    def import_file(self, name, source, expected_sha256):
        """Import an explicitly reviewed local file; never execute its content."""
        _name(name)
        if type(expected_sha256) is not str or not HASH.fullmatch(expected_sha256):
            raise ValueError("explicit full source SHA-256 required")
        input_path = Path(source)
        if (input_path.is_symlink() or not input_path.is_file()
                or input_path.resolve().is_relative_to(self.root.resolve())):
            raise ValueError("source must be an external ordinary regular file")
        meta_path, target = self._meta_path(name), self._input_path(name)
        _check_path(meta_path)
        _check_path(target)
        with _job_guard(meta_path):
            if meta_path.exists() or target.exists():
                raise ValueError("input name exists; import as a new revision")
            # The source file is opened once with no symlink following, so
            # replacing its *path* cannot swap the bytes halfway through.
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(input_path, flags)
            tmp = None
            try:
                info = os.fstat(fd)
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or info.st_size > MAX_INPUT_BYTES):
                    raise ValueError("unsafe or oversized input source")
                tmp_fd, tmp_name = tempfile.mkstemp(prefix=".input-", dir=self.root)
                tmp = Path(tmp_name)
                h = hashlib.sha256()
                size, count = 0, 0
                with os.fdopen(tmp_fd, "wb") as out, os.fdopen(fd, "rb") as src:
                    fd = -1
                    while True:
                        raw = src.readline(MAX_VALUE_BYTES + 2)
                        if not raw:
                            break
                        _line(raw)
                        size += len(raw)
                        count += 1
                        if size > MAX_INPUT_BYTES or count > MAX_ROWS:
                            raise ValueError("input limits exceeded")
                        h.update(raw)
                        out.write(raw)
                    out.flush()
                    os.fsync(out.fileno())
                # Check the complete digest before publishing ANY final input.
                if not count or h.hexdigest() != expected_sha256:
                    raise ValueError("input digest mismatch or empty input")
                if target.exists() or target.is_symlink():
                    raise ValueError("input target appeared during import")
                os.chmod(tmp, 0o400)
                os.replace(tmp, target)
                tmp = None
                payload = {
                    "revision": REVISION, "name": name,
                    "sha256": h.hexdigest(), "bytes": size, "rows": count,
                    "format": "UTF8_NEWLINE_VALUES_OPERATOR_IMPORTED",
                    "model_calls": 0,
                }
                payload["metadata_sha256"] = _sha(payload)
                _save(meta_path, payload)
                return {
                    "name": name, "rows": count, "bytes": size,
                    "sha256": h.hexdigest(), "status": "IMPORTED",
                    "model_calls": 0,
                }
            finally:
                if fd >= 0:
                    os.close(fd)
                if tmp is not None and tmp.exists():
                    tmp.unlink()

    def _metadata(self, name):
        p = _read(self._meta_path(name))
        if type(p) is not dict or p.get("name") != name or p.get("revision") != REVISION:
            raise ValueError("invalid input metadata")
        sig = p.get("metadata_sha256")
        body = dict(p)
        body.pop("metadata_sha256", None)
        if (type(sig) is not str or sig != _sha(body)
                or type(p.get("sha256")) is not str
                or not HASH.fullmatch(p["sha256"])
                or type(p.get("bytes")) is not int
                or not 1 <= p["bytes"] <= MAX_INPUT_BYTES
                or type(p.get("rows")) is not int
                or not 1 <= p["rows"] <= MAX_ROWS
                or p.get("format") != "UTF8_NEWLINE_VALUES_OPERATOR_IMPORTED"):
            raise ValueError("invalid or tampered input metadata")
        return p

    def _open_imported(self, name):
        source_path = self._input_path(name)
        _check_path(source_path)
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(source_path, flags)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            os.close(fd)
            raise ValueError("unsafe imported source file")
        return os.fdopen(fd, "rb")

    def status(self, name):
        meta = self._metadata(name)
        with self._open_imported(name) as source:
            _verify_fd(source, meta)
        return {**{k: meta[k] for k in ("name", "sha256", "bytes", "rows", "model_calls")},
                "source_bytes_verified": True}

    def _job_files(self, plan, name, meta):
        job_id = _sha(["INPUT_LINES", plan["sha256"], name, meta["sha256"]])[:24]
        stem = "input_" + plan["code"]["name"] + "_" + name + "_" + job_id
        return self.batch.jobs / (stem + ".json"), self.batch.jobs / (stem + ".txt"), job_id

    def _load_job(self, state_file, output_file, plan, name, meta, job_id):
        _check_path(state_file)
        _check_path(output_file)
        fields = {
            "revision": REVISION, "job_id": job_id,
            "plan_sha256": plan["sha256"],
            "input_sha256": meta["sha256"], "input_name": name,
            "total_rows": meta["rows"],
        }
        if state_file.exists():
            state = _read(state_file)
            if any(state.get(k) != v for k, v in fields.items()):
                raise ValueError("source plan or input changed")
            if (type(state.get("rows")) is not int
                    or not 0 <= state["rows"] <= meta["rows"]
                    or type(state.get("input_offset")) is not int
                    or not 0 <= state["input_offset"] <= meta["bytes"]
                    or type(state.get("bytes")) is not int
                    or not 0 <= state["bytes"] <= MAX_OUTPUT_BYTES
                    or type(state.get("input_prefix_sha256")) is not str
                    or not HASH.fullmatch(state["input_prefix_sha256"])
                    or type(state.get("sha256")) is not str
                    or not HASH.fullmatch(state["sha256"])
                    or state.get("status") not in ("PAUSED", "DONE")):
                raise ValueError("corrupted input transformation checkpoint")
        else:
            if output_file.exists() or output_file.is_symlink():
                raise ValueError("orphan output; refusing overwrite")
            state = {
                **fields, "rows": 0, "input_offset": 0,
                "input_prefix_sha256": hashlib.sha256(b"").hexdigest(),
                "bytes": 0, "sha256": hashlib.sha256(b"").hexdigest(),
                "status": "PAUSED",
            }
            _save(state_file, state)
        return state

    def read(self, plan_name, input_name, cursor=0, max_bytes=16384):
        """Return next committed UTF-8 slice; never advance output or train."""
        plan = self.batch.plan(plan_name)
        if plan["stage"] != "ACTIVE":
            raise PermissionError("activate the template with its SHA first")
        self.batch._verify_evidence(plan)
        meta = self._metadata(input_name)
        state_file, output_file, jid = self._job_files(plan, input_name, meta)
        with _job_guard(state_file):
            if not state_file.is_file():
                raise FileNotFoundError("run input procedure before reading output")
            state = self._load_job(state_file, output_file, plan, input_name, meta, jid)
            with self._open_imported(input_name) as source:
                _verify_fd(source, meta, state["input_offset"],
                           state["input_prefix_sha256"])
            self.batch._verify_prefix(output_file, state)
            text, next_cursor = _utf8_slice(output_file, state["bytes"],
                                             cursor, max_bytes)
            return {
                "status": state["status"], "job_id": jid,
                "name": plan_name, "input_name": input_name,
                "cursor_bytes": cursor, "next_cursor_bytes": next_cursor,
                "committed_bytes": state["bytes"],
                "more_committed": next_cursor < state["bytes"],
                "needs_run": next_cursor == state["bytes"] and state["status"] != "DONE",
                "text": text, "sha256": state["sha256"], "model_calls": 0,
            }

    def iter_output(self, plan_name, input_name, chunk_bytes=16384):
        """One source/prefix verification per streamed snapshot, no model.

        Unlike repeated :input read calls, reading a long document does not
        re-hash all earlier bytes on each output chunk. Any revocation of a
        learned template's FINAL source is checked before each yield.
        """
        plan = self.batch.plan(plan_name)
        if plan["stage"] != "ACTIVE":
            raise PermissionError("activate the template with its SHA first")
        self.batch._verify_evidence(plan)
        meta = self._metadata(input_name)
        state_file, output_file, jid = self._job_files(plan, input_name, meta)
        with _job_guard(state_file):
            if not state_file.is_file():
                raise FileNotFoundError("run input procedure before streaming output")
            state = self._load_job(state_file, output_file, plan, input_name, meta, jid)
            with self._open_imported(input_name) as source:
                _verify_fd(source, meta, state["input_offset"],
                           state["input_prefix_sha256"])
            self.batch._verify_prefix(output_file, state)
            for text in _iter_utf8_chunks(output_file, state["bytes"], chunk_bytes):
                if plan["code"].get("source_evidence"):
                    self.batch._verify_evidence(plan)
                yield text

    def run(self, plan_name, input_name, max_rows=None,
            max_seconds=MAX_SECONDS_PER_CALL):
        if max_rows is None:
            max_rows = MAX_ROWS
        if type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS:
            raise ValueError("max rows must be 1..1000000")
        if (type(max_seconds) not in (int, float)
                or not 0 < max_seconds <= 120):
            raise ValueError("max seconds must be in (0,120]")
        plan = self.batch.plan(plan_name)
        if plan["stage"] != "ACTIVE":
            raise PermissionError("activate the template with its SHA first")
        self.batch._verify_evidence(plan)
        meta = self._metadata(input_name)
        state_file, output_file, jid = self._job_files(plan, input_name, meta)
        with _job_guard(state_file):
            state = self._load_job(state_file, output_file, plan, input_name, meta, jid)
            output_sha = self.batch._verify_prefix(output_file, state)
            parts = _parts(plan["code"]["template"])
            start = time.monotonic()
            rows_before = state["rows"]
            bytes_before = state["bytes"]
            target = min(meta["rows"], rows_before + max_rows)
            with self._open_imported(input_name) as source:
                prefix = _verify_fd(source, meta, state["input_offset"],
                                    state["input_prefix_sha256"])
                while state["rows"] < target and time.monotonic() - start < max_seconds:
                    if plan["code"].get("source_evidence"):
                        self.batch._verify_evidence(plan)
                    chunk_rows = min(CHUNK_ROWS, target - state["rows"])
                    rendered = []
                    raw_bytes = []
                    for i in range(chunk_rows):
                        raw = source.readline(MAX_VALUE_BYTES + 2)
                        value = _line(raw)
                        raw_bytes.append(raw)
                        rendered.append(_render(parts, state["rows"] + i + 1, value))
                    data = "".join(rendered).encode("utf-8")
                    input_consumed = b"".join(raw_bytes)
                    if (state["rows"] + len(raw_bytes) == meta["rows"]
                            and state["input_offset"] + len(input_consumed) != meta["bytes"]):
                        raise ValueError("input row total inconsistent with pinned source")
                    if state["bytes"] + len(data) > MAX_OUTPUT_BYTES:
                        raise ValueError("output exceeds 64MiB; split input")
                    _check_path(output_file)
                    with output_file.open("ab") as output:
                        output.write(data)
                        output.flush()
                        os.fsync(output.fileno())
                    prefix.update(input_consumed)
                    output_sha.update(data)
                    state["rows"] += len(raw_bytes)
                    state["input_offset"] += len(input_consumed)
                    state["input_prefix_sha256"] = prefix.hexdigest()
                    state["bytes"] += len(data)
                    state["sha256"] = output_sha.hexdigest()
                    state["status"] = "DONE" if state["rows"] == meta["rows"] else "PAUSED"
                    _save(state_file, state)
            elapsed = max(1e-9, time.monotonic() - start)
            new_rows = state["rows"] - rows_before
            return {
                "name": plan_name, "input_name": input_name,
                "input_sha256": meta["sha256"], "status": state["status"],
                "rows": state["rows"], "total_rows": meta["rows"],
                "rows_this_call": new_rows, "bytes": state["bytes"],
                "bytes_this_call": state["bytes"] - bytes_before,
                "rows_per_second": round(new_rows / elapsed, 1),
                "sha256": state["sha256"],
                "output_path": str(output_file), "model_calls": 0,
                "claim_limit": "Pure preapproved text transform, no LLM or external action",
            }


def operator_command(runtime, args):
    """input import NAME FILE SHA | status NAME | run PLAN INPUT [--rows=N] | read PLAN INPUT [--cursor=N] [--bytes=N]."""
    bank = ProceduralInputs(runtime.home, store=runtime.store)
    if len(args) == 4 and args[0] == "import":
        return bank.import_file(args[1], args[2], args[3])
    if len(args) == 2 and args[0] == "status":
        return bank.status(args[1])
    if args and args[0] == "read" and 3 <= len(args) <= 5:
        options = args[3:]
        cursor_opts = [x for x in options if x.startswith("--cursor=")]
        bytes_opts = [x for x in options if x.startswith("--bytes=")]
        if len(options) != len(cursor_opts) + len(bytes_opts) or len(cursor_opts) > 1 or len(bytes_opts) > 1:
            raise ValueError("input read PLAN NAME [--cursor=N] [--bytes=N]")
        cursor = int(cursor_opts[0].split("=", 1)[1]) if cursor_opts else 0
        amount = int(bytes_opts[0].split("=", 1)[1]) if bytes_opts else 16384
        return bank.read(args[1], args[2], cursor, amount)
    if args and args[0] == "run" and len(args) in (3, 4):
        limit = None
        if len(args) == 4:
            if not re.fullmatch(r"--rows=[1-9][0-9]*", args[3]):
                raise ValueError("input run PLAN NAME [--rows=NUMBER]")
            limit = int(args[3].split("=", 1)[1])
        return bank.run(args[1], args[2], max_rows=limit)
    raise ValueError("input import NAME FILE SHA256 | status NAME | run PLAN NAME [--rows=N] | read PLAN NAME [--cursor=N] [--bytes=N]")
