"""WP-G (G1B part) / §1.2.2, §17.6, G1B: B2 gist grouping with Age-dependent, situation-flexible resolution.

B1 Detail keeps ~1 native token per fine slot (its 240-char source window). B2 Gist reads the source as groups of
~tokens_per_group native-token-equivalents in up to GIST_SLOTS active slots. The group size comes from
age.gist_resolution: Age/maturity may widen it, but novelty, conflict (re-entry with a peer message), literal/code input
and low boundary confidence narrow it again (§17.6: Age up != group size monotone up).

Grouping is readout scheduling, not a tokenizer change (§1.2.3): token-equivalents are estimated from text, and every
group carries its exact SourceRef span, so a gist slot points back to the exact/fine source without loss (G1B).
Boundary-aware grouping (cut at sentence/clause ends within 0.6..1.5 x size) is compared against fixed grouping by
`scripts/gist_grouping_bench.py`. When a long text needs more than GIST_SLOTS groups, the oldest groups are merged
first, so recent context stays fine and old context becomes coarser (multiscale), never dropped.

SHADOW (default): the plan is recorded in the B2 QueryPacket only. ACTIVE (`:gist active`, explicit human): B2 receives
`gist_slots` instead of the 960-char source segments.
"""
import math
import re
from .common import dumps

KEY='G1B_GIST';REVISION='g1b-gist-v1'
TOKEN=re.compile(r'\w+|[^\w\s]',re.U)
SENT_END=set('.!?');CLAUSE_END=set(',;:')
CODE=re.compile(r'```|`[^`]+`|\bdef |\bclass |[{}]|=>|\w+\.\w+\(')
LOW_MIN=.6;HIGH_MAX=1.5          # BOOT boundary window around the target size
LOW_CONFIDENCE=.5                # BOOT: below this mean boundary confidence the resolution narrows

def token_equivalents(text):
    """[(start, end, units)] with a rough BPE-like count: one unit per ~5 letters of a word, one per symbol."""
    return [(m.start(),m.end(),max(1,math.ceil(len(m.group(0))/5)) if m.group(0)[0].isalnum() or m.group(0)[0]=='_' else 1) for m in TOKEN.finditer(text)]

def _boundary(text,end):
    ch=text[end-1]
    nxt=text[end:end+2]
    if ch in SENT_END and (not nxt or nxt[0].isspace()):return 1.
    if '\n' in text[end:end+1]:return .9
    if ch in CLAUSE_END:return .7
    return .3

def group(text,ref,size,mode='boundary'):
    toks=token_equivalents(text);groups=[];cur=[];units=0
    inside=set()
    if mode!='fixed':  # boundary-aware grouping never cuts through an exact span (number, date, code, URL, quote)
        from .context_os import exact_spans
        for sp in exact_spans(text):
            for m in re.finditer(re.escape(sp),text):inside.update(range(m.start()+1,m.end()))
    def close(conf):
        nonlocal cur,units
        s,e=cur[0][0],cur[-1][1]
        groups.append({'text':text[s:e],'source_ref':dict(ref,char_start=ref['char_start']+s,char_end=ref['char_start']+e),'units':units,'boundary':conf,'scale':1})
        cur=[];units=0
    for i,t in enumerate(toks):
        cur.append(t);units+=t[2]
        nxt=toks[i+1] if i+1<len(toks) else None
        glued=nxt is not None and nxt[0]==t[1] and not text[nxt[0]].isalnum()  # never split a word from its own punctuation
        if mode=='fixed':
            if units>=size and not glued:close(_boundary(text,t[1]))
            continue
        b=_boundary(text,t[1])
        if glued or t[1] in inside and units<size*HIGH_MAX*2:continue
        if units>=size*HIGH_MAX:close(b)
        elif units>=size*LOW_MIN and b>=.7 and (b==1. or units>=size):close(b)
    if cur:close(1.)
    return groups

def fit_slots(groups,slots):
    """Merge the oldest adjacent groups until the count fits; recent groups keep their fine scale."""
    g=list(groups);i=0
    while len(g)>slots:
        a,b=g[i],g[i+1]
        g[i:i+2]=[{'text':None,'source_ref':dict(a['source_ref'],char_end=b['source_ref']['char_end']),'units':a['units']+b['units'],
                   'boundary':b['boundary'],'scale':a['scale']+b['scale'],'min_boundary':min(a.get('min_boundary',a['boundary']),b.get('min_boundary',b['boundary'])),
                   'parts':a.get('parts',[a['source_ref']])+b.get('parts',[b['source_ref']])}]
        i+=1
        if i>=len(g)-1:i=0
    return g

def plan(text,ref,resolution,mode='boundary'):
    size=resolution['tokens_per_group'];slots=resolution['slots']
    raw=group(text,ref,size,mode);fitted=fit_slots(raw,slots)
    base=ref['char_start']
    for x in fitted:
        if x['text'] is None:x['text']=text[x['source_ref']['char_start']-base:x['source_ref']['char_end']-base]
    rate=sum(x['boundary']>=.7 for x in raw)/len(raw) if raw else 1.
    return {'slots':[{'slot':i,'text':x['text'],'source_ref':x['source_ref'],'scale':x['scale'],'units':x['units']}|coupling(x) for i,x in enumerate(fitted)],
            'groups_raw':len(raw),'boundary_rate':round(rate,3),'mean_boundary':round(sum(x['boundary'] for x in raw)/len(raw),3) if raw else 1.,
            'tokens_per_group':size,'max_slots':slots,'coarsened':len(raw)>len(fitted)}

def coupling(x):
    """§3.2A fields of one gist slot: fine spans it covers, covered range, compression, boundary confidence, fallback."""
    from .context_os import exact_spans
    r=x['source_ref'];exact=bool(exact_spans(x['text'] or ''))
    return {'source_span_refs':x.get('parts',[r]),'covered':{'source_id':r.get('source_id'),'char_start':r['char_start'],'char_end':r['char_end']},
            'compression_ratio':round(float(x['units']),2),'boundary_confidence':round(x.get('min_boundary',x['boundary']),3),
            'fallback':'EXACT_STORE' if exact else 'B1_DETAIL'}

LOCAL_PAD_UNITS=16   # BOOT: fine context added on each side of a detail span for a provisional local gist
LOCAL_MAX_UNITS=96   # BOOT: a local bundle stays small (detail keeps its preferred time scale)

def local_bundle(text,ref,spans,pad=LOCAL_PAD_UNITS,max_units=LOCAL_MAX_UNITS):
    """§3.2A reverse direction: A/B1 bundles neighbouring fine groups around detail spans (offsets relative to text) into
    provisional local gists. Never replaces the fine view; authority PROVISIONAL_LOCAL_GIST, fallback B1_DETAIL."""
    from .age import GIST_FINE
    fine=group(text,ref,GIST_FINE,'boundary');base=ref['char_start'];out=[];used=set()
    for a,b in sorted(spans):
        idx=[i for i,g in enumerate(fine) if g['source_ref']['char_start']-base<b and a<g['source_ref']['char_end']-base]
        if not idx:continue
        lo,hi=idx[0],idx[-1];units=sum(fine[i]['units'] for i in range(lo,hi+1));left=right=0
        while lo>0 and left<pad and units+fine[lo-1]['units']<=max_units:lo-=1;left+=fine[lo]['units'];units+=fine[lo]['units']
        while hi<len(fine)-1 and right<pad and units+fine[hi+1]['units']<=max_units:hi+=1;right+=fine[hi]['units'];units+=fine[hi]['units']
        if (lo,hi) in used:continue
        used.add((lo,hi));part=fine[lo:hi+1];s0=part[0]['source_ref']['char_start'];e0=part[-1]['source_ref']['char_end']
        out.append({'text':text[s0-base:e0-base],'source_ref':dict(ref,char_start=s0,char_end=e0),'source_span_refs':[g['source_ref'] for g in part],
                    'covered':{'source_id':ref.get('source_id'),'char_start':s0,'char_end':e0},'compression_ratio':round(float(units),2),
                    'boundary_confidence':round(min(g['boundary'] for g in part),3),'fallback':'B1_DETAIL','provisional':True,
                    'authority':'PROVISIONAL_LOCAL_GIST','origin':'A_LOCAL_BUNDLE'})
    return out

def resolve(age,text,novelty=0.,conflict=False):
    """Age-dependent size, narrowed by literal/code text and, after a first pass, by low boundary confidence."""
    literal=bool(CODE.search(text))
    if age is None:
        from .age import GIST_BASE,GIST_FINE,GIST_SLOTS
        res={'tokens_per_group':GIST_FINE if literal else GIST_BASE[0],'slots':GIST_SLOTS,'stage':0}
    else:res=age.gist_resolution('language',novelty=novelty,conflict=conflict,literal=literal)
    return dict(res,literal=literal,novelty=novelty,conflict=conflict)

class Gist:
    def __init__(self,store,age=None):self.s=store;self.age=age
    def mode(self):
        st=self.s.state(KEY,None)[0] or {'revision':REVISION,'mode':'SHADOW'}
        if st.get('revision')!=REVISION:raise ValueError('Gist state revision mismatch')
        return st['mode']
    def set_mode(self,mode,authority='SYSTEM'):
        if mode not in {'SHADOW','ACTIVE'}:raise ValueError('SHADOW|ACTIVE')
        if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
        st,v=self.s.state(KEY,None);self.s.set_state(KEY,{'revision':REVISION,'mode':mode},expected=v);return mode
    def build(self,text,ref,novelty=0.,conflict=False):
        res=resolve(self.age,text,novelty,conflict);p=plan(text,ref,res)
        if p['mean_boundary']<LOW_CONFIDENCE and self.age is not None:  # §17.6 low boundary confidence refines temporarily
            res=dict(self.age.gist_resolution('language',novelty=novelty,conflict=conflict,literal=res['literal'],boundary_confidence=p['mean_boundary']),literal=res['literal'],novelty=novelty,conflict=conflict)
            p=plan(text,ref,res)
        p['resolution']=res;return p
    def report(self,sample=None):
        out={'revision':REVISION,'mode':self.mode(),'claim_limit':'Readout grouping only; native tokenizers unchanged; downstream utility not yet measured'}
        if sample:
            p=self.build(sample,{'source_id':'preview','sha256':'0'*64,'char_start':0,'char_end':len(sample),'modality':'text'})
            out['preview']={k:p[k] for k in ('tokens_per_group','max_slots','groups_raw','boundary_rate','coarsened','resolution')}|{'slots':[{'text':x['text'],'scale':x['scale']} for x in p['slots']]}
        return out

def for_offer(runtime,text,ref,conflict):
    """cognition.offer hook for B2: returns (plan_summary, slots or None). Fail-open."""
    try:
        from .age import controller as age_controller
        g=Gist(runtime.store,age_controller(runtime));p=g.build(text,ref,conflict=conflict);active=g.mode()=='ACTIVE'
        summary={k:p[k] for k in ('tokens_per_group','max_slots','groups_raw','boundary_rate','coarsened')}|{'slots':len(p['slots']),'stage':p['resolution'].get('stage'),
                 'slot_coupling':[{k:x[k] for k in ('covered','compression_ratio','boundary_confidence','fallback')}|{'fine_spans':len(x['source_span_refs'])} for x in p['slots']],
                 'literal':p['resolution']['literal'],'conflict':conflict,'applied':active}
        return summary,([{'slot':x['slot'],'text':x['text'],'source_ref':x['source_ref'],'scale':x['scale']} for x in p['slots']] if active else None)
    except Exception as exc:
        runtime.store.log('gist_unavailable',None,{'error':type(exc).__name__});return None,None

def operator_command(r,args):
    """:gist [status|shadow|active|preview <Text>|readout [fixed|text|native|hybrid]|similar [1..5]]"""
    if args and args[0]=='similar':
        from .gist_similarity import operator_command as similarity_command
        return similarity_command(r,args[1:])
    if args and args[0]=='readout':
        from .gist_readout import operator_command as readout_command
        return readout_command(r,args[1:])
    from .age import controller as age_controller
    g=Gist(r.store,age_controller(r))
    if not args or args==['status']:return dumps(g.report())
    if args==['shadow']:return dumps({'mode':g.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':g.set_mode('ACTIVE','EXPLICIT_HUMAN')})
    if args[0]=='preview' and len(args)>1:return dumps(g.report(' '.join(args[1:])))
    raise ValueError(':gist [status|shadow|active|preview <Text>|readout [fixed|text|native|hybrid]|similar [1..5]]')
