"""Apply local native-probe command dispatch only to the final staged Runtime.

The canonical v13/operator.py remains byte-identical. This post-composition
overlay is deliberately separate from the pinned native receiver and recovery
builders, so an operator command cannot silently alter their source inputs.
"""
from pathlib import Path
import hashlib

OPERATOR_PATH = "v13/operator.py"
APPROVAL_PATH = "v13/native_probe_approval.py"

SOURCE_PINS = {
    OPERATOR_PATH: "8d59efa1bfb7dea7bbb2fd1af2cf7d2e25adebc4",
    APPROVAL_PATH: "c52c4d5bf21b34ab691eb6633504b67254bdf098",
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
) -> dict:
    """Patch only the operator bytes emitted by the verified recovery builder."""
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
    staged_operator_path = staging / OPERATOR_PATH
    if staged_operator_path.is_symlink() or not staged_operator_path.is_file():
        raise ValueError("staged operator is missing or unsafe")
    staged_operator = staged_operator_path.read_bytes()
    if staged_operator != expected_staged_operator:
        raise ValueError("staged operator differs from verified recovery builder output")
    if HELP_OLD not in source_operator or DISPATCH_OLD not in source_operator:
        raise ValueError("canonical operator no longer contains the pinned overlay anchors")
    if b"def operator_command(" not in source_module:
        raise ValueError("native-probe approval module has no operator consumer")

    patched = _replace_once(staged_operator, HELP_OLD, HELP_NEW, "operator help")
    patched = _replace_once(patched, DISPATCH_OLD, DISPATCH_NEW, "callosum dispatch")
    try:
        compile(patched.decode("utf-8"), str(staged_operator_path), "exec")
    except (SyntaxError, UnicodeError) as exc:
        raise ValueError("staged native-probe operator overlay does not compile") from exc
    if (b"from .native_probe_approval import operator_command as probe_operator_command" not in patched
            or patched.index(b"probe_operator_command") > patched.index(DISPATCH_OLD)):
        raise ValueError("native-probe dispatch is not ahead of the normal Callosum handler")
    return {OPERATOR_PATH: patched}
