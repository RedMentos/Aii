"""WP-V2/V3 cheap guards restored from blueprint v4/v5 (2026-10-09).

v4 §63 collapse watch, v4 §24 / v5 §28 data-mix quotas with the 2 % retention
rollback, the stability envelope checked before `:approve`, and the v4 §64-65
decoder start values for C3 free text.

All thresholds are BOOT values (v4 start values or engineering choices), not
measurements. Every metric here is lexical: it detects echo/repetition/collapse
symptoms, it never judges semantic correctness.
"""
import json
import re

WORD=re.compile(r"\w+",re.UNICODE)
ABSTAIN=re.compile(r"(?i)\b(weiß (ich )?nicht|nichts belegtes|keine (belegte|gesicherte)n? (angabe|information|quelle)|kann ich nicht (sagen|beantworten)|unbekannt|i don'?t know|nothing verified|no (verified|reliable) (source|information))\b")

# v4 §65 start values. no_repeat_ngram 4 maps to llama-server's DRY sampler
# (penalise repeats longer than 3 tokens); llama-server has no hard n-gram ban.
C3_DECODER={'temperature':.6,'top_p':.95,'top_k':20,'min_p':.05,'repeat_penalty':1.08,'repeat_last_n':64,
            'dry_multiplier':.8,'dry_base':1.75,'dry_allowed_length':3,'dry_penalty_last_n':256}  # b10964 rejects -1 (whole context)
LEGACY_DECODER={'top_k':50,'repeat_penalty':1.05}
# The v4 citation/abstention rule for the C3 answer (WP-V3) lives in prompts.py ('answer_rules').
MIN_NEW_TOKENS=8  # v4 §64; checked on the finished turn, server has no min-token knob

# BOOT collapse thresholds over a rolling window of own answers.
COLLAPSE={'window':20,'min_turns':3,'repetition_rate':.35,'type_token_ratio':.30,'query_echo':.60,
          'self_citation':.50,'abstention_rate':.50}
# v4 §24: ≥60 % human, ≤10 % self-generated, dream ≤5 % (counted inside self), seed 0 %.
DATA_MIX={'human_min':.60,'self_max':.10,'dream_max':.05,'seed_max':0.}
ORIGINS=('human','human_replay','self','dream','seed')
RETENTION_MAX_DROP=.02


def words(text):return [w.lower() for w in WORD.findall(text or '')]

def ngrams(tokens,n):return [tuple(tokens[i:i+n]) for i in range(max(0,len(tokens)-n+1))]

def _overlap(a,b,n=3):
    """Share of a's n-grams that also occur in b (0 when a is too short)."""
    grams=ngrams(a,n)
    if not grams:return 0.
    other=set(ngrams(b,n));return sum(g in other for g in grams)/len(grams)

def turn_metrics(output,query='',previous_outputs=()):
    w=words(output);q=words(query);grams=ngrams(w,4)
    prev=[x for p in previous_outputs for x in words(p)]
    return {'tokens':len(w),
            'repetition_rate':(1-len(set(grams))/len(grams)) if grams else 0.,
            'type_token_ratio':(len(set(w))/len(w)) if w else 0.,
            'query_echo':_overlap(w,q),
            'self_citation':_overlap(w,prev) if prev else 0.,
            'abstention':bool(ABSTAIN.search(output or '')),
            'below_min_new':len(w)<MIN_NEW_TOKENS}

def _js_distance(a,b):
    """Jensen-Shannon distance between two unigram distributions (0..1)."""
    import math
    ca={};cb={}
    for x in a:ca[x]=ca.get(x,0)+1
    for x in b:cb[x]=cb.get(x,0)+1
    if not ca or not cb:return 0.
    na=sum(ca.values());nb=sum(cb.values());js=0.
    for k in set(ca)|set(cb):
        p=ca.get(k,0)/na;q=cb.get(k,0)/nb;m=(p+q)/2
        if p:js+=p/2*math.log2(p/m)
        if q:js+=q/2*math.log2(q/m)
    return math.sqrt(max(0.,js))

def collapse_report(pairs,limits=None):
    """pairs: chronological [(user_text, answer_text)] of own model answers."""
    lim=COLLAPSE|(limits or {});pairs=list(pairs)[-lim['window']:]
    rows=[];seen=[]
    for query,answer in pairs:
        rows.append(turn_metrics(answer,query,seen[-4:]));seen.append(answer)
    report={'kind':'COLLAPSE_GUARD','turns':len(rows),'thresholds':lim,'status':'INSUFFICIENT_TURNS','alarms':[],'boot_values':True}
    if not rows:return report
    mean=lambda k:sum(float(r[k]) for r in rows)/len(rows)
    half=len(pairs)//2
    drift=_js_distance([x for _,a in pairs[:half] for x in words(a)],[x for _,a in pairs[half:] for x in words(a)]) if half else 0.
    m={'repetition_rate':mean('repetition_rate'),'type_token_ratio':mean('type_token_ratio'),'query_echo':mean('query_echo'),
       'self_citation':mean('self_citation'),'abstention_rate':mean('abstention'),'below_min_new_rate':mean('below_min_new'),'drift':drift}
    report['metrics']=m
    if len(rows)<lim['min_turns']:return report
    # Drift is reported only: topic changes move unigram distributions too, so it
    # needs a measured per-user baseline before it may raise an alarm.
    for key in ('repetition_rate','query_echo','self_citation','abstention_rate'):
        if m[key]>lim[key]:report['alarms'].append(key)
    if m['type_token_ratio']<lim['type_token_ratio']:report['alarms'].append('type_token_ratio')
    report['status']='COLLAPSE_SUSPECTED' if report['alarms'] else 'OK'
    return report

def store_pairs(store,session=None,limit=COLLAPSE['window']):
    """Recent (user, assistant) pairs whose answer was model-generated."""
    where='AND a.session_id=?' if session else '';args=((session,) if session else ())+(limit,)
    rows=store.rows("SELECT u.text AS q,a.text AS a,a.metadata AS m FROM messages a JOIN messages u ON u.event_id=a.event_id AND u.role='user' "
                    "WHERE a.role='assistant' AND a.status='FINAL' "+where+" ORDER BY a.id DESC LIMIT ?",args)
    out=[]
    for r in reversed(rows):
        try:meta=json.loads(r['m'] or '{}')
        except ValueError:meta={}
        if meta.get('model_generated'):out.append((r['q'],r['a']))
    return out

def data_mix_check(counts,quotas=None):
    """counts: {origin: n} with origin in ORIGINS. Returns pass + violations (v4 §24)."""
    q=DATA_MIX|(quotas or {})
    if any(k not in ORIGINS or isinstance(v,bool) or not isinstance(v,int) or v<0 for k,v in counts.items()):raise ValueError('data_mix: Herkunft/Anzahl ungültig')
    total=sum(counts.values())
    if not total:return {'pass':False,'violations':['EMPTY_DATASET'],'shares':{}}
    share={k:counts.get(k,0)/total for k in ORIGINS}
    human=share['human']+share['human_replay'];own=share['self']+share['dream']
    v=[]
    if human<q['human_min']:v.append('HUMAN_SHARE_BELOW_MIN')
    if own>q['self_max']:v.append('SELF_GENERATED_ABOVE_MAX')
    if share['dream']>q['dream_max']:v.append('DREAM_ABOVE_MAX')
    if share['seed']>q['seed_max']:v.append('SEED_NOT_ALLOWED')
    return {'pass':not v,'violations':v,'shares':share|{'human_total':human,'self_total':own}}

SELF_KINDS=('rated_answer','sdft','ttt','own_final_answer')
def item_origin(item):
    """Origin class of one training item (ORIGINS). An explicit `origin` wins; model-written targets count as `self`
    even when a human rated them (the target text is still the model's), dream/hypothesis sources as `dream`."""
    o=item.get('origin')
    if o in ORIGINS:return o
    src=str((item.get('source_ref') or {}).get('label') or item.get('source_kind') or '').upper()
    if 'DREAM' in src or 'HYPOTHESIS' in src:return 'dream'
    if item.get('kind') in SELF_KINDS or item.get('label_source')=='own_final_answer':return 'self'
    if 'SEED' in src:return 'seed'
    return 'human'

def mix_for_training(items,quotas=None):
    """Applied before every weight-training job (ablation §99: the gate alone learns dream/self labels).
    Returns (kept items, report with counts before/after, dropped count and the data_mix_check verdict)."""
    items=list(items);kept=[x for x in enforce_data_mix(items,item_origin,quotas) if item_origin(x)!='seed']
    count=lambda xs:{o:sum(1 for x in xs if item_origin(x)==o) for o in ORIGINS}
    before,after=count(items),count(kept)
    return kept,{'before':before,'after':after,'dropped':len(items)-len(kept),
                 'check':data_mix_check(after,quotas) if kept else {'pass':False,'violations':['EMPTY_DATASET'],'shares':{}},'quotas':DATA_MIX|(quotas or {})}

def enforce_data_mix(items,origin_of,quotas=None):
    """Drop own/dream/seed items until the quotas hold; human items are never dropped."""
    q=DATA_MIX|(quotas or {});items=list(items)
    human=[x for x in items if origin_of(x) in ('human','human_replay')]
    rest={o:[x for x in items if origin_of(x)==o] for o in ('self','dream')}
    n=len(human)
    # Largest own share that keeps human ≥ human_min and own ≤ self_max.
    own_cap=int(n*min(q['self_max']/(1-q['self_max']),(1-q['human_min'])/q['human_min'])) if n else 0
    dream_cap=min(len(rest['dream']),int((n+own_cap)*q['dream_max']))
    dream=rest['dream'][:min(dream_cap,own_cap)]
    own=rest['self'][:max(0,own_cap-len(dream))]
    keep=set(map(id,human+own+dream))
    return [x for x in items if id(x) in keep]

def retention_rollback(before,after,max_drop=RETENTION_MAX_DROP):
    """v4 §24: a drop of more than 2 % on old human sets forces rollback."""
    if before is None or after is None:return {'rollback':False,'reason':'NO_OLD_SET_SCORE'}
    drop=(before-after)/before if before>0 else 0.
    return {'rollback':drop>max_drop,'drop':drop,'max_drop':max_drop,'reason':'OLD_SET_REGRESSION' if drop>max_drop else 'WITHIN_ENVELOPE'}

def stability_envelope(manifest,cfg):
    """Release criteria checked before `:approve`; only fields the manifest declares are checked."""
    v=[]
    norm=manifest.get('max_applied_step_norm')
    cap=manifest.get('effective_max_update_norm') or (manifest.get('training_policy') or {}).get('effective_max_update_norm') or cfg.get('max_update_norm',.02)
    if isinstance(norm,(int,float)) and isinstance(cap,(int,float)) and norm>cap*1.000001:v.append('UPDATE_NORM_ABOVE_CAP')
    for key,cap in (('route_shift',.25),('calibration_shift',.10)):
        x=manifest.get(key)
        if isinstance(x,(int,float)) and x>cap:v.append(key.upper()+'_ABOVE_CAP')
    mix=manifest.get('data_mix')
    if isinstance(mix,dict):
        try:
            check=data_mix_check(mix)
            if not check['pass']:v.extend(check['violations'])
        except ValueError:v.append('DATA_MIX_INVALID')
    old=manifest.get('old_set_score')
    if isinstance(old,dict) and retention_rollback(old.get('before'),old.get('after'))['rollback']:v.append('OLD_SET_REGRESSION_ABOVE_2_PERCENT')
    from .drift import gate as drift_gate
    v.extend(drift_gate(manifest,cfg))  # WP-S5 frozen-probe drift (RL's Razor)
    return v
