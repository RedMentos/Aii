from __future__ import annotations

import ast
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
OVERLAY = CODE / "scripts/integrated_audio_context_candidate_20261121.py"


def _load_overlay():
    namespace = {}
    source = OVERLAY.read_text(encoding="utf-8")
    exec(compile(source, str(OVERLAY), "exec"), namespace)
    return namespace


def _validator_from_overlay(source):
    tree = ast.parse(source)
    replacement = None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name) or node.func.id != "_replace":
            continue
        if len(node.args) < 4:
            continue
        label = node.args[3]
        if isinstance(label, ast.Constant) and label.value == "Runtime audio validator":
            value = node.args[2]
            assert isinstance(value, ast.Constant) and isinstance(value.value, bytes)
            replacement = value.value
            break
    assert replacement is not None
    marker = b"class Runtime:\n"
    assert replacement.endswith(marker)
    snippet = replacement[:-len(marker)]
    snippet_tree = ast.parse(snippet.decode("utf-8"))
    nodes = [
        node for node in snippet_tree.body
        if (isinstance(node, ast.FunctionDef) and node.name == "_validate_audio_window")
        or (isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "_AUDIO_WINDOW_FIELDS"
                    for target in node.targets))
    ]
    assert len(nodes) == 2
    namespace = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<audio-window-validator>", "exec"), namespace)
    return namespace["_validate_audio_window"]


def test_voice_overlay_pins_exact_sources_and_uses_raw_ear_voice_cues():
    overlay = _load_overlay()
    for relative, expected in overlay["SOURCE_BLOBS"].items():
        path = CODE / relative
        assert path.is_file() and not path.is_symlink()
        raw = path.read_bytes()
        assert overlay["_git_blob_sha1"](raw) == expected, relative

    source = OVERLAY.read_text(encoding="utf-8")
    compile(source, str(OVERLAY), "exec")
    assert overlay["SOURCE_BLOBS"]["v13/audio_voice_cues.py"] == "7ac80a0d0deec8f52361fe89756ebd743b0a3537"
    assert "consume_pcm16_voice_window" in source
    assert "finality=audio_window['finality']" in source
    assert "voice_activity_hint" in source
    assert "consume_pcm16_window" not in source


def test_audio_window_requires_explicit_finality_and_preserves_provisional():
    source = OVERLAY.read_text(encoding="utf-8")
    validate = _validator_from_overlay(source)
    window = {
        "pcm16": b"\x00\x00",
        "sample_rate": 8000,
        "start_ms": 100,
        "source_id": "fixture:audio",
        "consent_receipt": "fixture:consent",
        "consent_check": lambda source, receipt: True,
        "finality": "PROVISIONAL",
    }
    assert validate(window)["finality"] == "PROVISIONAL"
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
