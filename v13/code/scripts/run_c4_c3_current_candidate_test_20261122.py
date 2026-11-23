"""Run the same-turn B1/B2 -> C4 -> C3 test in the exact full staged Runtime.

This uses the production source composer (Store, memory/world, Context OS,
fair-budget, audio lease, C4 receipt and arithmetic overlays), then injects
synthetic runners. It does not claim native GGUF or Redmi execution.
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
STAGE_BUILDER = CODE / "scripts/stage_integrated_candidate.py"
TEST = CODE / "tests/test_v14_same_turn_c4_c3_consumption.py"
SOURCE_PATHS = (
    "v13/cognition.py",
    "v13/runtime.py",
    "v13/store.py",
    "v13/focal.py",
    "v13/native_turn_budget.py",
    "v13/observer_schedule.py",
    "v13/brain_panel.py",
    "v13/native_offer_prompt_receipt.py",
    "v13/runners.py",
    "scripts/stage_integrated_candidate.py",
    "scripts/termux_runtime_recovery_candidate_20261121.py",
    "scripts/integrated_c4_c3_receipt_candidate_20261122.py",
    "tests/test_v14_same_turn_c4_c3_consumption.py",
)


def source_hashes():
    return {
        relative: hashlib.sha256((CODE / relative).read_bytes()).hexdigest()
        for relative in SOURCE_PATHS
    }


def load_stage_builder():
    spec = importlib.util.spec_from_file_location(
        "v14_full_composed_stage_builder", STAGE_BUILDER
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("full integrated stage builder is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    before = source_hashes()
    builder = load_stage_builder()
    with tempfile.TemporaryDirectory(prefix="v14-full-c4-c3-") as folder:
        staged = Path(folder) / "runtime"
        manifest = builder.stage(CODE, staged)
        if manifest.get("status") != "SHADOW_REVIEW_ONLY":
            raise RuntimeError("full staged Runtime is not review-only")
        cognition = (staged / "v13/cognition.py").read_bytes()
        runtime = (staged / "v13/runtime.py").read_bytes()
        if b"c4_offer_context_ready" not in cognition:
            raise RuntimeError("full staged Runtime lacks the C4 -> C3 receipt")
        if b"minimum_role_slice_s" not in cognition:
            raise RuntimeError("full staged Runtime lost the fair B1/B2 role slice")
        if b"audio_consent_lease" not in runtime:
            raise RuntimeError("full staged Runtime lacks the A5 audio lease")

        (staged / "tests").mkdir(exist_ok=True)
        shutil.copy2(TEST, staged / "tests/test_v14_same_turn_c4_c3_consumption.py")
        env = dict(os.environ)
        env["PYTHONPATH"] = str(staged)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        run = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_v14_same_turn_c4_c3_consumption.py",
            ],
            cwd=staged,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        sys.stdout.write(run.stdout)
        sys.stderr.write(run.stderr)
        if run.returncode:
            raise SystemExit(run.returncode)

    if before != source_hashes():
        raise RuntimeError("full stage/test mutated a pinned source input")
    print(
        "FULL_COMPOSED_C4_C3_RUNTIME_TEST PASS "
        "(synthetic runners; actual full staged source composer)"
    )


if __name__ == "__main__":
    main()
