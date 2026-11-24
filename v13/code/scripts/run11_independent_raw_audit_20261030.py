#!/usr/bin/env python3
"""Independent, read-only closure audit of V13 Run11 GitHub Actions ZIPs.

Checks bytes, CRC, exact inner manifest, source/row/gate integrity. A clean
integrity result is NOT a native-utility or STEP2 promotion.
"""
import argparse,collections,hashlib,json,re,sys,zipfile
from pathlib import PurePosixPath,Path

SEED53='7c5da29e274c3d63a34b68baac6ac9b6e31a968d5632b938eff7de01cf2f24d4'
SEED59='610b7b1c2b2d203b6388a7717394cd9c7c8460f434509167286e7bf7a972e651'
B1REV='6767265158422fb8a19c62ceb45f16f05363615b'
B2REV='8fea620810c4afa23dd6443f999a48574c1611a3'
GATES=('step2_gate_promoted','b3_promoted','body_jepa_available','redmi_measured','whole_system_complete')

def require(x,code):
    if not x:raise ValueError(code)

def prompt53(f):
    return (f"Compare options for Project {f['project']}. Budget: {f['budget']} Euro. "
            f"Option {f['a']} costs {f['a_cost']} Euro and takes {f['a_days']} days. "
            f"Option {f['b']} costs {f['b_cost']} Euro and takes {f['b_days']} days. "
            "Both options must be local, no cloud. State the remaining budget "
            "for each named option and briefly explain the time/cost tradeoff.")

def prompt59(f):
    return (f"For {f['project']}, I have a spending ceiling of {f['budget']} Euro. "
            f"{f['a']} uses {f['a_cost']} Euro and needs {f['a_days']} days. "
            f"{f['b']} uses {f['b_cost']} Euro and needs {f['b_days']} days. "
            "Everything stays local on my device; no cloud. How many Euro "
            "would remain after each named choice, and which one finishes sooner?")

def credit(d,key):
    l=d['lexical'][key]['status'];e=d['equation'][key]['status']
    return (l=='CORRECT' and e in ('CORRECT','MISSING')) or (e=='CORRECT' and l in ('CORRECT','MISSING'))

def pilot_audit(z,kind):
    base='pilot/'
    require(base+'report.json' in z.namelist(),'MISSING_PILOT_REPORT')
    j=json.loads(z.read(base+'report.json'))
    if kind=='seed53':
        seed,hash_,n,arms,form=53,SEED53,24,('A_C3_ONLY','B_B1_ONLY','C_B2_ONLY','D_DISTINCT_BOTH','E_SHARED_DUAL_COLD','F_NATIVE_AUTO'),prompt53
        block=6
    else:
        seed,hash_,n,arms,form=59,SEED59,12,('A_FORCED_SIMPLE','B_NATIVE_AUTO','C_FORCED_BOTH'),prompt59
        block=3
    require(j['seed']==seed and j['fixture_sha256']==hash_,'SEED_OR_FIXTURE_CHANGED')
    require(tuple(j['arms'])==arms and len(j['rows'])==n and len(j['fixtures'])==4,'COHORT_SHAPE_CHANGED')
    fixture_hash=hashlib.sha256(json.dumps(j['fixtures'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    require(fixture_hash==hash_,'FIXTURE_BYTES_MISMATCH')
    require(j['learning_mode']=='RECORD_ONLY' and j['jepa_weight']==0,'AGE0_GATE_RED')
    require(all(j[k] is False for k in GATES) and j['comparative_utility_proven'] is False,'PROMOTION_GATE_RED')
    verified=j.get('model_verification',{})
    require(set(verified)=={'needle','language','body','gist'} and all(v=={'ok':True,'hash_checked':True} for v in verified.values()),'MODEL_HASH_PROOF_MISSING')
    totals={a:0 for a in arms};counts=collections.Counter();invalid=[];selected=invoked=0
    for i,row in enumerate(j['rows']):
        f=j['fixtures'][i//block];arm=j['arm_order'][i//block][i%block]
        require(row['index']==i and row['fixture']==f['project'] and row['arm']==arm,'ROW_ORDER_MISMATCH')
        path=f'{base}raw/{i:02d}_{arm}.json'
        require(path in z.namelist(),'MISSING_RAW_ROW_'+str(i))
        raw=json.loads(z.read(path))
        require(raw['index']==i and raw['fixture']==row['fixture'] and raw['arm']==arm,'RAW_ROW_IDENTITY_MISMATCH')
        require(raw['flags']==row['flags'] and raw['score']==row['score'],'RAW_REPORT_MISMATCH')
        s=row['score'];require(type(s['correct']) is int and 0<=s['correct']<=2,'BAD_SCORE_RANGE')
        require(s['correct']==int(s['a'])+int(s['b']),'SCORE_TOTAL_MISMATCH')
        totals[arm]+=s['correct'];counts[arm]+=1
        valid=row['flags'].get('valid_native') is True
        if not valid:invalid.append(i)
        if 'raw_audit' not in raw:
            require(not valid and 'error_type' in raw and s['correct']==0,'UNPROVEN_ROW_CREDITED')
            continue
        require(raw['prompt']==form(f),'SOURCE_PROMPT_CHANGED')
        a=raw['raw_audit']
        require(a['event_id']==row['event_id'] and a['output']==row['final_output'],'SOURCE_OUTPUT_BINDING_MISMATCH')
        require(raw['learning_mode']=='RECORD_ONLY' and raw['jepa_weight']==0 and all(raw[k] is False for k in GATES),'RAW_PROMOTION_GATE_RED')
        require(raw['b1_model_key']=='body','B1_MODEL_KEY_CHANGED')
        if kind=='seed53' and arm=='E_SHARED_DUAL_COLD':
            require(raw['b2_control']=='shared_body_dual_state' and raw['b2_model_key']=='body','SHARED_BODY_CONTROL_CHANGED')
            require(raw['b2_revision']==raw['b1_revision'],'SHARED_BODY_REVISION_CHANGED')
        else:
            require(raw['b2_control']=='two_body' and raw['b2_model_key']=='gist','DISTINCT_BODY_CONTROL_CHANGED')
        if arm in ('A_C3_ONLY','A_FORCED_SIMPLE'):
            require(raw['b1_revision']=='unavailable' and raw['b2_revision']=='unavailable','C3_ONLY_MODEL_NOT_UNINSTALLED')
        elif kind=='seed53' and arm=='E_SHARED_DUAL_COLD':
            require(raw['b1_revision']==B1REV and raw['b2_revision']==B1REV,'SHARED_MODEL_REVISION_CHANGED')
        else:
            require(raw['b1_revision']==B1REV and raw['b2_revision']==B2REV,'DISTINCT_MODEL_REVISION_CHANGED')
        if valid:
            require(a['source_errors']==[] and a['checks'] and all(v is True for v in a['checks'].values()),'SOURCE_CHECKS_RED')
            require(row['flags']['process_release_valid'] is True,'PROCESS_RELEASE_RED')
            require(all(bool(s[key])==credit(s,key) for key in ('a','b')),'SCORE_PARSER_VETO_MISMATCH')
        if arm in ('F_NATIVE_AUTO','B_NATIVE_AUTO'):
            invoked+=int(row['flags']['native_c2_invocation']);selected+=int(row['flags']['native_c2_selected'])
            if row['flags']['native_c2_invocation']:
                require(raw['native_c2_process_reaped'] is True,'NEEDLE_NOT_REAPED')
                require(type(raw['native_c2_pid']) is int and raw['route_info']['native_control_metrics']['memory']['pid']==raw['native_c2_pid'],'NEEDLE_PID_MISMATCH')
                ctx=raw['context_packet']
                require(ctx['event_id']==row['event_id'] and ctx['session_id']==row['session_id'] and ctx['external_action_authority'] is False,'C2_CONTEXT_BINDING_RED')
    require(all(counts[a]==4 for a in arms),'ARM_COUNT_MISMATCH')
    require(j['score_totals_out_of_8']==totals,'TOTAL_SCORE_MISMATCH')
    require(j['native_c2_invocations']==invoked and j['native_c2_selected']==selected,'C2_COUNTS_MISMATCH')
    complete=len(invalid)==0
    require(j['status']==('PILOT_COMPLETE_NO_GATE' if complete else 'PILOT_PARTIAL_RED'),'PILOT_STATUS_MISMATCH')
    return {'status':j['status'],'score_totals_out_of_8':totals,'invalid_rows':invalid,'native_c2_invocations':invoked,'native_c2_selected':selected,'native_pilot_complete':complete,'step2_promoted':False}

def audit(path,expected_sha,kind):
    b=Path(path).read_bytes();sha=hashlib.sha256(b).hexdigest()
    require(sha==expected_sha,'OUTER_SHA256_MISMATCH')
    with zipfile.ZipFile(path) as z:
        require(z.testzip() is None,'ZIP_CRC_RED')
        names=z.namelist();require(len(names)==len(set(names)),'DUPLICATE_ZIP_MEMBER')
        for name in names:
            p=PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts and not name.startswith('/'),'ZIP_PATH_TRAVERSAL')
        require('SHA256SUMS' in names,'MISSING_INNER_MANIFEST')
        entries={}
        for line in z.read('SHA256SUMS').decode().splitlines():
            want,name=line.split('  ',1);name=name.removeprefix('./')
            require(name not in entries and re.fullmatch(r'[0-9a-f]{64}',want),'BAD_INNER_MANIFEST')
            entries[name]=want
        require(set(entries)==set(names)-{'SHA256SUMS'},'INNER_MANIFEST_NOT_CLOSED')
        for name,want in entries.items():
            require(hashlib.sha256(z.read(name)).hexdigest()==want,'INNER_SHA256_MISMATCH_'+name)
        exits={name[:-9]:z.read(name).decode().strip() for name in names if name.endswith('_EXIT.txt')}
        result={'kind':kind,'sha256':sha,'bytes':len(b),'crc':'CLEAN','inner_sha256':f'{len(entries)}/{len(entries)}','stage_exits':exits,'integrity':'CLEAN','native_or_gate_promotion':False}
        if kind in ('seed53','seed59'):
            result.update(pilot_audit(z,kind))
        elif kind=='fullsuite':
            raw=z.read('FULL_RAW.log').decode(errors='replace')
            m=re.findall(r'(?m)^Ran (\d+) tests in [^\n]+',raw)
            require(len(m)==1,'FULLSUITE_COUNT_MISSING')
            result.update(tests=int(m[0]),errors=re.findall(r'(?m)^ERROR: ([^\n]+)',raw),failures=re.findall(r'(?m)^FAIL: ([^\n]+)',raw),skipped=re.findall(r'(?m)^FAILED \(([^\n]+)\)',raw))
        elif kind=='preflight':
            raw=z.read('TEST_RAW.log').decode(errors='replace')
            m=re.findall(r'(?m)^Ran (\d+) tests in [^\n]+',raw)
            require(len(m)==1,'TEST_COUNT_MISSING')
            result['tests']=int(m[0])
        return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zip',required=True)
    p.add_argument('--expected-sha256',required=True)
    p.add_argument('--kind',choices=('preflight','fullsuite','seed53','seed59'),required=True)
    a=p.parse_args()
    try:print(json.dumps(audit(a.zip,a.expected_sha256,a.kind),sort_keys=True,indent=2));return 0
    except Exception as e:
        print(json.dumps({'integrity':'RED','error_type':type(e).__name__,'error':str(e),'native_or_gate_promotion':False},sort_keys=True),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())