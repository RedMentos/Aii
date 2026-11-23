"""R4 part 8 script: corpus families disjoint and deterministic, question view, head fitting and metrics. No models."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import r4_tool_choice_head as H

class Head(unittest.TestCase):
    def test_corpus_families_disjoint_and_stable(self):
        rows=H.corpus();self.assertEqual(rows,H.corpus())
        self.assertEqual({s:sum(r['split']==s for r in rows) for s in H.TEMPLATES},{'train':240,'test':228,'de':120})
        qs={s:{r['question'] for r in rows if r['split']==s} for s in H.TEMPLATES}
        self.assertFalse(qs['train']&qs['test']);self.assertFalse(qs['train']&qs['de']);self.assertFalse(qs['test']&qs['de'])
        self.assertTrue(any('Total:' in r['text'] and r['label']=='none' for r in rows))  # rule false alarms are possible
    def test_question_view(self):
        self.assertEqual(H.question_view('Items: a 1, b 2. Summary line: "Total: 4 euros." Is that right?'),'Is that right?')
        self.assertEqual(H.question_view('Rainfall: Lyon 600, Brno 200. Sum these up for me.'),'Sum these up for me.')
    def test_fit_and_metrics(self):
        rng=np.random.default_rng(0);X=np.concatenate([rng.normal(c*3,1,(30,4)) for c in range(3)]);y=np.repeat([0,1,2],30)
        self.assertEqual(H.metrics(y,H.fit(X,y,1e-3)(X))['macro_f1'],1.)
        m=H.metrics([0,0,1,2],[1,0,2,0]);self.assertEqual((m['false_alarm_rate'],m['op_confusion_rate'],m['missed_rate']),(.5,.5,.5))

if __name__=='__main__':unittest.main()
