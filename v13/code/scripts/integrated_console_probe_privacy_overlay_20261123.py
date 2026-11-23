"""Apply the closed native-probe privacy boundary after all source builders.

This overlay is intentionally post-composition: it does not edit canonical
Runtime or the source builders that pin it. It patches only the final staged
Runtime/CLI bytes after the exact recovery and arithmetic overlays have run.
"""
from pathlib import Path
import hashlib

RUNTIME_PATH = "v13/runtime.py"
MAIN_PATH = "v13/__main__.py"
PROMPTS_PATH = "v13/prompts.py"
PUBLIC_PROBE_PATH = "v13/public_probe.py"

SOURCE_PINS = {
    RUNTIME_PATH: "30360f40eb784be5ea975ee85e94a57f0b154164",
    MAIN_PATH: "9248e46e199a4227c296d538e6a2ef969e8e10cb",
    PROMPTS_PATH: "1d5daae11ab80e294fde232d47eb3c199bb307c4",
    PUBLIC_PROBE_PATH: "8008a9f8031d7901450607ee966fd26c8a5c4b4b",
}

RUNTIME_PROBE_OLD = b"""                elif kind=='probe':
                    if payload=='sustained':
                        from .proofs import probe_sustained
                        self.notice(dumps(probe_sustained(self)))
                    elif payload=='jef-modes':
                        from .proofs import probe_jef_modes
                        self.notice(dumps(probe_jef_modes(self)))
                    elif payload=='body-state':
                        from .proofs import probe_body_state
                        self.notice(dumps(probe_body_state(self)))
                    elif payload=='step12':
                        from .proofs import probe_step12
                        self.notice(dumps(probe_step12(self)))
                    else:
                        from .verification import probe
                        self.notice(dumps(probe(self)))
                else:raise ValueError('Job unbekannt')"""

RUNTIME_PROBE_NEW = b"""                elif kind=='probe':
                    try:
                        if payload=='sustained':
                            from .proofs import probe_sustained
                            self.notice(dumps(probe_sustained(self)))
                        elif payload=='jef-modes':
                            from .proofs import probe_jef_modes
                            self.notice(dumps(probe_jef_modes(self)))
                        elif payload=='body-state':
                            from .proofs import probe_body_state
                            self.notice(dumps(probe_body_state(self)))
                        elif payload=='step12':
                            from .proofs import probe_step12
                            self.notice(dumps(probe_step12(self)))
                        else:
                            from .verification import probe
                            from .public_probe import public_probe_summary
                            self.notice(dumps(public_probe_summary(probe(self))))
                    except BaseException:
                        from .public_probe import public_probe_error_telemetry
                        try:self.store.log('job_error',None,public_probe_error_telemetry())
                        except Exception:pass
                        self.notice('probe: PROBE_ERROR')
                else:raise ValueError('Job unbekannt')"""

RUNTIME_ERROR_OLD = b"""            except BaseException as exc:
                self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')
                if kind=='turn' and not self.store.one("SELECT id FROM messages WHERE event_id=? AND role='assistant'",(payload['event_id'],)):self._rejected(payload,str(exc))"""

RUNTIME_ERROR_NEW = b"""            except BaseException as exc:
                if kind=='probe':
                    from .public_probe import public_probe_error_telemetry
                    try:self.store.log('job_error',None,public_probe_error_telemetry())
                    except Exception:pass
                    self.notice('probe: PROBE_ERROR')
                else:
                    self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')
                if kind=='turn' and not self.store.one("SELECT id FROM messages WHERE event_id=? AND role='assistant'",(payload['event_id'],)):self._rejected(payload,str(exc))"""

CLI_PROBE_OLD = b"""        if a.command=='probe':
            from .verification import probe
            if a.mode=='sustained':
                from .proofs import probe_sustained
                result=probe_sustained(r,a.cycles)
            elif a.mode=='jef-modes':
                from .proofs import probe_jef_modes
                result=probe_jef_modes(r)
            elif a.mode=='body-state':
                from .proofs import probe_body_state
                result=probe_body_state(r)
            elif a.mode=='step12':
                from .proofs import probe_step12
                result=probe_step12(r)
            else:result=probe(r)
            print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['status'] in {'SMOKE_PASS','JEF_MODES_PASS','VERTICAL_CHECKS_PASS','BODY_STATE_CHECKS_PASS','BOUNDED_STABILITY_PASS'} else 2"""

CLI_PROBE_NEW = b"""        if a.command=='probe':
            try:
                from .verification import probe
                from .public_probe import public_probe_summary, public_probe_error_report
                if a.mode=='sustained':
                    from .proofs import probe_sustained
                    result=probe_sustained(r,a.cycles)
                elif a.mode=='jef-modes':
                    from .proofs import probe_jef_modes
                    result=probe_jef_modes(r)
                elif a.mode=='body-state':
                    from .proofs import probe_body_state
                    result=probe_body_state(r)
                elif a.mode=='step12':
                    from .proofs import probe_step12
                    result=probe_step12(r)
                else:result=public_probe_summary(probe(r))
                print(json.dumps(result,ensure_ascii=False,indent=2))
                return 0 if result['status'] in {'SMOKE_PASS','JEF_MODES_PASS','VERTICAL_CHECKS_PASS','BODY_STATE_CHECKS_PASS','BOUNDED_STABILITY_PASS'} else 2
            except Exception:
                from .public_probe import public_probe_error_report
                print(json.dumps(public_probe_error_report(),ensure_ascii=False,indent=2))
                return 2"""

def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read_regular(root: Path, relative: str, label: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + " is missing or unsafe: " + relative)
    return path.read_bytes()


def _read_pinned(root: Path, relative: str, expected: str) -> bytes:
    raw = _read_regular(root, relative, "pinned source")
    if _git_blob_sha1(raw) != expected:
        raise ValueError("console privacy source pin mismatch: " + relative)
    return raw


def _replace_once(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError(label + " expected exactly one canonical anchor; found " + str(count))
    return raw.replace(old, new, 1)


def apply_staged_console_probe_privacy(
    code_dir: Path,
    staging: Path,
    *,
    expected_staged_files: dict,
) -> dict:
    """Patch only verified staged Runtime and CLI bytes; return the two replacements."""
    code_dir = Path(code_dir).resolve(strict=True)
    staging_input = Path(staging)
    if staging_input.is_symlink():
        raise ValueError("staging directory cannot be a symlink")
    staging = staging_input.resolve(strict=True)
    if type(expected_staged_files) is not dict:
        raise ValueError("expected staged file map is invalid")

    source = {
        relative: _read_pinned(code_dir, relative, expected)
        for relative, expected in SOURCE_PINS.items()
    }
    if (b"Do not reveal internal offers or roles." not in source[PROMPTS_PATH]
            or b"Interne Angebote oder Rollen nicht offenlegen." not in source[PROMPTS_PATH]):
        raise ValueError("model-facing internal-offer privacy instruction is missing")

    for relative in (PROMPTS_PATH, PUBLIC_PROBE_PATH):
        staged = _read_regular(staging, relative, "staged privacy dependency")
        if staged != source[relative]:
            raise ValueError("staged privacy dependency differs from pinned source: " + relative)

    staged_runtime = _read_regular(staging, RUNTIME_PATH, "staged Runtime")
    expected_runtime = expected_staged_files.get(RUNTIME_PATH, source[RUNTIME_PATH])
    if type(expected_runtime) is not bytes or staged_runtime != expected_runtime:
        raise ValueError("staged Runtime differs from the exact composed builder output")

    staged_main = _read_regular(staging, MAIN_PATH, "staged CLI")
    expected_main = expected_staged_files.get(MAIN_PATH, source[MAIN_PATH])
    if type(expected_main) is not bytes or staged_main != expected_main:
        raise ValueError("staged CLI differs from the exact composed builder output")

    patched_runtime = _replace_once(
        staged_runtime, RUNTIME_PROBE_OLD, RUNTIME_PROBE_NEW, "Runtime probe output",
    )
    patched_runtime = _replace_once(
        patched_runtime, RUNTIME_ERROR_OLD, RUNTIME_ERROR_NEW, "Runtime probe exception",
    )
    patched_main = _replace_once(
        staged_main, CLI_PROBE_OLD, CLI_PROBE_NEW, "one-shot probe CLI",
    )
    try:
        compile(patched_runtime.decode("utf-8"), str(staging / RUNTIME_PATH), "exec")
        compile(patched_main.decode("utf-8"), str(staging / MAIN_PATH), "exec")
    except (SyntaxError, UnicodeError) as exc:
        raise ValueError("staged public-probe privacy overlay does not compile") from exc

    return {RUNTIME_PATH: patched_runtime, MAIN_PATH: patched_main}
