from contextlib import contextmanager
import fcntl
import json
import os
import re
from pathlib import Path
import sqlite3
import threading
import time
from .common import uid,now,dumps,digest,atomic_write,file_hash,Limits
from .contracts import packet,validate
from .config import DEFAULTS
COMPONENT_ENCODERS={'route':'C2_CONTROL','wake':'C2_CONTROL','halt':'C2_CONTROL','b1_predictor':'B1_DETAIL','b2_predictor':'B2_GIST','a3_student':'C2_CONTROL','world_predictor':'C2_CONTROL'}
COMPONENT_ENCODERS['control_calibration']='C2_CONTROL'
COMPONENT_ENCODERS['memory_retrieval']='C2_CONTROL'
COMPONENT_ENCODERS.update(skill='C2_CONTROL',memory='C2_CONTROL',channel='C2_CONTROL')  # WP-T1 fast heads
COMPONENT_ENCODERS['output_adapter']='C3_LANGUAGE'

# Diagnostic telemetry carries measurements/IDs, never arbitrary native reasoning,
# exception bodies or user text. Exact content remains in its provenance store.
TELEMETRY_FIELDS=set(DEFAULTS)|set('''id memory_id memory_ids kind permission update_id generation request scope role error detail status
model_generated output_owner route source scaffold calibrated native_control_metrics control_unavailable decision margin
selected_offer_ids query_packet_id direct_source_copy resource_fallback fallback self_candidate_hash duration_s characters effective_config
context_offer_ids context_chars state_policy
focal focal_loop action_selection cycles coalition inquisition
memory_retrieval source_ref source_id sha256 char_start char_end modality retrieval_score
stage_durations_s last_phase elapsed_in_last_phase_s requested_tokens input_message_count load_s template_s prefill_to_first_token_s stream_s
stage_marks_s turn_stage failure_stage ingress perception_and_state memory_recall routing preanswer_observers output_prepare native_answer finished
interruption_unload process_reaped
first_output_monotonic_ns runner model_revision operation mode embeddings_available actual_model generated_tokens
prompt_tokens history_trimmed ttft_s timings predicted_n predicted_ms predicted_per_second predicted_per_token_ms
prompt_n prompt_ms prompt_per_second prompt_per_token_ms memory process_memory pid rss_bytes pss_bytes
mapped_file_bytes minor_faults major_faults sampled_peak_rss_bytes sampled_peak_pss_bytes resource_sample_count
resource_samples sample_interval_s elapsed_s phase CAN_LATENT_TAP CAN_LATENT_INJECT CAN_TRAIN_BODY
affects_committed_output rules_preserved metrics objective n embedding_dim trainable_parameter_count nontrainable_trace_count
loss_before loss_after held_out finite_difference_max_error gradient_check deterministic_repeat checkpoint_reload finite
device android cpu_count machine system python energy_joules phone_benchmark body_parameters_modified commit_eligible
before after count simple detail gist both timing_error_s scored
component action learned prediction fallback_reason wake_decision halt_decision baseline context_revision trajectory_offer_ids context_ref
probabilities confidence support_cosine support_floor in_support temperature calibration_scope
calibration_pass effective_accuracy scaffold_accuracy accepted_test_count cost_before cost_after missed_continue bounded_label_cost_pareto
partition train calibration test accuracy brier ece loss per_class uncalibrated 0 1 2 3
optimizer_steps target_parameter_count native_body_parameters_modified horizon_native_tokens ema_decay target_stop_gradient target_changed
train_pairs held_out_pairs prediction_mse copy_baseline_mse shuffled_target_mse target_std_mean target_std_ratio effective_rank predicted_std_mean
noncollapse_pass predictive_ablation_pass retention_pass master_weight_bytes ema_target_bytes activation_input_bytes
semantic_quality_proven receiver_authority tap_id pooling normalization runner_revision
student_shadow packet_id percept_packet_id student_route teacher_route agreement routing_authority
raw_dim latent_dim teacher_dim train_sources held_out_sources observed_target_std_mean reconstruction_preconditioner
teacher_mse reconstruction_mse teacher_cosine_mean teacher_variance_ratio mean_baseline alignment_off reconstruction_off
alignment_gain reconstruction_gain separate_ablation_pass teacher_parameter_updates teacher_truth_authority native_receiver_authority'''.split())
TELEMETRY_FIELDS.update('''action_ablation_pass no_action_mse shuffled_action_mse fixed_target_retention_mse
state_geometry_loss state_geometry_weight digital_latent_error world_transition_packet_id action_role action_source_count
held_out_support_pass support_state_bytes coverage_scope confidence_calibrated'''.split())
TELEMETRY_FIELDS.update('''control_calibration native_control_rejected calibrated_confidence raw_confidence route_observation_count
native_baseline correct_rate mean_confidence max_applied_step_norm semantic_truth_authority proposal_count ambiguous'''.split())
TELEMETRY_ENUMS=set('''FINAL CANCELLED DEADLINE ERROR INTERRUPTED PASS REJECTED PENDING_APPROVAL ABORTED
C2_CONTROL C3_LANGUAGE B1_DETAIL B2_GIST TEACHER C5_REPORT_BROKER TEXT_REPORT
BOOT_SCAFFOLD OPERATOR_ROUTE_OVERRIDE APPROVED_EXTERNAL_HEAD NATIVE_C2_ADVISORY EXPLICIT_EXACT_COPY
B2_BOUNDED_SOURCE_CONTEXT B1_SHORT_WINDOW
RECORD_ONLY SHADOW_UPDATE APPROVED_COMMIT NO_MESSAGE SOURCE_EXACT CONTROL SYMBOLIC
auto simple detail gist both background off load template prefill stream text C E native_cli_fallback
ingress perception_and_state memory_recall routing preanswer_observers output_prepare native_answer finished
turn download shadow teacher dream probe observers fact route global session EXPLICIT_OPERATOR
explicit-human-route-cross-entropy-v1 explicit-human-wake-readout-v1 explicit-human-halt-readout-v1
wake halt none continue NO_APPROVED_COMPONENT APPROVED_BOUNDED_READOUT OUT_OF_SUPPORT_OR_UNCERTAIN held_out_bounded_readout
b1_predictor b2_predictor dense-body-future-state-predictor-v1 EVALUATED_FAIL PREFILL_TAP lfm2.result_norm.final.v1 native_final_RMSNorm_only b10964
a3_student alignment a3-text-teacher-alignment-reconstruction-v1 OUT_OF_SUPPORT UNAVAILABLE
world_predictor world SOURCE_COPY world-digital-action-latent-v1
MEASURED_FROZEN_INPUT_AND_ACTUAL_ACTION_ROLE
control_calibration native-route-confidence-calibration-v1 HELD_OUT_NATIVE_ROUTE_AGREEMENT_ONLY
Unavailable Limits Cancelled ValueError RuntimeError'''.split())
TELEMETRY_FIELDS.update('probability retrieval_policy recall false_positive_rate balanced_accuracy retrieval_gain semantic_ablation_pass retained_test semantic_off lexical_retrieval effective_retrieval'.split())
# WP-V8: exception class names are not content; keep them so `except` logs stay diagnosable.
import builtins
TELEMETRY_ENUMS.update(n for n,v in vars(builtins).items() if isinstance(v,type) and issubclass(v,BaseException))
TELEMETRY_ENUMS.update('Unavailable Cancelled Limits InvalidRule'.split())
TELEMETRY_ENUMS.update('memory_retrieval retrieval admit reject baseline APPROVED_SOURCE_BOUND_RELEVANCE source-bound-semantic-retrieval-v1'.split())
TELEMETRY_FIELDS.update('plasticity_gain stability_score saturation consolidation_ready trials state_trials retained_cases_saved retained_support_preserved effective_learning_rate effective_max_update_norm'.split())
TELEMETRY_FIELDS.update('index_id confirmations members schema source_refs'.split())
TELEMETRY_ENUMS.update('semantic procedural consolidation APPROVED_SOURCE_BOUND_PROCEDURE V13_REPEATED_CONFIRMATION_INDEX_V1'.split())
TELEMETRY_FIELDS.update('nearest_native_cosine first_token_bias native_state_dimension vocabulary_rows held_out_per_native_token per_native_token first_native_token_accuracy_pass utility_pass finite_difference_sampled_coordinates token_id pass'.split())
TELEMETRY_FIELDS.update('executive_control_context_id executive_control_abstention executive_control_policy executive_state_version output_snapshot_id output_authority native_pressure resource_state critical_reason resource_cancel_signalled sample_count observer_failures samples transitions snapshot critical_snapshot monitor_stopped native_kv_bytes mem_available_bytes mem_total_bytes free_disk_bytes battery_temperature_c battery_percent charging processes own_peak_rss_bytes'.split())
TELEMETRY_ENUMS.update('output_adapter APPROVED_FIRST_NATIVE_TOKEN_DELTA EXTERNAL_FIRST_NATIVE_TOKEN_VOCABULARY_ROW_DELTA c3-native-first-token-delta-v2 LOCAL_PROCESSING_ONLY RESOURCE_CONTROL_ABSTENTION STALE_CONTROL_CONTEXT REVOKED_CONTROL_SOURCE SOURCE_SYSTEM_REPORT NORMAL PRESSURE RECOVERY CRITICAL MEMORY_CRITICAL THERMAL_CRITICAL MEMORY_AND_THERMAL_CRITICAL'.split())
TELEMETRY_FIELDS.update('output_removed_characters output_policy rule_id rule_version exact_policy_matched skipped_native_stages policy_check'.split())
TELEMETRY_ENUMS.update('APPROVED_FIXED_RULE FIXED_EXACT EXPLICIT_EXACT_POLICY policy_check A3_NATIVE_ALIGNMENT SEMANTIC_RECALL B_OBSERVERS C3_DECODE NATIVE_WORLD_PREDICTION'.split())
TELEMETRY_FIELDS.update('priority items passed failed retired hypotheses retention_rate origin'.split())  # WP-E sleep/scheduler
TELEMETRY_ENUMS.update('sleep full wake a b c DONE INTERRUPTED SKIPPED_RESOURCE_RED SKIPPED_RESOURCE_YELLOW USER SYSTEM SELF USER_INPUT TOOL_EVENT RESOURCE_CHANGE TIMER GOAL_WAKE REPLAY_DUE IDLE'.split())
TELEMETRY_ID=re.compile(r'(?:[a-f0-9]{40}|[a-f0-9]{64}|(?:pkt|evt|gen|mem|src|upd|req|rule|fixed|chat|exp|consolidation)_[a-f0-9]{28,32})\Z')
TELEMETRY_FIELDS.update('mode candidates encoded_keys deferred_keys dim encoder texts cold_load embedding_similarity retrieval_channel'.split())  # WP-H
TELEMETRY_ENUMS.update('on off shadow OK UNAVAILABLE lexical embedding learned'.split())
TELEMETRY_FIELDS.update('cut score reason signals context_shift prediction_error goal_shift action_transition source_transition correction failure pause episode stage'.split())  # WP-N8
TELEMETRY_ENUMS.update('first signals max_events observe'.split())
TELEMETRY_FIELDS.update('component measure value cap n passed probes_sha256 items'.split())  # WP-S5
TELEMETRY_ENUMS.update('LM_KL DECISION_FLIP route wake halt output_adapter memory_retrieval'.split())
TELEMETRY_FIELDS.update('decision relation latency_ms'.split())  # WP-N14
TELEMETRY_ENUMS.update('CONTINUE INTERRUPT REVISE OVERLAP STOP CORRECTION interrupt'.split())
TELEMETRY_FIELDS.update('action authority seconds width height encoder'.split())  # WP-N15
TELEMETRY_ENUMS.update('add describe train REFERENCE_NOT_FACT hashed_bow'.split())
TELEMETRY_ENUMS.update('NO_LIMITS NO_DATA'.split())  # WP-T14 control budget
TELEMETRY_FIELDS.update('exact_retained firing binding native_sha256 model_sha256 binary_sha256 sidecar_sha256 batch_id reasons provenance'.split())  # WP-T9 source-bound shadow inventory
TELEMETRY_ENUMS.update('SHADOW UNMEASURED NO_MATCHING_LOADED_BINDING INVALID_NATIVE_ROW_MAP NOT_ORDINARY_FACT NO_BOUND_LIVE_ROWS SOURCE_OR_CONTENT_MISMATCH BOUND_FACT_POSSIBLE_FIRING_UNMEASURED INVENTORY_ONLY'.split())

TELEMETRY_FIELDS.update('native_memory_firing request_status loaded_binding quality_proven activation_authorized layer evaluated_rows batches slot_applied_counts slot_guard_blocked_counts fired_rows observed_memory_ids observed_provenance firing_reason native_request'.split())
TELEMETRY_ENUMS.update('OBSERVED_NATIVE_WRITES REQUEST_WRITES_ONLY REQUEST_NOT_FINAL REQUEST_NOT_COMPLETED REQUEST_BINDING_CHANGED AUDIT_LOG_CHANGED AUDIT_LOG_UNREADABLE AUDIT_WINDOW_LIMIT NO_REQUEST_WINDOW MULTIPLE_NATIVE_STEPS NO_PROMPT_MARKER NO_EVALUATED_ROWS MULTIPLE_REQUESTS NO_REQUEST_OBSERVATION AUDIT_BINDING_OR_AUTHORITY_INVALID INVALID_REQUEST_ROW_MAP'.split())
TELEMETRY_FIELDS.update('resource_mode orange_mb yellow_mb'.split())  # §97.2 resource modes
TELEMETRY_FIELDS.update('observer_schedule schedule pre post parallel sampled rss_mb'.split())  # §22.2.4 observer scheduling, §73 RSS budget
TELEMETRY_ENUMS.update('A_THEN_B_SEQUENTIAL B_THEN_A_SEQUENTIAL ALWAYS_BOTH_ASYNC JEF_FIRST_THEN_BOTH SAMPLED_OBSERVER ON_DEMAND_REENTRY ASYNC_NEEDS_TWO_RESIDENT_BODIES SAMPLED_OUT ON_DEMAND_ONLY RSS_OVER_YELLOW RSS_OVER_ORANGE B1_DETAIL B2_GIST'.split())
TELEMETRY_ENUMS.update('GREEN YELLOW ORANGE RED UNCALIBRATED DEVICE_MEASURED HOST_MEASURED_NOT_REDMI MEM_BELOW_RED MEM_BELOW_ORANGE MEM_BELOW_YELLOW TEMP_AT_RED TEMP_AT_ORANGE TEMP_AT_YELLOW'.split())
TELEMETRY_FIELDS.update('direction level_from level_to triggers'.split())  # WP-N19 B3-H10 degradation
TELEMETRY_ENUMS.update('B1_TO_B2 B2_TO_B1 L4 L3 L2 L1 EXACT_SYMBOLIC NO_MESSAGE RECEIVER_REVISION_CHANGED RUNNER_REVISION_CHANGED CALIBRATION_EXPIRED PROJECTOR_COLLAPSED ROUTER_DRIFT EXPERT_FLIP_SPIKE RETENTION_REGRESSED MESSAGE_UTILITY_FELL COST_OVER_BUDGET ROLE_DIVERSITY_COLLAPSED PROMOTED_EXPLICIT_HUMAN'.split())

def telemetry_metrics(value):
    if isinstance(value,dict):
        result={}
        for k,v in value.items():
            if k not in TELEMETRY_FIELDS:continue
            if k in {'per_native_token','held_out_per_native_token'} and isinstance(v,dict):
                result[k]=[{'token_id':int(token),**telemetry_metrics(metrics)}
                           for token,metrics in list(v.items())[:16]
                           if isinstance(token,str) and re.fullmatch(r'[0-9]{1,5}',token)
                           and int(token)<65536 and isinstance(metrics,dict)]
            else:result[k]=telemetry_metrics(v)
        return result
    if isinstance(value,(list,tuple)):return [telemetry_metrics(v) for v in value[:64]]
    if isinstance(value,str):return value if value in TELEMETRY_ENUMS or TELEMETRY_ID.fullmatch(value) else {'redacted':True,'bytes':len(value.encode())}
    if value is None or isinstance(value,(bool,int,float)):return value
    return {'redacted':True}

DDL='''
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,hash TEXT NOT NULL,kind TEXT NOT NULL,bytes INTEGER NOT NULL,chars INTEGER NOT NULL,created REAL NOT NULL,deleted INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY,title TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS generations(id TEXT PRIMARY KEY,parent TEXT REFERENCES generations(id),manifest TEXT NOT NULL,hash TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY,session_id TEXT NOT NULL REFERENCES sessions(id),source_id TEXT NOT NULL REFERENCES sources(id),experience_id TEXT UNIQUE NOT NULL,generation_id TEXT NOT NULL REFERENCES generations(id),packet TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,session_id TEXT NOT NULL REFERENCES sessions(id),event_id TEXT REFERENCES events(id),role TEXT NOT NULL,text TEXT NOT NULL,status TEXT NOT NULL,metadata TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS packets(id TEXT PRIMARY KEY,kind TEXT NOT NULL,event_id TEXT NOT NULL,generation_id TEXT NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS states(key TEXT PRIMARY KEY,version INTEGER NOT NULL,payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES events(id),kind TEXT NOT NULL,status TEXT NOT NULL,corollary_id TEXT NOT NULL REFERENCES packets(id),expected TEXT NOT NULL,outcome TEXT,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS feedback(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES events(id),source_id TEXT NOT NULL REFERENCES sources(id),kind TEXT NOT NULL,value TEXT NOT NULL,permission TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES events(id),source_id TEXT NOT NULL REFERENCES sources(id),session_id TEXT NOT NULL REFERENCES sessions(id),kind TEXT NOT NULL,scope TEXT NOT NULL,key_text TEXT NOT NULL,value TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS updates(id TEXT PRIMARY KEY,base_generation TEXT NOT NULL REFERENCES generations(id),status TEXT NOT NULL,path TEXT,hash TEXT,manifest TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS rules(id TEXT PRIMARY KEY,parent TEXT REFERENCES rules(id),rules TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,status TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS telemetry(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,event_id TEXT,metrics TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS replay(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES events(id),kind TEXT NOT NULL,priority REAL NOT NULL,status TEXT NOT NULL,created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS event_session ON events(session_id,created);
CREATE INDEX IF NOT EXISTS message_session ON messages(session_id,id);
CREATE INDEX IF NOT EXISTS memory_scope ON memories(session_id,active,kind);
CREATE INDEX IF NOT EXISTS packet_event ON packets(event_id,kind);
CREATE INDEX IF NOT EXISTS telemetry_time ON telemetry(created);
'''

SCHEMA_VERSION=2
MIGRATION_DDL="""
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,from_version INTEGER NOT NULL,applied REAL NOT NULL,ddl_sha256 TEXT NOT NULL);
"""
QUEUE_DDL="""
CREATE TABLE accepted_turns(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT UNIQUE NOT NULL REFERENCES events(id),request_key TEXT UNIQUE,bytes INTEGER NOT NULL CHECK(bytes>0),accepted_at REAL NOT NULL,state TEXT NOT NULL CHECK(state IN ('PENDING','RUNNING','DONE','CANCELLED','DEADLINE','ERROR','INTERRUPTED')),started_at REAL,finished_at REAL);
CREATE INDEX accepted_turn_state ON accepted_turns(state,sequence);
"""

def _execute_ddl(db,ddl):
    # executescript commits an existing transaction implicitly; individual statements
    # preserve the version + schema + journal atomicity even if a later DDL fails.
    for statement in ddl.split(';'):
        if statement.strip():db.execute(statement)

def audit_schema(db,version=SCHEMA_VERSION):
    """Compare SQLite's actual columns, constraints and indexes to the owned schema."""
    if version not in (1,2):raise RuntimeError('Nicht unterstützte Datenbankschema-Version')
    expected=sqlite3.connect(':memory:')
    try:
        expected.executescript(DDL+(MIGRATION_DDL+QUEUE_DDL if version==2 else ''))
        tables=[r[0] for r in expected.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        errors=[]
        for table in tables:
            # These names come from the static DDL, never operator SQL.
            pragma=lambda conn,kind:list(map(tuple,conn.execute(f'PRAGMA {kind}("{table}")')))
            if pragma(db,'table_info')!=pragma(expected,'table_info'):errors.append(table+': columns')
            if sorted(pragma(db,'foreign_key_list'))!=sorted(pragma(expected,'foreign_key_list')):errors.append(table+': foreign keys')
            def indexes(conn):
                result=[]
                for row in conn.execute(f'PRAGMA index_list("{table}")'):
                    cols=tuple(r[2] for r in conn.execute(f'PRAGMA index_info("{row[1]}")'))
                    result.append((row[2],row[3],row[4],cols))
                return sorted(result,key=repr)
            if indexes(db)!=indexes(expected):errors.append(table+': indexes')
            sql=lambda conn:conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
            actual=sql(db);owned=sql(expected)
            normalize=lambda text:re.sub(r'\s+','',text.lower().replace('IF NOT EXISTS'.lower(),''))
            if not actual or normalize(actual[0])!=normalize(owned[0]):errors.append(table+': constraints')
        if db.execute('PRAGMA foreign_key_check').fetchall():errors.append('foreign_key_check')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':errors.append('integrity_check')
        if errors:raise RuntimeError('Datenbankschema beschädigt: '+', '.join(errors))
    finally:expected.close()
    return {'version':version,'tables':tables,'foreign_keys':'PASS','structure':'PASS'}

def audit_migration_journal(db):
    expected={1:(0,digest(DDL+MIGRATION_DDL)),2:(1,digest(MIGRATION_DDL+QUEUE_DDL))}
    rows=list(db.execute('SELECT version,from_version,ddl_sha256 FROM schema_migrations ORDER BY version'))
    if not rows or rows[-1][0]!=SCHEMA_VERSION:raise RuntimeError('Migrationsjournal unvollständig')
    for row in rows:
        if row[0] not in expected or (row[1],row[2])!=expected[row[0]]:raise RuntimeError('Migrationsjournal inkonsistent')
    return [row[0] for row in rows]

def migrate_database(db):
    """Transactional monotonic migrations, also used on verified restore staging DBs."""
    version=db.execute('PRAGMA user_version').fetchone()[0]
    if version>SCHEMA_VERSION:raise RuntimeError('Datenbank neuer als Build')
    if version<0:raise RuntimeError('Ungültige Datenbankschema-Version')
    if version: audit_schema(db,version)
    while version<SCHEMA_VERSION:
        target=version+1
        ddl=DDL+MIGRATION_DDL if target==1 else MIGRATION_DDL+QUEUE_DDL
        db.execute('BEGIN IMMEDIATE')
        try:
            _execute_ddl(db,ddl)
            audit_schema(db,target)
            db.execute('INSERT INTO schema_migrations VALUES (?,?,?,?)',(target,version,now(),digest(ddl)))
            db.execute(f'PRAGMA user_version={target}')
            db.execute('COMMIT')
        except BaseException:
            if db.in_transaction:db.execute('ROLLBACK')
            raise
        version=target
    report=audit_schema(db,SCHEMA_VERSION);report['migrations']=audit_migration_journal(db)
    return report

def audit_closed(home):
    """Read-only integrity/size probe of a closed Store; never checkpoints or repairs."""
    db=Path(home)/'data/db/brain.sqlite3';side={n:(db.parent/(db.name+n)) for n in ('-wal','-shm')}
    report={'file_bytes':db.stat().st_size,'wal_bytes':side['-wal'].stat().st_size if side['-wal'].exists() else None,'shm_bytes':side['-shm'].stat().st_size if side['-shm'].exists() else None}
    conn=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True,isolation_level=None)
    try:
        report['page_count']=conn.execute('PRAGMA page_count').fetchone()[0];report['page_size']=conn.execute('PRAGMA page_size').fetchone()[0]
        report['quick_check']=[r[0] for r in conn.execute('PRAGMA quick_check(5)').fetchall()]
    except sqlite3.DatabaseError as exc:report['error']={'type':type(exc).__name__,'message':str(exc)}
    finally:conn.close()
    report['ok']=report.get('quick_check')==['ok']
    return report

def preserve_sqlite(home,destination):
    """Copy database plus WAL/SHM sidecars byte-for-byte into a new directory."""
    db=Path(home)/'data/db/brain.sqlite3';destination=Path(destination);destination.mkdir(parents=True)
    copied={}
    for path in [db]+[db.parent/(db.name+n) for n in ('-wal','-shm')]:
        if path.exists():
            target=destination/path.name;target.write_bytes(path.read_bytes());copied[path.name]={'bytes':target.stat().st_size,'sha256':file_hash(target)}
    atomic_write(destination/'copied-files.json',dumps(copied))
    return copied

class Store:
    def __init__(self,home,log_retention_days=DEFAULTS['log_retention_days']):
        self.home=Path(home);self.mutex=threading.RLock();self.closed=False;self.log_retention_days=log_retention_days
        self.lock=open(home/"data/coordinator.lock","a+")
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:self.lock.close();raise RuntimeError("V13 läuft bereits mit diesem Speicher")
        self.lock.seek(0);self.lock.truncate();self.lock.write(str(os.getpid()));self.lock.flush()
        self.db=None
        try:
            self.db=sqlite3.connect(home/"data/db/brain.sqlite3",check_same_thread=False,isolation_level=None,timeout=10);self.db.row_factory=sqlite3.Row
            # Reject future versions before changing journal mode or any persisted data.
            if self.db.execute("PRAGMA user_version").fetchone()[0]>SCHEMA_VERSION:raise RuntimeError("Datenbank neuer als Build")
            self.db.execute("PRAGMA foreign_keys=ON");self.db.execute("PRAGMA journal_mode=WAL");self.db.execute("PRAGMA synchronous=FULL")
            migrate_database(self.db)
            self._recover()
        except BaseException:
            try:
                if self.db is not None:self.db.close()
            finally:self.closed=True;self.release_lock()
            raise
    def _recover(self):
        with self.tx() as c:
            for row in c.execute("SELECT event_id FROM accepted_turns WHERE state='RUNNING'").fetchall():
                terminal=c.execute("SELECT status FROM messages WHERE event_id=? AND role='assistant' AND status IN ('FINAL','CANCELLED','DEADLINE','ERROR','INTERRUPTED') ORDER BY id DESC LIMIT 1",(row['event_id'],)).fetchone()
                state=('DONE' if terminal['status']=='FINAL' else terminal['status']) if terminal else 'INTERRUPTED'
                c.execute("UPDATE accepted_turns SET state=?,finished_at=? WHERE event_id=?",(state,now(),row['event_id']))
            c.execute("UPDATE accepted_turns SET state='CANCELLED',finished_at=? WHERE state='PENDING' AND event_id IN (SELECT e.id FROM events e JOIN sources s ON s.id=e.source_id WHERE s.deleted=1)",(now(),))
        self.prune_telemetry()
        with self.tx() as c:
            c.execute("UPDATE messages SET status='INTERRUPTED' WHERE status IN ('STREAMING','DRAFT','OUTPUT_COMMITTED')")
            c.execute("UPDATE actions SET status='OUTCOME_UNKNOWN' WHERE status='DISPATCHED'")
            c.execute("UPDATE updates SET status='ABORTED' WHERE status IN ('SHADOW_TRAINING','EVALUATING')")
            c.execute("UPDATE replay SET status='PENDING' WHERE status='RUNNING'")
        if not self.meta("active_generation"):
            with self.tx() as c:
                rid=uid("rule");c.execute("INSERT INTO rules VALUES (?,?,?,?)",(rid,None,dumps([]),now()));self._generation(c,None,{}, {},rid,{},[])
        if self.meta('telemetry_policy_revision',0)<2:
            with self.tx() as c:
                for row in c.execute('SELECT id,metrics FROM telemetry').fetchall():
                    try:clean=telemetry_metrics(json.loads(row['metrics']))
                    except (ValueError,TypeError):clean={'redacted':True}
                    c.execute('UPDATE telemetry SET metrics=? WHERE id=?',(dumps(clean),row['id']))
                c.execute("INSERT OR REPLACE INTO meta VALUES ('telemetry_policy_revision','2')")
    @contextmanager
    def tx(self):
        with self.mutex:
            self.db.execute("BEGIN IMMEDIATE")
            try:yield self.db;self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:self.db.execute("ROLLBACK")
                raise
    def rows(self,sql,args=()):
        with self.mutex:return [dict(x) for x in self.db.execute(sql,args).fetchall()]
    def one(self,sql,args=()):
        rows=self.rows(sql,args);return rows[0] if rows else None
    def meta(self,key,default=None):
        row=self.one("SELECT value FROM meta WHERE key=?",(key,));return json.loads(row["value"]) if row else default
    def set_meta(self,key,value):
        with self.tx() as c:c.execute("INSERT OR REPLACE INTO meta VALUES (?,?)",(key,dumps(value)))
    @property
    def generation_id(self):return self.meta("active_generation")
    def generation(self,gid=None):
        r=self.one("SELECT * FROM generations WHERE id=?",(gid or self.generation_id,))
        if not r or digest(r["manifest"])!=r["hash"]:raise RuntimeError("Generation-Manifest beschädigt")
        return json.loads(r["manifest"])
    def components(self,manifest=None):
        """Read typed component ownership; adapt old route-only manifests in memory.

        Historical immutable generations are never rewritten during migration.
        """
        m=manifest or self.generation()
        if 'components' in m:return m['components']
        paths=[p for p in m['hashes'] if p.startswith('checkpoints/head-')]
        if len(paths)>1:raise ValueError('Mehrdeutige Legacy-Routing-Artefakte')
        if not paths:return {}
        row=self.one('SELECT id,manifest FROM updates WHERE path=?',(paths[0],))
        detail=json.loads(row['manifest']) if row else {}
        return {'route':{'path':paths[0],'sha256':m['hashes'][paths[0]],'update_id':row['id'] if row else None,
                         'encoder_revision':detail.get('encoder_revision',m['models'].get('C2_CONTROL'))}}
    def _generation(self,c,parent,hashes,config,rule,models,updates,components=None,last_update=None):
        if components is None:
            prior=self.generation(parent) if parent else None
            components=self.components(prior) if prior and prior['hashes']==hashes else {}
            if prior:last_update=prior.get('last_weight_update_id',prior['created_by_update_ids'][-1] if prior['created_by_update_ids'] else None)
        gid=uid("gen");m=packet("BrainGenerationManifest","F7_RUNTIME","GENERATION",gid,parent_generation_id=parent,rule_version=rule,hashes=hashes,config=config,models=models,
            created_by_update_ids=updates,components=components,last_weight_update_id=last_update,memory_schema_version=1,memory_semantics="append-only; weight rollback does not erase experience",age_state_version=0,callosum_bridge_revision=None,world_self_revision=None,skill_revision=None)
        data=dumps(m);c.execute("INSERT INTO generations VALUES (?,?,?,?,?)",(gid,parent,data,digest(data),now()));c.execute("INSERT OR REPLACE INTO meta VALUES ('active_generation',?)",(dumps(gid),));return gid
    def ensure_generation_snapshot(self,cfg,models):
        """Fill the boot generation's immutable runtime snapshot exactly once.

        Fresh stores are created before Runtime has loaded config/model manifests, so the
        bootstrap generation starts with empty config/models.  Before accepting work,
        promote that placeholder to a child generation containing the effective config
        and installed role revisions.  Existing non-empty generations are never rewritten.
        """
        base=self.generation()
        if base.get("config") or base.get("models"):
            return base["brain_generation_id"]
        cfg=dict(cfg);models=dict(models)
        with self.tx() as c:
            active=json.loads(c.execute("SELECT value FROM meta WHERE key='active_generation'").fetchone()[0])
            if active!=base["brain_generation_id"]:
                return active
            return self._generation(c,active,base["hashes"],cfg,base["rule_version"],models,base["created_by_update_ids"])

    def validate_artifacts(self,m):
        for rel,h in m["hashes"].items():
            p=(self.home/rel).resolve()
            if not p.is_relative_to(self.home.resolve()) or not p.is_file() or file_hash(p)!=h:raise RuntimeError("Ungültiges Generation-Artefakt: "+rel)
        owners=set()
        for component,entry in m.get('components',{}).items():
            if component not in COMPONENT_ENCODERS or m['hashes'].get(entry['path'])!=entry['sha256'] or entry['path'] in owners:raise ValueError('Komponenten-Manifest inkonsistent')
            owners.add(entry['path'])
    def switch_generation(self,update_id,cfg,models):
        r=self.one("SELECT * FROM updates WHERE id=?",(update_id,));base=self.generation()
        if not r or r["status"]!="PENDING_APPROVAL":raise ValueError("Update nicht freigabefähig")
        if r["base_generation"]!=base["brain_generation_id"]:raise ValueError("Update veraltet")
        m=json.loads(r["manifest"])
        if not m.get("commit_eligible"):raise ValueError("Train/Retention-Gate nicht erfüllt")
        from .guards import stability_envelope
        envelope=stability_envelope(m,cfg)
        if envelope:raise ValueError("Stabilitätshülle verletzt: "+", ".join(envelope))
        component=m.get('component','route')
        if component not in COMPONENT_ENCODERS:raise ValueError('Unbekannte Update-Komponente')
        encoder_role=COMPONENT_ENCODERS[component]
        if m.get('encoder_revision') and m['encoder_revision']!=models.get(encoder_role):raise ValueError('Encoder gewechselt: erneute Validierung nötig')
        prefix='checkpoints/head-' if component=='route' else 'checkpoints/'+component+'-'
        if not r['path'] or not r['path'].startswith(prefix) or '/' in r['path'][len(prefix):]:raise ValueError('Artefakt passt nicht zur Komponente')
        for role,revision in m.get('dependency_revisions',{}).items():
            if models.get(role)!=revision:raise ValueError('Abhängiges Modell geändert: '+role)
        if component=='output_adapter' and m.get('objective')=='c3-live-prefill-first-token-delta-v1':
            if cfg.get('learning_mode')!='APPROVED_COMMIT':raise ValueError('SAME-CAUSAL individual approval requires APPROVED_COMMIT')
            from .causal_output import validate_update
            validate_update(self,r,models)
            parent=self.components(base).get('output_adapter')
            if m.get('parent_output_update_id')!=(parent['update_id'] if parent else None):raise ValueError('SAME-CAUSAL retention parent changed')
        components=dict(self.components(base));hashes=dict(base['hashes']);old=components.get(component)
        if old:hashes.pop(old['path'])
        if r['path'] in hashes:raise ValueError('Artefakt gehört bereits anderer Komponente')
        hashes[r['path']]=r['hash']
        components[component]={'path':r['path'],'sha256':r['hash'],'update_id':update_id,'encoder_role':encoder_role,'encoder_revision':m.get('encoder_revision'),
                               'dependency_revisions':m.get('dependency_revisions',{}),'context_revision':m.get('context_revision')}
        self.validate_artifacts({'hashes':hashes,'components':components})
        source_ids=m.get('source_ids',[])
        if not isinstance(source_ids,list) or any(type(sid) is not str or not sid for sid in source_ids):
            raise ValueError('Update-Source-Lineage ungültig')
        with self.tx() as c:
            # Preflight is deliberately outside the write transaction. Another
            # Store thread can change the update before BEGIN IMMEDIATE; the
            # approval must therefore bind the *same* candidate row, not just
            # the active generation and the previously observed source IDs.
            live=c.execute(
                "SELECT status,base_generation,path,hash,manifest FROM updates WHERE id=?",
                (update_id,)).fetchone()
            if not live or live['status']!='PENDING_APPROVAL':
                raise ValueError('Update nicht mehr freigabefähig')
            if any(live[key]!=r[key] for key in ('base_generation','path','hash','manifest')):
                raise ValueError('Update nach Vorprüfung geändert; erneut prüfen')
            # Source revocation and generation commit share one write transaction.
            # A source forgotten while an optimizer was running must not be
            # resurrected by a later approval, even if its update was not yet
            # included in the forget path's candidate quarantine.
            for sid in source_ids:
                source=c.execute('SELECT deleted,hash FROM sources WHERE id=?',(sid,)).fetchone()
                if not source or source['deleted']:
                    raise ValueError('Update-Source-Lineage gelöscht/fehlt: '+sid)
                try:
                    source_bytes=self.blob_bytes(source['hash'])
                except (FileNotFoundError,ValueError) as exc:
                    raise ValueError('Update-Source-Lineage-Blob fehlt/beschädigt: '+sid) from exc
                if digest(source_bytes)!=source['hash']:
                    raise ValueError('Update-Source-Lineage-Hash falsch: '+sid)
            active=json.loads(c.execute("SELECT value FROM meta WHERE key='active_generation'").fetchone()[0])
            if active!=r["base_generation"]:raise ValueError("Generation konkurrierend geändert")
            ids=[entry['update_id'] for entry in components.values() if entry.get('update_id')]
            gid=self._generation(c,active,hashes,cfg,base["rule_version"],models,ids,components,update_id);m.update(approval_actor="OPERATOR_TTY",approval_time=now(),commit_generation_id=gid)
            c.execute("UPDATE updates SET status='COMMITTED',manifest=? WHERE id=?",(dumps(m),update_id))
        self.log("generation_commit",None,{"update_id":update_id,"generation":gid});return gid
    def rollback(self,update_id):
        r=self.one("SELECT * FROM updates WHERE id=?",(update_id,));active=self.generation()
        last=active.get('last_weight_update_id',active['created_by_update_ids'][-1] if active['created_by_update_ids'] else None)
        if not r or r["status"]!="COMMITTED" or update_id!=last:raise ValueError("Nur letztes aktives Update rollbackbar; spätere Änderungen zuerst zurücksetzen")
        parent=self.generation(r["base_generation"]);self.validate_artifacts(parent)
        with self.tx() as c:
            current=json.loads(c.execute("SELECT value FROM meta WHERE key='active_generation'").fetchone()[0])
            if current!=active['brain_generation_id']:raise ValueError('Generation konkurrierend geändert')
            previous=parent.get('last_weight_update_id',parent['created_by_update_ids'][-1] if parent['created_by_update_ids'] else None)
            gid=self._generation(c,active["brain_generation_id"],parent["hashes"],active["config"],active["rule_version"],parent["models"],parent["created_by_update_ids"],self.components(parent),previous)
            c.execute("UPDATE updates SET status='ROLLED_BACK' WHERE id=?",(update_id,))
        self.log("rollback",None,{"update_id":update_id,"generation":gid,"rules_preserved":True});return gid
    def source(self,text,kind="USER"):
        b=text.encode();h=digest(b);sid=uid("src");p=self.home/"data/blobs"/h
        if not p.exists():atomic_write(p,b)
        with self.tx() as c:c.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,0)",(sid,h,kind,len(b),len(text),now()))
        return {"source_id":sid,"sha256":h,"char_start":0,"char_end":len(text),"modality":"text"}
    def blob_bytes(self,h):
        """Blob content; a WP-U4 archived blob (<hash>.z, zlib) is decompressed in memory, the hash check stays with the caller."""
        p=self.home/"data/blobs"/h
        if p.is_file():return p.read_bytes()
        z=p.with_name(h+".z")
        if z.is_file():
            import zlib
            d=zlib.decompressobj()
            try:b=d.decompress(z.read_bytes(),64*1024*1024)
            except zlib.error as exc:raise ValueError("Archiv-Blob beschädigt") from exc
            if d.unconsumed_tail or not d.eof:raise ValueError("Archiv-Blob beschädigt oder zu groß")
            return b
        raise FileNotFoundError(str(p))
    def read_source(self,ref):
        r=self.one("SELECT * FROM sources WHERE id=?",(ref.get("source_id"),))
        if not r or r["deleted"] or r["hash"]!=ref.get("sha256"):raise ValueError("Dangling/gelöschter SourceRef")
        b=self.blob_bytes(r["hash"])
        if digest(b)!=r["hash"]:raise ValueError("Source-Hash falsch")
        txt=b.decode()
        if not 0<=ref["char_start"]<=ref["char_end"]<=len(txt):raise ValueError("SourceRef außerhalb Text")
        return txt[ref["char_start"]:ref["char_end"]]
    def new_session(self,title="Neuer Chat"):
        sid=uid("chat")
        with self.tx() as c:c.execute("INSERT INTO sessions VALUES (?,?,?)",(sid,title[:80],now()))
        self.set_meta("last_session",sid);return sid
    def _event_in_tx(self,c,session,text,authority):
        b=text.encode();h=digest(b);ref={'source_id':uid('src'),'sha256':h,'char_start':0,'char_end':len(text),'modality':'text'}
        path=self.home/'data/blobs'/h
        if not path.exists():atomic_write(path,b)
        c.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,0)',(ref['source_id'],h,'USER',len(b),len(text),now()))
        eid=uid('evt');exp=uid('exp');g=json.loads(c.execute("SELECT value FROM meta WHERE key='active_generation'").fetchone()[0])
        p=packet('EventEnvelope','A0_SOURCE',eid,g,[ref],source_ref=ref,authority=authority,kind='USER_TEXT',experience_id=exp)
        c.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?)',(eid,session,ref['source_id'],exp,g,dumps(p),now()))
        c.execute('INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)',(session,eid,'user',text,'FINAL',dumps({'source_ref':ref}),now()))
        c.execute("UPDATE sessions SET title=CASE WHEN title='Neuer Chat' THEN ? ELSE title END WHERE id=?",(text[:80],session))
        return p
    def event(self,session,text,authority='AUTHORITATIVE'):
        if authority!='AUTHORITATIVE':raise ValueError('PROVISIONAL darf nicht persistent/parametrisch wirken')
        with self.tx() as c:return self._event_in_tx(c,session,text,authority)
    def accept_turn(self,session,text,queue_count,queue_bytes,input_bytes,request_key=None):
        """Durably accept exactly once; capacity and event insertion share the commit."""
        b=len(text.encode())
        if not text.strip():raise ValueError('Leere Eingabe')
        if b>input_bytes:raise Limits('Eingabe zu lang: '+str(input_bytes)+' Bytes')
        for name,value in [('queue_count',queue_count),('queue_bytes',queue_bytes),('input_bytes',input_bytes)]:
            if isinstance(value,bool) or not isinstance(value,int) or not 1<=value<=({'queue_count':16,'queue_bytes':262144,'input_bytes':65536}[name]):raise ValueError('Ungültige Warteschlangen-Grenzen')
        if request_key is not None and (not isinstance(request_key,str) or not 1<=len(request_key.encode())<=128):raise ValueError('Ungültiger Eingabe-Schlüssel')
        with self.tx() as c:
            if request_key is not None:
                prior=c.execute('SELECT e.packet,e.session_id FROM accepted_turns q JOIN events e ON e.id=q.event_id WHERE q.request_key=?',(request_key,)).fetchone()
                if prior:
                    event=json.loads(prior['packet'])
                    if prior['session_id']!=session or self.read_source(event['source_ref'])!=text:raise ValueError('Eingabe-Schlüssel bereits anders verwendet')
                    return event
            size=c.execute("SELECT COUNT(*),COALESCE(SUM(bytes),0) FROM accepted_turns WHERE state='PENDING'").fetchone()
            if size[0]>=queue_count or size[1]+b>queue_bytes:raise Limits('Warteschlange voll; Eingabe wurde nicht angenommen')
            event=self._event_in_tx(c,session,text,'AUTHORITATIVE')
            c.execute('INSERT INTO accepted_turns(event_id,request_key,bytes,accepted_at,state) VALUES (?,?,?,?,?)',(event['event_id'],request_key,b,now(),'PENDING'))
            return event
    def pending_turns(self,limit=None):
        if limit is not None and (not isinstance(limit,int) or isinstance(limit,bool) or limit<1):raise ValueError('Ungültiges Queue-Limit')
        rows=self.rows("SELECT q.*,e.packet FROM accepted_turns q JOIN events e ON e.id=q.event_id WHERE q.state='PENDING' ORDER BY q.sequence"+(' LIMIT ?' if limit is not None else ''),(limit,) if limit is not None else ())
        for row in rows:row['event']=json.loads(row.pop('packet'))
        return rows
    def claim_turn(self,event_id):
        with self.tx() as c:
            if self.queue_paused():return False
            # A single coordinator may hold only one accepted user turn at a time.
            if c.execute("SELECT 1 FROM accepted_turns WHERE state='RUNNING' LIMIT 1").fetchone():return False
            first=c.execute("SELECT event_id FROM accepted_turns WHERE state='PENDING' ORDER BY sequence LIMIT 1").fetchone()
            if not first or first[0]!=event_id:return False
            row=c.execute('SELECT s.deleted FROM events e JOIN sources s ON s.id=e.source_id WHERE e.id=?',(event_id,)).fetchone()
            if not row or row[0]:
                c.execute("UPDATE accepted_turns SET state='CANCELLED',finished_at=? WHERE event_id=? AND state='PENDING'",(now(),event_id));return False
            return c.execute("UPDATE accepted_turns SET state='RUNNING',started_at=? WHERE event_id=? AND state='PENDING'",(now(),event_id)).rowcount==1
    def finish_turn(self,event_id,status):
        status='DONE' if status=='FINAL' else status
        if status not in {'DONE','CANCELLED','DEADLINE','ERROR','INTERRUPTED'}:raise ValueError('Ungültiger Queue-Abschluss')
        with self.tx() as c:return c.execute("UPDATE accepted_turns SET state=?,finished_at=? WHERE event_id=? AND state IN ('RUNNING','PENDING')",(status,now(),event_id)).rowcount==1
    def queue_stats(self):
        with self.mutex:
            row=self.db.execute("SELECT COUNT(*),COALESCE(SUM(bytes),0) FROM accepted_turns WHERE state='PENDING'").fetchone()
            return {'count':row[0],'bytes':row[1],'paused':self.queue_paused()}
    def queue_paused(self):return self.meta('queue_paused',False) is True
    def set_queue_paused(self,paused):
        if not isinstance(paused,bool):raise ValueError('Pause muss bool sein')
        self.set_meta('queue_paused',paused)
    def add_packet(self,kind,p):
        validate(kind,p)
        with self.tx() as c:c.execute("INSERT INTO packets VALUES (?,?,?,?,?,?)",(p["packet_id"],kind,p["event_id"],p["brain_generation_id"],dumps(p),now()))
        return p
    def message(self,session,event,role,text="",status="DRAFT",metadata=None):
        with self.tx() as c:return c.execute("INSERT INTO messages(session_id,event_id,role,text,status,metadata,created) VALUES (?,?,?,?,?,?,?)",(session,event,role,text,status,dumps(metadata or {}),now())).lastrowid
    def append_message(self,mid,delta):
        with self.tx() as c:
            cur=c.execute("UPDATE messages SET text=text||?,status='STREAMING' WHERE id=? AND status IN ('DRAFT','OUTPUT_COMMITTED','STREAMING')",(delta,mid))
            if cur.rowcount!=1:raise ValueError("Finaler Text unveränderlich")
    def finish_message(self,mid,status,metadata):
        if status not in {"FINAL","CANCELLED","DEADLINE","ERROR","INTERRUPTED"}:raise ValueError(status)
        with self.tx() as c:c.execute("UPDATE messages SET status=?,metadata=? WHERE id=? AND status IN ('DRAFT','OUTPUT_COMMITTED','STREAMING')",(status,dumps(metadata),mid))
    def history(self,session,limit=100):return self.rows("SELECT * FROM (SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?) ORDER BY id",(session,limit))
    def state(self,key,default=None):
        r=self.one("SELECT * FROM states WHERE key=?",(key,));return (json.loads(r["payload"]),r["version"]) if r else (default,0)
    def set_state(self,key,payload,expected=None):
        with self.tx() as c:
            r=c.execute("SELECT version FROM states WHERE key=?",(key,)).fetchone();v=r[0] if r else 0
            if expected is not None and expected!=v:raise ValueError("Stale state write")
            c.execute("INSERT OR REPLACE INTO states VALUES (?,?,?)",(key,v+1,dumps(payload)))
        return v+1
    def start_action(self,event,generation,kind="TEXT_REPORT",forecast=None):
        aid=uid("act");intent=packet("ActionIntent","C5_REPORT_BROKER",event,generation,action_id=aid,action_type=kind,permission="local_text_only")
        expected={"stream_owner":"C5_REPORT_BROKER","type":kind}
        if forecast is not None:expected['forecast']=forecast
        copy=packet("CorollaryCopy","F3_SELF",event,generation,action_id=aid,expected=expected,self_caused=True)
        self.add_packet("ActionIntent",intent);self.add_packet("CorollaryCopy",copy)
        with self.tx() as c:c.execute("INSERT INTO actions VALUES (?,?,?,?,?,?,?,?)",(aid,event,kind,"DISPATCHED",copy["packet_id"],dumps(copy["expected"]),None,now()))
        return aid
    def finish_action(self,aid,status,actual):
        r=self.one("SELECT * FROM actions WHERE id=?",(aid,));e=self.one("SELECT generation_id FROM events WHERE id=?",(r["event_id"],))
        self.add_packet("ActionOutcome",packet("ActionOutcome","C6_TEXT",r["event_id"],e["generation_id"],action_id=aid,status=status,actual=actual))
        with self.tx() as c:c.execute("UPDATE actions SET status=?,outcome=? WHERE id=?",(status,dumps(actual),aid))
    def prune_telemetry(self,clock=None):
        cutoff=(now() if clock is None else clock)-self.log_retention_days*86400
        with self.tx() as c:return c.execute('DELETE FROM telemetry WHERE created<?',(cutoff,)).rowcount
    def log(self,kind,event,metrics):
        with self.tx() as c:
            c.execute("INSERT INTO telemetry(kind,event_id,metrics,created) VALUES (?,?,?,?)",(kind,event,dumps(telemetry_metrics(metrics)),now()))
            if c.execute("SELECT last_insert_rowid()").fetchone()[0]%200==0:
                c.execute("DELETE FROM telemetry WHERE id<(SELECT MAX(id)-10000 FROM telemetry)")
                c.execute('DELETE FROM telemetry WHERE created<?',(now()-self.log_retention_days*86400,))
    def rules(self):
        # Return the current version atomically; raw access remains available so
        # the operator can remove an invalid/revoked fixed rule by explicit diff.
        with self.mutex:
            return json.loads(self.one("SELECT rules FROM rules WHERE id=?",(self.generation()["rule_version"],))["rules"])
    def request(self,kind,payload):
        rid=uid("req")
        with self.tx() as c:c.execute("INSERT INTO requests VALUES (?,?,?,?,?)",(rid,kind,dumps(payload),"PENDING",now()))
        return rid
    def approve_rule(self,rid,cfg,models):
        from .output_policy import validate_rules,preview,InvalidRule
        with self.tx() as c:
            r=c.execute("SELECT * FROM requests WHERE id=? AND kind='RULES' AND status='PENDING'",(rid,)).fetchone()
            if not r:raise ValueError("Keine offene Regeländerung")
            p=json.loads(r["payload"]);base=self.generation()
            if not isinstance(p,dict) or p.get("base_rule")!=base["rule_version"]:raise ValueError("Regel-Diff veraltet")
            if 'before' in p and p['before']!=self.rules():raise InvalidRule('Regel-Diff passt nicht zum aktiven Stand')
            validate_rules(self,p.get('after'))
            actual_preview=preview(self,p['after'])
            if actual_preview and p.get('fixed_preview')!=actual_preview:raise InvalidRule('Feste Antworten benötigen einen unveränderten lesbaren Diff')
            new=uid("rule");c.execute("INSERT INTO rules VALUES (?,?,?,?)",(new,base["rule_version"],dumps(p["after"]),now()))
            gid=self._generation(c,base["brain_generation_id"],base["hashes"],cfg,new,models,base["created_by_update_ids"])
            c.execute("UPDATE requests SET status='APPROVED' WHERE id=?",(rid,))
        self.log("rule_approved",None,{"request":rid,"generation":gid});return gid
    def schema_audit(self):
        with self.mutex:
            report=audit_schema(self.db);report['migrations']=audit_migration_journal(self.db);return report
    def integrity(self,full=False):
        errors=[]
        try:self.schema_audit()
        except (RuntimeError,sqlite3.Error) as exc:errors.append(str(exc))
        with self.mutex:
            check=self.db.execute("PRAGMA integrity_check").fetchone()[0]
            if check!="ok":errors.append(check)
            errors += [str(tuple(r)) for r in self.db.execute("PRAGMA foreign_key_check")]
        try:self.validate_artifacts(self.generation())
        except Exception as e:errors.append(str(e))
        try:
            from .output_policy import validate_rules
            validate_rules(self,self.rules())
        except (ValueError,OSError) as e:errors.append('Aktive Output-Regel ungültig: '+str(e))
        for r in self.rows("SELECT * FROM sources WHERE deleted=0 ORDER BY created DESC"+("" if full else " LIMIT 30")):
            try:ok=digest(self.blob_bytes(r["hash"]))==r["hash"]
            except (OSError,ValueError):ok=False
            if not ok:errors.append("Source beschädigt: "+r["id"])
        for row in self.rows("SELECT payload FROM packets WHERE kind='LatentTapPacket' ORDER BY created DESC"+("" if full else " LIMIT 30")):
            p=json.loads(row['payload']);path=(self.home/p['feature_path']).resolve()
            try:
                self.read_source(p['source_ref'])
                if not path.is_relative_to((self.home/'data/blobs').resolve()) or file_hash(path)!=p['feature_sha256']:raise ValueError('Tap hash')
            except (ValueError,OSError):errors.append('Tap-Artefakt beschädigt: '+p['packet_id'])
        for row in self.rows("SELECT payload FROM packets WHERE kind='PerceptPacket' ORDER BY created DESC"+("" if full else " LIMIT 30")):
            p=json.loads(row['payload'])
            for key,hash_key in (('student_feature_path','student_feature_sha256'),('feature_path','feature_sha256')):
                if key not in p:continue
                try:
                    self.read_source(p['source_ref']);path=(self.home/p[key]).resolve()
                    if not path.is_relative_to((self.home/'data/blobs').resolve()) or file_hash(path)!=p[hash_key]:raise ValueError('Percept feature hash')
                except (ValueError,OSError,KeyError):errors.append('Percept-Artefakt beschädigt: '+p['packet_id'])
        return errors
    def release_lock(self):
        if self.lock:fcntl.flock(self.lock,fcntl.LOCK_UN);self.lock.close();self.lock=None
    def close(self,release_lock=True):
        try:
            with self.mutex:
                if not self.closed:
                    # wal_checkpoint reports busy as a result row, not an exception.
                    try:
                        self.last_checkpoint=tuple(self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone())
                        if self.last_checkpoint and self.last_checkpoint[0]==1:
                            # WP-V8: busy result (another reader/writer). One short retry, then report it.
                            time.sleep(.05);self.last_checkpoint=tuple(self.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone())
                        self.checkpoint_busy=bool(self.last_checkpoint and self.last_checkpoint[0]==1)
                    finally:self.db.close();self.closed=True
        finally:
            if release_lock:self.release_lock()
