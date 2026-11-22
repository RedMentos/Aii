"""WP-AG6 live path end to end: Runtime -> `:growth trainer lora <master>` -> scheduler job growth_consolidate
-> real LoraTrainer (torch, deployed Q4 weights) -> deployed llama.cpp gate -> batch status (PENDING_USER or GATE_FAIL).

  V13_HOME=<installed home> python3 scripts/ag6_live_bench.py --master <HF dir of C3> --out <dir>

The 8 invented facts of scripts/lora_bench.py stand in for replay-passed human memories (candidates() is patched,
the rest of the pipeline is the real one). Nothing is approved or bound; a passing bench batch is rejected afterwards.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from unittest import mock
APP=Path(__file__).resolve().parents[1];sys.path.insert(0,str(APP));sys.path.insert(0,str(APP/'scripts'))
from lora_bench import FACTS  # noqa: E402
from v13.runtime import Runtime  # noqa: E402
from v13.agi import hub,job  # noqa: E402
from v13.agi import trainers  # noqa: E402

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--master',required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--kind',default='lora',choices=['lora','sparse']);ap.add_argument('--cfg',default='{}',help='JSON LoRA overrides, e.g. {"anchor_weight":8}')
    ap.add_argument('--tag',default='');ap.add_argument('--sdft',action='store_true',help='add 2 human corrections as SDFT items (self-taught targets)');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    r=Runtime(Path(os.environ['V13_HOME']))
    try:
        r.cfg['learning_mode']='SHADOW_UPDATE'  # = `:learning shadow` (in memory only; RECORD_ONLY never stages)
        g=hub(r);info=trainers.choose(g,r,a.kind,a.master)
        if a.kind=='lora':info=trainers.set_lora_cfg(g,r,json.loads(a.cfg))
        print('trainer',json.dumps(info),flush=True)
        items=[{'memory_id':'bench_%d'%k,'event_id':'bench_%d'%k,'kind':'fact','prompt':q,'target':t,'answer_keys':keys,
                'source_ref':{'source_id':0,'sha256':'bench','char_start':0,'char_end':len(t),'modality':'text'}} for k,(q,t,keys) in enumerate(FACTS)]
        t0=time.monotonic()
        from v13.drift import Drift,TEACHER_TEMPLATE
        corr=[('What is the name of my dog?','No, my dog is called Bruno.'),('What is my sister\'s job?','She works as a pilot.')] if a.sdft else []
        sdft=[{'item_id':'sdft:bench_%d'%k,'event_id':'sdft_%d'%k,'kind':'fact','student_prompt':q,'teacher_prompt':TEACHER_TEMPLATE.format(question=q,correction=c),
               'target':None,'correction':c,'target_policy':'SELF_TEACHER_IN_CONTEXT','origin':'human_replay',
               'source_ref':{'source_id':0,'sha256':'bench','modality':'text','label':'HUMAN_CORRECTION'}} for k,(q,c) in enumerate(corr)]
        with mock.patch.object(g.weights,'candidates',return_value=items),mock.patch.object(Drift,'sdft_dataset',return_value=sdft):
            out=job(r.sleep,{'action':'growth_consolidate','origin':'USER','payload':{}})
        b=g.weights.batch(out['batch_id'])
        rep={'job':out,'seconds':round(time.monotonic()-t0,1),'trainer_info':info,'status':b['status'],'gate':b['gate'],
             'trainer':{k:v for k,v in (b['trainer'] or {}).items() if k!='metrics'},
             'metrics':{k:v for k,v in ((b['trainer'] or {}).get('metrics') or {}).items() if k not in ('loss_history','history')}}
        (a.out/f'ag6-live-{a.kind}{a.tag}.json').write_text(json.dumps(rep,indent=1,default=str,ensure_ascii=False))
        if b['status']=='PENDING_USER':g.weights.reject(out['batch_id'],'bench')  # never left for approval; reruns train afresh
        print(json.dumps({'status':b['status'],'checks':(b['gate'] or {}).get('checks'),'seconds':rep['seconds']}),flush=True)
    finally:r.close()

if __name__=='__main__':main()
