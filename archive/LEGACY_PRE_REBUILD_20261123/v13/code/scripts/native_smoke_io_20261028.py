"""Fail-closed, bounded raw Linux subprocess capture for pinned native smoke only.

The child inherits a per-regular-file RLIMIT_FSIZE. Unlike capture_output=True,
a runaway interactive CLI cannot allocate unbounded Python RAM or upload huge
logs. A capped file is a raw *prefix*, never represented as complete evidence.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import resource
import signal
import subprocess
import time

MAX_RAW_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 180


def _limit_filesize():
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_RAW_BYTES, MAX_RAW_BYTES))


def run_one_turn(cmd, evidence_dir, prefix, env, timeout=TIMEOUT_SECONDS):
    """Execute a pinned llama-cli one-turn command, preserving bounded raw bytes.

    The caller must create evidence_dir and supply fresh prefix names. Never
    silently overwrite a prior attempt's raw evidence.
    """
    if '--single-turn' not in cmd:
        raise ValueError('Native smoke must be explicitly noninteractive')
    evidence_dir = Path(evidence_dir)
    stdout_path = evidence_dir / (prefix + '_STDOUT_RAW.log')
    stderr_path = evidence_dir / (prefix + '_STDERR_RAW.log')
    if stdout_path.exists() or stderr_path.exists():
        raise FileExistsError('Existing native raw evidence must not be overwritten')
    start = time.monotonic()
    timed_out = False
    # Exclusive creation avoids replacing a prior run's evidence.
    with stdout_path.open('xb') as out, stderr_path.open('xb') as err:
        try:
            proc = subprocess.run(
                cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                timeout=timeout, env=env, check=False, preexec_fn=_limit_filesize,
            )
            code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            code = 124
    elapsed = time.monotonic() - start
    stdout = stdout_path.read_bytes()
    stderr = stderr_path.read_bytes()
    capped = (
        code == -signal.SIGXFSZ
        or len(stdout) >= MAX_RAW_BYTES
        or len(stderr) >= MAX_RAW_BYTES
    )
    # The pinned llama-cli emits this only after actual token generation.
    # Banner/prompt-only output must not pass a native generation smoke.
    generated = b'[ Prompt:' in stdout and b'| Generation:' in stdout
    return {
        'native_exit_code': code,
        'native_elapsed_s': round(elapsed, 3),
        'native_timed_out': timed_out,
        'raw_output_cap_bytes_per_stream': MAX_RAW_BYTES,
        'raw_capture_complete': not capped,
        'raw_output_capped': capped,
        'generation_marker_seen': generated,
        'stdout_sha256': hashlib.sha256(stdout).hexdigest(),
        'stderr_sha256': hashlib.sha256(stderr).hexdigest(),
        'stdout_bytes': len(stdout),
        'stderr_bytes': len(stderr),
        'stdout_chars': len(stdout.decode('utf-8', errors='replace')),
        'stderr_chars': len(stderr.decode('utf-8', errors='replace')),
        'native_smoke_pass': code == 0 and not timed_out and not capped and generated,
    }
