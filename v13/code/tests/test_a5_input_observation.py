"""A5 runtime-consumer regression: metadata must not expose source text or claim native timing."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from v13.cognition import Cognition

class _Store:
    def __init__(self, text):
        self.text=text
        self.packet=None
    def read_source(self, ref):
        return self.text
    def add_packet(self, kind, packet):
        self.packet=packet
        return packet
    def log(self, *args):
        pass

class A5ObservationTest(unittest.TestCase):
    def _run(self, text):
        store=_Store(text)
        runtime=SimpleNamespace(store=store, cfg={'segment_mode':'fixed'},
                                learner=SimpleNamespace(student_percept=lambda _:None),
                                session='synthetic')
        event={'source_ref':{'source_id':'fixture'},'event_id':'fixture-event',
               'brain_generation_id':'fixture-generation'}
        with patch('v13.cognition.packet', return_value={'segments':[{'text':text,'source_ref':event['source_ref']}]}), \
             patch('v13.cognition.EnlightenedSpace') as space:
            Cognition(runtime).percept(event)
            self.assertEqual(space.call_count,1)
        return store.packet
    def test_unicode_source_measurement(self):
        packet=self._run('hi 🌍')
        obs=packet['input_observation']
        self.assertEqual(obs['source_chars'],4)
        self.assertEqual(obs['source_utf8_bytes'],7)
        self.assertEqual(obs['segment_count'],1)
        self.assertEqual(obs['measurement_class'],'SOURCE_TEXT_ONLY')
        self.assertIsNone(obs['native_prefill_ms'])
        self.assertIsNone(obs['native_prompt_tokens'])
        self.assertNotIn('hi 🌍',str(obs))
    def test_empty_source_keeps_original_packet(self):
        packet=self._run('')
        self.assertEqual(packet['segments'][0]['text'],'')
        self.assertEqual(packet['input_observation']['source_chars'],0)
    def test_no_native_success_claim(self):
        obs=self._run('2+2')['input_observation']
        self.assertNotIn('latency_ms',obs)
        self.assertNotIn('native_verified',obs)

if __name__=='__main__':
    unittest.main()
