import hashlib
import tempfile
from pathlib import Path
import unittest
import numpy as np
from v13.output_adapter_worker import DIM,features,loss_gradient,gradient_check,train,infer
from v13.runtime import Runtime
from v13.config import initialize

def fixture():
    rows=[];labels=[];groups=[]
    for i in range(160):
        k=i%2;v=np.zeros(DIM);v[0]=1.;v[1]=1. if k else -1.;v[2]=(i%7)/100
        rows.append(v.tolist());labels.append(k);groups.append(hashlib.sha256(('explicit-human-source-'+str(i)).encode()).hexdigest())
    return {'native_features':rows,'token_ids':[123,456],'base_log_probabilities':np.tile(np.log([.02,.02,.96]),(160,1)).tolist(),'target_indices':labels,'source_groups':groups,
        'config':{'output_adapter_steps':800,'output_adapter_lr':.1,'max_update_norm':.05,'retention_max_delta':.02,'output_adapter_max_bias':12.,'output_adapter_support_cosine':.95}}

class OutputAdapterTests(unittest.TestCase):
    def test_explicit_human_permission_and_exact_context_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            h=Path(d);initialize(h);r=Runtime(h)
            try:
                e=r.store.event(r.session,'Echte Frage');messages=[{'role':'system','content':'Deutsch'}, {'role':'user','content':'Echte Frage'}]
                dependency=r.store.source('Explizite Operator-Korrektur','HUMAN_FACT')
                self.assertIsNone(r.learner.output_delta(e,messages,999999999.,[dependency]))
                r.learner.output_feedback(e['event_id'],'Ja, gerne.','learn');rows=r.learner.output_labels();self.assertEqual(len(rows),1);self.assertEqual(rows[0][3],messages)
                self.assertIn(dependency,rows[0][2]['selection']['source_refs'])
                # The latest record-only decision revokes training eligibility.
                r.learner.output_feedback(e['event_id'],'Ja, gerne.','record');self.assertEqual(r.learner.output_labels(),[])
                self.assertEqual(r.store.rows("SELECT * FROM memories WHERE kind='output'"),[])
                with self.assertRaises(ValueError):r.learner.shadow_output_adapter()
                other=r.store.event(r.session,'Ohne tatsächlichen C3-Kontext')
                with self.assertRaises(ValueError):r.learner.output_feedback(other['event_id'],'Ja','learn')
                with self.assertRaises(ValueError):r.learner.output_delta(e,[{'role':'user','content':'Vertauschte Anfrage'}],999999999.)
            finally:r.close()
    def test_analytic_gradient_and_frozen_native_baseline(self):
        i=fixture();x=features(i['native_features'][:8]);b=np.asarray(i['base_log_probabilities'][:8]);y=np.asarray(i['target_indices'][:8]);w=np.zeros((DIM+1,2));copy=b.copy()
        self.assertLess(gradient_check(b,x,y,w,12.),1e-6);loss,g=loss_gradient(b,x,y,w);self.assertGreater(loss,0);self.assertEqual(g.shape,w.shape);self.assertTrue(np.array_equal(b,copy))
    def test_shadow_reload_native_bias_and_retention(self):
        with tempfile.TemporaryDirectory() as d:
            i=fixture();m=train(i,d);self.assertTrue(m['commit_eligible'],m);p=Path(d)/'candidate.npz';a=infer(i['native_features'][0],p)
            self.assertTrue(a['in_support']);self.assertEqual([x[0] for x in a['first_token_bias']],[123,456]);self.assertGreater(a['first_token_bias'][0][1],a['first_token_bias'][1][1]);self.assertEqual(a['native_body_parameters_modified'],0)
            alien=np.zeros(DIM);alien[-1]=1.;self.assertFalse(infer(alien,p)['in_support']);self.assertEqual(infer(alien,p)['first_token_bias'],[])
            # Production lineage uses a different output directory, never writes
            # over the active artifact while measuring retention.
            q=Path(d)/'second';q.mkdir();i['active_checkpoint']=str(p);second=train(i,q);self.assertEqual(second['retained_test']['n'],m['after']['n']);self.assertTrue(second['retention_pass'])
    def test_labels_probability_mass_and_vocabulary_fail_closed(self):
        i=fixture();i['source_groups'][0]=i['source_groups'][1]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):train(i,d)
        i=fixture();i['base_log_probabilities'][0][0]=float('nan')
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):train(i,d)
        i=fixture();i['token_ids']=[123,123]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):train(i,d)

if __name__=='__main__':unittest.main()
