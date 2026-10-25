"""Run199 actual ContextOS.plan software integration of Run198 candidate, no runtime changes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v13.runtime import Runtime
from v13 import context_os as C
from scripts import context_inline_guard_run198 as G

FILL = 'Ordinary history text for context planning and compression. ' * 12
BAD = 'Late unclosed `source_ref_sensitive ' + FILL

# Historical Run199 RED baseline, pinned to the pre-Run350 compress algorithm
# (source SHA256 832aaea23c3790c42720d5b7174b1a90f9ec677d60005b3424d9a93d85a8ecb2).
# This is test-only evidence of the old bug, never production compression.
def legacy_compress_run199(text, cap):
    spans = C.exact_spans(text)
    if text.count('```') % 2:
        return text, spans, False
    if sum(len(x) for x in spans) > C.SPAN_CHARS or len(spans) > C.SPAN_MAX:
        return text, spans, False
    head = C.first_sentence(text, cap)
    missing = [x for x in spans if x not in head]
    out = '[compressed earlier turn; exact source kept] ' + head + (
        (' | exact: ' + ' ; '.join(missing)) if missing else '')
    ok = len(out) < len(text) and all(x in out for x in spans)
    return (out, spans, True) if ok else (text, spans, False)


def history():
    out = []
    for i in range(12):
        text = 'Opening sentence. ' + FILL + (BAD if i == 0 else '')
        out += [{'event_id':f'ev{i}','role':'user','text':text},
                {'event_id':f'ev{i}','role':'assistant','text':'Acknowledged. ' + FILL}]
    return out


class PlanIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.r = Runtime(Path(self.tmp.name))
        self.r.sleep.cycle.set_policy('enabled','off')
        self.c = C.ContextOS(self.r.store, dict(self.r.cfg, context_tokens=8192, answer_tokens=256))

    def tearDown(self):
        self.r.close()
        self.tmp.cleanup()

    def _safe_patch(self):
        # Do NOT patch C.compress directly to G.compress_candidate: that
        # function calls C.compress and would recurse after patching.
        original = C.compress
        def guarded(text, cap):
            if G.unsafe_inline_delimiters(text):
                return text, C.exact_spans(text), False
            return original(text, cap)
        return patch.object(C, 'compress', guarded)

    def plan(self, q='new question'):
        eid = self.r.store.event(self.r.session,q)['event_id']
        return self.c.plan(eid,'C3_LANGUAGE','SYS',[],history(),q)

    def test_original_plan_exposes_exact_literal_loss_counterexample(self):
        # Reproduce the original negative on its frozen algorithm, not on the
        # subsequently fixed live implementation.
        with patch.object(C, 'compress', legacy_compress_run199):
            result = self.plan()
        first = next(x for x in result['plan']['items'] if x['item_id']=='ev0')
        self.assertEqual(first['form'],'COMPRESSED')
        self.assertNotIn('`source_ref_sensitive', ''.join(m['content'] for m in result['planned']))
        self.assertFalse(result['applied'])

    def test_candidate_preserves_raw_literal_in_planned_view(self):
        with self._safe_patch():
            result = self.plan()
        first = next(x for x in result['plan']['items'] if x['item_id']=='ev0')
        self.assertEqual(first['form'],'RAW')
        self.assertIn('`source_ref_sensitive', ''.join(m['content'] for m in result['planned']))
        self.assertFalse(result['applied'])
        self.assertEqual(result['messages'],result['legacy'])

    def test_explicit_human_active_candidate_still_has_no_automatic_promotion(self):
        with self.assertRaises(PermissionError):
            self.c.set_mode('ACTIVE')
        self.c.set_mode('ACTIVE','EXPLICIT_HUMAN')
        with self._safe_patch():
            result = self.plan()
        self.assertTrue(result['applied'])
        self.assertEqual(result['messages'],result['planned'])
        self.assertIn('`source_ref_sensitive', ''.join(m['content'] for m in result['messages']))

    def test_candidate_patch_scope_restores_original_function(self):
        original = C.compress
        with self._safe_patch():
            self.assertIsNot(C.compress,original)
        self.assertIs(C.compress,original)


if __name__=='__main__':unittest.main()