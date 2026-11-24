"""Apply local native-probe command dispatch only to the final staged Runtime.

The canonical v13/operator.py remains byte-identical. This post-composition
overlay is deliberately separate from the pinned native receiver and recovery
builders, so an operator command cannot silently alter their source inputs.
"""
from pathlib import Path
import hashlib

OPERATOR_PATH = "v13/operator.py"
APPROVAL_PATH = "v13/native_probe_approval.py"
RUNTIME_PATH = "v13/runtime.py"

SOURCE_PINS = {
    OPERATOR_PATH: "8d59efa1bfb7dea7bbb2fd1af2cf7d2e25adebc4",
    APPROVAL_PATH: "465824d251c108eeeeb31884ab140ef9005f8df3",
}

HELP_OLD = b":callosum [status|shadow|active|degrade|promote <Richtung>]"
HELP_NEW = (
    b":callosum [status|shadow|active|degrade|promote <Richtung>|"
    b"arm-probe <sender> <receiver> --last-source --confirm|"
    b"native-probe <sender> <receiver> --last-source --confirm|revoke-probe]"
)

DISPATCH_OLD = (
    b"        if cmd=='callosum':\n"
    b"            from .callosum import operator_command\n"
    b"            return operator_command(r,args)\n"
)
DISPATCH_NEW = (
    b"        if cmd=='callosum' and args and args[0] in {'arm-probe','native-probe','revoke-probe'}:\n"
    b"            from .native_probe_approval import operator_command as probe_operator_command\n"
    b"            return probe_operator_command(r,args)\n"
    + DISPATCH_OLD
)

RUNTIME_CLOSE_OLD = (
    b"        self.worker.join(6)\n"
    b"        if self.worker.is_alive():"
)
RUNTIME_CLOSE_NEW = (
    b"        self.worker.join(6)\n"
    b"        from .native_probe_approval import wait_for_runtime_probe_shutdown\n"
    b"        wait_for_runtime_probe_shutdown(self, timeout=getattr(self, '_native_probe_close_timeout_s', 5.0))\n"
    b"        if self.worker.is_alive():"
)


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read_pinned(root: Path, relative: str, expected: str, label: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError(label + " is missing or unsafe: " + relative)
    raw = path.read_bytes()
    if _git_blob_sha1(raw) != expected:
        raise ValueError(label + " source pin mismatch: " + relative)
    return raw


def _replace_once(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError(label + " expected exactly one canonical insertion point; found " + str(count))
    return raw.replace(old, new, 1)


def apply_staged_native_probe(
    code_dir: Path,
    staging: Path,
    *,
    expected_staged_operator: bytes,
    expected_staged_runtime: bytes,
) -> dict:
    """Patch only final staged operator dispatch and Runtime teardown barrier."""
    code_dir = Path(code_dir).resolve(strict=True)
    staging = Path(staging).resolve(strict=True)
    source_operator = _read_pinned(
        code_dir, OPERATOR_PATH, SOURCE_PINS[OPERATOR_PATH], "canonical operator",
    )
    source_module = _read_pinned(
        code_dir, APPROVAL_PATH, SOURCE_PINS[APPROVAL_PATH], "native-probe approval module",
    )
    staged_module = _read_pinned(
        staging, APPROVAL_PATH, SOURCE_PINS[APPROVAL_PATH], "staged native-probe approval module",
    )
    if source_module != staged_module:
        raise ValueError("native-probe approval module differs between source and staged tree")
    if not isinstance(expected_staged_operator, bytes):
        raise ValueError("verified recovery builder did not provide staged operator bytes")
    if not isinstance(expected_staged_runtime, bytes):
        raise ValueError("verified recovery builder did not provide staged Runtime bytes")
    staged_operator_path = staging / OPERATOR_PATH
    staged_runtime_path = staging / RUNTIME_PATH
    if staged_operator_path.is_symlink() or not staged_operator_path.is_file():
        raise ValueError("staged operator is missing or unsafe")
    if staged_runtime_path.is_symlink() or not staged_runtime_path.is_file():
        raise ValueError("staged Runtime is missing or unsafe")
    staged_operator = staged_operator_path.read_bytes()
    staged_runtime = staged_runtime_path.read_bytes()
    if staged_operator != expected_staged_operator:
        raise ValueError("staged operator differs from verified recovery builder output")
    if staged_runtime != expected_staged_runtime:
        raise ValueError("staged Runtime differs from verified recovery builder output")
    if HELP_OLD not in source_operator or DISPATCH_OLD not in source_operator:
        raise ValueError("canonical operator no longer contains the pinned overlay anchors")
    if b"def operator_command(" not in source_module:
        raise ValueError("native-probe approval module has no operator consumer")

    patched_operator = _replace_once(staged_operator, HELP_OLD, HELP_NEW, "operator help")
    patched_operator = _replace_once(patched_operator, DISPATCH_OLD, DISPATCH_NEW, "callosum dispatch")
    patched_runtime = _replace_once(
        staged_runtime, RUNTIME_CLOSE_OLD, RUNTIME_CLOSE_NEW, "Runtime close barrier",
    )
    try:
        compile(patched_operator.decode("utf-8"), str(staged_operator_path), "exec")
        compile(patched_runtime.decode("utf-8"), str(staged_runtime_path), "exec")
    except (SyntaxError, UnicodeError) as exc:
        raise ValueError("staged native-probe Runtime/operator overlay does not compile") from exc
    if (b"from .native_probe_approval import operator_command as probe_operator_command" not in patched_operator
            or patched_operator.index(b"probe_operator_command") > patched_operator.index(DISPATCH_OLD)):
        raise ValueError("native-probe dispatch is not ahead of the normal Callosum handler")
    if (b"wait_for_runtime_probe_shutdown" not in patched_runtime
            or patched_runtime.index(b"wait_for_runtime_probe_shutdown") > patched_runtime.index(b"if self.worker.is_alive():")):
        raise ValueError("Runtime close does not wait for the active native probe before teardown")
    return {OPERATOR_PATH: patched_operator, RUNTIME_PATH: patched_runtime}
