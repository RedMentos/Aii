import json
import math
import re
import time
from .contracts import packet,offer_is_fresh
from .inputs import looks_like_terminal_log
from .common import dumps,uid,atomic_write,file_hash
from .memory import relevance,entities
from .runners import check
ROUTES=['simple','detail','gist','both']
def scaffold_route(text):
    t=text.lower()
    if re.search(r'vergleich|compare|abwäg|trade.?off',t):return 'both'
    if re.search(r'code|python|berechn|calculate|budget|mathe|debug|fehler|\d\s*[+*/=]',t):return 'detail'
    if re.search(r'zusammenfass|summary|summarize|überblick|plan',t):return 'gist'
    return 'simple'
def segments(text,ref,width,mode='fixed'):
    """mode 'fixed': legacy fixed-width chunks (body views, byte-identical prompts). mode 'event': WP-N8 §51.2 A1 inside one
    text via episodes.text_segments (paragraph/sentence/topic boundaries, lossless tiling with SourceRefs)."""
    if mode=='event':
        from .episodes import text_segments
        return text_segments(text,ref,width)
    return [{'text':text[i:i+width],'source_ref':ref|{'char_start':i,'char_end':min(len(text),i+width)}} for i in range(0,len(text),width)]
from .age import RIGHTS as _RIGHTS
AGE0_RIGHTS=frozenset(r for r,s in _RIGHTS.items() if s==0)
def percept_mode(cfg):
    """segment_mode fixed|percept|all: the A4 PerceptPacket uses event segments unless the operator chose 'fixed'."""
    return 'fixed' if cfg.get('segment_mode','percept')=='fixed' else 'event'
OFFER_SCHEMA={'type':'object','properties':{'summary':{'type':'string'},'quotes':{'type':'array','items':{'type':'string'},'maxItems':3},'uncertainty':{'type':'string'},'needs_reentry':{'type':'boolean'}},'required':['summary','quotes','uncertainty','needs_reentry'],'additionalProperties':False}
def offer_schema(tokens,quote_min_chars=0):
    """OFFER_SCHEMA with string caps that fit the observer token budget, so a verbose body (B2 Qwen3.5 gist)
    closes its JSON instead of being cut off and discarded. ~2.2 chars/token (German + Qwen tokenizer, measured truncation at 3); split summary 45 %, quotes 2x20 %,
    uncertainty 15 % of what is left after ~30 tokens of JSON syntax. BOOT estimate, not tuned.
    quote_min_chars (cfg offer_quote_min_chars, 0 = off) raises the quote cap so one whole source sentence fits."""
    chars=max(110,int((int(tokens)-30)*2.2))
    s=json.loads(json.dumps(OFFER_SCHEMA));pr=s['properties']
    pr['summary']['maxLength']=max(48,int(chars*.45));pr['uncertainty']['maxLength']=max(16,int(chars*.15))
    pr['quotes']['maxItems']=2;pr['quotes']['items']['maxLength']=max(24,int(chars*.2))
    if quote_min_chars>pr['quotes']['items']['maxLength']:
        # Thread O STEP2 producer ablation: 57-char quotes cut every earlier rule sentence (~80 chars) before its last
        # rule ("... Local-"). A longer quote takes its room from the summary, so the worst case stays within budget.
        q=min(int(quote_min_chars),(chars-48-pr['uncertainty']['maxLength'])//2)  # never beyond the budget
        if q>pr['quotes']['items']['maxLength']:
            pr['quotes']['items']['maxLength']=q;pr['summary']['maxLength']=chars-2*q-pr['uncertainty']['maxLength']
    return s
# WP-KAL2 (2026-10-09, bench-results/KALIBRIERUNG.md): the 'hypothesis' wording made bodies restate the task
# ("requires adding 46 and 62") instead of solving it: B1 named the result in 5 % of checkable tasks, 'solve' in 37.5 %.
# 'hypothesis' stays selectable for ablations via cfg offer_style.
OFFER_STYLE='solve'
OFFER_SUMMARY={'hypothesis':'summary is a short hypothesis, NOT a final user answer.',
               'solve':'summary is a short hypothesis that states the exact result you computed or found (another component writes the user answer).'}
def offer_instructions(policy,style=OFFER_STYLE):
    role='detail analyst. Check exact details, calculations and contradictions.' if policy=='B1_DETAIL' else 'gist analyst. Identify the main goal, constraints and broader context.'
    return ('You are an internal '+role+' Return JSON only. '+OFFER_SUMMARY[style]+' quotes must be exact substrings of the supplied source. '
            'Use at most two short quotes. uncertainty is concise. needs_reentry indicates a material unresolved issue. Keep all fields short.')
def quote_span(quote,source,context_chars=0):
    """(start,end) of a body quote inside source, or None. context_chars 0 (live): exact substring only.
    context_chars>0 (cfg offer_quote_context_chars, 2026-10-20 STEP2 B2->C3 transport): a quote that differs from the
    source only in letter case or whitespace still verifies, and a quote of >= 12 chars grows to its whole sentences,
    then to neighbouring sentences of the same source while the span stays within context_chars. The quote is only a
    pointer; the transported text is always the exact source span (Qwen B2 split, cut or re-cased the earlier
    rule, so its full text reached C3 in only 7/30 STEP2 retain offers)."""
    if not isinstance(quote,str) or not quote:return None
    if quote in source:a=source.index(quote);b=a+len(quote)
    elif not context_chars:return None
    else:
        q=' '.join(quote.split()).casefold()
        if len(q)<12:return None
        flat=[];at=[]
        for i,ch in enumerate(source):
            if ch.isspace() and i and source[i-1].isspace():continue
            piece=' ' if ch.isspace() else ch.casefold();flat.append(piece);at+=[i]*len(piece)
        j=''.join(flat).find(q)
        if j<0:return None
        a,b=at[j],at[j+len(q)-1]+1
    if not context_chars or b-a<12:return a,b
    sents=[(m.start(),m.end()) for m in re.finditer(r'\S.*?(?:[.!?](?=\s|$)|$)',source,re.S)]
    inside=[k for k,(s,e) in enumerate(sents) if e>a and s<b]
    if not inside:return a,b
    i,k=inside[0],inside[-1]
    if sents[k][1]-sents[i][0]>context_chars:return a,b
    grew=True
    while grew:
        grew=False
        if k+1<len(sents) and sents[k+1][1]-sents[i][0]<=context_chars:k+=1;grew=True
        if i>0 and sents[k][1]-sents[i-1][0]<=context_chars:i-=1;grew=True
    return sents[i][0],sents[k][1]
_ANCHOR_STOP=frozenset('a an the of for and or is are be to in on at with by from this that it its has have as'.split())
def _anchor_tokens(s):
    out=set()
    for w in re.findall(r'[a-z]+|\d+',s.casefold()):
        if w not in _ANCHOR_STOP:out.add(w[:-1] if not w.isdigit() and len(w)>3 and w.endswith('s') else w)
    return out
def sentence_spans(source):return [(m.start(),m.end()) for m in re.finditer(r'\S.*?(?:[.!?](?=\s|$)|$)',source,re.S)]
def anchor_span(quote,sources,min_cover=.6,max_sentences=3):
    """WP-Z2c (cfg b2_quote_select='anchor'): a B2 quote that matches no source (Qwen B2 paraphrased the earlier rule,
    'Project X has a budget of 100 euros', in ~1/3 of Z2b offers) points at the 1..max_sentences consecutive source
    sentences that hold every number of the quote and >= min_cover of its content words. (source index,start,end) or
    None; None also when the best cover is tied across different sources. Only exact source text is ever transported."""
    q=_anchor_tokens(quote) if isinstance(quote,str) else set()
    if len(q)<3:return None
    nums={w for w in q if w.isdigit()};found=[]
    for si,src in enumerate(sources):
        ss=sentence_spans(src)
        for i in range(len(ss)):
            for k in range(i,min(i+max_sentences,len(ss))):
                a,b=ss[i][0],ss[k][1];t=_anchor_tokens(src[a:b])
                if nums<=t and len(q&t)/len(q)>=min_cover:found.append((len(q&t)/len(q),a-b,si,a,b))
    if not found:return None
    found.sort(reverse=True);top=found[0]
    if any(x[0]==top[0] and x[2]!=top[2] for x in found[1:]):return None
    return top[2],top[3],top[4]
def quote_choices(sources,cap=24):
    """WP-Z2c (cfg b2_quote_select='pointer'): the exact sentences of the given sources, in order, as (source index,
    start,end); the body answers with their numbers instead of copying text."""
    return [(si,a,b) for si,src in enumerate(sources) for a,b in sentence_spans(src)][:cap]
class Cognition:
    def __init__(self,runtime):self.r=runtime;self.s=runtime.store
    def tap(self,role,e,source_ref,deadline):
        """Source-bound native body observation; no receiver or learning authority."""
        if source_ref['source_id']!=e['source_ref']['source_id']:raise ValueError('Tap source must belong to this event')
        text=self.s.read_source(source_ref);tap_runner=self.r.pool.get_tap(role);native=tap_runner.tap(text,self.r.cancel_event,deadline)
        path=self.r.home/'data/blobs'/(uid('tap')+'.json');atomic_write(path,dumps({'token_ids':native['token_ids'],'vectors':native['vectors']}))
        prediction=None
        try:prediction=self.r.learner.predict_states(role,native['vectors'])
        except Exception as exc:self.s.log('local_predictor_unavailable',e['event_id'],{'role':role,'error':type(exc).__name__})
        p=packet('LatentTapPacket',role,e['event_id'],e['brain_generation_id'],[source_ref],role=role,source_ref=source_ref,
                 tap_id=getattr(tap_runner,'tap_id','lfm2.result_norm.final.v1'),model_revision=self.r.models.revision(role),runner_revision='b10964',
                 token_ids=native['token_ids'],feature_path=str(path.relative_to(self.r.home)),feature_sha256=file_hash(path),shape=[len(native['vectors']),len(native['vectors'][0]) if native['vectors'] else getattr(tap_runner,'tap_dim',2048)],
                 role_state='INDEPENDENT_READ_ONLY_PREFILL',receiver_read_authority=0,receiver_injection_authority=0,body_learning_authority=0,metrics=native['metrics'],local_prediction=prediction)
        self.s.add_packet('LatentTapPacket',p);self.s.log('native_tap',e['event_id'],native['metrics']|{'model_revision':p['model_revision'],'source_ref':source_ref});return p
    def read_tap(self,p):
        row=self.s.one("SELECT payload FROM packets WHERE kind='LatentTapPacket' AND id=?",(p['packet_id'],))
        if not row or json.loads(row['payload'])!=p:raise ValueError('Tap packet is not the stored observation')
        self.s.read_source(p['source_ref']);path=(self.r.home/p['feature_path']).resolve()
        if not path.is_relative_to((self.r.home/'data/blobs').resolve()) or file_hash(path)!=p['feature_sha256']:raise ValueError('Tap feature file/source binding invalid')
        data=json.loads(path.read_text())
        if data['token_ids']!=p['token_ids'] or len(data['vectors'])!=p['shape'][0] or any(len(v)!=p['shape'][1] for v in data['vectors']):raise ValueError('Tap feature shape/token mismatch')
        return data
    def body_context(self,role,e):
        """B2's bounded long window; persisted IDs, exact sources, no fact promotion.

        B1 retains its existing short last-offer window. B2 context survives a
        restart but never crosses sessions, generations, models or unrelated topics.
        Source lookup is repeated on every use, so deleted/tampered sources fail shut.
        """
        if role=='B1_DETAIL' and self.r.cfg.get('b1_recent_source_chars',0):return self.b1_recent_context(e)
        if role!='B2_GIST' or not self.r.cfg['b2_state_slots'] or self.r.cfg.get('b2_control','two_body') in ('same_model_prompt_only','same_model_same_policy'):return []
        previous,_=self.s.state(role+':'+self.r.session,{})
        ids=previous.get('retained_offer_ids',[previous.get('packet_id')])
        current_text=self.s.read_source(e['source_ref']);context=[];native=[]
        for pid in ids[:self.r.cfg['b2_state_slots']]:
            row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(pid,))
            if not row:continue
            p=json.loads(row['payload'])
            event=self.s.one('SELECT session_id,packet FROM events WHERE id=?',(p['event_id'],))
            if not event or event['session_id']!=self.r.session or p['event_id']==e['event_id']:continue
            if p['role']!=role or p['brain_generation_id']!=e['brain_generation_id'] or p.get('model_revision')!=self.r.models.revision(role):continue
            ref=json.loads(event['packet'])['source_ref']
            try:
                source=self.s.read_source(ref)
                if looks_like_terminal_log(source):continue  # WP-V5: pasted logs are not gist context
                current_entities,prior_entities=entities(current_text),entities(source)
                related=bool(current_entities&prior_entities) if current_entities and prior_entities else relevance(current_text,source)>=self.r.cfg['memory_threshold']
                if not related:continue
                excerpt_ref=ref|{'char_end':min(ref['char_end'],ref['char_start']+240)}
                excerpt=self.s.read_source(excerpt_ref)
            except (ValueError,OSError):continue
            item={'exact_source_excerpt':excerpt,'hypothesis':p['offer'].get('summary','')[:120],'authority':'PRIOR_HYPOTHESIS_NOT_FACT'}
            if len(dumps(native+[item]))>self.r.cfg['b2_context_chars']:continue
            native.append(item);context.append({'offer_id':pid,'source_ref':excerpt_ref,'native_context':item})
        try:  # WP-T5 B4: one prior coalition offer across sessions on the same topic (SHADOW logs only)
            from .bodyview import cross_session
            context+=cross_session(self.r,e,role,current_text,native,self.r.cfg['b2_context_chars'])
        except Exception as exc:self.s.log('bodyview_unavailable',e['event_id'],{'stage':'b4','error':type(exc).__name__})
        return context
    def b1_recent_context(self,e):
        """WP-Z2 (cfg b1_recent_source_chars, 0 = off, live): B1's short horizon keeps the exact source of its own
        last retained turn, up to N chars, instead of only its 240-char hypothesis. Timescale split of Canon §85.1:
        B1 = one recent turn at fine width (exactness), B2 = up to b2_state_slots turns at 240-char excerpts.
        Same session/generation/model/topic checks as B2; quotes may cite it; never a fact promotion."""
        previous,_=self.s.state('B1_DETAIL:'+self.r.session,{})
        pid=previous.get('packet_id')
        row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(pid,)) if pid else None
        if not row:return []
        p=json.loads(row['payload'])
        event=self.s.one('SELECT session_id,packet FROM events WHERE id=?',(p['event_id'],))
        if not event or event['session_id']!=self.r.session or p['event_id']==e['event_id']:return []
        if p['role']!='B1_DETAIL' or p['brain_generation_id']!=e['brain_generation_id'] or p.get('model_revision')!=self.r.models.revision('B1_DETAIL'):return []
        ref=json.loads(event['packet'])['source_ref']
        try:
            current_text,source=self.s.read_source(e['source_ref']),self.s.read_source(ref)
            if looks_like_terminal_log(source):return []
            current_entities,prior_entities=entities(current_text),entities(source)
            related=bool(current_entities&prior_entities) if current_entities and prior_entities else relevance(current_text,source)>=self.r.cfg['memory_threshold']
            if not related:return []
            excerpt_ref=ref|{'char_end':min(ref['char_end'],ref['char_start']+self.r.cfg['b1_recent_source_chars'])}
            excerpt=self.s.read_source(excerpt_ref)
        except (ValueError,OSError):return []
        return [{'offer_id':pid,'source_ref':excerpt_ref,'native_context':{'exact_source_excerpt':excerpt,'authority':'RECENT_SOURCE_NOT_FACT'}}]
    def retain_body_offer(self,p):
        key=p['role']+':'+self.r.session;previous,_=self.s.state(key,{})
        # State is bounded; immutable packet history remains in the event store.
        ids=[p['packet_id']];seen_events={p['event_id']}
        limit=max(1,self.r.cfg['b2_state_slots']) if p['role']=='B2_GIST' else 1
        for pid in previous.get('retained_offer_ids',[previous.get('packet_id')]):
            if len(ids)>=limit:break
            row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(pid,))
            if not row:continue
            old=json.loads(row['payload'])
            if old['event_id'] in seen_events or old['brain_generation_id']!=p['brain_generation_id'] or old.get('model_revision')!=p.get('model_revision'):continue
            if old['role']!=p['role']:continue
            event=self.s.one('SELECT session_id FROM events WHERE id=?',(old['event_id'],))
            if not event or event['session_id']!=self.r.session:continue
            ids.append(pid);seen_events.add(old['event_id'])
        self.s.set_state(key,p|{'retained_offer_ids':ids})
    def percept(self,e):
        text=self.s.read_source(e['source_ref']);p=packet('PerceptPacket','A5_PERCEPT',e['event_id'],e['brain_generation_id'],[e['source_ref']],source_ref=e['source_ref'],segments=segments(text,e['source_ref'],240,percept_mode(self.r.cfg)),modality='text')
        try:
            prediction=self.r.learner.student_percept(text)
            if prediction:
                path=self.r.home/'data/blobs'/(uid('a3')+'.json');atomic_write(path,dumps(prediction))
                p.update(student_feature_path=str(path.relative_to(self.r.home)),student_feature_sha256=file_hash(path),student_component='a3_student',student_latent_dim=len(prediction['latent']),student_in_support=prediction['in_support'],student_mode='T1_SHADOW',native_receiver_authority=0)
        except Exception as exc:
            p['student_unavailable']=type(exc).__name__;self.s.log('student_unavailable',e['event_id'],{'error':type(exc).__name__})
        return self.s.add_packet('PerceptPacket',p)
    def offer(self,role,e,version,deadline,peer=None,*,valid_until=None,focus=None):
        if role not in {'B1_DETAIL','B2_GIST'}:raise ValueError('Unbekannte Body-Rolle')
        # Inference must finish within its own budget. A completed foreground
        # result may remain eligible until the already bounded consumer turn ends.
        # Background/probe callers retain their original observer-window expiry.
        valid_until=deadline if valid_until is None else valid_until
        for value in (deadline,valid_until):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('Offer deadline ungültig')
        deadline=min(deadline,valid_until);check(self.r.cancel_event,deadline)
        control=self.r.cfg.get('b2_control','two_body')
        # §85.1 controls: the B2 role keeps its own state slot but may borrow B1's policy.
        policy='B1_DETAIL' if role=='B1_DETAIL' or control=='same_model_same_policy' else 'B2_GIST'
        text=self.s.read_source(e['source_ref']);width=240 if policy=='B1_DETAIL' or control=='same_model_prompt_only' else 960
        view=segments(text,e['source_ref'],width,'event' if self.r.cfg.get('segment_mode')=='all' else 'fixed');previous,_=self.s.state(role+':'+self.r.session,{})
        instructions=offer_instructions(policy,self.r.cfg.get('offer_style',OFFER_STYLE))
        broadcast=None
        if version:
            row=self.s.one("SELECT payload FROM packets WHERE event_id=? AND kind='JEFBroadcastPacket' ORDER BY created DESC LIMIT 1",(e['event_id'],))
            if not row:raise ValueError('C1-Broadcast fehlt')
            broadcast=json.loads(row['payload'])
            if broadcast['state_version']!=version or broadcast['brain_generation_id']!=e['brain_generation_id']:raise ValueError('C1-Broadcast veraltet')
        peer_id=None
        if peer:
            peer_id=peer.get('message_packet_id')
            row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='MessagePacket'",(peer_id,))
            if not row:raise ValueError('Peer-Nachricht ohne gespeicherte Provenance')
            peer_packet=json.loads(row['payload'])
            if peer_packet['event_id']!=e['event_id'] or peer_packet['brain_generation_id']!=e['brain_generation_id'] or peer_packet['receiver']!=role:raise ValueError('Peer-Nachricht für anderen Empfänger/Turn')
            # Read the persisted content, never trust a caller's mutable copy.
            peer=peer_packet['content']
        context=self.body_context(role,e)
        prior=previous.get('offer',{}).get('summary','')[:240]
        query={'source_segments':view,'peer_message':peer,'prior_hypothesis':prior if policy=='B1_DETAIL' else ''}
        if focus:  # WP-T1 §3.4.7 top-down QUERY_PACKET: the executive question of this re-entry (a question, never a fact)
            query['jef_query']={k:focus[k] for k in ('question','kind')};instructions+=' jef_query is the executive question for this re-entry; answer it from the source first.'
        bv_refs=[];bv={};win=[]
        try:  # WP-T5 B1 detail windows from granted A4 spans, B5 world/self/skill state as a source (state, never fact)
            from . import bodyview
            if policy=='B1_DETAIL':
                win=bodyview.detail_windows(self.s,e['event_id'],text,e['source_ref'])
                if win:query['detail_windows']=[w['text'] for w in win];bv_refs+=[w['source_ref'] for w in win];bv['detail_windows']=len(win)
            # Thread O STEP2 producer ablation: body_state hijacked 41/50 B2 offers; cfg b2_offer_body_state=False leaves it out for B2.
            bs=None if policy=='B2_GIST' and not self.r.cfg.get('b2_offer_body_state',True) else bodyview.body_state(self.r,e,role,text)
            if bs:query['body_state']=bs['view'];bv_refs.append(bs['source_ref']);bv['body_state_ref']=bs['source_ref']
        except Exception as exc:self.s.log('bodyview_unavailable',e['event_id'],{'stage':'offer','error':type(exc).__name__})
        if bv_refs:instructions+=' detail_windows are exact source spans attention marked as important; body_state is own world/self/skill state, never source evidence. Its world.mode counts only completed own digital actions; it says nothing about available source knowledge. self.external_tools limits tool execution, not reading supplied text or reasoning about its constraints.'
        local_gist=None
        if policy=='B1_DETAIL' and (focus or (previous.get('offer') or {}).get('needs_reentry')):  # WP-U7 §3.2A: A bundles fine context for a detail re-entry
            try:
                from .gist import local_bundle,Gist
                base=int(e['source_ref'].get('char_start',0));spans=[]
                for q in (previous.get('offer') or {}).get('quotes') or []:
                    i=text.find(q) if isinstance(q,str) and q else -1
                    if i>=0:spans.append((i,i+len(q)))
                spans+=[(w['source_ref']['char_start']-base,w['source_ref']['char_end']-base) for w in (win or [])]
                bundles=local_bundle(text,e['source_ref'],spans) if spans else []
                if bundles:
                    local_gist={'bundles':len(bundles),'covered':[b['covered'] for b in bundles],'applied':Gist(self.s).mode()=='ACTIVE'}
                    if local_gist['applied']:
                        query['local_gist']=[b['text'] for b in bundles];bv_refs+=[b['source_ref'] for b in bundles]
                        instructions+=' local_gist is provisional nearby context bundled from the exact source; prefer source_segments for exact details.'
            except Exception as exc:self.s.log('local_gist_unavailable',e['event_id'],{'error':type(exc).__name__})
        gist_plan=None
        if role=='B2_GIST' and policy=='B2_GIST' and control!='same_model_prompt_only':  # WP-G G1B: ~8-token gist groups, ~12 slots (SHADOW unless :gist active)
            from .gist import for_offer
            gist_plan,gist_slots=for_offer(self.r,text,e['source_ref'],bool(peer))
            if gist_slots:
                query.pop('source_segments');query['gist_slots']=gist_slots
                instructions+=' gist_slots are exact source groups in order (older parts are coarser); quotes must be exact substrings of them.'
        if role=='B2_GIST' and policy=='B2_GIST':
            query['earlier_context']=[x['native_context'] for x in context]
            instructions+=' Earlier context separates exact source excerpts from fallible prior hypotheses. Use relevant earlier source excerpts when current text leaves a rule unstated; prefer an explicit current-source revision when the same rule changes. Never treat a prior hypothesis as a fact. Select short exact quotes carrying the source rules needed by your summary; only your verified quotes, not the full earlier context, are passed to the answer component. If required evidence is absent, state that uncertainty and request re-entry rather than inventing it. Quotes may cite only current source text or an exact earlier source excerpt, never own-state or hypotheses.'
        select=self.r.cfg.get('b2_quote_select','off') if role=='B2_GIST' and policy=='B2_GIST' else 'off'
        choice_sources=[text]+[x['native_context']['exact_source_excerpt'] for x in context];choices=quote_choices(choice_sources) if select=='pointer' else []
        slots=int(self.r.cfg.get('b2_quote_slots',2)) if choices else 2
        order=self.r.cfg.get('b2_quote_choices','all') if choices and len(choice_sources)>1 else 'all'
        if order!='all':  # WP-Z2i: the current source reaches the answer component anyway
            idx=list(range(1,len(choice_sources)))[::-1 if order=='earlier_newest' else 1]
            choices=[(si,a,b) for si in idx for a,b in sentence_spans(choice_sources[si])][:24] or choices
        if choices:  # WP-Z2c: select exact sentences by number instead of copying them
            query['quote_choices']=[{'id':n+1,'text':choice_sources[si][a:b]} for n,(si,a,b) in enumerate(choices)]
            instructions+=' quote_choices are numbered exact sentences of '+({'all':'the current source and the earlier source excerpts','earlier':'the earlier source excerpts (the current source reaches the answer component anyway)','earlier_newest':'the earlier source excerpts, newest first (the current source reaches the answer component anyway)'}[order])+'. quotes are the ids of at most '+('two' if slots==2 else str(slots))+' choices that carry the source rules your summary needs; their exact text is copied for you.'
        if role=='B1_DETAIL' and policy=='B1_DETAIL' and context:
            query['recent_source']=[x['native_context'] for x in context]
            instructions+=' recent_source is the exact source of the previous turn of this topic. Use its exact details (values, entities) when the current text refers to them without restating them. Quote the exact sentences carrying the details your summary needs; only verified quotes reach the answer component. Prefer an explicit current-source revision.'
        if broadcast:
            query['executive_broadcast']={k:broadcast[k] for k in ['state_version','goal','constraints','source_refs']}
            pf=broadcast.get('permission_flags') or {}  # WP-T2: bodies see the Age envelope C1 granted (stage + rights above Age 0), never a way to widen it
            if pf.get('age') or set(pf.get('rights') or ())-AGE0_RIGHTS:query['executive_broadcast']['age']={'stage':pf.get('age',0),'rights':sorted(set(pf.get('rights') or ())-AGE0_RIGHTS)}
        try:  # WP-N9 §7.5: corollary view of own recent actions reaches B1/B2 (self-state, never a fact)
            from .selfmodel import controller as self_controller
            cv=self_controller(self.r).corollary_view()
            if cv:query['self_corollary']=cv
        except Exception:pass
        jbc_fields=[]
        try:  # WP-N3 §3.4.2 JEF2B bridge: learned extra broadcast fields (ACTIVE only)
            from .jefbridge import controller as jef_controller
            extra,jbc_fields=jef_controller(self.r).bridge_view(role,e,version)
            if extra:query['jef_broadcast']=extra
        except Exception:jbc_fields=[]
        query_packet=packet('QueryPacket','C1_EXEC',e['event_id'],e['brain_generation_id'],[e['source_ref']],target_role=role,goal=text,source_refs=[e['source_ref']],broadcast_packet_id=broadcast['packet_id'] if broadcast else None,peer_message_packet_id=peer_id,source_view_width_chars=width,based_on_state_version=version,probe_only=version==0)
        query_packet.update(context_offer_ids=[x['offer_id'] for x in context],context_source_refs=[x['source_ref'] for x in context],context_chars=len(dumps(query.get('earlier_context',query.get('recent_source')))) if context else 0,state_policy='B2_BOUNDED_SOURCE_CONTEXT' if role=='B2_GIST' else 'B1_SHORT_WINDOW')
        query_packet.update(compute_deadline_monotonic_ns=int(deadline*1e9),offer_valid_until_monotonic_ns=int(valid_until*1e9))
        query_packet['provenance'] += query_packet['context_source_refs']+bv_refs
        if bv:query_packet['bodyview']=bv
        query_packet['jbc_fields']=jbc_fields
        if focus:query_packet['jef_query']=focus
        if gist_plan:query_packet['gist']=gist_plan
        if local_gist:query_packet['local_gist']=local_gist
        self.s.add_packet('QueryPacket',query_packet)
        schema=offer_schema(self.r.cfg['observer_tokens'],**({'quote_min_chars':q} if (q:=self.r.cfg.get('offer_quote_min_chars',0)) else {}))
        if choices:schema['properties']['quotes']['items']={'type':'integer','enum':list(range(1,len(choices)+1))};schema['properties']['quotes']['maxItems']=slots
        runner=None;started=time.monotonic();attempt_status='ERROR'
        try:
            runner=self.r.pool.get(role)
            raw=''.join(runner.generate([{'role':'system','content':instructions},{'role':'user','content':dumps(query)}],self.r.cancel_event,deadline,self.r.cfg['observer_tokens'],schema));attempt_status='FINAL'
        finally:
            metrics=dict(runner.last_metrics) if runner else {'status':'ERROR','duration_s':time.monotonic()-started}
            self.s.log('body_offer_attempt',e['event_id'],{'role':role,'query_packet_id':query_packet['packet_id'],'status':metrics.get('status',attempt_status),'runner':metrics,'context_offer_ids':query_packet['context_offer_ids'],'context_chars':query_packet['context_chars'],'state_policy':query_packet['state_policy']})
        obj=json.loads(raw)
        check(self.r.cancel_event,deadline)
        if set(obj)!=set(OFFER_SCHEMA['required']) or not isinstance(obj['needs_reentry'],bool) or not isinstance(obj['quotes'],list) or not all(isinstance(obj[k],str) for k in ['summary','uncertainty']):raise ValueError('Offer-Schema ungültig')
        refs=[];rejected=0;sources=[(text,e['source_ref'])]+[(x['native_context']['exact_source_excerpt'],x['source_ref']) for x in context]
        wide=self.r.cfg.get('offer_quote_context_chars',0);selected=None
        if select!='off':selected={'mode':select,'choices':len(choices),'raw_quotes':list(obj['quotes'][:3]),'picked':None,'anchored':0}
        if choices:  # ids -> exact sentence text; an id outside the list is dropped
            selected['picked']=[x for x in obj['quotes'] if isinstance(x,int) and not isinstance(x,bool) and 1<=x<=len(choices)]
            obj['quotes']=[choice_sources[choices[x-1][0]][choices[x-1][1]:choices[x-1][2]] for x in selected['picked']]
        elif select=='anchor':
            for n,quote in enumerate(obj['quotes'][:3]):
                if any(quote_span(quote,source,wide) for source,_ in sources):continue
                hit=anchor_span(quote,[source for source,_ in sources])
                if hit:obj['quotes'][n]=sources[hit[0]][0][hit[1]:hit[2]];selected['anchored']+=1
        for quote in obj['quotes'][:max(3,slots)]:
            if wide:  # quote as pointer; the exact-substring lines below stay byte-identical for closed harnesses
                match=next(((source,ref,span) for source,ref in sources if (span:=quote_span(quote,source,wide))),None)
                if not match:rejected+=1;continue
                source,base,(a,b)=match;ref=base|{'char_start':base['char_start']+a,'char_end':base['char_start']+b}
                if ref not in refs:self.s.read_source(ref);refs.append(ref)  # two quotes may point at the same sentences
                continue
            match=next(((source,ref) for source,ref in sources if isinstance(quote,str) and quote and quote in source),None)
            if not match:rejected+=1;continue
            source,base=match;start=base['char_start']+source.index(quote);ref=base|{'char_start':start,'char_end':start+len(quote)};self.s.read_source(ref);refs.append(ref)
        p=packet('OfferPacket',role,e['event_id'],e['brain_generation_id'],[e['source_ref']],role=role,based_on_state_version=version,deadline_monotonic_ns=int(valid_until*1e9),compute_deadline_monotonic_ns=int(deadline*1e9),evidence_refs=refs,offer=obj,confidence=0.,confidence_status='UNCALIBRATED',rejected_quotes=rejected,model_revision=self.r.models.revision(role),native_metrics=runner.last_metrics,query_packet_id=query_packet['packet_id'],broadcast_packet_id=query_packet['broadcast_packet_id'],peer_message_packet_id=peer_id,source_view_width_chars=width)
        if wide:p['quote_context_chars']=wide  # analyst_context accepts the widened spans only for this offer
        p.update(context_offer_ids=query_packet['context_offer_ids'],context_source_refs=query_packet['context_source_refs'],context_chars=query_packet['context_chars'],state_policy=query_packet['state_policy'])
        if selected:p['b2_quote_select']=selected
        p['provenance'] += query_packet['context_source_refs']
        self.s.add_packet('OfferPacket',p);self.retain_body_offer(p);return p
    def analyst_context(self,offers,e,version):
        """Render selected hypotheses and only their source-verified quotations.

        An exact quote proves transport of source text, not semantic truth. A
        retained source merely available to a body is never copied wholesale.
        Persisted Query/Offer bindings, current event/generation/version, exact
        quote equality and source digest/range are rechecked before delivery.
        """
        rendered=[]
        for supplied in offers:
            row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='OfferPacket'",(supplied.get('packet_id'),))
            if not row:raise ValueError('Consumer offer is not stored')
            offer=json.loads(row['payload'])
            if (offer!=supplied or not offer_is_fresh(offer,e['event_id'],e['brain_generation_id'],version)
                    or offer.get('model_revision')!=self.r.models.revision(offer['role'])):
                raise ValueError('Consumer offer binding changed or expired')
            query_row=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='QueryPacket'",(offer.get('query_packet_id'),))
            if not query_row:raise ValueError('Consumer query binding missing')
            query=json.loads(query_row['payload'])
            if (query['event_id']!=e['event_id'] or query['brain_generation_id']!=e['brain_generation_id']
                    or query['target_role']!=offer['role'] or query.get('based_on_state_version')!=version
                    or query['source_refs']!=[e['source_ref']]
                    or query.get('context_source_refs',[])!=offer.get('context_source_refs',[])):
                raise ValueError('Consumer query scope changed')
            allowed=[e['source_ref']]+query.get('context_source_refs',[])
            verified=[]
            for ref in offer['evidence_refs']:
                bound=any(all(ref.get(k)==base.get(k) for k in ('source_id','sha256','modality'))
                    and base['char_start']<=ref['char_start']<ref['char_end']<=base['char_end'] for base in allowed)
                if not bound:raise ValueError('Consumer quote outside supplied source scope')
                text=self.s.read_source(ref);wide=offer.get('quote_context_chars',0)
                if wide and text not in offer['offer'].get('quotes',[]) and len(text)<=wide and any(quote_span(q,text,wide) for q in offer['offer'].get('quotes',[])):
                    # 2026-10-21: an exact source span the offered quote points into (live turn failed 'differs from offered quote' without this)
                    verified.append({'text':text,'source_ref':dict(ref),'verification':'EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE','semantic_truth_authority':False});continue
                if text not in offer['offer'].get('quotes',[]):raise ValueError('Consumer quote differs from offered quote')
                verified.append({'text':text,'source_ref':dict(ref),'verification':'EXACT_SOURCE_SUBSTRING_ONLY',
                                 'semantic_truth_authority':False})
            rendered.append({'role':offer['role'],'offer_packet_id':offer['packet_id'],
                'hypothesis':{k:offer['offer'][k] for k in ('summary','uncertainty','needs_reentry')},
                'hypothesis_authority':'MODEL_HYPOTHESIS_NOT_FACT','verified_quotes':verified})
        return rendered
    def communicate(self,offer,receiver,fast=None):
        if {offer['role'],receiver}!={'B1_DETAIL','B2_GIST'}:raise ValueError('Ungültige B3-Richtung')
        channel=self.r.cfg['channel'];proposal=channel;applied=False;cal=None
        try:  # WP-J B3-5: learned channel policy (SHADOW logs, ACTIVE chooses); LATENT stays unavailable
            from .callosum import controller as callosum_controller
            cal=callosum_controller(self.r)
            try:rev=self.r.models.revision(receiver)
            except Exception:rev=None
            channel,proposal,applied=cal.choose(offer['role'],receiver,channel,rev)
        except Exception as exc:cal=None;self.s.log('callosum_unavailable',offer['event_id'],{'stage':'choose','error':type(exc).__name__})
        if fast and fast.get('learned') and not applied and fast['action']!=channel:channel=fast['action']  # WP-T1 approved channel head (callosum ACTIVE wins)
        refs=offer['evidence_refs'] if channel=='SOURCE_EXACT' else []
        content={}
        if channel=='SOURCE_EXACT':content={'quotes':[self.s.read_source(ref) for ref in refs]}
        elif channel=='CONTROL':content={k:offer['offer'][k] for k in ['needs_reentry','uncertainty']}
        elif channel=='SYMBOLIC':content={'hypothesis':offer['offer']['summary']}
        extra={}
        if cal is not None:
            try:  # §85.2 B3_MESSAGE fields; signed_gain is a proposal to the receiver, never an override
                row=self.s.one("SELECT payload FROM packets WHERE kind='OfferPacket' AND event_id=? AND json_extract(payload,'$.role')=? ORDER BY rowid DESC LIMIT 1",(offer['event_id'],receiver))
                extra=cal.fields(offer,receiver,channel,content,json.loads(row['payload']) if row else None)|{'channel_proposal':proposal,'channel_policy_applied':applied}
                if applied and channel!='NO_MESSAGE':content=dict(content,callosum={'signed_gain':extra['signed_gain'],'urgency':extra['urgency']})
            except Exception as exc:extra={};self.s.log('callosum_unavailable',offer['event_id'],{'stage':'fields','error':type(exc).__name__})
        p=packet('MessagePacket','B3_CALLOSUM',offer['event_id'],offer['brain_generation_id'],refs,channel=channel,sender=offer['role'],receiver=receiver,source_refs=refs,content=content,latent_authority=0,receiver_effect_proven=False,parent_offer_packet_id=offer['packet_id'],**extra)
        self.s.add_packet('MessagePacket',p)
        if cal is not None and extra:
            try:cal.note(offer['event_id'],p['packet_id'],offer['role'],receiver,channel,proposal,applied,extra['signed_gain'])
            except Exception as exc:self.s.log('callosum_unavailable',offer['event_id'],{'stage':'note','error':type(exc).__name__})
        return None if channel=='NO_MESSAGE' else {'message_packet_id':p['packet_id'],'content':content}
    def focal(self,offers,e,version,slots=None):
        # WP-D: the effort plan may narrow the coalition; cfg focal_slots stays the ceiling.
        slots=self.r.cfg['focal_slots'] if slots is None else max(1,min(slots,self.r.cfg['focal_slots']))
        selected=[p for p in offers if offer_is_fresh(p,e['event_id'],e['brain_generation_id'],version)][:slots]
        # Single-pass legacy API (proofs/ablations). The live turn uses focal.FocalLoop (WP-N1).
        from .focal import offer_uncertainty
        for p in selected:
            u=offer_uncertainty(p)
            self.s.add_packet('FocalItem',packet('FocalItem','C4_FOCAL',e['event_id'],e['brain_generation_id'],p['evidence_refs'],item_id=p['packet_id'],source_kind=p['role'],source_refs=p['evidence_refs'],fact_hypothesis_status='HYPOTHESIS',state_type='ACTIVE',salience=0.,uncertainty=u,priority=0.,admission='LEGACY_FIRST_N'))
        return selected
