import contextlib
import inspect
import json
import queue
import re
import threading
import time
from .common import digest,dumps,safe_text,visible_text,atomic_write,Cancelled,Unavailable,Limits
from .config import initialize
from .contracts import packet
from .store import Store
from .models import ModelManager,ROLES
from . import semantic_memory,episodes,duplex
from .agi import live as agi_live
from .runners import RunnerPool,NeedleRunner,check,kill_process
from .resources import snapshot,ResourceGuard,prune_runner_logs
from . import resource_modes as rmodes
from . import observer_schedule as obsched
from .memory import Memory
from .consolidation import Consolidation
from .cognition import Cognition,scaffold_route,ROUTES,segments,percept_mode
from .learning import Learner
from .world import WorldState
from .executive import Executive
from .pressure import NativePressureMonitor
from . import effort
from .prompts import text as prompt
from .inputs import save_context
from . import age as agectl
from .focal import FocalLoop,ActionGate
from . import attention as attctl
from . import toolstep as toolctl
from . import skilllive
from . import jefoutcome
from . import fastpolicy as fastpol
from . import context_os as ctxos
from . import selfmodel as selfctl
from . import latewatch
from . import jefbridge as jefctl
from . import fastforward as ffctl
from . import reflex as reflexctl
from . import actionlearn as c5ctl
from . import transaction as txctl

class Runtime:
    @property
    def session(self):
        return getattr(self._session_local,'session_id',self._selected_session)
    @session.setter
    def session(self,value):self._selected_session=value
    def __init__(self,home,notify=None):
        self._session_local=threading.local();self._selected_session=None
        self.home=home;self.cfg=initialize(home);self.store=Store(home,self.cfg['log_retention_days']);prune_runner_logs(home,self.cfg['log_retention_days']);self.models=ModelManager(home,self.cfg.get('b2_control','two_body'));self.pool=RunnerPool(home,self.models,self.cfg,approval_store=self.store);self.needle=NeedleRunner(home,self.models)
        self.store.ensure_generation_snapshot(self.cfg,self.revisions())
        self.cancel_event=threading.Event()
        self.session=self.store.meta('last_session') or self.store.new_session();self.memory=Memory(self.store,self.cfg);semantic_memory.attach(self);self.cognition=Cognition(self);self.learner=Learner(self);self.world=WorldState(self)
        self.consolidation=Consolidation(self.store,self.cfg,self.memory);self.memory.consolidation=self.consolidation
        self.executive=Executive(self.store);self.turn_event=None
        self.world.recover()
        try:txctl.Transactions(self.store).recover()  # WP-K IH-H14: EXECUTING after a crash -> UNKNOWN, never re-run
        except Exception as exc:self.store.log('action_tx_recover_failed',None,{'error':type(exc).__name__})
        pending=self.store.pending_turns()
        self.guard=ResourceGuard(self.cfg);self.guard.load_profile(self.store);self.notify=notify or (lambda text:None);self.stop=threading.Event();self.wake=threading.Event();self.lock=threading.RLock();self.jobs=queue.Queue(max(self.cfg['queue_count'],len(pending)));self.queued_bytes=0;self.current=None;self.paused=self.store.queue_paused();self.status='Pausiert' if self.paused else 'Bereit';self.closed=False
        for row in pending:
            queued=time.monotonic()-max(0.,time.time()-row['accepted_at'])
            self.jobs.put_nowait(('turn',row['event'],row['bytes'],queued));self.queued_bytes+=row['bytes']
        from . import bodies
        bodies.attach(self)  # WP-N11: AG0 slot routing + AG13 body residency in the RunnerPool
        from .sleep import SleepRuntime
        self.sleep=SleepRuntime(self)  # WP-E: G13 wake scheduler + §94 sleep phases
        self.worker=threading.Thread(target=self._worker,name='V13-coordinator',daemon=True);self.worker.start()
    def notice(self,text):self.notify(safe_text(text))
    def resources(self):return snapshot(self.home,self.pool.pids()+self.needle.pids()+self.memory.semantic_keys.encoder.pids())
    def revisions(self):return {role:self.models.revision(role) for role in ROLES}
    def idle(self):
        with self.lock:return self.current is None and self.jobs.empty() and self.store.queue_stats()['count']==0
    def require_idle(self):
        if not self.idle():raise ValueError('Erst laufenden Vorgang beenden (:cancel); dann erneut ausführen.')
    def submit(self,text):
        b=len(text.encode())
        if not text.strip():raise ValueError('Leere Eingabe')
        if b>self.cfg['input_bytes']:raise Limits('Eingabe zu lang: '+str(self.cfg['input_bytes'])+' Bytes')
        with self.lock:
            if self.stop.is_set():raise ValueError('Runtime beendet')
            if self.current=='probe':raise Limits('Probe läuft in einem Testkontext; danach wieder Chat-Eingaben senden')
            if self.jobs.full() or self.queued_bytes+b>self.cfg['queue_bytes']:raise Limits('Warteschlange voll; Eingabe wurde nicht angenommen')
            e=self.store.accept_turn(self.session,text,self.cfg['queue_count'],self.cfg['queue_bytes'],self.cfg['input_bytes']);self.jobs.put_nowait(('turn',e,b,time.monotonic()));self.queued_bytes+=b
            if self.current in {'observers','shadow','dream','replay','tap','sleep'}:self.cancel_event.set()
            live=duplex.on_input(self,e['event_id'],text)  # WP-N14 live path: decide on overlap, no I/O under the lock
        try:duplex.record(self,live)
        except Exception as exc:self.store.log('duplex_unavailable',e['event_id'],{'stage':'record','error':type(exc).__name__})
        self.wake.set();self.notice('Eingabe gespeichert.');return e['event_id']
    def enqueue(self,kind,payload=None):
        with self.lock:
            if not self.idle():raise ValueError('Aufgabe läuft; erst :cancel oder warten')
            self.jobs.put_nowait((kind,payload,0,time.monotonic()))
        self.wake.set()
    def cancel(self):
        with self.lock:self.cancel_event.set()
        self.notice('Abbruch angefordert; vorhandener Text bleibt gespeichert.')
    def _pressure_cancel(self):
        with self.lock:
            if self.cancel_event.is_set():return False
            self.cancel_event.set();return True
    def pause(self):
        with self.lock:self.store.set_queue_paused(True);self.paused=True;self.status='Pausiert'
        self.cancel()
    def resume(self):
        with self.lock:self.store.set_queue_paused(False);self.paused=False
        self.wake.set();self.notice('Wartende Aufgaben werden fortgesetzt.')
    def _worker(self):
        while not self.stop.is_set():
            if self.paused:self.wake.wait(.2);self.wake.clear();continue
            with self.lock:
                if self.stop.is_set():break
                if self.paused:continue
                if self.jobs.empty() and not self.paused:
                    pending=self.store.pending_turns(1)
                    if pending:
                        row=pending[0];queued=time.monotonic()-max(0.,time.time()-row['accepted_at'])
                        self.jobs.put_nowait(('turn',row['event'],row['bytes'],queued));self.queued_bytes+=row['bytes']
                try:kind,payload,b,queued=self.jobs.get_nowait()
                except queue.Empty:kind=None
                if kind=='turn' and not self.store.claim_turn(payload['event_id']):
                    self.queued_bytes-=b;self.jobs.task_done();kind=None
                if kind:self.queued_bytes-=b;self.current=kind;self.cancel_event.clear()
            if not kind:
                try:self.sleep.tick()  # idle/timer/replay wakes; enqueues background 'sleep' only when idle
                except Exception as exc:self.store.log('job_error',None,{'kind':'sleep','error':type(exc).__name__})
                self.wake.wait(.2);self.wake.clear();continue
            try:
                self.status=kind
                if kind=='turn':
                    owner=self.store.one('SELECT session_id FROM events WHERE id=?',(payload['event_id'],))
                    if not owner:raise ValueError('Angenommene Anfrage ohne Chat')
                    self._session_local.session_id=owner['session_id']
                    if time.monotonic()-queued>self.cfg['queue_ttl_seconds']:self._rejected(payload,'Warteschlangen-Zeitlimit; bitte erneut senden.')
                    else:self._turn(payload)
                elif kind=='download':self.models.install(payload or 'all',self.notice,self.cancel_event)
                elif kind=='shadow':
                    if payload=='memory_retrieval':self.notice(self.learner.shadow_retrieval())
                    elif payload=='output_adapter':self.notice(self.learner.shadow_output_adapter())
                    elif payload=='control_calibration':self.notice(self.learner.shadow_control_calibration())
                    elif payload=='world_predictor':self.notice(self.learner.shadow_world())
                    elif payload=='a3_student':self.notice(self.learner.shadow_student())
                    elif payload in {'b1_predictor','b2_predictor'}:self.notice(self.learner.shadow_predictor('B1_DETAIL' if payload=='b1_predictor' else 'B2_GIST'))
                    else:self.notice(self.learner.shadow() if payload in (None,'route') else self.learner.shadow_readout(payload))
                elif kind=='causal_import':self.notice(self.learner.import_causal_output(payload['dataset'],payload['trained']))
                elif kind=='teacher':self._teacher(payload)
                elif kind=='dream':self._dream()
                elif kind=='sleep':self.sleep.job(payload)
                elif kind=='replay':self.notice(dumps(self._replay(payload)))
                elif kind=='tap':
                    e,role,ref=payload
                    try:self.notice(dumps(self.cognition.tap(role,e,ref,time.monotonic()+self.cfg['observer_seconds'])))
                    finally:self.pool.unload()
                elif kind=='probe':
                    if payload=='sustained':
                        from .proofs import probe_sustained
                        self.notice(dumps(probe_sustained(self)))
                    elif payload=='jef-modes':
                        from .proofs import probe_jef_modes
                        self.notice(dumps(probe_jef_modes(self)))
                    elif payload=='body-state':
                        from .proofs import probe_body_state
                        self.notice(dumps(probe_body_state(self)))
                    elif payload=='step12':
                        from .proofs import probe_step12
                        self.notice(dumps(probe_step12(self)))
                    else:
                        from .verification import probe
                        self.notice(dumps(probe(self)))
                else:raise ValueError('Job unbekannt')
            except BaseException as exc:
                self.store.log('job_error',None,{'kind':kind,'error':type(exc).__name__,'detail':str(exc)[:1000]});self.notice(f'{kind}: {type(exc).__name__}: {exc}')
                if kind=='turn' and not self.store.one("SELECT id FROM messages WHERE event_id=? AND role='assistant'",(payload['event_id'],)):self._rejected(payload,str(exc))
            finally:
                try:
                    if kind=='turn':
                        row=self.store.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(payload['event_id'],))
                        terminal={'FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED'}
                        status=row['status'] if row and row['status'] in terminal else 'INTERRUPTED'
                        if row and row['status'] not in terminal:
                            if not row['text']:self.store.append_message(row['id'],'[Systemdiagnose; keine Modellantwort] Verarbeitung unterbrochen; :doctor prüfen.')
                            self.store.finish_message(row['id'],status,json.loads(row['metadata'])|{'coordinator_interrupted':True})
                        self.store.finish_turn(payload['event_id'],status)
                except Exception as exc:
                    self.notice('Abschluss konnte nicht gespeichert werden: '+type(exc).__name__+'; Neustart rekonstruiert den Status.')
                finally:
                    if kind=='turn':self.turn_event=None
                    if hasattr(self._session_local,'session_id'):del self._session_local.session_id
                    with self.lock:self.current=None;self.jobs.task_done();self.status='Pausiert' if self.paused else 'Bereit'
    def _rejected(self,e,reason):
        row=self.store.one('SELECT session_id FROM events WHERE id=?',(e['event_id'],));self.store.message(row['session_id'],e['event_id'],'assistant','[Systemdiagnose] '+safe_text(reason),'ERROR',{'model_generated':False})
    def last_answer(self):return self.store.one("SELECT * FROM messages WHERE session_id=? AND role='assistant' AND status IN ('FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED') ORDER BY id DESC LIMIT 1",(self.session,))
    def force_report(self):
        # Read-only exact snapshot is visible immediately; deliberation stops.
        with self.lock:
            e=self.turn_event
            if self.current=='turn':self.cancel_event.set()
        if e:
            row=self.store.one("SELECT text,status,metadata FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(e['event_id'],))
            if row and row['text'].strip():
                snap='[CURRENT_OUTPUT_SNAPSHOT; '+row['status']+']\n'+row['text']
                try:
                    from .broker import Broker
                    Broker(self).snapshot_check(e,snap)  # WP-T7: C6 check of the read-only snapshot egress
                except Exception as exc:self.store.log('broker_unavailable',e['event_id'],{'stage':'snapshot','error':type(exc).__name__})
                return snap
        else:
            row=self.last_answer()
            if row and row['text'].strip():return '[CURRENT_OUTPUT_SNAPSHOT; '+row['status']+']\n'+row['text']
        owner=self.store.one('SELECT session_id FROM events WHERE id=?',(e['event_id'],)) if e else None
        return self.executive.report(owner['session_id'] if owner else self.session,e,'Operator erzwingt den aktuellen quellengebundenen Stand; weitere Deliberation wird beendet.')
    def _head_shadow(self,text,e,deadline):
        """WP-Z6i: what the active learned route head alone would do (None route below the decision margin)."""
        if e is None:return None
        entry=self.store.components().get('route') or {}
        if not entry.get('update_id'):return None
        p=self.learner.propose(text,e['source_ref']['source_id'],min(deadline,time.monotonic()+self.cfg['control_seconds']))
        return ((p['route'] if p and p['margin']>=.05 else None),entry['update_id'])
    def _route(self,text,e,deadline):
        override=self.cfg['route_override']
        if override!='auto':return override,{'source':'OPERATOR_ROUTE_OVERRIDE'}
        procedure=self.consolidation.route(text,self.session,cancel=self.cancel_event,deadline=deadline)
        if procedure:return procedure['route'],procedure
        episodic=None
        try:  # WP-U10 §9.1 fast episodic: one human route correction on a very similar request (shadow unless active)
            from .episodic_route import for_turn
            ep_route,episodic=for_turn(self.store,text,self.session,head=lambda:self._head_shadow(text,e,deadline),event_id=e['event_id'] if e else None)
            if ep_route:return ep_route,episodic
        except Exception as exc:self.store.log('episodic_route_unavailable',e['event_id'] if e else None,{'error':type(exc).__name__})
        route=scaffold_route(text);info={'source':'BOOT_SCAFFOLD','scaffold':route}
        if episodic:info['episodic_route']=episodic
        context=self.executive.control_context(e,self.session,self.guard.state)
        info['executive_control_context_id']=context['packet_id']
        allowed,reason=self.executive.control_admissible(context,e,self.session,text)
        if not allowed:return route,info|{'executive_control_abstention':reason}
        self.needle.last_metrics={}
        try:
            learned=self.learner.propose(text,e['source_ref']['source_id'],min(deadline,time.monotonic()+self.cfg['control_seconds']))
            if learned:
                shadow=self.learner.compare_student_route(e,learned)
                if shadow:info['student_shadow']=shadow
            if learned and learned['margin']>=.05:return learned['route'],info|{'source':'APPROVED_EXTERNAL_HEAD','decision':learned}
            control=self.needle.control(text,self.cancel_event,min(deadline,time.monotonic()+self.cfg['control_seconds']))
            allowed,reason=self.executive.control_admissible(context,e,self.session,text)
            if not allowed:return route,info|{'executive_control_abstention':reason}
            info['executive_control_policy']='LOCAL_PROCESSING_ONLY'
            info['native_control']=control;info['native_control_metrics']=dict(self.needle.last_metrics)
            # Only a successful, validated, unambiguous native
            # select_processing call can advise the scaffold. Never scan
            # arbitrary nested JSON/diagnostics for a route string.
            from .control_calibration_worker import observation
            proposals=[]
            try:
                observed=observation(control)
                calls=control.get('function_calls')
                if (type(calls) is list and len(calls)==1
                        and type(calls[0]) is dict
                        and calls[0].get('name')=='select_processing'
                        and observed['proposal_count']==1
                        and observed['ambiguous'] is False):
                    proposals=[observed['route']]
                else:info['native_control_rejected']=True
            except (ValueError,TypeError,KeyError,OverflowError):
                info['native_control_rejected']=True
            info['calibrated']=False
            calibrated=self.learner.control_calibrate(e,control)
            if calibrated and calibrated['in_support']:
                info.update(calibrated=True,control_calibration=calibrated)
                if calibrated['calibrated_confidence']<.6:proposals=[];info['native_control_rejected']=True
            elif self.store.components().get('control_calibration'):
                proposals=[];info['native_control_rejected']=True
            if route=='simple' and proposals:route=proposals[0];info['source']='NATIVE_C2_ADVISORY'
        except Cancelled:raise
        except Exception as exc:
            info['control_unavailable']=str(exc)[:200];info['native_control_metrics']=dict(self.needle.last_metrics)
            try:  # WP-T4 A3 T2: promoted student routes only while the teacher path is down
                from .aplane import student_fallback
                fb=student_fallback(self,e,info)
                if fb:return fb
            except Cancelled:raise
            except Exception as exc2:info['student_fallback_error']=type(exc2).__name__
        return route,info
    def _causal_output_context(self,e,messages,context_refs):
        """Preserve explicit human feedback lineage without a legacy feature call."""
        if not messages or messages[-1]!={'role':'user','content':self.store.read_source(e['source_ref'])}:
            raise ValueError('Native output context must end with the actual source query')
        refs=[e['source_ref'],*context_refs]
        for ref in refs:self.store.read_source(ref)
        revision=self.learner.output_context_revision()
        context=self.store.source(dumps(messages),'C3_OUTPUT_CONTEXT');refs.append(context)
        self.store.add_packet('OutputAdapterContext',packet('OutputAdapterContext','C3_LANGUAGE',e['event_id'],self.store.generation_id,refs,context_ref=context,model_revision=self.models.revision('C3_LANGUAGE'),context_revision=revision,native_role='C3_LANGUAGE'))
        reason='UNAVAILABLE_NO_APPROVED_SAME_CAUSAL_HEAD'
        self.store.add_packet('OutputAdapterDecision',packet('OutputAdapterDecision','C3_LANGUAGE',e['event_id'],self.store.generation_id,[e['source_ref'],context],context_ref=context,model_revision=self.models.revision('C3_LANGUAGE'),context_revision=revision,prediction=None,semantic_truth_authority=False,fallback_reason=reason))
        self.store.log('output_adapter',e['event_id'],{'component':'output_adapter','prediction':None,'fallback_reason':reason,'decode_mode':'same_causal_zero'})
        return reason
    def _world_error(self):
        try:  # WP-N2: recent own world-prediction error opens Inquisition (WORLD_PREDICTION_ERROR)
            from .deliberation import controller
            return controller(self).world_error(self.session)
        except Exception:return False
    def _action_gain(self,eid):
        try:return attctl.controller(self).gains()['action']  # WP-N5 thalamic action coupling for C5 (caution lowers it)
        except Exception as exc:self.store.log('attention_unavailable',eid,{'stage':'action_gain','error':type(exc).__name__});return None
    def _turn(self,e):
        eid=e['event_id'];g=e['brain_generation_id'];text=self.store.read_source(e['source_ref']);start=time.monotonic();deadline=start+self.cfg['deadline_seconds'];mid=self.store.message(self.session,eid,'assistant');meta={'model_generated':False,'memory_ids':[],'output_owner':'C5_REPORT_BROKER','effective_config':dict(self.cfg),'first_output_monotonic_ns':None};status='FINAL';output='';aid=None;offers=[];version=0;direct=False;runner=None;wake_decision=None;effort_plan=None;ff_x=ff_key=ff_surprise=None
        self.turn_event=e;self.bodies.begin_turn(eid)
        governor=self.executive.snapshot(e,self.session)
        meta['output_snapshot_id']=governor['packet_id'];meta['context_source_refs']=[e['source_ref']]
        meta['stage_marks_s']={}
        def mark(name):meta['stage_marks_s'][name]=time.monotonic()-start;meta['turn_stage']=name
        mark('ingress')
        monitor=NativePressureMonitor(self.home,self.cfg,pids=lambda:self.pool.pids()+self.needle.pids(),cancel=self.cancel_event,guard=self.guard,phase=lambda:meta.get('turn_stage'),request_cancel=self._pressure_cancel)
        try:
            monitor.start()
            check(self.cancel_event,deadline);resource=self.resources();state=self.guard.update(resource)
            rmode=self.guard.mode;rpol=rmodes.policy(rmode);meta['resource_mode']={'mode':rmode,'reasons':list(self.guard.reasons),'profile':self.guard.profile.get('status')}  # §97.2
            body={'modulation':{}}
            try:body=selfctl.controller(self).body(resource,True);meta['interoception']={'feeling':body['feeling'],'strain':body['strain'],'modulation':body['modulation']}  # WP-N9 §7.4
            except Exception as exc:self.store.log('self_unavailable',eid,{'stage':'body','error':type(exc).__name__})
            if state=='CRITICAL':
                try:meta['reflex']=[reflexctl.controller(self).critical(eid,self.pool,resource)]  # WP-F §5.3 OOM/heat reflex
                except Exception as exc:self.store.log('reflex_unavailable',eid,{'error':type(exc).__name__})
                raise Limits('Ressourcenlimit: zu wenig freier RAM oder zu heiß; :resources')
            from .output_policy import match
            mark('policy_check');fixed_policy=match(self.store,text)
            mark('perception_and_state')
            if fixed_policy:
                self.store.add_packet('PerceptPacket',packet('PerceptPacket','A5_PERCEPT',eid,g,[e['source_ref']],source_ref=e['source_ref'],segments=segments(text,e['source_ref'],240,percept_mode(self.cfg)),modality='text'))
            else:
                percept_packet=self.cognition.percept(e)
                try:  # WP-N5 A4 span salience; high-res re-looks are granted as exact source spans (no text in payload)
                    att=attctl.controller(self);a4=att.perceive_packet(percept_packet,goal=text)
                    if a4['requests']:att.admit(eid,a4['requests'],pressure=rpol['focal_pressure'],providers={'A_SOURCE':lambda r:{'source_ref':r['source_ref']}})
                except Exception as exc:self.store.log('attention_unavailable',eid,{'error':type(exc).__name__})
            exec_state=self.executive.begin(e,self.session,self.cfg,resource,rmode);version=exec_state['state_version']
            mark('memory_recall');retrieval_deadline=min(deadline,time.monotonic()+self.cfg['retrieval_seconds'])
            semantic=(lambda m:self.learner.retrieve(e,m,retrieval_deadline)) if self.store.components().get('memory_retrieval') else None
            if fixed_policy:memories=[]
            else:  # WP-T1 memory head (scaffold 'recall' unless an approved readout says skip/deep)
                top_k,cue,mem_head=fastpol.recall_plan(self,e,text,min(deadline,time.monotonic()+self.cfg['control_seconds']))
                if mem_head:meta['memory_head']={'action':mem_head.get('action'),'learned':bool(mem_head.get('learned')),'packet_id':mem_head.get('packet_id')}
                memories=self.memory.recall(cue,self.session,semantic,cancel=self.cancel_event,deadline=deadline,top_k=rmodes.scaled(self.cfg['memory_top_k'] if top_k is None else top_k,rmode,'context_scale'))  # §97.2 YELLOW+: less context
            meta['memory_ids']=[m['id'] for m in memories]
            if not fixed_policy:
                try:memories=episodes.recall_turn(self,text,memories,meta);meta['memory_ids']=[m['id'] for m in memories]  # WP-N8 §9.4 associative spread (SHADOW default)
                except Exception as exc:self.store.log('episodes_unavailable',eid,{'stage':'spread','error':type(exc).__name__})
            warm_ids=[]
            if not fixed_policy:
                try:  # WP-N7 §9.1 warm/activity-silent memory: reactivated only in ACTIVE; SHADOW records ids in the ContextPlan
                    warm=ctxos.controller(self).warm(text,self.session,memories);warm_ids=warm['ids']
                    if warm['applied'] and warm['items']:memories=memories+warm['items'];meta['memory_ids']=[m['id'] for m in memories];meta['warm_memory_ids']=warm_ids
                except Exception as exc:self.store.log('context_os_unavailable',eid,{'stage':'warm','error':type(exc).__name__})
            meta['memory_retrieval']=[{'memory_id':m['id'],'source_ref':m['source_ref'],'retrieval_score':m['retrieval_score'],'scope':m['scope'],'retrieval_policy':m.get('retrieval_policy'),'consolidation':m.get('consolidation'),'embedding_similarity':m.get('embedding_similarity'),'retrieval_channel':m.get('retrieval_channel')} for m in memories]
            exec_state=self.executive.update(e,self.session,memories=memories);version=exec_state['state_version']
            governor=self.executive.snapshot(e,self.session,memories);meta['output_snapshot_id']=governor['packet_id']
            jbp=self.store.add_packet('JEFBroadcastPacket',packet('JEFBroadcastPacket','C1_EXEC',eid,g,exec_state['provenance'],state_version=version,goal=text,constraints=exec_state['constraints'],source_refs=exec_state['provenance'],active_task=exec_state['active_task'],memory_refs=exec_state['memory_refs'],open_questions=exec_state['open_questions'],permission_flags=exec_state['permission_flags']))
            try:  # WP-N3 §3.4.2 JEF_BROADCAST_CACHE for the observer passes
                from .focal import Workspace
                jefctl.controller(self).broadcast_cache(e,jbp,exec_state,[s['item_id'] for s in Workspace(self.store,self.session).view()['slots']],selfctl.controller(self).corollary_view(),meta.get('interoception',{}).get('feeling'))
            except Exception as exc:self.store.log('jef_bridge_unavailable',eid,{'stage':'broadcast','error':type(exc).__name__})
            mark('routing');exact=re.fullmatch(r'(?:Kopiere exakt|Copy exactly):\s*([\s\S]+)',text,re.I)
            if fixed_policy:
                direct=True;route='simple';meta['route']={'source':'EXPLICIT_EXACT_POLICY'}
                refs=[e['source_ref'],fixed_policy['query_ref'],fixed_policy['answer_ref']]
                decision=self.store.add_packet('OutputPolicyDecision',packet('OutputPolicyDecision','C5_REPORT_BROKER',eid,g,refs,rule_id=fixed_policy['rule_id'],rule_version=fixed_policy['rule_version'],query_ref=fixed_policy['query_ref'],answer_ref=fixed_policy['answer_ref'],output_authority='APPROVED_FIXED_RULE',model_generated=False))
                meta.update(output_policy={k:fixed_policy[k] for k in ['kind','rule_id','rule_version','query_ref','answer_ref']},output_authority='APPROVED_FIXED_RULE',exact_policy_matched=True,skipped_native_stages=['A3_NATIVE_ALIGNMENT','SEMANTIC_RECALL','C2_CONTROL','B_OBSERVERS','C3_DECODE','NATIVE_WORLD_PREDICTION'])
                meta['context_source_refs']=refs
            elif exact:direct=True;route='simple';meta['route']={'source':'EXPLICIT_EXACT_COPY'}
            else:  # WP-T6: a trusted route-only skill routes before C_fast (no Needle call); else the full path
                auto=skilllive.automatic(self,e,text,meta) if self.cfg['route_override']=='auto' else None
                route,meta['route']=auto or self._route(text,e,deadline)
            if not meta.get('skill'):route=agi_live.skill_route(self,e,text,route,direct,meta)  # WP-N13 AG4 -> C5
            if not direct:skilllive.shadow_candidates(self,e,text,meta)  # WP-T6 learning-stage skills: parity after the turn
            if not direct:
                try:meta['c2_packet']=fastpol.c2_packet(self,e,text,route,meta.get('route'))  # WP-T1 structured C2 output
                except Exception as exc:self.store.log('fast_policy_unavailable',eid,{'stage':'c2_packet','error':type(exc).__name__})
                act,sk=fastpol.head(self,'skill',e,'skill' if meta.get('skill') else 'none')  # WP-T1 skill head may veto, never invent
                if sk and sk.get('learned') and act=='none' and meta.get('skill'):
                    meta['skill']['vetoed_by']=sk.get('packet_id')
                    if meta['skill'].get('automatic'):route,meta['route']=self._route(text,e,deadline)  # WP-T6 fallback: full C_fast path
                    else:route=meta['skill']['prior_route']
            mark('preanswer_observers')
            # WP-D reasoning effort (G5B): one bounded plan decides wake/re-entry/focal budgets.
            observer_end=start+self.cfg['deadline_seconds']*.45;effort_mode=effort.get_mode(self.store)
            age_lim=effort.age_limits(agectl.controller(self),rmode)
            effort_sig=effort.signals(text,route,meta.get('route'),memories,**self.executive.effort_context(self.session,e))
            effort_sig=agi_live.before_effort(self,e,meta,effort_sig)  # WP-N13 AG9 -> effort, AG11 -> C1
            effort_plan=effort.decide(effort_mode,effort_sig,direct=direct,observers=self.cfg['observer_mode']!='off',resource_state=state,resource_mode=rmode,observer_window_s=observer_end-time.monotonic(),cfg=self.cfg,age=age_lim)
            wake_route=effort_plan['wake'];wake_source='EFFORT_POLICY'
            if not direct and rpol['learned_wake'] and self.cfg['observer_mode']!='off':
                wake_decision=self.learner.decide('wake',e,wake_route,min(deadline,time.monotonic()+self.cfg['control_seconds']),enabled=self.cfg['route_override']=='auto' and effort_plan['learned_wake_allowed'])
                meta['wake_decision']=wake_decision
                if wake_decision['learned']:wake_route,wake_source=effort.resolve_wake(effort_plan,wake_decision['action'])
            try:  # WP-F §7.1/§75 fast-forward prediction, procedural wake (may only skip body passes), §5.3 timeout reflex
                ffc=ffctl.controller(self);ff_key=ffctl.pattern(text,route,effort_sig,memories)
                if not direct:
                    proc=ffc.procedural(ff_key,effort_sig);meta['procedural']=proc
                    if proc['apply'] and set(effort.roles(proc['wake']))<=set(effort.roles(wake_route)) and proc['wake']!=wake_route:wake_route,wake_source=proc['wake'],'PROCEDURAL_FAST_FORWARD'
                ff_x=ffctl.features(text,route,wake_route,memories,effort_plan['effort'],effort_sig);meta['fast_forward']=ffc.predict(ff_x)
                if not direct and wake_route!='none':
                    fired=reflexctl.controller(self).timeout_check(eid,deadline-time.monotonic(),meta['fast_forward']['duration_s'])
                    if fired:wake_route,wake_source='none','REFLEX_IMMINENT_TIMEOUT';meta['reflex']=meta.get('reflex',[])+[fired]
            except Exception as exc:self.store.log('fast_forward_unavailable',eid,{'stage':'predict','error':type(exc).__name__})
            meta['reasoning_effort']=effort.record(self.store,e,effort_plan,effort_sig,wake_route,wake_source)['packet_id']
            reenter=halt=None
            if wake_route in {'detail','gist','both'} and rpol['max_observer_bodies'] and not direct and self.cfg['observer_mode']!='off':
                roles=rmodes.cap_roles(effort.roles(wake_route),rmode);peers={};observer_seconds=max(1.,self.cfg['observer_seconds']*effort_plan['observer_scale'])  # §97.2 ORANGE: one body
                try:  # WP-N3 §24.25: learned observer frequency, lowers the observer time only in :jef active
                    jo=jefctl.controller(self).observer_scale(wake_route);meta['jef_observer']=jo
                    if jo['applied']:observer_seconds=max(1.,observer_seconds*jo['scale'])
                except Exception as exc:self.store.log('jef_observer_unavailable',eid,{'error':type(exc).__name__})
                _,channel_head=fastpol.head(self,'channel',e,self.cfg['channel'])  # WP-T1 channel head (applies only when approved)
                def ask(role,focus=None,use_peer=True):
                    p=self.cognition.offer(role,e,version,min(observer_end,time.monotonic()+observer_seconds),peers.get(role) if use_peer else None,valid_until=deadline,**({'focus':focus} if focus and 'focus' in inspect.signature(self.cognition.offer).parameters else {}))  # replaced/older offers take no focus
                    other='B2_GIST' if role=='B1_DETAIL' else 'B1_DETAIL';peers[other]=self.cognition.communicate(p,other,**({'fast':channel_head} if channel_head and channel_head.get('learned') else {}));return p
                sched=obsched.plan(self.cfg.get('observer_schedule',obsched.DEFAULT),roles,eid,self.cfg.get('observer_sample_rate',.5),parallel_ok=rpol['max_observer_bodies']>1 and bool(getattr(getattr(self.pool,'fabric',None),'enabled',False)))  # §22.2.4 deployment knob
                meta['observer_schedule']={k:sched[k] for k in ('schedule','pre','parallel','post','reason')}
                offers+=obsched.run(sched,lambda role,use_peer:ask(role,use_peer=use_peer),observer_end,lambda role,exc:self.store.log('offer_rejected',eid,{'role':role,'error':str(exc)[:300]}),cancelled=(Cancelled,))
                def reenter(role,focus=None):
                    try:return ask(role,focus)
                    except Cancelled:raise
                    except Exception as exc:self.store.log('reentry_failed',eid,{'role':role,'error':str(exc)[:300]})
                def halt(fresh,baseline):
                    meta['halt_decision']=self.learner.decide('halt',e,baseline,min(observer_end,time.monotonic()+self.cfg['control_seconds']),fresh,enabled=self.cfg['route_override']=='auto');return meta['halt_decision']
            # WP-N1 C4 focal loop: coalition, Inquisition P1/P2, targeted re-entry (replaces the fixed one-shot re-entry).
            selected=[];focal_run=None
            if not direct:
                mark('focal_loop')
                pre_offer_ids=[p['packet_id'] for p in offers]
                focal_run=FocalLoop(self).run(e,version,offers,goal=text,memories=memories,plan=effort_plan,sig=effort_sig,age=age_lim,deadline=observer_end,query=reenter,halt=halt,rules=[r for r in self.store.rules() if isinstance(r,str)],session=self.session,attention=attctl.controller(self),pressure=rpol['focal_pressure'],world_error=self._world_error())
                offers=focal_run['offers'];selected=focal_run['selected']
                meta['focal']={'decision':focal_run['decision'],'cycles':len(focal_run['trajectory']),'coalition':[x['item_id'] for x in focal_run['coalition']],'inquisition':[x['verdict'] for x in focal_run['inquisition']]}
            mark('output_prepare')
            # WP-N4 C5 action gate: candidate competition under permissions; BOOT reproduces the route table.
            view=focal_run['trajectory'][-1]['view'] if focal_run and focal_run['trajectory'] else None
            tool_plan=tool_result=tool_shadow=tool_pending=None
            if not direct:
                try:tool_plan=toolctl.ToolStep(self).plan(e,text,offers=selected,version=version)  # WP-K/AG10: concrete tool proposal -> C5 candidate under IH-H29
                except Exception as exc:self.store.log('tool_step_unavailable',eid,{'stage':'plan','error':type(exc).__name__})
            clar=agi_live.clarify(self,meta) if not direct else None  # WP-N13 AG9 abstain -> C5 ASK_USER
            c5=ActionGate(self.store).select(e,route=route,direct=direct,resource_state=state,coalition=focal_run['coalition'] if focal_run else [],view=view,age=age_lim,effort=effort_plan['effort'] if effort_plan else None,gain_action=self._action_gain(eid),tool=tool_plan,clarify=clar)
            clarify_turn=c5['role']=='ASK_USER'
            if clar:meta['clarify']=clar|{'selected':clarify_turn}
            if clarify_turn:c5['role']='C3_LANGUAGE'  # C3 voices the clarifying question
            if c5['role']=='EXTERNAL_TOOL':
                try:tool_result=toolctl.ToolStep(self).execute(e,tool_plan,intent={'action_selection':c5['packet_id']});meta['tool_call']={k:tool_result[k] for k in ('tool','status','tx','action_tx')}
                except Exception as exc:self.store.log('tool_step_unavailable',eid,{'stage':'execute','error':type(exc).__name__})
                c5['role']=next(a for a in c5['alternates'] if a in ('C3_LANGUAGE','B1_DETAIL','B2_GIST'))  # the body reports the grounded result
            elif tool_plan and tool_plan['status']=='PROPOSED':
                try:tool_pending=toolctl.ToolStep(self).propose_call(e,tool_plan);meta['tool_pending']={k:tool_pending[k] for k in ('tool','status','call_id')}  # WP-T7: preview + per-call approval
                except Exception as exc:self.store.log('tool_step_unavailable',eid,{'stage':'propose','error':type(exc).__name__})
            elif tool_plan:
                try:tool_shadow=toolctl.ToolStep(self).shadow(e,tool_plan);meta['tool_shadow']={'tool':tool_plan['tool'],'reason':tool_plan['reason']}
                except Exception as exc:self.store.log('tool_step_unavailable',eid,{'stage':'shadow','error':type(exc).__name__})
            predicted_role=c5['role'];meta['action_selection']=c5['packet_id']
            forecast=self.world.forecast(e,predicted_role,deadline,native_prediction=not direct)
            aid=self.store.start_action(eid,g,forecast=forecast);action_started=time.monotonic();meta['selected_offer_ids']=[p['packet_id'] for p in selected]
            try:  # WP-N9 §85.7 COROLLARY_PACKET before dispatch: what this own action should cause
                med=forecast.get('duration_median_s');rng=forecast.get('observed_range_s')
                preds=[{'channel':'action_status','value':'FINAL'}]+([{'channel':'duration_s','value':med,'tolerance':max(.5,(rng[1]-rng[0])/2 if rng else med*.5)}] if med is not None else [])
                selfctl.controller(self).issue(eid,aid,'TEXT_REPORT to user via '+predicted_role,preds,affected=['ram','heat','latency'],uncertainty=.3 if med is not None else .7,expected_cost={'duration_s':med},window_s=self.cfg['deadline_seconds'],refs=[e['source_ref']])
            except Exception as exc:self.store.log('self_unavailable',eid,{'stage':'corollary','error':type(exc).__name__})
            agi_live.expect(self,e,aid,predicted_role,route)  # WP-N13 AG2 prediction before acting
            exec_state=self.executive.update(e,self.session,offers=selected,action_id=aid,user_beliefs=meta.get('user_beliefs') or [])
            meta['executive_state_version']=exec_state['state_version']
            if direct:
                output=safe_text(fixed_policy['answer'] if fixed_policy else exact.group(1))
                if not visible_text(output):
                    output='';raise Unavailable('Exakte Quelle enthält keinen sichtbaren Text')
                txctl.commit_output(self.store,mid,eid,meta);meta['first_output_monotonic_ns']=time.monotonic_ns();self.store.append_message(mid,output);meta['direct_source_copy']=True
            else:
                role=c5['role']
                if any(x['reason']=='RESOURCE_PRESSURE' and x['action_id']==ActionGate.PRIOR[route] for x in c5['suppressed']):meta['resource_fallback']=ActionGate.PRIOR[route]+' -> '+role
                try:
                    if reflexctl.controller(self).circuit_open(role):raise Unavailable(role+': Reflex-Sperre nach wiederholten Fehlern')  # WP-F §5.3
                    runner=self.pool.get(role)
                except Unavailable:
                    if role=='C3_LANGUAGE':raise
                    self.notice(role+' fehlt; C3 übernimmt die Antwort.');runner=self.pool.get('C3_LANGUAGE');meta['fallback']='C3_LANGUAGE'
                # WP-N7 §8.3: pinned (stable) and volatile layers stay separate so the Context OS can plan the view.
                stable=prompt(self.cfg,'system')+' '+prompt(self.cfg,'conduct')+' '+prompt(self.cfg,'answer_rules')
                guidance=[rule for rule in self.store.rules() if isinstance(rule,str)]
                if guidance:stable+='\n'+prompt(self.cfg,'operator_rules')+dumps(guidance)
                volatile=[]
                if memories:volatile.append(('ACTIVE_VIEW','\n'+prompt(self.cfg,'memories'),self.memory.report_context(text,memories)))
                if selected:volatile.append(('HYPOTHESES','\n'+prompt(self.cfg,'hypotheses'),self.cognition.analyst_context(selected,e,version)))
                executive_view=self.executive.view(self.session)
                from .history import native_history
                history_records,history_refs=native_history(self.store,self.session,eid,self.cfg['history_turns'])
                try:  # WP-S7: sleep day digest of turns outside the history window (measured: recall of old facts 0 % -> 79-96 %)
                    if ctxos.controller(self).digest_enabled():
                        from .sleep_offline import context_items
                        dig=context_items(self.store,self.session,{m['event_id'] for m in history_records}|{eid})
                        if dig:volatile.append(('COMPRESSED','\n'+prompt(self.cfg,'digest'),dig));meta['digest_lines']=len(dig)
                except Exception as exc:self.store.log('digest_unavailable',eid,{'error':type(exc).__name__})
                volatile.append(('LATENT_STATE','\n'+prompt(self.cfg,'task_context'),self.executive.report_context(self.session)))
                ul=agi_live.user_layer(meta)
                if ul:volatile.append(('USER_MODEL','\n'+prompt(self.cfg,'user_model'),ul))  # WP-N13 AG11 beliefs, labelled
                if clarify_turn:volatile.append(('CLARIFY','\n'+prompt(self.cfg,'clarify'),{'reason':'METACOG_CALIBRATED_ABSTAIN'}))
                if tool_pending and tool_pending['status']=='PROPOSED':volatile.append(('TOOL_PENDING','\nProposed action (waiting for the user, not executed):',toolctl.ToolStep(self).pending_layer(tool_pending)))
                if tool_result and tool_result.get('result') is not None:volatile.append(('TOOL_RESULT','\nTool result (computed locally, exact; use this number):',toolctl.ToolStep(self).layer(tool_result)))
                try:  # WP-N14: the previous answer was cut off by this message; carry question, partial answer and its source
                    ho=duplex.handoff(self,eid)
                    if ho:volatile.append(('DUPLEX_HANDOFF','\n'+prompt(self.cfg,'duplex_handoff'),ho['body']));meta['duplex_handoff_refs']=ho['source_refs']
                except Exception as exc:self.store.log('duplex_unavailable',eid,{'stage':'handoff','error':type(exc).__name__})
                sys=stable+''.join(head+dumps(body) for _,head,body in volatile)
                history=[{'role':m['role'],'content':m['text']} for m in history_records]
                messages=[{'role':'system','content':sys}]+history+[{'role':'user','content':text}]
                try:  # WP-N7 Context OS: SHADOW logs the plan next to this legacy view; ACTIVE hands the planned view over
                    cplan=ctxos.controller(self).plan(eid,runner.role,stable,volatile,history_records,text,verdicts=[x['verdict'] for x in focal_run['inquisition']] if focal_run else [],warm_ids=warm_ids,provenance=[e['source_ref']],budget_scale=body['modulation'].get('context_budget_scale',1.))
                    messages=cplan['messages'];meta['context_plan']={'packet_id':cplan['packet_id'],'applied':cplan['applied']}
                except Exception as exc:self.store.log('context_os_unavailable',eid,{'stage':'plan','error':type(exc).__name__})
                try:save_context(self.store,self.session,eid,runner.role,messages)  # WP-V5 :context
                except Exception as exc:self.store.log('context_save_failed',eid,{'error':type(exc).__name__})
                context_refs=[e['source_ref'],*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[])]
                if executive_view.get('active_task'):context_refs.append(executive_view['active_task']['source_ref'])
                context_refs.extend(x['source_ref'] for x in executive_view['open_questions'])
                for item in selected:context_refs.extend(item['provenance']+item['evidence_refs'])
                for old in history_records:context_refs.append(self.store.source(old['text'],'C3_OUTPUT_HISTORY_CONTEXT'))
                context_refs=list({dumps(ref):ref for ref in context_refs}.values())
                # Durable answer lineage survives deletion of diagnostic/context
                # packets. Erased dependencies exclude this turn from future
                # native history while preserving the operator's chat display.
                meta['context_source_refs']=context_refs
                output_kwargs={}
                if runner.role=='C3_LANGUAGE':
                    if self.cfg.get('c3_decode_mode','server') in {'same_causal_zero','same_causal'}:
                        meta['output_adapter_status']=self._causal_output_context(e,messages,context_refs)
                        runner=self.pool.get_output('C3_LANGUAGE')
                        if self.cfg['c3_decode_mode']=='same_causal':
                            def causal_bias(observed):
                                selected=self.learner.causal_output_delta(e,observed)
                                meta['output_adapter_status']=selected['fallback_reason']
                                return selected
                            runner.bias_provider=causal_bias
                    else:
                        decision=self.learner.output_delta(e,messages,min(deadline,time.monotonic()+self.cfg['output_adapter_seconds']),context_refs)
                        if decision and decision['in_support']:output_kwargs['first_token_bias']=decision['first_token_bias']
                        runner=self.pool.get('C3_LANGUAGE')
                mark('native_answer')
                leading_output=''
                lead=toolctl.ToolStep(self).lead(tool_result) if tool_result and tool_result.get('result') is not None else None
                if lead:  # cfg tool_answer_first: the exact tool decision is the first visible sentence, the body continues
                    txctl.commit_output(self.store,mid,eid,meta);meta['first_output_monotonic_ns']=time.monotonic_ns()
                    final=toolctl.ToolStep(self).lead_final(tool_result);lead=final or lead
                    self.store.append_message(mid,lead+('' if final else ' '));output=lead+('' if final else ' ');meta['tool_answer_first']='FINAL' if final else 'LEAD'
                lw=latewatch.start(self,e,version,offers,deadline,meta,runner,eligible=not direct and state=='NORMAL')  # WP-U3 F2: late body offer may cut the stream
                for token in (() if meta.get('tool_answer_first')=='FINAL' else runner.generate(messages,self.cancel_event,deadline,**output_kwargs)):
                    clean=safe_text(token)
                    meta['output_removed_characters']=meta.get('output_removed_characters',0)+len(token)-len(clean)
                    if not output:
                        leading_output+=clean
                        if not visible_text(leading_output):continue
                        clean=leading_output;leading_output=''
                    if clean:
                        if meta['first_output_monotonic_ns'] is None:txctl.commit_output(self.store,mid,eid,meta);meta['first_output_monotonic_ns']=time.monotonic_ns()  # WP-K IH-H12 commit point
                        self.store.append_message(mid,clean);output+=clean
                        if lw.check(output):break
                output+=lw.finish(runner,messages,output,deadline,mid)
                meta.update(model_generated=True,runner=runner.last_metrics,model_revision=self.models.revision(runner.role))
                if getattr(runner,'memory',None) and memories:
                    try:  # WP-T9: inventory overlap on the actual final native runner; Exact stays delivered.
                        from .memory_server import shadow_delivery
                        loaded=getattr(runner,'memory_delivery_binding',None) if runner.pids() else None
                        audit=runner.last_metrics.get('native_memory_firing')
                        if audit is not None:
                            from .memory_server import observed_shadow_delivery
                            delivery=observed_shadow_delivery(self.store,self.home,runner.role,runner.model,loaded,memories,audit)
                        else:delivery=shadow_delivery(self.store,self.home,runner.role,runner.model,loaded,memories)
                        meta['sparse_delivery_shadow']=delivery
                        self.store.log('sparse_delivery_shadow',eid,delivery)
                    except Exception as exc:self.store.log('sparse_delivery_unavailable',eid,{'error':type(exc).__name__})
                try:ctxos.controller(self).observe(eid,runner.role,runner.last_metrics,'FINAL',meta['memory_ids'])  # WP-N7 cache outcome + warm set
                except Exception as exc:self.store.log('context_os_unavailable',eid,{'stage':'observe','error':type(exc).__name__})
                try:  # WP-N3: offer utility, re-entry value, observer-pass utility, bridge fields (SHADOW unless :jef active)
                    marks=meta['stage_marks_s'];obs_s=marks.get('focal_loop',0.)-marks.get('preanswer_observers',0.)
                    jefctl.controller(self).learn_turn(e,text,offers,output,focal_run,pre_offer_ids if focal_run else [],obs_s)
                except Exception as exc:self.store.log('jef_bridge_unavailable',eid,{'stage':'learn','error':type(exc).__name__})
                try:toolctl.ToolStep(self).compare(e,tool_shadow,output) if tool_shadow else None  # shadow agreement = evidence for the Age-1 tool right
                except Exception as exc:self.store.log('tool_step_unavailable',eid,{'stage':'compare','error':type(exc).__name__})
                try:attctl.controller(self).source_outcome(eid,text,output)  # WP-N5 §4B.4: did the A4 high-res spans reach the answer?
                except Exception as exc:self.store.log('attention_unavailable',eid,{'stage':'source_outcome','error':type(exc).__name__})
                if not visible_text(output):raise Unavailable('Modell lieferte keinen sichtbaren Text')
        except BaseException as exc:
            status='CANCELLED' if isinstance(exc,Cancelled) else ('DEADLINE' if isinstance(exc,Limits) and time.monotonic()>=deadline else 'ERROR')
            if monitor.resource_cancel_signalled:
                status='ERROR';exc=Limits('Ressourcenlimit während der Verarbeitung: '+monitor.reason)
            meta.update(error=type(exc).__name__,detail=str(exc)[:600],failure_stage=meta['turn_stage'])
            if runner is not None:meta['runner']=dict(runner.last_metrics)
            if not output:
                meta['model_generated']=False
                governor=self.executive.snapshot(e,self.session,memories if 'memories' in locals() else [],status);meta['output_snapshot_id']=governor['packet_id'];meta['output_authority']='SOURCE_SYSTEM_REPORT'
                # Preserve any native-context lineage already recorded before failure.
                meta['context_source_refs']=list({dumps(ref):ref for ref in meta['context_source_refs']+governor['provenance']}.values())
                output=self.executive.report(self.session,e,safe_text(str(exc)));txctl.commit_output(self.store,mid,eid,meta);self.store.append_message(mid,output)
                if meta['first_output_monotonic_ns'] is None:meta['first_output_monotonic_ns']=time.monotonic_ns()
            else:meta['model_generated']=not direct
            self.store.log('turn_interrupted',eid,{'status':status,'detail':str(exc)[:500]})
            if status=='ERROR':
                try:  # WP-N9 §20.4: repeated errors may become a self-message (gated; HELD below Age 4)
                    n=self.store.one("SELECT COUNT(*) AS n FROM (SELECT status FROM actions ORDER BY created DESC LIMIT 16) WHERE status='ERROR'")['n']
                    selfctl.controller(self).message('error','Repeated failures: '+type(exc).__name__+' ('+str(n)+' of the last 16 actions)',.5+.1*n)
                except Exception as e2:self.store.log('self_unavailable',eid,{'stage':'message','error':type(e2).__name__})
        finally:
            meta['native_pressure']=monitor.stop()
            try:duplex.settle(self,e,meta,status)  # WP-N14: a cut answer stays provisional, never learned
            except Exception as exc:self.store.log('duplex_unavailable',eid,{'stage':'settle','error':type(exc).__name__})
            try:
                self.executive.update(e,self.session,status=status)
            except Exception as exc:self.store.log('executive_finish_deferred',eid,{'error':type(exc).__name__})
            mark('finished');meta.update(self_candidate_hash=digest(output),duration_s=time.monotonic()-start,characters=len(output));self.store.finish_message(mid,status,meta)
            txctl.settle_turn(self,eid,status)  # WP-K IH-H13: provisional items promote at FINAL, else tombstone
            bout=None
            try:  # WP-T7 C7 output broker: authority decision, C6 check of the visible output, late correction / action preview
                from .broker import Broker
                lv=locals();bout=Broker(self).finalize(e,mid,meta,status,output,direct=direct,exact_requested=bool(lv.get('exact')),clarify=bool(lv.get('clarify_turn')),tool_result=lv.get('tool_result'),pending=lv.get('tool_pending'))
            except Exception as exc:self.store.log('broker_unavailable',eid,{'error':type(exc).__name__})
            try:  # WP-J B3-H9: score this turn's callosum messages by what the receiver did next
                from . import callosum
                fr=locals().get('focal_run');callosum.controller(self).outcome(eid,[x['item_id'] for x in fr['coalition']] if fr else [],status)
            except Exception as exc:self.store.log('callosum_unavailable',eid,{'stage':'outcome','error':type(exc).__name__})
            if aid:
                self.store.finish_action(aid,status,{'characters':len(output),'self_candidate_hash':meta['self_candidate_hash'],'action_duration_s':time.monotonic()-action_started,'role':'SOURCE_COPY' if direct else (runner.role if runner else None),'model_generated':meta['model_generated']})
                self.world.observe(aid)
                try:selfctl.controller(self).observe(eid,[{'channel':'action_status','value':status},{'channel':'duration_s','value':time.monotonic()-action_started}],close=[aid])  # WP-N9 self vs world
                except Exception as exc:self.store.log('self_unavailable',eid,{'stage':'attribution','error':type(exc).__name__})
                try:  # WP-F: circuit-breaker evidence, cerebellar update, procedural lifecycle
                    rx=reflexctl.controller(self);rr=runner.role if runner else None
                    if rr and status=='FINAL':rx.record_success(rr)
                    elif rr and status in ('ERROR','DEADLINE'):rx.record_failure(rr,eid,status)
                    for f in meta.get('reflex',[]):rx.outcome(f['reflex'],status)
                    if ff_x is not None:
                        ffc=ffctl.controller(self);dur=time.monotonic()-action_started;learned=ffc.learn(eid,ff_x,dur,status,len(output));ff_surprise=learned['surprise']
                        if ff_key and not direct:
                            fast=ffc.predict(ffctl.features(text,route,'none',memories,effort_plan['effort'],effort_sig))['duration_s']
                            ffc.record_turn(ff_key,wake_route,status,dur,learned['surprise'],fast,applied=bool(meta.get('procedural',{}).get('apply')))
                except Exception as exc:self.store.log('fast_forward_unavailable',eid,{'stage':'learn','error':type(exc).__name__})
                try:  # WP-N4: C6 egress schema check + separate C5 modulators for the taken action
                    eg=(bout if bout and bout['egress_ok'] is not None else c5ctl.check_output(self.store,e,'EXACT_RENDER' if direct else 'TEXT_REPORT',output)) if status=='FINAL' else None  # WP-T7: the broker already ran C6
                    if eg and 'egress_ok' in eg:eg={'ok':eg['egress_ok']}
                    sel=self.store.one("SELECT payload FROM packets WHERE kind='ActionSelection' AND event_id=? ORDER BY rowid DESC LIMIT 1",(eid,))
                    if sel:
                        sel=json.loads(sel['payload']);ctx=(sel.get('learning') or {}).get('context') or c5ctl.context(sel.get('route_hint'))
                        mixed=self.store.one("SELECT COUNT(*) n FROM packets WHERE kind='SelfWorldAttribution' AND event_id=? AND json_extract(payload,'$.attribution')='MIXED'",(eid,))['n']
                        c5ctl.controller(self).learn(ctx,sel['selected']['action_id'],eid,task_success=1. if status=='FINAL' else 0.,cost_error=min(1.,(time.monotonic()-action_started)/self.cfg['deadline_seconds']),
                            action_prediction_error=ff_surprise,rule_violation=0. if not eg or eg['ok'] else 1.,world_mismatch=1. if mixed else 0.)
                except Exception as exc:self.store.log('c5_learning_unavailable',eid,{'error':type(exc).__name__})
            self.world.self_state()
            self.store.add_packet('ExperienceRecord',packet('ExperienceRecord','F1_EPISODIC',eid,g,[e['source_ref']],source_ref=e['source_ref'],self_candidate_hash=meta['self_candidate_hash'],outcome=status,teacher_seen_before_commit=False))
            agi_live.after_turn(self,e,meta,status,aid)  # WP-N13 AG2 outcome, AG4 skill outcome, AG0 slots
            if not direct:skilllive.after_turn(self,e,meta,status,locals().get('route'))  # WP-T6 skill parity, habits, failure reopen (route unset if routing failed)
            if not direct:jefoutcome.after_turn(self,e,meta,status,locals().get('focal_run'))  # WP-U1 outcome labels for the fast heads (self, below human)
            try:meta['episode']=episodes.observe_turn(self,e,meta,status)['episode_id']  # WP-N8 event boundary + memory graph
            except Exception as exc:self.store.log('episodes_unavailable',eid,{'stage':'observe','error':type(exc).__name__})
            self.store.log('turn_finished',eid,meta|{'status':status});self.notice('Antwort gespeichert · '+status)
            self.turn_event=None
        if status=='FINAL' and not direct and self.cfg['observer_mode']=='background' and not offers and not (wake_decision and wake_decision['learned'] and wake_decision['action']=='none') and self.jobs.empty() and not self.stop.is_set() and rmodes.policy(self.guard.mode)['background_observers']:
            with self.lock:self.current='observers'
            peer=None
            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']
            background_roles=obsched.background(self.cfg.get('observer_schedule',obsched.DEFAULT),eid,self.cfg.get('observer_sample_rate',.5),background_roles,(meta.get('observer_schedule') or {}).get('post'))  # §22.2.4
            background_roles=rmodes.cap_roles(background_roles,self.guard.mode,'background_observers')  # §97.2 YELLOW: one post-commit body
            for role in background_roles:
                if role==(meta.get('late_watch') or {}).get('offered'):continue  # WP-U3: this body already ran during the output
                if self.guard.update(self.resources())!='NORMAL' or not rmodes.policy(self.guard.mode)['background_observers']:break
                if not self.jobs.empty() or self.cancel_event.is_set():break
                try:
                    p=self.cognition.offer(role,e,version,time.monotonic()+self.cfg['observer_seconds'],peer);peer=self.cognition.communicate(p,'B2_GIST' if role=='B1_DETAIL' else 'B1_DETAIL')
                    self.store.log('postcommit_offer',eid,{'id':p['packet_id'],'affects_committed_output':False})
                    try:selfctl.controller(self).late_offer(eid,p,output)  # WP-F §5.2: late salient disagreement -> gated self-message
                    except Exception as exc:self.store.log('self_unavailable',eid,{'stage':'late_offer','error':type(exc).__name__})
                except Exception as exc:self.store.log('background_observer_end',eid,{'error':str(exc)[:200]});break
    def _teacher(self,event_id=None):
        if not self.cfg['teacher_enabled']:raise ValueError(':teacher on zuerst; eigenes GGUF für TEACHER importieren')
        answer=self.last_answer()
        if not answer or answer['status']!='FINAL':raise ValueError('Erst eigene vollständige Antwort erzeugen')
        e=json.loads(self.store.one('SELECT packet FROM events WHERE id=?',(answer['event_id'],))['packet']);before=digest(answer['text']);runner=self.pool.get('TEACHER');deadline=time.monotonic()+self.cfg['deadline_seconds']
        prompt='Prüfe diese lokale Antwort. Trenne belegte Korrekturen von Unsicherheit. Frage: '+self.store.read_source(e['source_ref'])+'\nAntwort: '+answer['text'];mid=self.store.message(self.session,e['event_id'],'teacher');output='';status='FINAL'
        try:
            for tok in runner.generate([{'role':'system','content':'You are a frozen reference reviewer.'},{'role':'user','content':prompt}],self.cancel_event,deadline):output+=safe_text(tok);self.store.append_message(mid,safe_text(tok))
        except Exception as exc:status='ERROR';self.notice(str(exc))
        finally:
            if not output.strip():status='ERROR'
            ref=self.store.source(output,'TEACHER_REFERENCE') if output else None
            self.store.finish_message(mid,status,{'reference_only':True,'own_answer_hash_before_teacher':before,'not_fact':True,'runner':runner.last_metrics,'reference_source_ref':ref,'model_revision':self.models.revision('TEACHER')})
    def _replay(self,count):
        """Re-evaluate real corrections, without feeding generated replay into facts.

        RECORD_ONLY permits inference/retrieval; parameter updates still require
        :learning shadow, :learn, evaluation, and explicit artifact approval.
        """
        from .proofs import archive_previous
        if not isinstance(count,int) or not 1<=count<=16:raise ValueError('Replay-Anzahl 1..16')
        self.guard.update(self.resources());count=rmodes.scaled(count,self.guard.mode,'replay_scale')  # §97.2: YELLOW halves, ORANGE/RED none
        if not count:raise Limits('Replay pausiert wegen RAM-/Temperaturlimit (Modus '+self.guard.mode+')')
        path=self.home/'exports/replay-last.json';archive_previous(path)
        report={'kind':'F4_EPISODIC_REPLAY','status':'RUNNING','generation':self.store.generation_id,'rows':[],
                'weight_updates':False,'generated_output_authority':'HYPOTHESIS_NO_LEARNING','effective_config':dict(self.cfg),'resource_mode':self.guard.mode}
        def save():atomic_write(path,dumps(report))
        save()
        rows=self.store.rows("SELECT * FROM replay WHERE status='PENDING' ORDER BY priority DESC,created LIMIT ?",(count,))
        try:
            for row in rows:
                check(self.cancel_event,time.monotonic()+1)
                if self.guard.update(self.resources())!='NORMAL':raise Limits('Replay pausiert wegen RAM-/Temperaturlimit')
                with self.store.tx() as c:c.execute("UPDATE replay SET status='RUNNING' WHERE id=?",(row['id'],))
                output='';runner=None
                try:
                    event=self.store.one('SELECT * FROM events WHERE id=?',(row['event_id'],));e=json.loads(event['packet'])
                    text=self.store.read_source(e['source_ref'])
                    memories=self.memory.recall(text,event['session_id'],cancel=self.cancel_event,deadline=time.monotonic()+self.cfg['deadline_seconds'])
                    routes=self.store.rows("SELECT m.* FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.event_id=? AND m.kind='route' AND m.active=1 AND s.deleted=0 ORDER BY m.created DESC",(row['event_id'],))
                    if not memories and not routes:
                        with self.store.tx() as c:c.execute("UPDATE replay SET status='SKIPPED_NO_ACTIVE_FEEDBACK' WHERE id=?",(row['id'],))
                        report['rows'].append({'replay_id':row['id'],'status':'SKIPPED_NO_ACTIVE_FEEDBACK'});save();continue
                    deadline=time.monotonic()+self.cfg['deadline_seconds'];refs=[e['source_ref']]+self.consolidation.source_refs(memories)
                    route_result=None
                    if routes:
                        vector=self.learner.embedding(text,e['source_ref']['source_id'],deadline)
                        route_result=self.learner.propose(text,e['source_ref']['source_id'],deadline)
                        result={'target_route':routes[0]['value'],'prediction':route_result,'embedding_dim':len(vector),'scored':route_result is not None}
                        output=dumps(result);metrics=dict(self.needle.last_metrics)
                        source=self.store.one('SELECT * FROM sources WHERE id=?',(routes[0]['source_id'],))
                        ref={'source_id':source['id'],'sha256':source['hash'],'char_start':0,'char_end':source['chars'],'modality':'text'};self.store.read_source(ref);refs.append(ref)
                    else:
                        runner=self.pool.get('C3_LANGUAGE')
                        system=prompt(self.cfg,'replay')
                        system+='\n'+prompt(self.cfg,'replay_rules')+dumps(self.store.rules())+'\n'+prompt(self.cfg,'replay_memories')+dumps([{'topic':m['key_text'],'correction':m['value']} for m in memories])
                        for token in runner.generate([{'role':'system','content':system},{'role':'user','content':text}],self.cancel_event,deadline,self.cfg['replay_tokens']):output+=safe_text(token)
                        if not output.strip():raise Unavailable('Replay-Modell lieferte keinen Text')
                        metrics=dict(runner.last_metrics)
                    ref=self.store.source(output,'REPLAY_HYPOTHESIS')
                    p=packet('ReplayItem','F4_REPLAY',e['event_id'],self.store.generation_id,refs,replay_type='EPISODIC_REEVALUATION',source_refs=refs,priority=row['priority'],max_authority='HYPOTHESIS_NO_LEARNING',output_source_ref=ref,replay_id=row['id'],native_metrics=metrics,route_evaluation=route_result)
                    self.store.add_packet('ReplayItem',p)
                    with self.store.tx() as c:c.execute("UPDATE replay SET status='REPLAYED' WHERE id=?",(row['id'],))
                    self.store.log('replay_finished',e['event_id'],{'status':'FINAL','count':1,'runner':metrics})
                    report['rows'].append({'replay_id':row['id'],'event_id':e['event_id'],'status':'REPLAYED','packet_id':p['packet_id'],'output':output,'output_source_ref':ref,'source_refs':refs,'native_metrics':metrics});save()
                except BaseException:
                    with self.store.tx() as c:c.execute("UPDATE replay SET status='PENDING' WHERE id=? AND status='RUNNING'",(row['id'],))
                    raise
            report['status']='REPLAY_COMPLETE'
        except BaseException as exc:
            report.update(status='REPLAY_INTERRUPTED',error_type=type(exc).__name__,error=str(exc)[:500]);raise
        finally:
            self.pool.unload();self.needle.unload();save();self.store.set_meta('latest_replay_report',str(path))
        return {'status':report['status'],'count':len(report['rows']),'artifact':str(path),'weight_updates':False}
    def _dream(self):
        answer=self.last_answer()
        if not answer:raise ValueError('Erst eine Erfahrung sammeln')
        runner=self.pool.get('C3_LANGUAGE');e=json.loads(self.store.one('SELECT packet FROM events WHERE id=?',(answer['event_id'],))['packet']);deadline=time.monotonic()+30
        text=''.join(runner.generate([{'role':'system','content':'Erzeuge eine kurze hypothetische Testvariation. Sie ist kein Fakt.'},{'role':'user','content':self.store.read_source(e['source_ref'])}],self.cancel_event,deadline,96))
        self.store.add_packet('ReplayItem',packet('ReplayItem','F4_REPLAY',e['event_id'],e['brain_generation_id'],[e['source_ref']],replay_type='COUNTERFACTUAL_DRAFT',source_refs=[e['source_ref']],priority=0.,max_authority='HYPOTHESIS_NO_LEARNING',text=text));self.notice('Hypothetischer Testentwurf (kein Fakt): '+text)
    def close(self):
        if self.closed:return
        with self.lock:self.stop.set();self.cancel_event.set();self.wake.set()
        self.worker.join(6)
        if self.worker.is_alive():self.pool.unload();self.needle.unload();kill_process(self.learner.proc);self.worker.join(4)
        if self.worker.is_alive():raise RuntimeError('Worker beendet sich noch; Store bleibt zum Schutz offen')
        while not self.jobs.empty():
            kind,payload,_,_=self.jobs.get_nowait()
            # PENDING user turns remain durably accepted for the next process;
            # cache removal is not rejection or completion of their work.
            self.jobs.task_done()
        self.pool.unload();self.needle.unload();self.memory.semantic_keys.encoder.unload();self.store.close();self.closed=True
