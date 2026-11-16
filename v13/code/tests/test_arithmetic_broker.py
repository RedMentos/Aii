"""C6/C7 regression for deterministic arithmetic: computed != copied source."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock

from v13.broker import decide, egress_type
from v13.runtime import Runtime


class ArithmeticBroker(unittest.TestCase):
    def test_computed_authority_is_not_source_copy(self):
        self.assertEqual(decide(['LOCAL_EXACT_ARITHMETIC'])['selected'], 'LOCAL_EXACT_ARITHMETIC')
        self.assertEqual(egress_type('LOCAL_EXACT_ARITHMETIC'), 'TEXT_REPORT')
        self.assertEqual(decide(['APPROVED_FIXED_RULE', 'LOCAL_EXACT_ARITHMETIC'])['selected'], 'APPROVED_FIXED_RULE')

    def test_actual_sqlite_turn_broker_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime(Path(tmp))
            try:
                runtime.pool.get = Mock(side_effect=AssertionError('native called'))
                runtime.submit('2+2')
                until = time.monotonic() + 10
                while not runtime.idle() and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue(runtime.idle())
                answer = runtime.last_answer()
                self.assertEqual(answer['text'], '4')
                self.assertEqual(answer['status'], 'FINAL')
                meta = json.loads(answer['metadata'])
                self.assertEqual(meta['output_authority'], 'LOCAL_EXACT_ARITHMETIC')
                row = runtime.store.one("SELECT payload FROM packets WHERE kind='EgressCheck' ORDER BY rowid DESC LIMIT 1")
                self.assertIsNotNone(row)
                payload = json.loads(row['payload'])
                self.assertEqual(payload['action_type'], 'TEXT_REPORT')
                self.assertTrue(payload['ok'], payload)
                runtime.pool.get.assert_not_called()
                self.assertEqual(runtime.store.integrity(True), [])
            finally:
                runtime.close()


if __name__ == '__main__':
    unittest.main()
