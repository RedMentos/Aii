"""Source-bound C3 admission with fake native tokenizer and real ContextOS.

The inference server and tokenizer are deliberately simulated.  These tests
do not establish native latency, model quality, or Android device behavior.
"""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch as mock_patch

from v13.common import Limits
from v13.config import DEFAULTS
from v13.context_os import ContextOS, VOLATILE_HEAD
from v13.prompts import text as prompt
from v13.runners import LlamaRunner
from v13.runtime import Runtime


def pinned(cfg):
    return prompt(cfg, 'system') + ' ' + prompt(cfg, 'conduct') + ' ' + prompt(cfg, 'answer_rules')


def layer(cfg, name, value):
    return '\n' + prompt(cfg, name) + json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def fake_runner(*, context_tokens=2048, chars_per_token=4, role='C3_LANGUAGE'):
    runner = LlamaRunner.__new__(LlamaRunner)
    runner.role = role
    runner.cfg = dict(DEFAULTS, context_tokens=context_tokens, answer_tokens=48)
    runner.views = []
    def request(method, path, data, deadline):
        if path == '/apply-template':
            view = [dict(message) for message in data['messages']]
            runner.views.append(view)
            return {'prompt': '\n'.join(m['role'] + ':' + m['content'] for m in view)}
        if path == '/tokenize':
            return {'tokens': [0] * max(1, len(data['content']) // chars_per_token)}
        raise AssertionError(path)
    runner._json = request
    return runner


class PromptSourceIntegrity(unittest.TestCase):
    def run_prompt(self, runner, messages):
        return runner._prompt(messages, threading.Event(), time.monotonic() + 30, 48)

    def test_current_context_block_is_not_removed_for_soft_budget(self):
        runner = fake_runner()
        current = 'CURRENT exact input'
        body = VOLATILE_HEAD + layer(runner.cfg, 'hypotheses', [
            {'role': 'B1_DETAIL', 'quote': 'DETAIL ' + 'x' * 1400},
            {'role': 'B2_GIST', 'quote': 'GIST ' + 'y' * 1400}])
        body += '\nTool result (computed locally, exact; use this number):' + json.dumps({'result': 120})
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': body}, {'role': 'user', 'content': current}]
        result, _, _ = self.run_prompt(runner, messages)
        for value in ('DETAIL ', 'GIST ', '"result": 120', current):
            self.assertIn(value, result)
        self.assertEqual(runner._prompt_admission['status'], 'PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET')
        self.assertNotIn('OLD_NATIVE_HISTORY', runner._prompt_admission['removed_layers'])
        self.assertEqual(messages[1]['content'], body)

    def test_optional_layer_can_be_removed_without_losing_following_tool(self):
        runner = fake_runner()
        body = (VOLATILE_HEAD + layer(runner.cfg, 'hypotheses', [{'source': 'B1 exact'}]) +
                layer(runner.cfg, 'task_context', {'debug': 'z' * 3000}) +
                '\nTool result (computed locally, exact; use this number):{"result":42}')
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': body}, {'role': 'user', 'content': 'latest'}]
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn('B1 exact', result)
        self.assertIn('{"result":42}', result)
        self.assertIn('latest', result)
        self.assertNotIn('"debug"', result)
        self.assertIn('C3_LAYER_TASK_CONTEXT', runner._prompt_admission['removed_layers'])

    def test_history_is_removed_in_complete_pairs(self):
        runner = fake_runner()
        context = VOLATILE_HEAD + layer(runner.cfg, 'hypotheses', [{'source': 'current evidence'}])
        messages = [{'role': 'system', 'content': pinned(runner.cfg)}]
        for i in range(4):
            messages.extend([{'role': 'user', 'content': 'OLD_Q%d ' % i + 'x' * 800},
                             {'role': 'assistant', 'content': 'OLD_A%d ' % i + 'y' * 800}])
        messages.extend([{'role': 'user', 'content': context}, {'role': 'user', 'content': 'CURRENT'}])
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn('current evidence', result)
        self.assertIn('CURRENT', result)
        self.assertGreater(runner._prompt_admission['removed_layers'].count('OLD_NATIVE_HISTORY'), 0)
        for view in runner.views:
            self.assertNotEqual(view[1]['role'], 'assistant')

    def test_real_append_only_old_context_question_answer_removed_together(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = Runtime(Path(directory))
            try:
                runtime.sleep.cycle.set_policy('enabled', 'off')
                planner = ContextOS(runtime.store, dict(runtime.cfg, context_tokens=4096, answer_tokens=48), None, None)
                planner.set_capability('C3_LANGUAGE', 'consecutive_user', True)
                planner.set_layout('append_only')
                planner.set_mode('ACTIVE', 'EXPLICIT_HUMAN')
                volatile = [('HYPOTHESES', '\n' + prompt(runtime.cfg, 'hypotheses'),
                             [{'role': 'B1_DETAIL', 'quote': 'source-42-' + 'z' * 80}])]
                previous = 'Prior question'
                e1 = runtime.store.event(runtime.session, previous)['event_id']
                one = planner.plan(e1, 'C3_LANGUAGE', pinned(runtime.cfg), volatile, [], previous)
                history = [{'event_id': e1, 'role': 'user', 'text': previous},
                           {'event_id': e1, 'role': 'assistant', 'text': 'Prior answer'}]
                e2 = runtime.store.event(runtime.session, 'CURRENT QUESTION')['event_id']
                two = planner.plan(e2, 'C3_LANGUAGE', pinned(runtime.cfg), volatile, history, 'CURRENT QUESTION')
                self.assertTrue(one['applied'])
                self.assertIn('append_reentry', two['plan']['decisions'])
                runner = fake_runner(context_tokens=560, chars_per_token=2)
                result, _, _ = self.run_prompt(runner, two['messages'])
                self.assertIn('CURRENT QUESTION', result)
                self.assertIn('source-42-', result)
                self.assertNotIn('Prior question', result)
                self.assertNotIn('Prior answer', result)
                self.assertEqual(result.count(VOLATILE_HEAD), 1)
                self.assertIn('OLD_NATIVE_HISTORY', runner._prompt_admission['removed_layers'])
            finally:
                runtime.close()

    def test_unrecognized_middle_message_never_removed(self):
        runner = fake_runner()
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'tool', 'content': 'EXACT TOOL ' + 'z' * 2000},
                    {'role': 'user', 'content': 'CURRENT'}]
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn('EXACT TOOL', result)
        self.assertIn('CURRENT', result)
        self.assertEqual(runner._prompt_admission['removed_layers'], [])

    def test_unrecognized_old_prefix_is_not_detached_from_turn(self):
        runner = fake_runner()
        context = VOLATILE_HEAD + ' protected unknown context ' + 'z' * 1600
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': context},
                    {'role': 'assistant', 'content': 'no matching preceding question'},
                    {'role': 'user', 'content': 'CURRENT'}]
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn(context, result)
        self.assertIn('CURRENT', result)
        self.assertEqual(runner._prompt_admission['removed_layers'], [])

    def test_latest_user_message_looking_like_reference_is_not_edited(self):
        runner = fake_runner()
        current = (VOLATILE_HEAD + layer(runner.cfg, 'task_context',
                    {'exact_user_source': 'q' * 2000}))
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': current}]
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn(current, result)
        self.assertEqual(runner._prompt_admission['removed_layers'], [])

    def test_unknown_message_fields_do_not_make_an_old_pair_disposable(self):
        runner = fake_runner()
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': 'old input ' + 'x' * 1800,
                     'extra': 'unknown semantics'},
                    {'role': 'assistant', 'content': 'old answer'},
                    {'role': 'user', 'content': 'CURRENT'}]
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn('old input', result)
        self.assertIn('old answer', result)
        self.assertEqual(runner._prompt_admission['removed_layers'], [])

    def test_unremovable_context_over_hard_window_is_rejected(self):
        runner = fake_runner(context_tokens=512)
        body = VOLATILE_HEAD + layer(runner.cfg, 'hypotheses', [{'quote': 'KEEP' * 1000}])
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': body}, {'role': 'user', 'content': 'CURRENT'}]
        with self.assertRaises(Limits):
            self.run_prompt(runner, messages)
        self.assertEqual(runner.views[-1], messages)

    def test_body_role_never_drops_unrecognized_message(self):
        runner = fake_runner(role='B1_DETAIL')
        messages = [{'role': 'system', 'content': 'body'},
                    {'role': 'tool', 'content': 'must keep ' + 'z' * 2000},
                    {'role': 'user', 'content': 'CURRENT'}]
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn('must keep', result)
        self.assertEqual(runner._prompt_admission['removed_layers'], [])

    def test_more_than_sixteen_complete_old_turns_can_be_removed(self):
        runner = fake_runner()
        messages = [{'role': 'system', 'content': pinned(runner.cfg)}]
        for i in range(32):
            messages.extend([{'role': 'user', 'content': 'Q%d ' % i + 'x' * 250},
                             {'role': 'assistant', 'content': 'A%d ' % i + 'y' * 250}])
        messages.append({'role': 'user', 'content': 'CURRENT'})
        result, _, _ = self.run_prompt(runner, messages)
        self.assertIn('CURRENT', result)
        self.assertGreater(runner._prompt_admission['removed_layers'].count('OLD_NATIVE_HISTORY'), 16)
        self.assertEqual(runner._prompt_admission['status'], 'ADMITTED')


    def test_unknown_reference_fields_do_not_authorize_removal(self):
        from v13 import native_prompt_admission as admission
        runner = fake_runner()
        body = VOLATILE_HEAD + layer(runner.cfg, 'task_context',
                                    {'source_from_user': 'MUST_KEEP'})
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': body,
                     'extra': 'unknown semantics'},
                    {'role': 'user', 'content': 'CURRENT'}]
        before = json.dumps(messages, ensure_ascii=False)
        self.assertIsNone(admission.reduce_once(messages, 'C3_LANGUAGE', runner.cfg))
        self.assertEqual(json.dumps(messages, ensure_ascii=False), before)

    def test_admission_rechecks_remaining_time_after_tokenization(self):
        runner = fake_runner()
        clock = [0.0]
        def request(method, path, data, deadline):
            clock[0] += 7.6
            if path == '/apply-template':
                return {'prompt': 'x' * 704}
            if path == '/tokenize':
                return {'tokens': [0] * 176}
            raise AssertionError(path)
        runner._json = request
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': 'CURRENT'}]
        with mock_patch('v13.runners.time.monotonic', side_effect=lambda: clock[0]):
            _, count, _ = runner._prompt(messages, threading.Event(), 30.0, 48)
        self.assertEqual(count, 176)
        self.assertEqual(runner._prompt_admission['target_tokens'], 96)
        self.assertEqual(runner._prompt_admission['status'],
                         'PROTECTED_CONTEXT_EXCEEDS_TIME_TARGET')

    def test_deadline_during_tokenization_is_not_reported_as_admitted(self):
        runner = fake_runner()
        clock = [0.0]
        def request(method, path, data, deadline):
            clock[0] += 16.0
            if path == '/apply-template':
                return {'prompt': 'small'}
            if path == '/tokenize':
                return {'tokens': [0]}
            raise AssertionError(path)
        runner._json = request
        messages = [{'role': 'system', 'content': pinned(runner.cfg)},
                    {'role': 'user', 'content': 'CURRENT'}]
        with mock_patch('v13.runners.time.monotonic', side_effect=lambda: clock[0]):
            with self.assertRaises(Limits):
                runner._prompt(messages, threading.Event(), 30.0, 48)


if __name__ == '__main__':
    unittest.main()
