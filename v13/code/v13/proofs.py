"""Read-only audits and isolated, real-run STEP1/2 probes of the existing runtime."""
import copy
import json
import math
from pathlib import Path
import shutil
import tempfile
import threading
import time
from .common import APP,atomic_write,dumps,digest,file_hash,Cancelled
from .prompts import text as prompt_text
from .resources import device

REQUIRED_ROLES={'C3_LANGUAGE','C2_CONTROL','B1_DETAIL','B2_GIST'}
def assess_native_probe(report,revisions):
    """A file's presence cannot satisfy a proof gate. Legacy smoke remains valid evidence."""
    errors=[]
    if not isinstance(report,dict):return {'smoke_valid':False,'phone_smoke_valid':False,'errors':['not an object'],'step1_complete':False,'step2_complete':False}
    def obj(value):return value if isinstance(value,dict) else {}
    if report.get('status')!='SMOKE_PASS':errors.append('status is not SMOKE_PASS')
    roles=report.get('roles',{})
    if not isinstance(roles,dict) or not REQUIRED_ROLES.issubset(roles):errors.append('required roles missing');roles={}
    for role in REQUIRED_ROLES:
        row=roles.get(role,{})
        if not isinstance(row,dict) or row.get('ok') is not True:errors.append(role+': failed/missing');continue
        if obj(report.get('model_revisions')).get(role)!=revisions.get(role) or revisions.get(role) in {None,'unavailable'}:errors.append(role+': revision mismatch/missing')
        if role=='C2_CONTROL':
            if row.get('embedding_dim')!=3072:errors.append(role+': native embedding dimension')
            norm=row.get('embedding_squared_norm')
            if isinstance(norm,bool) or not isinstance(norm,(int,float)) or not math.isfinite(norm) or norm<=0:errors.append(role+': invalid embedding norm')
        else:
            if not isinstance(row.get('actual_output'),str) or not row['actual_output'].strip():errors.append(role+': empty output')
            if obj(row.get('unload')).get('process_reaped') is not True:errors.append(role+': unload not proven')
    android=obj(report.get('device')).get('android');measured=report.get('phone_measured')
    phone=measured is True and android is True
    if not isinstance(android,bool) or not isinstance(measured,bool) or android!=measured:errors.append('inconsistent/missing phone flags')
    return {'smoke_valid':not errors,'phone_smoke_valid':phone and not errors,'errors':errors,'step1_complete':False,'step2_complete':False,'configuration_recorded':isinstance(report.get('effective_config'),dict),'claim_limit':'Native smoke is not stable JEF proof, complementary utility, sustained RSS, thermal or energy proof.'}

def native_probe_evidence(r):
    path=r.store.meta('latest_native_probe')
    if not path:return {'smoke_valid':False,'phone_smoke_valid':False,'errors':['no local probe artifact'],'step1_complete':False,'step2_complete':False}
    try:
        p=Path(path)
        if not p.is_file():p=r.home/'exports'/Path(path).name
        report=json.loads(p.read_text());return assess_native_probe(report,r.revisions())|{'artifact':str(p),'sha256':file_hash(p),'device':report.get('device')}
    except (OSError,ValueError,TypeError) as exc:return {'smoke_valid':False,'phone_smoke_valid':False,'errors':['unreadable/invalid probe: '+type(exc).__name__],'step1_complete':False,'step2_complete':False}

def audit_event(store,eid):
    event=store.one('SELECT * FROM events WHERE id=?',(eid,));envelope=json.loads(event['packet']);packets=[json.loads(p['payload'])|{'_kind':p['kind']} for p in store.rows('SELECT * FROM packets WHERE event_id=? ORDER BY created',(eid,))];byid={p['packet_id']:p for p in packets}
    kinds=lambda k:[p for p in packets if p['_kind']==k]
    messages=store.rows("SELECT * FROM messages WHERE event_id=? AND role='assistant'",(eid,));m=messages[0] if messages else None;meta=json.loads(m['metadata']) if m else {};offers=kinds('OfferPacket');queries=kinds('QueryPacket');actions=store.rows('SELECT * FROM actions WHERE event_id=?',(eid,))
    source_errors=[]
    for p in packets:
        for ref in p.get('provenance',[])+p.get('evidence_refs',[]):
            try:store.read_source(ref)
            except Exception as exc:source_errors.append(type(exc).__name__)
    links=[]
    for offer in offers:
        q=byid.get(offer.get('query_packet_id'),{});broadcast=byid.get(q.get('broadcast_packet_id'),{});peer=byid.get(q.get('peer_message_packet_id'))
        links.append({'offer_id':offer['packet_id'],'role':offer['role'],'query_id':q.get('packet_id'),'query_link_valid':q.get('_kind')=='QueryPacket' and q.get('target_role')==offer['role'],'broadcast_link_valid':broadcast.get('_kind')=='JEFBroadcastPacket' and broadcast.get('state_version')==offer['based_on_state_version'],'peer_message_id':q.get('peer_message_packet_id'),'peer_link_valid':peer is None and q.get('peer_message_packet_id') is None or bool(peer and peer.get('receiver')==offer['role']),'view_width_chars':offer.get('source_view_width_chars')})
    first=meta.get('first_output_monotonic_ns');copies=kinds('CorollaryCopy');selected=meta.get('selected_offer_ids',[])
    states=kinds('ExecState');state_versions=[p['state_version'] for p in states]
    state_chain=bool(states and state_versions==sorted(set(state_versions)) and all(p['session_id']==event['session_id'] and p['last_event_id']==eid and p['goal']==store.read_source(envelope['source_ref']) for p in states))
    checks={'single_assistant_stream':len(messages)==1,'final_output':bool(m and m['status']=='FINAL' and m['text'].strip()),'actual_model_output':meta.get('model_generated') is True,'c1_state_packet':state_chain,'broadcast_packet':len(kinds('JEFBroadcastPacket'))==1,'percept_packet':len(kinds('PerceptPacket'))==1,'single_action_owner':len(actions)==1 and actions[0]['kind']=='TEXT_REPORT','corollary_before_first_output':bool(first and len(copies)==1 and copies[0]['created_monotonic_ns']<=first),'self_hash_matches':bool(m and meta.get('self_candidate_hash')==digest(m['text'])),'same_generation':all(p['brain_generation_id']==event['generation_id'] for p in packets),'source_refs_valid':not source_errors,'selected_offers_exist':all(id_ in byid and byid[id_]['_kind']=='OfferPacket' for id_ in selected),'offer_query_broadcast_links':all(x['query_link_valid'] and x['broadcast_link_valid'] and x['peer_link_valid'] for x in links)}
    attempts=[json.loads(x['metrics']) for x in store.rows("SELECT metrics FROM telemetry WHERE event_id=? AND kind='body_offer_attempt' ORDER BY id",(eid,))]
    return {'event_id':eid,'checks':checks,'packet_counts':{k:len(kinds(k)) for k in sorted({p['_kind'] for p in packets})},'links':links,'output':m['text'] if m else None,'output_metadata':meta,'offers':offers,'queries':queries,'observer_attempts':attempts,'source_errors':source_errors}

def archive_previous(path):
    if path.is_file():
        dest=path.parent/'proof-history'/(path.stem+'-'+file_hash(path)[:16]+path.suffix);dest.parent.mkdir(exist_ok=True)
        if not dest.exists():shutil.copyfile(path,dest)

def probe_sustained(parent,cycles=12):
    """Bounded actual turns/restarts; never substitutes for the STEP7 epoch."""
    from .runtime import Runtime
    from .config import initialize,save_config
    if isinstance(cycles,bool) or not isinstance(cycles,int) or not 4<=cycles<=128:raise ValueError('Sustained cycles: 4..128')
    parent.pool.unload();parent.needle.unload();path=parent.home/'exports/sustained-proof.json';archive_previous(path)
    report={'proof_kind':'BOUNDED_STABILITY_COLLECTION','status':'RUNNING','created_wall_time':time.time(),'device':device(),
            'phone_measured':device()['android'],'requested_cycles':cycles,'turns':[],'restarts':[],
            'full_runner_proof':False,'stability_epoch_complete':False,'energy_joules':None,
            'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in (APP/'v13').glob('*.py')},'model_revisions':parent.revisions()}
    def save():atomic_write(path,dumps(report))
    save();r=None;started=time.monotonic()
    try:
        with tempfile.TemporaryDirectory(dir=parent.home/'tmp',prefix='sustained-') as tmp:
            home=Path(tmp);cfg=initialize(home);cfg.update(parent.cfg);cfg.update(learning_mode='RECORD_ONLY',teacher_enabled=False,observer_mode='off',route_override='simple',history_turns=0,answer_tokens=64);save_config(home,cfg)
            for name in ['models','bin']:shutil.rmtree(home/name);(home/name).symlink_to(parent.home/name,target_is_directory=True)
            shutil.copyfile(parent.home/'config/models.json',home/'config/models.json');r=Runtime(home);report['effective_config']=dict(cfg);save()
            try:
                for i in range(cycles):
                    if parent.cancel_event.is_set():raise Cancelled('Sustained-Probe abgebrochen')
                    sample=r.resources()
                    if r.guard.update(sample)=='CRITICAL':raise Cancelled('Sustained-Probe wegen Ressourcenlimit gestoppt')
                    parent.notice(f'Stabilitätsmessung {i+1}/{cycles}')
                    prompt=f'Projekt Test{i%4}: Budget {100+10*i} Euro. Nenne kurz das Budget und dessen Hälfte.'
                    eid=r.submit(prompt);end=time.monotonic()+cfg['deadline_seconds']+15
                    while not r.idle():
                        if parent.cancel_event.is_set() or time.monotonic()>end:r.cancel();raise Cancelled('Sustained-Probe abgebrochen/Zeitbudget')
                        time.sleep(.05)
                    audit=audit_event(r.store,eid);world=r.world.world_state();own=r.world.self_state()
                    prediction=json.loads(r.store.one("SELECT payload FROM packets WHERE event_id=? AND kind='ActionPrediction'",(eid,))['payload'])
                    report['turns'].append({'cycle':i,'input':prompt,'audit':audit,'resources_before':sample,'resources_after':r.resources(),'prediction':prediction,
                                           'world_observation':world['recent'][-1],'self_state':own})
                    save()
                    if not all(audit['checks'].values()):raise RuntimeError('Vertikaler Pfad fehlgeschlagen; Zwischenstand gespeichert')
                    if (i+1)%4==0:
                        sid=r.session;gid=r.store.generation_id;r.close();r=Runtime(home)
                        report['restarts'].append({'cycle':i,'same_session':r.session==sid,'same_generation':r.store.generation_id==gid,'same_world':r.world.world_state()==world,
                                                   'no_lingering_actions':r.world.self_state()['unfinished_actions']==0});save()
                samples=[t['resources_after'] for t in report['turns']]
                report['observability']={'battery_temperature':any(s['battery_temperature_c'] is not None for s in samples),'battery_percent':any(s['battery_percent'] is not None for s in samples),
                    'process_rss':any(p.get('rss_bytes') is not None for s in samples for p in s['processes']),'energy_meter':False}
                report['checks']={'all_turns_native':len(report['turns'])==cycles and all(all(t['audit']['checks'].values()) for t in report['turns']),
                    'restart':bool(report['restarts']) and all(all(v for k,v in x.items() if k!='cycle') for x in report['restarts']),
                    'observed_world_outcomes':r.world.world_state()['observed_action_count']==cycles,
                    'no_weight_updates':not r.store.rows('SELECT * FROM updates'),'integrity':not r.store.integrity(True)}
                report['status']='BOUNDED_STABILITY_PASS' if all(report['checks'].values()) else 'BOUNDED_STABILITY_PARTIAL'
            finally:
                if r:r.close();r=None
    except Exception as exc:report.update(status='BOUNDED_STABILITY_INTERRUPTED',error_type=type(exc).__name__,error=str(exc)[:500])
    finally:
        if r:r.close()
        report['duration_s']=time.monotonic()-started
        report['claim_limits']=['Bounded collection is not the full STEP7 stability epoch.','Missing sensors stay null/unavailable.','Empirical timing forecasts are not semantic world-JEPA or calibrated confidence.','No body training, gate promotion or model substitution.']
        save();parent.store.set_meta('latest_sustained_proof',str(path))
    return {'status':report['status'],'checks':report.get('checks',{}),'artifact':str(path),'phone_measured':report['phone_measured'],'stability_epoch_complete':False}

def _mask_step1_bodies(runtime):
    """Remove *both* B model authority paths in a disposable STEP1 proof home.

    ModelManager's manifest is not the whole authority: AG0 committed slots
    can override path_for even when the installed 'body'/'gist' entries are
    absent. This helper is only called on a freshly created temporary proof
    Runtime; never on the user's persistent brain.
    """
    from .models import model_key
    from .common import Unavailable
    roles=('B1_DETAIL','B2_GIST')
    keys={model_key(role,runtime.models.b2_control) for role in roles}
    slots=runtime.bodies.slots.box.load()[0]['slots']
    saved={'installed':{k:runtime.models.installed[k] for k in keys if k in runtime.models.installed},
           'slots':{role:copy.deepcopy(slots[role]) for role in roles if role in slots}}
    runtime.pool.unload()  # no already-resident body may outlive the isolation
    for key in keys:runtime.models.installed.pop(key,None)
    runtime.models.save()
    def remove(st):
        for role in roles:st['slots'].pop(role,None)
    runtime.bodies.slots.box.mutate(remove)
    for role in roles:
        try:runtime.models.path_for(role)
        except Unavailable:continue
        raise RuntimeError('STEP1 body still accessible after slot mask: '+role)
    return saved


def _restore_step1_bodies(runtime,saved):
    """Restore exact original slot specs and installed entries before STEP2."""
    runtime.pool.unload()
    runtime.models.installed.update(saved['installed'])
    runtime.models.save()
    def restore(st):
        for role,slot in saved['slots'].items():st['slots'][role]=copy.deepcopy(slot)
    runtime.bodies.slots.box.mutate(restore)
    runtime.bodies.sync()


def probe_step12(parent,cycles=1):
    """Explicit proof job, separate brain. Does not train, tune prompts, or promote any gate."""
    if not 1<=cycles<=4:raise ValueError('Probe cycles: 1..4')
    from .runtime import Runtime
    from .config import initialize,save_config
    parent.pool.unload();parent.needle.unload();report={'proof_kind':'STEP12_VERTICAL_INTERMEDIATE','proof_version':1,'created_wall_time':time.time(),'device':device(),'phone_measured':device()['android'],'model_revisions':parent.revisions(),'cycles':cycles,'turns':[],'full_runner_proof':False,'complementarity_proven':False,'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in (APP/'v13').glob('*.py')}}
    runtime=None;temp=None
    try:
        temp=tempfile.TemporaryDirectory(dir=parent.home/'tmp',prefix='step12-');tmp=temp.name
        home=Path(tmp);cfg=initialize(home);cfg.update(parent.cfg);cfg.update(learning_mode='RECORD_ONLY',teacher_enabled=False,observer_mode='off',route_override='auto',history_turns=0);save_config(home,cfg)
        for name in ['models','bin']:shutil.rmtree(home/name);(home/name).symlink_to(parent.home/name,target_is_directory=True)
        shutil.copyfile(parent.home/'config/models.json',home/'config/models.json');runtime=Runtime(home)
        def ask(text):
            if parent.cancel_event.is_set():raise Cancelled('STEP12-Probe abgebrochen')
            eid=runtime.submit(text);end=time.monotonic()+runtime.cfg['deadline_seconds']+2*runtime.cfg['observer_seconds']+15
            while not runtime.idle():
                if parent.cancel_event.is_set() or time.monotonic()>end:runtime.cancel();raise Cancelled('STEP12-Probe abgebrochen/Zeitbudget')
                time.sleep(.05)
            result=audit_event(runtime.store,eid);report['turns'].append(result);return result
        # STEP1 must mask the disposable home's model manifest AND AG0 slots.
        saved_bodies=_mask_step1_bodies(runtime)
        first=ask('Hallo. Erkläre kurz, wie ich dir eine Frage stellen kann.')
        state,version=runtime.store.state('C1_EXEC:'+runtime.session);session=runtime.session;runtime.close();runtime=Runtime(home)
        recovered,recovered_version=runtime.store.state('C1_EXEC:'+runtime.session)
        report['step1_restart']={'same_session':runtime.session==session,'same_exec_state':recovered==state,'same_state_version':recovered_version==version,'body_manifest_absent':not {'body','gist'}&set(runtime.models.installed),'body_slot_absent':not {'B1_DETAIL','B2_GIST'}&set(runtime.bodies.slots.box.load()[0]['slots'])}
        report['step1_native_control_observed']='native_control' in first['output_metadata'].get('route',{})
        report['step1_c3_without_body']=first['output_metadata'].get('runner',{}).get('role')=='C3_LANGUAGE'
        _restore_step1_bodies(runtime,saved_bodies)
        runtime.cfg.update(route_override='both',observer_mode='background')
        for i in range(cycles):
            parent.notice(f'STEP2 Messung {i+1}/{cycles} · bestehende B1/B2-Pfade')
            ask('Vergleiche die Optionen für Projekt Aurora. Budget: 120 Euro. Option Rot kostet 80 Euro und benötigt 2 Tage. Option Blau kostet 110 Euro und benötigt 1 Tag. Vorgabe: nur lokal, keine Cloud. Nenne die Budgetreste und fasse den Zielkonflikt knapp zusammen.')
        report['body_releases']=list(runtime.pool.release_history);report['body_resident_after_turns']=runtime.resources();report['db_integrity_errors']=runtime.store.integrity(True)
        rows=report['turns'][1:];role_sets=[{p['role'] for p in row['offers']} for row in rows]
        report['step2_observed_both_roles']=bool(rows) and all(x=={'B1_DETAIL','B2_GIST'} for x in role_sets)
        report['step2_role_states']={role:runtime.store.state(role+':'+runtime.session)[1] for role in ['B1_DETAIL','B2_GIST']}
        report['step2_measurements']=[{'event_id':row['event_id'],'offers':[{'role':o['role'],'metrics':o['native_metrics'],'verified_quote_count':len(o['evidence_refs']),'view_width_chars':o.get('source_view_width_chars')} for o in row['offers']],'quoted_span_overlap':_quote_overlap(row['offers'])} for row in rows]
        report['checks']={'vertical_turn_checks':all(all(x['checks'].values()) for x in report['turns']),'c2_executed':report['step1_native_control_observed'],'c3_without_b':report['step1_c3_without_body'],'restart':all(report['step1_restart'].values()),'both_body_roles':report['step2_observed_both_roles'],'separate_persisted_role_states':all(v>0 for v in report['step2_role_states'].values()),'released_native_processes':bool(report['body_releases']) and all(x['process_reaped'] for x in report['body_releases']),'integrity':not report['db_integrity_errors']}
        report['status']='VERTICAL_CHECKS_PASS' if all(report['checks'].values()) else 'VERTICAL_CHECKS_PARTIAL'
    except Exception as exc:report.update(status='VERTICAL_CHECKS_INTERRUPTED',error_type=type(exc).__name__,error=str(exc)[:500])
    finally:
        if runtime:runtime.close()
        if temp:temp.cleanup()
        report['claim_limits']=['Chat/routing/output remain intermediate','Native and structural checks are not semantic quality or complementarity proof','Quoted-span overlap is descriptive, not a utility score','Bounded sample storage is not a measured long-run RAM ceiling','No C3 alternative-model benchmark, thermal/energy retention or latent proof is inferred']
        path=parent.home/'exports/step12-proof.json';archive_previous(path);atomic_write(path,dumps(report));parent.store.set_meta('latest_step12_proof',str(path))
    return {'status':report['status'],'checks':report.get('checks',{}),'artifact':str(path),'phone_measured':report['phone_measured'],'full_runner_proof':False,'complementarity_proven':False}


def probe_jef_modes(parent):
    """Real STEP1 C-plane proof: C2-only, C3-only and C2+C3, with B manifest and AG0 slots removed.

    Diagnostic only. C2 is a structured-control organ, so its row is judged on a
    native structured result rather than pretending it is a language answer.
    """
    from .runtime import Runtime
    from .config import initialize,save_config
    parent.pool.unload();parent.needle.unload()
    path=parent.home/'exports/jef-modes-proof.json';archive_previous(path)
    report={'proof_kind':'STEP1_JEF_MODES','proof_version':2,'status':'RUNNING','created_wall_time':time.time(),
            'device':device(),'phone_measured':device()['android'],'model_revisions':parent.revisions(),
            'modes':{},'full_runner_proof':False,'no_b_dependency_proven':False,
            'claim_limits':['C2 is structured control, not a free-language speaker.',
                            'Three bounded fixtures are a vertical-path proof, not a general quality benchmark.',
                            'Target-phone stability still requires a Redmi run.']}
    atomic_write(path,dumps(report));runtime=None;temp=None
    try:
        temp=tempfile.TemporaryDirectory(dir=parent.home/'tmp',prefix='jef-modes-');home=Path(temp.name)
        cfg=initialize(home);cfg.update(parent.cfg);cfg.update(learning_mode='RECORD_ONLY',teacher_enabled=False,observer_mode='off',route_override='simple',history_turns=0);save_config(home,cfg)
        for name in ['models','bin']:
            shutil.rmtree(home/name);(home/name).symlink_to(parent.home/name,target_is_directory=True)
        shutil.copyfile(parent.home/'config/models.json',home/'config/models.json')
        runtime=Runtime(home);runtime.cancel_event=parent.cancel_event
        saved_bodies=_mask_step1_bodies(runtime)
        fixtures=prompt_text(cfg,'probe_fixtures')
        # C2-only: real native structured-control calls.
        c2=[]
        for text in fixtures:
            started=time.monotonic();obj=runtime.needle.control(text,parent.cancel_event,time.monotonic()+cfg['control_seconds']);c2.append({'input':text,'structured':obj,'metrics':dict(runtime.needle.last_metrics),'elapsed_s':time.monotonic()-started})
        report['modes']['C2_ONLY']={'rows':c2,'all_structured':all(isinstance(x['structured'],(dict,list)) for x in c2)}
        atomic_write(path,dumps(report))
        runtime.needle.unload()
        # C3-only: direct language organ, no C2 routing and no B manifest.
        runner=runtime.pool.get('C3_LANGUAGE');c3=[]
        for text in fixtures:
            started=time.monotonic();out=''.join(runner.generate([{'role':'system','content':prompt_text(cfg,'probe_system')},{'role':'user','content':text}],parent.cancel_event,time.monotonic()+cfg['deadline_seconds'],96,seed=cfg['seed']));c3.append({'input':text,'output':out,'metrics':dict(runner.last_metrics),'elapsed_s':time.monotonic()-started})
        report['modes']['C3_ONLY']={'rows':c3,'all_nonempty':all(x['output'].strip() for x in c3)};runtime.pool.unload()
        atomic_write(path,dumps(report))
        # An operator route override intentionally bypasses C2. The combined
        # mode must use auto so it exercises the real structured-control path.
        runtime.cfg['route_override']='auto';save_config(home,runtime.cfg)
        combined=[]
        for text in fixtures:
            eid=runtime.submit(text);end=time.monotonic()+cfg['deadline_seconds']+10
            while not runtime.idle():
                if parent.cancel_event.is_set() or time.monotonic()>end:runtime.cancel();raise Cancelled('JEF-Modes-Probe abgebrochen/Zeitbudget')
                time.sleep(.05)
            row=audit_event(runtime.store,eid);combined.append(row)
            report['modes']['C2_PLUS_C3']={'turns':combined};atomic_write(path,dumps(report))
        state,version=runtime.store.state('C1_EXEC:'+runtime.session);sid=runtime.session
        runtime.cancel_event=threading.Event();runtime.close();runtime=Runtime(home);runtime.cancel_event=parent.cancel_event
        recovered,recovered_version=runtime.store.state('C1_EXEC:'+runtime.session)
        report['restart']={'same_session':runtime.session==sid,'same_exec_state':recovered==state,'same_state_version':recovered_version==version}
        report['modes']['C2_PLUS_C3']={'turns':combined,'all_final':all(x['checks']['final_output'] and x['checks']['actual_model_output'] for x in combined),'all_c2_observed':all('native_control' in x['output_metadata'].get('route',{}) for x in combined),'all_c3_output':all(x['output_metadata'].get('runner',{}).get('role')=='C3_LANGUAGE' for x in combined)}
        report['body_manifest_absent']=not {'body','gist'}&set(runtime.models.installed)
        report['body_slot_absent']=not {'B1_DETAIL','B2_GIST'}&set(runtime.bodies.slots.box.load()[0]['slots'])
        report['checks']={'c2_only':report['modes']['C2_ONLY']['all_structured'],'c3_only':report['modes']['C3_ONLY']['all_nonempty'],'combined_final':report['modes']['C2_PLUS_C3']['all_final'],'combined_c2':report['modes']['C2_PLUS_C3']['all_c2_observed'],'combined_c3':report['modes']['C2_PLUS_C3']['all_c3_output'],'restart':all(report['restart'].values()),'no_b_manifest':report['body_manifest_absent'],'no_b_slots':report['body_slot_absent'],'integrity':not runtime.store.integrity(True)}
        report['no_b_dependency_proven']=all(report['checks'].values());report['status']='JEF_MODES_PASS' if report['no_b_dependency_proven'] else 'JEF_MODES_PARTIAL'
        _restore_step1_bodies(runtime,saved_bodies)
    except Exception as exc:report.update(status='JEF_MODES_INTERRUPTED',error_type=type(exc).__name__,error=str(exc)[:500])
    finally:
        if runtime:
            runtime.cancel_event=threading.Event();runtime.close()
        if temp:temp.cleanup()
        atomic_write(path,dumps(report));parent.store.set_meta('latest_jef_modes_proof',str(path))
    return {'status':report['status'],'checks':report.get('checks',{}),'artifact':str(path),'phone_measured':report['phone_measured'],'no_b_dependency_proven':report.get('no_b_dependency_proven',False)}

def _quote_overlap(offers):
    grouped={role:{(r['source_id'],r['char_start'],r['char_end']) for o in offers if o['role']==role for r in o['evidence_refs']} for role in ['B1_DETAIL','B2_GIST']}
    a,b=grouped.values();return {'b1_spans':len(a),'b2_spans':len(b),'intersection':len(a&b),'union':len(a|b),'jaccard':len(a&b)/len(a|b) if a|b else None,'semantic_complementarity':None}


def probe_body_state(parent):
    """Real B1/B2 state-policy probe; a separate brain uses the installed weights.

    Saves each completed inference, supports :cancel, never overwrites user state.
    Checks source/state mechanics, not whether a hypothesis is semantically true.
    """
    from .runtime import Runtime
    from .config import initialize,save_config
    parent.pool.unload();parent.needle.unload()
    path=parent.home/'exports/body-state-proof.json';archive_previous(path)
    report={'proof_kind':'STEP2_BODY_STATE_POLICY','status':'RUNNING','device':device(),'phone_measured':device()['android'],
            'model_revisions':parent.revisions(),'turns':[],'uses_real_weights':True,'full_runner_proof':False,
            'semantic_complementarity_proven':False,'source_hashes':{str(p.relative_to(APP)):file_hash(p) for p in (APP/'v13').glob('*.py')},
            'claim_limits':['Source-bound B2 state and its native input path, not learned or latent memory.',
                            'These small structural cases do not establish semantic complementarity or sustained phone performance.']}
    def save():atomic_write(path,dumps(report))
    save();runtime=None;temp=None
    try:
        temp=tempfile.TemporaryDirectory(dir=parent.home/'tmp',prefix='body-state-');tmp=temp.name
        home=Path(tmp);cfg=initialize(home);cfg.update(parent.cfg);cfg.update(learning_mode='RECORD_ONLY',teacher_enabled=False,observer_mode='off',b2_state_slots=4,b2_context_chars=768);save_config(home,cfg)
        for name in ['models','bin']:shutil.rmtree(home/name);(home/name).symlink_to(parent.home/name,target_is_directory=True)
        shutil.copyfile(parent.home/'config/models.json',home/'config/models.json')
        runtime=Runtime(home);runtime.cancel_event=parent.cancel_event
        # Keep the child cancellation event independent when closing for restart.
        def close_child():
            runtime.cancel_event=threading.Event();runtime.close()
        report['effective_config']=dict(cfg);before=runtime.store.generation()
        def offer(name,text,role,expected_ids):
            if parent.cancel_event.is_set():raise Cancelled('Body-State-Probe abgebrochen')
            parent.notice('Body-State '+name+' · '+role)
            e=runtime.store.event(runtime.session,text)
            p=runtime.cognition.offer(role,e,0,time.monotonic()+runtime.cfg['observer_seconds'])
            refs=p['context_source_refs']+p['evidence_refs']
            for ref in refs:runtime.store.read_source(ref)
            state,_=runtime.store.state(role+':'+runtime.session)
            attempt=json.loads(runtime.store.one("SELECT metrics FROM telemetry WHERE event_id=? AND kind='body_offer_attempt' ORDER BY id DESC LIMIT 1",(e['event_id'],))['metrics'])
            checks={'expected_context_ids':set(p['context_offer_ids'])==set(expected_ids),
                    'native_tokens':p['native_metrics'].get('generated_tokens',0)>0,
                    'context_bounded':p['context_chars']<=cfg['b2_context_chars'],
                    'state_bounded':len(state['retained_offer_ids'])<=(4 if role=='B2_GIST' else 1),
                    'trace_records_context':attempt.get('context_offer_ids')==p['context_offer_ids'],
                    'source_refs_readable':True}
            report['turns'].append({'case':name,'input':text,'offer':p,'retained_offer_ids':state['retained_offer_ids'],'checks':checks});save();return p
        first=offer('first','Projekt Aurora: Budget 120 Euro. Halte das Budget fest.','B2_GIST',[])
        second=offer('related','Projekt Aurora: Nur lokal, keine Cloud. Fasse die Vorgaben zusammen.','B2_GIST',[first['packet_id']])
        sid=runtime.session;close_child();runtime=Runtime(home);runtime.cancel_event=parent.cancel_event
        report['restart_same_session']=runtime.session==sid
        offer('after_restart','Projekt Aurora: Fasse Budget und Vorgaben zusammen.','B2_GIST',[first['packet_id'],second['packet_id']])
        offer('different_project','Projekt Borealis: Fasse Budget und Vorgaben zusammen.','B2_GIST',[])
        offer('fine_short_window','Projekt Aurora: Prüfe die Details.','B1_DETAIL',[])
        runtime.cfg['b2_state_slots']=0
        offer('state_ablation','Projekt Aurora: Fasse Budget und Vorgaben zusammen.','B2_GIST',[])
        report['checks']={'all_cases':all(all(x['checks'].values()) for x in report['turns']),
                          'restart':report['restart_same_session'],'generation_unchanged':runtime.store.generation()==before,
                          'no_weight_updates':not runtime.store.rows('SELECT * FROM updates'),'integrity':not runtime.store.integrity(True)}
        report['unload']=runtime.pool.unload()
        report['checks']['native_process_reaped']=bool(report['unload'] and report['unload'].get('process_reaped'))
        report['status']='BODY_STATE_CHECKS_PASS' if all(report['checks'].values()) else 'BODY_STATE_CHECKS_PARTIAL'
        close_child();runtime=None
    except Exception as exc:report.update(status='BODY_STATE_CHECKS_INTERRUPTED',error_type=type(exc).__name__,error=str(exc)[:500])
    finally:
        if runtime:
            runtime.cancel_event=threading.Event();runtime.close()
        if temp:temp.cleanup()
        save();parent.store.set_meta('latest_body_state_proof',str(path))
    return {'status':report['status'],'checks':report.get('checks',{}),'artifact':str(path),'phone_measured':report['phone_measured'],'semantic_complementarity_proven':False}
