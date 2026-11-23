"""Preregistered explicit generator-finally execution on C3 collector abort."""
import unittest
from scripts import ask_verified_budget as V


class C3GeneratorFinalizerTests(unittest.TestCase):
    def make(self, chunks, closed):
        def generate():
            try:
                for chunk in chunks:
                    yield chunk
            finally:
                closed.append(True)
        return generate()

    def test_retained_oversized_generator_finally_runs_before_return(self):
        closed = []
        stream = self.make([" " * 32769, "615 Euro."], closed)
        self.assertIsNone(V._collect_bounded_output(stream))
        self.assertEqual(closed, [True])
        self.assertEqual(list(stream), [])

    def test_retained_non_string_generator_finally_runs_before_return(self):
        closed = []
        stream = self.make(["615", b" Euro", "."], closed)
        self.assertIsNone(V._collect_bounded_output(stream))
        self.assertEqual(closed, [True])
        self.assertEqual(list(stream), [])

    def test_valid_short_stream_is_preserved_and_finalized(self):
        closed = []
        stream = self.make(["615", " Euro", "."], closed)
        self.assertEqual(V._collect_bounded_output(stream), "615 Euro.")
        self.assertEqual(closed, [True])


if __name__ == "__main__":
    unittest.main()
