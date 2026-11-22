"""WP-U3 F2: a late body offer during C3 output (fixtures, no models)."""
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock
from unittest.mock import Mock
from v13 import latewatch as lw
from v13.operator import Operator
from v13.runtime import Runtime

OFFER={'role':'B1_DETAIL','packet_id':'pkt_late','offer':{'summary':'46 + 62 = 108','needs_reentry':False,'quotes':[]},'evidence_refs':[]}

class Pure(unittest.TestCase):
    def test_disagreement(self):
        src='What is 46 plus 62?'
        self.assertEqual(lw.disagreement(OFFER,'The answer is 100, because I added',src),'RESULT_CONFLICT')
        self.assertIsNone(lw.disagreement(OFFER,'The answer is 108, because I added',src))
        self.assertIsNone(lw.disagreement(OFFER,'It is 100',src))  # too early to cut
        self.assertIsNone(lw.disagreement(OFFER,'You asked about 46 and 62, let me think about it',src))  # no own result yet
        re_={'offer':{'summary':'unclear','needs_reentry':True,'quotes':['46 plus 62']}}
        self.assertEqual(lw.disagreement(re_,'x'*lw.REENTRY_CHARS,src),'BODY_REENTRY')
        self.assertIsNone(lw.disagreement(re_,'x'*lw.MIN_CHARS,src))
    def test_number_parsing(self):
        # thread L 2026-10-12, preregistered candidate PASS (bench-results/latewatch-numbers-20261012)
        self.assertEqual(lw.nums('2,5'),{'2.5'});self.assertEqual(lw.nums('is 1,290, because'),{'1290'})
        self.assertEqual(lw.nums('12,345,678 and 3.5'),{'12345678','3.5'})
        self.assertEqual(lw.complete('The result is 5026'),'The result is ');self.assertEqual(lw.complete('is 1,2'),'is ')
        src='What is 1,234 plus 56?';off={'offer':{'summary':'1234 + 56 = 1290','needs_reentry':False,'quotes':[]}}
        self.assertIsNone(lw.disagreement(off,'The result is 1,290, because I added them',src))  # comma is not a decimal point
        self.assertEqual(lw.disagreement(off,'The result is 1,300, because I added them',src),'RESULT_CONFLICT')
        self.assertIsNone(lw.disagreement(OFFER,'The answer is 10',  'What is 46 plus 62?'))  # number still streaming
        self.assertIsNone(lw.disagreement(OFFER,'Well, the answer to it is 10','What is 46 plus 62?'))
    def test_residency_never_evicts_c3(self):
        def r(experts,resident,budget=1800,guard='NORMAL',decode='server',enabled=True):
            box=SimpleNamespace(load=lambda:({'experts':experts,'resident':resident,'budget_mb':budget},0))
            return SimpleNamespace(cfg={'c3_decode_mode':decode},guard=SimpleNamespace(state=guard),pool=SimpleNamespace(fabric=SimpleNamespace(enabled=enabled,residency=SimpleNamespace(box=box))))
        ex={'C3_LANGUAGE':{'size_mb':700,'pinned':True},'B1_DETAIL':{'size_mb':900,'pinned':False}}
        self.assertIsNone(lw.residency(r(ex,['C3_LANGUAGE']),'B1_DETAIL'))
        self.assertEqual(lw.residency(r(ex,['C3_LANGUAGE'],budget=1500),'B1_DETAIL'),'NO_RESIDENCY')
        self.assertEqual(lw.residency(r(ex,['C3_LANGUAGE'],guard='PRESSURE'),'B1_DETAIL'),'NO_RESIDENCY')  # budget shrinks under pressure
        self.assertEqual(lw.residency(r(ex,['C3_LANGUAGE'],enabled=False),'B1_DETAIL'),'NO_RESIDENCY')
        self.assertEqual(lw.residency(r(ex,['C3_LANGUAGE'],decode='same_causal'),'B1_DETAIL'),'C3_EXCLUSIVE_DECODE')

class Turn(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name))
        Operator(self.r).run(':observers off');self.r.cfg['observer_mode']='background'  # no pre-answer observers, late path allowed
        self.r.learner.output_delta=Mock(return_value=None);self.calls=[];self.post=[]
        def offer(role,e,version,deadline,peer=None,**kw):
            if threading.current_thread().name!='latewatch':self.post.append(role);raise ValueError('only the late body runs in this fixture')
            self.calls.append(role);return dict(OFFER,role=role)
        self.r.cognition.offer=offer;self.done=threading.Event()
        def generate(messages,cancel,deadline,*a,**k):
            if messages[-1]['content'].startswith('(internal check'):yield 'Correction: it is 108.';return
            yield 'The answer is 100, because I added the numbers '
            until=time.monotonic()+3
            while not self.calls and time.monotonic()<until:time.sleep(.01)
            time.sleep(.05);yield 'and that is all. '
            yield 'Done.'
        self.r.pool.get=Mock(return_value=SimpleNamespace(role='C3_LANGUAGE',last_metrics={'test_seam':True},generate=generate))
        self.p=mock.patch.object(lw,'residency',return_value=None);self.p.start()
    def tearDown(self):self.p.stop();self.r.close();self.tmp.cleanup()
    def turn(self,text='What is 46 plus 62?'):
        self.r.submit(text);until=time.monotonic()+10
        while not self.r.idle() and time.monotonic()<until:time.sleep(.005)
        row=self.r.last_answer();return json.loads(row['metadata']),row
    def test_shadow_records_without_touching_the_answer(self):
        meta,row=self.turn()
        self.assertEqual(meta['late_watch']['status'],'WOULD_INTERRUPT');self.assertEqual(meta['late_watch']['reason'],'RESULT_CONFLICT')
        self.assertIn('Done.',row['text']);self.assertNotIn('108',row['text'])
        self.assertEqual(self.calls,['B1_DETAIL']);self.assertNotIn('B1_DETAIL',self.post)  # the post-commit pass skipped the body that already ran
        rep=json.loads(Operator(self.r).run(':latewatch'));self.assertEqual(rep['counts'],{'WOULD_INTERRUPT':1})
    def test_active_cuts_and_revises(self):
        Operator(self.r).run(':latewatch active');meta,row=self.turn()
        lwm=meta['late_watch'];self.assertEqual(lwm['status'],'INTERRUPTED')
        self.assertNotIn('Done.',row['text']);self.assertIn('(Revised after a late internal check) Correction: it is 108.',row['text'])
        self.assertEqual(lwm['provisional_chars'],lwm['at_char']);self.assertGreater(lwm['revision_chars'],0)
    def test_off_and_no_residency_run_no_body(self):
        Operator(self.r).run(':latewatch off');meta,_=self.turn();self.assertEqual(meta['late_watch']['status'],'OFF')
        Operator(self.r).run(':latewatch shadow');self.p.stop()
        with mock.patch.object(lw,'residency',return_value='NO_RESIDENCY'):meta,_=self.turn('What is 46 plus 62 again?')
        self.p.start();self.assertEqual(meta['late_watch']['status'],'NO_RESIDENCY')
        self.assertEqual(self.calls,[]);self.assertNotIn('offered',meta['late_watch'])
        with self.assertRaises(ValueError):Operator(self.r).run(':latewatch maybe')

if __name__=='__main__':unittest.main()
