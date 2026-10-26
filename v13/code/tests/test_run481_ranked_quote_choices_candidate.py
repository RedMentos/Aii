import unittest
from v13.cognition import quote_choices
from scripts.run481_ranked_quote_choices_candidate import ranked_quote_choices, diagnostic


class RankedChoices(unittest.TestCase):
    def test_relevant_earlier_source_survives_current_source_24_cap(self):
        current = ' '.join(f'Administrative topic {i} is unrelated.' for i in range(35))
        earlier = ('A decision memo. Budget 240 euros. Deadline 9 days. '
                   'Local-only requirement: true. Another note.')
        sources=[current,earlier]
        self.assertEqual(len(quote_choices(sources)),24)
        self.assertTrue(all(si==0 for si,_,_ in quote_choices(sources)))
        ranked=ranked_quote_choices(sources,'budget deadline local-only requirement',3)
        self.assertEqual(len(ranked),3)
        self.assertTrue(all(si==1 for si,_,_ in ranked))
        spans=[sources[si][a:b] for si,a,b in ranked]
        self.assertEqual(set(spans),{'Budget 240 euros.','Deadline 9 days.',
                                     'Local-only requirement: true.'})

    def test_rank_relevant_rules_above_first_project_title(self):
        current = ('Project Zephyr. An overview note. The meeting was brief. '
                   'The team met yesterday. No figures here.')
        earlier = ('Project Zephyr kickoff memo. Budget 75 euros. '
                   'Deadline 6 days. Local-only requirement: false.')
        sources=[current,earlier]
        self.assertEqual(quote_choices(sources)[0][0],0)
        selected=ranked_quote_choices(sources,'budget deadline local-only requirement',3)
        self.assertEqual(set(sources[si][a:b] for si,a,b in selected),
                         {'Budget 75 euros.','Deadline 6 days.',
                          'Local-only requirement: false.'})

    def test_no_matching_evidence_abstains(self):
        self.assertEqual(ranked_quote_choices(['Clouds pass.','A quiet morning.'],
                                              'budget deadline'),[])

    def test_no_generated_text_and_deterministic_ties(self):
        sources=['Budget 50 euros. Budget 60 euros.','Budget 70 euros.']
        a=ranked_quote_choices(sources,'budget',2)
        self.assertEqual(a,ranked_quote_choices(sources,'budget',2))
        self.assertEqual([sources[si][i:j] for si,i,j in a],
                         ['Budget 50 euros.','Budget 60 euros.'])

    def test_fails_closed_on_invalid_or_unbounded_inputs(self):
        bad=[(None,'budget',3),(['A'*16385],'budget',3),
             (['Budget.'],True,3),(['Budget.'],'budget',0),
             (['Budget.'],'budget',True),(['Budget.'],'the and',3)]
        for src,goal,cap in bad:
            with self.subTest(src=str(src)[:15],goal=goal,cap=cap),self.assertRaises(ValueError):
                ranked_quote_choices(src,goal,cap)

    def test_shadow_result_never_promotes(self):
        result=diagnostic(['Budget 40 euros.'],'budget')
        self.assertFalse(result['canonical_gate_pass'])
        self.assertEqual(result['latent_authority'],0)
        self.assertEqual(result['step2_exit'],'UTILITY_FAIL')
        self.assertEqual(result['choices'][0]['text'],'Budget 40 euros.')


if __name__=='__main__':unittest.main()
