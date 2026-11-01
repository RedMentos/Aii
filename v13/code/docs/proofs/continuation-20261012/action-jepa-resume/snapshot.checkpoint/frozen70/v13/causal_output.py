"""Existing output_adapter lifecycle for exact SAME-CAUSAL first-position heads.

No native calls, implicit human permissions or independent approval system.
Import reruns the unchanged numerical shadow fit against exported observations;
Store generation approval and every causal consume recheck current provenance.
"""
import json
import math
from pathlib import Path
import shutil
import zipfile
import numpy as np
from .common import APP,digest,dumps,file_hash,Unavailable
from scripts.live_output_adapter_port import HEAD_FORMAT,infer_live_head

GATES=('gradient_check','calibration_pass','utility_pass','retention_pass','held_out_support_pass',
       'checkpoint_reload','deterministic_repeat','first_native_token_accuracy_pass',
       'live_execution_support_capacity_pass','live_checkpoint_reload','commit_eligible')

def source_revision(model_revision):
    return digest(dumps({'worker':file_hash(APP/'v13/output_adapter_worker.py'),
                         'runner':file_hash(APP/'v13/runners.py'),'model':model_revision}))

def execution_revision(abi,model_revision):
    return digest(dumps({'feature_abi':abi,'model_revision':model_revision,
        'consumer_sources':{p:file_hash(APP/p) for p in ('v13/causal_output.py','v13/runners.py','v13/learning.py','v13/runtime.py')}}))

def gate_pass(metrics):
    return all(metrics.get(k) is True for k in GATES) and metrics.get('native_body_parameters_modified')==0 and metrics.get('semantic_truth_authority') is False

def validate_head(path,abi):
    """Reject legacy/foreign/nonfinite/malformed heads before publication."""
    if Path(path).stat().st_size>64*1024*1024:raise ValueError('Bounded64MiB head required')
    with zipfile.ZipFile(path) as z:
        if sum(f.file_size for f in z.infolist())>64*1024*1024:raise ValueError('Bounded uncompressed head required')
    with np.load(path,allow_pickle=False) as a:
        if str(a['format'])!=HEAD_FORMAT or json.loads(str(a['feature_abi']))!=abi:raise ValueError('Exact SAME-CAUSAL artifact ABI required; legacy heads cannot be converted')
        ids=a['token_ids'];w=a['weights'];anchors=a['anchors']
        if ids.ndim!=1 or ids.dtype.kind not in 'iu' or not 2<=len(ids)<=16 or len(set(ids.tolist()))!=len(ids) or np.any(ids<0) or np.any(ids>=65536):raise ValueError('Invalid native token vocabulary')
        if w.shape!=(1025,len(ids)) or not np.isfinite(w).all() or anchors.ndim!=2 or anchors.shape[1]!=1024 or not 1<=len(anchors)<=512 or not np.isfinite(anchors).all() or not np.allclose(np.linalg.norm(anchors,axis=1),1.,atol=1e-6):raise ValueError('Invalid native head/support')
        for name,low,high in [('temperature',.5,2.),('max_bias',.1,12.),('support_cosine',.9,1.)]:
            value=float(a[name])
            if not math.isfinite(value) or not low<=value<=high:raise ValueError('Invalid native head scalar')
        for name in ('feature_offset','feature_scale'):
            x=a[name]
            if x.shape!=(1024,) or not np.isfinite(x).all() or (name=='feature_scale' and np.any(x<.001)):raise ValueError('Invalid train-only feature normalization')
        n=len(a['retention_ids'])
        if not 1<=n<=2048 or a['retention_x'].shape!=(n,1025) or a['retention_base'].shape!=(n,len(ids)+1) or a['retention_y'].shape!=(n,):raise ValueError('Missing bounded native retention cases')
        if any(not np.isfinite(a[k]).all() for k in ('retention_x','retention_base','retention_y')):raise ValueError('Nonfinite retention cases')
        return ids.tolist()

def dataset_authorizations(store,dataset,model_revision,abi):
    """Bind actual exported F5 packets to the still-authorized original Store."""
    from scripts.train_live_output_adapter import artifact
    from scripts.export_live_output_dataset import select_label
    dataset=Path(dataset).resolve();inp=json.loads(dataset.read_text());rows=[];sources=set()
    for entry in inp['observations']:
        exported_path=artifact(dataset.parent,entry['human_decision']);decision=json.loads(exported_path.read_text())
        stored=store.one("SELECT payload FROM packets WHERE id=? AND kind='HumanDecision'",(decision['packet_id'],))
        if not stored or stored['payload']!=exported_path.read_text():raise ValueError('Exported HumanDecision must match actual current Store bytes')
        b=decision.get('export_binding',{})
        if b.get('schema')!='V13_HUMAN_OUTPUT_EXPORT_BINDING_V1' or b.get('human_saw_future_features') is not False or b.get('operator_export_intent')!='EXPLICIT_CLI_LEARN_UNCHANGED_LABEL_CONTEXT':raise ValueError('Explicit original-reference learn reexport required')
        selected=select_label(store,b['original_human_decision_packet_id'],decision['source_ref']['source_id'],model_revision,True)
        original=selected['decision']
        if digest(selected['original_payload'])!=b['original_human_decision_payload_sha256'] or b['original_label_source_ref']!=original['source_ref'] or decision['source_ref']!=original['source_ref'] or decision['value']!=selected['label'] or decision['selection']!={**original['selection'],'feature_abi':abi,'live_observation_sha256':entry['observed']['sha256']}:raise ValueError('Original/current reference lineage mismatch')
        observed_path=artifact(dataset.parent,entry['observed'])
        if b['observed_source_ref']['sha256']!=entry['observed']['sha256'] or store.read_source(b['observed_source_ref'])!=observed_path.read_text():raise ValueError('Actual Store native observation binding missing')
        if artifact(dataset.parent,entry['query_source']).read_text()!=selected['query'] or artifact(dataset.parent,entry['label_source']).read_text()!=selected['label']:raise ValueError('Store query/human source mismatch')
        refs=[*original['provenance'],*decision['provenance'],*original['selection']['source_refs'],original['selection']['context_ref'],selected['event']['source_ref']]
        for ref in refs:store.read_source(ref);sources.add(ref['source_id'])
        rows.append({'original_decision_id':original['packet_id'],'original_payload_sha256':digest(selected['original_payload']),
                     'export_decision_id':decision['packet_id'],'export_payload_sha256':digest(stored['payload']),
                     'label_source_id':original['source_ref']['source_id'],'observed_source_ref':b['observed_source_ref']})
    if not rows or len(rows)>512:raise ValueError('Bounded nonempty current human authorization cohort required')
    return rows,sorted(sources)

def current_authorizations(store,manifest,model_revision):
    from scripts.export_live_output_dataset import select_label
    rows=manifest.get('human_authorizations',[])
    if not 1<=len(rows)<=512:raise ValueError('Missing current human permissions')
    for row in rows:
        selected=select_label(store,row['original_decision_id'],row['label_source_id'],model_revision,True)
        if digest(selected['original_payload'])!=row['original_payload_sha256']:raise ValueError('Original human decision changed')
        exported=store.one("SELECT payload FROM packets WHERE id=? AND kind='HumanDecision'",(row['export_decision_id'],))
        if not exported or digest(exported['payload'])!=row['export_payload_sha256']:raise ValueError('Exported permission changed or removed')
        decision=json.loads(exported['payload']);b=decision.get('export_binding',{})
        if decision['learning_permission']!='learn' or b.get('original_human_decision_packet_id')!=row['original_decision_id'] or b.get('observed_source_ref')!=row['observed_source_ref'] or decision['selection']['feature_abi']!=manifest['feature_abi']:raise ValueError('Current exported authorization differs')
        store.read_source(row['observed_source_ref'])
    for sid in manifest['source_ids']:
        src=store.one('SELECT * FROM sources WHERE id=? AND deleted=0',(sid,))
        if not src:raise ValueError('Revoked learned source')
        store.read_source({'source_id':sid,'sha256':src['hash'],'char_start':0,'char_end':src['chars'],'modality':'text'})

def validate_update(store,row,models,*,committed=False):
    """Shared direct-Store approval and runtime consume guard."""
    from .causal_prepare import check_prepared
    manifest=json.loads(row['manifest']);abi=check_prepared(store.home)['feature_abi'];revision=models['C3_LANGUAGE']
    if manifest.get('component')!='output_adapter' or manifest.get('objective')!=HEAD_FORMAT or manifest.get('feature_abi')!=abi:raise ValueError('Output head is not exact current SAME-CAUSAL ABI')
    if manifest.get('context_revision')!=execution_revision(abi,revision) or manifest.get('encoder_revision')!=revision:raise ValueError('SAME-CAUSAL consumer/model revision changed')
    if not gate_pass(manifest.get('metrics',{})) or manifest.get('commit_eligible') is not True:raise ValueError('SAME-CAUSAL original numerical/calibration/utility/retention gates not passed')
    if committed and (row['status']!='COMMITTED' or manifest.get('approval_actor')!='OPERATOR_TTY' or not manifest.get('commit_generation_id')):raise ValueError('Individual operator approval required')
    path=(store.home/row['path']).resolve()
    if not path.is_relative_to(store.home.resolve()) or file_hash(path)!=row['hash'] or manifest.get('candidate_sha256')!=row['hash']:raise ValueError('Approved candidate bytes changed')
    proof=manifest.get('verified_shadow_report')
    proof_path=(store.home/proof['path']).resolve() if proof else None
    if proof_path is None or not proof_path.is_relative_to(store.home.resolve()) or file_hash(proof_path)!=proof['sha256']:raise ValueError('Verified shadow-fit receipt missing/changed')
    report=json.loads(proof_path.read_text())
    if report['candidate_sha256']!=row['hash'] or report['feature_abi']!=abi or report['metrics']!=manifest['metrics'] or report['dataset_sha256']!=manifest['dataset_sha256'] or report['numerical_worker_sha256']!=manifest['numerical_worker_sha256'] or file_hash(APP/'v13/output_adapter_worker.py')!=manifest['numerical_worker_sha256'] or not gate_pass(report['metrics']):raise ValueError('Verified original shadow-fit gates differ')
    current_authorizations(store,manifest,revision);validate_head(path,abi)
    return manifest,path

def approved_prediction(learner,observed):
    entry=learner.s.components().get('output_adapter')
    if not entry:return None,'NO_APPROVED_SAME_CAUSAL_COMPONENT'
    row=learner.s.one('SELECT * FROM updates WHERE id=?',(entry['update_id'],))
    if not row:raise ValueError('Active output update missing')
    # Exact old-format heads stay usable in server mode, never converted here.
    manifest=json.loads(row['manifest'])
    if manifest.get('objective')!=HEAD_FORMAT:return None,'INCOMPATIBLE_SEPARATE_PREFILL_HEAD'
    learner.active('output_adapter')
    manifest,path=validate_update(learner.s,row,learner.r.revisions(),committed=True)
    if observed['feature_abi']!=manifest['feature_abi']:raise ValueError('Live observation feature ABI differs')
    result=infer_live_head(observed,path,row['hash'],manifest['feature_abi'])
    result.update(approved_update_id=row['id'],artifact_sha256=row['hash'],individually_approved=True)
    return result,'APPROVED_SAME_CAUSAL_FIRST_TOKEN_DELTA' if result['in_support'] else 'OUT_OF_SUPPORT'

def copy_dataset(dataset,destination):
    """Private exact copy keeps every numerical source artifact restart-safe."""
    from scripts.train_live_output_adapter import artifact
    dataset=Path(dataset).resolve();destination=Path(destination);destination.mkdir()
    inp=json.loads(dataset.read_text());records=[]
    for row in inp['observations']:records.extend(row.values())
    if inp.get('active_checkpoint'):records.append(inp['active_checkpoint'])
    for descriptor in records:
        if not isinstance(descriptor,dict) or set(descriptor)!={'path','sha256'}:continue
        src=artifact(dataset.parent,descriptor);dst=destination/descriptor['path'];dst.parent.mkdir(parents=True,exist_ok=True)
        if dst.exists():
            if file_hash(dst)!=descriptor['sha256']:raise ValueError('Conflicting dataset destination')
        else:shutil.copyfile(src,dst)
    shutil.copyfile(dataset,destination/'dataset.json')
    return destination/'dataset.json'
