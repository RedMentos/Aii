"""Apply the source-pinned public native-probe privacy boundary to a staged tree."""
from __future__ import annotations

import hashlib
from pathlib import Path


PUBLIC_PROBE_SHA256 = "f76dd286bd9cbfa72d2dc1de1bed2dd61017dfa5c44a29136a42dfd564cfc3b4"

_RUNTIME_NATIVE_BRANCH = b"""                    else:
                        from .verification import probe
                        self.notice(dumps(probe(self)))
"""
_RUNTIME_NATIVE_REPLACEMENT = b"""                    else:
                        from .verification import probe
                        from .public_probe import public_probe_summary
                        self.notice(dumps(public_probe_summary(probe(self))))
"""
_RUNTIME_ERROR_LINE = b"""                self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')
"""
_RUNTIME_ERROR_REPLACEMENT = b"""                if kind == 'probe':
                    try:
                        self.store.log('job_error', None, {'kind': 'probe', 'error': 'PROBE_ERROR'})
                    except Exception:
                        pass
                    self.notice('probe: PROBE_ERROR')
                else:
                    self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')
"""
_MAIN_NATIVE_BRANCH = b"            else:result=probe(r)\n"
_MAIN_NATIVE_REPLACEMENT = b"""            else:
                from .public_probe import public_probe_summary, public_probe_error
                try:
                    result=public_probe_summary(probe(r))
                except Exception:
                    result=public_probe_error()
"""


def _replace_once(raw: bytes, before: bytes, after: bytes, label: str) -> bytes:
    if raw.count(before) != 1:
        raise ValueError("public probe privacy anchor mismatch: " + label)
    return raw.replace(before, after, 1)


def apply_staged_probe_privacy(staging: Path) -> dict:
    staging = Path(staging)
    if staging.is_symlink() or not staging.is_dir():
        raise ValueError("unsafe public probe staging root")
    staging = staging.resolve(strict=True)
    v13_dir = staging / "v13"
    if v13_dir.is_symlink() or not v13_dir.is_dir():
        raise ValueError("unsafe staged V13 directory")

    helper = v13_dir / "public_probe.py"
    runtime = v13_dir / "runtime.py"
    main = v13_dir / "__main__.py"
    for path, label in (
        (helper, "public probe helper"),
        (runtime, "runtime"),
        (main, "one-shot CLI"),
    ):
        if path.is_symlink() or not path.is_file():
            raise ValueError("unsafe staged public probe target: " + label)

    helper_raw = helper.read_bytes()
    if hashlib.sha256(helper_raw).hexdigest() != PUBLIC_PROBE_SHA256:
        raise ValueError("public probe helper source changed")

    runtime_raw = runtime.read_bytes()
    runtime_raw = _replace_once(
        runtime_raw, _RUNTIME_NATIVE_BRANCH, _RUNTIME_NATIVE_REPLACEMENT,
        "interactive native probe",
    )
    runtime_raw = _replace_once(
        runtime_raw, _RUNTIME_ERROR_LINE, _RUNTIME_ERROR_REPLACEMENT,
        "interactive probe exception",
    )

    main_raw = main.read_bytes()
    main_raw = _replace_once(
        main_raw, _MAIN_NATIVE_BRANCH, _MAIN_NATIVE_REPLACEMENT,
        "one-shot native probe",
    )

    runtime.write_bytes(runtime_raw)
    main.write_bytes(main_raw)
    return {
        "v13/runtime.py": hashlib.sha256(runtime_raw).hexdigest(),
        "v13/__main__.py": hashlib.sha256(main_raw).hexdigest(),
    }
