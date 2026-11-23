"""Model-free regressions for the hash-bound Termux chat recovery candidate."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest import mock

from scripts import termux_chat_recovery_candidate_20261112 as candidate
from v13.config import DEFAULTS


CODE = Path(__file__).resolve().parents[1]


def load_candidate(name, raw):
    module = types.ModuleType("v13." + name)
    module.__package__ = "v13"
    exec(compile(raw, "<chat-recovery-" + name + ">", "exec"), module.__dict__)
    return module


class HistoryStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.rows = [
            {"id": 1, "role": "user", "text": "previous user question"},
            {"id": 2, "role": "assistant", "text": "previous answer"},
        ]
        self.reads = 0

    def history(self, session, count):
        with self.lock:
            self.reads += 1
            return [dict(row) for row in self.rows[-count:]]


class TermuxChatRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = candidate.build_sources(CODE)

    def test_build_validates_pins_without_changing_frozen_files(self):
        before = {name: (CODE / name).read_bytes() for name in candidate.SOURCE_PINS}
        result = candidate.build_sources(CODE)
        self.assertEqual(set(result), set(candidate.SOURCE_PINS))
        for name, raw in before.items():
            self.assertEqual((CODE / name).read_bytes(), raw)
            self.assertNotEqual(result[name], raw)

    def test_fullscreen_renderer_is_unchanged(self):
        before = (CODE / "v13/ui.py").read_bytes().split(b"def chat(", 1)[1]
        after = self.sources["v13/ui.py"].split(b"def chat(", 1)[1]
        self.assertEqual(after, before)

    def test_plain_skips_old_answers_but_streams_new_and_continued_rows(self):
        ui = load_candidate("recovery_ui", self.sources["v13/ui.py"])
        store = HistoryStore()
        runtime = types.SimpleNamespace(store=store, session="persisted", stop=threading.Event())
        output = io.StringIO()
        initial_render = threading.Event()
        original_history = store.history

        def history(session, count):
            rows = original_history(session, count)
            if store.reads >= 2:
                initial_render.set()
            return rows

        store.history = history

        def read_once(_):
            self.assertTrue(initial_render.wait(2), "plain renderer did not poll")
            with store.lock:
                store.rows[1]["text"] += " + continued output"
                store.rows.append({"id": 3, "role": "assistant", "text": "new answer"})
            # Wait for the actual renderer to emit both changes.
            import time
            deadline = time.monotonic() + 2
            while "assistant> new answer" not in output.getvalue():
                self.assertLess(time.monotonic(), deadline, output.getvalue())
                time.sleep(.01)
            runtime.stop.set()
            return ":shutdown"

        with mock.patch.object(ui, "Operator") as op, \
                mock.patch.object(ui, "read_block", side_effect=read_once), \
                mock.patch.object(ui, "typing", return_value=False), redirect_stdout(output):
            op.return_value.run.return_value = ""
            ui.plain(runtime)
        text = output.getvalue()
        self.assertIn("Bisheriger Verlauf gespeichert; neue Ausgabe folgt.", text)
        self.assertNotIn("previous answer", text)
        self.assertNotIn("previous user question", text)
        self.assertEqual(text.count(" + continued output"), 1)
        self.assertEqual(text.count("assistant> new answer"), 1)

    def test_plain_empty_history_has_no_prior_history_notice(self):
        ui = load_candidate("empty_recovery_ui", self.sources["v13/ui.py"])
        runtime = types.SimpleNamespace(store=HistoryStore(), session="empty", stop=threading.Event())
        runtime.store.rows.clear()
        output = io.StringIO()

        def read_once(_):
            runtime.stop.set()
            return ":shutdown"

        with mock.patch.object(ui, "Operator") as op, \
                mock.patch.object(ui, "read_block", side_effect=read_once), redirect_stdout(output):
            op.return_value.run.return_value = ""
            ui.plain(runtime)
        self.assertNotIn("Bisheriger Verlauf", output.getvalue())

    def test_learning_status_works_during_job_without_idle_or_write(self):
        operator = load_candidate("recovery_operator", self.sources["v13/operator.py"])
        runtime = types.SimpleNamespace(
            store=object(), cfg={"learning_mode": "RECORD_ONLY"},
            current="probe", require_idle=mock.Mock(side_effect=ValueError("busy")),
        )
        with mock.patch.object(operator, "save_config") as save:
            result = json.loads(operator.Operator(runtime).run(":learning"))
        self.assertEqual(result, {"learning_mode": "RECORD_ONLY", "read_only": True})
        runtime.require_idle.assert_not_called()
        save.assert_not_called()

    def test_explicit_learning_changes_still_require_idle(self):
        operator = load_candidate("busy_recovery_operator", self.sources["v13/operator.py"])
        for value in ("record", "shadow", "commit"):
            with self.subTest(value=value):
                runtime = types.SimpleNamespace(
                    store=object(), cfg={"learning_mode": "RECORD_ONLY"},
                    require_idle=mock.Mock(side_effect=ValueError("busy")),
                )
                with self.assertRaisesRegex(ValueError, "busy"):
                    operator.Operator(runtime).run(":learning " + value)
                self.assertEqual(runtime.cfg, {"learning_mode": "RECORD_ONLY"})

    def test_idle_learning_changes_keep_validation_and_persistence(self):
        operator = load_candidate("idle_recovery_operator", self.sources["v13/operator.py"])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "config").mkdir()
            runtime = types.SimpleNamespace(store=object(), cfg=dict(DEFAULTS), home=root,
                                            require_idle=mock.Mock())
            op = operator.Operator(runtime)
            for command, expected in (("record", "RECORD_ONLY"), ("shadow", "SHADOW_UPDATE"),
                                      ("commit", "APPROVED_COMMIT")):
                self.assertIn(expected, op.run(":learning " + command))
                saved = json.loads((root / "config/settings.json").read_text())
                self.assertEqual(saved["learning_mode"], expected)
            prior = (root / "config/settings.json").read_bytes()
            with self.assertRaises(ValueError):
                op.run(":learning unrecognized")
            self.assertEqual((root / "config/settings.json").read_bytes(), prior)
            self.assertEqual(runtime.cfg["learning_mode"], "APPROVED_COMMIT")

    def test_pin_mismatch_or_symlink_is_refused(self):
        for changed in candidate.SOURCE_PINS:
            with self.subTest(path=changed), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                for name in candidate.SOURCE_PINS:
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((CODE / name).read_bytes())
                target = root / changed
                target.write_bytes(target.read_bytes() + b"\n# source changed\n")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    candidate.build_sources(root)
                target.unlink()
                target.symlink_to(CODE / changed)
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    candidate.build_sources(root)

    def test_composition_preserves_unrelated_integrated_operator_edits(self):
        originals = {name: (CODE / name).read_bytes() for name in candidate.SOURCE_PINS}
        injected = b"        if cmd=='onlineworld':return 'preserved integrated command'\n"
        originals["v13/operator.py"] = originals["v13/operator.py"].replace(
            b"        if cmd=='help':return HELP\n", b"        if cmd=='help':return HELP\n" + injected)
        result = candidate.apply_sources(originals)
        self.assertIn(injected, result["v13/operator.py"])
        operator = load_candidate("composed_recovery_operator", result["v13/operator.py"])
        runtime = types.SimpleNamespace(store=object())
        self.assertEqual(operator.Operator(runtime).run(":onlineworld"), "preserved integrated command")

    def test_missing_or_repeated_anchor_is_refused(self):
        originals = {name: (CODE / name).read_bytes() for name in candidate.SOURCE_PINS}
        for replacement in (b"", b"        if cmd=='status':return dumps(\n" * 2):
            mutated = dict(originals)
            mutated["v13/operator.py"] = mutated["v13/operator.py"].replace(
                b"        if cmd=='status':return dumps(", replacement)
            with self.assertRaisesRegex(ValueError, "anchor changed"):
                candidate.apply_sources(mutated)


if __name__ == "__main__":
    unittest.main()
