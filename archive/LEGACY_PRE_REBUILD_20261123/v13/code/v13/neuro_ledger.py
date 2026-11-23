"""§102 Updated Completion Ledger Fields: every ledger row states its neuro claim, the claim's limit and the
§99 ablation that tests it, so "brain-inspired" cannot stay an untestable label.

Curated values live in `specs/neuro-ledger.json`; rows without an entry get the conservative default (no claim).
Live parts are bound at ledger time, never curated:
  train_runner_proof_id  newest TrainRunnerProof packet whose runner_revision matches the row (None if never trained)
  age_window_policy      AGE_CONTROL rows report the live `age_plasticity_policy`
  redmi_longrun_proof    ABSENT unless a sustained proof measured on Android exists; a bounded phone run is
                         reported as BOUNDED_PHONE_ONLY, never as a long run
Rules: a claiming class (functional/developmental/mechanism) needs a claim limit; without an ablation its claim
status is UNTESTED_LABEL and a PASS gate is lowered to PARTIAL. Evidence paths are checked but a missing file only
marks the row (the phone package ships without bench-results).
"""
import json
from .common import APP,file_hash
from .contracts import FIELDS

SPEC=APP/'specs/neuro-ledger.json'
FIELD_NAMES=('neuro_inspiration_class','neuro_claim_limit','ablation_baseline','train_runner_proof_id','modulator_schema',
             'eligibility_owner','corollary_required','replay_authority','age_window_policy','redmi_longrun_proof')
STATUS={'SUPPORTED':'TESTED_SUPPORTED','SUPPORTED_SYNTHETIC':'TESTED_SUPPORTED_SYNTHETIC','PARTIAL':'TESTED_PARTIAL',
        'NOT_SUPPORTED':'TESTED_NOT_SUPPORTED','FAIL':'TESTED_FAIL'}

def spec():
    value=json.loads(SPEC.read_text(encoding='utf-8'))
    if tuple(value['fields'])!=FIELD_NAMES:raise ValueError('§102 field list drift')
    for fid,row in value['rows'].items():validate_entry(value,fid,dict(value['default'],**row))
    return value

def validate_entry(sp,fid,e):
    cls=e['neuro_inspiration_class']
    if cls not in sp['classes']:raise ValueError(f'{fid}: unknown neuro_inspiration_class {cls}')
    if cls in sp['claiming_classes'] and not str(e.get('neuro_claim_limit') or '').strip():raise ValueError(f'{fid}: claim without neuro_claim_limit')
    ab=e.get('ablation_baseline')
    if ab is not None:
        if not (ab.get('hypothesis') and ab.get('controls') and ab.get('evidence')):raise ValueError(f'{fid}: ablation needs hypothesis, controls and evidence')
        if ab.get('verdict') not in sp['verdicts']:raise ValueError(f'{fid}: unknown ablation verdict')
    if e.get('modulator_schema') is not None and e['modulator_schema'] not in FIELDS:raise ValueError(f'{fid}: modulator_schema is not a registered schema')
    if e.get('eligibility_owner') is not None and not (APP/e['eligibility_owner']).is_file():raise ValueError(f'{fid}: eligibility_owner missing')
    if not isinstance(e.get('corollary_required'),bool):raise ValueError(f'{fid}: corollary_required must be bool')
    if e['corollary_required'] and not {'CorollaryCopy','SelfCorollary'}<=set(FIELDS):raise ValueError(f'{fid}: corollary schema missing')
    if e.get('replay_authority') not in sp['replay_authorities']:raise ValueError(f'{fid}: unknown replay_authority')
    if e.get('age_window_policy') not in sp['age_window_policies']:raise ValueError(f'{fid}: unknown age_window_policy')

def _proofs(store):
    out={}
    if store is None:return out
    for row in store.rows("SELECT payload FROM packets WHERE kind='TrainRunnerProof' ORDER BY rowid"):
        p=json.loads(row['payload']);out[p.get('runner_revision')]=p.get('packet_id')  # newest wins
    return out

def longrun_proof(r):
    """Only an Android-measured sustained artifact counts, and the bounded collection is never a long run."""
    path=r.store.meta('latest_sustained_proof') if r is not None else None
    if not path:return {'status':'ABSENT','reason':'no sustained proof artifact on this home'}
    try:
        from pathlib import Path
        p=Path(path);rep=json.loads(p.read_text())
        if not rep.get('phone_measured'):return {'status':'ABSENT','reason':'sustained proof not measured on the phone','artifact':str(p)}
        return {'status':'BOUNDED_PHONE_ONLY','reason':'bounded collection; weeks-long Redmi run absent','artifact':str(p),'sha256':file_hash(p),'proof_status':rep.get('status')}
    except (OSError,ValueError,TypeError) as exc:return {'status':'ABSENT','reason':'unreadable sustained proof: '+type(exc).__name__}

def annotate(rows,r=None):
    """Adds the ten §102 fields plus `neuro_claim_status` to every row in place; returns the summary block."""
    sp=spec();proofs=_proofs(getattr(r,'store',None));longrun=longrun_proof(r)
    policy=(getattr(r,'cfg',None) or {}).get('age_plasticity_policy','boot')
    summary={'canon_source':sp['canon_source'],'by_class':{},'by_claim_status':{},'untested_labels':[],'missing_evidence':[],'lowered_pass':[],
             'redmi_longrun_proof':longrun['status'],'curated_rows':0,'unknown_curated_ids':[]}
    ids={row['feature_id'] for row in rows}
    summary['unknown_curated_ids']=sorted(set(sp['rows'])-ids)
    for row in rows:
        fid=row['feature_id'];curated=fid in sp['rows'];e=dict(sp['default'],**sp['rows'].get(fid,{}));summary['curated_rows']+=curated
        cls=e['neuro_inspiration_class'];ab=e['ablation_baseline']
        if ab is not None:
            ab=dict(ab,evidence_present={p:(APP/p).exists() for p in ab['evidence']})
            if not all(ab['evidence_present'].values()):summary['missing_evidence'].append(fid)
        rev=e.get('train_runner_revision')
        row.update(neuro_inspiration_class=cls,neuro_claim_limit=e['neuro_claim_limit'],ablation_baseline=ab,
                   train_runner_proof_id=proofs.get(rev) if rev else None,modulator_schema=e['modulator_schema'],eligibility_owner=e['eligibility_owner'],
                   corollary_required=e['corollary_required'],replay_authority=e['replay_authority'],
                   age_window_policy=('AGE_CONTROL:'+policy) if e['age_window_policy']=='AGE_CONTROL' else 'NONE',redmi_longrun_proof=longrun)
        if cls not in sp['claiming_classes']:status='NO_CLAIM'
        elif ab is None:status='UNTESTED_LABEL'
        else:status=STATUS[ab['verdict']]
        row['neuro_claim_status']=status
        if status=='UNTESTED_LABEL':
            summary['untested_labels'].append(fid)
            if row.get('gate_status')=='PASS':
                row['gate_status']='PARTIAL';row['known_limitations']=list(row.get('known_limitations') or [])+['§102: neuro claim without §99 ablation cannot PASS']
                summary['lowered_pass'].append(fid)
        summary['by_class'][cls]=summary['by_class'].get(cls,0)+1;summary['by_claim_status'][status]=summary['by_claim_status'].get(status,0)+1
    return summary
