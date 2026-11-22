"""WP-J model-free part: §85.2 B3_MESSAGE with signed_gain, learned channel policy (B3-5), utility contract (B3-H9),
degradation (B3-H10), :doctor fields (B3-H11). LATENT stays unavailable."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from v13.runtime import Runtime
from v13.operator import Operator
from v13.contracts import packet
from v13.verification import b3_doctor
from v13 import callosum as C
from v13 import neuromod as N

def offer(role,summary,quotes=(),refs=(),reentry=False,eid='e',gen='g',pid=None):
    return {'role':role,'event_id':eid,'brain_generation_id':gen,'packet_id':pid or 'pkt_'+role,'evidence_refs':list(refs),'rejected_quotes':0,
            'offer':{'summary':summary,'quotes':list(quotes),'uncertainty':'','needs_reentry':reentry}}

class GainTests(unittest.TestCase):
    def test_signed_gain_amplify_suppress_neutral(self):
        ref={'source_id':'s','sha256':'0'*64,'char_start':0,'char_end':3,'modality':'text'}
        self.assertEqual(C.signed_gain(offer('B1_DETAIL','Total is 391',refs=[ref]),offer('B2_GIST','Total is 400'))[0],-.5)
        self.assertEqual(C.signed_gain(offer('B1_DETAIL','Total is 391'),offer('B2_GIST','about 391 overall'))[0],.5)
        self.assertEqual(C.signed_gain(offer('B1_DETAIL','unclear',reentry=True),None)[0],.25)
        self.assertEqual(C.signed_gain(offer('B1_DETAIL','Total is 391'),offer('B2_GIST','Total is 400'))[0],0.)  # no exact evidence: no suppress
    def test_probabilities_keep_baselines_and_block_latent(self):
        d={'u':{'CONTROL':{'v':2.,'n':9}}}
        p=C.Callosum.probabilities(d);self.assertEqual(p['LATENT'],0.);self.assertTrue(all(p[c]>=C.FLOOR for c in C.CHANNELS))
        self.assertAlmostEqual(sum(p[c] for c in C.CHANNELS),1.,places=3);self.assertEqual(max(C.CHANNELS,key=p.get),'CONTROL')

class Base(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.r.sleep.cycle.set_policy('enabled','off')
        self.c=C.Callosum(self.r.store,N.Neuromod(self.r.store))
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def teach(self,channel,util,n=C.MIN_N,d='B1_TO_B2'):
        def fn(st):
            for _ in range(n):self.c._update(st,d,channel,util)
        self.c._mutate(fn)

class PolicyTests(Base):
    def test_shadow_proposes_active_applies_and_never_below_no_message(self):
        self.assertEqual(self.c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT'),('SOURCE_EXACT','SOURCE_EXACT',False))
        self.teach('NO_MESSAGE',.5);self.teach('CONTROL',1.2);self.teach('SYMBOLIC',.2)
        self.assertEqual(self.c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT'),('SOURCE_EXACT','CONTROL',False))
        with self.assertRaises(PermissionError):self.c.set_mode('ACTIVE')
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN');self.assertEqual(self.c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT')[0],'CONTROL')
        self.teach('CONTROL',-1.,n=30);self.assertEqual(self.c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT')[0],'NO_MESSAGE')
        self.assertEqual(self.c.choose('B2_GIST','B1_DETAIL','SYMBOLIC')[0],'SYMBOLIC')  # other direction unlearned
    def test_receiver_revision_change_degrades_to_configured(self):
        self.c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT','rev1');self.teach('NO_MESSAGE',.1);self.teach('CONTROL',1.)
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN');self.assertEqual(self.c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT','rev1')[0],'CONTROL')
        self.assertEqual(self.c.choose('B1_DETAIL','B2_GIST','SOURCE_EXACT','rev2')[0],'SOURCE_EXACT')
        self.assertEqual(self.c.doctor(self.r.cfg)['B1_TO_B2']['resets'],1)

class UtilityTests(Base):
    def test_message_fields_outcome_rating_and_doctor(self):
        # This positive learning test opts in explicitly; Runtime defaults to RECORD_ONLY.
        self.r.cfg['learning_mode']='SHADOW_UPDATE'
        e=self.r.store.event(self.r.session,'Rent 120 plus food 271');eid,gen=e['event_id'],e['brain_generation_id']
        sender=offer('B1_DETAIL','Total is 391',quotes=['120'],eid=eid,gen=gen,pid='pkt_s')
        out=self.r.cognition.communicate(sender,'B2_GIST')
        msg=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='MessagePacket' ORDER BY rowid DESC LIMIT 1")['payload'])
        for k in ('salience','confidence','signed_gain','urgency','temporal_scope','compatibility_score','utility_history','channel_proposal'):self.assertIn(k,msg)
        self.assertEqual((msg['latent_authority'],msg['latent_level']),(0,'unavailable'));self.assertEqual(out['message_packet_id'],msg['packet_id'])
        recv=packet('OfferPacket','B2_GIST',eid,gen,[],role='B2_GIST',based_on_state_version=0,deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[],
                    offer={'summary':'total 391','quotes':[],'uncertainty':'','needs_reentry':False},confidence=0.,native_metrics={'duration_s':3.})
        self.r.store.add_packet('OfferPacket',recv)
        # Diagnose the persisted handoff before scoring. This makes a missing
        # Callosum.note write distinguishable from a receiver-row lookup error.
        state,_=self.r.store.state(C.KEY,None)
        pending=(state or {}).get('pending',{}).get(eid,[])
        message_row=self.r.store.one("SELECT rowid FROM packets WHERE id=?",(out['message_packet_id'],))
        receiver_rows=self.r.store.rows(
            "SELECT rowid,json_extract(payload,'$.role') AS role FROM packets "
            "WHERE kind='OfferPacket' AND event_id=? ORDER BY rowid",(eid,))
        note_errors=self.r.store.rows(
            "SELECT metrics FROM telemetry WHERE kind='callosum_unavailable' AND event_id=?",(eid,))
        self.assertTrue(
            pending and message_row and any(
                row['rowid']>message_row['rowid'] and row['role']=='B2_GIST'
                for row in receiver_rows),
            f"callosum handoff precondition: pending={pending!r}; "
            f"message_row={message_row!r}; receiver_rows={receiver_rows!r}; "
            f"note_errors={note_errors!r}")
        pending_row=self.r.store.one(
            "SELECT rowid FROM packets WHERE id=?",(pending[0]['msg'],))
        exact_receiver=self.r.store.one(
            "SELECT rowid,payload FROM packets WHERE kind='OfferPacket' AND event_id=? "
            "AND rowid>? AND json_extract(payload,'$.role')=? ORDER BY rowid LIMIT 1",
            (eid,pending_row['rowid'] if pending_row else 0,pending[0]['receiver']))
        self.assertEqual(pending[0]['msg'],out['message_packet_id'],
                         f"Callosum message identity mismatch: {pending!r}; out={out!r}")
        self.assertEqual(pending[0]['receiver'],'B2_GIST',
                         f"Callosum receiver mismatch: {pending!r}")
        self.assertIsNotNone(
            exact_receiver,
            f"exact Callosum receiver lookup failed: pending={pending!r}; "
            f"pending_row={pending_row!r}; receiver_rows={receiver_rows!r}")
        self.assertIs(self.c.s,self.r.store,"Callosum and Runtime must share the exact Store instance")
        loaded_pending=self.c._load()[0].get('pending',{}).get(eid,[])
        self.assertEqual(loaded_pending,pending,
                         f"Callosum instance sees different persisted pending state: {loaded_pending!r} vs {pending!r}")
        res=self.c.outcome(eid,[recv['packet_id']],'FINAL');self.assertEqual(res['scored'],1);self.assertGreater(res['utilities'][0],1.)
        q=self.c._load()[0]['dirs']['B1_TO_B2']['u']['SOURCE_EXACT'];self.assertEqual(q['n'],1);self.assertIn('task_gain',q['parts'])
        self.assertEqual(C.on_rating(self.r.store,eid,10)['updated'],1)
        doc=b3_doctor(self.r)['B1_TO_B2'];self.assertEqual((doc['latent_level'],doc['status'],doc['injection_level']),('unavailable','PASS',0))
        self.assertEqual(doc['experience_count'],2);self.assertIn('utility_vs_no_message',doc)
        self.assertIn('LATENT blocked',Operator(self.r).run(':callosum'));self.assertEqual(N.kind_of('callosum_channel_policy'),'control')


    def test_record_only_guard_blocks_callosum_policy_updates(self):
        # record_only_gate.py is composed only in the staged candidate. The
        # source-only suite skips this staged-overlay-specific negative control.
        try:
            from v13.record_only_gate import blocked_status
        except ImportError:
            self.skipTest('RECORD_ONLY controller guard is a staged overlay')
        self.r.cfg['learning_mode']='RECORD_ONLY'
        e=self.r.store.event(self.r.session,'Rent 120 plus food 271')
        eid,gen=e['event_id'],e['brain_generation_id']
        sender=offer('B1_DETAIL','Total is 391',quotes=['120'],eid=eid,gen=gen,pid='pkt_record_only')
        out=self.r.cognition.communicate(sender,'B2_GIST')
        recv=packet('OfferPacket','B2_GIST',eid,gen,[],role='B2_GIST',based_on_state_version=0,
                    deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[],
                    offer={'summary':'total 391','quotes':[],'uncertainty':'','needs_reentry':False},
                    confidence=0.,native_metrics={'duration_s':3.})
        self.r.store.add_packet('OfferPacket',recv)
        before=self.c._load()[0]
        pending_before=before.get('pending',{}).get(eid,[])
        self.assertTrue(pending_before)
        self.assertEqual(pending_before[0]['msg'],out['message_packet_id'])
        result=self.c.outcome(eid,[recv['packet_id']],'FINAL')
        self.assertEqual(result,{'scored':0,'status':blocked_status(self.r.store)})
        rating=C.on_rating(self.r.store,eid,1.)
        self.assertEqual(rating,{'updated':0,'status':blocked_status(self.r.store)})
        after=self.c._load()[0]
        self.assertEqual(after['dirs'],before['dirs'])
        self.assertEqual(after.get('pending',{}).get(eid,[]),pending_before)

if __name__=='__main__':unittest.main()
