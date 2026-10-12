"""WP-K / IH-H12, IH-H13, IH-H14, IH-H29, §6.4, §11.1-11.2, §72: action transaction, output commit point, provisional buffer.

IH-H14 action transaction    PREPARED -> COPY_COMMITTED -> EXECUTING -> SUCCEEDED | FAILED | UNKNOWN | CANCELLED.
                             ActionIntent + CorollaryCopy and the COPY_COMMITTED state are written in one SQLite
                             transaction *before* the side effect starts. EXECUTING is persisted before the executor
                             runs, so a crash leaves EXECUTING, which recover() turns into UNKNOWN and never re-runs.
                             An idempotency key deduplicates repeated requests. Reversible tools may carry an undo.
IH-H29 tool security         model/skill candidate -> typed schema -> capability (user enabled) -> risk/reversibility
                             -> human confirmation if required -> ActionIntent -> C5 authorization -> executor.
                             Arguments are typed values (no shell strings); tool names live in their own namespace
                             (never ':'-commands). Secrets are handles {'$secret': NAME}; the value is read from the
                             environment (V13_SECRET_<NAME>) only inside the executor and is scrubbed from result,
                             error, logs and state.
IH-H12 output commit point   DRAFT -> OUTPUT_COMMITTED (first visible byte) -> STREAMING -> FINAL. Before the commit a
                             candidate may be replaced; after it, late evidence may only add a separate correction
                             message, never rewrite the transcript.
IH-H13 provisional buffer    PROVISIONAL items are a TTL scratch buffer, never the authoritative store and never a
                             learning source. At FINAL they are promoted through a registered sink, on revision or a
                             non-FINAL end they are tombstoned (§72 provisional_weight_learning = 0).
"""
import hashlib
import json
import os
import re
import time
from .common import dumps,uid,now
from .contracts import packet,validate

KEY='K_ACTION_TX';REVISION='k-action-tx-v1'
STATES=('PREPARED','COPY_COMMITTED','EXECUTING','SUCCEEDED','FAILED','UNKNOWN','CANCELLED')
TERMINAL={'SUCCEEDED','FAILED','UNKNOWN','CANCELLED'}
NEXT={'PREPARED':{'COPY_COMMITTED','CANCELLED'},'COPY_COMMITTED':{'EXECUTING','CANCELLED'},'EXECUTING':{'SUCCEEDED','FAILED','UNKNOWN'}}
HISTORY=128;IDEM_MAX=512;STALE_PREPARED_S=3600.;PREVIEW_CHARS=200
NAME=re.compile(r'^[a-z][a-z0-9_]{1,31}$')
SHELLISH=re.compile(r'[;&|`$<>]|\b(rm|sudo|curl|wget|chmod|sh|bash)\b')
ARG_TYPES={'str':str,'int':int,'float':(int,float),'bool':bool,'secret':dict,'text':str}  # 'text': quoted source data for pure READ_LOCAL functions, never passed to a shell (WP-W2c)
CONFIRM_ALWAYS={'WRITE_LOCAL','NETWORK','EXTERNAL_EFFECT'}
EVENT={'provisional_gain':.65,'provisional_memory_write':.20,'provisional_weight_learning':0.,
       'final_gain':1.,'final_memory_write':.90,'final_learning_eligibility':.80}   # §72 BOOT
PROVISIONAL_KEY='K_PROVISIONAL';PROVISIONAL_REVISION='k-provisional-v1';PROVISIONAL_TTL_S=900.;PROVISIONAL_MAX=256

def sha(x):return hashlib.sha256(dumps(x).encode()).hexdigest()

# -- IH-H29 contract --------------------------------------------------------------------------------------------
def valid_name(name):
    if not isinstance(name,str) or not NAME.match(name):raise ValueError('Werkzeugname: nur [a-z0-9_], kein Operator-Namensraum')
    return name

def check_args(schema,args):
    """Typed schema validation. Returns a list of violations (empty = ok)."""
    v=[]
    if not isinstance(args,dict):return ['args_not_object']
    if schema is None:  # legacy spec without schema: scalar values only, strings without shell syntax
        schema={k:('bool' if isinstance(a,bool) else 'float' if isinstance(a,(int,float)) else 'secret' if isinstance(a,dict) else 'str') for k,a in args.items()}
    for k in args:
        if k not in schema:v.append('unexpected_arg:'+str(k)[:32])
    for k,t in schema.items():
        opt=t.endswith('?');t=t.rstrip('?')
        if k not in args:
            if not opt:v.append('missing_arg:'+k)
            continue
        a=args[k]
        if t=='secret':
            if not (isinstance(a,dict) and set(a)=={'$secret'} and isinstance(a['$secret'],str) and NAME.match(a['$secret'].lower())):v.append('secret_handle:'+k)
            continue
        if isinstance(a,bool) and t!='bool' or not isinstance(a,ARG_TYPES[t]):v.append('type:'+k);continue
        if isinstance(a,str) and len(a)>4000:v.append('unsafe_arg:'+k)
        elif isinstance(a,str) and t!='text' and SHELLISH.search(a):v.append('unsafe_arg:'+k)
    return v

def secrets_in(args):return {k:a['$secret'] for k,a in (args or {}).items() if isinstance(a,dict) and set(a)=={'$secret'}}
def resolve(args):
    out={};values=[]
    for k,a in args.items():
        if isinstance(a,dict) and set(a)=={'$secret'}:
            val=os.environ.get('V13_SECRET_'+a['$secret'].upper())
            if val is None:raise PermissionError('Secret-Handle nicht gesetzt: '+a['$secret'])
            out[k]=val;values.append(val)
        else:out[k]=a
    return out,values
def scrub(x,values):
    if not values:return x
    s=dumps(x)
    for v in values:
        if v:s=s.replace(json.dumps(v)[1:-1],'[REDACTED]')
    return json.loads(s)

def authorize(spec,args,origin,enabled,age_ok,confirmed=False):
    """IH-H29 pipeline up to C5 authorization. Returns (decision, reason, steps); decision APPROVED|PROPOSED|DENIED."""
    steps=[]
    bad=check_args(getattr(spec,'schema',None),args);steps.append(['schema',not bad])
    if bad:return 'DENIED','SCHEMA:'+','.join(bad[:4]),steps
    steps.append(['capability',enabled])
    if not enabled:return 'DENIED','TOOL_NOT_ENABLED_BY_USER',steps
    need=spec.risk in CONFIRM_ALWAYS or not spec.reversible;steps.append(['risk',spec.risk+('' if spec.reversible else '+IRREVERSIBLE')])
    if need and not confirmed:steps.append(['confirmation',False]);return 'PROPOSED','NEEDS_PER_CALL_APPROVAL',steps
    steps.append(['confirmation',True if need else 'not_required'])
    steps.append(['c5',age_ok or confirmed])
    if not (age_ok or confirmed):return 'DENIED','AGE_RIGHT:'+spec.right,steps
    return 'APPROVED','USER_APPROVED' if confirmed else 'POLICY',steps

# -- IH-H14 transaction -----------------------------------------------------------------------------------------
class Transactions:
    def __init__(self,store,clock=time.time):self.s=store;self.clock=clock
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st={'revision':REVISION,'tx':{},'idem':{},'counts':{}}
        if st.get('revision')!=REVISION:raise ValueError('Action transaction state revision mismatch')
        return st,v
    def _write(self,fn,packets=()):
        """One SQLite transaction: packets + state (optimistic version), so the copy precedes any side effect."""
        for p in packets:validate(p[0],p[1])
        for attempt in (0,1):
            st,v=self._load();out=fn(st);self._trim(st);payload=dumps(st)
            try:
                with self.s.tx() as c:
                    r=c.execute("SELECT version FROM states WHERE key=?",(KEY,)).fetchone();cur=r[0] if r else 0
                    if cur!=v:raise ValueError('Stale state write')
                    for kind,p in packets:c.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)",(p['packet_id'],kind,p['event_id'],p['brain_generation_id'],dumps(p),now()))
                    c.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)",(KEY,v+1,payload))
                return out
            except ValueError:
                if attempt:raise
    @staticmethod
    def _trim(st):
        done=[k for k,t in st['tx'].items() if t['state'] in TERMINAL]
        for k in sorted(done,key=lambda k:st['tx'][k]['updated'])[:max(0,len(done)-HISTORY)]:del st['tx'][k]
        if len(st['idem'])>IDEM_MAX:
            for k in list(st['idem'])[:len(st['idem'])-IDEM_MAX]:del st['idem'][k]
    def _move(self,st,tid,state,**extra):
        t=st['tx'][tid]
        if state not in NEXT.get(t['state'],()):raise ValueError('Übergang '+t['state']+' -> '+state+' unzulässig')
        t.update(state=state,updated=self.clock(),**extra);t['trail'].append([state,round(self.clock(),3)])
        st['counts'][state]=st['counts'].get(state,0)+1;return t
    def get(self,tid):return self._load()[0]['tx'].get(tid)
    def prepare(self,event_id,tool,args,origin,risk,reversible,idempotency_key=None,intent=None):
        def fn(st):
            if idempotency_key and idempotency_key in st['idem'] and st['idem'][idempotency_key] in st['tx']:
                return dict(st['tx'][st['idem'][idempotency_key]],deduplicated=True)
            tid=uid('atx')
            st['tx'][tid]={'id':tid,'event_id':event_id or 'operator','tool':tool,'args':args,'args_sha256':sha(args),'origin':origin,'risk':risk,
                           'reversible':bool(reversible),'intent':intent,'state':'PREPARED','created':self.clock(),'updated':self.clock(),
                           'trail':[['PREPARED',round(self.clock(),3)]],'idempotency_key':idempotency_key,'result':None,'error':None,'undo':None,'undone':False}
            if idempotency_key:st['idem'][idempotency_key]=tid
            st['counts']['PREPARED']=st['counts'].get('PREPARED',0)+1
            return dict(st['tx'][tid])
        return self._write(fn)
    def commit_copy(self,tid,expected=None):
        """ActionIntent + CorollaryCopy and COPY_COMMITTED in one write, before the external effect (IH-H14)."""
        t=self.get(tid);gen=self.s.generation_id
        intent=packet('ActionIntent','C5_ACTION_TX',t['event_id'],gen,[],action_id=tid,action_type='TOOL_CALL:'+t['tool'],permission=t['risk'])
        copy=packet('CorollaryCopy','F3_SELF',t['event_id'],gen,[],action_id=tid,expected=dict(expected or {},tool=t['tool'],args_sha256=t['args_sha256']),self_caused=True)
        return self._write(lambda st:dict(self._move(st,tid,'COPY_COMMITTED',intent_packet=intent['packet_id'],corollary_packet=copy['packet_id'])),
                           [('ActionIntent',intent),('CorollaryCopy',copy)])
    def execute(self,tid,fn):
        """Persist EXECUTING, run the side effect, persist the outcome. Returns the final transaction."""
        self._write(lambda st:self._move(st,tid,'EXECUTING'))
        t=self.get(tid);start=time.monotonic();values=[];undo=None
        try:
            args,values=resolve(t['args'])
            res=fn(**args)
            if isinstance(res,tuple) and len(res)==2 and isinstance(res[1],dict) and res[1].get('__undo__'):res,undo=res[0],res[1]
            try:dumps(res)
            except Exception:res=repr(res)[:500]
            state,result,error='SUCCEEDED',scrub(res,values),None
        except Exception as exc:
            state,result,error='FAILED',None,scrub(type(exc).__name__+': '+str(exc)[:200],values)
        dur=round(time.monotonic()-start,6)
        out=packet('ActionOutcome','C6_TOOL',t['event_id'],self.s.generation_id,[],action_id=tid,status=state,actual={'duration_s':dur,'error':error,'result_sha256':sha(result)})
        return self._write(lambda st:dict(self._move(st,tid,state,result=result,error=error,duration_s=dur,undo=undo)),[('ActionOutcome',out)])
    def cancel(self,tid,reason='CANCELLED_BY_USER'):return self._write(lambda st:dict(self._move(st,tid,'CANCELLED',error=reason)))
    def undo(self,tid,undo_fn):
        """Compensating action for a reversible SUCCEEDED transaction (its own transaction record)."""
        t=self.get(tid)
        if not t or t['state']!='SUCCEEDED' or not t['reversible'] or not t.get('undo') or t['undone']:raise ValueError('Nicht rücknehmbar')
        u=self.prepare(t['event_id'],t['tool']+'.undo',{'of':tid},'USER','WRITE_LOCAL',False);self.commit_copy(u['id'],{'undo_of':tid})
        res=self.execute(u['id'],lambda of:undo_fn(t['undo']))
        if res['state']=='SUCCEEDED':
            def fn(st):st['tx'][tid]['undone']=True;st['tx'][tid]['updated']=self.clock()
            self._write(fn)
        return res
    def recover(self):
        """After a crash: EXECUTING -> UNKNOWN (never re-run blindly); stale PREPARED/COPY_COMMITTED -> CANCELLED."""
        def fn(st):
            n={'UNKNOWN':0,'CANCELLED':0}
            for tid,t in list(st['tx'].items()):
                if t['state']=='EXECUTING':self._move(st,tid,'UNKNOWN',error='CRASH_DURING_EXECUTION_NOT_RETRIED');n['UNKNOWN']+=1
                elif t['state'] in ('PREPARED','COPY_COMMITTED') and self.clock()-t['created']>STALE_PREPARED_S:self._move(st,tid,'CANCELLED',error='STALE_AFTER_RESTART');n['CANCELLED']+=1
            return n
        return self._write(fn)
    def report(self):
        st,_=self._load()
        return {'revision':REVISION,'counts':st['counts'],'open':[{k:t[k] for k in ('id','tool','state','origin','risk')} for t in st['tx'].values() if t['state'] not in TERMINAL],
                'recent':[{k:t.get(k) for k in ('id','tool','state','origin','risk','undone','error')} for t in sorted(st['tx'].values(),key=lambda t:t['updated'])[-8:]],
                'claim_limit':'Only registered typed tools run; EXECUTING after a crash becomes UNKNOWN and is never repeated'}

# -- first WRITE_LOCAL tool: a sandboxed note file with undo ----------------------------------------------------------
def sandbox_note_tool(home):
    """(fn, risk, reversible, right, description, schema, undo, preview) for ToolSpec: writes only <home>/data/tool_sandbox/<name>.txt."""
    from pathlib import Path
    from .common import atomic_write
    root=Path(home)/'data'/'tool_sandbox'
    def path(name):
        if not NAME.match(name):raise ValueError('Notizname: nur [a-z0-9_]')
        return root/(name+'.txt')
    def write(name,text):
        p=path(name);old=p.read_text() if p.exists() else None
        atomic_write(p,text.encode());return {'written':name,'chars':len(text)},{'__undo__':True,'name':name,'previous':old}
    def undo(u):
        p=path(u['name'])
        if u['previous'] is None:p.unlink(missing_ok=True)
        else:atomic_write(p,u['previous'].encode())
        return {'restored':u['name']}
    def preview(name,text):
        """WP-T7 dry run: what the write would change, without touching the file system."""
        p=path(name);old=p.read_text() if p.exists() else None
        return {'effect':'REPLACE' if old is not None else 'CREATE','target':'data/tool_sandbox/'+name+'.txt','sandbox':True,'reversible':True,
                'old_chars':None if old is None else len(old),'new_chars':len(text),'old_head':None if old is None else old[:PREVIEW_CHARS],'new_head':text[:PREVIEW_CHARS],
                'unchanged':old==text}
    return write,'WRITE_LOCAL',True,'simple_tool_choice','Notiz im Sandbox-Ordner schreiben (rücknehmbar)',{'name':'str','text':'str'},undo,preview

# -- IH-H12 output commit point ---------------------------------------------------------------------------------
def commit_output(store,mid,event_id,meta=None):
    """DRAFT -> OUTPUT_COMMITTED right before the first visible byte reaches the user. Idempotent."""
    with store.tx() as c:moved=c.execute("UPDATE messages SET status='OUTPUT_COMMITTED' WHERE id=? AND status='DRAFT'",(mid,)).rowcount==1
    if moved and meta is not None:meta['output_committed_monotonic_ns']=time.monotonic_ns();meta['output_committed']=True
    return moved

def correction(store,session,event_id,mid,text,reason,refs=None):
    """Late evidence after the commit point: a separate, visible correction; the committed transcript stays as it was."""
    row=store.one("SELECT status FROM messages WHERE id=?",(mid,))
    if not row:raise ValueError('Unbekannte Nachricht')
    if row['status'] in ('DRAFT',):raise ValueError('Vor dem Commit-Punkt wird ersetzt, nicht korrigiert')
    return store.message(session,event_id,'assistant',text,'FINAL',{'correction_of':mid,'reason':reason,'late_evidence_refs':refs or [],'output_authority':'LATE_CORRECTION'})

# -- IH-H13 provisional buffer ----------------------------------------------------------------------------------
SINKS={}   # kind -> callable(payload); registered in-process by producers (the buffer itself is ephemeral)

def learning_factor(finality):return EVENT['final_learning_eligibility'] if finality=='FINAL' else EVENT['provisional_weight_learning']

class Provisional:
    def __init__(self,store,clock=time.time):self.s=store;self.clock=clock
    def _load(self):
        st,v=self.s.state(PROVISIONAL_KEY,None)
        if st is None:st={'revision':PROVISIONAL_REVISION,'items':{},'counts':{}}
        if st.get('revision')!=PROVISIONAL_REVISION:raise ValueError('Provisional buffer revision mismatch')
        return st,v
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();out=fn(st);dumps(st)
            try:self.s.set_state(PROVISIONAL_KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def _count(self,st,k,n=1):st['counts'][k]=st['counts'].get(k,0)+n
    def put(self,event_id,kind,payload,ttl_s=PROVISIONAL_TTL_S):
        def fn(st):
            self._expire(st);iid=uid('prov')
            st['items'][iid]={'event_id':event_id,'kind':kind,'payload':payload,'sha256':sha(payload),'state':'PROVISIONAL','expires':self.clock()+ttl_s,'learning_eligible':False}
            live=[k for k,x in st['items'].items() if x['state']=='PROVISIONAL']
            for k in live[:max(0,len(live)-PROVISIONAL_MAX)]:self._tomb(st,k,'CAPACITY')
            self._count(st,'put');return iid
        return self._mutate(fn)
    def _tomb(self,st,k,reason):
        x=st['items'][k];st['items'][k]={'event_id':x['event_id'],'kind':x['kind'],'sha256':x['sha256'],'state':'TOMBSTONE','reason':reason,'at':self.clock()};self._count(st,'tombstoned')
    def _expire(self,st):
        for k,x in list(st['items'].items()):
            if x['state']=='PROVISIONAL' and x['expires']<self.clock():self._tomb(st,k,'TTL')
            elif x['state']!='PROVISIONAL' and self.clock()-x.get('at',0)>PROVISIONAL_TTL_S:del st['items'][k]
    def settle(self,event_id,status):
        """FINAL -> promote through the registered sink; any other end -> invalidate + tombstone."""
        taken=self._mutate(lambda st:(self._expire(st),[(k,x) for k,x in st['items'].items() if x['event_id']==event_id and x['state']=='PROVISIONAL'])[1])
        done={'promoted':0,'tombstoned':0,'no_sink':0}
        for k,x in taken:
            sink=SINKS.get(x['kind']) if status=='FINAL' else None
            ok=False
            if sink is not None:
                try:sink(x['payload']);ok=True
                except Exception as exc:self.s.log('provisional_sink_failed',event_id,{'kind':x['kind'],'error':type(exc).__name__})
            elif status=='FINAL':done['no_sink']+=1
            def fn(st,k=k,ok=ok):
                if k not in st['items']:return
                if ok:st['items'][k]={'event_id':event_id,'kind':x['kind'],'sha256':x['sha256'],'state':'PROMOTED','at':self.clock()};self._count(st,'promoted')
                else:self._tomb(st,k,'REVISED' if status!='FINAL' else 'NO_SINK')
            self._mutate(fn);done['promoted' if ok else 'tombstoned']+=1
        return done
    def invalidate(self,event_id,reason='REVISED'):
        def fn(st):
            ks=[k for k,x in st['items'].items() if x['event_id']==event_id and x['state']=='PROVISIONAL']
            for k in ks:self._tomb(st,k,reason)
            return len(ks)
        return self._mutate(fn)
    def report(self):
        st,_=self._load()
        return {'revision':PROVISIONAL_REVISION,'live':sum(x['state']=='PROVISIONAL' for x in st['items'].values()),'counts':st['counts'],'factors':EVENT,
                'claim_limit':'TTL scratch only: never authoritative memory and never a learning source'}

def settle_turn(runtime,event_id,status):
    try:return Provisional(runtime.store).settle(event_id,status)
    except Exception as exc:runtime.store.log('provisional_unavailable',event_id,{'error':type(exc).__name__});return None

def operator_command(r,args):
    """:tx [status|provisional|broker|cancel <atx>|approve <tool-call>|undo <tool-call>]"""
    t=Transactions(r.store)
    if not args or args==['status']:return dumps(t.report())
    if args==['provisional']:return dumps(Provisional(r.store).report())
    if args==['broker']:
        from .broker import report
        return dumps(report(r.store))  # WP-T7 output broker decisions
    if len(args)==2 and args[0]=='cancel':return dumps({k:v for k,v in t.cancel(args[1]).items() if k in ('id','state','error')})
    if len(args)==2 and args[0] in ('approve','undo'):
        from .agi import hub as growth
        tools=growth(r).tools;out=tools.approve(args[1]) if args[0]=='approve' else tools.undo(args[1])
        return dumps({k:out.get(k) for k in ('id','tool','status','state','reason','result','error','action_tx')})
    raise ValueError(':tx [status|provisional|broker|cancel <atx>|approve <tool-call>|undo <tool-call>]')
