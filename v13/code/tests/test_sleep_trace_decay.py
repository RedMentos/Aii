"""Run62 focused §94.4 synthetic software regressions; no native gate promotion."""
import copy
import unittest

from v13.sleep_trace_decay import DAY, plan_trace_decay, apply_trace_decay


def item(priority=1.0, created=0.0, last=None, expires=100 * DAY, **extra):
    return dict(priority=priority, created=created, last=last, expires=expires,
                retired=None, **extra)


def tick(items, now, per_day=0.98, floor=0.05):
    return apply_trace_decay(plan_trace_decay(items, now, per_day, floor))


class TraceDecayTests(unittest.TestCase):
    def test_same_time_no_double_decay(self):
        i = item()
        self.assertEqual(tick([i], 10 * DAY), (1, 0))
        p = i['priority']
        for _ in range(20):
            self.assertEqual(tick([i], 10 * DAY), (0, 0))
            self.assertEqual(i['priority'], p)

    def test_hourly_and_daily_equivalent(self):
        hourly = item(); daily = item()
        for hour in range(1, 25):
            tick([hourly], hour * DAY / 24)
        tick([daily], DAY)
        self.assertAlmostEqual(hourly['priority'], daily['priority'], places=13)
        self.assertAlmostEqual(daily['priority'], 0.98, places=13)

    def test_replay_last_supersedes_old_watermark(self):
        i = item(created=0, last=3 * DAY, trace_decay_at=DAY)
        tick([i], 4 * DAY)
        self.assertAlmostEqual(i['priority'], 0.98)
        self.assertEqual(i['trace_decay_at'], 4 * DAY)

    def test_clock_rollback_no_rewind_or_decay(self):
        i = item(trace_decay_at=4 * DAY)
        tick([i], 2 * DAY)
        self.assertEqual(i['priority'], 1.0)
        self.assertEqual(i['trace_decay_at'], 4 * DAY)
        tick([i], 5 * DAY)
        self.assertAlmostEqual(i['priority'], 0.98)

    def test_floor_never_increases_priority(self):
        i = item(priority=0.01)
        tick([i], 10 * DAY, floor=0.05)
        self.assertEqual(i['priority'], 0.01)

    def test_floor_stops_further_decay(self):
        i = item(priority=0.1)
        tick([i], 90 * DAY)
        self.assertEqual(i['priority'], 0.05)
        tick([i], 91 * DAY)
        self.assertEqual(i['priority'], 0.05)

    def test_legacy_no_watermark(self):
        i = item(priority=0.8, last=2 * DAY)
        tick([i], 3 * DAY)
        self.assertAlmostEqual(i['priority'], 0.8 * 0.98)
        self.assertEqual(i['trace_decay_at'], 3 * DAY)

    def test_expiry_retired_once(self):
        i = item(expires=DAY)
        self.assertEqual(tick([i], 2 * DAY), (0, 1))
        self.assertEqual(tick([i], 3 * DAY), (0, 0))
        self.assertEqual(i['retired'], 'TTL')

    def test_batch_validation_no_partial_mutation(self):
        good = item(); bad = item(priority=float('nan'))
        before = copy.deepcopy(good)
        with self.assertRaises(ValueError):
            tick([good, bad], DAY)
        self.assertEqual(good, before)

    def test_reject_nonfinite_and_bool_inputs(self):
        for bad in [float('nan'), float('inf'), -float('inf'), True, '2']:
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError): plan_trace_decay([item()], bad, .98, .05)
                with self.assertRaises(ValueError): plan_trace_decay([item()], DAY, bad, .05)
                with self.assertRaises(ValueError): plan_trace_decay([item()], DAY, .98, bad)

    def test_bad_persisted_watermark_refused(self):
        for bad in [float('nan'), float('inf'), True, 'yesterday']:
            with self.subTest(bad=repr(bad)):
                with self.assertRaises(ValueError): tick([item(trace_decay_at=bad)], DAY)

    def test_future_anchor_does_not_decay(self):
        i = item(created=10 * DAY)
        tick([i], DAY)
        self.assertEqual(i['priority'], 1.0)
        self.assertNotIn('trace_decay_at', i)

    def test_no_source_or_authority_mutation(self):
        refs = [{'source_id':'s1','sha256':'a'*64}]
        i = item(source_refs=refs, fact_write_authority=0, max_authority='SHADOW')
        tick([i], DAY)
        self.assertEqual(i['source_refs'], refs)
        self.assertEqual(i['fact_write_authority'], 0)
        self.assertEqual(i['max_authority'], 'SHADOW')


if __name__ == '__main__': unittest.main()
