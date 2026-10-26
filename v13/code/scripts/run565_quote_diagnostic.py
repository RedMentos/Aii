#!/usr/bin/env python3
"""Non-promoting frozen STEP2 quote-coverage diagnostic for independently audited safe ZIPs.

This never invokes models, trusts no claimed learning, and does not itself authenticate
Run491 original source; original SHA/frozen-source audits must be completed separately.
"""
import argparse,collections,hashlib,json,re,zipfile
from pathlib import Path

FIELDS=('budget','deadline','local_only','option_A','option_B')
VARIANTS=('b1_only','b2_only','both_none','both_exact','both_control','same_policy_dual','prompt_only_dual')
PATTERNS={
    'budget':re.compile(r'\bBudget\s+\d+\s+euros\b',re.I),
    'deadline':re.compile(r'\bDeadline\s+\d+\s+days\b',re.I),
    'local_only':re.compile(r'\bLocal-only requirement:\s*(?:true|false)\b',re.I),
    'option_A':re.compile(r'\bOption A:\s*cost\s+\d+\s+euros,\s*duration\s+\d+\s+days,\s*local\s+(?:true|false)\b',re.I),
    'option_B':re.compile(r'\bOption B:\s*cost\s+\d+\s+euros,\s*duration\s+\d+\s+days,\s*local\s+(?:true|false)\b',re.I),
}

def sha(data):return hashlib.sha256(data).hexdigest()

def required_rules(fixture):
    history=fixture['history']
    current=fixture['current']
    if not isinstance(history,list) or not isinstance(current,str):
        raise ValueError('MALFORMED_SOURCE')
    past='\n'.join(history)
    rules={}
    for key,pat in PATTERNS.items():
        new=pat.findall(current)
        old=pat.findall(past)
        if len(new)>1 or (not new and len(old)!=1):
            raise ValueError('RULE_MISSING_OR_AMBIGUOUS:'+key)
        if new:rules[key]={'sentence':new[-1],'location':'current'}
        else:rules[key]={'sentence':old[0],'location':'history'}
    return rules

def quote_coverage(analysts,rules):
    if not isinstance(analysts,list):raise ValueError('ANALYSTS_NOT_LIST')
    quotes=[]
    for analyst in analysts:
        if not isinstance(analyst,dict) or not isinstance(analyst.get('verified_quotes'),list):
            raise ValueError('MALFORMED_ANALYST')
        if analyst.get('role') in ('B1_DETAIL','B2_GIST'):
            quotes.extend(analyst['verified_quotes'])
    if any(not isinstance(q,str) for q in quotes):raise ValueError('MALFORMED_QUOTE')
    # Exact source value phrase with a word boundary; not a numeric prefix.
    return {key:any(re.search(re.escape(v['sentence'])+r'(?![\w])',q,re.I) for q in quotes)
            for key,v in rules.items()}

def audit(paths,expected_shas):
    if len(paths)!=3 or len(expected_shas)!=3:raise ValueError('EXACT_THREE_ORIGINAL_BATCHES_REQUIRED')
    report={'schema':'V13_RUN565_FROZEN_STEP2_QUOTE_DIAGNOSTIC_V1',
            'scope':'exploratory original safe ZIPs; separate Run559/560/563 frozen-source audit required',
            'batches':{},'totals':{},'canonical_gate_pass':False,'step2_exit':'UTILITY_FAIL',
            'jepa_weight':0,'redmi_measured':False,'native_inference_performed':False}
    total=collections.defaultdict(lambda:collections.Counter())
    for path,expected in zip(paths,expected_shas):
        p=Path(path)
        if not p.is_file() or p.is_symlink() or len(expected)!=64 or sha(p.read_bytes())!=expected:
            raise ValueError('PINNED_ZIP_SHA_MISMATCH')
        with zipfile.ZipFile(p) as z:
            plans=[n for n in z.namelist() if n.endswith('_BATCH_PLAN.json')]
            if len(plans)!=1:raise ValueError('BATCH_PLAN_COUNT')
            plan=json.loads(z.read(plans[0]));bid=plan['batch_id']
            if bid in report['batches'] or bid not in ('FUTURE_001','FUTURE_002','FUTURE_003'):
                raise ValueError('BATCH_DUPLICATE_OR_OUT_OF_SCOPE')
            counts=collections.defaultdict(lambda:collections.Counter())
            for sid in plan['stage_ids']:
                base='stage_'+sid+'/'
                s=[n for n in z.namelist() if n.startswith(base+'step2_') and n.endswith('.json')]
                t=[n for n in z.namelist() if n.startswith(base+'tool_') and n.endswith('.json')]
                if len(s)!=1 or len(t)!=1:raise ValueError('STAGE_SOURCE_MISSING')
                source=json.loads(z.read(s[0]));tool=json.loads(z.read(t[0]))
                fixtures={f['id']:f for f in source['fixtures']}
                sr={(r['fixture'],r['variant']):r for r in source['rows']}
                if len(sr)!=14 or len(tool['rows'])!=14:raise ValueError('STAGE_ROWS')
                for row in tool['rows']:
                    fid,v=row['fixture'],row['variant']
                    if v not in VARIANTS or fid not in fixtures or (fid,v) not in sr:raise ValueError('ROW_SOURCE')
                    analysts=json.loads(sr[(fid,v)]['consumer_messages'][-1]['content'])['analysts']
                    source_text='\n'.join(fixtures[fid]['history']+[fixtures[fid]['current']])
                    for analyst in analysts:
                        if any(q not in source_text for q in analyst['verified_quotes']):
                            raise ValueError('QUOTE_NOT_IN_FROZEN_SOURCE')
                    rules=required_rules(fixtures[fid]);covered=quote_coverage(analysts,rules)
                    answer=json.loads(row['answer']);action=answer['action']
                    if action not in ('A','B','NONE','UNKNOWN'):raise ValueError('INVALID_ACTION')
                    counts[v]['rows']+=1;counts[v]['action_'+action]+=1
                    for field in FIELDS:
                        counts[v][field+'_quoted']+=int(covered[field])
                        counts[v][field+'_in_current']+=int(rules[field]['location']=='current')
                    counts[v]['all_three_rules_quoted']+=int(all(covered[field] for field in ('budget','deadline','local_only')))
                    counts[v]['all_three_rules_available']+=int(all(covered[field] or rules[field]['location']=='current' for field in ('budget','deadline','local_only')))
                    counts[v]['all_two_options_available']+=int(all(covered[field] or rules[field]['location']=='current' for field in ('option_A','option_B')))
                    counts[v]['all_five_inputs_available']+=int(all(covered[field] or rules[field]['location']=='current' for field in FIELDS))
            if any(counts[v]['rows']!=6 for v in VARIANTS):raise ValueError('BATCH_COVERAGE')
            report['batches'][bid]={v:dict(counts[v]) for v in VARIANTS}
            for v in VARIANTS:total[v].update(counts[v])
    if set(report['batches'])!={'FUTURE_001','FUTURE_002','FUTURE_003'}:raise ValueError('BATCH_SET')
    if any(total[v]['rows']!=18 for v in VARIANTS):raise ValueError('TOTAL_COVERAGE')
    report['totals']={v:dict(total[v]) for v in VARIANTS}
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for i in (1,2,3):
        p.add_argument(f'--safe{i}',required=True);p.add_argument(f'--sha{i}',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args();r=audit([getattr(a,f'safe{i}') for i in (1,2,3)],
                            [getattr(a,f'sha{i}') for i in (1,2,3)])
    out=Path(a.output);out.write_text(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('FROZEN_QUOTE_DIAGNOSTIC_PASS; NO_MODEL; TOTAL_ROWS',sum(v['rows'] for v in r['totals'].values()))
    print('REPORT_SHA256',sha(out.read_bytes()))
if __name__=='__main__':main()
