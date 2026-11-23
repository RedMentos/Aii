"""QA negative controls for date-shaped subtraction in the staged exact-arithmetic path."""
from __future__ import annotations

import importlib.util
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
STAGER = CODE / "scripts" / "stage_integrated_candidate.py"


def _stage(code_dir: Path, destination: Path):
    spec = importlib.util.spec_from_file_location("v14_arithmetic_qa_stager", STAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("V14 staged Runtime builder unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.stage(code_dir, destination)


def _load_exact_arithmetic(destination: Path):
    path = destination / "v13" / "arithmetic_reflex.py"
    spec = importlib.util.spec_from_file_location("v14_staged_arithmetic_reflex", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("staged exact-arithmetic module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.exact_arithmetic


def test_date_shaped_subtraction_requires_an_explicit_math_verb(tmp_path):
    destination = tmp_path / "candidate"
    manifest = _stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert manifest["arithmetic_overlay"]["status"] == "SHADOW_REVIEW_ONLY"

    exact_arithmetic = _load_exact_arithmetic(destination)

    # Clear math remains available in English and German.
    assert exact_arithmetic("2+2") == "4"
    assert exact_arithmetic("Was ist 2+2?") == "4"
    assert exact_arithmetic("Wie viel ist 2+2?") == "4"
    assert exact_arithmetic("calculate 11-21") == "-10"
    assert exact_arithmetic("compute 11-21") == "-10"
    assert exact_arithmetic("berechne 11-21") == "-10"

    # These are date-shaped or ambiguous month/day expressions. A generic
    # question prefix is not an explicit math verb and must not force subtraction.
    assert exact_arithmetic("2026-11") is None
    assert exact_arithmetic("What is 2026-11?") is None
    assert exact_arithmetic("What is 11-21?") is None
    assert exact_arithmetic("Was ist 11-21?") is None
    assert exact_arithmetic("11-21") is None
    assert exact_arithmetic("7-12") is None
