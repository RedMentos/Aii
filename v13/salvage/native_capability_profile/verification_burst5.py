import contextlib
import json
from pathlib import Path
import time
from .common import APP,atomic_write,dumps,digest,file_hash
from .contracts import packet,FIELDS,BASE
from .resources import device
from .proofs import native_probe_evidence,archive_previous
from .body_training import inspect_train_port

GATES={
 'MobileMoE_native_bodies':'UNAVAILABLE: gated weights/license and packed Android runner/train proof absent; temporary dense bodies only',
 'B3_latents':'OFF: dense read-only taps exist; no native receiver injection, receiver calibration, utility/stability/OOD/ablation proof',
 'native_readonly_taps':'Implemented on exact pinned dense LFM2: independent final-state prefill, 2048 dimensions, 64-token bound; hash checked on request; no receiver authority',
 'A3_student_projector':'Text port implemented: learned raw-byte projection, actual frozen semantic targets and separate reconstruction/ablations; existing JEF T1 shadow consumer; no teacher removal or multimodal proof',
 'world_self_JEPA':'Scoped digital action-conditioned latent objective implemented: actual source/intent/corollary/committed own outcome, target EMA, measured support and retention/ablations; broad external-world causal/semantic prediction still unproven',
 'predictive_head':'Empirical action timing, approved digital action predictor and explicit dense-body future-state predictor with stop-gradient target EMA; actual consumers remain separately scoped; executive JEPA unavailable',
 'semantic_procedural_consolidation':'PARTIAL: approved repeated human-confirmation source indexes, memory compaction and exact authored procedural cues; native parametric consolidation and unseen-cue generalization remain unavailable',
 'teacher':'OPTIONAL: separate frozen reference after own committed candidate; exact operator self/teacher/span selection and dataset export implemented',
 'learning':'SHADOW: external route/wake/halt readouts, native first-route agreement calibration, A3 text student, digital World and dense-state predictors; explicit labels/observations, per-component artifact approval; native body weights frozen',
 'native_route_calibration':'External first native proposal agreement with explicit human route labels; support/confidence abstention and individual approval; no semantic truth confidence or native confidence-head training',
 'output_adapter':'External approved first-native-token C3 vocabulary row delta on actual1024D hidden states and65536 native logit probabilities; native continuation unbiased; not general LM/body training or semantic OOD',
 'memory_retrieval':'External source-pair Needle interaction head, explicit relevance labels, grouped held-out calibration/ablation/retention and approved query/source report binding; no learned fact truth or broad cue/phone guarantee',
 'metaplasticity':'Measured persistent per-component external shadow-budget feedback, retention damping/reopening and stability tags; no learned neural controller or native shared-layer measurement',
 'sleep':'Explicit native episodic replay + one hypothetical test draft; no autonomous consolidation',
 'external_tools':'OFF: no shell, messaging, web action or filesystem tools callable by models',
 'vision_audio':'UNAVAILABLE: text-only Age 0',
 'higher_age':'OFF: cap does not promote system',
 'phone_proof':'Prior Redmi smoke milestone preserved; local artifact validated separately. Sustained phone proof remains open'
}


def native_capability_profile(r=None):
    """Conservative executable capability inventory; absence of a proof never promotes authority."""
    runner_exists=bool(r and (r.home/'bin/llama-server').is_file())
    train_ports={role:inspect_train_port(r.home,role) for role in ('B1_DETAIL','B2_GIST')} if r else {}
    bound=[role for role,row in train_ports.items() if row.get('port_bound')]
    body_reason=('Bound native port descriptor(s) '+','.join(bound)+' still require TrainRunnerProof; update authority remains zero' if bound else 'No native trainable body parameter port/master-weight/requantization proof')
    return {
      'age':0,
      'runner_present':runner_exists,
      'readonly_dense_final_state_tap':{'status':'IMPLEMENTED','authority':'READ_ONLY','tap_id':'lfm2.result_norm.final.v1','max_tokens':64,'requires_pinned_model':True},
      'live_receiver_latent_tap':{'status':'UNAVAILABLE','authority':'NONE','reason':'No live receiver/private-KV tap proof'},
      'latent_injection':{'status':'OFF','authority':'NONE','reason':'No native receiver injection + calibration/utility/OOD proof'},
      'body_training':{'status':'UNAVAILABLE','authority':'NONE','reason':body_reason,'ports':train_ports},
      'native_sparse_bodies':{'status':'UNAVAILABLE','authority':'NONE','reason':'No accessible proven sparse mobile body runner/train path in this build'},
      'native_confidence_head_training':{'status':'UNAVAILABLE','authority':'NONE','reason':'Only separately approved external calibration/readout heads exist'},
      'model_callable_tools':{'status':'OFF','authority':'NONE','reason':'Age-0 model outputs cannot invoke external tools'}
    }

def component_registry():
    value=json.loads((APP/'specs/component-contracts.json').read_text())
    expected={*(f'A{i}' for i in range(6)),*(f'B{i}' for i in range(1,6)),*(f'C{i}' for i in range(8)),*(f'F{i}' for i in range(1,12))}
    ids=[x['component_id'] for x in value['components']]
    if set(ids)!=expected or len(ids)!=len(expected):raise ValueError('Component registry incomplete/duplicate')
    if file_hash(APP/value['canon_file'])!=value['canon_sha256']:raise ValueError('Canon identity mismatch')
    for row in value['components']:
        if any(s not in FIELDS for s in row['schemas']):raise ValueError('Component schema missing: '+row['component_id'])
        for path in row['implementation_files']:
            if not (APP/path).is_file():raise ValueError('Component implementation missing: '+path)
        if row['current_mode']=='UNAVAILABLE' and (row['latent_read_authority'] or row['latent_learn_authority']):raise ValueError('Unavailable component cannot receive authority')
    return value

def objective_registry(r):
    value=json.loads((APP/'specs/learning-objectives.json').read_text())
    for objective in value['objectives']:
        objective['effective_learn_gain']=r.cfg[objective.get('learning_rate_config_key','learning_rate')] if objective['status']=='IMPLEMENTED' and r.cfg['learning_mode']!='RECORD_ONLY' else 0
        objective['requires_explicit_job']=True
    return value

def schema_registry():
    def typename(t):
        if isinstance(t,tuple): return [getattr(x,'__name__',str(x)) for x in t]
        return getattr(t,'__name__',str(t))
    return {kind:{'schema_version':'1.0','base_fields':{k:typename(v) for k,v in BASE.items()},'fields':{k:typename(v) for k,v in fields.items()}} for kind,fields in sorted(FIELDS.items())}

def completion_ledger(r):
    """Machine-readable, deliberately conservative ledger for the implemented Age-0 slice."""
    evidence=native_probe_evidence(r)
    hardware=('VALIDATED_PHONE_SMOKE_ONLY' if evidence.get('phone_smoke_valid') else ('VALIDATED_LINUX_SMOKE_ONLY' if evidence.get('smoke_valid') else 'NO_VALID_MATCHING_LOCAL_SMOKE_ARTIFACT'))
    common={'persistence':'SQLite WAL + content-addressed blobs','current_mode':'IMPLEMENTED','hardware_proof':'platform-independent unit/integration tests','benchmark':None,'known_limitations':[]}
    rows=[
      dict(common,feature_id='STEP0_STORAGE_PROVENANCE',canon_source='§22A STEP 0 / §96 STEP 0',implementation_files=['v13/store.py','v13/contracts.py'],runtime_owner='F7_RUNTIME',state_owner='Store',schema_id='EventEnvelope/SourceRef/BrainGenerationManifest',unit_tests=['test_unicode_source_and_tamper','test_final_immutable_and_partial_restart','test_backup_restore_roundtrip'],integration_tests=['tests/integration_real.py'],gate_status='PASS'),
      dict(common,feature_id='STEP0_OPERATOR_GOVERNOR',canon_source='§22A STEP 0 / §96 STEP 0',implementation_files=['v13/operator.py','v13/runtime.py','v13/resources.py'],runtime_owner='F7_RUNTIME',state_owner='Runtime',schema_id=None,unit_tests=['test_model_text_cannot_execute','test_pause_resume_queue_and_age','test_queue_input_bounds_and_config_validation'],integration_tests=['tests/integration_real.py'],gate_status='PASS'),
      dict(common,feature_id='STEP0_LOGGING_MIGRATION',canon_source='IH-H30 / §96 STEP 0',implementation_files=['v13/store.py','v13/runners.py','v13/verification.py'],runtime_owner='F7_RUNTIME',state_owner='Store + logs/',schema_id='DB user_version=2 / MIGRATIONS 0→1→2 / LOG_POLICY-001',persistence='SQLite telemetry bounded to ~10000 rows; runner logs rotate at 3 MiB',hardware_proof='platform-independent unit tests',unit_tests=['test_database_version_and_telemetry_bound','test_runner_log_rotation_policy'],integration_tests=[],gate_status='PASS',known_limitations=['time-based log retention not implemented; size/row bounds are enforced']),
      dict(common,feature_id='STEP0_SCHEMA_REGISTRY',canon_source='IH-H27 / §96 STEP 0',implementation_files=['v13/contracts.py','v13/verification.py'],runtime_owner='F7_RUNTIME',state_owner='code registry',schema_id='FIELDS/BASE schema_version=1.0',unit_tests=['test_schema_registry_exposed'],integration_tests=[],gate_status='PASS'),
      dict(common,feature_id='STEP1_JEF_VERTICAL',canon_source='§22A STEP 1 / §96 STEP 1',implementation_files=['v13/runtime.py','v13/cognition.py','v13/runners.py'],runtime_owner='C_JEF_SYSTEM',state_owner='C1_EXEC + native runners',schema_id='ExecState/JEFBroadcastPacket/ActionIntent',persistence='C1 state + messages persisted; runner KV transient',hardware_proof=hardware,unit_tests=['test_model_text_cannot_execute'],integration_tests=['tests/integration_real.py','v13.proofs.probe_jef_modes','v13.proofs.probe_step12'],benchmark='native-probe.json, jef-modes-proof.json and step12-proof.json when available',gate_status='PARTIAL',known_limitations=['C2 confidence not calibrated','C3 baseline quality not a final V13 quality claim','Dedicated C2-only/C3-only/C2+C3 no-B proof is implemented but requires a real-weight run on the target phone; C3 alternative comparison remains open']),
      dict(common,feature_id='STEP2_SPLIT_BRAIN_OBSERVER',canon_source='§22A STEP 2 / §96 STEP 2',implementation_files=['v13/cognition.py','v13/runtime.py','v13/runners.py'],runtime_owner='B1_DETAIL+B2_GIST',state_owner='OfferPacket/FocalItem',schema_id='OfferPacket/MessagePacket/FocalItem',persistence='offers/packets persisted; body runner state transient',hardware_proof=hardware,unit_tests=['test_offer_stale_generation_and_commit'],integration_tests=['tests/integration_real.py','v13.proofs.probe_step12','tests/integration_step2.py','scripts/analyze_step2_proof.py'],benchmark='native-probe.json; step12-proof.json; docs/proofs/step2-ablations-linux.json + docs/proofs/step2-analysis-linux.json',gate_status='PARTIAL',known_limitations=['temporary dense harness body','measurable Gist/Detail complementarity not yet proven','latent injection OFF']),
      dict(common,feature_id='STEP3_FAST_EPISODIC',canon_source='§24.1 / §22A STEP 3',implementation_files=['v13/memory.py','v13/store.py','v13/runtime.py'],runtime_owner='F1_EPISODIC',state_owner='Memory',schema_id='HumanDecision/ExperienceRecord/MemoryRecord',unit_tests=['test_source_memory_restart_and_scope','test_feedback_supersedes_same_key_only','test_forget_source_and_packets','test_entity_topic_retrieval_handles_partial_transfer_without_other_attribute_leak'],integration_tests=['tests/integration_real.py','tests/integration_second_attempt.py'],gate_status='PARTIAL',known_limitations=['Second-attempt family is diagnostic; broader semantic advantage and target-phone repetition remain open','Lexical entity/topic recall is not semantic memory or JEPA','Native parametric semantic/procedural consolidation unimplemented; approved repeated human source indexes available']),
      {'feature_id':'B3_LATENT','canon_source':'G2/G2C','implementation_files':['v13/cognition.py'],'runtime_owner':'B3_CALLOSUM','state_owner':'MessagePacket','schema_id':'ReceiverCalibration','persistence':'packet log only','current_mode':'OFF','hardware_proof':None,'unit_tests':[],'integration_tests':[],'benchmark':None,'gate_status':'BLOCKED_BY_PROOF','known_limitations':['read-only dense taps do not provide receiver injection','no receiver calibration/utility/OOD ablation']},
      {'feature_id':'BODY_JEPA','canon_source':'STEP 6+','implementation_files':[],'runtime_owner':'F4_LEARNING','state_owner':None,'schema_id':'TrainRunnerProof','persistence':None,'current_mode':'UNAVAILABLE','hardware_proof':None,'unit_tests':[],'integration_tests':[],'benchmark':None,'gate_status':'NOT_STARTED','known_limitations':['no train runner proof','quantized inference weights are not train masters']}
    ]
    rows.append(dict(common,feature_id='STEP2_BODY_STATE_POLICY',canon_source='§96 STEP 2 / B1 Detail + B2 Gist',implementation_files=['v13/cognition.py','v13/config.py'],runtime_owner='B1_DETAIL+B2_GIST',state_owner='session-scoped body states',schema_id='QueryPacket/OfferPacket',persistence='bounded retained offer IDs + exact source bindings; restart-safe SQLite state',unit_tests=['tests/test_body_state.py'],integration_tests=['v13.proofs.probe_body_state'],benchmark='exports/body-state-proof.json',gate_status='PARTIAL',known_limitations=['Explicit source-backed context, not native recurrent/latent body memory','Lexical/entity admission is a BOOT policy, not learned semantic admission','Model hypotheses remain fallible; no semantic complementarity or sustained target-phone proof inferred']))
    additions=[
        ('STEP4_REFERENCE_SELECTION','§96 STEP4',['v13/memory.py','v13/models.py','v13/runtime.py','v13/operator.py'],'F8+F3','HumanDecision',['tests/test_experience_replay.py'],['tests/integration_experience.py'],'docs/proofs/experience-export-linux-20260929.json',['Frozen reused B1 is not asserted stronger or automatically factual']),
        ('STEP5_EXTERNAL_ROUTE_LEARNING','§96 STEP5',['v13/learning.py','v13/learning_worker.py'],'F6','TrainRunnerProof',['tests/test_learning_worker.py'],['tests/integration_learning.py'],'docs/proofs/acceptance-20260929/learning.json',['External route classifier; distinct wake/halt heads do not establish executive JEPA or output-adapter training']),
        ('STEP5_BOUNDED_WAKE_HALT','§96 STEP5',['v13/learning.py','v13/readout_worker.py','v13/runtime.py'],'C2+C4','ExecutiveDecision',['tests/test_executive_readouts.py','tests/test_readout_worker.py'],['tests/integration_readouts.py'],'docs/proofs/readouts-native-runtime-20260929.json',['Bounded labelled fixture calibration, not native C2 confidence calibration or general recurrent-depth quality']),
        ('C2_NATIVE_ROUTE_CALIBRATION','IH-H25 / §3.3.3',['v13/control_calibration_worker.py','v13/learning.py','v13/runtime.py'],'C2','ControlCalibration/TrainRunnerProof',['tests/test_control_calibration.py'],['tests/integration_control_calibration.py'],'docs/proofs/control-calibration-native-consumer-20261001.json',['External first native route proposal agreement calibration against explicit operator labels; input confidence/route support only; not semantic truth confidence or native confidence-head training']),
        ('F3_LEARNED_CUE_RETRIEVAL','IH-H25 / STEP3',['v13/retrieval_worker.py','v13/memory.py','v13/learning.py','v13/runtime.py'],'F3+C5','MemoryRetrievalDecision/TrainRunnerProof',['tests/test_retrieval.py'],['tests/integration_retrieval.py'],'docs/proofs/memory-retrieval-report-binding-20261001.json',['External relevance only; memory groups are held out, lexical cue families repeat across groups; broad unseen phrasing, fact truth, consolidation and target-phone proof remain open']),
        ('STEP6_DENSE_READONLY_TAPS','STEP6 / native tap interface',['v13/runners.py','v13/cognition.py'],'B1+B2','LatentTapPacket',['tests/test_native_taps.py'],['tests/integration_taps.py'],'docs/proofs/native-taps-20260929.json',['Independent frozen dense prefill; not live receiver KV, sparse body training or injection']),
        ('STEP6_DENSE_LOCAL_PREDICTOR','IH-H25 / predictor-first',['v13/learning.py','v13/predictor_worker.py','v13/cognition.py'],'B1+B2','TrainRunnerProof/LatentTapPacket',['tests/test_predictor_worker.py'],['tests/integration_predictor.py'],'docs/proofs/predictor-b2-native-20260930.json',['External 16-dimensional local predictor and target EMA on actual t+2 states; explicit tap consumer only; no semantic quality, body training or cross-body JEPA claim']),
        ('A3_TEXT_STUDENT','A3 / IH-H25 / G10',['v13/student_worker.py','v13/learning.py','v13/cognition.py','v13/runtime.py'],'A3+C2','PerceptPacket/StudentEvaluation',['tests/test_student_worker.py'],['tests/integration_student.py'],'docs/proofs/student-native-current-20260930.json',['Explicit learned text projection with separate alignment/reconstruction and T1 JEF shadow; no teacher removal, multimodal or native receiver injection proof']),
        ('F4_DIGITAL_ACTION_PREDICTOR','IH-H25 / §92.2',['v13/world_worker.py','v13/learning.py','v13/world.py','v13/runtime.py'],'F4','WorldTransition/ActionPrediction/PredictionOutcome/ModulatorPacket',['tests/test_world_worker.py'],['tests/integration_world.py'],'docs/proofs/world-native-geometry-20260930.json',['Approved external 16-dimensional action-conditioned digital outcome predictor; actual source/action/output bindings and target EMA; not external-world causal understanding, semantic truth, or native body training']),
        ('F9_EPISODIC_REPLAY','§15 / §31.2',['v13/runtime.py'],'F9','ReplayItem',['tests/test_experience_replay.py'],['tests/integration_experience.py'],'docs/proofs/experience-export-linux-20260929.json',['Explicit bounded inference; no generated fact/weight promotion or semantic/skill consolidation']),
        ('F4_SELF_WORLD_OBSERVATIONS','§7.1–7.5 / §31.2',['v13/world.py','v13/runtime.py','v13/store.py'],'F4','ActionPrediction/PredictionOutcome',['tests/test_world_state.py'],['v13.proofs.probe_sustained'],'docs/proofs/acceptance-20260929/sustained.json',['Digital self/action state and empirical timing only; no semantic/world JEPA; confidence uncalibrated']),
        ('F3_F9_CONFIRMED_CONSOLIDATION','§14–16 / STEP3–5',['v13/consolidation.py','v13/memory.py','v13/runtime.py','v13/operator.py'],'F3+F9','HumanDecision/MemoryRecord/ReplayItem',['tests/test_consolidation.py'],['tests/integration_consolidation.py'],'docs/proofs/consolidation-native-approval-bounds-20261002.json',['Human-approved repeated confirmation indexes, exact cue procedure and native memory/replay consumers; no novel abstractions, generated truth promotion or native weight consolidation']),
        ('C3_NATIVE_OUTPUT_DELTA','STEP5 / IH-H25',['v13/output_adapter_worker.py','v13/learning.py','v13/runners.py','v13/runtime.py'],'C3','OutputAdapterContext/OutputAdapterDecision',['tests/test_output_adapter.py'],['tests/integration_output_adapter.py --production'],'docs/proofs/output-adapter-production-20261003.json',['Small individually approved external native first-position vocabulary delta; unchanged native weights and unbiased remaining positions; no broad semantic quality/phone or native base-training claim']),
        ('F7_MEASURED_PLASTICITY','§16 / STEP5',['v13/plasticity.py','v13/learning.py'],'F7','PlasticityState/PlasticityBudget',['tests/test_plasticity.py'],['tests/integration_learning.py'],'docs/proofs/f7-learning-crash-native-20261002.json',['Bounded slow feedback controller over measured external shadow trials; not a neural learned controller, shared native interference measurement, semantic consolidation or autonomous authority']),
        ('STEP0_DURABLE_QUEUE','§96 STEP0',['v13/store.py','v13/runtime.py','v13/backup.py'],'F7_RUNTIME','EventEnvelope / SQLite accepted_turns',['tests/test_migrations.py','tests/test_runtime_queue.py','tests/test_runtime_queue_audit.py'],['tests/integration_real.py'],'docs/proofs/runtime-queue-combined-20261004.log',['Pending accepted input persists; started interrupted work is not automatically duplicated; configured queue TTL still applies']),
        ('STEP1_EXECUTIVE_CONTINUITY','§3.3.4 / §4.5 / §1.6',['v13/executive.py','v13/runtime.py'],'C1_EXEC','ExecState/ExecutiveControlContext/OutputSnapshot',['tests/test_executive.py'],['tests/integration_executive.py'],'docs/proofs/executive-native-20261004.json',['Explicit source-bound state and control constraints; no trained executive latent objective or general taskcompletion proof']),
        ('F7_NATIVE_PRESSURE_MONITOR','§96 STEP0/STEP7',['v13/resources.py','v13/pressure.py','v13/runtime.py'],'F7_RUNTIME','Native process identity / bounded resource samples',['tests/test_process_memory.py','tests/test_resource_monitor.py'],['tests/integration_resources.py'],'docs/proofs/resource-monitor-native-20261004.json',['Actual native RSS/PSS, cancellation/restart scope; real thermal/RAM critical stress and native KV bytes remain unmeasured']),
        ('STEP7_BOUNDED_COLLECTION','§96 STEP7',['v13/proofs.py'],'F7+F11','ActionOutcome',[],['v13.proofs.probe_sustained'],'docs/proofs/acceptance-20260929/sustained.json',['Short collection does not establish weeks of retention, thermal/energy or a memory ceiling'])]
    for fid,canon,files,owner,schema,unit,integration,benchmark,limits in additions:
        rows.append(dict(common,feature_id=fid,canon_source=canon,implementation_files=files,runtime_owner=owner,state_owner=owner,schema_id=schema,unit_tests=unit,integration_tests=integration,benchmark=benchmark,gate_status='PARTIAL',known_limitations=limits))
    for row in rows:
        if row['feature_id']=='STEP0_LOGGING_MIGRATION':row.update(unit_tests=row['unit_tests']+['tests/test_log_retention.py'],known_limitations=['System wall-clock age; telemetry expiry on startup and every 200 rows, runner expiry on startup'])
        if row['feature_id']=='STEP1_JEF_VERTICAL':row['known_limitations']=['External first native route agreement calibration implemented; general/native semantic confidence uncalibrated','C3 quality and sustained target-phone JEF remain open','Paired C3 comparison and independent/combined JEF modes executed on Linux; no model selection or phone proof inferred']
    return {'ledger_version':2,'canonical_architecture_complete':False,'rows':rows,'component_contracts':component_registry(),'learning_objectives':objective_registry(r),'native_smoke_evidence':evidence,'step12_proof_path':r.store.meta('latest_step12_proof'),'jef_modes_proof_path':r.store.meta('latest_jef_modes_proof'),'sustained_proof_path':r.store.meta('latest_sustained_proof')}

def unresolved_items(r):
    # Only questions that genuinely need the operator belong here. Proof gaps are not user questions.
    return {'artifact_version':1,'user_decision_required':[],
            'research_needed':['Paired native C3 4+4 comparison complete; broader German quality and target-phone latency/memory comparison remain open.',
                               'STEP2 semantic utility needs validated scoring; sparse-body/full A/B-JEPA, multimodal A3/receiver projectors, native confidence-head training, multi-position native output adaptation and parametric semantic/skill consolidation remain open. External first-route agreement calibration, dense local predictors and bounded wake/halt heads are separate implemented experiments.'],
            'hard_blockers':['Target-phone sustained thermal/energy + RSS/KV pressure proof requires another real Redmi run.',
                             'Native sparse-body training and B3 latent receiver-effect proof require capabilities not present in this Age-0 build.'],
            'can_decide_autonomously':['Continue STEP1 JEF proof, STEP2 complementarity measurement, and STEP3 second-attempt proof without architecture redesign.']}

def write_build_artifacts(r):
    out=r.home/'exports';out.mkdir(parents=True,exist_ok=True)
    ledger=completion_ledger(r);questions=unresolved_items(r)
    log_policy={'policy_id':'LOG_POLICY-001','revision':3,'telemetry':{'raw_content_allowed':False,'source_ref_preferred':True,'retention':'bounded rows and age','retention_days':r.cfg['log_retention_days'],'age_enforcement':'Startup and each 200 diagnostic rows; budget change immediately prunes old telemetry','max_rows_approx':10000,'enforcement':'Allowlisted metric keys, enums and opaque IDs; arbitrary strings redacted; unknown keys dropped. Existing telemetry scrubbed once on upgrade.','resource_samples_per_attempt':64},'runner_logs':{'rotation':'size','rotation_bytes':3145728,'generations':2,'retention_days':r.cfg['log_retention_days'],'age_enforcement':'Startup; only known runner diagnostic names, no symlinks or traversal','raw_content_allowed':False,'enforcement':'Pinned llama runner starts with --log-disable; native diagnostic files retained separately.'},'clear_logs_scope':'diagnostic logs + telemetry only; never chat/memory/experience/exports/proofs'}
    atomic_write(out/'schema-registry.json',dumps(schema_registry()))
    atomic_write(out/'component-contracts.json',dumps(component_registry()))
    atomic_write(out/'learning-objectives.json',dumps(objective_registry(r)))
    atomic_write(out/'completion-ledger.json',dumps(ledger))
    atomic_write(out/'logging-policy.json',dumps(log_policy))
    md='# V13 — User Decisions and Open Questions\n\n'
    md+='## USER_DECISION_REQUIRED\n\nNone.\n\n## RESEARCH_NEEDED\n\n'+''.join('- '+x+'\n' for x in questions['research_needed'])+'\n## HARD_BLOCKER\n\n'+''.join('- '+x+'\n' for x in questions['hard_blockers'])+'\n## CAN_DECIDE_AUTONOMOUSLY\n\n'+''.join('- '+x+'\n' for x in questions['can_decide_autonomously'])
    atomic_write(out/'USER_DECISIONS_AND_OPEN_QUESTIONS.md',md)
    return {'schema_registry':str(out/'schema-registry.json'),'completion_ledger':str(out/'completion-ledger.json'),'logging_policy':str(out/'logging-policy.json'),'open_questions':str(out/'USER_DECISIONS_AND_OPEN_QUESTIONS.md')}

def doctor(r,full=False):
    artifacts=write_build_artifacts(r)
    models=r.models.verify(full);missing=[x for x in ['language','body','needle'] if x not in models];integrity=r.store.integrity(full)
    return {'build':'0.1.0-age0-lab','canonical_architecture_complete':False,'device':device(),'data_integrity_errors':integrity,'models':models,'missing_models':missing,'native_runner_exists':(r.home/'bin/llama-server').exists(),'native_capabilities':native_capability_profile(r),'needle_embedding_worker_exists':(r.home/'bin/needle-worker').exists(),'resources':r.resources(),'learning_mode':r.cfg['learning_mode'],'active_generation':r.store.generation_id,'gates':GATES,'B3':{direction:{'injection_level':0,'latent_read_authority':0,'latent_learn_authority':0,'native_taps':False,'calibration':None,'downstream_utility':None,'router_collision_metrics':None,'fallback':r.cfg['channel']} for direction in ['B1_TO_B2','B2_TO_B1']},'latest_native_probe':r.store.meta('latest_native_probe'),'native_smoke_evidence':native_probe_evidence(r),'latest_step12_proof':r.store.meta('latest_step12_proof'),'latest_jef_modes_proof':r.store.meta('latest_jef_modes_proof'),'defaults_status':'BOOT estimates, see :budget','build_artifacts':artifacts,'completion_ledger_summary':{x['feature_id']:x['gate_status'] for x in completion_ledger(r)['rows']}}

def probe(r):
    old=r.session;oldlast=r.store.meta('last_session');r.session=r.store.new_session('Native Runner Probe');result={'device':device(),'model_revisions':r.revisions(),'roles':{},'full_runner_proof':False,'phone_measured':device()['android'],'gates':GATES,'proof_kind':'NATIVE_SMOKE','created_wall_time':time.time(),'effective_config':dict(r.cfg)}
    try:
        e=r.store.event(r.session,'Projekt Test: Budget 120 Euro. Berechne die Hälfte.');r.cognition.percept(e)
        for role in ['C3_LANGUAGE','B1_DETAIL','B2_GIST']:
            start=time.monotonic()
            try:
                runner=r.pool.get(role);deadline=time.monotonic()+r.cfg['deadline_seconds'];answer=''.join(runner.generate([{'role':'system','content':'Antworte kurz auf Deutsch.'},{'role':'user','content':'Sag kurz Hallo. Was kann ich dich fragen?'}],r.cancel_event,deadline,48))
                result['roles'][role]={'ok':bool(answer.strip()),'actual_output':answer,'metrics':runner.last_metrics}
                if role!='C3_LANGUAGE':
                    p=r.cognition.offer(role,e,0,time.monotonic()+r.cfg['observer_seconds']);result['roles'][role]['structured_offer']={'verified_quote_count':len(p['evidence_refs']),'rejected_quote_count':p['rejected_quotes'],'actual':p['offer']}
                result['roles'][role]['unload']=r.pool.unload()
            except Exception as exc:result['roles'][role]={'ok':False,'error':str(exc),'duration_s':time.monotonic()-start};r.pool.unload()
        try:
            vector=r.needle.embed('Projekt Test: Budget 120 Euro.',r.cancel_event,time.monotonic()+15);control=r.needle.control('Berechne die Hälfte von 120.',r.cancel_event,time.monotonic()+15)
            result['roles']['C2_CONTROL']={'ok':len(vector)>0,'embedding_dim':len(vector),'embedding_squared_norm':sum(v*v for v in vector),'embedding_hash':digest(dumps(vector)),'actual_control':control,'metrics':r.needle.last_metrics,'confidence_calibrated':False}
        except Exception as exc:result['roles']['C2_CONTROL']={'ok':False,'error':str(exc)}
        finally:r.needle.unload()
        result['status']='SMOKE_PASS' if all(p['ok'] for p in result['roles'].values()) else 'SMOKE_PARTIAL';result['missing_proofs']=['sustained thermal/energy','target-phone RSS/KV growth under pressure','native sparse body training','B3 receiver-effect ablations','long-term retention']
        path=r.home/'exports/native-probe.json';archive_previous(path);atomic_write(path,dumps(result));r.store.set_meta('latest_native_probe',str(path));return result
    finally:r.session=old;r.store.set_meta('last_session',oldlast or old)
