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
        e=self.r.store.event(self.r.session,'Rent 120 plus food 271');eid,gen=e['event_id'],e['brain_generation_id']
        sender=offer('B1_DETAIL','Total is 391',quotes=['120'],eid=eid,gen=gen,pid='pkt_s')
        out=self.r.cognition.communicate(sender,'B2_GIST')
        msg=json.loads(self.r.store.one("SELECT payload FROM packets WHERE kind='MessagePacket' ORDER BY rowid DESC LIMIT 1")['payload'])
        for k in ('salience','confidence','signed_gain','urgency','temporal_scope','compatibility_score','utility_history','channel_proposal'):self.assertIn(k,msg)
        self.assertEqual((msg['latent_authority'],msg['latent_level']),(0,'unavailable'));self.assertEqual(out['message_packet_id'],msg['packet_id'])
        recv=packet('OfferPacket','B2_GIST',eid,gen,[],role='B2_GIST',based_on_state_version=0,deadline_monotonic_ns=time.monotonic_ns()+10**9,evidence_refs=[],
                    offer={'summary':'total 391','quotes':[],'uncertainty':'','needs_reentry':False},confidence=0.,native_metrics={'duration_s':3.})
        self.r.store.add_packet('OfferPacket',recv)
        res=self.c.outcome(eid,[recv['packet_id']],'FINAL');self.assertEqual(res['scored'],1);self.assertGreater(res['utilities'][0],1.)
        q=self.c._load()[0]['dirs']['B1_TO_B2']['u']['SOURCE_EXACT'];self.assertEqual(q['n'],1);self.assertIn('task_gain',q['parts'])
        self.assertEqual(C.on_rating(self.r.store,eid,10)['updated'],1)
        doc=b3_doctor(self.r)['B1_TO_B2'];self.assertEqual((doc['latent_level'],doc['status'],doc['injection_level']),('unavailable','PASS',0))
        self.assertEqual(doc['experience_count'],2);self.assertIn('utility_vs_no_message',doc)
        self.assertIn('LATENT blocked',Operator(self.r).run(':callosum'));self.assertEqual(N.kind_of('callosum_channel_policy'),'control')

if __name__=='__main__':unittest.main()
