from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys


CODE = Path(__file__).resolve().parents[1]
SOURCE_BLOBS = {
    "v13/runtime.py": "30360f40eb784be5ea975ee85e94a57f0b154164",
    "v13/cognition.py": "90138474db6f7c0b66cea24f52d22cd7a6e2f87b",
    "v13/audio_voice_cues.py": "7ac80a0d0deec8f52361fe89756ebd743b0a3537",
}
BUILDER_SHA256 = "563c77338970aebb84f1836a930c34671bf0a94455d924aa51a510b101eae1fc"


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _load_stager():
    path = CODE / "scripts/stage_integrated_candidate.py"
    spec = importlib.util.spec_from_file_location("v14_audio_stage_stager", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("stage builder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audio_voice_and_arithmetic_share_one_hash_bound_stage(tmp_path):
    source_before = {
        relative: _git_blob_sha1((CODE / relative).read_bytes())
        for relative in SOURCE_BLOBS
    }
    assert source_before == SOURCE_BLOBS

    destination = tmp_path / "staged"
    manifest = _load_stager().stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert manifest["builder"] == "scripts/termux_runtime_recovery_candidate_20261121.py"
    assert manifest["builder_sha256"] == BUILDER_SHA256
    assert {"v13/runtime.py", "v13/cognition.py", "v13/arithmetic_reflex.py"} <= set(
        manifest["replaced_files"]
    )

    runtime = (destination / "v13/runtime.py").read_text(encoding="utf-8")
    cognition = (destination / "v13/cognition.py").read_text(encoding="utf-8")
    assert "not fixed_policy and arithmetic_answer is None" in runtime
    assert "LOCAL_EXACT_ARITHMETIC" in runtime
    assert "audio_source_refs" in runtime
    assert "finality=audio_window['finality']" in runtime
    assert "segment.get('finality')!='FINAL'" in runtime
    assert "consume_pcm16_voice_window" in runtime
    assert "voice_cues=validate_voice_cues" in runtime
    assert "'voice_cues':voice_cues" in runtime
    assert "voice_cue_method" in runtime
    assert "c3_prompt_included" in runtime
    assert "if not included:meta.pop('audio_source_refs',None);audio_source_ref=None" in runtime
    assert "audio_context_refs" in cognition
    assert "audio_context=audio_context_packet" in cognition
    assert "self._audio_context_query(e,offer['role'])" in cognition
    assert "audio_offer_omitted" in cognition
    assert "Consumer audio context source mismatch" in cognition
    assert (destination / "v13/audio_voice_cues.py").is_file()

    test_names = (
        "test_c3_audio_runtime_consumer.py",
        "test_arithmetic_reflex.py",
        "arithmetic_disposable_cases_20261116.py",
        "arithmetic_outcome_disposable_cases_20261116.py",
        "test_broker.py",
        "test_output_policy.py",
        "test_v14_arithmetic_policy_separation.py",
    )
    staged_tests = destination / "tests"
    staged_tests.mkdir(exist_ok=True)
    for name in test_names:
        source = CODE / "tests" / name
        assert source.is_file(), "missing staged regression: " + name
        shutil.copy2(source, staged_tests / name)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(destination)
    command = [sys.executable, "-m", "pytest", "-q"] + [
        "tests/" + name for name in test_names
    ]
    result = subprocess.run(
        command, cwd=destination, env=env, text=True, capture_output=True, timeout=240
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert {
        relative: _git_blob_sha1((CODE / relative).read_bytes())
        for relative in SOURCE_BLOBS
    } == SOURCE_BLOBS
