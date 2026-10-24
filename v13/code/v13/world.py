"""F4 digital self/world state (§31), backed by actual action outcomes.

The timing baseline remains independent of the approved external digital latent
predictor. Only explicitly permitted completed actions can train that predictor;
own outputs never become semantic truth. RECORD_ONLY performs no weight updates.
"""
import json
import math
import statistics
from .common import digest,dumps,now,Unavailable
from .contracts import packet
from .resources import device

def _reject_json_constant(value):
    raise ValueError('Nonfinite JSON literal in persisted World state')


def _strict_json_object(raw):
    obj=json.loads(raw,parse_constant=_reject_json_constant)
    if not isinstance(obj,dict):raise ValueError('World JSON object required')
    return obj


def _finite_duration(value):
    if value is None:return True  # unfinished actions may lack a timing measurement
    try:return type(value) in (int,float) and 0<=value<=1e9 and math.isfinite(value)
    except (TypeError,OverflowError,ValueError):return False


class WorldState:
    def __init__(self,runtime):self.r=runtime;self.s=runtime.store

    def profile(self,role):
        r=self.r
        data={'role':role,'model_revision':r.models.revision(role) if role!='SOURCE_COPY' else None,
              'device':device(),'config':{k:r.cfg[k] for k in ('threads','context_tokens','answer_tokens','temperature')}}
        return {'id':digest(dumps(data)),**data}

    def forecast(self,event,role,deadline=None,native_prediction=True):
        profile=self.profile(role);length=len(self.s.read_source(event['source_ref']))
        # Strict session/profile isolation. Interrupted actions are not successful
        # latency samples; their failure count is shown separately.
        rows=self.s.rows("SELECT a.* FROM actions a JOIN events e ON e.id=a.event_id WHERE e.session_id=? ORDER BY a.created DESC LIMIT 256",(self.r.session,))
        samples=[];failures=0;rejected=0
        for row in rows:
            if row['event_id']==event['event_id']:continue
            try:
                expected=json.loads(row['expected'])
                if not isinstance(expected,dict):raise ValueError('invalid expected shape')
                old=expected.get('forecast',{})
                if not isinstance(old,dict):raise ValueError('invalid forecast shape')
                previous_profile=old.get('profile',{})
                if not isinstance(previous_profile,dict):raise ValueError('invalid profile shape')
            except (ValueError,TypeError):
                rejected+=1;continue
            if previous_profile.get('id')!=profile['id']:continue
            if row['status']!='FINAL':failures+=1;continue
            try:
                actual=json.loads(row['outcome'] or '{}')
                if not isinstance(actual,dict):raise ValueError('invalid outcome shape')
            except (ValueError,TypeError):
                rejected+=1;continue
            if actual.get('role')!=role:continue
            duration=actual.get('action_duration_s');chars=old.get('input_chars')
            # Historical SQLite JSON is untrusted, including Python's permissive NaN/Infinity parsing.
            # Bounds only reject impossible/corrupt samples; they are not model timing calibrations.
            try:
                valid_duration=(type(duration) in (int,float) and 0<=duration<=1e9 and math.isfinite(duration))
                valid_chars=(type(chars) is int and 0<=chars<=1_000_000_000)
            except (OverflowError,TypeError,ValueError):
                valid_duration=valid_chars=False
            if not (valid_duration and valid_chars):
                rejected+=1;continue
            samples.append({'action_id':row['id'],'event_id':row['event_id'],'duration_s':duration,'input_chars':chars})
            if len(samples)>=32:break
        enough=len(samples)>=3
        lengths=[x['input_chars'] for x in samples]
        covered=bool(lengths and min(lengths)*.5<=length<=max(lengths)*2)
        values=[x['duration_s'] for x in samples]
        result={'method':'EMPIRICAL_TIMING_V1','profile':profile,'input_chars':length,'sample_count':len(samples),'failed_action_count':failures,
                'sample_action_ids':[x['action_id'] for x in samples],'covered':covered,'rejected_sample_count':rejected,'prediction_authority':'HYPOTHESIS',
                'duration_median_s':statistics.median(values) if enough and covered else None,
                'observed_range_s':[min(values),max(values)] if values else None,'confidence_calibrated':False,
                'status':'SUPPORTED_BY_RECENT_OBSERVATIONS' if enough and covered else 'INSUFFICIENT_COVERAGE'}
        try:
            learned=self.r.learner.world_predict(event,role,deadline) if native_prediction else None
            if learned:result['learned_latent_prediction']=learned
        except Exception as exc:self.s.log('world_prediction_unavailable',event['event_id'],{'error':type(exc).__name__})
        p=packet('ActionPrediction','F4_FAST_FORWARD',event['event_id'],event['brain_generation_id'],[event['source_ref']],action_type='TEXT_REPORT',profile_id=profile['id'],prediction=result)
        self.s.add_packet('ActionPrediction',p);result['packet_id']=p['packet_id'];return result

    def observe(self,aid):
        action=self.s.one('SELECT * FROM actions WHERE id=?',(aid,))
        if not action or action['outcome'] is None:return None
        event=self.s.one('SELECT * FROM events WHERE id=?',(action['event_id'],))
        try:
            if not event:raise ValueError('World originating event missing')
            env=_strict_json_object(event['packet'])
            if env.get('event_id')!=action['event_id'] or env.get('authority')!='AUTHORITATIVE':
                raise ValueError('World event lineage invalid')
            self.s.read_source(env['source_ref'])
        except (ValueError,TypeError,KeyError,OSError,UnicodeError,RecursionError,OverflowError):
            self.s.log('world_observation_refused',action['event_id'],{'reason':'INVALID_EVENT_SOURCE'})
            return None
        existing=self.s.one("SELECT payload FROM packets WHERE event_id=? AND kind='PredictionOutcome' AND json_extract(payload,'$.action_id')=?",(env['event_id'],aid))
        if existing:
            self._refresh(event['session_id'])
            return json.loads(existing['payload'])['observation']
        try:
            actual=_strict_json_object(action['outcome'])
            expected=_strict_json_object(action['expected'])
            forecast=expected.get('forecast',{})
            if not isinstance(forecast,dict) or not isinstance(forecast.get('profile',{}),dict):
                raise ValueError('World forecast shape invalid')
            predicted=forecast.get('duration_median_s');duration=actual.get('action_duration_s')
            if not _finite_duration(duration) or not _finite_duration(predicted):
                raise ValueError('World timing invalid')
        except (ValueError,TypeError,KeyError,OSError,UnicodeError,RecursionError,OverflowError):
            # Original action bytes remain untouched; no fake PredictionOutcome or learning signal.
            self.s.log('world_observation_refused',action['event_id'],{'reason':'INVALID_PERSISTED_WORLD_OUTCOME'})
            return None
        comparable=action['status']=='FINAL' and actual.get('role')==forecast.get('profile',{}).get('role') and predicted is not None and duration is not None
        outcome={'action_id':aid,'status':action['status'],'self_caused':True,'observed':actual,'prediction_packet_id':forecast.get('packet_id'),
                 'timing_error_s':duration-predicted if comparable else None,'scored':bool(comparable),'semantic_success':None,
                 'causal_claim':False,'external_world_observation':False}
        if action['status']=='FINAL' and forecast.get('learned_latent_prediction'):
            try:
                transition=self.transition(aid)
                error=self.r.learner.world_score(transition,forecast['learned_latent_prediction'])
                if type(error) not in (int,float) or not math.isfinite(error):
                    raise ValueError('World latent score nonfinite')
                outcome.update(digital_latent_error=error,world_transition_packet_id=transition['packet_id'])
                self.s.add_packet('ModulatorPacket',packet('ModulatorPacket','F4_WORLD',env['event_id'],env['brain_generation_id'],[transition['source_ref'],transition['outcome_source_ref']],
                    epistemic_evidence=1.,human_correction=0.,task_success=0.,resource_cost=min(1.,max(0.,float(duration or 0))/self.r.cfg['deadline_seconds']),safety_veto=False,
                    digital_prediction_error=error,values_status='measured own digital outcome; no semantic truth reward or automatic weight permission'))
            except Exception as exc:self.s.log('world_error_unavailable',env['event_id'],{'error':type(exc).__name__})
        p=packet('PredictionOutcome','F4_WORLD',env['event_id'],env['brain_generation_id'],[env['source_ref']],action_id=aid,observation=outcome)
        self.s.add_packet('PredictionOutcome',p)
        self._refresh(event['session_id'])
        self.s.log('prediction_outcome',env['event_id'],{'status':action['status'],'duration_s':duration,'timing_error_s':outcome['timing_error_s'],'scored':comparable})
        return outcome

    def transition(self,aid):
        """Bind a real committed own outcome to intent/corollary and raw source."""
        action=self.s.one("SELECT * FROM actions WHERE id=? AND status='FINAL' AND outcome IS NOT NULL",(aid,))
        if not action:raise ValueError('Completed World action required')
        event=self.s.one('SELECT packet FROM events WHERE id=?',(action['event_id'],));env=json.loads(event['packet'])
        if env['authority']!='AUTHORITATIVE':raise ValueError('World requires authoritative input')
        copy=self.s.one("SELECT payload FROM packets WHERE kind='CorollaryCopy' AND id=?",(action['corollary_id'],))
        if not copy:raise ValueError('World CorollaryCopy missing')
        copy=json.loads(copy['payload']);actual=json.loads(action['outcome']);forecast=json.loads(action['expected']).get('forecast',{})
        intent=self.s.one("SELECT payload FROM packets WHERE kind='ActionIntent' AND event_id=? AND json_extract(payload,'$.action_id')=?",(env['event_id'],aid))
        if not intent:raise ValueError('World ActionIntent missing')
        intent=json.loads(intent['payload'])
        if intent['permission']!='local_text_only' or intent['action_type']!=action['kind'] or intent['brain_generation_id']!=env['brain_generation_id']:raise ValueError('World intent/generation mismatch')
        if not copy['self_caused'] or copy['brain_generation_id']!=env['brain_generation_id'] or copy['event_id']!=env['event_id'] or copy['action_id']!=aid or copy['expected']!=json.loads(action['expected']):raise ValueError('World action/corollary mismatch')
        own=self.s.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' AND status='FINAL' ORDER BY id DESC LIMIT 1",(env['event_id'],))
        if not own or digest(own['text'])!=actual.get('self_candidate_hash'):raise ValueError('World outcome differs from committed Self-Candidate')
        role=actual.get('role')
        if role not in ('SOURCE_COPY','C3_LANGUAGE','B1_DETAIL','B2_GIST') or forecast.get('profile',{}).get('role')!=role:raise ValueError('World measured action role mismatch')
        if role!='SOURCE_COPY' and forecast['profile'].get('model_revision')!=self.r.models.revision(role):raise Unavailable('World action model changed')
        existing=self.s.one("SELECT payload FROM packets WHERE kind='WorldTransition' AND event_id=? AND json_extract(payload,'$.action_id')=?",(env['event_id'],aid))
        if existing:
            p=json.loads(existing['payload'])
            if p['source_ref']!=env['source_ref'] or p['action_role']!=role or p['corollary_packet_id']!=copy['packet_id'] or self.s.read_source(p['outcome_source_ref'])!=own['text']:raise ValueError('Stored World transition binding changed')
            self.s.read_source(p['source_ref']);return p
        ref=self.s.source(own['text'],'DIGITAL_ACTION_OUTCOME');self.s.read_source(env['source_ref'])
        p=packet('WorldTransition','F4_WORLD',env['event_id'],env['brain_generation_id'],[env['source_ref'],ref],action_id=aid,source_ref=env['source_ref'],outcome_source_ref=ref,action_role=role,
                 corollary_packet_id=copy['packet_id'],teacher_truth_authority=False,external_world_observation=False,semantic_success=None)
        self.s.add_packet('WorldTransition',p);return p

    def _refresh(self,session):
        # Rebuild the materialized view from durable outcome packets. A crash
        # between packet insert and state write cannot silently lose an action.
        rows=self.s.rows("SELECT p.payload,p.event_id FROM packets p JOIN events e ON e.id=p.event_id WHERE p.kind='PredictionOutcome' AND e.session_id=? ORDER BY p.created DESC LIMIT 128",(session,))
        if not rows:return
        byaction={}
        for row in rows:
            observation=json.loads(row['payload'])['observation'];byaction.setdefault(observation['action_id'],observation)
            if len(byaction)==32:break
        count=self.s.one("SELECT COUNT(DISTINCT p.event_id) AS n FROM packets p JOIN events e ON e.id=p.event_id WHERE p.kind='PredictionOutcome' AND e.session_id=?",(session,))['n']
        value={'mode':'OBSERVED_DIGITAL_ACTIONS','recent':list(reversed(list(byaction.values()))),'observed_action_count':count,'last_event_id':rows[0]['event_id']}
        key='WORLD_STATE:'+session;old,v=self.s.state(key,{})
        if {k:x for k,x in old.items() if k!='updated_wall_time'}!=value:self.s.set_state(key,value|{'updated_wall_time':now()},expected=v)

    def recover(self):
        # A completed action is authoritative even if its derived observation
        # was not written before termination. No outcome is invented for an
        # unfinished DISPATCHED/OUTCOME_UNKNOWN action.
        rows=self.s.rows("SELECT a.id FROM actions a JOIN events e ON e.id=a.event_id WHERE e.session_id=? AND a.outcome IS NOT NULL AND a.expected LIKE ? AND NOT EXISTS (SELECT 1 FROM packets p WHERE p.event_id=a.event_id AND p.kind='PredictionOutcome') ORDER BY a.created",(self.r.session,'%"forecast"%'))
        for row in rows:self.observe(row['id'])
        self._refresh(self.r.session)

    def self_state(self):
        r=self.r
        state={'mode':'STRUCTURED_OBSERVED_STATE','session_id':r.session,'generation':self.s.generation_id,'updated_wall_time':now(),
               'models':r.revisions(),'native_capabilities':{'latent_tap':False,'live_receiver_latent_tap':False,'readonly_latent_tap':'EXPLICIT_PINNED_DENSE_PREFILL_HASH_CHECKED_ON_REQUEST','latent_inject':False,'body_training':__import__('v13.verification',fromlist=['native_capability_profile']).native_capability_profile(r)['body_training']['status']!='UNAVAILABLE'},
               'available_skills':['local_text','exact_source_copy','source_backed_recall','teacher_reference_selection','episodic_replay','external_route_head_training','bounded_wake_halt_training','dense_local_predictor_training','text_student_alignment_training','digital_action_predictor_training'],
               'permissions':{'external_tools':False,'weight_activation':'EXPLICIT_OPERATOR_ARTIFACT_APPROVAL','system_stage':0},
               'learning':{'mode':r.cfg['learning_mode'],'active_artifact_count':len(self.s.generation()['hashes']),'body_learning':False},
               'resources':r.resources(),'teacher':{'enabled':r.cfg['teacher_enabled'],'revision':r.models.revision('TEACHER')},
               'memory':{'active_corrections':self.s.one('SELECT COUNT(*) AS n FROM memories WHERE active=1')['n'],'pending_replay':self.s.one("SELECT COUNT(*) AS n FROM replay WHERE status='PENDING'")['n']},
               'unfinished_actions':self.s.one("SELECT COUNT(*) AS n FROM actions WHERE status IN ('DISPATCHED','OUTCOME_UNKNOWN')")['n'],
               'calibration':{'native_control_confidence':False,'native_route_agreement_active':'control_calibration' in self.s.components(),
                              'native_route_agreement_scope':'HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY','semantic_truth_authority':False,'timing_forecast':False}}
        self.s.set_state('SELF_MODEL:'+r.session,state);return state

    def world_state(self):return self.s.state('WORLD_STATE:'+self.r.session,{'mode':'NO_OBSERVATIONS','recent':[],'observed_action_count':0})[0]
