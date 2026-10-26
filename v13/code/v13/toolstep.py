"""WP-K rest / WP-AG10 / WP-N4: TOOL_CALL as a real C5 candidate in the live turn (§6.4, §11.1, IH-H29, §17.3).

Per turn a C2-style proposer looks for a concrete local tool use (BOOT: arithmetic for `calc`). The proposal enters the
C5 ActionGate as the EXTERNAL_TOOL candidate; IH-H29 decides permission (schema -> user enabled -> risk -> confirmation ->
Age right `simple_tool_choice`, Age 1). V13 choosing a tool for a user question is its own choice (origin SYSTEM).

  allowed  -> C5 may select TOOL_CALL; the call runs as an IH-H14 transaction through ToolRegistry; its result becomes a
              grounded TOOL_RESULT layer for the answering body (the body still writes the answer, C6 egress stays).
  refused  -> SHADOW: the candidate stays suppressed with the policy reason; for pure READ_LOCAL tools (calc) the result
              is computed off-path, never shown, and compared with the final answer afterwards (agreement log), which is
              the evidence an Age-1 tool right needs. Write/network tools are never computed in shadow.
  proposed -> WP-T7: a WRITE_LOCAL tool the user enabled (BOOT: `sandbox_note` for "save a note ...") needs a per-call
              approval. The call is registered as PROPOSED with a dry-run preview, the body is told it has not happened,
              and the output broker shows the preview with `:tx approve <id>` (undo afterwards with `:tx undo <id>`).
R4 part 6: a question over listed values ("how many ... more ... than", "total") becomes `list_arith`: C3 only reads typed values,
the recipe in agi/listarith.py computes (measured: r4-typed-recipe BEFUND). The proposer is a BOOT regex, not learned; Needle/C2 tool choice replaces it later (§57, c2-benchmark).
Thread Q (2026-10-21): a decision over Option A/B with budget/deadline/locality rules becomes `eligibility` the same way: C3 copies
typed values from the current message plus earlier exact text (the user's own earlier messages, verified body quotes), the
rule-anchored recipe in agi/eligibility.py decides (measured offline: wrong committed decisions 3 -> 0, WP-W2c/W2d).
2026-10-21 user decision: by default (cfg eligibility_reader='fixed') no language model reads the rules either; the fixed reader
agi/eligibility.fixed_read takes them from the fixed rule wording, newest statement wins, and anything unclear stays UNKNOWN.
"""
import json
import re
import time
from .common import dumps
from .contracts import packet

PROPOSER='boot-arith-note-v3';KEY='TOOL_SHADOW_AGREEMENT'
LIST_PROPOSER='boot-listarith-v1';LIST_READ_SECONDS=45  # R4 part 6: C3 value read for list_arith
ELIG_PROPOSER='boot-eligibility-v1';ELIG_READ_SECONDS=60  # Thread Q: C3 value read for eligibility (only with cfg eligibility_reader='c3'; default 'fixed' reads without a model)
LIST_NOTE='Use this exact number in the answer. If the text states a different number for it, say clearly that it is wrong.'  # wording of r4_typed_recipe RESULT_TEMPLATE
WORD_OPS=[(r'\bmultiplied by\b|\btimes\b|×','*'),(r'\bdivided by\b|÷','/'),(r'\bplus\b','+'),(r'\bminus\b','-'),(r'\bto the power of\b|\^','**')]
NUM=r'\d+(?:[.,]\d+)?'
PERCENT=re.compile(r'('+NUM+r')\s*%\s*of\s*('+NUM+r')',re.I)
EXPR=re.compile(r'(?<![\w.])(\(?\s*'+NUM+r'(?:\s*(?:\*\*|[+\-*/%])\s*\(?\s*'+NUM+r'\s*\)?)+)')

NOTE_NAMED=re.compile(r'^\s*(?:please\s+)?(?:save|write|make|take|create)\s+(?:a\s+)?note\s+(?:called|named)\s+["\']?([a-z][a-z0-9_]{1,31})["\']?\s*:\s*(\S[\s\S]{0,1999})$',re.I)
NOTE=re.compile(r'^\s*(?:please\s+)?(?:note down|(?:save|write|make|take|create)\s+(?:a\s+)?note)\s*:\s*(\S[\s\S]{0,1999})$',re.I)

def _slug(text):
    w=re.findall(r'[a-z0-9]+',text.lower())[:3]
    return ('note_'+'_'.join(w))[:32].rstrip('_') if w else 'note'
def propose_note(text):
    """Explicit note request -> sandbox_note proposal (WRITE_LOCAL: never runs without a per-call approval)."""
    m=NOTE_NAMED.match(text)
    if m:return {'tool':'sandbox_note','args':{'name':m.group(1).lower(),'text':m.group(2).strip()},'confidence':.95,'span':[0,len(text)]}
    m=NOTE.match(text)
    if m:return {'tool':'sandbox_note','args':{'name':_slug(m.group(1)),'text':m.group(1).strip()},'confidence':.9,'span':[0,len(text)]}
    return None

NOTE_EDIT=[(re.compile(r'^\s*(?:please\s+)?mark\s+(?:the\s+)?note\s+["\']?([a-z][a-z0-9_]{1,31})["\']?\s+(?:as\s+)?done\s*[.!]?\s*$',re.I),lambda c:c+' Done.'),
           (re.compile(r'^\s*(?:please\s+)?(?:make|mark)\s+(?:the\s+)?note\s+["\']?([a-z][a-z0-9_]{1,31})["\']?\s+(?:as\s+)?urgent\s*[.!]?\s*$',re.I),lambda c:'Urgent: '+c),
           (re.compile(r'^\s*(?:please\s+)?(?:uppercase|capitalize)\s+(?:the\s+)?note\s+["\']?([a-z][a-z0-9_]{1,31})["\']?\s*[.!]?\s*$',re.I),lambda c:c.upper())]
def propose_note_edit(text,read):
    """Thread M: edit of an existing sandbox note (done/urgent/uppercase) -> sandbox_note proposal with the full new text.
    read(name) returns the current content or None; still WRITE_LOCAL, so it never runs without a per-call approval."""
    for rx,edit in NOTE_EDIT:
        m=rx.match(str(text))
        if m:
            old=read(m.group(1).lower())
            if old is None or edit(old)==old or len(edit(old))>2000:return None
            return {'tool':'sandbox_note','args':{'name':m.group(1).lower(),'text':edit(old)},'confidence':.9,'span':[0,len(text)]}
    return None

def _num(s):return s.replace(',','') if re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?',s) else s.replace(',','.')
def propose(text):
    """Return {'tool','args','confidence','span'} for a concrete arithmetic request, else None (never guesses)."""
    t=str(text)
    note=propose_note(t)
    if note:return note
    if len(t)>400:return None
    m=PERCENT.search(t)
    if m:return {'tool':'calc','args':{'expression':f'{_num(m.group(1))}/100*{_num(m.group(2))}'},'confidence':.9,'span':[m.start(),m.end()]}
    w=t
    for pat,op in WORD_OPS:w=re.sub(pat,op,w,flags=re.I)
    w=re.sub(r'(?<=\d),(?=\d{3}\b)','',w)
    m=EXPR.search(w)
    if not m:return None
    expr=re.sub(r'\s+','',m.group(1)).replace(',','.')
    if expr.count('(')!=expr.count(')'):expr=expr.replace('(','').replace(')','')
    if re.fullmatch(r'\d{4}-\d{1,2}(?:-\d{1,2})?',expr) or re.fullmatch(r'\d{1,2}/\d{1,2}(?:/\d{2,4})?',expr):return None  # dates
    return {'tool':'calc','args':{'expression':expr},'confidence':.8 if w!=t else .9,'span':[m.start(),m.end()]}

class ToolStep:
    def __init__(self,runtime):self.r=runtime
    def _registry(self):
        from .agi import hub
        return hub(self.r).tools
    def plan(self,e,text,offers=(),version=None):
        """Proposal + IH-H29 policy (no effect yet). Logged as ToolProposal packet."""
        from .toolforecast import note_text
        p=propose_note_edit(text,lambda name:note_text(self.r.home,name)) or self._propose_eligibility(e,text,offers,version) or propose(text) or self._propose_list(e,text)
        if not p:return None
        reg=self._registry();spec=reg.tools.get(p['tool'])
        if spec is None:return None
        status,why,steps=reg._policy(spec,'SYSTEM',p['args'])
        p.update(status=status,reason=why,risk=spec.risk,proposer=p.get('proposer',PROPOSER),utility=round(.5+.5*p['confidence'],4))  # BOOT: exact local tool beats a free-text body (route utilities .4-.8)
        pk=self.r.store.add_packet('ToolProposal',packet('ToolProposal','C2_TOOL_PROPOSER',e['event_id'],e['brain_generation_id'],[e['source_ref']],
             tool=p['tool'],args=p['args'],policy_status=status,policy_reason=why,contract=steps,confidence=p['confidence'],proposer=p['proposer'],truth_authority=0))
        p['packet_id']=pk['packet_id'];return p
    def _propose_list(self,e,text):
        """R4: strict local row fast arm, otherwise C3 typed read -> guarded list_arith proposal."""
        from .agi import listarith
        op=listarith.operation(text)
        if not op or 'list_arith' not in self._registry().box.load()[0]['enabled']:return None  # the C3 read costs a model call: only after the user enabled the tool
        from .prohibitions import verdict
        if verdict(self.r.store,self._registry().tools['list_arith'])['blocked']:return None  # prohibited / Notaus: no model read either
        try:
            values=listarith.parse_explicit_rows(text)
            if values is None:
                values=listarith.read_values(self.r.pool.get('C3_LANGUAGE'),text,self.r.cancel_event,time.monotonic()+LIST_READ_SECONDS)
            listarith.compute(op,values,text)  # guard before proposing: every value must be an exact number of the user text
        except Exception as exc:self.r.store.log('tool_step_unavailable',e['event_id'],{'stage':'list_read','error':type(exc).__name__});return None
        return {'tool':'list_arith','args':{'operation':op,'text':str(text),'values':listarith.encode(values)},'confidence':.8,'span':[0,len(str(text))],'proposer':LIST_PROPOSER}
    def earlier_parts(self,e,offers=(),version=None):
        """Thread Q: earlier exact evidence for eligibility, as (user history oldest->newest, verified body quotes). The user's
        own earlier messages in the history window (stored source text) and source-verified quotes of the selected body
        offers; never hypotheses or assistant answers."""
        hist=[];quotes=[]
        try:
            from .history import native_history
            rows,_=native_history(self.r.store,self.r.session,e['event_id'],self.r.cfg['history_turns'])
            hist+=[m['text'] for m in rows if m['role']=='user']
        except Exception as exc:self.r.store.log('tool_step_unavailable',e['event_id'],{'stage':'elig_history','error':type(exc).__name__})
        if offers and version is not None:
            try:quotes+=[q['text'] for a in self.r.cognition.analyst_context(list(offers),e,version) for q in a['verified_quotes']]
            except Exception as exc:self.r.store.log('tool_step_unavailable',e['event_id'],{'stage':'elig_quotes','error':type(exc).__name__})
        seen=set();keep=[]
        for kind,t in [('h',x) for x in hist]+[('q',x) for x in quotes]:
            t=str(t).strip()
            if t and t not in seen and len(t)<=1000:seen.add(t);keep.append((kind,t))
        from .agi import eligibility
        keep=keep[-eligibility.MAX_EARLIER:]
        return [t for k,t in keep if k=='h'],[t for k,t in keep if k=='q']
    def earlier_exact(self,e,offers=(),version=None):
        h,q=self.earlier_parts(e,offers,version);return h+q
    def _propose_eligibility(self,e,text,offers=(),version=None):
        """Thread Q: Option A/B decision (BOOT wording rule) -> C3 copies typed values -> eligibility proposal."""
        from .agi import eligibility
        if not eligibility.question(text) or 'eligibility' not in self._registry().box.load()[0]['enabled']:return None  # C3 read costs a model call: only after the user enabled the tool
        from .prohibitions import verdict
        if verdict(self.r.store,self._registry().tools['eligibility'])['blocked']:return None  # prohibited / Notaus: no read either
        hist,quotes=self.earlier_parts(e,offers,version)
        hist,quotes=eligibility.scope_earlier(text,hist,quotes)  # Run576: never import another project's exact rules
        earlier=hist+quotes
        try:
            mode=self.r.cfg.get('eligibility_reader','model')
            if mode=='fixed_strict':values=eligibility.fixed_read(text,hist,quotes)  # 2026-10-21 reader: no language model at all (thread „Zitierhilfe an“)
            else:
                fixed=eligibility.read_fixed(text,earlier) if mode=='fixed' else None  # 22.10. reader (FIRST_SUPPORTED): rules never from a model
                if fixed and fixed['options']:values=fixed  # this wording is fully covered: no model call
                else:
                    values=eligibility.read_values(self.r.pool.get('C3_LANGUAGE'),text,earlier,self.r.cancel_event,time.monotonic()+ELIG_READ_SECONDS)
                    if fixed:values=eligibility.with_fixed_rules(values,fixed)
            args=eligibility.args_for(values,text,earlier)
        except Exception as exc:self.r.store.log('tool_step_unavailable',e['event_id'],{'stage':'elig_read','error':type(exc).__name__});return None
        return {'tool':'eligibility','args':args,'confidence':.8,'span':[0,len(str(text))],'proposer':ELIG_PROPOSER}
    def _forecast(self,e,p):
        """Thread M: SHADOW tool-consequence forecast before the effect (None when OFF or outside a confirmed world)."""
        try:
            from .toolforecast import for_runtime
            return for_runtime(self.r).predict(p['tool'],p['args'],e['event_id'])
        except Exception as exc:self.r.store.log('tool_forecast_unavailable',e['event_id'],{'error':type(exc).__name__});return None
    def execute(self,e,p,intent=None):
        """C5 selected TOOL_CALL: run through ToolRegistry (IH-H14 transaction, grounding outcome)."""
        tx=self._registry().call(p['tool'],p['args'],origin='SYSTEM',intent=intent,predicted=self._forecast(e,p),event_id=e['event_id'],idempotency_key=e['event_id']+':'+p['tool'])
        ok=tx['status'] in ('EXECUTED','DEDUPLICATED') and tx.get('error') is None
        self.r.store.log('tool_step',e['event_id'],{'tool':p['tool'],'status':tx['status'],'mode':'ACTIVE'})
        return {'tool':p['tool'],'args':p['args'],'status':tx['status'],'result':tx.get('result') if ok else None,'error':tx.get('error'),'tx':tx['id'],'action_tx':tx.get('action_tx')}
    def propose_call(self,e,p):
        """WP-T7: register a PROPOSED call (no effect) with its dry-run preview; the user approves it with :tx approve."""
        if p.get('status')!='PROPOSED':return None
        tx=self._registry().call(p['tool'],p['args'],origin='SYSTEM',predicted=self._forecast(e,p),event_id=e['event_id'],idempotency_key=e['event_id']+':'+p['tool'])
        self.r.store.log('tool_step',e['event_id'],{'tool':p['tool'],'status':tx['status'],'mode':'PROPOSED'})
        return {'tool':p['tool'],'args':p['args'],'status':tx['status'],'call_id':tx['id'],'preview':tx.get('preview'),'reason':tx['reason'],'user_rules':tx.get('user_rules') or []}
    def pending_layer(self,pending):
        """Volatile layer: the body must not claim the action happened."""
        pv=pending.get('preview') or {}
        return {'tool':pending['tool'],'status':'WAITING_FOR_USER_APPROVAL','effect':pv.get('effect'),'target':pv.get('target'),
                'note':'Not executed. The user sees a preview and can approve it; do not say it was done.'}
    def shadow(self,e,p):
        """Refused by policy: compute pure READ_LOCAL tools off-path for later agreement; never shown, never a fact.
        Never when a user rule forbids it or asks to be asked first (2026-10-21): not even off-path."""
        if p['risk']!='READ_LOCAL' or p['tool'] not in ('calc','list_arith','eligibility') or 'USER_RULE' in str(p.get('reason','')):return None
        if str(p.get('reason') or '').startswith('HARD_BLOCK:'):return None  # a prohibited tool is not run in the background either
        try:
            from .agi.tools import calc
            from .agi import listarith,eligibility
            value=calc(p['args']['expression']) if p['tool']=='calc' else listarith.tool(**p['args']) if p['tool']=='list_arith' else eligibility.tool(**p['args'])
            return {'tool':p['tool'],'args':p['args'],'result':value,'reason':p['reason']}
        except Exception as exc:return {'tool':p['tool'],'args':p['args'],'result':None,'error':type(exc).__name__,'reason':p['reason']}
    def compare(self,e,shadow,output):
        """Did the body's answer contain the tool result? Agreement evidence for the Age-1 tool right (log only)."""
        if not shadow or shadow.get('result') is None:return None
        v=shadow['result'];cands={str(v)}
        if isinstance(v,float):cands|={f'{v:.2f}',f'{v:.1f}',str(round(v)),f'{v:,.2f}'}
        if isinstance(v,int):cands|={f'{v:,}'}
        if shadow['tool']=='eligibility':  # Thread Q: agreement = the answer commits to the recipe's decision
            from .agi import eligibility
            agree=eligibility.answer_action(output)==v['action']
        elif shadow['tool']=='calc':
            # Mere presence is not agreement: "1776 is wrong" must not
            # increase the Age-1 shadow evidence counter. These conservative
            # lexical checks are NOT general natural-language verification.
            text=str(output);agree=False
            for c in sorted(cands,key=len,reverse=True):
                rx=r'(?<![\d.])'+re.escape(c)+r'(?![\d])'
                for match in re.finditer(rx,text):
                    before=text[max(0,match.start()-40):match.start()]
                    after=text[match.end():match.end()+40]
                    denied_before=re.search(
                        r"(?:\bnot|\bnever|\bno|\bcannot(?:\s+verify)?|\bcan't(?:\s+verify)?|\bunable\s+to\s+verify)\s*$",
                        before,re.I)
                    denied_after=re.search(
                        r'^\s*(?:(?:is|was|would be|seems)\s+)?(?:wrong|incorrect|false|invalid|not\s+(?:correct|right|the\s+(?:correct\s+)?answer))\b',
                        after,re.I)
                    ambiguous=(re.search(r'\b(?:either|or)\s*$',before,re.I) or
                               re.search(r'^\s*(?:or|/)\s*(?=[-+]?\d)',after,re.I))
                    if not (denied_before or denied_after or ambiguous):
                        agree=True;break
                if agree:break
        else:agree=any(re.search(r'(?<![\d.])'+re.escape(c)+r'(?![\d])',str(output)) for c in cands)
        for attempt in (0,1):  # telemetry whitelists fields, so the agreement count lives in a state (ids/numbers only)
            st,v=self.r.store.state(KEY);st=st or {'compared':0,'agree':0,'tools':{}}
            st['compared']+=1;st['agree']+=int(agree);t=st['tools'].setdefault(shadow['tool'],[0,0]);t[0]+=1;t[1]+=int(agree)
            try:self.r.store.set_state(KEY,st,expected=v);break
            except ValueError:
                if attempt:raise
        self.r.store.log('tool_shadow_outcome',e['event_id'],{})
        return agree
    def lead(self,result):
        """cfg tool_answer_first: the executed eligibility decision opens the visible answer as a fixed sentence (the body
        only explains it), so a 350M body that ignores the TOOL_RESULT layer can no longer replace the decision."""
        if not self.r.cfg.get('tool_answer_first') or not result or result.get('tool')!='eligibility' or not isinstance(result.get('result'),dict):return None
        from .agi import eligibility
        return eligibility.answer_sentence(result['args'],result['result'])
    def lead_final(self,result):
        """UNKNOWN/NONE: the fixed text is the whole answer (no body continuation that could still pick an option)."""
        if not self.lead(result) or result['result'].get('action') not in ('UNKNOWN','NONE'):return None
        from .agi import eligibility
        return eligibility.final_text(result['args'],result['result'])
    def layer(self,result):
        """Volatile context layer for the answering body: grounded tool output with its transaction id."""
        args=result['args']
        if result['tool']=='list_arith':  # R4 part 6 dev seed 7: as raw JSON args C3 350M ignored the value in 7/15 sums
            from .agi import listarith
            return {'tool':'list_arith','exact_result':result['result'],'recipe':f"{listarith.label(args)} = {result['result']}",
                    'note':LIST_NOTE,'transaction':result['action_tx'] or result['tx'],'source':'TOOL_RESULT (executed locally, exact)'}
        if result['tool']=='eligibility':  # Thread Q: readable decision line, like list_arith (raw JSON gets ignored by C3 350M)
            from .agi import eligibility
            return {'tool':'eligibility','answer':eligibility.answer_sentence(args,result['result']),'details':eligibility.decision_line(result['result']),'rejected_values':result['result'].get('rejected',[]),
                    'note':eligibility.FIRST_NOTE if self.lead(result) else eligibility.LIVE_NOTE,'transaction':result['action_tx'] or result['tx'],'source':'TOOL_RESULT (executed locally, exact)'}
        return {'tool':result['tool'],'input':args,'output':result['result'],'transaction':result['action_tx'] or result['tx'],'source':'TOOL_RESULT (executed locally, exact)'}

def report(store,limit=200):
    st=store.state(KEY)[0] or {'compared':0,'agree':0,'tools':{}}
    act=store.rows("SELECT id FROM telemetry WHERE kind='tool_step' ORDER BY id DESC LIMIT ?",(limit,))
    return {'proposer':PROPOSER,'shadow_compared':st['compared'],'shadow_agreement':round(st['agree']/st['compared'],4) if st['compared'] else None,
            'per_tool':st['tools'],'recent_active_calls':len(act),
            'claim_limit':'Shadow agreement is evidence for the Age-1 tool right, not a permission; tools run only when the user enabled them and the Age right allows it'}
