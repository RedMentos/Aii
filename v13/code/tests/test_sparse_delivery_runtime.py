"""WP-T9 Runtime/SQLite integration; synthetic sparse bytes and mocked native streams.

These fixtures prove delivery/lineage and fallbacks, not native firing or recall quality.
"""
import copy
import json
from pathlib import Path
import struct
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from v13.common import file_hash
from v13.history import native_history
from v13.inputs import last_context
from v13.lora_trainer import AdapterRegistry
from v13.memory_server import MANIFEST, captured_delivery_binding, shadow_delivery
from v13.memory_trainer import ROLE
from v13.runtime import Runtime
from v13.sparse_memory import DELIVERY_SCHEMA, fact_item_bindings, native_items_path


class SparseDeliveryRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.r.cfg['observer_mode'] = 'off'
        self.r._route = Mock(return_value=('simple', {'source': 'SOFTWARE_TEST_SEAM'}))
        self.r.learner.output_delta = Mock(return_value=None)
        event = self.r.store.event(self.r.session, 'What is the name of my cat?')
        self.r.memory.feedback(event['event_id'], 'fact', 'Mitzi')
        self.memory = self.r.memory.recall('cat', self.r.session)[0]
        self.mid = self.memory['id']
        self.model = self.home / 'c3.gguf'
        self.model.write_bytes(b'synthetic model fixture, not weights')
        binary = self.home / 'bin/llama-server-mem'
        binary.write_bytes(b'synthetic server fixture, not executable')
        (self.home / MANIFEST).write_text(json.dumps({'binary_sha256': file_hash(binary)}))
        native = self.home / 'fixture-memory.bin'
        native.write_bytes(
            b'V13SMEM1' + struct.pack('<6i', 7, 4, 1, 2, 32, 1) + struct.pack('<2f', .01, 1.) +
            struct.pack('<4f', 0, 0, 0, 0) + struct.pack('<4f', 1, 0, 0, 0) + struct.pack('<f', .5) +
            struct.pack('<4f', 1, 1, 1, 1) + struct.pack('<2i', 5, -1))
        native_items_path(native).write_text(json.dumps({
            'schema': DELIVERY_SCHEMA, 'source_pt': None, 'rows': [self.mid], 'forgotten': [],
            'native_sha256': file_hash(native), 'item_bindings': fact_item_bindings([{
                'memory_id': self.mid, 'kind': 'fact', 'prompt': self.memory['key_text'],
                'target': self.memory['value'], 'source_ref': self.memory['source_ref']}])}))
        AdapterRegistry(self.r.store).activate(ROLE, native, file_hash(native), file_hash(self.model), 'software-fixture')
        self.binding = captured_delivery_binding(self.home, 'C3_LANGUAGE', self.model)
        self.assertIsNotNone(self.binding)
        self.messages = []
        self.generated = False
        self.runner = self.runner_fixture(memory=True)
        self.r.pool.get = Mock(return_value=self.runner)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def runner_fixture(self, memory=False, alive=True):
        def stream(messages, *_args, **_kwargs):
            self.messages.append(copy.deepcopy(messages))
            yield 'Mitzi'
            yield ' ist der Name.'
            self.generated = True
        return SimpleNamespace(
            role='C3_LANGUAGE', model=self.model, last_metrics={'software_test_seam': True},
            memory={'software_fixture': True} if memory else None,
            memory_delivery_binding=dict(self.binding) if memory else None,
            pids=Mock(return_value=[12345] if alive else []), generate=stream)

    def turn(self):
        event = self.r.submit('What is the name of my cat?')
        until = time.monotonic() + 5
        while not self.r.idle() and time.monotonic() < until:
            time.sleep(.005)
        self.assertTrue(self.r.idle())
        row = self.r.last_answer()
        self.assertEqual((row['status'], row['text']), ('FINAL', 'Mitzi ist der Name.'))
        meta = json.loads(row['metadata'])
        self.assertTrue(meta['model_generated'])
        self.assertEqual(meta['memory_ids'], [self.mid])
        self.assertIn(self.memory['source_ref'], meta['context_source_refs'])
        self.assertIn('Mitzi', self.messages[-1][0]['content'])
        saved = last_context(self.r.store, self.r.session)
        self.assertEqual(saved['event_id'], event)
        self.assertEqual(saved['messages'], self.messages[-1])
        return event, row, meta

    def test_final_healthy_runner_inventories_without_removing_exact_or_lineage(self):
        def inventory(*args):
            self.assertTrue(self.generated)  # Only the final runner after actual output.
            return shadow_delivery(*args)
        with patch('v13.memory_server.shadow_delivery', side_effect=inventory) as observed:
            event, row, meta = self.turn()
        observed.assert_called_once()
        self.assertEqual(observed.call_args.args[2:5], ('C3_LANGUAGE', self.model, self.binding))
        delivery = meta['sparse_delivery_shadow']
        self.assertEqual(delivery['candidates'], [self.mid])
        self.assertTrue(delivery['exact_retained'])
        self.assertEqual((delivery['mode'], delivery['firing']), ('SHADOW', 'UNMEASURED'))
        self.assertEqual(delivery['provenance'], [self.memory['source_ref']])
        audit = self.r.store.one("SELECT metrics FROM telemetry WHERE kind='sparse_delivery_shadow' AND event_id=?", (event,))
        self.assertIsNotNone(audit)
        metrics = json.loads(audit['metrics'])
        self.assertEqual(metrics['mode'], 'SHADOW')
        self.assertEqual(metrics['candidates'], [self.mid])
        self.assertTrue(metrics['exact_retained'])
        self.assertEqual(metrics['firing'], 'UNMEASURED')
        self.assertEqual(metrics['reason'], 'INVENTORY_ONLY')
        self.assertEqual(metrics['binding']['native_sha256'], self.binding['native_sha256'])
        self.assertNotIn('path', metrics['binding'])
        self.assertNotIn('Mitzi', audit['metrics'])
        self.assertNotIn(self.memory['key_text'], audit['metrics'])
        records, refs = native_history(self.r.store, self.r.session, 'next', 4)
        self.assertEqual([r['event_id'] for r in records], [event, event])
        self.assertIn(self.memory['source_ref'], refs)
        # Forget through the production erasure path; retained chat is not reusable inference evidence.
        session = self.r.session
        self.r.memory.forget(self.mid)
        self.assertEqual(native_history(self.r.store, session, 'next', 4), ([], []))
        self.r.close()
        self.r = Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled', 'off')
        self.assertEqual(native_history(self.r.store, session, 'next', 4), ([], []))
        self.assertEqual(self.r.store.one('SELECT text FROM messages WHERE id=?', (row['id'],))['text'], row['text'])

    def test_dead_final_runner_never_claims_loaded_snapshot(self):
        self.runner.pids.return_value = []
        with patch('v13.memory_server.shadow_delivery', wraps=shadow_delivery) as observed:
            _event, _row, meta = self.turn()
        self.assertIsNone(observed.call_args.args[4])
        delivery = meta['sparse_delivery_shadow']
        self.assertIsNone(delivery['binding'])
        self.assertEqual(delivery['candidates'], [])
        self.assertEqual(delivery['reason'], 'NO_MATCHING_LOADED_BINDING')
        self.assertTrue(delivery['exact_retained'])

    def test_same_causal_replacement_cannot_inventory_obsolete_selected_server(self):
        self.r.cfg.update(c3_decode_mode='same_causal_zero', answer_tokens=64)
        final = self.runner_fixture(memory=False)
        self.r.pool.get_output = Mock(return_value=final)
        with patch('v13.memory_server.shadow_delivery', wraps=shadow_delivery) as observed:
            event, _row, meta = self.turn()
        self.r.pool.get_output.assert_called_once_with('C3_LANGUAGE')
        self.r.learner.output_delta.assert_not_called()
        self.runner.pids.assert_not_called()
        observed.assert_not_called()
        self.assertNotIn('sparse_delivery_shadow', meta)
        self.assertIsNone(self.r.store.one("SELECT id FROM telemetry WHERE kind='sparse_delivery_shadow' AND event_id=?", (event,)))

    def test_normal_replacement_uses_final_memory_runner_binding(self):
        final = self.runner_fixture(memory=True, alive=False)
        self.r.pool.get.side_effect = [self.runner, final]
        with patch('v13.memory_server.shadow_delivery', wraps=shadow_delivery) as observed:
            _event, _row, meta = self.turn()
        self.runner.pids.assert_not_called()
        final.pids.assert_called_once()
        self.assertIsNone(observed.call_args.args[4])
        self.assertEqual(meta['sparse_delivery_shadow']['candidates'], [])

    def test_inventory_exception_cannot_remove_native_output_or_exact_dependencies(self):
        with patch('v13.memory_server.shadow_delivery', side_effect=RuntimeError('software inventory failure')):
            event, _row, meta = self.turn()
        self.assertNotIn('sparse_delivery_shadow', meta)
        self.assertIsNotNone(self.r.store.one("SELECT id FROM telemetry WHERE kind='sparse_delivery_unavailable' AND event_id=?", (event,)))
        records, refs = native_history(self.r.store, self.r.session, 'next', 4)
        self.assertEqual([r['event_id'] for r in records], [event, event])
        self.assertIn(self.memory['source_ref'], refs)


if __name__ == '__main__':
    unittest.main()
