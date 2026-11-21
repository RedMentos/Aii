from __future__ import annotations

import ast
import importlib.util
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
OVERLAY = CODE / "scripts/integrated_audio_context_candidate_20261121.py"


def _load_overlay():
    spec = importlib.util.spec_from_file_location("v14_voice_audio_overlay", OVERLAY)
    if spec is None or spec.loader is None:
        raise RuntimeError("audio overlay unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _window_validator(runtime_bytes):
    tree = ast.parse(runtime_bytes.decode("utf-8"))
    nodes = [
        node for node in tree.body
        if (isinstance(node, ast.FunctionDef) and node.name == "_validate_audio_window")
        or (isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "_AUDIO_WINDOW_FIELDS"
                    for target in node.targets))
    ]
    assert len(nodes) == 2
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<audio-window-validator>", "exec"), namespace)
    return namespace["_validate_audio_window"]


def test_voice_overlay_composes_on_exact_shared_runtime_sources():
    overlay = _load_overlay()
    sources = {
        "v13/runtime.py": (CODE / "v13/runtime.py").read_bytes(),
        "v13/cognition.py": (CODE / "v13/cognition.py").read_bytes(),
        "v13/arithmetic_reflex.py": (CODE / "v13/arithmetic_reflex.py").read_bytes(),
    }
    result = overlay.apply_sources(CODE, sources)
    runtime = result["v13/runtime.py"]
    cognition = result["v13/cognition.py"]
    compile(runtime, "v13/runtime.py", "exec")
    compile(cognition, "v13/cognition.py", "exec")

    assert "v13/audio_voice_cues.py" in overlay.SOURCE_BLOBS
    assert (CODE / "v13/audio_voice_cues.py").is_file()
    assert b"consume_pcm16_voice_window" in runtime
    assert b"finality=audio_window['finality']" in runtime
    assert b"voice_activity_hint" in runtime
    assert b"consume_pcm16_window" not in runtime


def test_audio_window_requires_explicit_finality_and_preserves_provisional():
    overlay = _load_overlay()
    sources = {
        "v13/runtime.py": (CODE / "v13/runtime.py").read_bytes(),
        "v13/cognition.py": (CODE / "v13/cognition.py").read_bytes(),
        "v13/arithmetic_reflex.py": (CODE / "v13/arithmetic_reflex.py").read_bytes(),
    }
    result = overlay.apply_sources(CODE, sources)
    validate = _window_validator(result["v13/runtime.py"])
    window = {
        "pcm16": b"\x00\x00",
        "sample_rate": 8000,
        "start_ms": 100,
        "source_id": "fixture:audio",
        "consent_receipt": "fixture:consent",
        "consent_check": lambda source, receipt: True,
        "finality": "PROVISIONAL",
    }
    accepted = validate(window)
    assert accepted["finality"] == "PROVISIONAL"
    assert validate(window | {"finality": "FINAL"})["finality"] == "FINAL"

    missing = dict(window)
    missing.pop("finality")
    try:
        validate(missing)
    except ValueError:
        pass
    else:
        raise AssertionError("missing finality must fail closed")

    try:
        validate(window | {"finality": "PARTIAL"})
    except ValueError as exc:
        assert "finality" in str(exc)
    else:
        raise AssertionError("unknown finality must fail closed")
