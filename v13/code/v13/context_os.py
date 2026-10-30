"""WP-N7 / §8.3-8.6, §9.1, §74, G6/G6B: Context OS and adaptive cache policy.

Context is not one growing chat string (§8.3). Every turn the Context OS builds an explicit plan over layers

  EXACT_PINNED     system/conduct/answer rules + operator rules: never compressed, never reordered
  RAW_HISTORY      recent source-valid turns, verbatim (CTX.exact_recent_pin of the window is pinned)
  COMPRESSED       older turns as extractive summaries that keep every exact span (numbers, code, quotes, URLs)
  SOURCE_LINKS     turns left out of the model view; their SourceRefs stay in the answer lineage
  ACTIVE_VIEW      recalled memories (exact corrections) + warm reactivations (§9.1 Warm/activity-silent)
  HYPOTHESES       selected B1/B2 offers (never facts)
  LATENT_STATE     executive task context
  MEMORY_POINTERS  warm memory ids that stay silent (cheaply reactivatable, not shown)
  ARCHIVE          everything older than the history window (counted only)

The policy changes only the *active view*, never a source (§8.3): compression is derived text pointing back to the
unchanged source, and a compressed item is restored exactly (§8.4) when the query needs evidence, numbers, code,
literal wording or a conflict is open. Cache handling is a control action (§8.5): the `stable_prefix` layout keeps the
pinned prefix and the history byte-identical across turns and moves the volatile layers behind the history, so the
runner's prompt cache (llama.cpp `cache_prompt`) can reuse the KV state ("re-entry instead of re-prefill"). Moving
volatile context behind the history needs the chat template to accept two consecutive user messages; that is a
declared body capability (G6B), probed with `:ctxos probe <role>`, never assumed. Without it the layout stays legacy.

Modes: SHADOW (default, Age 0) computes and logs the plan and the counterfactual prefix reuse next to the legacy
context, which is what the model sees. ACTIVE (explicit human `:ctxos active`) hands the planned messages to the
runner. The learned raw-vs-compressed prior (§8.4 "lernbar") has its own SHADOW/ACTIVE switch, like WP-N5.
Every plan touches the WP-N10 eligibility of path `context_policy`; measured prefill reuse becomes a cost modulator.
No native attention/KV geometry is patched (§8.5, §8.6.6); full KV stays the fallback. All numbers are §74 starts or
marked BOOT, not measured optima.
"""
import math
import re
from .common import dumps,digest
from .contracts import packet
from .neuromod import step

KEY='N7_CONTEXT_OS';REVISION='n7-context-os-v1';PATH='context_policy'
CTX={'exact_recent_pin':.80,'global_compact_state':.60,'reconstruct_disposable_cache':.40,'long_context_block_index':.45,
     'prefetch_gain':.30,'cache_compression_aggressiveness':.35}  # §74 start values
# Raising these (or lowering exact_recent_pin) is allowed only while exact-span recall stays stable (§74).
RISKY_UP={'global_compact_state','reconstruct_disposable_cache','cache_compression_aggressiveness','long_context_block_index'}
RISKY_DOWN={'exact_recent_pin'}
RECALL_STABLE=.98;RECALL_MIN_PLANS=20;RECALL_WINDOW=50  # BOOT
LAYERS=('EXACT_PINNED','RAW_HISTORY','COMPRESSED','SOURCE_LINKS','ACTIVE_VIEW','HYPOTHESES','LATENT_STATE','MEMORY_POINTERS','ARCHIVE')
FORMS=('RAW','COMPRESSED','POINTER')
LAYOUTS=('legacy','stable_prefix','append_only')
TRANSCRIPT_MAX_CHARS=64000  # BOOT cap on the stored per-role transcript
CAPABILITIES=('consecutive_user',)
CHARS_PER_TOKEN=3.0          # BOOT conservative estimate; the runner still trims on exact token counts
MAX_CACHE_METRIC_TOKENS=2**31-1  # defensive bound; no bool/negative/float native cost credit
EXACT_NEED={'numbers':.5,'code':.65,'literal':.8,'source_critique':.6,'conflict':.7}  # BOOT §8.4 trigger strengths
CONFLICT_VERDICTS={'CONTESTED','VIOLATION','SOURCE_LOSS'}
WARM_DECAY=.6;WARM_MIN=.15;WARM_MAX=16;WARM_ADMIT=.5;WARM_PREFETCH_MAX=2  # BOOT §9.1 warm set per experience event
SUMMARY_USER=140;SUMMARY_ASSISTANT=200;SPAN_MAX=12;SPAN_CHARS=400  # BOOT compression shape
LEARNED_MAX=.25;POLICY_RATE=.2;LEARNED_MIN_N=3  # BOOT, as WP-N5
VOLATILE_HEAD='Context for the next message (reference material, not a question):'
CODE=re.compile(r'```[\s\S]*?```|`[^`\n]+`')
QUOTE=re.compile(r'"[^"]+"|„[^“]+“')  # bounded by SPAN_CHARS/RAW fallback, not silent truncation
SINGLE_QUOTE=re.compile(r"(?<!\w)'(?:[^'\n]|(?<=\w)'(?=\w)){1,400}'(?!\w)")
# Paired typographic delimiters: German „...” closes with U+201C,
# the glyph that opens English “...”. Inspect German pairs first.
GERMAN_PAIR=re.compile(r'„[^“]+“')
EN_CURLY=re.compile(r'“[^”]+”')
FR_QUOTE=re.compile(r'«[^»]+»')
CURLY_SINGLE=re.compile(r"(?<!\w)‘(?:[^’\n]|(?<=\w)’(?=\w)){1,400}’(?!\w)")
URL=re.compile(r'https?://\S+')
NUMBER=re.compile(r'(?<![\w.])[-+]?\d[\d.,:/-]*\d(?:%|[a-zA-Z]{0,3})?|(?<![\w.])\d(?:%|[a-zA-Z]{0,3})?(?![\w])')
LITERAL=re.compile(r'\b(exact(ly)?|verbatim|literal(ly)?|word for word|quote|exakt|wörtlich|genau so|zitier\w*|wortgleich)\b',re.I)
CRITIQUE=re.compile(r'\b(source|sources|according to|cite|citation|evidence|proof|quelle\w*|laut|beleg\w*|nachweis\w*)\b',re.I)
CODEISH=re.compile(r'```|`|\bdef |\bclass |=>|[{};]\s*$|\(\)|\w+\.\w+\(',re.M)
WORD=re.compile(r'[a-zA-ZäöüÄÖÜß0-9_]{3,}')

def clamp(x,lo=0.,hi=1.):
    x=float(x)
    if not math.isfinite(x):raise ValueError('Wert nicht endlich')
    return min(hi,max(lo,x))

def empty():
    return {'revision':REVISION,'mode':'SHADOW','learned':'SHADOW','layout':'append_only','knobs':dict(CTX),'capabilities':{},
            'warm':{},'seq':0,'last':{},'policy':{},'recall':[],'plans':0,'cache':{'n':0,'cached_tokens':0,'prompt_tokens':0}}

def exact_spans(text):
    """Spans that must survive any compression verbatim (exact-span pinning, §8.5)."""
    out=[]
    for rx in (CODE,URL,QUOTE,EN_CURLY,FR_QUOTE,CURLY_SINGLE,SINGLE_QUOTE,NUMBER):
        for m in rx.finditer(text):
            s=m.group(0).strip()
            if s and not any(s in o for o in out):out.append(s)
    return out

def first_sentence(text,cap):
    t=' '.join(CODE.sub(' ',text).split())
    m=re.search(r'(.+?[.!?])(\s|$)',t);s=(m.group(1) if m else t)
    return s if len(s)<=cap else s[:cap-1].rstrip()+'…'

def _unsafe_backticks(text):
    """Fail closed if Markdown code cannot be fully pinned by CODE regex.

    Only paired single-backtick inline spans and properly closed triple-fenced
    blocks are compressible. Double/multi-backtick syntax, an unclosed span,
    an ambiguous fence delimiter or multiline inline code stays RAW rather
    than silently losing literal source text.
    """
    mode=None
    for line in text.splitlines(keepends=True):
        for match in re.finditer(r'`+',line):
            width=len(match.group())
            if width not in (1,3):return True
            if mode is None:
                mode='fence' if width==3 else 'inline'
            elif mode=='inline':
                if width!=1:return True
                mode=None
            elif width==3:
                # A fence closes on its own line, never inside a code string.
                if line[:match.start()].strip() or line[match.end():].strip():return True
                mode=None
        if mode=='inline' and line.endswith(('\n','\r')):return True
    return mode is not None



def _unsafe_single_quotes(text):
    """Preserve delimiter-style single quotes; ignore intra-word apostrophes.

    Unmatched or overlong quoted text stays RAW. A contraction inside a
    balanced quoted literal is not a second delimiter.
    """
    matches=list(SINGLE_QUOTE.finditer(text))
    boundaries={i for m in matches for i in (m.start(),m.end()-1)}
    for m in re.finditer("'",text):
        i=m.start()
        if i in boundaries:
            continue
        if (i>0 and i+1<len(text) and
                text[i-1].isalnum() and text[i+1].isalnum()):
            continue
        return True
    return False


def _unsafe_typographic_quotes(text):
    """Fail closed on unmatched typographic delimiters, not contractions."""
    remaining=GERMAN_PAIR.sub('',text)
    if '„' in remaining:return True
    for rx,opener,closer in ((EN_CURLY,'“','”'),(FR_QUOTE,'«','»')):
        remaining=rx.sub('',remaining)
        if opener in remaining or closer in remaining:return True
    remaining=CURLY_SINGLE.sub('',remaining)
    for match in re.finditer('[‘’]',remaining):
        i=match.start()
        if (match.group()=='’' and 0<i<len(remaining)-1
                and remaining[i-1].isalnum() and remaining[i+1].isalnum()):
            continue  # typographic apostrophe inside a word
        return True
    return False


def compress(text,cap):
    """Extractive, deterministic, never invents content. Returns (text, spans, ok). ok=False keeps RAW."""
    spans=exact_spans(text)
    if (_unsafe_backticks(text) or _unsafe_single_quotes(text)
            or _unsafe_typographic_quotes(text)):return text,spans,False
    # An unmatched quote can span an unknown literal; never silently compress it.
    if text.count('"')%2:return text,spans,False
    if sum(len(s) for s in spans)>SPAN_CHARS or len(spans)>SPAN_MAX:return text,spans,False
    head=first_sentence(text,cap);missing=[s for s in spans if s not in head]
    out='[compressed earlier turn; exact source kept] '+head+((' | exact: '+' ; '.join(missing)) if missing else '')
    ok=len(out)<len(text) and all(s in out for s in spans)
    return (out,spans,True) if ok else (text,spans,False)

def terms(text):return {w.lower() for w in WORD.findall(text or '')}

def relevance(query,text):
    q=terms(query)
    return len(q&terms(text))/len(q) if q else 0.

def exact_need(query,verdicts=()):
    hits={}
    if NUMBER.search(query or ''):hits['numbers']=EXACT_NEED['numbers']
    if CODEISH.search(query or ''):hits['code']=EXACT_NEED['code']
    if LITERAL.search(query or ''):hits['literal']=EXACT_NEED['literal']
    if CRITIQUE.search(query or ''):hits['source_critique']=EXACT_NEED['source_critique']
    if CONFLICT_VERDICTS&set(verdicts or ()):hits['conflict']=EXACT_NEED['conflict']
    return (max(hits.values()) if hits else 0.),hits

def pairs(history):
    """Group source-valid history rows into complete turns, oldest first, keeping role order."""
    out={};order=[]
    for row in history:
        if row['event_id'] not in out:out[row['event_id']]=[];order.append(row['event_id'])
        out[row['event_id']].append({'role':row['role'],'content':row['text']})
    return [(eid,out[eid]) for eid in order]

def prefix_reuse(old,new):
    """Characters of `new` whose serialized message prefix matches `old` (what a prompt cache could keep)."""
    n=0
    for a,(b,chars) in zip(old or [],new):
        if a[0]!=b:break
        n+=chars
    return n

def fingerprint(messages):return [(digest(dumps(m).encode())[:16],len(m['content'])) for m in messages]

class ContextOS:
    def __init__(self,store,cfg,age=None,neuromod=None):
        self.s=store;self.cfg=cfg;self.age=age;self.n=neuromod
    # -- state ------------------------------------------------------------------------------------------
    def _seq(self):return int(self.s.one('SELECT COALESCE(MAX(rowid),0) AS n FROM events')['n'])
    def _load(self):
        st,v=self.s.state(KEY,None)
        if st is None:st=empty()
        if st.get('revision')!=REVISION:raise ValueError('Context OS state revision mismatch')
        return st,v
    def _decay(self,st):
        """Warm/activity-silent memory decays per experience event (§9.1), lazily."""
        seq=self._seq();d=WARM_DECAY**max(0,seq-st['seq'])
        st['warm']={k:round(a*d,6) for k,a in st['warm'].items() if a*d>=WARM_MIN};st['seq']=seq
    def _mutate(self,fn):
        for attempt in (0,1):
            st,v=self._load();self._decay(st);out=fn(st);dumps(st)
            try:self.s.set_state(KEY,st,expected=v);return out
            except ValueError:
                if attempt:raise
    def knobs(self):return dict(self._load()[0]['knobs'])
    def _recall_stable(self,st):
        r=st['recall'][-RECALL_WINDOW:]
        return len(r)>=RECALL_MIN_PLANS and sum(r)/len(r)>=RECALL_STABLE
    def set_knob(self,name,value,restore=False):
        if name not in CTX:raise ValueError('Unbekannter CTX-Regler: '+str(name))
        value=clamp(value)
        def fn(st):
            old=st['knobs'][name];risky=(name in RISKY_UP and value>old) or (name in RISKY_DOWN and value<old)
            if risky and not restore and not self._recall_stable(st):
                raise ValueError(f'CTX.{name}: nur erhöhen, wenn Exact Recall stabil ist (>= {RECALL_STABLE} über {RECALL_MIN_PLANS} Pläne)')
            st['knobs'][name]=value;return {name:value}
        return self._mutate(fn)
    def set_mode(self,mode,authority='SYSTEM',which='mode'):
        if mode not in {'SHADOW','ACTIVE'} or which not in {'mode','learned'}:raise ValueError('SHADOW|ACTIVE')
        if mode=='ACTIVE' and authority!='EXPLICIT_HUMAN':raise PermissionError('ACTIVE nur per expliziter Nutzerfreigabe (Age 0)')
        def fn(st):st[which]=mode;return mode
        return self._mutate(fn)
    def digest_enabled(self):return self._load()[0].get('digest',True)
    def set_digest(self,on):
        """WP-S7: sleep day digest of turns outside the history window as a COMPRESSED context layer (measured default on)."""
        def fn(st):st['digest']=bool(on);return st['digest']
        return self._mutate(fn)
    def set_layout(self,layout):
        if layout not in LAYOUTS:raise ValueError('Layout: '+'|'.join(LAYOUTS))
        def fn(st):st['layout']=layout;return layout
        return self._mutate(fn)
    def set_capability(self,role,cap,value,evidence=None):
        if cap not in CAPABILITIES:raise ValueError('Unbekannte Fähigkeit: '+str(cap))
        def fn(st):
            st['capabilities'].setdefault(role,{})[cap]={'value':bool(value),'evidence':evidence or 'operator'};return st['capabilities'][role]
        return self._mutate(fn)
    def capability(self,role,cap):
        return bool(self._load()[0]['capabilities'].get(role,{}).get(cap,{}).get('value'))
    # -- warm memory (§9.1) ----------------------------------------------------------------------------
    def warm(self,query,session,recalled,threshold=WARM_ADMIT):
        """Reactivate only still-human-authorized F1 memories in warm order.

        Warm candidates bypass normal lexical recall by design, but must never
        bypass its F5 HumanDecision/feedback/source lineage. Validate the full
        eligible pool before applying the two-slot cap, so a revoked first item
        cannot starve a valid later item. Neither SHADOW nor ACTIVE can surface
        an invalid correction, and the persisted warm state is not rewritten.
        """
        st,_=self._load();self._decay(st);have={str(m['id']) for m in recalled};gain=st['knobs']['prefetch_gain'];out=[]
        candidates=[]
        for mid,a in sorted(st['warm'].items(),key=lambda kv:-kv[1]):
            if str(mid) in have:continue
            r=self.s.one("SELECT m.*,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=? AND m.active=1 AND s.deleted=0 AND m.kind IN ('fact','style','preference') AND (m.session_id=? OR m.scope='global')",(mid,session))
            if not r:continue
            rel=relevance(query,r['key_text'])
            if a*(rel+gain)<threshold:continue
            candidates.append((dict(r),rel,a))
        if candidates:
            from .memory import Memory
            verified={m['id'] for m in Memory(self.s,self.cfg)._verified_rows([r for r,_,_ in candidates])}
            for r,rel,a in candidates:
                if r['id'] not in verified:continue
                ref={'source_id':r['source_id'],'sha256':r['hash'],'char_start':0,'char_end':r['chars'],'modality':'text'}
                try:value=self.s.read_source(ref)
                # The blob can disappear after F5 verification but before
                # delivery; a late OSError is not permission to serve stale data.
                except (ValueError,OSError):continue
                if value!=r['value']:continue
                r.update(source_ref=ref,value=value,retrieval_score=rel,retrieval_policy=None,warm_activation=a);out.append(r)
                if len(out)>=WARM_PREFETCH_MAX:break
        return {'items':out,'applied':st['mode']=='ACTIVE','ids':[m['id'] for m in out]}
    # -- plan ------------------------------------------------------------------------------------------
    def _shift(self,st,key):
        q=st['policy'].get(key)
        if st['learned']!='ACTIVE' or not q or q['n']<LEARNED_MIN_N:return 0.
        return LEARNED_MAX*(q['mean']-.5)*2
    def plan(self,event_id,role,stable,volatile,history,query,verdicts=(),warm_ids=(),archived=0,provenance=None,budget_scale=1.):
        """stable: pinned system text. volatile: [(layer, header, payload)] in legacy order. history: native rows.
        Returns the messages the runner gets (legacy in SHADOW) plus the ContextPlan packet."""
        st,_=self._load();self._decay(st);k=st['knobs'];items=[];decisions=[]
        legacy_sys=stable+''.join(h+dumps(p) for _,h,p in volatile)
        turns=pairs(history)
        legacy=[{'role':'system','content':legacy_sys}]+[m for _,ms in turns for m in ms]+[{'role':'user','content':query}]
        budget=max(256,int((self.cfg['context_tokens']-self.cfg['answer_tokens']-16)*CHARS_PER_TOKEN*clamp(budget_scale,.25,1.)))  # §7.4 body may shrink it
        need,triggers=exact_need(query,verdicts);restore_thr=1-k['reconstruct_disposable_cache']-self._shift(st,'restore')
        exact_mode=need>=restore_thr;block_thr=1-k['long_context_block_index']
        n=len(turns);pinned=min(n,math.ceil(k['exact_recent_pin']*n)) if n else 0
        state=[]  # per turn: [eid, msgs, form, pinned, restored]
        for i,(eid,ms) in enumerate(turns):
            restored=exact_mode and relevance(query,' '.join(m['content'] for m in ms))>=block_thr
            state.append([eid,ms,'RAW',i>=n-pinned,restored])
        # volatile layers: keep order, drop trailing list items beyond the global compact share (POINTER)
        share=clamp(k['global_compact_state'])*budget;vol=[]
        for layer,head,payload in volatile:
            kept=payload;dropped=0
            if isinstance(payload,list):
                while len(kept)>1 and len(dumps(kept))+sum(len(h)+len(dumps(p)) for _,h,p in vol)>share:kept=kept[:-1];dropped+=1
            vol.append((layer,head,kept))
            items.append({'item_id':layer,'layer':layer,'form':'RAW' if not dropped else 'COMPRESSED','chars':len(head)+len(dumps(kept)),'pointers':dropped})
            if dropped:decisions.append('compact_'+layer.lower())
        def size():
            t=len(stable)+len(query)+sum(len(h)+len(dumps(p)) for _,h,p in vol)
            for s in state:
                if s[2]=='POINTER':continue
                t+=sum(len(compress(m['content'],SUMMARY_USER if m['role']=='user' else SUMMARY_ASSISTANT)[0]) if s[2]=='COMPRESSED' else len(m['content']) for m in s[1])
            return t
        def try_compress(s):
            if s[2]!='RAW' or s[4]:return False
            if any(not compress(m['content'],SUMMARY_USER if m['role']=='user' else SUMMARY_ASSISTANT)[2] for m in s[1]):return False
            s[2]='COMPRESSED';return True
        # proactive compression of the oldest unpinned turns (§74 cache_compression_aggressiveness)
        unpinned=[s for s in state if not s[3]]
        aggr=clamp(k['cache_compression_aggressiveness']+self._shift(st,'compress'))
        for s in unpinned[:round(aggr*len(unpinned))]:
            if try_compress(s):decisions.append('compress')
        # budget pressure: compress, then point, unpinned first; the newest turn is never dropped by policy
        for group in (unpinned,[s for s in state[:-1] if s[3]]):
            for s in group:
                if size()<=budget:break
                if try_compress(s):decisions.append('compress_budget')
            for s in group:
                if size()<=budget:break
                if not s[4]:s[2]='POINTER';decisions.append('pointer_budget')
        if any(s[4] for s in state):decisions.append('restore')
        hist=[];span_total=span_kept=0
        for eid,ms,form,pin,restored in state:
            chars=0
            for m in ms:
                c,spans,_=compress(m['content'],SUMMARY_USER if m['role']=='user' else SUMMARY_ASSISTANT)
                span_total+=len(spans)
                if form=='POINTER':continue
                content=c if form=='COMPRESSED' else m['content'];span_kept+=sum(s in content for s in spans)
                hist.append({'role':m['role'],'content':content});chars+=len(content)
            items.append({'item_id':eid,'layer':{'RAW':'RAW_HISTORY','COMPRESSED':'COMPRESSED','POINTER':'SOURCE_LINKS'}[form],'form':form,'chars':chars,'pinned':pin,'restored':restored})
        if warm_ids:items.append({'item_id':'warm','layer':'MEMORY_POINTERS','form':'POINTER','chars':0,'ids':list(warm_ids)})
        if archived:items.append({'item_id':'archive','layer':'ARCHIVE','form':'POINTER','chars':0,'count':int(archived)})
        recall=span_kept/span_total if span_total else 1.
        layout=st['layout'];reason=None
        if layout in ('stable_prefix','append_only') and not st['capabilities'].get(role,{}).get('consecutive_user',{}).get('value'):layout,reason='legacy','template_capability_unknown'
        vtext=''.join(h+dumps(p) for _,h,p in vol);tail=([{'role':'user','content':VOLATILE_HEAD+vtext}] if vtext else [])+[{'role':'user','content':query}]
        planned=None
        if layout=='append_only':
            # Hybrid/recurrent bodies (LFM2, Qwen3.5) can only reuse state when the new prompt *extends* the old one
            # (measured 2026-10-09, bench-results/context-cache-20261009). Re-enter the stored transcript: old prompt +
            # the committed answer + new volatile block + query. Any mismatch falls back to stable_prefix.
            prev=st.get('transcripts',{}).get(role);last=turns[-1] if turns else None
            # Re-enter only the exact still-valid prefix. A changed/removed volatile
            # memory or rewritten source turn must never survive in a cached prompt.
            # In ACTIVE, a SHADOW counterfactual was not actually sent to the runner.
            if not (prev and last and prev.get('event_id')==last[0] and prev.get('system')==stable
                    and len(last[1])==2 and last[1][0]['role']=='user'
                    and last[1][-1]['role']=='assistant'):
                reason='append_no_matching_transcript'
            elif st['mode']=='ACTIVE' and not prev.get('applied',False):
                reason='append_unapplied_transcript'
            elif prev.get('volatile_hash')!=digest(vtext):
                reason='append_volatile_changed'
            elif prev.get('history_hash')!=digest(dumps(turns[:-1])):
                reason='append_history_changed'
            elif prev.get('query')!=last[1][0]['content']:
                reason='append_query_changed'
            else:
                cand=prev['messages']+[{'role':'assistant','content':last[1][-1]['content']}]+tail
                if sum(len(m['content']) for m in cand)<=budget:planned=cand;decisions.append('append_reentry')
                else:reason='append_budget_rebuild'
            if planned is None:layout='stable_prefix'
        if planned is None:
            if layout=='stable_prefix' and vtext:planned=[{'role':'system','content':stable}]+hist+tail
            else:planned=[{'role':'system','content':stable+vtext}]+hist+[{'role':'user','content':query}]
        applied=st['mode']=='ACTIVE'
        fp_legacy,fp_planned=fingerprint(legacy),fingerprint(planned);last=st['last'].get(role,{})
        cache={'layout_requested':st['layout'],'layout':layout,'fallback_reason':reason,'prompt_cache':'cache_prompt',
               'est_prompt_chars_legacy':sum(c for _,c in fp_legacy),'est_prompt_chars_planned':sum(c for _,c in fp_planned),
               'est_reused_chars_legacy':prefix_reuse(last.get('legacy'),fp_legacy),'est_reused_chars_planned':prefix_reuse(last.get('planned'),fp_planned),
               'actions':sorted({'pin_exact_span','reuse_prefix'}|({'compress'} if 'compress' in ' '.join(decisions) else set())|({'restore_exact'} if 'restore' in decisions else set())|({'prefetch_warm'} if warm_ids else set()))}
        p=self.s.add_packet('ContextPlan',packet('ContextPlan','N7_CONTEXT_OS',event_id,self.s.generation_id,provenance or [],
            mode=st['mode'],layout=layout,applied=applied,budget={'chars':budget,'planned_chars':cache['est_prompt_chars_planned'],'chars_per_token':CHARS_PER_TOKEN},
            items=items,cache=cache,exact={'need':round(need,4),'threshold':round(restore_thr,4),'triggers':triggers,'span_recall':round(recall,6)},
            decisions=decisions,role=role,learned=st['learned'],knobs=k))
        def fn(st2):
            st2['last'][role]={'legacy':fp_legacy,'planned':fp_planned,'event_id':event_id,'packet_id':p['packet_id'],'decisions':sorted(set(decisions)),'applied':applied}
            st2['recall']=(st2['recall']+[recall])[-RECALL_WINDOW:];st2['plans']+=1
            if st2['layout']=='append_only' and sum(len(m['content']) for m in planned)<=TRANSCRIPT_MAX_CHARS:
                st2.setdefault('transcripts',{})[role]={'event_id':event_id,'system':stable,'messages':planned,
                    'volatile_hash':digest(vtext),'history_hash':digest(dumps(turns)),
                    'query':query,'applied':applied}
            else:st2.get('transcripts',{}).pop(role,None)
        self._mutate(fn)
        if self.n is not None:
            try:self.n.touch(PATH,event_id,activity=1. if decisions else .3,detail={'decisions':sorted(set(decisions)),'mode':st['mode']},refs=provenance)
            except Exception:pass
        return {'messages':planned if applied else legacy,'planned':planned,'legacy':legacy,'applied':applied,'packet_id':p['packet_id'],'plan':p}
    # -- outcomes --------------------------------------------------------------------------------------
    def observe(self,event_id,role,metrics=None,status='FINAL',memory_ids=()):
        """After the answer: runner cache timings -> cost modulator; used memories become warm (§9.1)."""
        # Native cost evidence is not trusted merely because Python treats bool as int.
        # Missing metrics mean no measurement; malformed supplied metrics are rejected,
        # never forwarded as negative/over-100% reuse or learning-cost credit.
        bad_envelope=metrics is not None and type(metrics) is not dict
        raw=metrics.get('timings') if type(metrics) is dict else None
        t=raw if type(raw) is dict else {}
        supplied=bad_envelope or (raw is not None and (type(raw) is not dict or 'cache_n' in t or 'prompt_n' in t))
        cached=t.get('cache_n');prompt=t.get('prompt_n')
        valid=(type(cached) is int and type(prompt) is int
               and 0<=cached<=MAX_CACHE_METRIC_TOKENS
               and 0<=prompt<=MAX_CACHE_METRIC_TOKENS
               and cached+prompt>0)
        ratio=cached/(cached+prompt) if valid else None
        rejected=bool(supplied and not valid)
        def fn(st):
            # Activity-silent reactivation is a state update: an interrupted,
            # failed or provisional answer must not refresh its memory traces.
            if status=='FINAL':
                for mid in memory_ids:st['warm'][str(mid)]=1.
                if len(st['warm'])>WARM_MAX:st['warm']=dict(sorted(st['warm'].items(),key=lambda kv:-kv[1])[:WARM_MAX])
            last=st['last'].get(role)
            matches=bool(last and last.get('event_id')==event_id)
            # One current FINAL result per role/event. CAS in _mutate makes
            # concurrent replays observe the committed receipt before credit.
            # Older events cannot contaminate the current plan's cost baseline.
            credited=bool(ratio is not None and status=='FINAL' and matches
                          and not last.get('cache_recorded',False))
            if credited:
                c=st['cache'];c['n']+=1;c['cached_tokens']+=cached;c['prompt_tokens']+=prompt
                last['measured_reuse']=ratio;last['cache_recorded']=True
            if matches and not (last.get('cache_recorded') and not credited):
                last['status']=status
            return {'credited':credited,'applied':bool(last.get('applied')) if matches else False}
        outcome=self._mutate(fn)
        if self.n is not None and outcome['credited'] and outcome['applied']:
            try:self.n.signal(event_id,path=PATH,source_class='real_deterministic_outcome',cost_error=1-ratio)
            except Exception:pass
        return {'reuse_ratio':ratio if outcome['credited'] else None,
                'warm':list(memory_ids) if status=='FINAL' else [],
                'cache_rejected':rejected or bool(ratio is not None and not outcome['credited'])}
    def outcome(self,event_id,utility,source_class='internal_crosscheck'):
        """Usefulness of the context decisions of one event (e.g. a rating). Updates the learned prior per decision."""
        u=clamp(utility);row=self.s.one("SELECT payload FROM packets WHERE kind='ContextPlan' AND event_id=? ORDER BY created DESC LIMIT 1",(event_id,))
        if not row:raise ValueError('Kein ContextPlan für dieses Event')
        import json
        sc=step(self.n,PATH)  # WP-U6 §12.7
        plan=json.loads(row['payload']);keys={'compress' if d.startswith('compress') else d for d in plan['decisions'] if d.startswith('compress') or d=='restore'}
        def fn(st):
            for key in keys:
                q=st['policy'].setdefault(key,{'n':0,'mean':.5});q['n']+=1;q['mean']+=sc*POLICY_RATE*(u-q['mean'])
            return {k2:dict(st['policy'][k2]) for k2 in keys}
        out=self._mutate(fn)
        if self.n is not None:
            try:self.n.signal(event_id,path=PATH,source_class=source_class,task_success=u)
            except Exception:pass
        return out
    def report(self):
        st,_=self._load();self._decay(st);c=st['cache'];r=st['recall'][-RECALL_WINDOW:]
        return {'revision':REVISION,'mode':st['mode'],'learned':st['learned'],'layout':st['layout'],'knobs':st['knobs'],'capabilities':st['capabilities'],
                'warm':st['warm'],'plans':st['plans'],'exact_span_recall':{'n':len(r),'mean':round(sum(r)/len(r),6) if r else None,'stable':self._recall_stable(st)},
                'measured_cache_reuse':round(c['cached_tokens']/(c['cached_tokens']+c['prompt_tokens']),6) if c['cached_tokens']+c['prompt_tokens'] else None,
                'last':{role:{k2:v for k2,v in x.items() if k2 not in {'legacy','planned'}} for role,x in st['last'].items()},
                'policy':st['policy'],'claim_limit':'Changes the model view only; sources stay unchanged and restorable. No native KV/attention patching.'}

def probe_template(runner,cancel,deadline):
    """G6B capability probe: does the body's chat template keep two consecutive user messages in order?"""
    msgs=[{'role':'system','content':'s'},{'role':'user','content':'PROBE_CONTEXT_7'},{'role':'user','content':'PROBE_QUERY_9'}]
    try:
        runner.load(cancel,deadline)
        p=runner._json('POST','/apply-template',{'messages':msgs,'add_generation_prompt':True,'chat_template_kwargs':{'enable_thinking':False}},deadline)['prompt']
    except Exception as exc:return {'value':False,'evidence':'template_error:'+type(exc).__name__}
    a,b=p.find('PROBE_CONTEXT_7'),p.find('PROBE_QUERY_9')
    return {'value':0<=a<b,'evidence':'apply-template order' if 0<=a<b else 'missing_or_reordered'}

def controller(runtime):
    """Runtime-scoped instance without growing runtime.__init__ (like attention/neuromod controllers)."""
    c=getattr(runtime,'context_os',None)
    if c is None:
        age=n=None
        try:
            from .age import controller as age_controller
            age=age_controller(runtime)
        except Exception:age=None
        try:
            from .neuromod import controller as neuromod_controller
            n=neuromod_controller(runtime)
        except Exception:n=None
        c=runtime.context_os=ContextOS(runtime.store,runtime.cfg,age,n)
    return c

USAGE=':ctxos [status|last|shadow|active|learned shadow|learned active|layout legacy|stable_prefix|append_only|digest on|off|knob <Name> <0..1>|capability <Rolle> on|off|probe <Rolle>|outcome <Event> <0..1>]'
def operator_command(r,args):
    c=controller(r)
    if not args or args==['status']:return dumps(c.report())
    if args==['last']:
        # Context plans may contain raw/source-linked text. Never show another
        # chat's latest packet merely because it was written more recently.
        row=r.store.one("SELECT p.payload FROM packets p "
                        "JOIN events e ON e.id=p.event_id "
                        "WHERE p.kind='ContextPlan' AND e.session_id=? "
                        "ORDER BY p.created DESC, p.rowid DESC LIMIT 1",
                        (r.session,))
        return row['payload'] if row else dumps(None)
    if args==['shadow']:return dumps({'mode':c.set_mode('SHADOW')})
    if args==['active']:return dumps({'mode':c.set_mode('ACTIVE','EXPLICIT_HUMAN')})  # typed by the operator = explicit
    if len(args)==2 and args[0]=='learned':return dumps({'learned':c.set_mode(args[1].upper(),'EXPLICIT_HUMAN','learned')})
    if len(args)==2 and args[0]=='layout':return dumps({'layout':c.set_layout(args[1])})
    if len(args)==2 and args[0]=='digest' and args[1] in {'on','off'}:return dumps({'digest':c.set_digest(args[1]=='on')})
    if len(args)==3 and args[0]=='knob':return dumps(c.set_knob(args[1],float(args[2])))
    if len(args)==3 and args[0]=='capability' and args[2] in {'on','off'}:return dumps(c.set_capability(args[1],'consecutive_user',args[2]=='on'))
    if len(args)==2 and args[0]=='probe':
        import threading,time
        res=probe_template(r.pool.get(args[1]),threading.Event(),time.monotonic()+120)
        return dumps(c.set_capability(args[1],'consecutive_user',res['value'],res['evidence']))
    if len(args)==3 and args[0]=='outcome':
        row=r.store.one('SELECT session_id FROM events WHERE id=?',(args[1],))
        if row is None or row['session_id']!=r.session:
            raise ValueError('Event nicht im aktuellen Chat')
        return dumps(c.outcome(args[1],float(args[2]),'human_correction'))
    raise ValueError(USAGE)
