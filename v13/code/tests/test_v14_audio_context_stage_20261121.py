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
    "v13/cognition.py": "06de0acf2c6d30d50301d5073f5569822edff813",
    "v13/audio_voice_cues.py": "e75c393939183d2f16e071ebf4a6f5ff65417a61",
    "v13/audio_temporal_evidence.py": "098ce2ec6bb0b744166d711a3401b7acf0252de1",
    "v13/focal.py": "a0588a768cc91266ef02243bcfda2e631860d8ad",
}
BUILDER_SHA256 = "06297e4f0e9a33e50fe8a5d38f8dc77839889cc09afd8366116c11fffc564b40"


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
    assert "consent_guard=audio_window['consent_guard']" in runtime
    assert "C3_NATIVE_DISPATCH" in runtime
    assert "REVOKED_BEFORE_C3_DISPATCH" in runtime
    assert "finality=audio_window['finality']" in runtime
    assert "segment.get('finality')!='FINAL'" in runtime
    assert "consume_pcm16_voice_window" in runtime
    assert "voice_cues=validate_voice_cues" in runtime
    assert "'voice_cues':voice_cues" in runtime
    assert "voice_cue_method" in runtime
    assert "c3_prompt_included" in runtime
    assert "if not included:meta.pop('audio_source_refs',None);audio_source_ref=None" in runtime
    assert "audio_context_refs" in cognition
    assert "CONSENT_REVOKED_BEFORE_DISPATCH" in cognition
    assert "audio_context=audio_context_packet" in cognition
    assert "self._audio_context_query(e,offer['role'])" in cognition
    assert "audio_offer_omitted" in cognition
    assert "STORED_SOURCE_MISMATCH" in cognition
    assert "QUERY_CONTEXT_MISMATCH" in cognition
    assert (destination / "v13/audio_voice_cues.py").is_file()
    assert (destination / "v13/audio_temporal_evidence.py").is_file()
    audio_store = destination / "v13/audio_context_store.py"
    assert audio_store.is_file()
    assert "UPDATE sources SET deleted=1" in audio_store.read_text(encoding="utf-8")
    staged_focal = (destination / "v13/focal.py").read_text(encoding="utf-8")
    assert "SCALE_AWARE_C4_RULE = 'DISJOINT_SAME_SOURCE_SPANS_ONLY'" in staged_focal
    assert "_scale_aware_redundancy(c,a)" in staged_focal

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
