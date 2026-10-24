"""Run88 preregistered SQLite/Operator literal :search regression tests.

No models, no training, no native execution, no authority or gate promotion.
"""
import json
import tempfile
import unittest
from pathlib import Path

from v13.operator import Operator
from v13.runtime import Runtime


class LiteralSearchRun88(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = Runtime(Path(self.temp.name))
        self.runtime.sleep.cycle.set_policy("enabled", "off")
        self.operator = Operator(self.runtime)

    def tearDown(self):
        self.runtime.close()
        self.temp.cleanup()

    def add(self, text):
        self.runtime.store.event(self.runtime.session, text)

    def found(self, query):
        return [row["text"] for row in json.loads(self.operator.run(query))
                if row["role"] == "user"]

    def test_underscore_is_literal_not_any_character(self):
        self.add("alpha_1")
        self.add("alphaX1")
        self.assertEqual(self.found(":search alpha_1"), ["alpha_1"])

    def test_percent_is_literal_not_any_substring(self):
        self.add("100% done")
        self.add("100 percent done")
        self.assertEqual(self.found(':search "100%"'), ["100% done"])

    def test_backslash_is_literal_and_ascii_case_insensitive_is_preserved(self):
        slash = chr(92)
        self.add("path" + slash + "notes")
        self.add("pathnotes")
        self.assertEqual(self.found(':search "path' + slash + 'notes"'),
                         ["path" + slash + "notes"])
        self.add("MiXeD Case")
        self.assertEqual(self.found(':search "mixed case"'), ["MiXeD Case"])


if __name__ == "__main__":
    unittest.main()
