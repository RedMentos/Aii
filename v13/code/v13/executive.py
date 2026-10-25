"""Explicit source-bound C1 continuity and exact C5 fallback snapshots.

No generated summary becomes a fact. Native KV, body projections and semantic
completion are not claimed by this bounded structured-state implementation.
"""
import json
from .common import dumps, now, safe_text
from .contracts import packet,validate
from .age import AgeControl

MAX_EVENTS=8

def permission_flags(control,cfg,resource_state='UNKNOWN'):
    """WP-T2 §3.3.0 C0/§17.5: ExecState permissions come from Age per capability, not fixed flags.
    External tool execution and native body training stay closed unless their Age right is granted."""
    from .resource_modes import as_mode
    try:r=control.rights(as_mode(resource_state))  # §97.2: accepts a mode or a legacy guard state
    except Exception:r={'age':0,'by_capability':{},'granted':[],'resource_mode':'UNAVAILABLE'}
    g=set(r['granted'])
    return {'age':r['age'],'age_by_capability':r['by_capability'],'rights':r['granted'],'resource_mode':r['resource_mode'],
            'user_stage_cap':cfg['user_stage_cap'],'learning_mode':cfg['learning_mode'],
            'external_tool_execution':'simple_tool_choice' in g,'native_body_training':'raw_body_attempt' in g and cfg['learning_mode']=='APPROVED_COMMIT'}
MAX_QUESTIONS=8

class Executive:
    def __init__(self,store):self.s=store
    def _event(self,e,session):
        row=self.s.one('SELECT session_id,packet FROM events WHERE id=?',(e['event_id'],))
        if not row or row['session_id']!=session or json.loads(row['packet'])!=e or e['authority']!='AUTHORITATIVE':raise ValueError('Executive event/session/source binding invalid')
        self.s.read_source(e['source_ref'])
    def _valid_ref(self,ref):
        try:self.s.read_source(ref);return True
        except (ValueError,OSError,KeyError,TypeError):return False
    def _goal_event_valid(self,item,session):
        """A continuity goal must name its own session's exact event source."""
        if not isinstance(item,dict) or type(item.get('event_id')) is not str or not isinstance(item.get('source_ref'),dict):
            return False
        row=self.s.one('SELECT session_id,packet FROM events WHERE id=?',(item['event_id'],))
        if not row or row['session_id']!=session:return False
        try:
            event=json.loads(row['packet'])
            return (event.get('event_id')==item['event_id'] and event.get('source_ref')==item['source_ref']
                    and self._valid_ref(item['source_ref']))
        except (ValueError,TypeError,KeyError):return False
    def _task_valid(self,task,state,session):
        """An implicit task is the current query; a pinned task is a same-session HumanDecision."""
        if not isinstance(task,dict) or not isinstance(task.get('source_ref'),dict):return False
        ref=task['source_ref']
        if not self._valid_ref(ref):return False
        if task.get('origin')=='SOURCE_USER_REQUEST':
            return self._goal_event_valid({'event_id':state.get('last_event_id'),'source_ref':ref},session)
        if task.get('origin')!='EXPLICIT_OPERATOR_TASK':return False
        try:
            row=self.s.one("SELECT p.payload,p.event_id FROM packets p JOIN events e ON e.id=p.event_id "
                           "WHERE p.kind='HumanDecision' AND e.session_id=? "
                           "AND json_extract(p.payload,'$.source_ref.source_id')=? ORDER BY p.rowid DESC LIMIT 1",
                           (session,ref['source_id']))
            if not row:return False
            decision=json.loads(row['payload'])
            return (decision.get('kind')=='executive_task' and decision.get('event_id')==row['event_id']
                    and decision.get('source_ref')==ref and decision.get('value')==self.s.read_source(ref))
        except (ValueError,TypeError,KeyError,OSError):return False
    def _action_valid(self,item,state,session):
        # Re-check persisted action and corollary against this event/session.
        # An old or foreign action cannot become C1's current action intent.
        if not isinstance(item,dict) or item.get('type')!='LOCAL_TEXT_REPORT':return False
        aid=item.get('action_id');copy_id=item.get('corollary_packet_id')
        if type(aid) is not str or type(copy_id) is not str:return False
        row=self.s.one("SELECT a.event_id,a.kind,a.corollary_id,e.session_id,"
                       "p.kind AS packet_kind,p.event_id AS copy_event,p.payload "
                       "FROM actions a JOIN events e ON e.id=a.event_id "
                       "JOIN packets p ON p.id=a.corollary_id WHERE a.id=?",(aid,))
        if not row or row['session_id']!=session or row['event_id']!=state.get('last_event_id'):return False
        if row['kind']!='TEXT_REPORT' or row['corollary_id']!=copy_id:return False
        if row['packet_kind']!='CorollaryCopy' or row['copy_event']!=row['event_id']:return False
        try:
            copy=json.loads(row['payload'])
            return (copy.get('packet_id')==copy_id and copy.get('event_id')==row['event_id']
                    and copy.get('action_id')==aid and copy.get('self_caused') is True
                    and copy.get('expected',{}).get('type')=='TEXT_REPORT')
        except (KeyError,TypeError,ValueError):return False
    def _clean(self,state,session):
        state=json.loads(dumps(state or {}))
        if state.get('session_id')!=session:return {}
        state['goal_sequence']=[x for x in state.get('goal_sequence',[]) if self._goal_event_valid(x,session)][-MAX_EVENTS:]
        task=state.get('active_task')
        if not self._task_valid(task,state,session):state['active_task']=None
        if not self._action_valid(state.get('current_action_intent'),state,session):state['current_action_intent']=None
        state['memory_refs']=[x for x in state.get('memory_refs',[]) if self._memory(x,session)]
        state['open_questions']=[x for x in state.get('open_questions',[]) if self._question_valid(x,session)][-MAX_QUESTIONS:]
        # Never carry old hypotheses into another generation as current offers.
        goal_ref=state.get('goal_source_ref')
        if (not self._goal_event_valid({'event_id':state.get('last_event_id'),'source_ref':goal_ref},session)
                or self.s.read_source(goal_ref)!=state.get('goal')):
            state['goal']='';state['goal_source_ref']=None
        state['salient_A_offer']=state.get('goal_source_ref')
        state['salient_B_offer']=[x for x in state.get('salient_B_offer',[]) if self._offer_valid(x,state.get('brain_generation_id'),session)]
        return state
    def _question_valid(self,item,session):
        # An open question is about the user event that produced its OfferPacket,
        # never an arbitrary readable source from another chat or later event.
        if not isinstance(item,dict) or not isinstance(item.get('source_ref'),dict):return False
        if not self._valid_ref(item['source_ref']):return False
        row=self.s.one("SELECT p.payload,e.session_id,e.packet AS event_packet,e.id AS event_id "
                       "FROM packets p JOIN events e ON e.id=p.event_id "
                       "WHERE p.id=? AND p.kind='OfferPacket'",(item.get('offer_packet_id'),))
        if not row or row['session_id']!=session:return False
        try:
            offer=json.loads(row['payload']);event=json.loads(row['event_packet'])
            return (event.get('event_id')==row['event_id']
                    and event.get('source_ref')==item['source_ref']
                    and offer.get('event_id')==row['event_id']
                    and offer.get('packet_id')==item['offer_packet_id']
                    and offer['offer'].get('needs_reentry') is True
                    and item.get('uncertainty')==offer['offer'].get('uncertainty','')[:160]
                    and all(self._valid_ref(x) for x in offer['provenance']+offer['evidence_refs']))
        except (KeyError,TypeError,ValueError):return False
    def _offer_valid(self,item,generation,session):
        row=self.s.one("SELECT p.payload,e.session_id FROM packets p JOIN events e ON e.id=p.event_id WHERE p.id=? AND p.kind='OfferPacket'",(item.get('packet_id'),))
        if not row or row['session_id']!=session:return False
        p=json.loads(row['payload'])
        return p['brain_generation_id']==generation and p['evidence_refs']==item.get('source_refs') and all(self._valid_ref(x) for x in p['provenance']+p['evidence_refs'])
    def _memory(self,item,session):
        if not isinstance(item,dict):return False
        row=self.s.one("SELECT m.*,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id "
                       "WHERE m.id=? AND m.active=1 AND s.deleted=0 AND (m.session_id=? OR m.scope='global')",
                       (item.get('memory_id'),session))
        if not row or not self._valid_ref(item.get('source_ref',{})) or row['source_id']!=item['source_ref']['source_id']:return False
        if row['value']!=self.s.read_source(item['source_ref']):return False
        # C1 persists references across turns and snapshots. A readable blob alone
        # cannot authorize a correction after its F5 HumanDecision is revoked.
        from .memory import Memory
        if not Memory(self.s,{})._verified_rows([row]):return False
        # A same-key local correction supersedes a global value in this session.
        if row['scope']=='global':
            local=self.s.one("SELECT value FROM memories WHERE session_id=? AND kind=? AND key_text=? AND scope='session' AND active=1 ORDER BY created DESC LIMIT 1",(session,row['kind'],row['key_text']))
            if local and local['value']!=row['value']:return False
        return True
    def view(self,session):
        state,_=self.s.state('C1_EXEC:'+session,{})
        state=self._clean(state,session)
        if not state:return {'session_id':session,'active_task':None,'goal_sequence':[],'memory_refs':[],'open_questions':[]}
        task=state.get('active_task')
        if task:task['exact_task']=self.s.read_source(task['source_ref'])[:320]
        state['constraints']=self.s.rules()
        return state
    def _write(self,state,expected):
        # Packet publication and continuity version move together, including on crash.
        with self.s.tx() as c:
            row=c.execute('SELECT version FROM states WHERE key=?',('C1_EXEC:'+state['session_id'],)).fetchone()
            v=row[0] if row else 0
            if v!=expected:raise ValueError('Stale executive state write')
            state['state_version']=v+1
            validate('ExecState',state)
            c.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',('C1_EXEC:'+state['session_id'],v+1,dumps(state)))
            c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',(state['packet_id'],'ExecState',state['event_id'],state['brain_generation_id'],dumps(state),now()))
        return state
    def report_context(self,session):
        """Validated continuity for native readers; IDs remain in packets.

        Task requests and observer hypotheses never override human corrections.
        """
        view=self.view(session);task=view.get('active_task')
        result={'task_request':None,'unresolved_observer_hypotheses':[],
                'action_type':(view.get('current_action_intent') or {}).get('type'),
                'external_tool_execution':False}
        if task:
            result['task_request']={'exact_request':self.s.read_source(task['source_ref'])[:320],
                                    'origin':task['origin'],'authority':'REQUEST_NOT_FACT'}
        for item in view.get('open_questions',[])[:MAX_QUESTIONS]:
            result['unresolved_observer_hypotheses'].append({
                'source_request':self.s.read_source(item['source_ref'])[:240],
                'uncertainty':item.get('uncertainty','')[:160],
                'authority':'UNRESOLVED_HYPOTHESIS'})
        return result
    def begin(self,e,session,cfg,resources=None,resource_state='UNKNOWN'):
        self._event(e,session);previous,v=self.s.state('C1_EXEC:'+session,{})
        previous=self._clean(previous,session);ref=e['source_ref'];text=self.s.read_source(ref)
        sequence=previous.get('goal_sequence',[])+[{'event_id':e['event_id'],'source_ref':ref}]
        # Ordinary chat turns are their own current task. Only an explicitly
        # operator-pinned task persists across later user turns; otherwise stale
        # source text would leak into unrelated native context indefinitely.
        prior_task=previous.get('active_task')
        task=prior_task if isinstance(prior_task,dict) and prior_task.get('origin')=='EXPLICIT_OPERATOR_TASK' else {'source_ref':ref,'origin':'SOURCE_USER_REQUEST','status':'UNCONFIRMED'}
        refs=[x['source_ref'] for x in sequence[-MAX_EVENTS:]]
        if task['source_ref'] not in refs:refs.append(task['source_ref'])
        state=packet('ExecState','C1_EXEC',e['event_id'],e['brain_generation_id'],refs,session_id=session,state_version=v+1,goal=text,constraints=self.s.rules(),last_event_id=e['event_id'],goal_source_ref=ref,goal_sequence=sequence[-MAX_EVENTS:],active_task=task,current_action_intent=None,salient_A_offer=ref,salient_B_offer=[],memory_refs=[],uncertainty={'report':'NO_NATIVE_ANSWER_YET','semantic_confidence':None},resource_state={'guard':resource_state,'measurements':resources or {}},permission_flags=permission_flags(AgeControl(self.s,cfg),cfg,resource_state),open_questions=previous.get('open_questions',[]),conversation_event_version=v+1)
        return self._write(state,v)
    def update(self,e,session,memories=None,offers=None,action_id=None,status=None,user_beliefs=None):
        old,v=self.s.state('C1_EXEC:'+session,{})
        if not old or old.get('last_event_id')!=e['event_id']:raise ValueError('Executive update belongs to another event')
        state=json.loads(dumps(old));fresh=packet('ExecState','C1_EXEC',e['event_id'],e['brain_generation_id'],session_id=session,state_version=v+1,goal=old['goal'],constraints=self.s.rules(),last_event_id=e['event_id'])
        state.update({name:fresh[name] for name in ['packet_id','created_monotonic_ns','created_wall_time']})
        state['constraints']=self.s.rules();state['conversation_event_version']=v+1
        if user_beliefs is not None:state['user_beliefs']=[dict(b,authority='BELIEF_NOT_FACT') for b in user_beliefs[:6]]  # WP-N13 AG11 -> C1, never constraints
        if memories is not None:
            items=[{'memory_id':m['id'],'source_ref':m['source_ref'],'scope':m['scope']} for m in memories[:16]]
            state['memory_refs']=[x for x in items if self._memory(x,session)]
        if offers is not None:
            state['salient_B_offer']=[]
            for offer in offers[:8]:
                row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(offer['packet_id'],))
                if not row or json.loads(row['payload'])!=offer or offer['event_id']!=e['event_id'] or offer['brain_generation_id']!=e['brain_generation_id']:continue
                refs=offer['evidence_refs']
                if not all(self._valid_ref(x) for x in refs):continue
                state['salient_B_offer'].append({'packet_id':offer['packet_id'],'source_refs':refs,'authority':'HYPOTHESIS_NOT_FACT'})
                if offer['offer'].get('needs_reentry'):
                    state['open_questions'].append({'source_ref':e['source_ref'],'offer_packet_id':offer['packet_id'],'uncertainty':offer['offer'].get('uncertainty','')[:160],'authority':'UNRESOLVED_HYPOTHESIS'})
            state['open_questions']=state['open_questions'][-MAX_QUESTIONS:]
        if action_id:
            action=self.s.one('SELECT event_id,corollary_id FROM actions WHERE id=?',(action_id,))
            if not action or action['event_id']!=e['event_id']:raise ValueError('Executive action binding invalid')
            state['current_action_intent']={'action_id':action_id,'corollary_packet_id':action['corollary_id'],'type':'LOCAL_TEXT_REPORT'}
        if status:
            state['uncertainty']={'report':status,'semantic_confidence':None}
            if state.get('active_task'):state['active_task']['status']='REPORTED_UNCONFIRMED' if status=='FINAL' else 'REPORT_'+status
        state['provenance']=list({dumps(ref):ref for ref in old['provenance']+[x['source_ref'] for x in state['memory_refs']]+[x for p in state['salient_B_offer'] for x in p['source_refs']]}.values())
        return self._write(state,v)
    def effort_context(self,session,e):
        """WP-D: validated continuity features for the reasoning-effort policy."""
        view=self.view(session);prior=[]
        for item in view.get('goal_sequence',[]):
            if item.get('event_id')==e['event_id']:continue
            try:prior.append(self.s.read_source(item['source_ref'])[:2000])
            except (ValueError,OSError,KeyError):continue
        return {'prior_goals':prior,'open_questions':len(view.get('open_questions',[]))}
    def control_view(self,session,e):
        """Typed executive fields around the unmodified source-bound C2 query."""
        state=self.view(session);self._event(e,session)
        return {'query_ref':e['source_ref'],'raw_query':self.s.read_source(e['source_ref']),'state_version':state.get('state_version',0),'active_task':state.get('active_task'),'constraints':state.get('constraints',self.s.rules()),'current_action_intent':state.get('current_action_intent'),'memory_refs':state.get('memory_refs',[]),'open_questions':state.get('open_questions',[]),'permission_flags':state.get('permission_flags',{}),'user_beliefs':state.get('user_beliefs',[]),'native_control_context_injection':False}
    def task(self,session,value=None,clear=False):
        old,v=self.s.state('C1_EXEC:'+session,{})
        if value is None and not clear:return self.view(session).get('active_task')
        if not old:raise ValueError('Erst eine Eingabe für den Executive-Kontext speichern')
        if not clear and (not isinstance(value,str) or not value.strip() or len(value.encode())>4096):raise ValueError('Executive-Aufgabe: 1..4096 Bytes')
        event=json.loads(self.s.one('SELECT packet FROM events WHERE id=?',(old['last_event_id'],))['packet'])
        source=self.s.source(value or 'CLEAR_ACTIVE_TASK','HUMAN_DECISION')
        self.s.add_packet('HumanDecision',packet('HumanDecision','F5_HUMAN_CONTROL',event['event_id'],event['brain_generation_id'],[source],kind='executive_task',value=value or 'CLEAR_ACTIVE_TASK',source_ref=source,learning_permission='record'))
        state=json.loads(dumps(old));fresh=packet('ExecState','C1_EXEC',event['event_id'],event['brain_generation_id'],session_id=session,state_version=v+1,goal=old['goal'],constraints=self.s.rules(),last_event_id=event['event_id'])
        state.update({name:fresh[name] for name in ['packet_id','created_monotonic_ns','created_wall_time']})
        if clear:state['open_questions']=[]
        state['active_task']=None if clear else {'source_ref':source,'origin':'EXPLICIT_OPERATOR_TASK','status':'UNCONFIRMED'}
        state['provenance'].append(source);state['conversation_event_version']=v+1
        return self._write(state,v)
    def control_context(self,e,session,resource_state='NORMAL'):
        view=self.control_view(session,e)
        refs=[e['source_ref']]+[x['source_ref'] for x in view['memory_refs']]
        if view['active_task']:refs.append(view['active_task']['source_ref'])
        p=packet('ExecutiveControlContext','C1_EXEC',e['event_id'],e['brain_generation_id'],refs,session_id=session,query_ref=e['source_ref'],state_version=view['state_version'],allowed_routes=['simple','detail','gist','both'],external_action_authority=False,resource_state=resource_state,compact_view=view,probe_only=view['state_version']==0)
        self.s.add_packet('ExecutiveControlContext',p);return p
    def control_admissible(self,p,e,session,text):
        # A typed C2 boundary, consumed before and after native invocation. Raw
        # native prompts stay unchanged, retaining measured calibration semantics.
        row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='ExecutiveControlContext'",(p['packet_id'],))
        if not row or json.loads(row['payload'])!=p:return False,'UNSTORED_CONTROL_CONTEXT'
        if p['session_id']!=session or p['event_id']!=e['event_id'] or p['brain_generation_id']!=e['brain_generation_id'] or p['query_ref']!=e['source_ref']:return False,'CONTROL_CONTEXT_BINDING'
        if not all(self._valid_ref(x) for x in p['provenance']):return False,'REVOKED_CONTROL_SOURCE'
        if self.s.read_source(p['query_ref'])!=text:return False,'CONTROL_QUERY_MISMATCH'
        _,version=self.s.state('C1_EXEC:'+session,{})
        if version!=p['state_version']:return False,'STALE_CONTROL_CONTEXT'
        if p['external_action_authority'] or p['allowed_routes']!=['simple','detail','gist','both']:return False,'NO_ACTION_PERMISSION'
        if p['resource_state'] not in {'NORMAL','UNKNOWN'}:return False,'RESOURCE_CONTROL_ABSTENTION'
        if self.s.rules()!=p['compact_view']['constraints']:return False,'STALE_CONTROL_CONSTRAINTS'
        return True,'LOCAL_PROCESSING_ONLY'
    def snapshot(self,e,session,memories=None,status='WAITING'):
        self._event(e,session);ref=e['source_ref'];items=[]
        for m in (memories or [])[:8]:
            item={'memory_id':m['id'],'source_ref':m['source_ref'],'scope':m['scope']}
            if self._memory(item,session):items.append(item)
        p=packet('OutputSnapshot','C5_RESPONSE_GOVERNOR',e['event_id'],e['brain_generation_id'],[ref]+[x['source_ref'] for x in items],session_id=session,query_ref=ref,memory_refs=items,status=status,authority='SOURCE_SYSTEM_REPORT',model_generated=False,semantic_answer_available=False)
        self.s.add_packet('OutputSnapshot',p);return p
    def report(self,session,e=None,reason='Aktueller Arbeitsstand'):
        if e is None:
            row=self.s.one("SELECT p.payload FROM packets p JOIN events e ON e.id=p.event_id WHERE p.kind='OutputSnapshot' AND e.session_id=? ORDER BY p.rowid DESC LIMIT 1",(session,))
            if not row:return '[SOURCE_SYSTEM_REPORT; Systemdiagnose; keine Modellantwort] Noch keine angenommene Eingabe in diesem Chat.'
            p=json.loads(row['payload'])
        else:
            row=self.s.one("SELECT payload FROM packets WHERE kind='OutputSnapshot' AND event_id=? ORDER BY rowid DESC LIMIT 1",(e['event_id'],))
            p=json.loads(row['payload']) if row else self.snapshot(e,session)
        if p['session_id']!=session:raise ValueError('Report session mismatch')
        lines=['[SOURCE_SYSTEM_REPORT; Systemdiagnose; keine Modellantwort]',safe_text(reason)[:300]]
        try:lines.append('Angenommene Eingabe (exakte Quelle): '+safe_text(self.s.read_source(p['query_ref']))[:480])
        except (ValueError,OSError):return lines[0]+'\nDie Eingabequelle ist gelöscht oder ungültig; keine Quellenaussage verfügbar.'
        for item in p['memory_refs']:
            if self._memory(item,session):lines.append('Passende Nutzerkorrektur (exakte Quelle): '+safe_text(self.s.read_source(item['source_ref']))[:240])
        lines.append('Status: '+p['status']+'. Eine inhaltliche Modellantwort ist in diesem Snapshot nicht belegt.')
        return '\n'.join(lines)
