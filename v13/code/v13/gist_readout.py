"""WP-G2 / §1.2.3, G1B: native gist readout consumer for B2.

`gist.py` groups B2's source text by estimated token-equivalents. This module consumes what B2's native body actually
produced: the read-only final-state tap (`LatentTapPacket`, one vector per native token, pooling none) together with
the native tokenizer pieces. Native tokenizers stay unchanged (§1.2.3); grouping is readout scheduling on top.

Pipeline:
1. `token_spans` binds every native token to an exact UTF-8 byte span of the source. The concatenated pieces must
   reproduce the source bytes exactly, otherwise the readout is refused (no guessed alignment).
2. `native_shift` is the cosine distance between adjacent token states, a body-internal change signal.
3. `group` cuts native tokens into gist groups of ~size tokens. Modes: `fixed` (every size tokens), `text`
   (sentence/clause end in the 0.6..1.5 x size window), `native` (largest state shift in that window), `hybrid`
   (text boundary + HYBRID_WEIGHT x z-scored shift). `text`/`native`/`hybrid` share the same legal cut positions:
   never inside a word, an exact span (number, date, code, URL, quote) or before attached punctuation.
4. Each group carries its exact SourceRef (char span), its fine native token range, the mean-pooled state, the §3.2A
   coupling fields and its boundary confidence; `fit` merges the oldest groups to GIST_SLOTS like `gist.fit_slots`.

Which mode is the default comes from the preregistered native bench (`scripts/gist_readout_native_bench.py`, see
`docs/GIST_READOUT.md`). Authority: SHADOW readout only. Vectors never enter a prompt, receivers get no read or
injection right, and no body learns from them.
"""
import hashlib
import math
import numpy as np
from .common import dumps

KEY='G1B_GIST_READOUT';REVISION='g1b-gist-readout-v1'
MODES=('fixed','text','native','hybrid')
DEFAULT_MODE='hybrid'   # BOOT; replaced only by a preregistered bench verdict (docs/GIST_READOUT.md)
HYBRID_WEIGHT=1.        # BOOT, preregistered: weight of the z-scored native shift next to the text boundary score
LOW_MIN=.6;HIGH_MAX=1.5 # same window as gist.py
CLAIM_LIMIT=('Native readout grouping only: final-state tap, mean pooling, no receiver read/injection authority, '
             'no body learning; utility only as far as the preregistered retrieval bench measured it')

class ReadoutError(ValueError):pass

def _piece_bytes(piece):
    if isinstance(piece,str):return piece.encode('utf-8')
    if isinstance(piece,list) and all(isinstance(b,int) and 0<=b<256 for b in piece):return bytes(piece)
    raise ReadoutError('Unbekanntes Piece-Format')

def token_spans(text,pieces):
    """[(char_start, char_end)] per native token; pieces as returned by /tokenize with_pieces (str or byte list).

    A token that ends inside a multi-byte character covers that whole character; its neighbour then starts at the
    same character (zero-width when the character is fully owned by the previous token)."""
    raw=text.encode('utf-8');pos=0;byte_spans=[]
    for p in pieces:
        b=_piece_bytes(p)
        if raw[pos:pos+len(b)]!=b:raise ReadoutError('Native Pieces reproduzieren die Quelle nicht exakt (Token %d)'%len(byte_spans))
        byte_spans.append((pos,pos+len(b)));pos+=len(b)
    if pos!=len(raw):raise ReadoutError('Native Pieces decken die Quelle nicht vollständig ab')
    owner=[0]*len(raw);first=[False]*(len(raw)+1);c=0  # byte offset -> index of the char containing it
    for i,ch in enumerate(text):
        first[c]=True
        for k in range(len(ch.encode('utf-8'))):owner[c+k]=i
        c+=len(ch.encode('utf-8'))
    first[len(raw)]=True
    def char_start(b):return len(text) if b==len(raw) else owner[b]
    def char_end(b):return len(text) if b==len(raw) else owner[b] if first[b] else owner[b]+1
    out=[];prev=0
    for a,b in byte_spans:
        e=char_end(b);s=min(max(char_start(a),prev),e);out.append((s,e));prev=e
    return out

def native_shift(vectors):
    """Cosine distance d[i] between token i and i+1 (len n-1); all-zero rows are refused."""
    v=np.asarray(vectors,dtype=np.float64)
    if v.ndim!=2 or not np.isfinite(v).all():raise ReadoutError('Tap-Vektoren ungültig')
    n=np.linalg.norm(v,axis=1)
    if (n<=1e-10).any():raise ReadoutError('Tap enthält Null-Vektor')
    u=v/n[:,None];return 1.-np.sum(u[:-1]*u[1:],axis=1)

def _text_boundary(text,end):
    from .gist import _boundary
    return _boundary(text,end) if 0<end<=len(text) else 1.

def _exact_inside(text):
    import re
    from .context_os import exact_spans
    inside=set()
    for sp in exact_spans(text):
        for m in re.finditer(re.escape(sp),text):inside.update(range(m.start()+1,m.end()))
    return inside

def legal(text,spans,i,inside):
    """May a group end after token i? Same rule for text/native/hybrid/random; only the cut score differs."""
    e=spans[i][1]
    if e in inside:return False
    if e<=0 or e>=len(text):return True
    a,b=text[e-1],text[e]
    if a.isalnum() and b.isalnum():return False        # never inside a word
    return b.isspace() or b.isalnum()                  # never split a word from its own punctuation

def cut_points(text,spans,shift,size,mode):
    """Token indices after which a group ends (last token always ends one)."""
    if mode not in MODES:raise ReadoutError('Modus '+'|'.join(MODES))
    n=len(spans)
    if n==0:return []
    if mode=='fixed':return sorted(set(list(range(size-1,n-1,size))+[n-1]))
    inside=_exact_inside(text);allowed=lambda i:i+1>=n or legal(text,spans,i,inside)
    z=np.zeros(max(n-1,0))
    if len(shift):sd=float(shift.std());z=(shift-float(shift.mean()))/sd if sd>1e-12 else np.zeros_like(shift)
    def score(i):
        t=_text_boundary(text,spans[i][1])
        if mode=='text':return t
        if mode=='native':return float(z[i]) if i<n-1 else 0.
        return t+HYBRID_WEIGHT*(float(z[i]) if i<n-1 else 0.)
    lo=max(1,int(math.ceil(size*LOW_MIN)));hi=max(lo,int(math.floor(size*HIGH_MAX)))
    cuts=[];start=0
    while n-start>hi:
        window=[i for i in range(start+lo-1,min(start+hi,n-1)) if allowed(i)]
        if not window:  # no legal cut in the window: extend until the next legal one (never through an exact span)
            nxt=next((i for i in range(start+hi,n-1) if allowed(i)),None)
            if nxt is None:break
            window=[nxt]
        if mode=='text':  # like gist.group: first sentence end after the minimum or clause end after size, else best
            best=next((i for i in window if score(i)>=1. or score(i)>=.7 and i-start+1>=size),None)
            best=best if best is not None else max(window,key=lambda i:(score(i),-abs(i-start+1-size)))
        else:best=max(window,key=lambda i:(score(i),-abs(i-start+1-size)))
        cuts.append(best);start=best+1
    cuts.append(n-1);return cuts

def group(text,ref,spans,vectors,size,mode=DEFAULT_MODE,shift=None):
    v=np.asarray(vectors,dtype=np.float64)
    if len(v)!=len(spans):raise ReadoutError('Tap- und Token-Anzahl verschieden')
    shift=native_shift(v) if shift is None else shift
    out=[];start=0
    for c in cut_points(text,spans,shift,size,mode):
        cs,ce=spans[start][0],spans[c][1]
        out.append({'tokens':(start,c+1),'char':(cs,ce),'units':c+1-start,'vector':v[start:c+1].mean(0),
                    'boundary':round(_text_boundary(text,ce),3),'shift':round(float(shift[c]),5) if c<len(shift) else None,'scale':1,
                    'source_ref':dict(ref,char_start=ref['char_start']+cs,char_end=ref['char_start']+ce)})
        start=c+1
    return out

def fit(groups,slots):
    """Merge the oldest adjacent groups until the count fits (token-weighted mean vector); recent groups stay fine."""
    g=[dict(x,parts=x.get('parts',[x['source_ref']])) for x in groups];i=0
    while len(g)>slots:
        a,b=g[i],g[i+1];ua,ub=a['units'],b['units']
        g[i:i+2]=[{'tokens':(a['tokens'][0],b['tokens'][1]),'char':(a['char'][0],b['char'][1]),'units':ua+ub,
                   'vector':(a['vector']*ua+b['vector']*ub)/(ua+ub),'boundary':b['boundary'],'shift':b['shift'],'scale':a['scale']+b['scale'],
                   'min_boundary':min(a.get('min_boundary',a['boundary']),b.get('min_boundary',b['boundary'])),
                   'source_ref':dict(a['source_ref'],char_end=b['source_ref']['char_end']),'parts':a['parts']+b['parts']}]
        i+=1
        if i>=len(g)-1:i=0
    return g

def vector_sha256(vec):
    return hashlib.sha256(np.asarray(vec,dtype='<f4').tobytes()).hexdigest()

def slot_view(x,i,text,base):
    from .context_os import exact_spans
    s,e=x['source_ref']['char_start']-base,x['source_ref']['char_end']-base;t=text[s:e]
    return {'slot':i,'text':t,'source_ref':x['source_ref'],'native_tokens':list(x['tokens']),'units':x['units'],'scale':x['scale'],
            'source_span_refs':x.get('parts',[x['source_ref']]),'covered':{'source_id':x['source_ref'].get('source_id'),'char_start':x['source_ref']['char_start'],'char_end':x['source_ref']['char_end']},
            'compression_ratio':float(x['units']),'boundary_confidence':round(x.get('min_boundary',x['boundary']),3),
            'fallback':'EXACT_STORE' if exact_spans(t) else 'B1_DETAIL','vector_sha256':vector_sha256(x['vector'])}

def consume(text,ref,token_ids,pieces,vectors,size=None,slots=None,mode=DEFAULT_MODE,tap_id=None):
    """Native gist plan from one B2 tap. Returns (plan, slot_vectors); vectors stay out of the JSON plan."""
    from .age import GIST_BASE,GIST_SLOTS
    size=int(size or GIST_BASE[0]);slots=int(slots or GIST_SLOTS)
    if len(pieces)!=len(token_ids) or len(vectors)!=len(token_ids):raise ReadoutError('Token/Piece/Vektor-Anzahl verschieden')
    spans=token_spans(text,pieces);raw=group(text,ref,spans,vectors,size,mode);fitted=fit(raw,slots);base=ref['char_start']
    cover=[0]*len(text)
    for x in fitted:
        for k in range(x['char'][0],x['char'][1]):cover[k]+=1
    lossless=all(c==1 for c in cover)
    if not lossless:raise ReadoutError('Gist-Slots decken die Quelle nicht verlustfrei ab')
    plan={'revision':REVISION,'mode':mode,'tokens_per_group':size,'max_slots':slots,'native_tokens':len(token_ids),'groups_raw':len(raw),
          'coarsened':len(raw)>len(fitted),'boundary_rate':round(sum(g['boundary']>=.7 for g in raw)/len(raw),3) if raw else 1.,
          'tap_id':tap_id,'pooling':'mean_over_group_tokens','dim':int(np.asarray(vectors).shape[1]),'lossless':lossless,
          'slots':[slot_view(x,i,text,base) for i,x in enumerate(fitted)],
          'authority':'SHADOW','receiver_read_authority':0,'receiver_injection_authority':0,'body_learning_authority':0,'claim_limit':CLAIM_LIMIT}
    return plan,np.stack([x['vector'] for x in fitted]) if fitted else np.zeros((0,plan['dim']))

def latest_tap(r):
    import json
    rows=r.store.rows("SELECT payload FROM packets WHERE kind='LatentTapPacket' ORDER BY rowid DESC LIMIT 50")
    for x in rows:
        p=json.loads(x['payload'])
        if p.get('role')=='B2_GIST':return p
    raise ReadoutError('Kein B2_GIST-Tap gespeichert; erst :tap B2_GIST [Start:Ende]')

def readout(r,packet=None,mode=DEFAULT_MODE,deadline=None):
    """Consume the stored B2 tap: verify it (`Cognition.read_tap`), re-tokenize the source with the same pinned body to
    get the pieces, require identical token IDs, then group. The tokenizer runner is unloaded afterwards."""
    import time
    p=packet or latest_tap(r);data=r.cognition.read_tap(p);text=r.store.read_source(p['source_ref'])
    deadline=deadline or time.monotonic()+float(r.cfg.get('observer_seconds',60))
    runner=r.pool.get_tap('B2_GIST')
    try:
        runner.load(r.cancel_event,deadline)
        toks=runner._json('POST','/tokenize',{'content':text,'add_special':True,'with_pieces':True},deadline)['tokens']
    finally:r.pool.unload()
    ids=[t['id'] for t in toks]
    if ids!=data['token_ids']:raise ReadoutError('Tokenizer-Pieces gehören nicht zu diesem Tap')
    plan,_=consume(text,p['source_ref'],ids,[t['piece'] for t in toks],data['vectors'],mode=mode,tap_id=p.get('tap_id'))
    plan['tap_packet_id']=p['packet_id'];plan['feature_sha256']=p['feature_sha256']
    r.store.log('gist_readout',p.get('event_id'),{k:plan[k] for k in ('revision','mode','native_tokens','groups_raw','coarsened','boundary_rate','tap_id')}|{'slots':len(plan['slots'])})
    return plan

def operator_command(r,args):
    """:gist readout [fixed|text|native|hybrid]"""
    mode=args[0] if args else DEFAULT_MODE
    if len(args)>1 or mode not in MODES:raise ValueError(':gist readout ['+'|'.join(MODES)+']')
    plan=readout(r,mode=mode)
    return dumps(plan|{'slots':[{k:s[k] for k in ('slot','text','native_tokens','scale','boundary_confidence','fallback')} for s in plan['slots']]})
