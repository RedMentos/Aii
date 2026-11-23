"""K/M integration through real policy, transactions, Broker and restart; deterministic fake model/taps only."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

from v13 import broker, toolforecast as F, toolstep as T
from v13.agi import hub
from v13.focal import ActionGate
from v13.runtime import Runtime
from v13.transaction import operator_command, settle_turn


RAIN = ('Monthly rainfall in millimetres: Lyon 644, Brno 255, Bremen 636. '
        'Which city had the most rain, and how many millimetres more than the city with the least?')
VALUES = [{'name': 'Lyon', 'number': 644}, {'name': 'Brno', 'number': 255}, {'name': 'Bremen', 'number': 636}]


class Taps:
    def __init__(self):
        self.calls = []

    def tap(self, texts):
        self.calls.append(list(texts))
        return np.stack([np.random.default_rng(int(hashlib.sha256(t.encode()).hexdigest()[:12], 16))
                        .normal(size=1024).astype(np.float32) for t in texts])


class CombinedToolpath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.taps = Taps()
        self.reads = []
        self.open_runtime()

    def open_runtime(self):
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.tool_forecast = F.ToolForecast(self.r.store, self.home, taps=self.taps)
        self.g = hub(self.r)
        def generate(messages, cancel, deadline, max_tokens=None, schema=None, **kwargs):
            self.reads.append({'messages': messages, 'schema': schema})
            yield json.dumps({'values': VALUES})
        self.r.pool.get = lambda role: SimpleNamespace(generate=generate)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def event(self, text):
        return self.r.store.event(self.r.session, text)

    def allow_age_for_fixture(self):
        # Only the Age verdict is a seam. Real schema, enablement, confirmation,
        # ActionGate and transaction execution are never bypassed.
        self.g.tools.age = SimpleNamespace(allowed=lambda right, **kwargs: right == 'simple_tool_choice')

    def test_disabled_list_and_unrelated_text_cost_no_model_or_forecast(self):
        ts = T.ToolStep(self.r)
        self.assertFalse(self.g.tools.report()['tools']['list_arith']['enabled'])
        for text in (RAIN, 'Hello there, which note is most recent?'):
            self.assertIsNone(ts.plan(self.event(text), text))
        self.assertEqual(self.reads, [])
        self.assertEqual(self.taps.calls, [])
        self.assertEqual(self.g.tools.box.load()[0]['calls'], [])
        self.assertEqual(self.r.tool_forecast.report()['mode'], 'OFF')

    def test_list_shadow_age_gate_then_real_execution_keeps_forecast_unmapped(self):
        self.g.tools.enable('list_arith')
        self.r.tool_forecast.set_mode('SHADOW')
        event = self.event(RAIN)
        ts = T.ToolStep(self.r)
        proposal = ts.plan(event, RAIN)
        self.assertEqual(proposal['proposer'], T.LIST_PROPOSER)
        self.assertEqual(proposal['reason'], 'AGE_RIGHT:simple_tool_choice')
        self.assertNotEqual(ActionGate(self.r.store).select(event, route='detail', direct=False,
                             resource_state='NORMAL', tool=proposal)['role'], 'EXTERNAL_TOOL')
        shadow = ts.shadow(event, proposal)
        self.assertEqual(shadow['result'], 389)
        self.assertEqual(self.g.tools.box.load()[0]['calls'], [])
        self.assertEqual(self.taps.calls, [])
        self.allow_age_for_fixture()
        proposal = ts.plan(event, RAIN)
        choice = ActionGate(self.r.store).select(event, route='detail', direct=False,
                                               resource_state='NORMAL', tool=proposal)
        self.assertEqual(choice['role'], 'EXTERNAL_TOOL')
        result = ts.execute(event, proposal)
        self.assertEqual((result['status'], result['result']), ('EXECUTED', 389))
        self.assertEqual(ts.layer(result)['recipe'], 'largest Lyon 644 - smallest Brno 255 = 389')
        self.assertNotIn('Monthly rainfall', broker.correction_text(result))
        output = 'Lyon had more rain.'
        meta = {'model_generated': True, 'output_committed': True}
        mid = self.r.store.message(self.r.session, event['event_id'], 'assistant', output, 'FINAL', meta)
        decision = broker.Broker(self.r).finalize(event, mid, meta, 'FINAL', output, tool_result=result)
        self.assertIn('ANSWER_OMITS_TOOL_RESULT', decision['conflicts'])
        correction = self.r.store.one("SELECT text FROM messages WHERE event_id=? AND role='broker'", (event['event_id'],))
        self.assertIn('list_arith: largest Lyon 644 - smallest Brno 255 = 389', correction['text'])
        self.assertEqual(self.r.store.one('SELECT text FROM messages WHERE id=?', (mid,))['text'], output)
        self.assertEqual(self.r.tool_forecast.report()['counts']['TOOL_WITHOUT_WORLD'], 1)
        self.assertEqual(self.taps.calls, [])  # No measured world is invented for list_arith.
        self.assertIsNone(self.g.tools.box.load()[0]['calls'][-1]['predicted'])
        settle_turn(self.r, event['event_id'], 'FINAL')
        self.assertEqual(self.g.grounding.box.load()[0]['closed'][-1]['actual'], 'EXECUTED:389')
        self.assertEqual(ts.execute(event, proposal)['status'], 'DEDUPLICATED')

    def test_calc_and_pending_note_forecast_survive_interleaved_list_and_restart(self):
        self.allow_age_for_fixture()
        for name in ('calc', 'list_arith', 'sandbox_note'):
            self.g.tools.enable(name)
        self.r.tool_forecast.set_mode('SHADOW')
        ts = T.ToolStep(self.r)
        event = self.event('What is 37 times 2?')
        calc = ts.execute(event, ts.plan(event, 'What is 37 times 2?'))
        self.assertEqual(calc['result'], 74)
        self.assertEqual(self.reads, [])
        settle_turn(self.r, event['event_id'], 'FINAL')
        self.assertEqual(self.r.tool_forecast.report()['stats']['calc_counter:double']['n'], 1)
        sandbox = self.home / 'data/tool_sandbox'
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / 'todo.txt').write_text('Pay the dentist next week.')
        event = self.event('Mark note todo as done')
        pending = ts.propose_call(event, ts.plan(event, 'Mark note todo as done'))
        self.assertEqual((sandbox / 'todo.txt').read_text(), 'Pay the dentist next week.')
        self.assertEqual(self.r.tool_forecast.report()['pending'], 1)
        # Tool-call proposal and measured-world forecast remain separate from an
        # intervening list extraction, including its unmeasured-world no-op.
        other = self.event(RAIN)
        listed = ts.execute(other, ts.plan(other, RAIN))
        self.assertEqual(listed['result'], 389)
        settle_turn(self.r, other['event_id'], 'FINAL')
        self.assertEqual(self.r.tool_forecast.report()['pending'], 1)
        self.r.close()
        self.open_runtime()
        self.assertTrue(self.g.tools.report()['tools']['list_arith']['enabled'])
        self.assertEqual(self.r.tool_forecast.report()['pending'], 1)
        done = json.loads(operator_command(self.r, ['approve', pending['call_id']]))
        self.assertEqual(done['status'], 'EXECUTED')
        self.assertEqual((sandbox / 'todo.txt').read_text(), 'Pay the dentist next week. Done.')
        stats = self.r.tool_forecast.report()['stats']
        self.assertEqual(stats['calc_counter:double']['n'], 1)
        self.assertEqual(stats['note_edit:append_done']['n'], 1)
        self.assertEqual(self.r.tool_forecast.report()['pending'], 0)
        self.assertEqual(self.r.cfg.get('system_stage'), 0)  # The fixture did not promote production Age.

    def test_note_approval_after_final_turn_reaches_grounding(self):
        self.g.tools.enable('sandbox_note')
        sandbox = self.home / 'data/tool_sandbox'
        sandbox.mkdir(parents=True, exist_ok=True)
        (sandbox / 'todo.txt').write_text('Pay the dentist next week.')
        event = self.event('Mark note todo as done')
        ts = T.ToolStep(self.r)
        pending = ts.propose_call(event, ts.plan(event, 'Mark note todo as done'))
        self.r.store.message(self.r.session, event['event_id'], 'assistant', 'Waiting for approval.', 'FINAL', {})
        settle_turn(self.r, event['event_id'], 'FINAL')
        done = json.loads(operator_command(self.r, ['approve', pending['call_id']]))
        self.assertEqual(done['status'], 'EXECUTED')
        closed = self.g.grounding.box.load()[0]['closed']
        self.assertEqual(len(closed), 1)

    def test_text_contract_is_data_only_and_keeps_string_guards(self):
        from v13.agi.tools import ToolSpec
        from v13.transaction import check_args
        content = 'User data: a=3; b=7 | this is text, not an executable argument.'
        self.assertEqual(check_args({'value': 'text'}, {'value': content}), [])
        self.assertEqual(check_args({'value': 'str'}, {'value': content}), ['unsafe_arg:value'])
        self.assertEqual(check_args({'value': 'text'}, {'value': 'x' * 4001}), ['unsafe_arg:value'])
        self.assertEqual(check_args({'value': 'text'}, {'value': 7}), ['type:value'])
        for risk in ('WRITE_LOCAL', 'NETWORK', 'EXTERNAL_EFFECT'):
            with self.assertRaisesRegex(ValueError, 'text args only for READ_LOCAL'):
                ToolSpec('text_target', lambda value: value, risk=risk, schema={'value': 'text'})


if __name__ == '__main__':
    unittest.main()
