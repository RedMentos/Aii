#!/usr/bin/env python3
"""WP-Z6b: read-only off-policy wake diagnostic over paired real model outputs.

NOT an online selective-wake experiment: adaptive-arm outputs were produced
under a different runtime path. Estimates are descriptive, not causal.
"""
import argparse
import hashlib
import os
import tempfile
import json
from math import comb
from pathlib import Path
from c3_draft_math_guard import assess

ARMS=('disabled','low','adaptive','high','max')

def _sign_p(w,l):
    n=w+l
    return min(1.0,2*sum(comb(n,k) for k in range(min(w,l)+1))/(2**n)) if n else 1.0

def analyse(dataset,*,source_sha256=None):
    """Select using ONLY disabled C3 text; never leak answer labels into routing."""
    if type(dataset) is not dict or dataset.get('kind')!='V13_Z6A_EFFORT_BENCH' or dataset.get('seed')!=23:
        raise ValueError('unregistered Z6a dataset')
    rows=dataset.get('rows')
    if type(rows) is not list or len(rows)!=300:
        raise ValueError('expected exactly 60 fixtures x five arms')
    by={arm:{} for arm in ARMS}
    for row in rows:
        if type(row) is not dict or row.get('arm') not in by:
            raise ValueError('unknown arm')
        arm,fid=row['arm'],row.get('fixture')
        if type(fid) is not str or fid in by[arm] or type(row.get('pass')) is not bool or type(row.get('output')) is not str:
            raise ValueError('duplicate or invalid row')
        if type(row.get('turn_s')) not in (float,int) or row['turn_s']<0:
            raise ValueError('invalid time')
        by[arm][fid]=row
    fixtures=set(by['disabled'])
    if len(fixtures)!=60 or any(set(by[arm])!=fixtures for arm in ARMS):
        raise ValueError('arm fixture mismatch')
    decisions=[];gains=losses=0;wakes=overthinking=0
    for fid in sorted(fixtures):
        c=by['disabled'][fid];a=by['adaptive'][fid]
        reason=assess(c['output'])
        triggered=bool(reason['findings'])
        selected=a if triggered else c
        if triggered:
            wakes+=1
            overthinking+=int(c['pass'])
            gains+=int(a['pass'] and not c['pass'])
            losses+=int(c['pass'] and not a['pass'])
        decisions.append({'fixture':fid,'selected_arm':'adaptive' if triggered else 'disabled',
                          'signal':reason['status'],'selected_pass':selected['pass'],
                          'disabled_pass':c['pass'],'adaptive_pass':a['pass'],
                          'estimated_turn_s':selected['turn_s']})
    disabled_pass=sum(by['disabled'][f]['pass'] for f in fixtures)
    mixture_pass=sum(x['selected_pass'] for x in decisions)
    return {'schema':'V13_Z6B_OFFPOLICY_DIAGNOSTIC_V1','source_sha256':source_sha256,
            'source_seed':23,'n':len(decisions),'disabled_pass':disabled_pass,
            'adaptive_pass':sum(by['adaptive'][f]['pass'] for f in fixtures),
            'selected_pass':mixture_pass,'net_pass_delta':mixture_pass-disabled_pass,
            'wakes':wakes,'overthinking_on_disabled_passes':overthinking,
            'overthinking_rate':overthinking/disabled_pass if disabled_pass else None,
            'gains':gains,'losses':losses,'paired_sign_p':_sign_p(gains,losses),
            'estimated_mean_turn_s':sum(x['estimated_turn_s'] for x in decisions)/len(decisions),
            'claim':'RETROSPECTIVE_OFF_POLICY_NOT_CAUSAL_NOT_PREREGISTERED',
            'canonical_gate_pass':False,'decisions':decisions}


def run(input_path,output_path,expected_git_blob):
    """Bind to a pre-existing Git blob and atomically publish closed report."""
    if type(expected_git_blob) is not str or len(expected_git_blob)!=40 or any(c not in '0123456789abcdef' for c in expected_git_blob):
        raise ValueError('explicit registered Git blob SHA required')
    with Path(input_path).open('rb') as f:
        raw=f.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:raise ValueError('dataset too large')
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!=expected_git_blob:raise ValueError('source Git blob mismatch')
    def unique_pairs(pairs):
        d={}
        for k,v in pairs:
            if k in d:raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    result=analyse(json.loads(raw,object_pairs_hook=unique_pairs),source_sha256=hashlib.sha256(raw).hexdigest())
    data=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    out=Path(output_path)
    fd,tmp=tempfile.mkstemp(prefix='.z6b-',dir=out.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.link(tmp,out)  # no overwrite on racing publisher
        dirfd=os.open(out.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(dirfd)
        finally:os.close(dirfd)
    finally:os.unlink(tmp)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('z6a_json');p.add_argument('output_json');p.add_argument('--expected-git-blob',required=True);a=p.parse_args()
    r=run(a.z6a_json,a.output_json,a.expected_git_blob)
    print(json.dumps({k:r[k] for k in ('n','wakes','disabled_pass','selected_pass','gains','losses','paired_sign_p','canonical_gate_pass')}))
