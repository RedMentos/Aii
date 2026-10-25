"""Run157: A3 real raw-stem source-group support diagnostic, no training.

Uses frozen student_worker.raw_features/split without changing worker, weights,
threshold or any V13 gate. Value substitutions are novelty controls, not OOD truth.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from scripts.a3_support_ood_probe_run156 import score
from v13.student_worker import raw_features,split

GATES={'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
       'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}


def corpus():
    groups=[f'source_{i:04d}' for i in range(128)]
    texts=[f'Project Atlas rule {i:04d}: approved budget is {1000+i*3} units and owner is team {i%11}.' for i in range(128)]
    far=[f'Cosmic geology sample {i:04d}: basalt age is {i*7+400} million years and isotope is {i%17}.' for i in range(64)]
    substituted=[f'Project Atlas rule {i:04d}: approved budget is {900000+i*9} units and owner is team {i%11}.' for i in range(64)]
    return groups,texts,far,substituted


def probe():
    groups,texts,far,substituted=corpus()
    ti,vi=split(groups)
    x=np.stack([raw_features(t) for t in texts])
    f=np.stack([raw_features(t) for t in far])
    s=np.stack([raw_features(t) for t in substituted])
    far_result=score(x[ti],x[vi],f)
    substituted_result=score(x[ti],x[vi],s)
    assert far_result['support_floor']==substituted_result['support_floor']
    spec={'group_count':128,'far_count':64,'substituted_count':64,
          'group_prefix':'source_', 'text_template':'Project Atlas rule {id}: approved budget is {1000+3id} units and owner is team {id%11}.',
          'far_template':'Cosmic geology sample {id}: basalt age is {400+7id} million years and isotope is {id%17}.',
          'substitution_template':'Project Atlas rule {id}: approved budget is {900000+9id} units and owner is team {id%11}.'}
    return {'schema':'V13_RUN157_A3_RAWSTEM_SOURCE_PROBE_V1',
            'source_definition_sha256':hashlib.sha256(json.dumps(spec,sort_keys=True).encode()).hexdigest(),
            'source_texts_sha256':hashlib.sha256(json.dumps([groups,texts,far,substituted],ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
            'train_count':len(ti),'heldout_id_count':len(vi),
            'far_domain':far_result,'unseen_value_substitution':substituted_result,
            'evidence_class':'MODEL_FREE_RAW_STEM_SOFTWARE_ONLY',
            'claim':'SOURCE_SIMILARITY_IS_NOT_FACTUAL_TRUTH_OR_LEARNING',
            'teacher_parameter_updates':0,'student_parameter_updates':0,
            'authority':'SHADOW_DIAGNOSTIC_NOT_ACTIVE','gate':'UNVERIFIED','gates':GATES,
            'limitations':['no native teacher embeddings or student learning',
                           'substituted values are a novelty stressor, not ground-truth OOD class',
                           'fixed synthetic English templates are not real user data',
                           'no Redmi, Body-JEPA or full V13 proof']}


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();r=probe()
    with a.output.open('x',encoding='utf-8') as f:f.write(json.dumps(r,sort_keys=True,indent=2)+'\n')
    print('RUN157_A3_RAWSTEM',r['train_count'],r['heldout_id_count'],r['gate'])

if __name__=='__main__':main()
