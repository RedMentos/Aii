"""Run40 real SQLite read-only lineage tests; no Runtime or model inference."""
import hashlib
import json
import sqlite3
import unittest

from scripts import run40_b2_store_history_readonly as c

CURRENT = 'Project Aquila: decide using the earlier project rules.'
NOTE = ('Project Aquila initial approved note. ' + 'Administrative introduction. '*10 +
        'Binding rules: Budget 134 euros. Deadline 9 days. Local-only requirement: true.')
SHEET = 'Project Aquila supplier sheet: option A 91 euros, option B 105 euros.'


class Store:
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('CREATE TABLE events(id TEXT PRIMARY KEY,session_id TEXT,source_id TEXT,experience_id TEXT,generation_id TEXT,packet TEXT,created REAL);'
                              'CREATE TABLE packets(id TEXT PRIMARY KEY,kind TEXT,event_id TEXT,generation_id TEXT,payload TEXT,created REAL);'
                              'CREATE TABLE sources(id TEXT PRIMARY KEY,hash TEXT,deleted INTEGER);')
        self.sources = {}
        self.queries = []
        self.clock = 0

    def rows(self, sql, args=()):
        self.queries.append(sql)
        assert sql.lstrip().upper().startswith('SELECT'), sql
        return [dict(x) for x in self.db.execute(sql, args).fetchall()]

    def one(self, sql, args=()):
        return next(iter(self.rows(sql, args)), None)

    def event(self, text, *, session='s', generation='g'):
        self.clock += 1
        n = self.clock
        source_id = f'src{n}'
        h = hashlib.sha256(text.encode()).hexdigest()
        ref = {'source_id': source_id, 'sha256': h, 'char_start': 0,
               'char_end': len(text), 'modality': 'text'}
        self.db.execute('INSERT INTO sources VALUES (?,?,0)', (source_id, h))
        self.sources[source_id] = text
        e = {'event_id': f'e{n}', 'source_ref': ref, 'brain_generation_id': generation}
        self.db.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',
                        (e['event_id'], session, source_id, f'x{n}', generation,
                         json.dumps(e), float(n*10)))
        return e

    def offer(self, e, *, role='B2_GIST', model='m', created=None, generation=None):
        p = {'packet_id': f'p{e["event_id"]}', 'event_id': e['event_id'],
             'role': role, 'brain_generation_id': generation or e['brain_generation_id'],
             'model_revision': model, 'offer': {'summary': 'untrusted hypothesis'}}
        self.db.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',
                        (p['packet_id'], 'OfferPacket', e['event_id'], p['brain_generation_id'],
                         json.dumps(p), float(created if created is not None else self.clock*10+1)))
        return p

    def read_source(self, ref):
        row = self.db.execute('SELECT hash,deleted FROM sources WHERE id=?',
                              (ref['source_id'],)).fetchone()
        if not row or row['deleted'] or row['hash'] != ref['sha256']:
            raise ValueError('deleted or wrong hash')
        text = self.sources[ref['source_id']]
        if hashlib.sha256(text.encode()).hexdigest() != row['hash']:
            raise ValueError('tampered')
        if not 0 <= ref['char_start'] <= ref['char_end'] <= len(text):
            raise ValueError('span')
        return text[ref['char_start']:ref['char_end']]


class StoreHistoryTests(unittest.TestCase):
    def setUp(self):
        self.s = Store()

    def test_old_note_outside_recent_four_recovered_read_only(self):
        note = self.s.event(NOTE); self.s.offer(note)
        for _ in range(5):
            e = self.s.event(SHEET); self.s.offer(e)
        cur = self.s.event(CURRENT)
        before = self.s.db.total_changes
        out = c.select_from_store(self.s, cur, 's', 'g', 'm')
        self.assertEqual(self.s.db.total_changes, before)
        self.assertEqual(len(out['items']), 1)
        self.assertEqual(out['items'][0]['source_ref']['source_id'], note['source_ref']['source_id'])
        self.assertIn('Budget 134 euros', out['items'][0]['native_context']['exact_source_excerpt'])
        self.assertFalse(out['canonical_gate_pass'])
        self.assertTrue(all(q.lstrip().upper().startswith('SELECT') for q in self.s.queries))

    def test_future_event_and_late_completed_prior_offer_excluded(self):
        note = self.s.event(NOTE)
        cur = self.s.event(CURRENT)
        self.s.offer(note, created=1000)  # completed after current was accepted
        future = self.s.event(NOTE); self.s.offer(future)
        self.assertEqual(c.collect_history(self.s, cur, 's', 'g', 'm'), [])

    def test_cross_session_generation_and_model_excluded(self):
        a = self.s.event(NOTE, session='other'); self.s.offer(a)
        b = self.s.event(NOTE, generation='old'); self.s.offer(b)
        d = self.s.event(NOTE); self.s.offer(d, model='old')
        cur = self.s.event(CURRENT)
        self.assertEqual(c.collect_history(self.s, cur, 's', 'g', 'm'), [])

    def test_tombstone_and_corrupt_packet_excluded(self):
        a = self.s.event(NOTE); self.s.offer(a)
        b = self.s.event(NOTE); self.s.offer(b)
        self.s.db.execute('UPDATE sources SET deleted=1 WHERE id=?',(a['source_ref']['source_id'],))
        self.s.db.execute('UPDATE packets SET payload=? WHERE event_id=?', ('{bad', b['event_id']))
        cur = self.s.event(CURRENT)
        self.assertEqual(c.collect_history(self.s, cur, 's', 'g', 'm'), [])

    def test_current_source_mismatch_refused(self):
        self.s.event(NOTE)
        cur = self.s.event(CURRENT)
        wrong = dict(cur, source_ref={'source_id':'other'})
        with self.assertRaisesRegex(ValueError,'RUN40_INPUT_OR_BOUNDS'):
            c.collect_history(self.s, wrong, 's', 'g', 'm')
        wrong = dict(cur, source_ref=dict(cur['source_ref'], sha256='0'*64))
        with self.assertRaisesRegex(ValueError,'RUN40_CURRENT_EVENT_SOURCE'):
            c.collect_history(self.s, wrong, 's', 'g', 'm')

    def test_current_generation_and_session_refused(self):
        cur = self.s.event(CURRENT)
        with self.assertRaisesRegex(ValueError,'RUN40_CURRENT_EVENT_SCOPE'):
            c.collect_history(self.s, cur, 'other', 'g', 'm')
        with self.assertRaisesRegex(ValueError,'RUN40_CURRENT_EVENT_SCOPE'):
            c.collect_history(self.s, cur, 's', 'other', 'm')

    def test_duplicate_event_offer_is_not_used_twice(self):
        a = self.s.event(NOTE); self.s.offer(a)
        # One offer per event in this fixture; additional B2 packet for same event.
        p = {'packet_id':'p2','event_id':a['event_id'],'role':'B2_GIST',
             'brain_generation_id':'g','model_revision':'m','offer':{'summary':'x'}}
        self.s.db.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',
                          ('p2','OfferPacket',a['event_id'],'g',json.dumps(p),10.5))
        cur = self.s.event(CURRENT)
        self.assertEqual(len(c.collect_history(self.s,cur,'s','g','m')),1)

    def test_bool_limit_and_unbounded_input_refused(self):
        cur = self.s.event(CURRENT)
        with self.assertRaisesRegex(ValueError,'RUN40_INPUT_OR_BOUNDS'):
            c.collect_history(self.s,cur,'s','g','m',limit=True)
        with self.assertRaisesRegex(ValueError,'RUN40_INPUT_OR_BOUNDS'):
            c.select_from_store(self.s,cur,'s','g','m',scan_limit=100)


if __name__ == '__main__': unittest.main()
