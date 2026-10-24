"""WP-H/WP-S2 semantic memory keys for STEP3 (fast episodic recall).

A sentence embedding (EmbeddingGemma-300M, Matryoshka-truncated) ranks which stored human
correction belongs to a differently worded question. It is a relevance key only: the recalled
value is always re-read from its source, the entity guard still applies, and an explicitly
human-labelled learned cue head (retrieval_worker) keeps the last word. Never an answer cache.
"""
import math
import time
from .common import digest,Unavailable,Limits

PROMPT_VERSION='egemma-similarity-v1'
MAX_CHARS=1500  # one physical batch of 512 tokens holds this comfortably
BATCH=16

def prompt(text):
    """EmbeddingGemma symmetric task prompt; question is compared with stored question."""
    return 'task: sentence similarity | query: '+text[:MAX_CHARS]

def truncate(vector,dim):
    """Matryoshka view: first `dim` coordinates, renormalised to unit length."""
    v=[float(x) for x in vector[:dim]]
    if len(v)<dim:raise Unavailable(f'Embedding hat {len(vector)} statt mindestens {dim} Dimensionen')
    n=math.sqrt(sum(x*x for x in v))
    if not math.isfinite(n) or n<1e-12:raise Unavailable('Embedding ohne Norm')
    return [x/n for x in v]

def cosine(a,b):return max(-1.,min(1.,sum(x*y for x,y in zip(a,b))))

def mode(cfg,installed):
    m=cfg.get('memory_embedding','auto')
    return ('on' if installed else 'off') if m=='auto' else m

class EmbeddingEncoder:
    """Owns the optional M_EMBED llama-server; unloads after use unless memory_embed_keep=1."""
    def __init__(self,home,models,cfg):
        self.home=home;self.models=models;self.cfg=cfg;self.runner=None;self.last_metrics={}
    def installed(self):
        try:self.models.path_for('M_EMBED');return True
        except Unavailable:return False
    def revision(self):return self.models.revision('M_EMBED')
    def pids(self):return self.runner.pids() if self.runner else []
    def unload(self):
        if self.runner:self.runner.unload()
    def __call__(self,texts,cancel,deadline):
        from .runners import LlamaRunner
        started=time.monotonic()
        if self.runner is None:self.runner=LlamaRunner(self.home,'M_EMBED',self.models.path_for('M_EMBED'),self.cfg,purpose='embed')
        cold=not self.runner.pids()
        try:
            out=[]
            for i in range(0,len(texts),BATCH):out+=self.runner.embed([prompt(t) for t in texts[i:i+BATCH]],cancel,deadline)
            return out
        finally:
            self.last_metrics={'texts':len(texts),'cold_load':cold,'duration_s':round(time.monotonic()-started,4)}
            if not self.cfg.get('memory_embed_keep'):self.unload()

def _cached_unit_vector(value, dim):
    """Only finite real unit vectors are eligible for relevance scoring.

    Persisted SQLite cache is not a trusted encoder output. Six-decimal
    rounding of stored coordinates needs a small norm tolerance; this does
    not authenticate a forged *valid* unit vector.
    """
    if not isinstance(value, list) or len(value) != dim:
        return False
    try:
        if any(type(x) not in (int, float) or not math.isfinite(x) for x in value):
            return False
        norm = math.hypot(*value)
        return math.isfinite(norm) and abs(norm - 1.) <= 1e-3
    except (OverflowError, TypeError, ValueError):
        return False


class SemanticKeys:
    """Cached key vectors per memory; cache keys carry the value source id so :forget removes them."""
    def __init__(self,store,cfg,encoder,revision=None):
        self.s=store;self.cfg=cfg;self.encoder=encoder;self._revision=revision;self.last={};self.last_query=None
    @property
    def revision(self):return self._revision or (self.encoder.revision() if hasattr(self.encoder,'revision') else 'unversioned')
    def installed(self):return self.encoder.installed() if hasattr(self.encoder,'installed') else True
    def mode(self):return mode(self.cfg,self.installed())
    def cache_key(self,m):
        return 'memory-embed:'+m['source_id']+':'+digest(m['key_text'])[:16]+':'+self.revision+':'+str(self.cfg['memory_embed_dim'])+':'+PROMPT_VERSION
    def similarities(self,query,rows,cancel,deadline,cap=None):
        """Cosine query↔stored key per memory id. Up to `cap` missing keys are encoded in the query batch; the rest follow on later turns."""
        dim=self.cfg['memory_embed_dim'];started=time.monotonic();cached={};missing=[]
        for r in rows:
            v,_=self.s.state(self.cache_key(r))
            if _cached_unit_vector(v,dim):cached[r['id']]=v
            else:missing.append(r)
        deferred=len(missing)-(cap if cap is not None else len(missing));missing=missing[:cap] if cap is not None else missing
        if time.monotonic()>=deadline:raise Limits('Semantic recall budget')
        vectors=self.encoder([query]+[r['key_text'] for r in missing],cancel,deadline)
        if len(vectors)!=1+len(missing):raise Unavailable('Embedding-Anzahl passt nicht')
        q=truncate(vectors[0],dim)
        self.last_query={'digest':digest(query),'vector':q}  # reused by WP-N8 event boundaries (no extra encode)
        for r,v in zip(missing,vectors[1:]):
            v=[round(x,6) for x in truncate(v,dim)];cached[r['id']]=v;self.s.set_state(self.cache_key(r),v)
        result={mid:cosine(q,v) for mid,v in cached.items()}
        self.last={'status':'OK','mode':self.mode(),'candidates':len(rows),'encoded_keys':len(missing),'deferred_keys':max(0,deferred),'dim':dim,
                   'duration_s':round(time.monotonic()-started,4),'encoder':dict(getattr(self.encoder,'last_metrics',{}) or {})}
        return result

def attach(runtime):
    """Install the semantic key channel on runtime.memory (model optional; lexical recall stays)."""
    enc=EmbeddingEncoder(runtime.home,runtime.models,runtime.cfg);runtime.memory.semantic_keys=SemanticKeys(runtime.store,runtime.cfg,enc)
    return runtime.memory.semantic_keys

def status(runtime):
    keys=getattr(runtime.memory,'semantic_keys',None)
    if keys is None:return {'mode':'off','attached':False}
    n=runtime.store.one("SELECT COUNT(*) AS n FROM states WHERE key LIKE 'memory-embed:%'")['n']
    return {'mode':keys.mode(),'setting':runtime.cfg.get('memory_embedding','auto'),'installed':keys.installed(),'revision':keys.revision,
            'dim':runtime.cfg['memory_embed_dim'],'threshold':runtime.cfg['memory_embed_threshold'],'keep_loaded':bool(runtime.cfg['memory_embed_keep']),
            'cached_keys':n,'last':keys.last,'authority':'RELEVANCE_ONLY_VALUE_FROM_SOURCE','install':':download embedding'}
