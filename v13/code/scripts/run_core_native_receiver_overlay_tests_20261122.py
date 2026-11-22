"""Run C4 and native-receiver tests on source-pinned Core overlays.

No GGUF model is loaded here. Python tests use deterministic synthetic runners;
the separate native CI jobs compile the pinned llama.cpp receiver for Linux
and Android arm64 without installing it on a device.
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
C4_RECEIPT = CODE / "scripts/integrated_c4_c3_receipt_candidate_20261122.py"
NATIVE_RECEIVER = CODE / "scripts/integrated_native_latent_receiver_candidate_20261122.py"
TESTS = (
    "test_v14_same_turn_c4_c3_consumption.py",
    "test_native_latent_receiver.py",
    "test_native_latent_receiver_runtime.py",
    "test_native_taps.py",
    "test_callosum.py",
)
OBSERVER_SHA256 = "15850e2498a8145bb451a7178b84f3023edcf3651970a60bd39bcc702d57fd4a"
C4_RECEIPT_SHA256 = "0f3aab12b64454eaa3b49ce4adf22e8a29aeae081c5f82e8376e54a22028dff3"
NATIVE_RECEIVER_SHA256 = "dcc910c7912b4d1ebc273f3bb365b871401c07abca48d79d0addf4577e0bf7b0"
IGNORED = ("__pycache__", "*.pyc", "*.db", "*.sqlite", "*.sqlite3",
           "*.gguf", "*.safetensors", "*.pt", "*.pth", "*.log")
SOURCE_PATHS = (
    "v13/cognition.py",
    "v13/callosum.py",
    "v13/runtime.py",
    "v13/native_turn_budget.py",
    "v13/observer_schedule.py",
    "v13/store.py",
    "v13/native_latent_receiver.py",
    "scripts/integrated_observer_fair_budget_candidate_20261116.py",
    "scripts/integrated_c4_c3_receipt_candidate_20261122.py",
    "scripts/integrated_native_latent_receiver_candidate_20261122.py",
)


def load_pinned(path, name, expected_sha256):
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(name + " overlay missing or unsafe")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
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
    c4 = load_pinned(C4_RECEIPT, "v14_core_c4_receipt", C4_RECEIPT_SHA256)
    native = load_pinned(NATIVE_RECEIVER, "v14_core_native_receiver",
                         NATIVE_RECEIVER_SHA256)
    replacements = observer.apply_sources(CODE, {})
    replacements = c4.apply_sources(CODE, replacements)
    replacements = native.apply_sources(CODE, replacements)
    cognition = replacements.get("v13/cognition.py", b"")
    callosum = replacements.get("v13/callosum.py", b"")
    if b"c4_offer_context_ready" not in cognition:
        raise RuntimeError("C4 context receipt missing from composed Runtime")
    if b"def native_receive(" not in cognition:
        raise RuntimeError("native receive method missing from composed Runtime")
    if b"native_receiver_probe" not in callosum:
        raise RuntimeError("native receiver Callosum command/status missing")
    if before != source_hashes():
        raise RuntimeError("overlay composition mutated pinned source files")

    with tempfile.TemporaryDirectory(prefix="v14-core-native-receiver-") as folder:
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
        for name in TESTS:
            shutil.copy2(CODE / "tests" / name, staged / "tests" / name)
        env = dict(os.environ)
        env["PYTHONPATH"] = str(staged)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        run = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", *("tests/" + x for x in TESTS)],
            cwd=staged, env=env, capture_output=True, text=True, timeout=150)
        sys.stdout.write(run.stdout)
        sys.stderr.write(run.stderr)
        if run.returncode:
            raise SystemExit(run.returncode)
    print("CORE_C4_NATIVE_RECEIVER_OVERLAY_TEST PASS (synthetic model runners; no GGUF loaded)")


if __name__ == "__main__":
    main()
