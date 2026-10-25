"""Run315: source-bound second-turn/forget through actual C3 or explicit fixture.

Native path is a controlled C3-language probe (route_override=simple), not a
full-body/JEPA/Redmi utility proof. The synthetic correction is authored by the
test, not a real user's feedback or a weight-training event.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write, dumps  # noqa: E402
from v13.inputs import last_context  # noqa: E402
from v13.runtime import Runtime  # noqa: E402
from longrun_soak import attach_native_assets  # noqa: E402

QUESTION = 'What is the exact calibration code for fictional Project RUN315-ORBIT?'
CODE = '73194'
GATES = {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE','jepa_weight':0,'V13':'INCOMPLETE'}


def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def wait_idle(runtime, timeout):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        if runtime.idle() and runtime.jobs.empty():return True
        time.sleep(.02)
    return False


def fixture_speaker(runtime):
    """Only for separate local harness tests; NEVER used by native CI."""
    def generate(messages,cancel,deadline,*args,**kwargs):
        prompt=dumps(messages)
        yield CODE if CODE in prompt else 'I do not know.'
    runtime.pool.get=lambda role:SimpleNamespace(role=role,last_metrics={'fixture_only':True},generate=generate,pids=lambda:[])
    runtime.learner.output_delta=lambda *args,**kwargs:None


def context_evidence(store,session):
    ctx=last_context(store,session)
    if not ctx:return {'available':False,'contains_code':None}
    body=dumps(ctx['messages']) if ctx.get('messages') is not None else ctx.get('preview','')
    return {'available':True,'event_id':ctx.get('event_id'),'role':ctx.get('role'),
            'truncated':bool(ctx.get('truncated')),'chars':ctx.get('chars'),
            'sha256':hashlib.sha256(body.encode()).hexdigest(),
            'contains_code':CODE in body if not ctx.get('truncated') else None}


def stage(home, label, native, timeout, memory_id=None, forget=False):
    r=Runtime(home)
    try:
        r.sleep.cycle.set_policy('enabled','off')
        r.cfg.update(route_override='simple',observer_mode='off',memory_embedding='off',
                     duplex_mode='off',history_turns=0,answer_tokens=64,deadline_seconds=90,
                     c3_decode_mode='server')
        r.session=r.store.new_session('Run315 '+label)
        if not native:fixture_speaker(r)
        before=r.memory.recall(QUESTION,r.session)
        t0=time.monotonic();eid=r.submit(QUESTION)
        if not wait_idle(r,timeout):
            r.cancel();wait_idle(r,15)
            raise TimeoutError('Run315 turn did not settle within native deadline')
        elapsed=round(time.monotonic()-t0,3)
        answer=r.last_answer()
        if not answer or answer['event_id']!=eid:raise ValueError('Run315 missing exact terminal answer')
        meta=json.loads(answer['metadata'])
        evidence={'stage':label,'event_id':eid,'status':answer['status'],
                  'answer':answer['text'][:600],'answer_chars':len(answer['text']),
                  'answer_contains_code':CODE in answer['text'],
                  'elapsed_s':elapsed,'context':context_evidence(r.store,r.session),
                  'recalled_before':len(before),'recalled_code':any(m.get('value')==CODE for m in before),
                  'model_revision':meta.get('model_revision'),'model_generated':meta.get('model_generated'),
                  'runner_metrics':meta.get('runner',{}),'context_plan':meta.get('context_plan')}
        if label=='before':
            mid=r.memory.feedback(eid,'fact',CODE,permission='record',scope='global')
            evidence['synthetic_correction_memory_id']=mid
            evidence['memory_source_sha256']=r.store.one('SELECT s.hash FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=?',(mid,))['hash']
        if forget:
            r.memory.forget(memory_id)
            evidence['forgotten_memory_id']=memory_id
            evidence['active_after_forget']=r.store.one('SELECT active FROM memories WHERE id=?',(memory_id,))['active']
        evidence['integrity_errors']=r.store.integrity(True)
        return evidence
    finally:
        r.close()
        if 'evidence' in locals():
            evidence['resident_pids_after_close']=r.pool.pids()+r.needle.pids()


def probe(home,models_from,out,native=True,timeout=140):
    home=Path(home);out=Path(out)
    home.mkdir(parents=True,exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True)
    report={'schema':'V13_RUN315_C3_SECOND_TURN_V1','native':bool(native),
            'evidence_level':'LINUX_NATIVE_C3' if native else 'FIXTURE_ONLY',
            'status':'INCOMPLETE','gates':dict(GATES),'stages':[],
            'source_only':False,'question':QUESTION,'synthetic_correction':CODE,
            'claim_limit':'C3 controlled route; synthetic correction, no native weight learning or Redmi proof'}
    def save():atomic_write(out,(dumps(report)+'\n').encode())
    save()
    try:
        if native:
            if models_from is None:raise ValueError('Native probe requires pinned installed model source')
            attach_native_assets(home,models_from)
            from v13.models import ModelManager
            specs=json.loads((Path(__file__).resolve().parents[1]/'specs/models.json').read_text())
            expected=specs['models']['language']['files'][0]['sha256']
            model=ModelManager(home).path_for('C3_LANGUAGE')
            actual=sha256_file(model)
            report['model']={'id':specs['models']['language']['model_id'],
                             'revision':specs['models']['language']['revision'],
                             'file':Path(model).name,'sha256':actual,'expected_sha256':expected}
            if actual!=expected:raise ValueError('C3 model hash differs from registered spec')
            server=home/'bin/llama-server'
            report['runner_binary_sha256']=sha256_file(server) if server.is_file() else None
            save()
        first=stage(home,'before',native,timeout)
        report['stages'].append(first);save()
        mid=first['synthetic_correction_memory_id']
        second=stage(home,'after_correction',native,timeout,memory_id=mid,forget=True)
        report['stages'].append(second);save()
        third=stage(home,'after_forget',native,timeout)
        report['stages'].append(third);save()
        contexts=[x['context'] for x in report['stages']]
        report['checks']={
            'all_final':all(x['status']=='FINAL' for x in report['stages']),
            'all_native_generated':all(x['model_generated'] is True for x in report['stages']) if native else False,
            'first_context_no_code':contexts[0]['contains_code'] is False,
            'second_context_has_code':contexts[1]['contains_code'] is True,
            'third_context_no_code':contexts[2]['contains_code'] is False,
            'second_source_recalled':second['recalled_code'],
            'third_source_forgotten':not third['recalled_code'],
            'source_revoked':second.get('active_after_forget')==0,
            'integrity_clean':all(not x['integrity_errors'] for x in report['stages']),
            'native_processes_reaped':all(not x['resident_pids_after_close'] for x in report['stages'])}
        report['utility']={'second_exact':second['answer_contains_code'],
                           'after_forget_exact':third['answer_contains_code'],
                           'observed_improvement':not first['answer_contains_code'] and second['answer_contains_code'],
                           'forget_output_nonretention':not third['answer_contains_code']}
        report['integration_pass']=all(report['checks'].values()) if native else all(
            v for k,v in report['checks'].items() if k!='all_native_generated')
        report['utility_pass']=bool(report['integration_pass'] and report['utility']['observed_improvement']
                                    and report['utility']['forget_output_nonretention'])
        report['status']='COMPLETE' if report['integration_pass'] else 'INTEGRATION_FAIL'
        save();return report
    except BaseException as exc:
        report['status']='ERROR';report['error']={'type':type(exc).__name__,'message':str(exc)[:400]}
        save();raise


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--home',required=True);ap.add_argument('--models-from')
    ap.add_argument('--out',required=True);ap.add_argument('--fixture',action='store_true')
    ap.add_argument('--timeout',type=int,default=140)
    args=ap.parse_args()
    result=probe(args.home,args.models_from,args.out,native=not args.fixture,timeout=args.timeout)
    print(dumps({'status':result['status'],'integration_pass':result['integration_pass'],
                 'utility_pass':result['utility_pass'],'native':result['native'],
                 'stages':[(x['stage'],x['status'],x['elapsed_s']) for x in result['stages']]}))
    if not result['integration_pass']:raise SystemExit(2)

if __name__=='__main__':main()
