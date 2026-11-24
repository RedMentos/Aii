"""Real Store/operator policy authority tests; no inference or quality claim."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from v13.common import atomic_write, dumps, file_hash, now, uid
from v13.config import initialize
from v13.operator import Operator
from v13.output_policy import InvalidRule, create, match, preview, validate_rules
from v13.store import Store, telemetry_metrics


class FixedOutputPolicy(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.cfg = initialize(self.home)
        self.s = Store(self.home)
        self.operator = Operator(SimpleNamespace(
            store=self.s, cfg=self.cfg, revisions=lambda: {}, require_idle=lambda: None))

    def tearDown(self):
        self.s.close()
        self.tmp.cleanup()

    def request(self, after, **extra):
        payload = {'base_rule': self.s.generation()['rule_version'],
                   'before': self.s.rules(), 'after': after,
                   'fixed_preview': preview(self.s, after)}
        payload.update(extra)
        return self.s.request('RULES', payload)

    def approve(self, after):
        request = self.request(after)
        self.s.approve_rule(request, self.cfg, {})
        return request

    def test_operator_diff_is_reviewable_and_never_implicitly_activates(self):
        response = self.operator.run(':rules fixed "Welche Regel?" "Genau diese. 🍎"')
        rid = response.split(';')[0]
        self.assertEqual(self.s.rules(), [])
        self.assertIsNone(match(self.s, 'Welche Regel?'))
        payload = json.loads(self.s.one('SELECT payload FROM requests WHERE id=?', (rid,))['payload'])
        self.assertEqual(payload['fixed_preview'][0]['query'], 'Welche Regel?')
        self.assertEqual(payload['fixed_preview'][0]['answer'], 'Genau diese. 🍎')
        self.operator.run(':approve ' + rid)
        chosen = match(self.s, 'Welche Regel?')
        self.assertEqual(chosen['answer'], 'Genau diese. 🍎')
        self.assertFalse(chosen['model_generated'])
        self.assertEqual(chosen['output_authority'], 'APPROVED_FIXED_RULE')
        with self.assertRaises(ValueError):
            self.operator.run(':approve ' + rid)
        self.assertEqual(self.s.integrity(True), [])

    def test_restart_and_exact_matching_preserve_utf8_without_normalization(self):
        text = 'Grüße café 👨‍👩‍👧‍👦'
        answer = 'نعم\nGenau\t🍎'
        entry = create(self.s, text, answer)
        self.approve(['kurz antworten', entry])
        rule_version = self.s.generation()['rule_version']
        for other in (text.lower(), text + ' ', text.replace('é', 'e\u0301'), 'Grüße'):
            self.assertIsNone(match(self.s, other))
        self.s.close()
        self.s = Store(self.home)
        chosen = match(self.s, text)
        self.assertEqual(chosen['answer'].encode(), answer.encode())
        self.assertEqual(chosen['rule_version'], rule_version)
        self.assertEqual(self.s.rules()[0], 'kurz antworten')

    def test_new_diff_supersedes_removed_rule_only_after_approval(self):
        old = create(self.s, 'Frage', 'Alt')
        self.approve([old])
        new = create(self.s, 'Frage', 'Neu')
        rid = self.request([new])
        self.assertEqual(match(self.s, 'Frage')['answer'], 'Alt')
        self.s.approve_rule(rid, self.cfg, {})
        self.assertEqual(match(self.s, 'Frage')['answer'], 'Neu')
        self.approve([])
        self.assertIsNone(match(self.s, 'Frage'))

    def test_stale_rule_request_cannot_activate_and_transaction_keeps_pending(self):
        pending = self.request([create(self.s, 'A', 'B')])
        self.approve(['kurz'])
        before = self.s.generation_id
        with self.assertRaisesRegex(ValueError, 'veraltet'):
            self.s.approve_rule(pending, self.cfg, {})
        self.assertEqual(self.s.generation_id, before)
        self.assertEqual(self.s.one('SELECT status FROM requests WHERE id=?', (pending,))['status'], 'PENDING')
        self.assertEqual(self.s.rules(), ['kurz'])

    def test_source_tamper_before_approval_rejects_without_generation_change(self):
        entry = create(self.s, 'Frage', 'Antwort')
        pending = self.request([entry])
        before = self.s.generation_id
        atomic_write(self.home / 'data/blobs' / entry['answer_ref']['sha256'], 'Manipuliert')
        with self.assertRaises(InvalidRule):
            self.s.approve_rule(pending, self.cfg, {})
        self.assertEqual(self.s.generation_id, before)
        self.assertEqual(self.s.rules(), [])

    def test_tampered_active_rule_fails_closed_even_for_unrelated_input(self):
        entry = create(self.s, 'Frage', 'Antwort')
        self.approve([entry])
        atomic_write(self.home / 'data/blobs' / entry['answer_ref']['sha256'], 'Manipuliert')
        for text in ('Frage', 'unabhängige Frage'):
            with self.assertRaises(InvalidRule):
                match(self.s, text)
        self.assertTrue(any('Output-Regel' in e for e in self.s.integrity(True)))
        # Explicit operator removal remains possible, including bad sources.
        rid = self.operator.run(':rules remove 0').split(';')[0]
        self.s.approve_rule(rid, self.cfg, {})
        self.assertIsNone(match(self.s, 'Frage'))

    def test_revoked_source_rechecked_on_every_match(self):
        entry = create(self.s, 'Frage', 'Antwort')
        self.approve([entry])
        self.assertEqual(match(self.s, 'Frage')['answer'], 'Antwort')
        with self.s.tx() as c:
            c.execute('UPDATE sources SET deleted=1 WHERE id=?', (entry['query_ref']['source_id'],))
        with self.assertRaises(InvalidRule):
            match(self.s, 'Frage')

    def test_multiple_corrupt_rules_are_explicitly_removed_in_one_reviewed_diff(self):
        first=create(self.s,'Erste Frage','Erste Antwort')
        second=create(self.s,'Zweite Frage','Zweite Antwort')
        third=create(self.s,'Dritte Frage','Dritte Antwort')
        self.approve(['kurz',first,second,third])
        for entry in (first,second):
            atomic_write(self.home/'data/blobs'/entry['answer_ref']['sha256'],'beschädigt')
        with self.assertRaises(InvalidRule):match(self.s,'Dritte Frage')
        # One removal leaves an invalid active policy; no partial diff activates.
        before=self.s.generation_id
        with self.assertRaises(InvalidRule):self.operator.run(':rules remove 1')
        for command in (':rules remove 1 1',':rules remove -1 2',':rules remove 1 99'):
            with self.subTest(command=command),self.assertRaises(ValueError):self.operator.run(command)
        self.assertEqual(self.s.generation_id,before)
        pending=self.operator.run(':rules remove 2 1').split(';')[0]
        payload=json.loads(self.s.one('SELECT payload FROM requests WHERE id=?',(pending,))['payload'])
        self.assertEqual(payload['before'],['kurz',first,second,third])
        self.assertEqual(payload['after'],['kurz',third])
        self.assertEqual(payload['fixed_preview'][0]['answer'],'Dritte Antwort')
        self.assertEqual(self.s.generation_id,before)
        with self.assertRaises(InvalidRule):match(self.s,'Dritte Frage')
        self.s.approve_rule(pending,self.cfg,{})
        self.assertIsNone(match(self.s,'Erste Frage'))
        self.assertIsNone(match(self.s,'Zweite Frage'))
        self.assertEqual(match(self.s,'Dritte Frage')['answer'],'Dritte Antwort')
        self.assertEqual(self.s.rules()[0],'kurz')

    def test_duplicate_conflict_and_duplicate_id_are_rejected(self):
        first = create(self.s, 'Frage', 'Antwort')
        for second in (create(self.s, 'Frage', 'Antwort'),
                       create(self.s, 'Frage', 'Andere Antwort'),
                       create(self.s, 'Andere Frage', 'Antwort') | {'rule_id': first['rule_id']}):
            with self.assertRaises(InvalidRule):
                validate_rules(self.s, [first, second])
        # Approval rechecks a forged diff even if the operator preview was bypassed.
        rid = self.s.request('RULES', {'base_rule': self.s.generation()['rule_version'],
                                     'after': [first, first]})
        with self.assertRaises(InvalidRule):
            self.s.approve_rule(rid, self.cfg, {})

    def test_wrong_authority_unknown_schema_and_partial_source_are_rejected(self):
        entry = create(self.s, 'Frage', 'Antwort')
        invalid = [entry | {'model_authority': True},
                   entry | {'owner': 'MODEL_OUTPUT'},
                   entry | {'matcher': 'FUZZY'},
                   entry | {'unexpected': True},
                   entry | {'query_ref': entry['query_ref'] | {'char_end': 2}},
                   entry | {'query_ref': entry['query_ref'] | {'char_start': False}},
                   entry | {'answer_ref': self.s.source('Antwort', 'USER')}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(InvalidRule):
                validate_rules(self.s, [value])
        with self.assertRaises(ValueError):
            self.operator.run(':rules fixed "Frage" "Antwort"', origin='MODEL_OUTPUT')

    def test_utf8_bounds_control_safety_and_fixed_rule_count(self):
        for query, answer in [(' ', 'x'), ('x', '\u200d'),
                              ('x\x1b[2J', 'x'), ('x', '\u202eevil'),
                              ('x', '\ud800'), ('é' * 2049, 'x'),
                              ('x', 'é' * 8193)]:
            with self.subTest(query=repr(query[:10]), answer=repr(answer[:10])), self.assertRaises(InvalidRule):
                create(self.s, query, answer)
        validate_rules(self.s, [create(self.s, 'x' * 4096, 'y' * 16384)])
        rows = [create(self.s, 'Frage ' + str(i), 'Antwort') for i in range(33)]
        self.assertEqual(len(validate_rules(self.s, rows[:32])), 32)
        with self.assertRaises(InvalidRule):
            validate_rules(self.s, rows)

    def test_missing_or_changed_preview_and_before_diff_are_rejected(self):
        entry = create(self.s, 'Frage', 'Antwort')
        for extra in ({'fixed_preview': []},
                      {'fixed_preview': [{'rule_id': entry['rule_id'], 'query': 'Frage', 'answer': 'Andere'}]},
                      {'before': ['vorgetäuscht']}):
            rid = self.request([entry], **extra)
            before = self.s.generation_id
            with self.assertRaises(InvalidRule):
                self.s.approve_rule(rid, self.cfg, {})
            self.assertEqual(self.s.generation_id, before)

    def test_model_rollback_preserves_latest_rule_generation(self):
        update = uid('upd')
        rel = 'checkpoints/head-' + update + '.npz'
        atomic_write(self.home / rel, b'real-stored-artifact')
        with self.s.tx() as c:
            c.execute('INSERT INTO updates VALUES (?,?,?,?,?,?,?)',
                      (update, self.s.generation_id, 'PENDING_APPROVAL', rel,
                       file_hash(self.home / rel), dumps({'commit_eligible': True}), now()))
        self.s.switch_generation(update, self.cfg, {})
        self.approve([create(self.s, 'Frage', 'Antwort')])
        rule = self.s.generation()['rule_version']
        self.s.rollback(update)
        self.assertEqual(self.s.generation()['rule_version'], rule)
        self.assertEqual(match(self.s, 'Frage')['answer'], 'Antwort')

    def test_policy_telemetry_keeps_ids_and_counts_without_answer_text(self):
        rule_id = uid('fixed')
        raw = {'output_policy': {'rule_id': rule_id, 'rule_version': uid('rule'),
                                 'kind': 'FIXED_EXACT', 'answer': 'private answer',
                                 'query': 'private query'},
               'output_authority': 'APPROVED_FIXED_RULE',
               'exact_policy_matched': True, 'output_removed_characters': 2}
        result = telemetry_metrics(raw)
        self.assertEqual(result['output_policy']['rule_id'], rule_id)
        self.assertEqual(result['output_authority'], 'APPROVED_FIXED_RULE')
        self.assertNotIn('private', dumps(result))
        self.assertEqual(result['output_removed_characters'], 2)


if __name__ == '__main__':
    unittest.main()
