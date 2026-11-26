"""Regression for composing consent-bound RAW EAR with Core fair-budget Cognition."""
import importlib.util
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


def test_full_audio_composition_preserves_core_budget_and_native_receiver_contracts():
    module = load_builder()
    source_path = CODE / "v13/cognition.py"
    source_before = source_path.read_bytes()

    composed = module.build_sources(CODE)
    cognition = composed["v13/cognition.py"]

    assert b"def _audio_context_query(" in cognition
    assert b"audio_context_refs" in cognition
    assert b"preanswer_budgeted=None" in cognition
    assert b"preanswer_observer = (valid_until is not None if preanswer_budgeted is None else preanswer_budgeted)" in cognition
    assert b"minimum_role_slice_s" in cognition
    assert b"def native_receive(" in cognition
    assert b"c4_offer_context_ready" in cognition
    assert source_path.read_bytes() == source_before
