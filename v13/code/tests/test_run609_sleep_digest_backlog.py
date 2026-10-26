"""Run609 source-only real SQLite/Runtime tests for >64-turn Sleep A backlog."""
import json
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from v13.runtime import Runtime
from v13 import sleep_offline as S
from v13.history import native_history,native_history_since


class SleepBacklog(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.home=Path(self.tmp.name)
        self.r=Runtime(self.home)
        self.r.sleep.cycle.set_policy('enabled','off')
        self.r.sleep.cycle.set_policy('tick_seconds','300')
        self.r._route=Mock(return_value=('simple',{'source':'TEST_ROUTE_SEAM'}))
        def gen(messages,*a,**k):
            yield 'Verified answer for '+messages[-1]['content'][:60]
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={},generate=gen))
        self.r.learner.output_delta=Mock(return_value=None)

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def turn(self,i):
        self.r.submit(f'Unique long-session question number {i:03d}?')
        until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:
            time.sleep(.003)
        self.assertTrue(self.r.idle())
        self.assertIsNotNone(self.r.last_answer())

    def assistant_ids(self):
        return [int(x['id']) for x in self.r.store.rows(
            "SELECT id FROM messages WHERE session_id=? AND role='assistant' ORDER BY id",(self.r.session,))]

    def test_seventy_final_turns_drain_64_then_6_then_zero(self):
        for i in range(70):self.turn(i)
        first=S.digest(self.r.store)
        self.assertEqual(first['turns'],64)
        self.assertEqual(first['backlog_remaining'],6)
        # Even if an earlier deferred set becomes FINAL together with a new
        # window, one cycle returns at most 64 validated pairs; the remainder
        # is retained by assistant ID for the next cycle.
        ids=self.assistant_ids()
        bounded,_,high,deferred=native_history_since(
            self.r.store,self.r.session,ids[63],64,ids[:64])
        self.assertEqual(len(bounded),128)
        self.assertEqual(high,ids[-1])
        self.assertEqual(deferred,ids[64:])
        recovered,_,_,left=native_history_since(
            self.r.store,self.r.session,high,64,deferred)
        self.assertEqual(len(recovered),12)
        self.assertEqual(left,[])
        second=S.digest(self.r.store)
        self.assertEqual(second['turns'],6)
        self.assertEqual(second['backlog_remaining'],0)
        self.assertEqual(S.digest(self.r.store)['turns'],0)
        d=S._load(self.r.store)[0]['sessions'][self.r.session]
        self.assertEqual(d['cursor_version'],2)
        self.assertEqual(d['until'],self.assistant_ids()[-1])
        self.assertEqual([e['msg'] for e in d['entries']],self.assistant_ids())
        self.assertEqual(len({e['event_id'] for e in d['entries']}),70)
        self.assertIn('question number 000',d['entries'][0]['user'])

    def test_interleaved_unfinished_assistant_is_deferred_and_later_recovered(self):
        for i in range(3):self.turn(i)
        ids=self.assistant_ids()
        with self.r.store.tx() as c:
            c.execute("UPDATE messages SET status='STREAMING' WHERE id=?",(ids[1],))
        first=S.digest(self.r.store)
        self.assertEqual(first['turns'],2)
        d=S._load(self.r.store)[0]['sessions'][self.r.session]
        self.assertEqual(d['pending'],[ids[1]])
        self.assertEqual(d['until'],ids[2])
        with self.r.store.tx() as c:
            c.execute("UPDATE messages SET status='FINAL' WHERE id=?",(ids[1],))
        second=S.digest(self.r.store)
        self.assertEqual(second['turns'],1)
        d=S._load(self.r.store)[0]['sessions'][self.r.session]
        self.assertEqual(d['pending'],[])
        self.assertEqual([e['msg'] for e in d['entries']],ids)
        self.assertEqual(S.digest(self.r.store)['turns'],0)

    def test_revoked_source_never_enters_digest_but_cursor_progresses(self):
        for i in range(3):self.turn(i)
        rows=self.r.store.rows("SELECT event_id,id FROM messages WHERE session_id=? AND role='assistant' ORDER BY id",(self.r.session,))
        mid=rows[1]
        event=self.r.store.one("SELECT source_id FROM events WHERE id=?",(mid['event_id'],))
        with self.r.store.tx() as c:
            c.execute("UPDATE sources SET deleted=1 WHERE id=?",(event['source_id'],))
        rep=S.digest(self.r.store)
        # The later model answer also depends on the revoked middle turn's
        # context source; native_history correctly excludes both, not just the
        # directly revoked pair. The first independent turn remains valid.
        self.assertEqual(rep['turns'],1)
        d=S._load(self.r.store)[0]['sessions'][self.r.session]
        self.assertEqual(d['until'],int(rows[-1]['id']))
        self.assertNotIn(int(mid['id']),[e['msg'] for e in d['entries']])
        self.assertNotIn('question number 001',S.view(self.r.store,self.r.session)['text'])
        self.assertEqual(S.digest(self.r.store)['turns'],0)

    def test_legacy_tail_cursor_migration_backfills_without_duplicates(self):
        for i in range(70):self.turn(i)
        self.assertEqual(S.digest(self.r.store)['turns'],64)
        st,v=S._load(self.r.store)
        d=st['sessions'][self.r.session]
        d.pop('cursor_version')
        d['until']=self.assistant_ids()[-1]  # old v1 skipped last six
        self.r.store.set_state(S.KEY,st,expected=v)
        first=S.digest(self.r.store)
        self.assertEqual(first['turns'],0)  # 64 already in entries, but cursor reset
        self.assertEqual(S.digest(self.r.store)['turns'],6)
        d=S._load(self.r.store)[0]['sessions'][self.r.session]
        self.assertEqual(len(d['entries']),70)
        self.assertEqual(len({e['msg'] for e in d['entries']}),70)

    def test_original_latest_n_history_stays_unchanged(self):
        for i in range(4):self.turn(i)
        before,refs=native_history(self.r.store,self.r.session,'',2)
        rows,other,high,pending=native_history_since(self.r.store,self.r.session,0,2)
        after,refs2=native_history(self.r.store,self.r.session,'',2)
        self.assertEqual(before,after)
        self.assertEqual(refs,refs2)
        self.assertEqual(len(rows),4)
        self.assertEqual(len(pending),0)
        self.assertEqual(high,self.assistant_ids()[1])
        self.assertEqual([r['event_id'] for r in rows if r['role']=='assistant'],
                         [r['event_id'] for r in self.r.store.rows(
                             "SELECT * FROM messages WHERE session_id=? AND role='assistant' ORDER BY id LIMIT 2",(self.r.session,))])

    def test_bad_cursor_and_pending_fail_closed(self):
        for i in (True,-1,'0'):
            with self.subTest(cursor=i),self.assertRaises(ValueError):
                native_history_since(self.r.store,self.r.session,i,64)
        for ids in ([0],[2,2],['3'],list(range(1,131))):
            with self.subTest(pending=ids[:4]),self.assertRaises(ValueError):
                native_history_since(self.r.store,self.r.session,0,64,ids)


if __name__=="__main__":
    unittest.main()
