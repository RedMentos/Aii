"""Synthetic-only offline TP27 candidate replay, no original artifact in CI."""
import copy
import hashlib
import unittest

from scripts import run12_b2_context_identity_tp27_replay as replay
from scripts import step2_tp27_visibility_diagnostic as evidence
from tests.test_step2_tp27_visibility_diagnostic import reports

NOTE='Project F0 kickoff. Budget 134 euros. Deadline 9 days. Local-only requirement: true.'
ATLAS='Project Atlas archive index. No active project rules or supplier prices.'
SHEET='Project F0 supplier sheet. Option A: cost 91 euros, duration 7 days, local true.'
CUR='Project F0. Decide using earlier project rules and the latest supplier sheet.'


def ref(text,n):
    return {'source_id':'src_'+format(n,'032x'),'sha256':hashlib.sha256(text.encode()).hexdigest(),
            'char_start':0,'char_end':len(text),'modality':'text'}


def fixture_reports():
    native,tool=reports()
    for other in native['fixtures'][1:]:other['type']='DETAIL'
    fixture=native['fixtures'][0]
    fixture.update(type='SPLIT',history=[NOTE,ATLAS,SHEET],current=CUR)
    events=[];offers=[]
    for i,text in enumerate(fixture['history']):
        event='evt_'+format(i+1,'032x')
        events.append({'event_id':event,'source_ref':ref(text,i+1)})
        offers.append({'role':'B2_GIST','packet_id':'pkt_'+format(i+1,'032x'),
                       'event_id':event,'brain_generation_id':'g1','model_revision':'m1',
                       'offer':{'summary':'hypothesis'}})
    native['preparations']=[{'fixture':'F0','prior_events':events,'offers':offers,'session':'s1'}]
    native['config']={'b2_context_chars':768,'b2_state_slots':4}
    row=next(r for r in native['rows'] if r['fixture']=='F0' and r['variant']=='both_exact')
    row['event']={'event_id':'evt_current'}
    row['offers']=[{'role':'B2_GIST','context_source_refs':[events[2]['source_ref'],events[1]['source_ref']]}]
    native['row_sha256']['F0:both_exact']=evidence.sha(evidence.canonical(row))
    receipt={'raw_source_sha256':'x'*64,'raw_tool_sha256':'y'*64}
    return native,tool,receipt


class ReplayTests(unittest.TestCase):
    def test_one_synthetic_old_rule_note_recovered(self):
        n,t,r=fixture_reports()
        result=replay.replay(n,t,r)
        self.assertEqual(result['counts']['earlier_rule_fixtures'],1)
        self.assertEqual(result['counts']['original_prior_rule_note_in_b2_context'],0)
        self.assertEqual(result['counts']['candidate_prior_rule_note_in_b2_context'],1)
        self.assertEqual(result['counts']['candidate_distractor_selected'],0)
        self.assertFalse(result['canonical_gate_pass'])

    def test_tampered_prior_source_ref_fails(self):
        n,t,r=fixture_reports()
        n['preparations'][0]['prior_events'][0]['source_ref']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'HISTORY_SOURCE_HASH'):
            replay.replay(n,t,r)

    def test_fixture_oracle_not_read(self):
        n,t,r=fixture_reports()
        expected=replay.replay(n,t,r)
        n['fixtures'][0]['oracle']={'action':'INVALID','secret':'never used'}
        self.assertEqual(expected,replay.replay(n,t,r))


if __name__=='__main__':unittest.main()
