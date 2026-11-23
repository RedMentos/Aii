"""WP-N15 vision scaffold in the lab (STEP 8, §18.9, G10B, part of §24.31). Shadow only: the Age-0 core stays text.

  SOURCE        an image is an immutable source (sha256 blob, sources.kind='IMAGE'); every region carries a SourceRef
                with modality 'image' and its pixel box, so anything derived from a region points back to exact pixels.
  RAW EYE       tiles -> handcrafted features (colour, hue histogram, edges/orientation, coarse layout, 4x4 luminance;
                numpy + PIL only) -> a learnable student projector into the text-embedding space.
  TEACHER EYE   a frozen small VLM (LFM2.5-VL-450M GGUF + mmproj via llama.cpp `llama-mtmd-cli`). Its captions are
                REFERENCE_NOT_FACT: a training target and a hint, never a source of truth. Missing teacher fails open.
  ALIGNMENT     the student is fitted (ridge, closed form) to the teacher-caption embedding (EmbeddingGemma when
                installed, else a deterministic hashed bag of words); measured by held-out caption retrieval.
  RECONSTRUCT   a linear decoder from the student embedding back to an 8x8 luminance thumbnail, used only as a
                measurement of how much image information the student keeps (relative MSE vs the mean image).
  TILES (WP-T16) alignment per grid tile without tile captions: a tile inside a described region (whole image, half or
                quadrant) inherits that region's caption when it is salient (differs from the border background), else
                the BACKGROUND text; a separate tile projector maps single-tile features into the same text space, so
                `:image find` scores every tile (4x4 heat map) and several objects in one image are found separately.
  TEACHER OFF   `:image teacher off` removes the teacher: describe is refused, look/locate/find keep working from the
                student alone (teacher removal, reliance measured in scripts/vision_bench3.py). `on` restores it.
Nothing here reaches the chat context or the weights of the core; `:image` is the operator surface.
"""
import io
import json
import math
import os
import re
import subprocess
import tempfile
import time
import zlib
from pathlib import Path
from .common import Unavailable,atomic_write,digest,dumps,uid,now

KEY='WP_N15_VISION';REVISION='wp-n15-vision-v1';AUTHORITY='REFERENCE_NOT_FACT';STUDENT='STUDENT_ESTIMATE'
PROMPT='Describe the image in one sentence: name the main objects, their colours and where they are.'
DEFAULTS={'grid':4,'tile_px':32,'thumb':8,'max_bytes':20*1024*1024,'max_pixels':40_000_000,'max_images':256,
          'hash_dim':256,'ridge':1.,'min_train':4,'teacher_tokens':64,'teacher_timeout':180,'threads':4}
HUE_BINS=8;ORI_BINS=4
BACKGROUND='plain empty background'   # WP-T16 target text for non-salient tiles
SALIENT=.08                            # BOOT: mean |pixel - border median| (0..1) above which a tile shows something

# ---------------------------------------------------------------- source + regions
def _np():
    import numpy;return numpy

def decode(data,cfg=DEFAULTS):
    """Bytes -> RGB PIL image with size limits (decompression-bomb guard)."""
    from PIL import Image
    if len(data)>cfg['max_bytes']:raise ValueError('Bild zu groß (> %d MB)'%(cfg['max_bytes']>>20))
    try:
        with Image.open(io.BytesIO(data)) as probe:
            w,h=probe.size
            if w<1 or h<1 or w*h>cfg['max_pixels']:raise ValueError('Bildgröße ungültig: %dx%d'%(w,h))
            probe.verify()
        with Image.open(io.BytesIO(data)) as im:return im.convert('RGB')
    except (OSError,SyntaxError,Image.DecompressionBombError) as e:raise ValueError('Kein lesbares Bild: '+type(e).__name__) from e

def boxes(w,h,grid):
    """Region 'g' is the whole image, 'rIJ' the grid cell in row I, column J, 'hl/hr/ht/hb' the left/right/top/bottom
    half (integer pixel boxes, x1/y1 exclusive). Halves give the teacher and the student a coarse place vocabulary."""
    out=[{'region_id':'g','box':[0,0,w,h]}]
    for i in range(grid):
        for j in range(grid):
            out.append({'region_id':'r%d%d'%(i,j),'box':[w*j//grid,h*i//grid,max(w*(j+1)//grid,w*j//grid+1),max(h*(i+1)//grid,h*i//grid+1)]})
    hw,hh=max(1,w//2),max(1,h//2)
    out+=[{'region_id':'hl','box':[0,0,hw,h]},{'region_id':'hr','box':[w-hw,0,w,h]},{'region_id':'ht','box':[0,0,w,hh]},{'region_id':'hb','box':[0,h-hh,w,h]}]
    out+=[{'region_id':'qtl','box':[0,0,hw,hh]},{'region_id':'qtr','box':[w-hw,0,w,hh]},{'region_id':'qbl','box':[0,h-hh,hw,h]},{'region_id':'qbr','box':[w-hw,h-hh,w,h]}]  # WP-T16 quadrants
    return out

def region_ref(ref,region):
    """SourceRef of one region: same blob, modality 'image', char range empty, pixel box as provenance."""
    return {'source_id':ref['source_id'],'sha256':ref['sha256'],'char_start':0,'char_end':0,'modality':'image','region_id':region['region_id'],'box':list(region['box'])}

def ingest(store,data,cfg=DEFAULTS,label=None):
    """Store image bytes as an IMAGE source (dedup by hash) and register its regions. Returns the image record."""
    im=decode(data,cfg);w,h=im.size;sha=digest(data);st=load(store)
    for rec in st['images'].values():
        if rec['ref']['sha256']==sha:return rec
    if len(st['images'])>=cfg['max_images']:raise ValueError('Zu viele Bilder im Lab; erst :image forget')
    path=store.home/'data/blobs'/sha
    if not path.exists():atomic_write(path,data)
    sid=uid('src')
    with store.tx() as c:c.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,0)',(sid,sha,'IMAGE',len(data),0,now()))
    ref={'source_id':sid,'sha256':sha,'char_start':0,'char_end':0,'modality':'image'}
    rec={'ref':ref,'size':[w,h],'label':(label or '')[:80],'regions':boxes(w,h,cfg['grid']),'captions':[],'created':now()}
    st['images'][sid]=rec;save(store,st);return rec

def read_image(store,ref,cfg=DEFAULTS):
    """Verified pixels for a (region) SourceRef: the source row must be live, the blob hash must match."""
    r=store.one('SELECT * FROM sources WHERE id=?',(ref.get('source_id'),))
    if not r or r['deleted'] or r['kind']!='IMAGE' or r['hash']!=ref.get('sha256'):raise ValueError('Dangling/gelöschter Bild-SourceRef')
    b=(store.home/'data/blobs'/r['hash']).read_bytes()
    if digest(b)!=r['hash']:raise ValueError('Bild-Hash falsch')
    im=decode(b,cfg)
    if 'box' in ref:
        x0,y0,x1,y1=ref['box'];w,h=im.size
        if not (0<=x0<x1<=w and 0<=y0<y1<=h):raise ValueError('Region außerhalb des Bildes')
        im=im.crop((x0,y0,x1,y1))
    return im

# ---------------------------------------------------------------- RAW EYE
def tile_features(im,px=32):
    """37 numbers per tile: mean/std RGB, saturation-weighted hue histogram, mean S/V, edge energy, orientation
    histogram, 4x4 luminance. All in [0,1]-ish, no learning."""
    np=_np();a=np.asarray(im.resize((px,px)),dtype=np.float32)/255.
    rgb_mean=a.reshape(-1,3).mean(0);rgb_std=a.reshape(-1,3).std(0)
    hsv=np.asarray(im.resize((px,px)).convert('HSV'),dtype=np.float32)/255.
    hue,sat,val=hsv[...,0].ravel(),hsv[...,1].ravel(),hsv[...,2].ravel()
    hh=np.bincount(np.minimum((hue*HUE_BINS).astype(int),HUE_BINS-1),weights=sat,minlength=HUE_BINS)/max(1.,len(hue))
    g=a.mean(-1);gx=np.zeros_like(g);gy=np.zeros_like(g);gx[:,1:-1]=g[:,2:]-g[:,:-2];gy[1:-1]=g[2:]-g[:-2]
    mag=np.hypot(gx,gy);ang=(np.arctan2(gy,gx)%math.pi)/math.pi
    ori=np.bincount(np.minimum((ang.ravel()*ORI_BINS).astype(int),ORI_BINS-1),weights=mag.ravel(),minlength=ORI_BINS)/max(1e-6,float(mag.sum()))
    lum=g.reshape(4,px//4,4,px//4).mean((1,3)).ravel()
    return np.concatenate([rgb_mean,rgb_std,hh,[sat.mean(),val.mean(),mag.mean()],ori,lum]).astype(np.float32)

def features(im,cfg=DEFAULTS):
    """Global descriptor: whole-image tile features + per-cell (mean RGB, edge energy) layout over the grid."""
    np=_np();w,h=im.size;cells=[]
    for r in boxes(w,h,cfg['grid']):
        if r['region_id'][0]!='r':continue
        t=tile_features(im.crop(tuple(r['box'])),cfg['tile_px']);cells.append(np.concatenate([t[:3],t[16:17],t[17:18]]))
    return np.concatenate([tile_features(im,cfg['tile_px'])]+cells).astype(np.float32)

def background(im):
    """Median colour of the 2-pixel border (WP-T16): what 'nothing' looks like in this image."""
    np=_np();a=np.asarray(im,dtype=np.float32)/255.
    edge=np.concatenate([a[:2].reshape(-1,3),a[-2:].reshape(-1,3),a[:,:2].reshape(-1,3),a[:,-2:].reshape(-1,3)])
    return np.median(edge,0)

def saliency(im,box,bg):
    np=_np();a=np.asarray(im.crop(tuple(box)),dtype=np.float32)/255.
    return float(np.abs(a-bg).mean()) if a.size else 0.

def inside(inner,outer):return outer[0]<=inner[0] and outer[1]<=inner[1] and inner[2]<=outer[2] and inner[3]<=outer[3]

def tile_pairs(im,regions,captions,cfg=DEFAULTS,thr=SALIENT):
    """Weak tile labels: for every grid tile, the caption of the *smallest* described region that contains it if the
    tile is salient, else BACKGROUND. captions: {region_id: text}. Returns [(tile_id, features, text, saliency)]."""
    bg=background(im);area=lambda b:(b[2]-b[0])*(b[3]-b[1]);described=[r for r in regions if r['region_id'] in captions]
    out=[]
    for t in regions:
        if t['region_id'][0]!='r':continue
        s=saliency(im,t['box'],bg)
        own=sorted((r for r in described if inside(t['box'],r['box'])),key=lambda r:area(r['box']))
        if s>thr and not own:continue  # salient but no description covers it: no label (never guessed)
        text=captions[own[0]['region_id']] if s>thr else BACKGROUND
        out.append((t['region_id'],tile_features(im.crop(tuple(t['box'])),cfg['tile_px']),text,round(s,4)))
    return out

def thumbnail(im,n=8):
    np=_np();return np.asarray(im.convert('L').resize((n,n)),dtype=np.float32).ravel()/255.

# ---------------------------------------------------------------- text side of the alignment
WORD=re.compile(r"[a-zäöüß]+")
def hashed_embed(text,dim=256):
    """Deterministic signed hashing of words and word bigrams, L2-normalised (fallback text encoder)."""
    np=_np();v=np.zeros(dim,dtype=np.float32);w=WORD.findall(text.lower())
    for t in w+[a+' '+b for a,b in zip(w,w[1:])]:
        hsh=zlib.crc32(t.encode());v[hsh%dim]+=1. if hsh>>31 else -1.
    n=float(np.linalg.norm(v));return v/n if n else v

def text_encoder(runtime=None,cfg=DEFAULTS):
    """(name, callable texts->array): EmbeddingGemma when installed, else hashed bag of words."""
    np=_np()
    if runtime is not None:
        from .semantic_memory import EmbeddingEncoder
        enc=EmbeddingEncoder(runtime.home,runtime.models,runtime.cfg)
        if enc.installed():
            def call(texts):
                v=np.asarray(enc(list(texts),None,time.monotonic()+600),dtype=np.float32);return v/np.maximum(1e-8,np.linalg.norm(v,axis=1,keepdims=True))
            return 'embedding:'+str(enc.revision()),call
    return 'hashed_bow',lambda texts:np.stack([hashed_embed(t,cfg['hash_dim']) for t in texts])

# ---------------------------------------------------------------- student projector (learnable) + measurements
class Projector:
    """Standardised features -> ridge regression -> normalised text-embedding space. Closed form, refittable."""
    def __init__(self,ridge=1.):self.ridge=ridge;self.mu=self.sd=self.W=None;self.n=0
    def _x(self,X):
        np=_np();X=(np.asarray(X,dtype=np.float64)-self.mu)/self.sd;return np.hstack([X,np.ones((len(X),1))])
    def fit(self,X,Y):
        np=_np();X=np.asarray(X,dtype=np.float64);Y=np.asarray(Y,dtype=np.float64)
        self.mu=X.mean(0);self.sd=X.std(0)+1e-6;A=self._x(X);reg=self.ridge*np.eye(A.shape[1]);reg[-1,-1]=0.
        self.W=np.linalg.solve(A.T@A+reg,A.T@Y);self.n=len(X);return self
    def __call__(self,X):
        np=_np();Z=self._x(X)@self.W;return Z/np.maximum(1e-8,np.linalg.norm(Z,axis=1,keepdims=True))
    def save(self,path):
        np=_np();buf=io.BytesIO();np.savez(buf,mu=self.mu,sd=self.sd,W=self.W,meta=np.array([self.ridge,self.n]));atomic_write(Path(path),buf.getvalue())
        return digest(buf.getvalue())
    @classmethod
    def load(cls,path,sha=None):
        np=_np();b=Path(path).read_bytes()
        if sha and digest(b)!=sha:raise ValueError('Projektor-Hash falsch')
        d=np.load(io.BytesIO(b));p=cls(float(d['meta'][0]));p.mu,p.sd,p.W,p.n=d['mu'],d['sd'],d['W'],int(d['meta'][1]);return p

def retrieval(Z,Y):
    """Top-1 accuracy of picking the right caption embedding for each image among all captions, plus mean cosine."""
    np=_np();S=np.asarray(Z)@np.asarray(Y).T;n=len(S)
    return {'top1':float((S.argmax(1)==np.arange(n)).mean()) if n else 0.,'chance':1./n if n else 0.,'mean_cosine':float(np.diag(S).mean()) if n else 0.}

def crossval(X,Y,thumbs=None,folds=4,ridge=1.):
    """K-fold held-out alignment (retrieval among held-out captions) and reconstruction (measurement only)."""
    np=_np();X=np.asarray(X);Y=np.asarray(Y);n=len(X);idx=np.arange(n);top=[];cos=[];rec=[];base=[]
    if n<2*folds:folds=max(2,n//2)
    for k in range(folds):
        te=idx[k::folds];tr=np.setdiff1d(idx,te)
        if len(tr)<2 or not len(te):continue
        p=Projector(ridge).fit(X[tr],Y[tr]);m=retrieval(p(X[te]),Y[te]);top.append(m['top1']*len(te));cos.append(m['mean_cosine']*len(te))
        if thumbs is not None:
            T=np.asarray(thumbs);d=Projector(ridge).fit(p(X[tr]),T[tr]);Zte=p(X[te])
            pred=(d._x(Zte)@d.W);rec.append(float(((pred-T[te])**2).mean())*len(te));base.append(float(((T[tr].mean(0)-T[te])**2).mean())*len(te))
    out={'n':n,'folds':folds,'held_out_top1':sum(top)/n,'chance':folds/n,'held_out_mean_cosine':sum(cos)/n}
    if rec:out['reconstruction']={'mse':sum(rec)/n,'mean_image_mse':sum(base)/n,'ratio':(sum(rec)/max(1e-12,sum(base))),'authority':'MEASUREMENT_ONLY'}
    return out

# ---------------------------------------------------------------- TEACHER EYE
class Teacher:
    """Frozen VLM via llama-mtmd-cli; one process per call (no resident RAM between lab calls)."""
    def __init__(self,home,models=None,cfg=DEFAULTS,binary=None,model=None,mmproj=None):
        self.home=Path(home);self.cfg=cfg;self.models=models
        self.binary=binary or os.environ.get('V13_LLAMA_MTMD',str(self.home/'bin/llama-mtmd-cli'));self.model=model;self.mmproj=mmproj;self.revision=None
        if models is not None and model is None:
            s=models.installed.get('vision')
            if s and s.get('download_complete'):
                f=s['files'];self.model=self.home/f[s['main_file']]['path'];self.revision=s['exact_revision']
                self.mmproj=next((self.home/v['path'] for k,v in f.items() if k.startswith('mmproj')),None)
    def available(self):
        missing=[n for n,p in (('llama-mtmd-cli',self.binary),('Modell',self.model),('mmproj',self.mmproj)) if not p or not Path(p).is_file()]
        return (not missing,missing)
    def describe(self,im,prompt=PROMPT,cancel=None):
        ok,missing=self.available()
        if not ok:raise Unavailable('Vision-Teacher fehlt: '+', '.join(missing)+'; :download vision')
        tmp=Path(tempfile.mkdtemp(prefix='v13-vis-'));path=tmp/'img.png';im.save(path)
        cmd=[str(self.binary),'-m',str(self.model),'--mmproj',str(self.mmproj),'--image',str(path),'-p',prompt,'-n',str(self.cfg['teacher_tokens']),
             '--temp','0','-t',str(self.cfg['threads']),'--no-warmup','-c','4096']
        t0=time.monotonic()
        try:
            p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=dict(os.environ,LLAMA_ARG_NO_MMPROJ_AUTO='1'))
            deadline=t0+self.cfg['teacher_timeout']
            while p.poll() is None:
                if (cancel and cancel.is_set()) or time.monotonic()>deadline:
                    p.kill();p.wait();raise Unavailable('Vision-Teacher abgebrochen/Zeitlimit')
                time.sleep(.05)
            out=p.stdout.read().decode(errors='replace').strip()
            if p.returncode or not out:raise Unavailable('Vision-Teacher ohne Antwort (rc=%s)'%p.returncode)
        finally:
            path.unlink(missing_ok=True);tmp.rmdir()
        return {'text':' '.join(out.split())[:600],'authority':AUTHORITY,'teacher':'LFM2.5-VL-450M','revision':self.revision,'prompt':prompt,'seconds':round(time.monotonic()-t0,2)}

# ---------------------------------------------------------------- lab state + operator surface
def load(store):return store.state(KEY,None)[0] or {'revision':REVISION,'images':{},'projector':None,'last':None}
def save(store,st):store.set_state(KEY,st)

def _find(st,arg):
    if arg in (None,'last'):
        if not st['images']:raise ValueError('Noch kein Bild; :image add <Pfad>')
        return max(st['images'].values(),key=lambda r:r['created'])
    for sid,rec in st['images'].items():
        if sid==arg or sid.startswith(arg) or rec['ref']['sha256'].startswith(arg):return rec
    raise ValueError('Unbekanntes Bild: '+arg)

def describe(runtime,rec,region='g',teacher=None,cfg=DEFAULTS):
    if load(runtime.store).get('teacher_removed'):raise Unavailable('Vision-Teacher entfernt (:image teacher on stellt ihn wieder her); look/locate/find arbeiten ohne ihn')
    reg=next((r for r in rec['regions'] if r['region_id']==region),None)
    if reg is None:raise ValueError('Region g, hl/hr/ht/hb, qtl/qtr/qbl/qbr oder r00..r%d%d'%(cfg['grid']-1,cfg['grid']-1))
    ref=region_ref(rec['ref'],reg);teacher=teacher or Teacher(runtime.home,runtime.models,cfg)
    cap=teacher.describe(read_image(runtime.store,ref,cfg),cancel=getattr(runtime,'cancel_event',None))|{'source_ref':ref,'created':now()}
    st=load(runtime.store);cur=st['images'][rec['ref']['source_id']]
    cur['captions']=[c for c in cur['captions'] if c['source_ref'].get('region_id')!=region]+[cap];save(runtime.store,st)
    runtime.store.log('vision',None,{'action':'describe','authority':AUTHORITY,'seconds':cap['seconds']});return cap

def dataset(store,cfg=DEFAULTS):
    """(features, captions, thumbnails, keys) of every described region (whole image and crops). Each region is its
    own training pair (crop features -> caption of that crop), so place enters through region provenance."""
    np=_np();X=[];caps=[];T=[];ids=[]
    for sid,rec in load(store)['images'].items():
        for cap in rec['captions']:
            im=read_image(store,cap['source_ref'],cfg);X.append(features(im,cfg));caps.append(cap['text']);T.append(thumbnail(im,cfg['thumb']))
            ids.append(sid+':'+cap['source_ref'].get('region_id','g'))
    return np.asarray(X),caps,np.asarray(T),ids

def train(runtime,encoder=None,cfg=DEFAULTS):
    X,caps,T,ids=dataset(runtime.store,cfg)
    if len(X)<cfg['min_train']:raise ValueError('Zu wenig beschriebene Bilder (%d < %d); erst :image describe'%(len(X),cfg['min_train']))
    name,enc=encoder or text_encoder(runtime,cfg);Y=enc(caps);cv=crossval(X,Y,T,ridge=cfg['ridge'])
    p=Projector(cfg['ridge']).fit(X,Y);path=runtime.home/'data/vision'/('projector-'+uid('vis')[4:]+'.npz');sha=p.save(path)
    st=load(runtime.store);old=st.get('projector')
    st['projector']={'path':str(path.relative_to(runtime.home)),'sha256':sha,'n':len(X),'encoder':name,'metrics':cv,'created':now(),
                     'captions':{sid:c for sid,c in zip(ids,caps)},'authority':'LAB_SHADOW_ONLY'}
    save(runtime.store,st)
    if old and old['path']!=st['projector']['path']:(runtime.home/old['path']).unlink(missing_ok=True)
    runtime.store.log('vision',None,{'action':'train','n':len(X),'encoder':'embedding' if name.startswith('embedding') else 'hashed_bow','value':round(cv['held_out_top1'],4)})
    return st['projector']

def look(runtime,rec,encoder=None,cfg=DEFAULTS,k=3):
    """Student guess: nearest known teacher captions for this image by the projector alone (no teacher call)."""
    np=_np();st=load(runtime.store);pj=st.get('projector')
    if not pj:raise ValueError('Noch kein Projektor; :image train')
    p=Projector.load(runtime.home/pj['path'],pj['sha256']);name,enc=encoder or text_encoder(runtime,cfg)
    if name!=pj['encoder']:raise ValueError('Text-Encoder hat gewechselt (%s -> %s); :image train'%(pj['encoder'],name))
    z=p(features(read_image(runtime.store,rec['ref'],cfg),cfg)[None])[0];items=list(pj['captions'].items());Y=enc([c for _,c in items]);s=Y@z
    order=np.argsort(-s)[:k]
    return {'authority':STUDENT,'source_ref':rec['ref'],'nearest':[{'region':items[i][0],'caption':items[i][1],'cosine':round(float(s[i]),4)} for i in order]}

def locate(runtime,rec,text,encoder=None,cfg=DEFAULTS,k=3):
    """Student grounding without the teacher: score every region crop against a text query, best first, each with
    its region SourceRef (STUDENT_ESTIMATE; the pixels behind the ref are the evidence, not the score)."""
    np=_np();st=load(runtime.store);pj=st.get('projector')
    if not pj:raise ValueError('Noch kein Projektor; :image train')
    if not text.strip():raise ValueError(':image locate <id|last> <Text>')
    p=Projector.load(runtime.home/pj['path'],pj['sha256']);name,enc=encoder or text_encoder(runtime,cfg)
    if name!=pj['encoder']:raise ValueError('Text-Encoder hat gewechselt (%s -> %s); :image train'%(pj['encoder'],name))
    regs=[r for r in rec['regions'] if r['region_id']!='g'];refs=[region_ref(rec['ref'],r) for r in regs]
    Z=p(np.stack([features(read_image(runtime.store,ref,cfg),cfg) for ref in refs]));s=Z@enc([text])[0]
    return {'authority':STUDENT,'query':text[:200],'regions':[{'source_ref':refs[i],'cosine':round(float(s[i]),4)} for i in np.argsort(-s)[:k]]}

def tile_dataset(store,cfg=DEFAULTS):
    """(tile features, texts, keys) from every image with at least one caption (WP-T16 weak tile labels)."""
    np=_np();X=[];texts=[];keys=[]
    for sid,rec in load(store)['images'].items():
        caps={c['source_ref'].get('region_id','g'):c['text'] for c in rec['captions']}
        if not caps:continue
        im=read_image(store,rec['ref'],cfg)
        for tid,f,text,_ in tile_pairs(im,rec['regions'],caps,cfg):X.append(f);texts.append(text);keys.append(sid+':'+tid)
    return np.asarray(X),texts,keys

def train_tiles(runtime,encoder=None,cfg=DEFAULTS):
    X,texts,keys=tile_dataset(runtime.store,cfg)
    if len(set(texts)-{BACKGROUND})<2 or len(X)<cfg['min_train']:raise ValueError('Zu wenig beschriebene Bildbereiche für Kacheln; erst :image describe (g, Hälften, Quadranten)')
    name,enc=encoder or text_encoder(runtime,cfg);uniq=sorted(set(texts));E=dict(zip(uniq,enc(uniq)));Y=_np().stack([E[t] for t in texts])
    p=Projector(cfg['ridge']).fit(X,Y);path=runtime.home/'data/vision'/('tiles-'+uid('vis')[4:]+'.npz');sha=p.save(path)
    st=load(runtime.store);old=st.get('tile_projector')
    st['tile_projector']={'path':str(path.relative_to(runtime.home)),'sha256':sha,'n':len(X),'encoder':name,'created':now(),
                          'salient_tiles':sum(t!=BACKGROUND for t in texts),'authority':'LAB_SHADOW_ONLY'}
    save(runtime.store,st)
    if old and old['path']!=st['tile_projector']['path']:(runtime.home/old['path']).unlink(missing_ok=True)
    runtime.store.log('vision',None,{'action':'train_tiles','n':len(X),'encoder':'embedding' if name.startswith('embedding') else 'hashed_bow'})
    return st['tile_projector']

def tile_scores(p,im,regions,query_vec,background_vec,cfg=DEFAULTS):
    """Per tile: cosine to the query minus cosine to BACKGROUND (a tile must look more like the query than like nothing)."""
    np=_np();tiles=[r for r in regions if r['region_id'][0]=='r']
    Z=p(np.stack([tile_features(im.crop(tuple(t['box'])),cfg['tile_px']) for t in tiles]))
    return tiles,Z@query_vec-Z@background_vec

def find(runtime,rec,text,encoder=None,cfg=DEFAULTS,k=3):
    """WP-T16 student grounding per tile (no teacher): 4x4 heat map + best tiles with their region SourceRefs."""
    np=_np();st=load(runtime.store);pj=st.get('tile_projector')
    if not pj:raise ValueError('Noch kein Kachel-Projektor; :image tiles')
    if not text.strip():raise ValueError(':image find <id|last> <Text>')
    p=Projector.load(runtime.home/pj['path'],pj['sha256']);name,enc=encoder or text_encoder(runtime,cfg)
    if name!=pj['encoder']:raise ValueError('Text-Encoder hat gewechselt (%s -> %s); :image tiles'%(pj['encoder'],name))
    q,b=enc([text,BACKGROUND]);tiles,s=tile_scores(p,read_image(runtime.store,rec['ref'],cfg),rec['regions'],q,b,cfg)
    g=cfg['grid'];heat=[[None]*g for _ in range(g)]
    for t,v in zip(tiles,s):heat[int(t['region_id'][1])][int(t['region_id'][2])]=round(float(v),3)
    return {'authority':STUDENT,'query':text[:200],'heat':heat,'tiles':[{'source_ref':region_ref(rec['ref'],tiles[i]),'score':round(float(s[i]),4)} for i in np.argsort(-s)[:k]]}

def teacher_switch(store,on):
    st=load(store);st['teacher_removed']=not on;save(store,st);return {'teacher':'on' if on else 'removed'}

def forget(store,rec):
    st=load(store);sid=rec['ref']['source_id'];st['images'].pop(sid,None)
    if st.get('projector'):st['projector']['captions']={k:v for k,v in st['projector']['captions'].items() if k.split(':')[0]!=sid}
    save(store,st)
    with store.tx() as c:c.execute('UPDATE sources SET deleted=1 WHERE id=?',(sid,))
    if not store.one('SELECT id FROM sources WHERE hash=? AND deleted=0',(rec['ref']['sha256'],)):(store.home/'data/blobs'/rec['ref']['sha256']).unlink(missing_ok=True)
    return {'forgotten':sid}

def status(runtime):
    st=load(runtime.store);t=Teacher(runtime.home,runtime.models);ok,missing=t.available();pj=st.get('projector');tp=st.get('tile_projector')
    return {'revision':REVISION,'scope':'LAB_SHADOW_ONLY (Age-0-Kern bleibt Text)','images':len(st['images']),
            'described':sum(1 for r in st['images'].values() if r['captions']),'teacher':{'available':ok,'missing':missing,'authority':AUTHORITY,'removed':bool(st.get('teacher_removed'))},
            'projector':{k:pj[k] for k in ('n','encoder','metrics','created')} if pj else None,
            'tile_projector':{k:tp[k] for k in ('n','salient_tiles','encoder','created')} if tp else None}

def operator_command(runtime,args):
    """:image [status|add <Pfad> [Label]|list|describe [id|last] [g|rIJ|hl|hr|ht|hb|qtl|qtr|qbl|qbr]|train|tiles|look [id|last]|locate <id|last> <Text>|find <id|last> <Text>|teacher on|off|forget <id>]"""
    a=args[0] if args else 'status'
    if a=='status':return status(runtime)
    if a=='add':
        if len(args)<2:raise ValueError(':image add <Pfad> [Label]')
        p=Path(args[1]).expanduser()
        if not p.is_file():raise ValueError('Datei fehlt: '+str(p))
        rec=ingest(runtime.store,p.read_bytes(),label=' '.join(args[2:]) or p.name);runtime.store.log('vision',None,{'action':'add','width':rec['size'][0],'height':rec['size'][1]})
        f=features(read_image(runtime.store,rec['ref']))
        return {'source_ref':rec['ref'],'size':rec['size'],'regions':len(rec['regions']),'raw_eye_dim':int(f.shape[0]),'next':':image describe '+rec['ref']['source_id']}
    if a=='list':return [{'source_id':s,'label':r['label'],'size':r['size'],'captions':len(r['captions'])} for s,r in load(runtime.store)['images'].items()]
    if a=='describe':return describe(runtime,_find(load(runtime.store),args[1] if len(args)>1 else None),args[2] if len(args)>2 else 'g')
    if a=='train':return train(runtime)
    if a=='tiles':return train_tiles(runtime)
    if a=='find':
        if len(args)<3:raise ValueError(':image find <id|last> <Text>')
        return find(runtime,_find(load(runtime.store),args[1]),' '.join(args[2:]))
    if a=='teacher':
        if len(args)!=2 or args[1] not in ('on','off'):raise ValueError(':image teacher on|off')
        return teacher_switch(runtime.store,args[1]=='on')
    if a=='look':return look(runtime,_find(load(runtime.store),args[1] if len(args)>1 else None))
    if a=='locate':
        if len(args)<3:raise ValueError(':image locate <id|last> <Text>')
        return locate(runtime,_find(load(runtime.store),args[1]),' '.join(args[2:]))
    if a=='forget':
        if len(args)!=2:raise ValueError(':image forget <id>')
        return forget(runtime.store,_find(load(runtime.store),args[1]))
    raise ValueError(':image [status|add <Pfad>|list|describe [id] [g|rIJ|hl|hr|ht|hb|qtl|qtr|qbl|qbr]|train|tiles|look [id]|locate <id> <Text>|find <id> <Text>|teacher on|off|forget <id>]')
