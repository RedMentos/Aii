"""WP-V7 C2 benchmark harness: frozen corpus, call parsing, metrics (no models)."""
import json,sys,unittest
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

if __name__=='__main__':unittest.main()
