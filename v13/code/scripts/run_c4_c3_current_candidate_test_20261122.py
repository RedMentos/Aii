"""Exercise the current pinned Runtime composition before the known postcommit guard.

This is a connected synthetic model test: real Runtime/SQLite/Focal/Cognition,
real source-pinned base + observer + audio overlays, deterministic model stubs.
It deliberately skips only include_postcommit overlays whose upstream pin-order
failure is tracked separately on Boss #2288.
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
WRAPPER = CODE / "scripts/termux_runtime_recovery_candidate_20261121.py"
TEST = CODE / "tests/test_v14_same_turn_c4_c3_consumption.py"
IGNORED = ("__pycache__", "*.pyc", "*.db", "*.sqlite", "*.sqlite3",
           "*.gguf", "*.safetensors", "*.pt", "*.pth", "*.log")
SOURCE_PATHS = (
    "v13/cognition.py",
    "v13/runtime.py",
    "v13/native_turn_budget.py",
    "v13/observer_schedule.py",
    "v13/store.py",
    "scripts/integrated_observer_fair_budget_candidate_20261116.py",
    "scripts/integrated_audio_context_candidate_20261121.py",
    "scripts/integrated_c4_c3_receipt_candidate_20261122.py",
    "scripts/termux_runtime_recovery_candidate_20261112.py",
    "scripts/termux_runtime_recovery_candidate_20261121.py",
)


def load_wrapper():
    spec = importlib.util.spec_from_file_location("v14_core_runtime_wrapper", WRAPPER)
    if spec is None or spec.loader is None:
        raise RuntimeError("current Runtime wrapper is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_hashes():
    return {name: hashlib.sha256((CODE / name).read_bytes()).hexdigest()
            for name in SOURCE_PATHS}


def main():
    before = source_hashes()
    wrapper = load_wrapper()
    replacements = wrapper.build_sources(CODE, include_postcommit=False)
    cognition = replacements.get("v13/cognition.py")
    if not isinstance(cognition, bytes) or b"c4_offer_context_ready" not in cognition:
        raise RuntimeError("C4 receipt missing from composed Runtime")
    if before != source_hashes():
        raise RuntimeError("composition mutated pinned source files")

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
    print("C4_C3_COMPOSED_RUNTIME_TEST PASS (synthetic runners; pre-postcommit composition)")


if __name__ == "__main__":
    main()
