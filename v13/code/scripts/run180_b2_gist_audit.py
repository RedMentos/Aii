"""Independent read-only Run180 raw B2/Gist evidence auditor."""
import hashlib
import json
from pathlib import Path
import numpy as np

MODEL_SHA='57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def piece_bytes(piece):
    if isinstance(piece,str):return piece.encode('utf-8')
    if isinstance(piece,list) and all(type(x) is int and 0<=x<256 for x in piece):return bytes(piece)
    raise ValueError('invalid native token piece')


def audit(root):
    root=Path(root);m=json.loads((root/'manifest.json').read_text())
    if m.get('schema')!='V13_RUN180_B2_GIST_NATIVE_RAW_V1' or m.get('status')!='NATIVE_READONLY_GIST_CONSUMER_PASS':
        raise ValueError('manifest status/schema mismatch')
    if m.get('model_sha256')!=MODEL_SHA or m.get('embedding_dim')!=1024 or m.get('tap_id')!='qwen35.result_norm.final.v1':
        raise ValueError('model/tap provenance mismatch')
    if any(m.get(k) is not False for k in ('step2_promoted','b3_promoted','body_learning','redmi_proven','full_v13_proven')):
        raise ValueError('unexpected authority promotion')
    for name in ('raw-token-vectors.npz','native-token-pieces.json','gist-plan.json'):
        if digest(root/name)!=m['files_sha256'][name]:raise ValueError('raw file hash mismatch: '+name)
    with np.load(root/'raw-token-vectors.npz',allow_pickle=False) as z:
        ids=z['token_ids'];v=z['vectors']
    tokens=json.loads((root/'native-token-pieces.json').read_text())
    plan=json.loads((root/'gist-plan.json').read_text())
    n=m['token_count']
    if ids.shape!=(n,) or v.shape!=(n,1024) or not np.isfinite(v).all() or np.any(np.linalg.norm(v,axis=1)<=1e-10):
        raise ValueError('raw native vector shape/finite/norm mismatch')
    if [t['id'] for t in tokens]!=ids.tolist():raise ValueError('native token ID mismatch')
    source=m['source_text']
    if b''.join(piece_bytes(t['piece']) for t in tokens)!=source.encode('utf-8'):
        raise ValueError('token pieces do not reconstruct exact source')
    if plan.get('dim')!=1024 or plan.get('tap_id')!=m['tap_id'] or plan.get('lossless') is not True:
        raise ValueError('Gist plan dimension/identity/losslessness mismatch')
    if plan.get('authority')!='SHADOW' or any(plan.get(k)!=0 for k in
            ('receiver_read_authority','receiver_injection_authority','body_learning_authority')):
        raise ValueError('Gist plan gained unauthorized authority')
    slots=plan['slots'];prev=0
    for s in slots:
        a,b=s['native_tokens'];cs,ce=s['source_ref']['char_start'],s['source_ref']['char_end']
        if not (a==prev and a<b<=n and s['text']==source[cs:ce]):
            raise ValueError('Gist slot source/token range mismatch')
        mean=v[a:b].mean(axis=0)
        if hashlib.sha256(np.asarray(mean,dtype='<f4').tobytes()).hexdigest()!=s['vector_sha256']:
            raise ValueError('Gist slot vector hash mismatch')
        prev=b
    if prev!=n or ''.join(s['text'] for s in slots)!=source or len(slots)!=m['slot_count']:
        raise ValueError('Gist slots incomplete')
    return {'status':'INDEPENDENT_RAW_AUDIT_PASS','tokens':n,'dim':1024,'slots':len(slots),
            'evidence_class':'LINUX_NATIVE_MODEL_READONLY','step2_promoted':False,'b3_promoted':False}


if __name__=='__main__':
    import sys
    print(json.dumps(audit(sys.argv[1]),sort_keys=True))
