"""Synthetic fanout test; no real model, mic or Android inference."""
import unittest
from dataclasses import replace
from v14.experiments.timed_perception import AudioSource, pcm_digest, timed_audio_packets
from v14.experiments.audio_route import route_timed_audio

class AudioRouteTests(unittest.TestCase):
    def setUp(self):
        self.samples = [1000, -1000] * 401
        self.source = AudioSource('fixture', 'consent-fixture', 5000, 8000, len(self.samples), pcm_digest(self.samples))
        self.packets = timed_audio_packets(self.samples, self.source)
        self.calls = []
    def consume(self, organ):
        def callback(observation):
            self.calls.append((organ, observation))
            return {'organ': organ, 'source': observation.source_id, 'authority': observation.authority}
        return callback
    def run_route(self, packets=None, source=None):
        return route_timed_audio(self.packets if packets is None else packets,
                                 self.source if source is None else source,
                                 b_detail=self.consume('B1'), b_gist=self.consume('B2'),
                                 c_observer=self.consume('C'))
    def test_three_consumers_and_source_provenance(self):
        result = self.run_route()
        self.assertEqual([x[0] for x in self.calls], ['B1','B2','C'])
        self.assertTrue(all(x[1] is result['observation'] for x in self.calls))
        self.assertEqual(result['observation'].source_digest, self.source.pcm_sha256)
        self.assertEqual(result['observation'].authority, 'OBSERVATION_ONLY')
        self.assertEqual(result['observation'].frame_count, 3)
    def test_tamper_prevents_any_consumer(self):
        self.packets[1]['sample_start'] += 1
        with self.assertRaises(ValueError): self.run_route()
        self.assertFalse(self.calls)
    def test_consent_prevents_any_consumer(self):
        with self.assertRaises(PermissionError): self.run_route(source=replace(self.source,consent_id='revoked'))
        self.assertFalse(self.calls)
    def test_provisional_provenance(self):
        source = replace(self.source, provisional=True)
        packets = timed_audio_packets(self.samples, source)
        self.assertTrue(self.run_route(packets,source)['observation'].provisional)
    def test_empty_rejected(self):
        source = AudioSource('empty','consent',0,8000,0,pcm_digest([]))
        with self.assertRaises(ValueError): self.run_route([],source)
        self.assertFalse(self.calls)

if __name__ == '__main__': unittest.main()
