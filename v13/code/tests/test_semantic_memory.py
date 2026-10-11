"""WP-H/WP-S2 semantic memory keys. Synthetic concept vectors: tests authority/caching, not model quality."""
from pathlib import Path
import tempfile
import threading
import unittest
from v13.common import Unavailable,Cancelled
from v13.models import model_key,catalog
from v13.runtime import Runtime
from v13.semantic_memory import SemanticKeys,truncate,mode,status

CONCEPTS={'budget':0,'money':0,'funds':0,'keys':1,'car':1,'vehicle':1,'rain':2,'weather':2}

class Fake:
    def __init__(self,fail=None):self.calls=[];self.fail=fail;self.last_metrics={}
    def installed(self):return True
    def revision(self):return 'fake-r1'
    def pids(self):return []
    def unload(self):pass
    def __call__(self,texts,cancel,deadline):
        if self.fail:raise self.fail
        if cancel is not None and cancel.is_set():raise Cancelled('x')
        self.calls.append(list(texts));out=[]
        for t in texts:
            v=[.01]*300
            for word,axis in CONCEPTS.items():
                if word in t.lower():v[axis]+=1.
            out.append(v)
        return out

class SemanticRecall(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(Path(self.tmp.name));self.fake=Fake()
        self.keys=SemanticKeys(self.r.store,self.r.cfg,self.fake);self.r.memory.semantic_keys=self.keys
    def tearDown(self):self.r.close();self.tmp.cleanup()
    def remember(self,key='What is the budget of Project Alpha?',value='120 Euro'):
        e=self.r.store.event(self.r.session,key);return self.r.memory.feedback(e['event_id'],'fact',value,key=key)
    def recall(self,q,**kw):return self.r.memory.recall(q,self.r.session,cancel=threading.Event(),**kw)
    def test_paraphrase_found_only_by_embedding_and_value_comes_from_source(self):
        mid=self.remember();q='How much money does Project Alpha have?'
        self.r.cfg['memory_embedding']='off';self.assertEqual(self.recall(q),[]);self.assertEqual(self.fake.calls,[])
        self.r.cfg['memory_embedding']='on';got=self.recall(q)
        self.assertEqual([m['id'] for m in got],[mid]);self.assertEqual(got[0]['value'],'120 Euro')
        self.assertEqual(got[0]['retrieval_channel'],'embedding');self.assertGreater(got[0]['embedding_similarity'],.9)
        self.assertEqual(self.r.store.read_source(got[0]['source_ref']),'120 Euro')
    def test_entity_guard_and_unrelated_question_stay_out(self):
        self.remember();self.r.cfg['memory_embedding']='on'
        self.assertEqual(self.recall('How much money does Project Beta have?'),[])
        self.assertEqual(self.recall('Will it rain tomorrow?'),[])
    def test_shadow_measures_without_admitting(self):
        self.remember();self.r.cfg['memory_embedding']='shadow'
        self.assertEqual(self.recall('How much money does Project Alpha have?'),[])
        self.assertEqual(self.keys.last['status'],'OK');self.assertEqual(self.keys.last['mode'],'shadow')
        row=self.r.store.one("SELECT metrics FROM telemetry WHERE kind='memory_embedding' ORDER BY id DESC LIMIT 1");self.assertNotIn('Alpha',row['metrics']);self.assertIn('"mode": "shadow"',row['metrics'].replace('"mode":"shadow"','"mode": "shadow"'))
    def test_key_cache_reused_invalidated_by_revision_and_removed_by_forget(self):
        mid=self.remember();self.r.cfg['memory_embedding']='on'
        self.recall('How much money does Project Alpha have?');self.recall('Project Alpha funds?')
        self.assertEqual([len(c) for c in self.fake.calls],[2,1]);self.assertEqual(self.keys.last['encoded_keys'],0)
        self.keys._revision='fake-r2';self.recall('Project Alpha funds?');self.assertEqual(len(self.fake.calls[-1]),2)
        self.assertEqual(status(self.r)['cached_keys'],2)
        self.r.memory.forget(mid);self.assertEqual(status(self.r)['cached_keys'],0)
    def test_new_keys_beyond_cap_are_deferred(self):
        for i in range(3):self.remember('What is the budget of Project Alpha part '+str(i)+'?',str(i))
        self.r.cfg['memory_embedding']='on';self.r.cfg['retrieval_candidates']=2
        self.recall('How much money does Project Alpha have?');self.assertEqual(self.keys.last['deferred_keys'],1)
        self.recall('How much money does Project Alpha have?');self.assertEqual(self.keys.last['encoded_keys'],1)
    def test_encoder_failure_falls_back_to_lexical_and_cancel_propagates(self):
        mid=self.remember();self.r.cfg['memory_embedding']='on';self.keys.encoder=Fake(Unavailable('no model'))
        self.assertEqual([m['id'] for m in self.recall('What is the budget of Project Alpha?')],[mid])
        self.assertEqual(self.keys.last['status'],'UNAVAILABLE')
        self.keys.encoder=Fake();stop=threading.Event();stop.set()
        with self.assertRaises(Cancelled):self.r.memory.recall('How much money does Project Alpha have?',self.r.session,cancel=stop)

class SemanticPieces(unittest.TestCase):
    def test_matryoshka_truncation_and_modes(self):
        v=truncate([3.,4.,99.],2);self.assertAlmostEqual(v[0],.6);self.assertAlmostEqual(v[1],.8)
        with self.assertRaises(Unavailable):truncate([1.],2)
        with self.assertRaises(Unavailable):truncate([0.,0.],2)
        self.assertEqual(mode({'memory_embedding':'auto'},False),'off');self.assertEqual(mode({'memory_embedding':'auto'},True),'on')
        self.assertEqual(mode({'memory_embedding':'shadow'},True),'shadow')
    def test_optional_model_role_is_pinned_and_not_a_runtime_revision(self):
        spec=catalog()['models']['embedding'];self.assertEqual(model_key('M_EMBED'),'embedding')
        self.assertEqual(len(spec['files'][0]['sha256']),64);self.assertIn(spec['revision'],spec['files'][0]['url'])
        with tempfile.TemporaryDirectory() as td:
            r=Runtime(Path(td))
            try:
                self.assertNotIn('M_EMBED',r.revisions());self.assertEqual(status(r)['mode'],'off');self.assertFalse(status(r)['installed'])
            finally:r.close()

if __name__=='__main__':unittest.main()
