"""Regression for composing consent-bound RAW EAR with Core fair-budget Cognition."""
import hashlib
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

CODE = Path(__file__).resolve().parents[1]
BUILDER_PATH = CODE / "scripts/termux_runtime_recovery_candidate_20261121.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("core_audio_observer_composition", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preanswer_budget_contract_normalization_is_exact_and_reversible():
    module = load_builder()
    base = module._load(CODE, module.BASE_BUILDER, module.BASE_BUILDER_BLOB_SHA1)
    result = base.build_sources(CODE)
    original = result["v13/cognition.py"]

    normalized, changed = module._normalize_preanswer_budget_contract(original)
    assert changed is True
    assert module._PREANSWER_SIGNATURE in normalized
    assert module._PREANSWER_BUDGET_SIGNATURE not in normalized
    assert module._PREANSWER_BODY in normalized
    assert module._PREANSWER_BUDGET_BODY not in normalized
    assert module._restore_preanswer_budget_contract(normalized, changed) == original

    with pytest.raises(ValueError, match="contract changed or is ambiguous"):
        module._normalize_preanswer_budget_contract(
            original.replace(module._PREANSWER_BUDGET_BODY, b"", 1)
        )
    with pytest.raises(ValueError, match="contract changed or is ambiguous"):
        module._normalize_preanswer_budget_contract(original + original)



def test_context_os_audio_composition_preserves_core_source_recall_refs():
    module = load_builder()
    core_runtime = b"prefix" + module._CONTEXT_PROVENANCE_RECALL + b"suffix"
    normalized, changed = module._normalize_context_provenance_contract(core_runtime)
    assert changed is True
    assert normalized == b"prefix" + module._CONTEXT_PROVENANCE_BASE + b"suffix"

    audio_runtime = (
        b"main:" + module._CONTEXT_PROVENANCE_AUDIO
        + b"\nrevoke:" + module._CONTEXT_PROVENANCE_BASE
    )
    restored = module._restore_context_provenance_contract(audio_runtime, changed)
    assert restored == (
        b"main:" + module._CONTEXT_PROVENANCE_RECALL_AUDIO
        + b"\nrevoke:" + module._CONTEXT_PROVENANCE_RECALL
    )

    with pytest.raises(ValueError, match="changed or is ambiguous"):
        module._normalize_context_provenance_contract(core_runtime + core_runtime)
    with pytest.raises(ValueError, match="normalized Core Context OS provenance anchors"):
        module._restore_context_provenance_contract(audio_runtime + audio_runtime, changed)


def test_audio_context_refs_preserve_core_source_recall_and_duplex_refs():
    module = load_builder()
    original = (
        b"    context_refs=[e['source_ref'],*meta.get('source_recall_refs',[]),"
        b"*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[])]\n"
    )
    normalized, saved = module._normalize_audio_context_refs(original)
    assert saved == original
    assert normalized == b"    " + module._CONTEXT_REFS_BASE + b"\n"

    audio_line = b"    " + module._CONTEXT_REFS_AUDIO + b"\n"
    restored = module._restore_audio_context_refs(audio_line, saved)
    assert restored == (
        b"    context_refs=[e['source_ref'],*meta.get('audio_source_refs',[]),"
        b"*meta.get('source_recall_refs',[]),*self.consolidation.source_refs(memories),"
        b"*history_refs,*meta.get('duplex_handoff_refs',[])]\n"
    )
    with pytest.raises(ValueError, match="changed or are ambiguous"):
        module._normalize_audio_context_refs(original + original)
    with pytest.raises(ValueError, match="changed or duplicated"):
        module._restore_audio_context_refs(audio_line + audio_line, saved)


def test_full_audio_composition_preserves_core_budget_and_native_receiver_contracts():
    module = load_builder()
    source_path = CODE / "v13/cognition.py"
    source_before = source_path.read_bytes()

    composed = module.build_sources(CODE)
    cognition = composed["v13/cognition.py"]
    runtime = composed["v13/runtime.py"]
    assert b"provenance=[e['source_ref']]+meta.get('source_recall_refs',[])+([audio_source_ref] if audio_source_ref else [])" in runtime
    assert b"provenance=[e['source_ref']]+meta.get('source_recall_refs',[]),budget_scale=" in runtime
    assert b"context_refs=[e['source_ref'],*meta.get('audio_source_refs',[])," in runtime
    assert b"*meta.get('source_recall_refs',[])" in runtime
    assert b"from .greeting_fastpath import match as greeting_match" in runtime
    assert b"BUILTIN_GREETING_REFLEX" in runtime

    assert b"def _audio_context_query(" in cognition
    assert b"audio_context_refs" in cognition
    assert b"preanswer_budgeted=None" in cognition
    assert b"preanswer_observer = (valid_until is not None if preanswer_budgeted is None else preanswer_budgeted)" in cognition
    assert b"minimum_role_slice_s" in cognition
    assert b"def native_receive(" in cognition
    assert b"c4_offer_context_ready" in cognition
    source_fastforward = (CODE / "tests/test_fastforward_reflex.py").read_bytes()
    staged_fastforward = composed["tests/test_fastforward_reflex.py"]
    # Preserve the pinned source fixture; only the staged candidate must avoid the exact greeting reflex.
    assert b"self.r.submit('hello there')" in source_fastforward
    assert b"self.r.submit('Please explain the current task.')" in staged_fastforward
    assert source_path.read_bytes() == source_before


def test_staged_runtime_greeting_and_acknowledgment_path_end_to_end():
    stage_path = CODE / "scripts/stage_integrated_candidate.py"
    spec = importlib.util.spec_from_file_location("stage_for_greeting_runtime", stage_path)
    stage_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage_module)

    with tempfile.TemporaryDirectory(prefix="v14-greeting-stage-") as tmp:
        staged = Path(tmp) / "staged"
        manifest = stage_module.stage(CODE, staged)
        assert "v13/runtime.py" in manifest["replaced_files"]
        assert (staged / "v13/greeting_fastpath.py").is_file()

        env = os.environ.copy()
        env["PYTHONPATH"] = str(staged) + os.pathsep + str(CODE)
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest", "-q",
                str(CODE / "tests/test_greeting_fastpath_runtime.py"),
            ],
            cwd=staged,
            env=env,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_android_ui_overlay_locates_current_fair_budget_ask_signatures():
    path = CODE / "scripts/integrated_android_ui_runtime_candidate_20261127.py"
    spec = importlib.util.spec_from_file_location("android_ui_runtime_overlay", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    signatures = (
        b"                def ask(role,focus=None,use_peer=True):",
        b"                def ask(role,focus=None,use_peer=True,role_end=None):",
        b"                def ask(role,focus=None,use_peer=True,role_end=None,preanswer_budgeted=True):",
    )
    for signature in signatures:
        raw = signature + b"\n                    pass\n                sched=object()\n"
        start, end = module._ask_block_bounds(raw)
        assert raw[start:end].startswith(signature)
        assert raw[end:].startswith(b"\n                sched=")

    duplicate = signatures[-1] + b"\n                def ask(role,focus=None,use_peer=True):\n"
    with pytest.raises(ValueError, match="exactly one"):
        module._ask_block_bounds(duplicate)

    unsupported = signatures[-1].replace(
        b"preanswer_budgeted=True", b"unreviewed=False"
    ) + b"\n                sched=object()\n"
    with pytest.raises(ValueError, match="unsupported optional parameters"):
        module._ask_block_bounds(unsupported)

