"""Synthetic-only B2 context project identity and exact-span regressions."""
import hashlib
import json
import re
import unittest

from scripts import run12_b2_context_identity_candidate as c

CUR='Project Aquila. Use the earlier binding project rules and the latest supplier sheet.'
NOTE='Project Aquila kickoff memo: archived heading, binding values follow. Budget 134 euros. Deadline 9 days. Local-only requirement: true.'
ATLAS='Project Atlas archive index. No active project rules or supplier prices.'
SHEET='Project Aquila supplier sheet. Option A: cost 91 euros, duration 7 days, local true. Option B: cost 105 euros, duration 8 days, local false.'


def make_item(text,n):
    ref={'source_id':'src_'+format(n,'032x'),'sha256':hashlib.sha256(text.encode()).hexdigest(),
         'char_start':0,'char_end':len(text),'modality':'text'}
    return {'offer_id':'pkt_'+format(n,'032x'),'role':'B2_GIST','event_id':'evt_'+format(n,'032x'),
            'session':'s1','generation':'g1','model_revision':'m1','source_ref':ref,'hypothesis':'untrusted'}


def reader_for(items,texts):
    lookup={item['source_ref']['source_id']:text for item,text in zip(items,texts)}
    def reader(ref):
        full=lookup[ref['source_id']]
        if hashlib.sha256(full.encode()).hexdigest()!=ref['sha256']:raise ValueError('HASH_CHANGED')
        return full[ref['char_start']:ref['char_end']]
    return reader


def run(items,texts,**kwargs):
    return c.select_context(CUR,'current','s1','g1','m1',items,reader_for(items,texts),**kwargs)


class B2IdentityTests(unittest.TestCase):
    def test_generic_project_rules_never_a_named_entity(self):
        self.assertEqual(c.named_entities(CUR),{'aquila'})
        self.assertEqual(c.named_entities(ATLAS),{'atlas'})
        old=lambda t:set(re.findall(r'\b(?:project|projekt)\s+["\']?([\w-]+)',t.lower()))
        self.assertIn('rules',old(CUR)&old(ATLAS))
        self.assertFalse(c.named_entities(CUR)&c.named_entities(ATLAS))

    def test_relevant_old_note_survives_bounded_context(self):
        items=[make_item(SHEET,3),make_item(ATLAS,2),make_item(NOTE,1)]
        x=run(items,[SHEET,ATLAS,NOTE],cap=768)
        ids=[v['source_ref']['source_id'] for v in x['items']]
        self.assertEqual(ids,[items[2]['source_ref']['source_id'],items[0]['source_ref']['source_id']])
        self.assertEqual(x['reasons']['PROJECT_MISMATCH'],1)
        self.assertIn('Budget 134 euros.',x['items'][0]['native_context']['exact_source_excerpt'])
        self.assertFalse(x['canonical_gate_pass'])

    def test_realistic_240_char_sheet_cannot_displace_older_rules(self):
        long_sheet=('Project Aquila supplier data sheet revision 3. The latest sheet lists the two remaining '
                    'offers and explains that earlier offers were withdrawn. All figures confirmed. '
                    'The procurement desk repeats the source introduction for clarity. '
                    'Option A: cost 91 euros, duration 7 days, local true.')
        items=[make_item(long_sheet,3),make_item(ATLAS,2),make_item(NOTE,1)]
        for item in items:item['hypothesis']='H'*120
        x=run(items,[long_sheet,ATLAS,NOTE],cap=768)
        self.assertEqual(x['items'][0]['source_ref']['source_id'],items[2]['source_ref']['source_id'])
        self.assertIn('Budget 134 euros.',x['items'][0]['native_context']['exact_source_excerpt'])
        self.assertEqual(x['reasons']['CAP'],1)

    def test_current_complete_rules_do_not_prioritize_old_note(self):
        long_sheet=('Project Aquila supplier data sheet revision 3. The latest sheet lists the two remaining '
                    'offers and explains that earlier offers were withdrawn. All figures confirmed. '
                    'The procurement desk repeats the source introduction for clarity. '
                    'Option A: cost 91 euros, duration 7 days, local true.')
        items=[make_item(long_sheet,3),make_item(ATLAS,2),make_item(NOTE,1)]
        for item in items:item['hypothesis']='H'*120
        current=CUR+' Current binding rules: Budget 100 euros. Deadline 5 days. Local-only requirement: false.'
        x=c.select_context(current,'current','s1','g1','m1',items,reader_for(items,[long_sheet,ATLAS,NOTE]))
        self.assertEqual(x['items'][0]['source_ref']['source_id'],items[0]['source_ref']['source_id'])
        self.assertEqual(x['reasons']['CAP'],1)

    def test_no_cross_project_even_with_shared_rule_words(self):
        items=[make_item(ATLAS,2)]
        self.assertEqual(run(items,[ATLAS])['items'],[])

    def test_refusal_on_missing_current_named_entity(self):
        items=[make_item(NOTE,1)]
        x=c.select_context('Use the rules.','current','s1','g1','m1',items,reader_for(items,[NOTE]))
        self.assertEqual(x['items'],[])
        self.assertEqual(x['reasons']['NO_CURRENT_NAMED_ENTITY'],1)

    def test_scope_and_model_revision_must_match(self):
        item=make_item(NOTE,1);item['model_revision']='old'
        x=run([item],[NOTE]);self.assertEqual(x['items'],[])
        self.assertEqual(x['reasons']['OUT_OF_SCOPE'],1)

    def test_tombstone_or_corruption_refused(self):
        item=make_item(NOTE,1)
        x=c.select_context(CUR,'current','s1','g1','m1',[item],lambda ref:(_ for _ in ()).throw(ValueError('DELETED')))
        self.assertEqual(x['items'],[]);self.assertEqual(x['reasons']['SOURCE_UNAVAILABLE'],1)

    def test_duplicated_source_id_not_twice(self):
        item=make_item(NOTE,1)
        x=run([item,item],[NOTE,NOTE]);self.assertEqual(len(x['items']),1)
        self.assertEqual(x['reasons']['DUPLICATE_SOURCE'],1)

    def test_invalid_ref_refused(self):
        item=make_item(NOTE,1);item['source_ref']['sha256']='bad'
        x=run([item],[NOTE]);self.assertEqual(x['items'],[])
        self.assertEqual(x['reasons']['BAD_REF'],1)

    def test_oversized_source_refused(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_TEXT_SIZE'):
            c.named_entities('Project Aquila '+'x'*10001)

    def test_bounds_refused(self):
        item=make_item(NOTE,1)
        with self.assertRaisesRegex(ValueError,'BOUNDS'):
            run([item],[NOTE],cap=10)

    def test_current_revised_rules_are_not_overridden(self):
        # Selector only exposes source; does not compute or authorize any rule.
        item=make_item(NOTE,1)
        x=c.select_context(CUR+' Current revised binding rules: Budget 100 euros. Deadline 5 days. Local-only requirement: false.',
                           'current','s1','g1','m1',[item],reader_for([item],[NOTE]))
        self.assertEqual(x['authority'],'SOURCE_POINTER_ONLY')
        self.assertEqual(len(x['items']),1)
        self.assertFalse(x['canonical_gate_pass'])


if __name__=='__main__':unittest.main()
