"""WP-AG1 teacher backends: who answers TeacherDistillation requests.

- 'local'  : the TEACHER role in the runner pool (an imported bigger GGUF, or `use_reference` of a
             frozen body). Needs `:teacher on` (cfg teacher_enabled) and an installed teacher model.
- 'claude' : Claude through the official Anthropic Python SDK. kind='cloud', so TeacherDistillation
             refuses it until the user allows cloud (`:growth teacher cloud on`); the prompt leaves the phone.
             Key: V13_SECRET_ANTHROPIC_API_KEY (same secret-handle convention as transaction.py) or the
             SDK's own resolution (ANTHROPIC_API_KEY / `ant auth login`). Without the SDK: Unavailable.
Both return {'answer','reasoning','model'}; traces stay REFERENCE_NOT_FACT (teacher.py).
"""
import os
import re
import time
from ..common import Unavailable

SYS=('You are the teacher of a small on-device language model. Answer the question correctly and concisely. '
     'Reply in exactly this form:\nANSWER: <the final answer>\nREASONING: <at most five short sentences why>')
CLAUDE_MODEL='claude-opus-5-5'
CLAUDE_EFFORT='high'
SECRET='V13_SECRET_ANTHROPIC_API_KEY'
FULFIL_LIMIT=8

def split(text):
    t=(text or '').strip()
    m=re.search(r'ANSWER:\s*(.*?)(?:\n\s*REASONING:\s*(.*))?$',t,re.S)
    if not m:return t,''
    return m.group(1).strip(),(m.group(2) or '').strip()

def local_backend(runtime,deadline_s=None):
    def backend(prompt):
        if not runtime.cfg.get('teacher_enabled'):raise Unavailable(':teacher on zuerst')
        runner=runtime.pool.get('TEACHER');text=''
        dl=time.monotonic()+(deadline_s or runtime.cfg.get('deadline_seconds',120))
        for tok in runner.generate([{'role':'system','content':SYS},{'role':'user','content':prompt}],runtime.cancel_event,dl,max_tokens=384):text+=tok
        a,r=split(text)
        return {'answer':a,'reasoning':r,'model':'local:'+runtime.models.revision('TEACHER')}
    return backend

def claude_backend(model=CLAUDE_MODEL,effort=CLAUDE_EFFORT,client=None):
    """client is injectable for tests; default is anthropic.Anthropic()."""
    def backend(prompt):
        c=client
        if c is None:
            try:import anthropic
            except ImportError:raise Unavailable('Anthropic-SDK fehlt: pip install anthropic') from None
            key=os.environ.get(SECRET)
            c=anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        resp=c.beta.messages.create(model=model,max_tokens=16000,system=SYS,output_config={'effort':effort},
                                    betas=['server-side-fallback-2026-07-01'],fallbacks='default',
                                    messages=[{'role':'user','content':prompt}])
        if resp.stop_reason=='refusal':
            cat=getattr(getattr(resp,'stop_details',None),'category',None)
            raise Unavailable('Lehrer hat abgelehnt'+(f' ({cat})' if cat else ''))
        text=''.join(b.text for b in resp.content if getattr(b,'type',None)=='text')
        a,r=split(text)
        return {'answer':a,'reasoning':r,'model':getattr(resp,'model',model)}
    return backend

def register(growth,runtime):
    t=growth.teacher
    if 'local' not in t.backends:t.register('local',local_backend(runtime),'local')
    if 'claude' not in t.backends:t.register('claude',claude_backend(),'cloud')

def preferred(growth,runtime):
    """Local first (nothing leaves the phone); Claude only when cloud is allowed and no local teacher is usable."""
    try:
        if runtime.cfg.get('teacher_enabled'):runtime.models.path_for('TEACHER');return 'local'
    except Exception:pass
    return 'claude' if growth.teacher.box.load()[0]['cloud_allowed'] else None

def fulfil_open(growth,runtime,backend=None,cancel=None,limit=FULFIL_LIMIT):
    """Scheduler job growth_teacher: answer up to `limit` open requests, oldest first."""
    register(growth,runtime)
    name=backend or preferred(growth,runtime)
    if name is None:return {'status':'NO_TEACHER','done':0}
    if name not in growth.teacher.backends:raise ValueError('Lehrer: '+'|'.join(growth.teacher.backends))
    st=growth.teacher.box.load()[0]
    open_=sorted((r for r in st['requests'].values() if r['status']=='OPEN'),key=lambda r:r['created'])[:limit]
    done=0;errors=[];denied=0
    for r in open_:
        if cancel is not None and cancel.is_set():return {'status':'INTERRUPTED','backend':name,'done':done,'errors':errors}
        try:
            tr=growth.teacher.fulfil(r['id'],name,cancel)
            if tr is None:denied+=1
            else:done+=1
        except Exception as exc:errors.append({'request':r['id'],'error':type(exc).__name__+': '+str(exc)[:160]})
    return {'status':'DONE','backend':name,'done':done,'denied_cloud':denied,'errors':errors,'left':max(0,len(open_)-done-denied-len(errors))}
