"""WP-BP5b prerequisite: hash manifest for paired sender/receiver states and the small pre-check before any receiver tuning.

Why: receiver tuning (L3-like) must not be measured on a state pair that cannot be reproduced or that has no headroom.
Raw states stay out of git (public repo); only a manifest (revisions, seed, row hashes, split) is stored and verified.
`precheck` encodes the think-before-test rule: tune only if the L1 read beats NO_MESSAGE and a headroom to the
L2 read exists. numpy only.
"""
import hashlib
import json
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
    """Returns (ok, reasons). Refuses changed rows, changed order, other revisions (B3-H10)."""
    why=[]
    try:cur=build_manifest(Hs,Hr,y,manifest['sender_revision'],manifest['receiver_revision'],manifest['seed'],manifest['task'])
    except ValueError as e:return False,[str(e)]
    for k in ('rows','dims','sender_sha256','receiver_sha256','labels_sha256'):
        if cur[k]!=manifest[k]:why.append(k+' differs')
    if sender_rev is not None and sender_rev!=manifest['sender_revision']:why.append('sender revision differs')
    if receiver_rev is not None and receiver_rev!=manifest['receiver_revision']:why.append('receiver revision differs')
    return not why,why

def disjoint(m_a,m_b):
    """Two manifests (e.g. training seed and replication seed) must share no row."""
    return not (set(m_a['row_sha256'])&set(m_b['row_sha256']))

def precheck(acc,manifest):
    """acc: {'NO_MESSAGE','SCALAR','L1','L2'} mean accuracies in [0,1] on the NEW pair. Verdict GO / NO_GO with reasons."""
    why=[]
    if manifest['rows']<MIN_ROWS:why.append('rows %d < %d (power)'%(manifest['rows'],MIN_ROWS))
    if acc['L1']<=acc['NO_MESSAGE']+.02:why.append('L1 read does not beat NO_MESSAGE: no signal in the pair')
    head=acc['L1']-acc['L2']
    if head<MIN_HEADROOM:why.append('headroom L1-L2 %.3f < %.2f: tuning cannot show visible gain'%(head,MIN_HEADROOM))
    return {'verdict':'NO_GO' if why else 'GO','headroom':round(head,4),'latent_over_scalar':round(acc['L1']-acc['SCALAR'],4),
            'reasons':why,'note':'GO only allows a separately preregistered tuning test; L3 stays locked until the user releases it'}

def dump(manifest,path):
    with open(path,'w') as f:json.dump(manifest,f,sort_keys=True)
