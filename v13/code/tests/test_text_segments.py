"""WP-N8 rest / §51.2 A1 inside one text: event segments instead of fixed 240-char chunks."""
import unittest
from v13.episodes import text_segments,TEXT_MAX,TEXT_MIN
from v13.cognition import segments,percept_mode

TEXT=('Project Aurora has a budget of 120 euros. The deadline is 2026-11-02 and the lead is Mila.\n\n'
      'Now something else: how do I bake bread? I need flour, water and salt.\n- step 1: mix\n- step 2: knead for 10 minutes\n'
      'Thanks!'+' This is a very long sentence without any break'*12+' end.')

class TextSegments(unittest.TestCase):
    def test_segments_tile_the_text_and_keep_source_refs(self):
        s=text_segments(TEXT,{'source_id':'src1'},120)
        self.assertEqual(''.join(x['text'] for x in s),TEXT)
        for x in s:
            r=x['source_ref'];self.assertEqual(r['source_id'],'src1');self.assertEqual(TEXT[r['char_start']:r['char_end']],x['text'])
        self.assertEqual([a['source_ref']['char_end'] for a in s[:-1]],[b['source_ref']['char_start'] for b in s[1:]])
    def test_topic_paragraph_and_list_boundaries_cut_fixed_chunks_do_not(self):
        s=text_segments(TEXT,{},120);first=s[0]['text']
        self.assertTrue(first.rstrip().endswith('Mila.'))  # paragraph + topic shift, not mid-sentence
        self.assertTrue(any(x['text'].startswith('- step 1') for x in s))  # list starts its own segment
        fixed=segments(TEXT,{},120);self.assertFalse(fixed[0]['text'].rstrip().endswith('Mila.'))
        self.assertTrue(all(x.get('reason') in ('first','signals','max_width') for x in s))
    def test_width_bounds_and_exact_spans_survive_splitting(self):
        long='The code is A7-99X-3. '+'word '*400+'and the invoice 55-1209 is due.'
        s=text_segments(long,{},100)
        self.assertTrue(all(len(x['text'])<=100*TEXT_MAX*2 for x in s))
        self.assertTrue(any('55-1209' in x['text'] for x in s) and any('A7-99X-3' in x['text'] for x in s))
        self.assertEqual(text_segments('',{},100),[])
        short=text_segments('Hi. Ok.',{},240);self.assertEqual(len(short),1)  # never below TEXT_MIN of the width
    def test_mode_switch(self):
        self.assertEqual(percept_mode({}),'event');self.assertEqual(percept_mode({'segment_mode':'fixed'}),'fixed')
        self.assertEqual(segments('abc'*100,{},240)[0]['text'],('abc'*100)[:240])
        self.assertEqual(segments(TEXT,{},120,'event'),text_segments(TEXT,{},120))

if __name__=='__main__':unittest.main()
