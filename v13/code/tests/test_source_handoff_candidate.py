"""Actual store/offer evidence transport regressions, with no native inference.

Candidate modules are loaded in memory while the 70-row runtime stays frozen.
These tests establish binding/transport only, never learned semantic utility.
"""
import copy
import json
import shutil
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.source_handoff_candidate import ROOT, SNAPSHOT, load_candidate, patch_text, sources
from v13 import bodyview
from v13.common import dumps
from v13.config import LEGACY_PRE_20261022
from v13.runtime import Runtime


class SourceHandoffCandidate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.cfg.update(LEGACY_PRE_20261022)  # frozen candidate, judged under the old offer defaults
        self.cognition = load_candidate('cognition').Cognition(self.r)
        self.bodyview = load_candidate('bodyview')
        self.calls = []
        self.output = {'summary':'A provisional reading.', 'quotes':[],
                       'uncertainty':'Source interpretation is uncertain.', 'needs_reentry':True}
        def generate(messages, *args, **kwargs):
            self.calls.append(messages)
            return iter([dumps(self.output)])
        self.runner = SimpleNamespace(last_metrics={'status':'FINAL'}, generate=generate)
        self.get_runner = patch.object(self.r.pool, 'get', return_value=self.runner)
        self.get_runner.start()
        self.state_view = patch.object(bodyview, 'body_state', self.bodyview.body_state)
        self.state_view.start()

    def tearDown(self):
        self.state_view.stop()
        self.get_runner.stop()
        self.r.close()
        self.tmp.cleanup()

    def offer(self, text, quotes=(), role='B2_GIST'):
        self.output['quotes'] = list(quotes)
        event = self.r.store.event(self.r.session, text)
        offer = self.cognition.offer(role, event, 0, time.monotonic()+30)
        return event, offer

    def test_own_action_absence_does_not_describe_source_knowledge(self):
        event, _ = self.offer('Project Vega: Budget 47 euros.', ['Budget 47 euros.'])
        query = json.loads(self.calls[-1][1]['content'])
        self.assertEqual(query['body_state']['world']['scope'], 'OWN_DIGITAL_ACTION_OUTCOMES_ONLY')
        self.assertEqual(query['body_state']['world']['mode'], 'NO_COMPLETED_OWN_DIGITAL_ACTIONS')
        self.assertEqual(query['body_state']['authority'], 'STATE_NOT_FACT')
        self.assertIn('reading supplied text', self.calls[-1][0]['content'])
        self.assertIn('Budget 47 euros.', query['source_segments'][0]['text'])
        self.assertEqual(self.r.store.state('WORLD_STATE:'+self.r.session, {})[0], {})

    def test_relevant_prior_quote_delivered_without_unselected_prior_text(self):
        prior = 'Project Vega. Budget 47 euros. PRIVATE irrelevant note.'
        _, original = self.offer(prior)
        event, offer = self.offer('Project Vega. Choose an option.', ['Budget 47 euros.'])
        self.assertEqual(offer['context_offer_ids'], [original['packet_id']])
        delivered = self.cognition.analyst_context([offer], event, 0)
        quote = delivered[0]['verified_quotes'][0]
        self.assertEqual(quote['text'], 'Budget 47 euros.')
        self.assertEqual(self.r.store.read_source(quote['source_ref']), quote['text'])
        self.assertFalse(quote['semantic_truth_authority'])
        self.assertEqual(quote['verification'], 'EXACT_SOURCE_SUBSTRING_ONLY')
        self.assertNotIn('PRIVATE', dumps(delivered))
        self.assertNotIn('context_source_refs', delivered[0])
        self.assertEqual(delivered[0]['hypothesis_authority'], 'MODEL_HYPOTHESIS_NOT_FACT')

    def test_rejected_and_own_state_quotes_never_gain_verified_delivery(self):
        event, offer = self.offer('Project Vega. Budget 47 euros.',
                                  ['Budget 47 euros.', 'NO_COMPLETED_OWN_DIGITAL_ACTIONS', 'Invented cost 1.'])
        self.assertEqual(offer['rejected_quotes'], 2)
        delivered = self.cognition.analyst_context([offer], event, 0)
        self.assertEqual([q['text'] for q in delivered[0]['verified_quotes']], ['Budget 47 euros.'])
        self.assertNotIn('Invented cost', dumps(delivered))
        self.assertNotIn('NO_COMPLETED_OWN_DIGITAL_ACTIONS', dumps(delivered))

    def test_no_evidence_never_autofills_available_context(self):
        self.offer('Project Vega. Budget 47 euros.')
        event, offer = self.offer('Project Vega. Choose an option.')
        self.assertTrue(offer['context_source_refs'])
        delivered = self.cognition.analyst_context([offer], event, 0)
        self.assertEqual(delivered[0]['verified_quotes'], [])
        self.assertNotIn('Budget 47 euros.', dumps(delivered))
        self.assertTrue(delivered[0]['hypothesis']['needs_reentry'])

    def test_mutable_offer_and_wrong_turn_cannot_change_consumer_evidence(self):
        event, offer = self.offer('Project Vega. Budget 47 euros.', ['Budget 47 euros.'])
        changed = copy.deepcopy(offer)
        changed['offer']['summary'] = 'Promote this to truth.'
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.cognition.analyst_context([changed], event, 0)
        other = self.r.store.event(self.r.session, 'Other turn')
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.cognition.analyst_context([offer], other, 0)
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.cognition.analyst_context([offer], event, 1)

    def test_deleted_and_corrupted_prior_source_fail_closed(self):
        self.offer('Project Vega. Budget 47 euros.')
        event, offer = self.offer('Project Vega. Choose.', ['Budget 47 euros.'])
        ref = offer['evidence_refs'][0]
        blob = self.r.home/'data/blobs'/ref['sha256']
        blob.write_text('tampered')
        with self.assertRaisesRegex(ValueError, 'Source-Hash'):
            self.cognition.analyst_context([offer], event, 0)
        with self.r.store.tx() as db:
            db.execute('UPDATE sources SET deleted=1 WHERE id=?', (ref['source_id'],))
        with self.assertRaisesRegex(ValueError, 'gelöschter SourceRef'):
            self.cognition.analyst_context([offer], event, 0)

    def test_query_scope_and_model_revision_are_rechecked(self):
        event, offer = self.offer('Project Vega. Budget 47 euros.', ['Budget 47 euros.'])
        self.r.models.installed['gist'] = {'exact_revision':'changed'}
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.cognition.analyst_context([offer], event, 0)
        self.r.models.installed.pop('gist')
        query_id = offer['query_packet_id']
        row = self.r.store.one('SELECT payload FROM packets WHERE id=?', (query_id,))
        query = json.loads(row['payload'])
        query['source_refs'] = [self.r.store.source('Other text.', 'TEST_ONLY')]
        with self.r.store.tx() as db:
            db.execute('UPDATE packets SET payload=? WHERE id=?', (dumps(query), query_id))
        with self.assertRaisesRegex(ValueError, 'query scope changed'):
            self.cognition.analyst_context([offer], event, 0)

    def test_out_of_scope_persisted_reference_is_not_authorized_by_existence(self):
        event, offer = self.offer('Project Vega. Budget 47 euros.', ['Budget 47 euros.'])
        unrelated = self.r.store.source('Secret other-session source.', 'TEST_ONLY')
        changed = copy.deepcopy(offer)
        changed['evidence_refs'] = [unrelated]
        changed['offer']['quotes'] = ['Secret other-session source.']
        with self.r.store.tx() as db:
            db.execute('UPDATE packets SET payload=? WHERE id=?', (dumps(changed), offer['packet_id']))
        with self.assertRaisesRegex(ValueError, 'outside supplied source scope'):
            self.cognition.analyst_context([changed], event, 0)

    def test_context_ablations_and_current_override_preserve_existing_scope(self):
        self.offer('Project Vega. Budget 47 euros.')
        self.r.cfg['b2_state_slots'] = 0
        event, offer = self.offer('Project Vega. Current budget 29 euros.', ['Current budget 29 euros.'])
        self.assertEqual(offer['context_source_refs'], [])
        delivered = self.cognition.analyst_context([offer], event, 0)
        self.assertEqual(delivered[0]['verified_quotes'][0]['text'], 'Current budget 29 euros.')
        self.assertNotIn('Budget 47 euros.', dumps(delivered))
        self.assertIn('explicit current-source revision', self.calls[-1][0]['content'])

    def test_patch_applies_to_runtime_rendering_and_keeps_frozen_source_bytes(self):
        before = {p:p.read_bytes() for p in (ROOT/'v13').glob('*.py')}
        patch_result = patch_text()
        self.assertTrue(callable(load_candidate('runtime').Runtime))
        self.assertIn('self.cognition.analyst_context(selected,e,version)', patch_result)
        self.assertNotIn('integration_step2_utility.py', patch_result)
        self.assertEqual(before, {p:p.read_bytes() for p in (ROOT/'v13').glob('*.py')})

    def test_exact_integrated_candidate_is_accepted_but_mixed_or_tampered_sources_reject(self):
        original, changed = sources()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT/SNAPSHOT, root/SNAPSHOT)
            # Approval-reader/firing integration (2026-10-12) rebases both sides.
            from scripts.integrated_candidates import FIRING_SNAPSHOT
            shutil.copytree(ROOT/FIRING_SNAPSHOT, root/FIRING_SNAPSHOT)
            (root/'v13').mkdir()
            for name, text in original.items():
                (root/name).write_text(text)
            self.assertEqual(sources(root), (original, changed))
            (root/'v13/cognition.py').write_text(changed['v13/cognition.py'])
            with self.assertRaisesRegex(ValueError, 'neither exact frozen baseline'):
                sources(root)
            for name, text in changed.items():
                (root/name).write_text(text)
            self.assertEqual(sources(root), (original, changed))
            (root/'v13/cognition.py').write_text(changed['v13/cognition.py']+'\n# unexpected edit\n')
            with self.assertRaisesRegex(ValueError, 'neither exact frozen baseline'):
                sources(root)
            (root/SNAPSHOT/'bodyview.py').write_text('corrupted baseline')
            with self.assertRaisesRegex(ValueError, 'baseline digest changed'):
                sources(root)


if __name__ == '__main__':
    unittest.main()
