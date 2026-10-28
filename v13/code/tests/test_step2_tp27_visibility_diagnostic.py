"""Synthetic-only regressions for source-bound TP27 visibility diagnosis."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts import step2_tp27_visibility_diagnostic as d

CURRENT = 'Project Demo. Choose cheapest eligible. Option A: cost 5 euros, duration 2 days, local true. Option B: cost 7 euros, duration 3 days, local false.'
OLD = 'Project Demo kickoff. Budget 10 euros. Deadline 4 days. Local-only requirement: true.'
NEW = 'Budget 12 euros. Deadline 5 days. Local-only requirement: false.'


def row(current=CURRENT, quotes=(OLD,), evidence=None):
    if evidence is None:evidence=[current, *quotes]
    return {'fixture':'Demo','variant':'both_exact','consumer_messages':[
        {'role':'system','content':'Do not invent.'},
        {'role':'user','content':json.dumps({'current_source':current,'analysts':[
            {'role':'B2_GIST','verified_quotes':list(quotes)}]})}],
        'source_evidence':[{'text':s,'source_ref':{'source_id':'src_'+str(i)}} for i,s in enumerate(evidence)],
        'oracle_visible_to_native':False}


def reports():
    fixtures=[{'id':'F'+str(i),'type':'SPLIT'} for i in range(10)]
    native_rows=[];tool_rows=[]
    for f in fixtures:
        for variant in d.VARIANTS:
            x=row();x['fixture']=f['id'];x['variant']=variant
            native_rows.append(x)
            tool_rows.append({'fixture':f['id'],'variant':variant,'oracle_visible_to_native':False,
                              'consumer_messages_sha256':d.sha(d.canonical(x['consumer_messages'])),
                              'answer':'{"action":"UNKNOWN"}', 'score':{'exact':False}})
    n={'status':'UTILITY_FAIL','fixtures':fixtures,'rows':native_rows,
       'row_sha256':{x['fixture']+':'+x['variant']:d.sha(d.canonical(x)) for x in native_rows}}
    t={'status':'TOOL_UTILITY_FAIL','canonical_gate_pass':False,'rows':tool_rows,
       'row_sha256':{x['fixture']+':'+x['variant']:d.sha(d.canonical(x)) for x in tool_rows}}
    return n,t


class VisibilityTests(unittest.TestCase):
    def test_prior_rules_plus_current_options_complete(self):
        v=d._visible(row())
        self.assertTrue(v['complete'])
        self.assertEqual(v['rules'],{'budget':10,'deadline':4,'local_only':True})
        self.assertEqual(v['origins']['budget'],'quotes')
        self.assertEqual(v['options']['A'],(5,2,True))

    def test_no_prior_rules_abstains(self):
        v=d._visible(row(quotes=()))
        self.assertFalse(v['complete'])
        self.assertIsNone(v['rules']['budget'])

    def test_current_revision_overrides_old_quote(self):
        v=d._visible(row(current=CURRENT+' '+NEW))
        self.assertTrue(v['complete'])
        self.assertEqual(v['rules'],{'budget':12,'deadline':5,'local_only':False})
        self.assertEqual(v['origins']['budget'],'current')

    def test_conflicting_prior_quotes_abstain(self):
        v=d._visible(row(quotes=(OLD,NEW)))
        self.assertFalse(v['complete'])
        self.assertIsNone(v['rules']['budget'])
        self.assertIsNone(v['rules']['deadline'])

    def test_forged_verified_quote_refused(self):
        with self.assertRaisesRegex(ValueError,'UNBACKED_VERIFIED_QUOTE'):
            d._visible(row(evidence=[CURRENT]))

    def test_forged_current_refused(self):
        with self.assertRaisesRegex(ValueError,'CURRENT_NOT_SOURCE_BACKED'):
            d._visible(row(evidence=[OLD]))

    def test_all_seventy_row_digests_and_consumer_linkage(self):
        n,t=reports()
        self.assertEqual(len(d.checked_rows(n,t)[0]),70)
        out=d.analyze(n,t,{'raw_source_sha256':'abc','raw_tool_sha256':'def'},'x'*64,'y'*40)
        self.assertFalse(out['canonical_gate_pass'])
        self.assertEqual(out['per_variant']['both_exact']['earlier_rule_fully_visible'],10)
        self.assertEqual(out['per_variant']['both_exact']['complete_visible'],10)

    def test_duplicate_or_missing_row_refused(self):
        n,t=reports();n['rows'][0]=copy.deepcopy(n['rows'][1])
        with self.assertRaisesRegex(ValueError,'ROW_IDENTITY'):
            d.checked_rows(n,t)

    def test_modified_row_refused(self):
        n,t=reports();n['rows'][0]['oracle_visible_to_native']=True
        with self.assertRaisesRegex(ValueError,'ROW_DIGEST_MISMATCH'):
            d.checked_rows(n,t)

    def test_oracle_leak_refused_even_with_recomputed_digest(self):
        n,t=reports();n['rows'][0]['oracle_visible_to_native']=True
        x=n['rows'][0];n['row_sha256'][x['fixture']+':'+x['variant']]=d.sha(d.canonical(x))
        with self.assertRaisesRegex(ValueError,'ORACLE_LEAK'):
            d.checked_rows(n,t)

    def test_consumer_hash_refused(self):
        n,t=reports();t['rows'][0]['consumer_messages_sha256']='f'*64
        x=t['rows'][0];t['row_sha256'][x['fixture']+':'+x['variant']]=d.sha(d.canonical(x))
        with self.assertRaisesRegex(ValueError,'CONSUMER_MESSAGES_MISMATCH'):
            d.checked_rows(n,t)

    def test_invalid_zip_hash_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'evidence.zip';p.write_bytes(b'not a zip')
            with self.assertRaisesRegex(ValueError,'ZIP_SIZE_OR_HASH_MISMATCH'):
                d.read_archive(p,'0'*64,'f'*40)


if __name__=='__main__':unittest.main()
