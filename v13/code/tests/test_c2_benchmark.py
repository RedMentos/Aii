"""WP-V7 C2 benchmark harness: frozen corpus, call parsing, metrics (no models)."""
import json,sys,tempfile,types,unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import c2_benchmark as C

class C2BenchTests(unittest.TestCase):
    def test_corpus_is_frozen_balanced_and_matches_tool_enum(self):
        d=C.corpus();labels=[x['label'] for x in d['items']]
        self.assertEqual(sorted(set(labels)),sorted(C.ROUTES));self.assertTrue(all(labels.count(r)==24 for r in C.ROUTES))
        self.assertEqual(C.tool()['parameters']['properties']['route']['enum'],list(C.ROUTES))
        self.assertEqual(len({x['id'] for x in d['items']}),len(d['items']))
    def test_route_parsing_openai_json_and_functiongemma_native(self):
        self.assertEqual(C.route_of('{"route":"gist"}'),'gist');self.assertEqual(C.route_of({'route':'nope'}),None)
        self.assertEqual(C.NATIVE_CALL.search('<start_function_call>call:select_processing{route:<escape>both<escape>}').group(1),'both')
    def test_summary_counts_invalid_as_wrong(self):
        rows=[{'label':'simple','pred':'simple','latency_s':.1},{'label':'detail','pred':None,'latency_s':.2},
              {'label':'gist','pred':'gist','latency_s':.1},{'label':'both','pred':'gist','latency_s':.3}]
        s=C.summarize(rows);self.assertEqual(s['accuracy'],.5);self.assertEqual(s['valid_rate'],.75);self.assertEqual(s['confusion']['detail'],{'None':1})
        self.assertEqual(C.auroc([.9,.1],[True,False]),1.)

    def test_native_scores_first_validated_select_processing_not_unrelated_tool(self):
        class FakeNeedle:
            proc = None
            def load(self, *args): pass
            def control(self, *args):
                return {'success':True, 'validation':{'negation':False,'ungrounded':False},
                        'confidence':.8, 'function_calls':[
                            {'name':'other_tool','arguments':{'route':'gist'}},
                            {'name':'select_processing','arguments':{'route':'detail'}},
                            {'name':'select_processing','arguments':{'route':'both'}}]}
        class FakeModels:
            def __init__(self, path): self.path = path
            def path_for(self, role): return self.path
        class FakeRuntime:
            def __init__(self, path):
                self.needle = FakeNeedle()
                self.models = FakeModels(path)
            def close(self): pass
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'needle3.cact'
            model.write_bytes(b'CACT')
            with patch('v13.runtime.Runtime', return_value=FakeRuntime(model)):
                rows, extra = C.run_needle([{'id':'one','text':'calculate','label':'detail'}], Path(td))
        self.assertEqual(rows[0]['pred'], 'detail')
        self.assertTrue(rows[0]['validated'])
        self.assertEqual(extra['validated_rate'], 1.)
        self.assertEqual(C.summarize(rows)['accuracy'], 1.)

    def test_native_rejects_unrelated_tool_without_select_processing(self):
        class FakeNeedle:
            proc = None
            def load(self, *args): pass
            def control(self, *args):
                return {'success':True, 'validation':{}, 'confidence':.8,
                        'function_calls':[{'name':'other_tool','arguments':{'route':'detail'}}]}
        class FakeModels:
            def __init__(self, path): self.path = path
            def path_for(self, role): return self.path
        class FakeRuntime:
            def __init__(self, path):
                self.needle = FakeNeedle()
                self.models = FakeModels(path)
            def close(self): pass
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'needle3.cact'
            model.write_bytes(b'CACT')
            with patch('v13.runtime.Runtime', return_value=FakeRuntime(model)):
                rows, extra = C.run_needle([{'id':'one','text':'calculate','label':'detail'}], Path(td))
        self.assertIsNone(rows[0]['pred'])
        self.assertFalse(rows[0]['validated'])
        self.assertEqual(extra['validated_rate'], 0.)

    def test_invalid_native_observation_never_scores_pred_and_nonfinite_confidence(self):
        class FakeNeedle:
            proc = None
            def load(self, *args): pass
            def control(self, *args):
                return {'function_calls': [{'name':'select_processing',
                                            'arguments':{'route':'detail'}}],
                        'confidence': float('nan')}
        class FakeModels:
            def __init__(self, path): self.path = path
            def path_for(self, role): return self.path
        class FakeRuntime:
            def __init__(self, path):
                self.needle = FakeNeedle()
                self.models = FakeModels(path)
            def close(self): pass
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'needle3.cact'
            model.write_bytes(b'CACT')
            fake_observer=types.ModuleType('v13.control_calibration_worker')
            def reject(_): raise ValueError('invalid native control')
            fake_observer.observation=reject
            with (patch('v13.runtime.Runtime', return_value=FakeRuntime(model)),
                  patch.dict(sys.modules, {'v13.control_calibration_worker': fake_observer})):
                rows, extra = C.run_needle([{'id':'one','text':'budget',
                                             'label':'detail'}], Path(td))
            self.assertIsNone(rows[0]['pred'])
            self.assertFalse(rows[0]['validated'])
            self.assertEqual(extra['validated_rate'], 0.)
            self.assertIsNone(extra['confidence_auroc'])
            self.assertEqual(C.summarize(rows)['accuracy'], 0.)

if __name__=='__main__':unittest.main()
