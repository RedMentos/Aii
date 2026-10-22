"""WP-T7 / §6.4, §11, C6/C7: output broker. One place decides which source owns the visible output of a turn and
what late material may still be shown, and every egress kind gets its C6 schema check.

Authority order before the commit point (IH-H12), highest first:
  APPROVED_FIXED_RULE   operator-approved exact answer (output_policy); beats everything, also an explicit copy request
  EXPLICIT_EXACT_COPY   "Copy exactly: ..." renders the source span unchanged
  MODEL_ANSWER          body answer (grounded by an executed TOOL_RESULT layer when C5 chose the tool)
  SOURCE_SYSTEM_REPORT  source-bound diagnostic when no visible model text exists (error, deadline, cancel)
After the commit point nothing is replaced. Late material is a separate message with role 'broker' (never part of
native history, memory lanes or training rows, which only read user/assistant rows):
  CORRECTION            a higher-authority fact that arrives late, e.g. an executed tool result the answer omits
                        (`tool_conflict_policy`: correct = show the exact value, log = record only)
  ACTION_PREVIEW        a proposed, not executed WRITE_LOCAL tool call with its dry run and `:tx approve <id>`
SNAPSHOT (`:report` / force_report) is read-only and outside the turn: it shows the current text, never rewrites it.
The broker never rewrites model text; a schema violation is reported (C6 rule_violation) and left visible.
"""
import json
import re
from .common import dumps
from .contracts import packet

RANK={'APPROVED_FIXED_RULE':0,'EXPLICIT_EXACT_COPY':1,'MODEL_ANSWER':2,'SOURCE_SYSTEM_REPORT':3}
LATE=('CORRECTION','ACTION_PREVIEW')
DONE_CLAIM=re.compile(r"(?i)\b(i(?:'ve| have)? (?:saved|written|created|stored|noted)|(?:has|have) been (?:saved|written|created|stored)|note (?:is|was) saved|done[.!])")

def decide(candidates,committed=None):
    """candidates: authority names present this turn. committed: authority already visible (or None).
    Before the commit the best authority wins and the rest are overridden; after it a better late candidate becomes a
    CORRECTION, anything else is dropped. Returns {'selected','overridden','late':[(authority,'CORRECTION'|'DROP')]}"""
    bad=[c for c in candidates if c not in RANK]
    if bad:raise ValueError('Unbekannte Ausgabe-Autorität: '+','.join(bad))
    if committed is None:
        if not candidates:return {'selected':None,'overridden':[],'late':[]}
        order=sorted(set(candidates),key=RANK.get)
        return {'selected':order[0],'overridden':order[1:],'late':[]}
    if committed not in RANK:raise ValueError('Unbekannte Ausgabe-Autorität: '+committed)
    return {'selected':committed,'overridden':[],'late':[(c,'CORRECTION' if RANK[c]<RANK[committed] else 'DROP') for c in candidates if c!=committed]}

def egress_type(authority,clarify=False,status='FINAL'):
    if authority in ('APPROVED_FIXED_RULE','EXPLICIT_EXACT_COPY'):return 'EXACT_RENDER'
    if authority=='SOURCE_SYSTEM_REPORT' or status!='FINAL':return 'SYSTEM_REPORT' if authority=='SOURCE_SYSTEM_REPORT' else 'TEXT_REPORT'
    return 'CLARIFY' if clarify else 'TEXT_REPORT'

def value_forms(v):
    out={str(v)}
    if isinstance(v,float):out|={f'{v:.2f}',f'{v:.1f}',str(round(v)),f'{v:,.2f}'}
    if isinstance(v,int) and not isinstance(v,bool):out|={f'{v:,}'}
    return out
def contains_value(v,text):return any(re.search(r'(?<![\d.])'+re.escape(c)+r'(?![\d])',str(text)) for c in value_forms(v))

def conflicts(output,status,tool_result=None,pending=None,egress=None):
    out=[]
    if status=='FINAL' and tool_result and tool_result.get('result') is not None and not isinstance(tool_result['result'],(dict,list)) and not contains_value(tool_result['result'],output):
        out.append('ANSWER_OMITS_TOOL_RESULT')
    elif status=='FINAL' and tool_result and tool_result.get('tool')=='eligibility' and isinstance(tool_result.get('result'),dict):
        from .agi import eligibility  # Thread Q: the answer must commit to the recipe's decision
        if eligibility.answer_action(output)!=tool_result['result'].get('action'):out.append('ANSWER_OMITS_TOOL_RESULT')
    if pending and DONE_CLAIM.search(output or ''):out.append('ANSWER_CLAIMS_PENDING_ACTION_DONE')
    if egress and not egress['ok']:out+=['EGRESS:'+v for v in egress['violations']]
    return out

def preview_text(pending):
    pv=pending.get('preview') or {};cid=pending['call_id']
    what={'CREATE':'neue Datei','REPLACE':'ersetzt bestehende Datei'}.get(pv.get('effect'),pv.get('effect') or 'Wirkung unbekannt')
    lines=['[Aktion wartet auf Freigabe] '+pending['tool']+(' → '+pv['target'] if pv.get('target') else '')+' ('+what+(', '+str(pv['new_chars'])+' Zeichen' if pv.get('new_chars') is not None else '')+')']
    if pv.get('old_head') is not None:lines.append('Bisher: '+pv['old_head'])
    if pv.get('new_head') is not None:lines.append('Neu: '+pv['new_head'])
    lines.append('Nichts ist geschehen. Freigeben: :tx approve '+cid+(' · danach rücknehmbar: :tx undo '+cid if pv.get('undo_available') else ''))
    return '\n'.join(lines)

def correction_text(tool_result):
    call=tool_result['tool']+'('+dumps(tool_result['args'])+')'
    if tool_result['tool']=='list_arith':  # R4 part 6: args carry the whole user text; show the recipe line instead
        from .agi import listarith
        call='list_arith: '+(listarith.label(tool_result['args']) or tool_result['args'].get('operation','?'))
    if tool_result['tool']=='eligibility':
        from .agi import eligibility
        return '[Korrektur · Werkzeugergebnis] eligibility: '+eligibility.decision_line(tool_result['result'])+' (lokal nach den genannten Regeln berechnet; die Antwort oben trifft diese Entscheidung nicht).'
    return '[Korrektur · Werkzeugergebnis] '+call+' = '+str(tool_result['result'])+' (lokal exakt berechnet; die Antwort oben nennt diesen Wert nicht).'

class Broker:
    def __init__(self,runtime):self.r=runtime;self.s=runtime.store
    def _check(self,e,kind,payload,source_text=None,tools=None):
        from .actionlearn import egress
        out=egress(kind,payload,source_text,tools)
        self.s.add_packet('EgressCheck',packet('EgressCheck','C6_EGRESS',e['event_id'],e['brain_generation_id'],[e['source_ref']],action_type=kind,ok=out['ok'],violations=out['violations'],rewrites=0))
        return out
    def _late(self,e,mid,text,meta):
        return self.s.message(self.r.session,e['event_id'],'broker',text,'FINAL',{'model_generated':False,'output_owner':'C7_OUTPUT_BROKER','late_of':mid}|meta)
    def finalize(self,e,mid,meta,status,output,*,direct=False,exact_requested=False,clarify=False,tool_result=None,pending=None):
        """After finish_message: decision packet, C6 check of the visible output, late CORRECTION / ACTION_PREVIEW."""
        cands=[]
        if meta.get('output_authority')=='APPROVED_FIXED_RULE' or meta.get('exact_policy_matched'):cands.append('APPROVED_FIXED_RULE')
        if exact_requested or (direct and not cands):cands.append('EXPLICIT_EXACT_COPY')
        if meta.get('model_generated') and output:cands.append('MODEL_ANSWER')
        if meta.get('output_authority')=='SOURCE_SYSTEM_REPORT':cands.append('SOURCE_SYSTEM_REPORT')
        d=decide(cands)
        kind=egress_type(d['selected'],clarify,status)
        eg=self._check(e,kind,output) if output else None
        cf=conflicts(output,status,tool_result,pending,eg)
        late=[]
        if 'ANSWER_OMITS_TOOL_RESULT' in cf:
            pol=self.r.cfg.get('tool_conflict_policy','correct');late.append({'kind':'CORRECTION','applied':pol=='correct'})
            if pol=='correct':
                text=correction_text(tool_result);self._check(e,'CORRECTION',{'text':text,'correction_of':mid,'reason':'TOOL_RESULT_OMITTED'})
                late[-1]['message_id']=self._late(e,mid,text,{'output_authority':'LATE_CORRECTION','correction_of':mid,'reason':'TOOL_RESULT_OMITTED','tool_tx':tool_result.get('action_tx') or tool_result.get('tx')})
        if pending and status=='FINAL':
            text=preview_text(pending);tools=set(self._tools())
            chk=self._check(e,'ACTION_PREVIEW',dict(pending,text=text),tools=tools or None)
            item={'kind':'ACTION_PREVIEW','call_id':pending['call_id'],'applied':chk['ok']}
            if chk['ok']:item['message_id']=self._late(e,mid,text,{'output_authority':'ACTION_PREVIEW','tool_call':pending['call_id']})
            late.append(item)
        p=self.s.add_packet('OutputBrokerDecision',packet('OutputBrokerDecision','C7_OUTPUT_BROKER',e['event_id'],e['brain_generation_id'],[e['source_ref']],
            authority=d['selected'] or 'NONE',egress_type=kind,status=status,overridden=d['overridden'],conflicts=cf,committed=bool(meta.get('output_committed')),late=late,
            message_id=mid,rewrites=0))
        return {'packet_id':p['packet_id'],'authority':d['selected'],'egress_type':kind,'egress_ok':eg['ok'] if eg else None,'conflicts':cf,'late':late}
    def _tools(self):
        try:
            from .agi import hub
            return list(hub(self.r).tools.tools)
        except Exception:return []
    def snapshot_check(self,e,text):
        """force_report: the read-only snapshot gets its own C6 check (no message is written)."""
        return self._check(e,'SNAPSHOT',text) if e else None

def report(store,limit=200):
    rows=[json.loads(r['payload']) for r in store.rows("SELECT payload FROM packets WHERE kind='OutputBrokerDecision' ORDER BY rowid DESC LIMIT ?",(limit,))]
    by={};cf={};late={}
    for p in rows:
        by[p['authority']]=by.get(p['authority'],0)+1
        for c in p['conflicts']:k=c.split(':')[0] if c.startswith('EGRESS') else c;cf[k]=cf.get(k,0)+1
        for x in p.get('late',[]):late[x['kind']]=late.get(x['kind'],0)+1
    return {'turns':len(rows),'authority':by,'conflicts':cf,'late':late,'order':list(RANK),
            'claim_limit':'Precedence and egress schema only; the broker never judges whether a model answer is true'}
