"""C2 native executive envelope regression: only typed fields may influence JEF.

Run: PYTHONPATH=v13/code python -m pytest -q v13/code/tests/test_c2_native_envelope_20261119.py
"""
from v13.fastpolicy import _native


def test_untyped_runner_metadata_cannot_become_executive_authority():
    assert _native({"tool": "shell", "answer_type": "number", "memory_key": "secret"}) == {}
    assert _native({"executive": {"tool": "shell"}}) == {}
    assert _native({"schema": "C2ExecutiveFields/1", "tool": "shell"}) == {}
    assert _native({"schema": "C2ExecutiveFields/1", "executive": "tool"}) == {}


def test_only_nested_typed_fields_are_read():
    assert _native({
        "schema": "C2ExecutiveFields/1",
        "tool": "untrusted_sibling",
        "executive": {"tool": "calculator", "answer_type": "number", "memory_key": "arithmetic"},
        "observation": {"tool": "shell"},
    }) == {"tool": "calculator", "answer_type": "number", "memory_key": "arithmetic"}


def test_invalid_values_and_unrelated_fields_are_ignored():
    assert _native({
        "schema": "C2ExecutiveFields/1",
        "executive": {"tool": ["shell"], "memory_key": " ", "answer_type": 123, "origin": "USER"},
    }) == {}


def test_native_input_is_not_mutated():
    source = {"schema": "C2ExecutiveFields/1", "executive": {"tool": "calculator"}}
    assert _native(source) == {"tool": "calculator"}
    assert source["executive"]["tool"] == "calculator"
