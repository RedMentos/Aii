"""V14 regression for the real fixed-policy consumer of exact arithmetic."""
import ast
import hashlib
import threading
from pathlib import Path

from v13.output_policy import match


class FakeStore:
    def __init__(self):
        self.mutex = threading.RLock()
        self.sources = []

    def source(self, text, kind):
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        ref = {
            "source_id": f"source-{len(self.sources) + 1}",
            "sha256": digest,
            "char_start": 0,
            "char_end": len(text),
            "modality": "text",
        }
        self.sources.append((text, kind, ref))
        return ref

    def generation(self):
        return {"rule_version": 1}

    def one(self, sql, params):
        return {"rules": "[]"}


def test_exact_arithmetic_returns_source_bound_fixed_policy():
    store = FakeStore()
    policy = match(store, "2+2")
    assert policy["answer"] == "4"
    assert policy["kind"] == "SYSTEM_DETERMINISTIC_ARITHMETIC"
    assert policy["rule_id"] == "fixed_builtin_exact_integer_arithmetic_v1"
    assert policy["rule_version"] == "builtin-1"
    assert policy["model_generated"] is False
    assert policy["output_authority"] == "APPROVED_FIXED_RULE"
    assert [item[1] for item in store.sources] == [
        "SYSTEM_DETERMINISTIC_QUERY", "SYSTEM_DETERMINISTIC_ANSWER"
    ]
    assert store.sources[0][0] == "2+2"
    assert store.sources[1][0] == "4"


def test_ambiguous_or_date_shaped_input_stays_on_normal_route():
    store = FakeStore()
    for prompt in ("2+2 and explain", "1+2+3", "2026-11", "please run 2+2"):
        assert match(store, prompt) is None
    assert store.sources == []


def test_runtime_already_consumes_policy_before_perception_and_output():
    runtime = Path(__file__).resolve().parents[1] / "v13" / "runtime.py"
    source = runtime.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(runtime))
    turn = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "_turn")
    calls = {node.func.id for node in ast.walk(turn)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    literals = {node.value for node in ast.walk(turn)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert "match" in calls
    assert "output_policy" in literals
    assert "APPROVED_FIXED_RULE" in literals
    assert "fixed_policy['answer']" in source

def test_human_fixed_rule_keeps_precedence_over_builtin_arithmetic():
    from unittest.mock import patch
    store = FakeStore()
    item = {
        "entry": {
            "rule_id": "fixed_0123456789abcdef0123456789abcdef",
            "query_ref": {"source_id": "human-query"},
            "answer_ref": {"source_id": "human-answer"},
        },
        "query": "2+2",
        "answer": "operator answer",
    }
    with patch("v13.output_policy.validate_rules", return_value=[item]):
        policy = match(store, "2+2")
    assert policy["answer"] == "operator answer"
    assert policy["rule_id"] == item["entry"]["rule_id"]
    assert store.sources == []
