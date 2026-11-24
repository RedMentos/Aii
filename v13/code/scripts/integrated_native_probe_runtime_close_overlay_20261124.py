"""Bind the native-probe lease barrier into the final staged Runtime.close method.

The instance wrapper in native_probe_approval remains a source-tree fallback.
The staged Runtime also calls the guard from its class method, so a shutdown
callback that captured Runtime.close before a probe starts cannot bypass it.
"""
from pathlib import Path


RUNTIME_PATH = "v13/runtime.py"
APPROVAL_PATH = "v13/native_probe_approval.py"
OLD = b"    def close(self):\n        if self.closed:return\n"
NEW = (
    b"    def close(self):\n"
    b"        if self.closed:return\n"
    b"        from .native_probe_approval import guard_runtime_close\n"
    b"        guard_runtime_close(self)\n"
)


def apply_sources(sources, *, code_dir: Path) -> dict:
    code_dir = Path(code_dir).resolve(strict=True)
    runtime = sources.get(RUNTIME_PATH)
    if not isinstance(runtime, bytes):
        raise ValueError("native-probe close overlay has no composed Runtime source")
    approval_path = code_dir / APPROVAL_PATH
    if approval_path.is_symlink() or not approval_path.is_file():
        raise ValueError("native-probe close guard module is missing or unsafe")
    approval = approval_path.read_bytes()
    if b"def guard_runtime_close(" not in approval:
        raise ValueError("native-probe approval module has no Runtime.close barrier")
    count = runtime.count(OLD)
    if count != 1:
        raise ValueError(
            "native-probe Runtime.close anchor expected exactly once; found " + str(count)
        )
    patched = runtime.replace(OLD, NEW, 1)
    try:
        compile(patched.decode("utf-8"), RUNTIME_PATH, "exec")
    except (SyntaxError, UnicodeError) as exc:
        raise ValueError("native-probe Runtime.close overlay does not compile") from exc
    if patched.count(b"guard_runtime_close(self)") != 1:
        raise ValueError("native-probe Runtime.close barrier was not installed exactly once")
    return {RUNTIME_PATH: patched}
