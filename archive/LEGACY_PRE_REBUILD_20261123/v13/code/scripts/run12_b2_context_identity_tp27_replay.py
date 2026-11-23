"""Post-hoc source-only TP/s27 replay of B2 identity shadow candidate.

Never re-runs native models. Original ZIP is pinned by the shared TP27
visibility verifier. Fixture history text is used solely as a source-backed
read callback; fixture oracle/rules are not read by the candidate.
"""
import argparse
import hashlib
import json
from pathlib import Path

from scripts import step2_tp27_visibility_diagnostic as evidence
from scripts import run12_b2_context_identity_candidate as candidate

SCHEMA='V13_RUN12B_TP27_B2_CONTEXT_IDENTITY_POSTHOC_V1'


def replay(native,tool,receipt):
    rows, _ = evidence.checked_rows(native,tool)
    by_fixture={(r['fixture'],r['variant']):r for r in rows}
    preparations={p['fixture']:p for p in native['preparations']}
    counts={'earlier_rule_fixtures':0,'original_prior_rule_note_in_b2_context':0,
            'candidate_prior_rule_note_in_b2_context':0,'candidate_distractor_selected':0,
            'candidate_source_unavailable':0,'candidate_context_cap_skips':0}
    for fixture in native['fixtures']:
        if fixture['type'] not in ('SPLIT','RULE'):
            continue
        counts['earlier_rule_fixtures'] += 1
        p=preparations[fixture['id']]
        events=p['prior_events'];history=fixture['history']
        if len(events)!=len(history) or len(events)!=3:
            raise ValueError('PRIOR_SOURCE_COUNT')
        sources={};by_event={}
        for event,text in zip(events,history):
            ref=event['source_ref']
            if (len(text)!=ref['char_end']-ref['char_start'] or
                    hashlib.sha256(text.encode()).hexdigest()!=ref['sha256'] or
                    ref['char_start']!=0 or ref['modality']!='text'):
                raise ValueError('HISTORY_SOURCE_HASH')
            sources[ref['source_id']]=text
            by_event[event['event_id']]=ref
        def read_source(ref):
            full=sources[ref['source_id']]
            if hashlib.sha256(full.encode()).hexdigest()!=ref['sha256']:
                raise ValueError('CHANGED_SOURCE')
            if not (0<=ref['char_start']<=ref['char_end']<=len(full)):
                raise ValueError('SOURCE_SPAN')
            return full[ref['char_start']:ref['char_end']]
        prior_offers=[o for o in p['offers'] if o['role']=='B2_GIST']
        if len(prior_offers)!=3:raise ValueError('B2_PREP_OFFERS')
        latest=prior_offers[-1]
        session=p['session'];generation=latest['brain_generation_id'];revision=latest['model_revision']
        retained=[]
        for offer in reversed(prior_offers):
            retained.append({'role':offer['role'],'offer_id':offer['packet_id'],
                             'event_id':offer['event_id'],'session':session,
                             'generation':offer['brain_generation_id'],
                             'model_revision':offer['model_revision'],
                             'source_ref':by_event[offer['event_id']],
                             'hypothesis':offer['offer'].get('summary','')})
        row=by_fixture[(fixture['id'],'both_exact')]
        offers=[o for o in row['offers'] if o['role']=='B2_GIST']
        if len(offers)!=1:raise ValueError('B2_FINAL_OFFER')
        original=offers[0]
        note_ref=events[0]['source_ref'];distractor_ref=events[1]['source_ref']
        counts['original_prior_rule_note_in_b2_context']+=int(any(
            ref['sha256']==note_ref['sha256'] for ref in original.get('context_source_refs',[])))
        selected=candidate.select_context(fixture['current'],row['event']['event_id'],
                                           session,generation,revision,retained,read_source,
                                           cap=native['config']['b2_context_chars'],
                                           slots=native['config']['b2_state_slots'],excerpt_chars=240)
        counts['candidate_prior_rule_note_in_b2_context']+=int(any(
            x['source_ref']['sha256']==note_ref['sha256'] for x in selected['items']))
        counts['candidate_distractor_selected']+=int(any(
            x['source_ref']['sha256']==distractor_ref['sha256'] for x in selected['items']))
        counts['candidate_source_unavailable']+=selected['reasons'].get('SOURCE_UNAVAILABLE',0)
        counts['candidate_context_cap_skips']+=selected['reasons'].get('CAP',0)
    return {'schema':SCHEMA,'scope':'POST_HOC_SOURCE_ONLY_COUNTERFACTUAL_SELECTION_NOT_NATIVE',
            'original_native_source_sha256':receipt['raw_source_sha256'],
            'original_tool_sha256':receipt['raw_tool_sha256'],
            'source_head':evidence.REGISTERED_HEAD,
            'source_zip_sha256':evidence.REGISTERED_ZIP_SHA256,
            'candidate_revision':candidate.REVISION,
            'counts':counts,
            'claim_limits':['Uses original native source/history for offline pointer selection, no model run.',
                            'A selected note is not a B2 quote or C3 decision; no utility improvement is measured.',
                            'No oracle, no weight update, no registered cohort change, no gate promotion.'],
            'canonical_gate_pass':False,'jepa_weight':0,'whole_system_complete':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zip',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    n,t,r=evidence.read_archive(a.zip,evidence.REGISTERED_ZIP_SHA256,evidence.REGISTERED_HEAD)
    report=replay(n,t,r)
    if a.out.exists():raise ValueError('OUTPUT_EXISTS')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_bytes(evidence.canonical(report)+b'\n')
    print(json.dumps({'status':'COUNTERFACTUAL_SOURCE_ONLY','counts':report['counts']},sort_keys=True))

if __name__=='__main__':main()
