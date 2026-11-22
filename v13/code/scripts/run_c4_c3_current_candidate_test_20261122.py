"""Run the C4 -> C3 regression on the exact pinned observer and Core overlays.

This is a connected synthetic-model test over the real Runtime/SQLite/Focal/
Cognition path. It intentionally does not claim the full production composer
passes; Boss #2288 has a separate local-error pin-order failure.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


CODE = Path(__file__).resolve().parents[1]
OBSERVER = CODE / "scripts/integrated_observer_fair_budget_candidate_20261116.py"
RECEIPT = CODE / "scripts/integrated_c4_c3_receipt_candidate_20261122.py"
TEST = CODE / "tests/test_v14_same_turn_c4_c3_consumption.py"
OBSERVER_SHA256 = "15850e2498a8145bb451a7178b84f3023edcf3651970a60bd39bcc702d57fd4a"
RECEIPT_SHA256 = "0f3aab12b64454eaa3b49ce4adf22e8a29aeae081c5f82e8376e54a22028dff3"
IGNORED = ("__pycache__", "*.pyc", "*.db", "*.sqlite", "*.sqlite3",
           "*.gguf", "*.safetensors", "*.pt", "*.pth", "*.log")
SOURCE_PATHS = (
    "v13/cognition.py",
    "v13/runtime.py",
    "v13/native_turn_budget.py",
    "v13/observer_schedule.py",
    "v13/store.py",
    "scripts/integrated_observer_fair_budget_candidate_20261116.py",
    "scripts/integrated_c4_c3_receipt_candidate_20261122.py",
)


def load_pinned(path, name, expected_sha256):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(name + " overlay missing or unsafe")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise RuntimeError(name + " overlay SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(name + " overlay is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_hashes():
    return {name: hashlib.sha256((CODE / name).read_bytes()).hexdigest()
            for name in SOURCE_PATHS}


def main():
    before = source_hashes()
    observer = load_pinned(OBSERVER, "v14_observer_fair_budget",
                           OBSERVER_SHA256)
    receipt = load_pinned(RECEIPT, "v14_core_c4_c3_receipt",
                          RECEIPT_SHA256)
    replacements = observer.apply_sources(CODE, {})
    replacements = receipt.apply_sources(CODE, replacements)
    cognition = replacements.get("v13/cognition.py")
    if not isinstance(cognition, bytes) or b"c4_offer_context_ready" not in cognition:
        raise RuntimeError("C4 receipt missing from composed Core Runtime")
    if before != source_hashes():
        raise RuntimeError("overlay composition mutated pinned source files")

    with tempfile.TemporaryDirectory(prefix="v14-c4-c3-runtime-") as folder:
        staged = Path(folder) / "runtime"
        shutil.copytree(CODE / "v13", staged / "v13",
                        ignore=shutil.ignore_patterns(*IGNORED))
        for directory in ("specs", "scripts"):
            source = CODE / directory
            if source.is_dir():
                shutil.copytree(source, staged / directory,
                                ignore=shutil.ignore_patterns(*IGNORED))
        for relative, payload in replacements.items():
            target_rel = Path(relative)
            if target_rel.is_absolute() or ".." in target_rel.parts:
                raise ValueError("unsafe composed path")
            target = staged / target_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        (staged / "tests").mkdir()
        shutil.copy2(TEST, staged / "tests/test_v14_same_turn_c4_c3_consumption.py")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(staged)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        run = subprocess.run(
            [sys.executable, "-m", "pytest", "-q",
             "tests/test_v14_same_turn_c4_c3_consumption.py"],
            cwd=staged, env=env, capture_output=True, text=True, timeout=90)
        sys.stdout.write(run.stdout)
        sys.stderr.write(run.stderr)
        if run.returncode:
            raise SystemExit(run.returncode)
    print("C4_C3_OBSERVER_OVERLAY_RUNTIME_TEST PASS (synthetic model runners)")
    

if __name__ == "__main__":
    main()
