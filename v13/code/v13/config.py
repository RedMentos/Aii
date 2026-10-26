import json
import os
from pathlib import Path
from .common import atomic_write,dumps

# BOOT engineering values. All are estimates/choices, not Redmi measurements.
KNOBS={
 "context_tokens":(2048,"COUNT",512,8192,"Native context per role"),
 "answer_tokens":(256,"COUNT",16,1024,"Answer token budget"),
 "observer_tokens":(160,"COUNT",32,256,"Structured offer budget"),
 "b2_state_slots":(4,"COUNT",0,8,"BOOT retained source-bound B2 offers; 0 disables cross-turn context"),
 "b2_context_chars":(768,"COUNT",0,4096,"BOOT total serialized earlier B2 context character cap"),
 "threads":(4,"COUNT",1,8,"Native CPU threads"),
 "deadline_seconds":(90,"DURATION_S",5,600,"Absolute user deadline"),
 "observer_seconds":(35,"DURATION_S",2,180,"Observer budget per role"),
 "control_seconds":(4.,"DURATION_S",.2,30,"Needle control budget"),
 "temperature":(.1,"TEMPERATURE",0.,1.,"Text sampling"),
 "history_turns":(8,"COUNT",0,32,"Recent pairs, then exact token trimming"),
 "memory_top_k":(3,"COUNT",0,8,"Maximum retrieved corrections"),
 "memory_threshold":(.25,"THRESHOLD",0.,1.,"Lexical match threshold"),
 "focal_slots":(4,"COUNT",1,8,"Bounded coalition items"),
 "body_residency_mb":(1800,"BYTES_MB",0,8192,"WP-N11/AG13 RAM budget for resident bodies (B1/B2/C3 at once); 0 = one process at a time. BOOT, not a Redmi measurement"),
 "max_reentry":(2,"COUNT",0,3,"Re-entry ceiling per turn (WP-T1: goal-directed, stops on a stable trajectory)"),
 "queue_count":(4,"COUNT",1,16,"Waiting user turns"),
 "queue_bytes":(64000,"BYTES",1024,262144,"Total queued input"),
 "input_bytes":(16000,"BYTES",512,65536,"Single input cap"),
 "queue_ttl_seconds":(600,"DURATION_S",10,3600,"Queue expiry"),
 "thermal_limit_c":(45.,"THRESHOLD",35.,60.,"BOOT battery temperature limit"),
 "minimum_free_mb":(500,"BYTES_MB",100,4000,"BOOT MemAvailable floor"),
 "learning_rate":(.01,"LEARNING_RATE",.00001,.1,"External route-head SGD"),
 "predictor_lr":(.002,"LEARNING_RATE",.000001,.05,"Local predictive head SGD"),
 "eligibility_decay":(.95,"DECAY",0.,.9999,"Local activity trace EMA"),
 "ema_decay":(.99,"DECAY",.5,.99999,"Slow target projector"),
 "max_update_norm":(.02,"THRESHOLD",.00001,.2,"L2 optimizer-step cap"),
 "retention_max_delta":(.02,"THRESHOLD",0.,.1,"Held-out per-class regression cap"),
 "replay_batch":(4,"COUNT",1,16,"BOOT maximum experiences in one explicit replay job"),
 "replay_tokens":(96,"COUNT",16,256,"BOOT native replay output token cap"),
 "learning_steps":(80,"COUNT",1,1000,"Shadow step budget")}
KNOBS['readout_steps']=(480,"COUNT",1,1000,"BOOT bounded JEF wake/halt fit; route budget unchanged")
KNOBS['predictor_steps']=(240,"COUNT",1,1000,"BOOT small projector/predictor shadow optimizer steps")
KNOBS['student_steps']=(640,"COUNT",1,2000,"BOOT text A3 alignment/reconstruction optimizer steps")
KNOBS['student_lr']=(.02,"LEARNING_RATE",.000001,.1,"BOOT A3 projector/reconstruction SGD")
KNOBS['calibration_steps']=(1600,"COUNT",1,4000,"BOOT tiny external native-confidence fit; route/readout budgets unchanged")
KNOBS['calibration_lr']=(.05,"LEARNING_RATE",.000001,.1,"BOOT six-parameter native route calibration SGD")
KNOBS['calibration_sources']=(256,"COUNT",32,512,"BOOT maximum distinct explicitly labelled native calibration sources")
KNOBS['calibration_observation_seconds']=(30.,"DURATION_S",.2,30.,"BOOT shadow-only native calibration observation cap within 600 s job; real-time control budget unchanged")
KNOBS['retrieval_steps']=(1600,"COUNT",1,4000,"BOOT external memory cue optimizer steps")
KNOBS['retrieval_lr']=(.05,"LEARNING_RATE",.000001,.1,"BOOT memory cue SGD")
KNOBS['retrieval_seconds']=(8.,"DURATION_S",.2,30,"BOOT total semantic recall budget within user deadline")
KNOBS['retrieval_candidates']=(32,"COUNT",1,64,"BOOT semantic candidate cap; lexical retrieval remains available")
KNOBS['memory_embed_dim']=(256,"COUNT",128,768,"WP-H Matryoshka dimensions of the semantic memory key (EmbeddingGemma 768)")
KNOBS['memory_embed_threshold']=(.84,"THRESHOLD",0.,1.,"WP-H cosine floor for semantic memory admission (EN calibration, bench-results/semantic-recall-20261009; not Redmi-measured)")
KNOBS['memory_embed_keep']=(0,"COUNT",0,1,"WP-H 1 keeps the embedding runner loaded between turns (RAM), 0 unloads after recall")
KNOBS['episode_boundary_threshold']=(.30,"THRESHOLD",0.,1.,"WP-N8 noisy-OR boundary score that opens a new episode (A1.boundary_threshold)")
KNOBS['episode_pause_seconds']=(1800,"DURATION_S",60,86400,"WP-N8 pause that always cuts an episode")
KNOBS['episode_max_events']=(24,"COUNT",2,256,"WP-N8 forced boundary after this many turns")
KNOBS['episode_admission_threshold']=(.5,"THRESHOLD",0.,1.,"WP-N8 episode becomes a semantic staging candidate (§9.5)")
KNOBS['memory_half_life_days']=(30,"DURATION_DAYS",1,365,"WP-N8 memory strength half-life without recall")
KNOBS['memory_forget_floor']=(.05,"THRESHOLD",0.,1.,"WP-N8 strength below which a memory is proposed for :forget (never deleted automatically)")
KNOBS['log_retention_days']=(14,"DURATION_DAYS",1,365,"BOOT diagnostic retention; chat, memory, experience and proofs are excluded")
KNOBS['output_adapter_steps']=(1600,"COUNT",1,4000,"BOOT human-labelled first-native-token delta optimizer steps")
KNOBS['output_adapter_lr']=(.1,"LEARNING_RATE",.000001,.2,"BOOT external C3 output-row SGD")
KNOBS['output_adapter_max_bias']=(12.,"THRESHOLD",.1,12.,"BOOT maximum first-position native logit delta")
KNOBS['output_adapter_support_cosine']=(.95,"THRESHOLD",.9,1.,"BOOT native hidden-state support cosine")
KNOBS['output_adapter_seconds']=(8.,"DURATION_S",.2,30.,"BOOT first-position feature budget within user deadline")
KNOBS['drift_kl_max']=(.05,"THRESHOLD",0.,1.,"WP-S5 max mean KL(base || candidate) on the frozen probe set before :approve (RL's Razor); same BOOT value as AG6 DRIFT_MAX")
KNOBS['drift_flip_max']=(.10,"THRESHOLD",0.,1.,"WP-S5 max share of frozen protected decisions a candidate head may flip before :approve")
KNOBS['drift_required']=(0,"COUNT",0,1,"WP-S5 1 = updates without a drift measurement are refused at :approve; 0 = checked when measured")
KNOBS['control_budget_p95_ms']=(0.,"THRESHOLD",0.,60000.,"WP-T14 §22.2.3 cap on P95 control-fabric latency per turn in ms; 0 = unset (limits only after Redmi measurement)")
KNOBS['control_budget_state_mb']=(0.,"THRESHOLD",0.,4096.,"WP-T14 §22.2.3 cap on persistent control state (states table) in MB; 0 = unset")
KNOBS['native_cache_ram_mb']=(128,"BYTES_MB",0,8192,"G6B BOOT llama-server --cache-ram per runner (b10964 default 8192); 0 disables the host prompt cache. With native_ctx_checkpoints 6 the worst case stays <=256 MiB per body (cloud measurement, Redmi open)")
KNOBS['native_ctx_checkpoints']=(6,"COUNT",0,32,"G6B BOOT llama-server --ctx-checkpoints per slot (b10964 default 32; Qwen3.5 B2 ~19 MiB each, LFM2.5 <0.2 MiB)")
KNOBS['observer_sample_rate']=(.5,"BUDGET_FRACTION",0.,1.,"§22.2.4 BOOT share of events that get pre-answer observer passes under observer_schedule SAMPLED_OBSERVER (deterministic per event)")
KNOBS['control_budget_params_mb']=(0.,"THRESHOLD",0.,4096.,"WP-T14 §22.2.3 cap on approved learned control checkpoints in MB; 0 = unset")
DEFAULTS={k:v[0] for k,v in KNOBS.items()}|{"schema_version":1,"learning_mode":"RECORD_ONLY","system_stage":0,"user_stage_cap":0,
 "memory_embedding":"auto","duplex_mode":"auto","c3_decode_mode":"server","c3_sampling":"anti_echo","answer_language":"en","b2_control":"two_body","observer_mode":"background","observer_schedule":"A_THEN_B_SEQUENTIAL","route_override":"auto","channel":"SOURCE_EXACT","teacher_enabled":False,"latents_enabled":False,"seed":13,"age_plasticity_policy":"boot","segment_mode":"percept","tool_conflict_policy":"correct",
 # 2026-10-21 user decision (thread "Zitierhilfe an, Regeln ohne Halluzination"): quote help ON. Bodies point at exact source
 # sentences instead of copying them (measured WP-Z2/Z2b/Z2d settings: B2 rule quote .17 -> .97, 0 wrong); the standing
 # rule questions are asked only on rule-decision turns; deciding stays with the fixed recipe, never a language model.
 "offer_quote_context_chars":200,"b2_quote_select":"pointer","b2_offer_body_state":False,"offer_quote_min_chars":90,"b1_recent_source_chars":600,
 "body_question_scope":"rule_decision","eligibility_reader":"fixed",
 # WP-UR8: caution-only second opinion on user rules (v13/userrules_second.py); value set by the preregistered switch rule.
 "user_rules_second_opinion":"off",
 "body_question_b1":"Which option figures apply here: cost, duration and locality of Option A and Option B? Quote the exact source sentences that state them, or say they are not in the source.",
 "body_question_b2":"Which earlier project rules apply here: budget, deadline and local-only requirement? Quote the exact earlier source sentence that states them, or say they are not in the source."}
# Values before the 2026-10-21 quote-help decision. Frozen measurement harnesses and their regression tests pin these, so a
# re-run measures exactly what was preregistered (live and new benches use DEFAULTS).
LEGACY_QUOTE_PATH={"offer_quote_context_chars":0,"b2_quote_select":"off","b2_offer_body_state":True,"offer_quote_min_chars":0,"b1_recent_source_chars":0,
 "body_question_scope":"always","eligibility_reader":"c3","body_question_b1":"","body_question_b2":""}
# IH-H5 KnobSpec: every knob has a declared kind, so 0..1 is never silently read as a probability.
KNOB_KINDS={'AUTHORITY','MIX_WEIGHT','PRIOR','PROBABILITY','THRESHOLD','BUDGET_FRACTION','BOOLEAN','COUNT','BYTES','BYTES_MB',
            'DURATION_MS','DURATION_S','DURATION_DAYS','RATE_HZ','LEARNING_RATE','DECAY','TEMPERATURE'}
KNOB_UNITS={'BYTES':'B','BYTES_MB':'MB','DURATION_MS':'ms','DURATION_S':'s','DURATION_DAYS':'d','RATE_HZ':'Hz','COUNT':'1','TEMPERATURE':'1'}
def knob_specs(cfg=None):
    cfg=cfg or DEFAULTS
    return [{'id':k,'kind':kind,'value':cfg.get(k,default),'unit':KNOB_UNITS.get(kind,'normalized' if kind!='LEARNING_RATE' else 'log-scale'),
             'min':lo,'max':hi,'owner':'OPERATOR','stage_cap':None,'user_cap':None,'learned_allowed':False,
             'clamp_policy':'REJECT_OUT_OF_RANGE','description':text} for k,(default,kind,lo,hi,text) in KNOBS.items()]
def home_path(value=None):return Path(value or os.environ.get("V13_HOME",Path.home()/"v13")).expanduser().resolve()
def validate(cfg):
    for k,(default,_,lo,hi,_) in KNOBS.items():
        v=cfg[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not lo<=v<=hi:raise ValueError(f"{k}: Bereich {lo}..{hi}")
        if isinstance(default,int) and not isinstance(v,int):raise ValueError(k+" muss ganzzahlig sein")
    if cfg["system_stage"]!=0 or cfg["latents_enabled"]:raise ValueError("Age >0/latente Injection sind nicht freigegeben")
    if cfg["learning_mode"] not in {"RECORD_ONLY","SHADOW_UPDATE","APPROVED_COMMIT"}:raise ValueError("learning_mode")
    if cfg["channel"] not in {"NO_MESSAGE","SOURCE_EXACT","CONTROL","SYMBOLIC"}:raise ValueError("channel")
    if cfg["route_override"] not in {"auto","simple","detail","gist","both"}:raise ValueError("route")
    if cfg.get("c3_decode_mode","server") not in {"server","same_causal_zero","same_causal"}:raise ValueError("c3_decode_mode")
    if cfg.get("c3_decode_mode","server") in {"same_causal_zero","same_causal"} and cfg["answer_tokens"] not in {64,128}:raise ValueError("Same-causal answer_tokens muss64 oder128 sein")
    if cfg.get("c3_sampling","anti_echo") not in {"anti_echo","legacy"}:raise ValueError("c3_sampling anti_echo|legacy")
    if cfg.get("answer_language","en") not in {"en","de"}:raise ValueError("answer_language en|de")
    if cfg.get("memory_embedding","auto") not in {"off","shadow","on","auto"}:raise ValueError("memory_embedding off|shadow|on|auto")
    if cfg.get("duplex_mode","auto") not in {"auto","interrupt","off"}:raise ValueError("duplex_mode auto|interrupt|off")
    if cfg.get("b2_control","two_body") not in {"two_body","shared_body_dual_state","same_model_prompt_only","same_model_same_policy"}:raise ValueError("b2_control")
    if cfg["observer_mode"] not in {"background","off"}:raise ValueError("observer")
    if cfg.get("observer_schedule","A_THEN_B_SEQUENTIAL") not in {"A_THEN_B_SEQUENTIAL","B_THEN_A_SEQUENTIAL","ALWAYS_BOTH_ASYNC","JEF_FIRST_THEN_BOTH","SAMPLED_OBSERVER","ON_DEMAND_REENTRY"}:raise ValueError("observer_schedule")
    if not 0<=cfg["user_stage_cap"]<=5:raise ValueError("stage cap")
    if cfg.get("tool_conflict_policy","correct") not in {"log","correct"}:raise ValueError("tool_conflict_policy log|correct")
    if cfg.get("segment_mode","percept") not in {"fixed","percept","all"}:raise ValueError("segment_mode fixed|percept|all")
    if not isinstance(cfg.get("b2_offer_body_state",True),bool):raise ValueError("b2_offer_body_state true|false")
    if not (isinstance(cfg.get("offer_quote_min_chars",0),int) and 0<=cfg.get("offer_quote_min_chars",0)<=400):raise ValueError("offer_quote_min_chars 0..400")
    if not (isinstance(cfg.get("offer_quote_context_chars",0),int) and not isinstance(cfg.get("offer_quote_context_chars",0),bool) and 0<=cfg.get("offer_quote_context_chars",0)<=400):raise ValueError("offer_quote_context_chars 0..400")
    if not (isinstance(cfg.get("b1_recent_source_chars",0),int) and not isinstance(cfg.get("b1_recent_source_chars",0),bool) and 0<=cfg.get("b1_recent_source_chars",0)<=960):raise ValueError("b1_recent_source_chars 0..960")
    if cfg.get("b2_quote_select","off") not in {"off","anchor","pointer"}:raise ValueError("b2_quote_select off|anchor|pointer")
    for key in ("body_question_b1","body_question_b2"):
        if not (isinstance(cfg.get(key,""),str) and len(cfg.get(key,""))<=400):raise ValueError(key+" text 0..400 chars")
    if cfg.get("body_question_scope","always") not in {"always","rule_decision"}:raise ValueError("body_question_scope always|rule_decision")
    if cfg.get("eligibility_reader","c3") not in {"fixed","c3"}:raise ValueError("eligibility_reader fixed|c3")
    if cfg.get("user_rules_second_opinion","off") not in {"jef","off"}:raise ValueError("user_rules_second_opinion jef|off")
    if cfg.get("age_plasticity_policy","boot") not in {"boot","stable_reopen","noise_aware"}:raise ValueError("age_plasticity_policy boot|stable_reopen|noise_aware")
    return cfg
def initialize(home):
    home.mkdir(parents=True,exist_ok=True,mode=0o700)
    for rel in ["models","bin","config","data/db","data/blobs","checkpoints","shadow","logs","tmp","exports","backups"]:(home/rel).mkdir(parents=True,exist_ok=True,mode=0o700)
    p=home/"config/settings.json"
    if not p.exists():atomic_write(p,dumps(DEFAULTS))
    return validate(DEFAULTS|json.loads(p.read_text()))
def save_config(home,cfg):validate(cfg);atomic_write(home/"config/settings.json",dumps(cfg))
