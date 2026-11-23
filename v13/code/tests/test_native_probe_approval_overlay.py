"""Fail-closed tests for the final-stage local native-probe operator overlay."""
import importlib.util
from pathlib import Path
import shutil

import pytest

CODE = Path(__file__).resolve().parents[1]
OVERLAY_PATH = CODE / "scripts/integrated_native_probe_approval_overlay_20261123.py"
SPEC = importlib.util.spec_from_file_location("v14_native_probe_overlay_test", OVERLAY_PATH)
OVERLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OVERLAY)


def _trees(tmp_path):
    code_dir = tmp_path / "source"
    staging = tmp_path / "staging"
    for root in (code_dir, staging):
        (root / "v13").mkdir(parents=True)
        shutil.copy2(CODE / "v13/operator.py", root / "v13/operator.py")
        shutil.copy2(CODE / "v13/native_probe_approval.py", root / "v13/native_probe_approval.py")
    return code_dir, staging


def _apply(code_dir, staging):
    expected = (code_dir / "v13/operator.py").read_bytes()
    return OVERLAY.apply_staged_native_probe(
        code_dir, staging, expected_staged_operator=expected,
    )


def test_overlay_changes_only_staged_operator_and_preserves_source(tmp_path):
    code_dir, staging = _trees(tmp_path)
    source_before = (code_dir / "v13/operator.py").read_bytes()
    result = _apply(code_dir, staging)
    assert set(result) == {"v13/operator.py"}
    for relative, payload in result.items():
        (staging / relative).write_bytes(payload)

    staged = (staging / "v13/operator.py").read_bytes()
    assert (code_dir / "v13/operator.py").read_bytes() == source_before
    assert staged != source_before
    assert b"arm-probe <sender> <receiver>" in staged
    assert b"from .native_probe_approval import operator_command as probe_operator_command" in staged
    assert staged.index(b"probe_operator_command") < staged.index(OVERLAY.DISPATCH_OLD)
    compile(staged.decode("utf-8"), str(staging / "v13/operator.py"), "exec")


def test_overlay_rejects_staged_operator_drift(tmp_path):
    code_dir, staging = _trees(tmp_path)
    path = staging / "v13/operator.py"
    path.write_bytes(path.read_bytes() + b"\\n# tampered staged operator\\n")
    with pytest.raises(ValueError, match="staged operator source pin mismatch"):
        _apply(code_dir, staging)


def test_overlay_rejects_approval_module_drift(tmp_path):
    code_dir, staging = _trees(tmp_path)
    path = code_dir / "v13/native_probe_approval.py"
    path.write_bytes(path.read_bytes() + b"\\n# tampered approval module\\n")
    with pytest.raises(ValueError, match="native-probe approval module source pin mismatch"):
        _apply(code_dir, staging)


def test_overlay_rejects_duplicate_help_insertion_point(tmp_path, monkeypatch):
    code_dir, staging = _trees(tmp_path)
    path = code_dir / "v13/operator.py"
    raw = path.read_bytes() + OVERLAY.HELP_OLD
    path.write_bytes(raw)
    (staging / "v13/operator.py").write_bytes(raw)
    monkeypatch.setitem(
        OVERLAY.SOURCE_PINS,
        OVERLAY.OPERATOR_PATH,
        OVERLAY._git_blob_sha1(raw),
    )
    with pytest.raises(ValueError, match="operator help expected exactly one"):
        _apply(code_dir, staging)
