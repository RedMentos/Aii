"""WP-BP5b prerequisite: hash manifest for paired sender/receiver states and the small pre-check before any receiver tuning.

Why: receiver tuning (L3-like) must not be measured on a state pair that cannot be reproduced or that has no headroom.
Raw states stay out of git (public repo); only a manifest (revisions, seed, row hashes, split) is stored and verified.
`precheck` encodes the think-before-test rule: tune only if the L1 read beats NO_MESSAGE and a headroom to the
L2 read exists. numpy only.
"""
import hashlib
import json
from collections.abc import Mapping
from numbers import Integral, Real
import numpy as np

REVISION='b3pair-v1'
MIN_ROWS=3000      # attempt-7 power level (600 test rows per split)
MIN_HEADROOM=.03   # L1 read minus L2 read, accuracy fraction; below this tuning cannot show visible gain

def _h(a):return hashlib.sha256(np.ascontiguousarray(a,dtype=np.float32).tobytes()).hexdigest()

def build_manifest(Hs,Hr,y,sender_rev,receiver_rev,seed,task):
    """Hs[n,d_s], Hr[n,d_r] pooled paired states of the SAME n texts, y[n] labels. Returns a JSON-safe manifest."""
    Hs,Hr,y=np.asarray(Hs),np.asarray(Hr),np.asarray(y)
    if not (len(Hs)==len(Hr)==len(y)):raise ValueError('rows not paired: %d/%d/%d'%(len(Hs),len(Hr),len(y)))
    if not (np.isfinite(Hs).all() and np.isfinite(Hr).all()):raise ValueError('non-finite states')
    return {'revision':REVISION,'task':task,'seed':int(seed),'sender_revision':sender_rev,'receiver_revision':receiver_rev,
            'rows':int(len(y)),'dims':[int(Hs.shape[1]),int(Hr.shape[1])],'sender_sha256':_h(Hs),'receiver_sha256':_h(Hr),
            'labels_sha256':hashlib.sha256(np.asarray(y,dtype=np.int64).tobytes()).hexdigest(),
            'row_sha256':[hashlib.sha256(Hs[i].astype(np.float32).tobytes()+Hr[i].astype(np.float32).tobytes()).hexdigest()[:16] for i in range(len(y))]}

def verify(manifest,Hs,Hr,y,sender_rev=None,receiver_rev=None):
    """Returns (ok, reasons); verifies state/label hashes and the row hashes used by disjoint()."""
    why=[]
    try:cur=build_manifest(Hs,Hr,y,manifest['sender_revision'],manifest['receiver_revision'],manifest['seed'],manifest['task'])
    except (ValueError,KeyError,TypeError,IndexError) as e:return False,[str(e)]
    for k in ('revision','rows','dims','sender_sha256','receiver_sha256','labels_sha256','row_sha256'):
        if cur[k]!=manifest.get(k):why.append(k+' differs')
    if sender_rev is not None and sender_rev!=manifest['sender_revision']:why.append('sender revision differs')
    if receiver_rev is not None and receiver_rev!=manifest['receiver_revision']:why.append('receiver revision differs')
    return not why,why

def disjoint(m_a,m_b):
    """Compare verified state-pair hashes; this does not prove distinct input texts or independent seeds."""
    return not (set(m_a['row_sha256'])&set(m_b['row_sha256']))

def precheck(acc,manifest):
    """Numerical precheck only; does not verify the pair or unlock an L3 experiment."""
    why=[]
    rows=manifest.get('rows') if isinstance(manifest,Mapping) else None
    if isinstance(rows,bool) or not isinstance(rows,Integral) or rows<0:
        why.append('rows must be a non-negative integer')
    elif rows<MIN_ROWS:why.append('rows %d < %d (power)'%(rows,MIN_ROWS))
    values={}
    for key in ('NO_MESSAGE','SCALAR','L1','L2'):
        value=acc.get(key) if isinstance(acc,Mapping) else None
        if isinstance(value,bool) or not isinstance(value,Real) or not 0<=value<=1:
            why.append('%s accuracy must be a finite number in [0,1]'%key)
        else:values[key]=float(value)
    note=('GO is only a numerical precheck; pair integrity, model revisions, seed independence, '
          'L2 gate and L3 release require separate verification')
    if len(values)!=4:
        return {'verdict':'NO_GO','headroom':None,'latent_over_scalar':None,'reasons':why,'note':note}
    if values['L1']<=values['NO_MESSAGE']+.02:why.append('L1 read does not beat NO_MESSAGE: no signal in the pair')
    if values['L1']<=values['SCALAR']:why.append('L1 read does not beat SCALAR')
    head=values['L1']-values['L2']
    if head<MIN_HEADROOM:why.append('headroom L1-L2 %.3f < %.2f: tuning cannot show visible gain'%(head,MIN_HEADROOM))
    return {'verdict':'NO_GO' if why else 'GO','headroom':round(head,4),'latent_over_scalar':round(values['L1']-values['SCALAR'],4),
            'reasons':why,'note':note}

def dump(manifest,path):
    with open(path,'w') as f:json.dump(manifest,f,sort_keys=True)
