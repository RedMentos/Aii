"""Independent BP11b regression: typed module export must honor fixed local-write bans."""
import json
import unittest
from pathlib import Path

from tests.test_modules_gate import Base, H
from v13 import modules_gate as M, prohibitions as P
from v13 import module_learn


class ExportGateReview(Base):
    def ready_for_export(self):
        mid, _ = self.ready()
        self.activate(mid)
        M.set_learn(self.s, True, authority=H)
        return Path(self.tmp.name) / 'module-export.jsonl'

    def test_positive_explicit_export_is_tagged_and_never_trains(self):
        path = self.ready_for_export()
        result = M.operator_command(self.r, ['export', str(path)])
        self.assertIn('Einträge', result)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row['tag'].startswith('MODULE:M1:') for row in rows))

    def test_write_local_ban_blocks_typed_export_before_file_creation(self):
        path = self.ready_for_export()
        P.add(self.s, 'risk', 'WRITE_LOCAL', authority=H)
        with self.assertRaises(PermissionError):
            M.operator_command(self.r, ['export', str(path)])
        self.assertFalse(path.exists())
        self.assertEqual(len(M.corpus(self.s)), 2)

    def test_specific_module_export_tool_ban_blocks_direct_api(self):
        path = self.ready_for_export()
        P.add(self.s, 'tool', 'module_export', authority=H)
        with self.assertRaises(PermissionError):
            module_learn.export_dataset(self.s, path)
        self.assertFalse(path.exists())

    def test_notaus_precedes_empty_corpus_and_does_not_write(self):
        path = self.ready_for_export()
        P.halt(self.s, True, authority=H)
        with self.assertRaises(PermissionError):
            M.operator_command(self.r, ['export', str(path)])
        self.assertFalse(path.exists())

    def test_read_only_module_question_is_conservatively_blocked_by_write_ban(self):
        self.ready_for_export()
        P.add(self.s, 'risk', 'WRITE_LOCAL', authority=H)
        result = M.operator_command(self.r, ['frage', 'Hauptstadt von Frankreich'])
        self.assertIn('Nichts Passendes', result)


if __name__ == '__main__':
    unittest.main()
