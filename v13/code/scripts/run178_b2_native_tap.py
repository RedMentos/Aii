"""Run178 pinned Qwen B2 native read-only tap proof; no JEPA or learning."""
import hashlib
import json
import threading
import time
import numpy as np

TEXTS=(
 'The astronomer checked the small telescope before sunrise.',
 'A blue train stopped near the old stone bridge.',
 'The mechanic replaced a loose screw in the bicycle.',
 'Three students compared notes after the science lesson.',
 'A farmer counted the sheep beside the wooden fence.',
 'The museum guide described an ancient clay bowl.',
 'At noon, a chef measured flour for a fresh loaf.',
 'The pilot reviewed the weather before leaving the airport.',
 'A gardener watered the young tree behind the house.',
 'The librarian sorted books into two labeled boxes.',
 'The engineer inspected the sensor inside the workshop.',
 'A traveler folded the paper map and crossed the square.',
)
SCHEMA='V13_RUN178_QWEN_B2_NATIVE_TAP_V1'
DIM=1024
TAP_ID='qwen35.result_norm.final.v1'

def text_sha():
    return hashlib.sha256(json.dumps(TEXTS,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def one(runner,text):
    r=runner.tap(text,threading.Event(),time.monotonic()+180,max_tokens=64)
    ids=r['token_ids'];v=np.asarray(r['vectors'],dtype=np.float64);m=r['metrics']
    if (type(ids) is not list or not 3<=len(ids)<=64 or v.shape!=(len(ids),DIM)
            or not np.isfinite(v).all() or np.any(np.sum(v*v,axis=1)<=1e-20)
            or m.get('tap_id')!=TAP_ID or m.get('embedding_dim')!=DIM
            or m.get('CAN_TRAIN_BODY') is not False or m.get('CAN_LATENT_INJECT') is not False):
        raise ValueError('run178_native_b2_tap_invalid')
    return ids,v

def probe(runner):
    samples=[];token_counts=[];token_hashes=[];norms=[]
    for text in TEXTS:
        ids,v=one(runner,text)
        samples.append(v);token_counts.append(len(ids))
        token_hashes.append(hashlib.sha256(json.dumps(ids).encode()).hexdigest())
        norms.extend(np.linalg.norm(v,axis=1).tolist())
    repeat=[]
    for i in (0,1):
        ids,v=one(runner,TEXTS[i]);repeat.append(float(np.max(np.abs(v-samples[i]))))
        if hashlib.sha256(json.dumps(ids).encode()).hexdigest()!=token_hashes[i]:
            raise ValueError('run178_token_repeat_mismatch')
    distinct=float(np.linalg.norm(samples[0][-1]-samples[1][-1]))
    repeat_pass=max(repeat)<=1e-5
    distinct_pass=distinct>1e-4
    return {'schema':SCHEMA,'text_set_sha256':text_sha(),'texts':len(TEXTS),
            'tap_id':TAP_ID,'embedding_dim':DIM,'token_counts':token_counts,
            'token_id_hashes':token_hashes,'repeat_max_abs_diff':repeat,
            'repeat_pass':repeat_pass,'distinct_source_l2':distinct,
            'distinct_source_pass':distinct_pass,
            'vector_norm_min':min(norms),'vector_norm_max':max(norms),
            'b2_native_tap_gate_pass':bool(repeat_pass and distinct_pass),
            'body_training_authority':0,'body_jepa_gate_pass':False,'jepa_weight':0,
            'redmi':False,'semantic_answer_utility_proven':False,
            'gates':{'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
                     'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}}
