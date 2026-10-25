"""Run174 prereg: frozen B1 native token taps, topic-disjoint external predictor.

No body weights, Age permission, answer utility, or Body-JEPA gate promotion.
"""
import hashlib
import json
import threading
import time
import numpy as np

TOPICS = (
 ('Mira','compass','harbor'),('Theo','lantern','orchard'),('Nina','map','station'),
 ('Omar','notebook','library'),('Iris','bicycle','workshop'),('Leah','camera','museum'),
 ('Aria','radio','garden'),('Jonas','key','courtyard'),('Eva','thermometer','kitchen'),
 ('Luca','telescope','observatory'),('Noah','hammer','barn'),('Rosa','ticket','airport'),
 ('Ada','sensor','laboratory'),('Liam','clock','tower'),('Zoe','rope','campsite'),
 ('Maya','brush','gallery'),('Finn','meter','bridge'),('Sara','tablet','classroom'),
 ('Pia','suitcase','hotel'),('Emil','umbrella','market'),
)
VARIANTS = (
 'They checked the markings carefully and wrote down the first measurement before leaving.',
 'They compared two readings, corrected an earlier mistake, and explained the result to a friend.',
 'After a short pause, they opened the case and examined every part under a bright light.',
 'They noticed a small difference, recorded the change, and returned the object to its shelf.',
 'Before sunset, they repeated the observation and described what had changed since morning.',
 'They followed the written instructions, finished the inspection, and stored the result safely.',
)
TEXTS = tuple(f'{name} carried a {item} to the {place}. {suffix}'
              for name,item,place in TOPICS for suffix in VARIANTS)
SEED = 17425
SCHEMA = 'V13_RUN174_B1_TOPIC_DISJOINT_SHADOW_V1'

def text_sha():
    return hashlib.sha256(json.dumps(TEXTS,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def collect(runner):
    taps=[]
    for i,text in enumerate(TEXTS):
        r=runner.tap(text,threading.Event(),time.monotonic()+180,max_tokens=64)
        ids=r['token_ids'];v=np.asarray(r['vectors'],dtype=np.float64);m=r['metrics']
        if (type(ids) is not list or not 12<=len(ids)<=64 or v.shape!=(len(ids),2048)
                or not np.isfinite(v).all() or np.any(np.sum(v*v,axis=1)<1e-20)
                or m.get('tap_id')!='lfm2.result_norm.final.v1'
                or m.get('CAN_TRAIN_BODY') is not False or m.get('CAN_LATENT_INJECT') is not False):
            raise ValueError('run174_native_tap_invalid')
        taps.append({'topic':i//len(VARIANTS),'tokens':len(ids),'vectors':v,
                     'token_ids_sha256':hashlib.sha256(json.dumps(ids).encode()).hexdigest()})
    return taps

def pairs(taps):
    if len(taps)!=len(TEXTS):raise ValueError('run174_source_count')
    x=[];y=[];groups=[]
    for i,row in enumerate(taps):
        if row['topic']!=i//len(VARIANTS):raise ValueError('run174_source_order')
        v=np.asarray(row['vectors'],dtype=np.float64)
        if v.ndim!=2 or v.shape[1]!=2048 or not 12<=len(v)<=64 or not np.isfinite(v).all():
            raise ValueError('run174_source_invalid')
        for j in range(3,len(v)-2,3):
            x.append(v[j]);y.append(v[j+2]);groups.append('topic-%02d'%row['topic'])
    return np.stack(x),np.stack(y),groups

def run_shadow(taps,train_fn,normalize_fn,out_dir,config):
    x,y,groups=pairs(taps)
    g=np.array(groups);train_dev=np.array([int(s.split('-')[1])<17 for s in groups]);test=~train_dev
    if len(set(g[train_dev]))!=17 or len(set(g[test]))!=3 or len(x[test])<30:
        raise ValueError('run174_partition_count')
    metrics=train_fn({'config':config,'context_states':x[train_dev],
                      'future_states':y[train_dev],'source_groups':g[train_dev].tolist(),
                      'active_checkpoint':None},out_dir)
    from pathlib import Path
    with np.load(Path(out_dir)/'candidate.npz',allow_pickle=False) as z:
        p,q,t,anchor=(z[k].copy() for k in ('projector','predictor','target','anchor'))
    xx=normalize_fn(x[test]);yy=normalize_fn(y[test])
    prediction=(xx@p)@q;fixed=yy@anchor
    mse=lambda a,b:float(np.mean((a-b)**2))
    scores={'prediction_fixed_target_mse':mse(prediction,fixed),
            'copy_fixed_target_mse':mse(xx@anchor,fixed),
            'shuffled_fixed_target_mse':mse(prediction,np.roll(fixed,1,axis=0)),
            'moving_target_prediction_mse':mse(prediction,yy@t),
            'test_pairs':int(test.sum()),'test_topics':[17,18,19]}
    beats=bool(scores['prediction_fixed_target_mse']<.98*min(scores['copy_fixed_target_mse'],scores['shuffled_fixed_target_mse']))
    return {'schema':SCHEMA,'text_set_sha256':text_sha(),'texts':len(TEXTS),
            'topic_groups':20,'train_dev_topics':list(range(17)),'test_topics':[17,18,19],
            'temporal_pairs':len(x),'worker_metrics':metrics,'independent_test':scores,
            'fixed_target_control_pass':beats,'shadow_commit_eligible':bool(metrics['commit_eligible'] and beats),
            'native_body_parameters_modified':0,'body_jepa_gate_pass':False,
            'semantic_answer_utility_proven':False,'jepa_weight':0,'redmi':False,
            'gates':{'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
                     'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}}
