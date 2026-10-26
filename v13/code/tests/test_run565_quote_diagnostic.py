"""Run565: adversarial model-free quote-source and missing-input diagnostic tests."""
import tempfile,unittest
from pathlib import Path
import run565_quote_diagnostic as m

H='Project A kickoff. Budget 142 euros. Deadline 4 days. Local-only requirement: true. Option A: cost 120 euros, duration 3 days, local true. Option B: cost 110 euros, duration 5 days, local false.'
C='Project A. Decide from earlier rules.'

class TestRun565(unittest.TestCase):
    def fixture(self,current=C,history=None):
        return {'history':[H] if history is None else history,'current':current}
    def analyst(self,quotes,role='B2_GIST'):
        return [{'role':role,'verified_quotes':quotes}]
    def test_all_five_exact_quotes(self):
        rules=m.required_rules(self.fixture())
        quotes=[x['sentence'] for x in rules.values()]
        self.assertTrue(all(m.quote_coverage(self.analyst(quotes),rules).values()))
    def test_numeric_prefix_and_wrong_boolean_are_not_evidence(self):
        rules=m.required_rules(self.fixture())
        q=['Budget 1420 euros.','Deadline 40 days.','Local-only requirement: false.',
           'Option A: cost 1200 euros, duration 3 days, local true.',
           'Option B: cost 110 euros, duration 50 days, local false.']
        self.assertFalse(any(m.quote_coverage(self.analyst(q),rules).values()))
    def test_current_override_without_history_quote(self):
        current='Rules for this decision: budget 107 euros, deadline 7 days, local-only requirement: true.'
        rules=m.required_rules(self.fixture(current=current,history=[H]))
        self.assertEqual(rules['budget']['location'],'current')
        self.assertEqual(rules['budget']['sentence'].lower(),'budget 107 euros')
        self.assertEqual(rules['option_A']['location'],'history')
    def test_missing_history_and_current_refused(self):
        with self.assertRaisesRegex(ValueError,'RULE_MISSING'):
            m.required_rules(self.fixture(history=['No budget, deadline or options.']))
    def test_malformed_quote_and_wrong_role(self):
        rules=m.required_rules(self.fixture())
        with self.assertRaisesRegex(ValueError,'MALFORMED_QUOTE'):
            m.quote_coverage(self.analyst([None]),rules)
        self.assertFalse(any(m.quote_coverage(self.analyst([rules['budget']['sentence']],role='C3_LANGUAGE'),rules).values()))
    def test_exact_three_pinned_safe_archives_required(self):
        with self.assertRaisesRegex(ValueError,'EXACT_THREE'):
            m.audit([],[])
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'safe.zip';p.write_bytes(b'not a zip')
            with self.assertRaisesRegex(ValueError,'PINNED_ZIP_SHA_MISMATCH'):
                m.audit([p,p,p],['0'*64]*3)

if __name__=='__main__':unittest.main()
