"""V14 regression for the current Runtime's exact-arithmetic direct path."""
import ast
from pathlib import Path

from v13.exact_arithmetic import evidence, direct_output


def test_direct_output_priority_and_missing_match_safety():
    arithmetic = evidence("2+2")
    assert arithmetic["result"] == "4"
    assert direct_output(arithmetic=arithmetic) == "4"
    assert direct_output(fixed_answer="approved", arithmetic=arithmetic) == "approved"
    assert direct_output(exact_copy="literal", arithmetic=arithmetic) == "literal"


def test_runtime_wires_evidence_to_direct_c5_output():
    runtime = Path(__file__).resolve().parents[1] / "v13" / "runtime.py"
    tree = ast.parse(runtime.read_text(encoding="utf-8"), filename=str(runtime))
    turn = next(node for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name == "_turn")
    calls = {node.func.id for node in ast.walk(turn)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    imports = {node.module for node in ast.walk(turn)
               if isinstance(node, ast.ImportFrom)}
    literals = {node.value for node in ast.walk(turn)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    assert "evidence" in calls or "arithmetic_evidence" in calls
    assert "direct_output" in calls
    assert "exact_arithmetic" in imports
    assert "ExactArithmeticDecision" in literals
    assert "EXACT_ARITHMETIC" in literals
