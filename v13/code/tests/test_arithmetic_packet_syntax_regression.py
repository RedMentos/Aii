"""Regression: arithmetic packet integration must remain valid Python source.

The original integration accidentally inserted literal backslash-n escape sequences
into fastpolicy.py, making every import of that module fail before chat startup.
"""
import ast
import pathlib
import unittest


class ArithmeticPacketSyntaxRegression(unittest.TestCase):
    def test_fastpolicy_compiles_and_contains_arithmetic_packet(self):
        source = pathlib.Path(__file__).resolve().parents[1] / "v13" / "fastpolicy.py"
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        funcs = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.assertIn("c2_packet", {node.name for node in funcs})
        packet = next(node for node in funcs if node.name == "c2_packet")
        self.assertTrue(any(
            isinstance(node, ast.ImportFrom) and node.module == "arithmetic_evidence"
            for node in ast.walk(packet)
        ))


if __name__ == "__main__":
    unittest.main()
