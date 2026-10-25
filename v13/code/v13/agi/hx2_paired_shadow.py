"""WP-HX2 same-task blinded holdout comparison, read-only SHADOW orchestration.

Reference, guided harness and unguided control get the identical task and seed.
Existing HX4 blind_select judges each pair twice in reversed order. No live
harness consumer, no gate promotion; real-model evaluation is separate.
"""
import math
from ..common import digest,dumps
from .blind_select import blind_select,verify

REVISION='hx2-paired-shadow-v1'
ARMS=('reference','guided','unguided')
PAIRS=(('guided','reference'),('unguided','reference'),('guided','unguided'))
GROUPS=('general','domain')
MAX_TASKS=64
MAX_PROMPT=2000
MAX_OUTPUT=4000


def _lower95(wins,losses):
    n=wins+losses
    if not n:return None
    p=wins/n;z=1.6448536269514722  # one-sided Wilson lower 95%
    return round((p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/(1+z*z/n),6)


def _validate(tasks):
    if not isinstance(tasks,(list,tuple)) or not 1<=len(tasks)<=MAX_TASKS:
        raise ValueError('1..64 holdout tasks required')
    seen=set()
    for t in tasks:
        if not isinstance(t,dict) or not isinstance(t.get('id'),str) or not t['id'] or len(t['id'])>80:
            raise ValueError('stable task id required')
        if t['id'] in seen:raise ValueError('duplicate task id')
        seen.add(t['id'])
        if t.get('split')!='holdout' or t.get('group') not in GROUPS:
            raise ValueError('holdout group must be general|domain')
        if not isinstance(t.get('prompt'),str) or not t['prompt'].strip() or len(t['prompt'])>MAX_PROMPT:
            raise ValueError('bounded prompt required')


def _counts():return {'wins':0,'losses':0,'ties':0,'inconsistent':0,'no_pick':0,'lower95':None}


def compare(tasks,generate,judge,seed=0):
    """generate(prompt, arm, same_seed)->text; judge(task, anonymous_items)->label.

    Calls are sequential. The returned audit contains only hashes, not prompt or
    generated text. Any failed generation leaves the experiment INCOMPLETE.
    """
    _validate(tasks)
    axes={g:{f'{a}_vs_{b}':_counts() for a,b in PAIRS} for g in GROUPS}
    rows=[];incomplete=False
    for task in tasks:
        task_seed=int(digest(dumps({'revision':REVISION,'seed':seed,'task_id':task['id']}))[:15],16)
        row={'id':task['id'],'group':task['group'],'split':'holdout',
             'prompt_sha256':digest(task['prompt']),'seed':task_seed,'pairs':{}}
        outputs={}
        try:
            for arm in ARMS:
                out=generate(task['prompt'],arm,task_seed)
                if not isinstance(out,str) or not out or len(out)>MAX_OUTPUT:
                    raise ValueError('invalid model output')
                outputs[arm]=out
        except Exception as exc:
            row['status']='GENERATION_ERROR';row['error']=type(exc).__name__
            rows.append(row);incomplete=True;continue
        row['output_sha256']={arm:digest(out) for arm,out in outputs.items()}
        for a,b in PAIRS:
            key=f'{a}_vs_{b}';stat=axes[task['group']][key]
            if outputs[a]==outputs[b]:
                stat['ties']+=1;row['pairs'][key]={'status':'TIE','verified':True}
                continue
            sel=blind_select([{'origin':a,'output':outputs[a]},{'origin':b,'output':outputs[b]}],
                             lambda items:judge(task,items),seed=f'{task_seed}:{key}',rounds=2)
            if not verify(sel):
                incomplete=True;row['pairs'][key]={'status':'INVALID_COMMITMENT','verified':False};continue
            pick=sel['pick_origin']
            if sel['status']=='PICKED':
                stat['wins' if pick==a else 'losses']+=1
            elif sel['status']=='INCONSISTENT':stat['inconsistent']+=1
            else:stat['no_pick']+=1
            row['pairs'][key]={'status':sel['status'],'winner':pick,'verified':True,
                               'commitment':sel['commitment'],'reveal':sel['reveal']}
        row['status']='COMPARED';rows.append(row)
    for group in GROUPS:
        for a,b in PAIRS:
            s=axes[group][f'{a}_vs_{b}'];s['lower95']=_lower95(s['wins'],s['losses'])
    # Diagnostic only: never an HX2 PASS, even with a synthetic strong signal.
    signal=all((axes[g][key]['wins']+axes[g][key]['losses']>=20 and
                axes[g][key]['lower95'] is not None and axes[g][key]['lower95']>.5)
               for g in GROUPS for key in ('guided_vs_reference','guided_vs_unguided'))
    return {'revision':REVISION,'status':'INCOMPLETE' if incomplete else 'COMPARED',
            'gate':'UNVERIFIED','claim_limit':'SYNTHETIC_OR_SOFTWARE_ONLY',
            'signal':'SYNTHETIC_DIAGNOSTIC_ONLY' if signal and not incomplete else 'NOT_SUPPORTED_OR_UNMEASURED',
            'axes':axes,'rows':rows,'n':len(tasks),'live_consumer':False}
