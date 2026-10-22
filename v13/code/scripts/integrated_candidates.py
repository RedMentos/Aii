"""Reviewed changes integrated into the live runtime, as one ordered chain.

After the SourceHandoff cohort closed (2026-10-12), the merged approval-reader
+ native firing candidate was written into the live sources byte-exactly.
Later reviewed runtime changes to the same files are appended to `_later`.
Candidate regressions stay runnable: a candidate loader accepts live sources
only when they are the exact frozen baseline, its own complete candidate, or
this exact integrated chain. Anything else still fails shut.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRING_SNAPSHOT = 'docs/proofs/continuation-20261011/native-firing-runtime-baseline'
NAMES = ('v13/runners.py', 'v13/memory_server.py', 'v13/runtime.py', 'v13/store.py')
INTEGRATED = ('approval_reader_runtime_candidate', 'native_firing_runtime_candidate', 'native_cache_bounds', 'schema_order', 'resource_modes', 'observer_schedule', 'b2_offer', 'quote_context', 'eligibility_live', 'tool_answer_first', 'runner_seed')

NATIVE_CACHE_ARGS = '''def native_cache_args(cfg):
    # b10964 defaults (--cache-ram 8192 MiB host prompt cache, 32 context
    # checkpoints per slot) assume a desktop. Qwen3.5 checkpoints are ~19 MiB
    # each (docs/NATIVE_CACHE.md), so a 6 GB phone needs explicit bounds.
    from .config import DEFAULTS
    ram=cfg.get('native_cache_ram_mb',DEFAULTS['native_cache_ram_mb'])
    checkpoints=cfg.get('native_ctx_checkpoints',DEFAULTS['native_ctx_checkpoints'])
    return ['--cache-ram',str(ram),'--ctx-checkpoints',str(checkpoints)]
'''


def _replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Integrated anchor changed: '+old[:80])
    return text.replace(old, new, 1)


def native_cache_bounds(sources):
    """2026-10-12 thread G: bound host prompt cache and context checkpoints."""
    out = dict(sources)
    t = out['v13/runners.py']
    t = _replace(t, 'def rotate_log(path,cap=3*1024*1024):', NATIVE_CACHE_ARGS+'def rotate_log(path,cap=3*1024*1024):')
    t = _replace(t, '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n',
                 '"-ngl","0","--no-warmup","--no-webui","--log-disable"]\n        cmd += native_cache_args(self.cfg)\n')
    out['v13/runners.py'] = t
    return out


WIRE_JSON = '''def wire_json(v):
    """Request body for llama-server. Unlike common.dumps it keeps key order: the server builds the JSON-schema
    grammar in property order, so sorting would make the model decide e.g. `action` before `options` or
    `needs_reentry` before `summary` (WP-W1). Hashes/logs keep using the sorted common.dumps."""
    return json.dumps(v,ensure_ascii=False,separators=(",",":"),allow_nan=False)
'''


def schema_order(sources):
    """2026-10-12 thread H (WP-W1): llama-server request bodies keep schema key order."""
    out = dict(sources)
    t = out['v13/runners.py']
    t = _replace(t, 'from .resources import process_memory\n', 'from .resources import process_memory\n'+WIRE_JSON)
    t = _replace(t, 'conn.request(method,path,dumps(payload)', 'conn.request(method,path,wire_json(payload)')
    t = _replace(t, "conn.request('POST','/completion',dumps(payload|", "conn.request('POST','/completion',wire_json(payload|")
    t = _replace(t, 'conn.request("POST","/completion",dumps(payload)', 'conn.request("POST","/completion",wire_json(payload)')
    out['v13/runners.py'] = t
    return out


def resource_modes(sources):
    """2026-10-12 thread N (§97.2): GREEN/YELLOW/ORANGE/RED resource modes in the turn, replay and telemetry."""
    out = dict(sources)
    t = out['v13/runtime.py']
    t = _replace(t, 'from .resources import snapshot,ResourceGuard,prune_runner_logs\n',
                 'from .resources import snapshot,ResourceGuard,prune_runner_logs\nfrom . import resource_modes as rmodes\n')
    t = _replace(t, '(self.cfg);self.notify=notify or',
                 '(self.cfg);self.guard.load_profile(self.store);self.notify=notify or')
    t = _replace(t, '            check(self.cancel_event,deadline);resource=self.resources();state=self.guard.update(resource)\n',
                 "            check(self.cancel_event,deadline);resource=self.resources();state=self.guard.update(resource)\n            rmode=self.guard.mode;rpol=rmodes.policy(rmode);meta['resource_mode']={'mode':rmode,'reasons':list(self.guard.reasons),'profile':self.guard.profile.get('status')}  # §97.2\n")
    t = _replace(t, "ressure=0. if state=='NORMAL' else 1.,provide",
                 "ressure=rpol['focal_pressure'],provide")
    t = _replace(t, 'lf.cfg,resource,state);version=exec_',
                 'lf.cfg,resource,rmode);version=exec_')
    t = _replace(t, 'deadline=deadline,top_k=top_k)\n',
                 "deadline=deadline,top_k=rmodes.scaled(self.cfg['memory_top_k'] if top_k is None else top_k,rmode,'context_scale'))  # §97.2 YELLOW+: less context\n")
    t = _replace(t, 'agectl.controller(self),state)\n',
                 'agectl.controller(self),rmode)\n')
    t = _replace(t, 'rce_state=state,observer_window_',
                 'rce_state=state,resource_mode=rmode,observer_window_')
    t = _replace(t, "ect and state=='NORMAL' and sel",
                 "ect and rpol['learned_wake'] and sel")
    t = _replace(t, "h'} and state=='NORMAL' and not",
                 "h'} and rpol['max_observer_bodies'] and not")
    t = _replace(t, "effort.roles(wake_route);peers={};observer_seconds=max(1.,self.cfg['observer_seconds']*effort_plan['observer_scale'])",
                 "rmodes.cap_roles(effort.roles(wake_route),rmode);peers={};observer_seconds=max(1.,self.cfg['observer_seconds']*effort_plan['observer_scale'])  # §97.2 ORANGE: one body")
    t = _replace(t, "ressure=0. if state=='NORMAL' else 1.,world_e",
                 "ressure=rpol['focal_pressure'],world_e")
    t = _replace(t, "t() and self.guard.state=='NORMAL':\n",
                 "t() and rmodes.policy(self.guard.mode)['background_observers']:\n")
    t = _replace(t, "            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']\n",
                 "            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']\n            background_roles=rmodes.cap_roles(background_roles,self.guard.mode,'background_observers')  # §97.2 YELLOW: one post-commit body\n")
    t = _replace(t, "f.resources())!='NORMAL':break\n",
                 "f.resources())!='NORMAL' or not rmodes.policy(self.guard.mode)['background_observers']:break\n")
    t = _replace(t, "        if not isinstance(count,int) or not 1<=count<=16:raise ValueError('Replay-Anzahl 1..16')\n",
                 "        if not isinstance(count,int) or not 1<=count<=16:raise ValueError('Replay-Anzahl 1..16')\n        self.guard.update(self.resources());count=rmodes.scaled(count,self.guard.mode,'replay_scale')  # §97.2: YELLOW halves, ORANGE/RED none\n        if not count:raise Limits('Replay pausiert wegen RAM-/Temperaturlimit (Modus '+self.guard.mode+')')\n")
    t = _replace(t, "effective_config':dict(self.cfg)}\n",
                 "effective_config':dict(self.cfg),'resource_mode':self.guard.mode}\n")
    out['v13/runtime.py'] = t
    t = out['v13/store.py']
    t = _replace(t, "TELEMETRY_ENUMS.update('OBSERVED_NATIVE_WRITES REQUEST_WRITES_ONLY REQUEST_NOT_FINAL REQUEST_NOT_COMPLETED REQUEST_BINDING_CHANGED AUDIT_LOG_CHANGED AUDIT_LOG_UNREADABLE AUDIT_WINDOW_LIMIT NO_REQUEST_WINDOW MULTIPLE_NATIVE_STEPS NO_PROMPT_MARKER NO_EVALUATED_ROWS MULTIPLE_REQUESTS NO_REQUEST_OBSERVATION AUDIT_BINDING_OR_AUTHORITY_INVALID INVALID_REQUEST_ROW_MAP'.split())\n",
                 "TELEMETRY_ENUMS.update('OBSERVED_NATIVE_WRITES REQUEST_WRITES_ONLY REQUEST_NOT_FINAL REQUEST_NOT_COMPLETED REQUEST_BINDING_CHANGED AUDIT_LOG_CHANGED AUDIT_LOG_UNREADABLE AUDIT_WINDOW_LIMIT NO_REQUEST_WINDOW MULTIPLE_NATIVE_STEPS NO_PROMPT_MARKER NO_EVALUATED_ROWS MULTIPLE_REQUESTS NO_REQUEST_OBSERVATION AUDIT_BINDING_OR_AUTHORITY_INVALID INVALID_REQUEST_ROW_MAP'.split())\nTELEMETRY_FIELDS.update('resource_mode orange_mb yellow_mb'.split())  # §97.2 resource modes\nTELEMETRY_ENUMS.update('GREEN YELLOW ORANGE RED UNCALIBRATED DEVICE_MEASURED HOST_MEASURED_NOT_REDMI MEM_BELOW_RED MEM_BELOW_ORANGE MEM_BELOW_YELLOW TEMP_AT_RED TEMP_AT_ORANGE TEMP_AT_YELLOW'.split())\n")
    out['v13/store.py'] = t
    return out


def observer_schedule(sources):
    """2026-10-12 thread N (§22.2.4/§73): observer scheduling knob in the turn and post-commit pass; telemetry."""
    out = dict(sources)
    t = out['v13/runtime.py']
    t = _replace(t, 'from . import resource_modes as rmodes\n',
                 'from . import resource_modes as rmodes\nfrom . import observer_schedule as obsched\n')
    t = _replace(t, '         def ask(role,focus=None):\n',
                 '         def ask(role,focus=None,use_peer=True):\n')
    t = _replace(t, ',peers.get(role),valid_until=dea',
                 ',peers.get(role) if use_peer else None,valid_until=dea')
    t = _replace(t, "                for role in roles:\n                    if time.monotonic()+1>=observer_end:break\n                    try:offers.append(ask(role))\n                    except Cancelled:raise\n                    except Exception as exc:self.store.log('offer_rejected',eid,{'role':role,'error':str(exc)[:300]})\n",
                 "                sched=obsched.plan(self.cfg.get('observer_schedule',obsched.DEFAULT),roles,eid,self.cfg.get('observer_sample_rate',.5),parallel_ok=rpol['max_observer_bodies']>1 and bool(getattr(getattr(self.pool,'fabric',None),'enabled',False)))  # §22.2.4 deployment knob\n                meta['observer_schedule']={k:sched[k] for k in ('schedule','pre','parallel','post','reason')}\n                offers+=obsched.run(sched,lambda role,use_peer:ask(role,use_peer=use_peer),observer_end,lambda role,exc:self.store.log('offer_rejected',eid,{'role':role,'error':str(exc)[:300]}),cancelled=(Cancelled,))\n")
    t = _replace(t, "            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']\n",
                 "            background_roles={'none':[],'detail':['B1_DETAIL'],'gist':['B2_GIST'],'both':['B1_DETAIL','B2_GIST']}[wake_decision['action']] if wake_decision and wake_decision['learned'] else ['B1_DETAIL','B2_GIST']\n            background_roles=obsched.background(self.cfg.get('observer_schedule',obsched.DEFAULT),eid,self.cfg.get('observer_sample_rate',.5),background_roles,(meta.get('observer_schedule') or {}).get('post'))  # §22.2.4\n")
    out['v13/runtime.py'] = t
    t = out['v13/store.py']
    t = _replace(t, "TELEMETRY_FIELDS.update('resource_mode orange_mb yellow_mb'.split())  # §97.2 resource modes\n",
                 "TELEMETRY_FIELDS.update('resource_mode orange_mb yellow_mb'.split())  # §97.2 resource modes\nTELEMETRY_FIELDS.update('observer_schedule schedule pre post parallel sampled rss_mb'.split())  # §22.2.4 observer scheduling, §73 RSS budget\nTELEMETRY_ENUMS.update('A_THEN_B_SEQUENTIAL B_THEN_A_SEQUENTIAL ALWAYS_BOTH_ASYNC JEF_FIRST_THEN_BOTH SAMPLED_OBSERVER ON_DEMAND_REENTRY ASYNC_NEEDS_TWO_RESIDENT_BODIES SAMPLED_OUT ON_DEMAND_ONLY RSS_OVER_YELLOW RSS_OVER_ORANGE B1_DETAIL B2_GIST'.split())\n")
    out['v13/store.py'] = t
    return out


def b3_degrade(sources):
    """2026-10-12 thread N (B3-H10): telemetry fields/enums for the B3 latent degradation ladder."""
    out = dict(sources)
    t = out['v13/store.py']
    t = _replace(t, "TELEMETRY_ENUMS.update('GREEN YELLOW ORANGE RED UNCALIBRATED DEVICE_MEASURED HOST_MEASURED_NOT_REDMI MEM_BELOW_RED MEM_BELOW_ORANGE MEM_BELOW_YELLOW TEMP_AT_RED TEMP_AT_ORANGE TEMP_AT_YELLOW'.split())\n",
                 "TELEMETRY_ENUMS.update('GREEN YELLOW ORANGE RED UNCALIBRATED DEVICE_MEASURED HOST_MEASURED_NOT_REDMI MEM_BELOW_RED MEM_BELOW_ORANGE MEM_BELOW_YELLOW TEMP_AT_RED TEMP_AT_ORANGE TEMP_AT_YELLOW'.split())\nTELEMETRY_FIELDS.update('direction level_from level_to triggers'.split())  # WP-N19 B3-H10 degradation\nTELEMETRY_ENUMS.update('B1_TO_B2 B2_TO_B1 L4 L3 L2 L1 EXACT_SYMBOLIC NO_MESSAGE RECEIVER_REVISION_CHANGED RUNNER_REVISION_CHANGED CALIBRATION_EXPIRED PROJECTOR_COLLAPSED ROUTER_DRIFT EXPERT_FLIP_SPIKE RETENTION_REGRESSED MESSAGE_UTILITY_FELL COST_OVER_BUDGET ROLE_DIVERSITY_COLLAPSED PROMOTED_EXPLICIT_HUMAN'.split())\n")
    out['v13/store.py'] = t
    return out


B2_OFFER_PATCH = 'docs/proofs/continuation-20261013/b2-offer-candidate/cognition.patch'


def b2_offer(text):
    """2026-10-13 thread O, integrated by thread G: two cfg switches for B2 offers, both off = previous behaviour.
    b2_offer_body_state=False leaves body_state out of B2 offers; offer_quote_min_chars=N lengthens quotes within
    the same budget. Same edits as the archived, preregistered candidate patch (B2_OFFER_PATCH), except that the
    offer call passes quote_min_chars only when it is set: with the switch off the call is byte-for-byte the old one,
    so closed harnesses that wrap offer_schema(tokens) (rule_transport_ablation) keep running unchanged."""
    t = _replace(text, 'def offer_schema(tokens):\n', 'def offer_schema(tokens,quote_min_chars=0):\n')
    t = _replace(t, '    uncertainty 15 % of what is left after ~30 tokens of JSON syntax. BOOT estimate, not tuned."""\n',
                 '    uncertainty 15 % of what is left after ~30 tokens of JSON syntax. BOOT estimate, not tuned.\n'
                 '    quote_min_chars (cfg offer_quote_min_chars, 0 = off) raises the quote cap so one whole source sentence fits."""\n')
    t = _replace(t, "    pr['quotes']['maxItems']=2;pr['quotes']['items']['maxLength']=max(24,int(chars*.2))\n    return s\n",
                 "    pr['quotes']['maxItems']=2;pr['quotes']['items']['maxLength']=max(24,int(chars*.2))\n"
                 "    if quote_min_chars>pr['quotes']['items']['maxLength']:\n"
                 "        # Thread O STEP2 producer ablation: 57-char quotes cut every earlier rule sentence (~80 chars) before its last\n"
                 "        # rule (\"... Local-\"). A longer quote takes its room from the summary, so the worst case stays within budget.\n"
                 "        q=min(int(quote_min_chars),(chars-48-pr['uncertainty']['maxLength'])//2)  # never beyond the budget\n"
                 "        if q>pr['quotes']['items']['maxLength']:\n"
                 "            pr['quotes']['items']['maxLength']=q;pr['summary']['maxLength']=chars-2*q-pr['uncertainty']['maxLength']\n"
                 "    return s\n")
    t = _replace(t, "            bs=bodyview.body_state(self.r,e,role,text)\n",
                 "            # Thread O STEP2 producer ablation: body_state hijacked 41/50 B2 offers; cfg b2_offer_body_state=False leaves it out for B2.\n"
                 "            bs=None if policy=='B2_GIST' and not self.r.cfg.get('b2_offer_body_state',True) else bodyview.body_state(self.r,e,role,text)\n")
    t = _replace(t, "offer_schema(self.r.cfg['observer_tokens'])));attempt_status='FINAL'",
                 "offer_schema(self.r.cfg['observer_tokens'],**({'quote_min_chars':q} if (q:=self.r.cfg.get('offer_quote_min_chars',0)) else {}))));attempt_status='FINAL'")
    return t


QUOTE_SPAN = """def quote_span(quote,source,context_chars=0):
    \"\"\"(start,end) of a body quote inside source, or None. context_chars 0 (live): exact substring only.
    context_chars>0 (cfg offer_quote_context_chars, 2026-10-20 STEP2 B2->C3 transport): a quote that differs from the
    source only in letter case or whitespace still verifies, and a quote of >= 12 chars grows to its whole sentences,
    then to neighbouring sentences of the same source while the span stays within context_chars. The quote is only a
    pointer; the transported text is always the exact source span (Qwen B2 split, cut or re-cased the earlier
    rule, so its full text reached C3 in only 7/30 STEP2 retain offers).\"\"\"
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
    sents=[(m.start(),m.end()) for m in re.finditer(r'\\S.*?(?:[.!?](?=\\s|$)|$)',source,re.S)]
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
"""


def quote_context(text):
    """2026-10-20 STEP2 B2->C3 thread: cfg offer_quote_context_chars (0 = off = previous behaviour, byte-for-byte the
    old verification) lets a body quote point at its exact source sentences instead of having to copy them."""
    if 'def quote_span(' in text:
        raise ValueError('Integrated anchor changed: quote_context already applied')
    t = _replace(text, 'class Cognition:\n', QUOTE_SPAN+'class Cognition:\n')
    t = _replace(t, "        for quote in obj['quotes'][:3]:\n",
                 "        wide=self.r.cfg.get('offer_quote_context_chars',0)\n"
                 "        for quote in obj['quotes'][:3]:\n"
                 "            if wide:  # quote as pointer; the exact-substring lines below stay byte-identical for closed harnesses\n"
                 "                match=next(((source,ref,span) for source,ref in sources if (span:=quote_span(quote,source,wide))),None)\n"
                 "                if not match:rejected+=1;continue\n"
                 "                source,base,(a,b)=match;ref=base|{'char_start':base['char_start']+a,'char_end':base['char_start']+b}\n"
                 "                if ref not in refs:self.s.read_source(ref);refs.append(ref)  # two quotes may point at the same sentences\n"
                 "                continue\n")
    t = _replace(t, "        p.update(context_offer_ids=query_packet['context_offer_ids'],",
                 "        if wide:p['quote_context_chars']=wide  # analyst_context accepts the widened spans only for this offer\n"
                 "        p.update(context_offer_ids=query_packet['context_offer_ids'],")
    anchor = "                text=self.s.read_source(ref)\n                if text not in offer['offer'].get('quotes',[]):raise"
    if anchor in t:  # analyst_context exists only on the SourceHandoff-changed side of the frozen candidate views
        t = _replace(t, anchor,
                     "                text=self.s.read_source(ref);wide=offer.get('quote_context_chars',0)\n"
                     "                if wide and text not in offer['offer'].get('quotes',[]) and len(text)<=wide and any(quote_span(q,text,wide) for q in offer['offer'].get('quotes',[])):\n"
                     "                    # 2026-10-21: an exact source span the offered quote points into (live turn failed 'differs from offered quote' without this)\n"
                     "                    verified.append({'text':text,'source_ref':dict(ref),'verification':'EXACT_SOURCE_SENTENCES_POINTED_BY_QUOTE','semantic_truth_authority':False});continue\n"
                     "                if text not in offer['offer'].get('quotes',[]):raise")
    return t


def eligibility_live(sources):
    """2026-10-21 thread Q: ToolStep.plan gets the selected body offers and the state version, so the eligibility tool
    can use their source-verified quotes as earlier exact evidence (it only acts when the user enabled `eligibility`)."""
    out = dict(sources)
    out['v13/runtime.py'] = _replace(out['v13/runtime.py'], 'try:tool_plan=toolctl.ToolStep(self).plan(e,text)  #',
                                     'try:tool_plan=toolctl.ToolStep(self).plan(e,text,offers=selected,version=version)  #')
    return out


def tool_answer_first(sources):
    """2026-10-22 (thread „STEP2-Nutzen Engpass“): with cfg tool_answer_first the executed eligibility decision is the first
    visible sentence of the answer (ToolStep.lead), the body only continues; for UNKNOWN/NONE the fixed text is the whole
    answer (ToolStep.lead_final, no generation); default off = unchanged turn."""
    out = dict(sources)
    out['v13/runtime.py'] = _replace(out['v13/runtime.py'], "                leading_output=''\n                lw=latewatch.start(",
        "                leading_output=''\n"
        "                lead=toolctl.ToolStep(self).lead(tool_result) if tool_result and tool_result.get('result') is not None else None\n"
        "                if lead:  # cfg tool_answer_first: the exact tool decision is the first visible sentence, the body continues\n"
        "                    txctl.commit_output(self.store,mid,eid,meta);meta['first_output_monotonic_ns']=time.monotonic_ns()\n"
        "                    final=toolctl.ToolStep(self).lead_final(tool_result);lead=final or lead\n"
        "                    self.store.append_message(mid,lead+('' if final else ' '));output=lead+('' if final else ' ');meta['tool_answer_first']='FINAL' if final else 'LEAD'\n"
        "                lw=latewatch.start(")
    out['v13/runtime.py'] = _replace(out['v13/runtime.py'], 'for token in runner.generate(messages,self.cancel_event,deadline,**output_kwargs):',
                                     "for token in (() if meta.get('tool_answer_first')=='FINAL' else runner.generate(messages,self.cancel_event,deadline,**output_kwargs)):")
    return out


def runner_seed(sources):
    """2026-10-22 (WP-Z2b offen c): the native runner used seed 13 whatever cfg['seed'] said (STEP2 body offers ignored
    their seed). A call without an explicit seed now uses cfg['seed']; the default cfg seed is 13, so default turns are
    unchanged."""
    out = dict(sources)
    t = _replace(out['v13/runners.py'], "def generate(self,messages,cancel,deadline,max_tokens=None,schema=None,seed=13,first_token_bias=None,confidence_field='summary'):",
                 "def generate(self,messages,cancel,deadline,max_tokens=None,schema=None,seed=None,first_token_bias=None,confidence_field='summary'):")
    out['v13/runners.py'] = _replace(t, '"seed":seed,', '"seed":self.cfg.get("seed",13) if seed is None else seed,')
    return out


def _later(sources):
    return runner_seed(tool_answer_first(eligibility_live(b3_degrade(observer_schedule(resource_modes(schema_order(native_cache_bounds(sources))))))))


def _baseline(root):
    folder = root/FIRING_SNAPSHOT
    manifest = json.loads((folder/'manifest.json').read_text())
    if manifest.get('schema') != 'NATIVE_FIRING_RUNTIME_BASELINE_V1' or set(manifest['files']) != set(NAMES):
        raise ValueError('Integrated baseline manifest changed')
    original = {}
    for name, expected in manifest['files'].items():
        data = (folder/Path(name).name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Integrated baseline digest changed: '+name)
        original[name] = data.decode()
    return original


def _chain(full):
    from scripts import approval_reader_runtime_candidate as reader
    from scripts import native_firing_runtime_candidate as firing
    full = dict(full)
    full.update(reader.transform({k: full[k] for k in reader.NAMES}))
    return _later(firing.transform(full))


def integrated_sources(root=ROOT):
    """Frozen baseline -> approval reader -> native firing -> later changes."""
    return _chain(_baseline(root))


def overlay(original, root=ROOT):
    """Baseline files with the integrated files replaced, if live equals that."""
    expected = integrated_sources(root)
    view = {name: expected.get(name, text) for name, text in original.items()}
    actual = {name: (root/name).read_text() for name in original}
    return view if actual == view else None


def rebase(texts, root=ROOT):
    """Apply the same integrated chain to another candidate's view.

    Files of `texts` outside the integrated set are returned unchanged; the
    remaining integrated files come from the digest-bound baseline.
    """
    full = _baseline(root)
    full.update({k: v for k, v in texts.items() if k in NAMES})
    out = _chain(full)
    out = {k: (out[k] if k in NAMES else v) for k, v in texts.items()}
    if 'v13/cognition.py' in out:  # cognition.py is bound exactly by source_handoff_candidate, not by NAMES
        out['v13/cognition.py'] = quote_context(b2_offer(out['v13/cognition.py']))
    return out


def write_live(root=ROOT):
    """Write the integrated chain to the live files (used once per change)."""
    for name, text in integrated_sources(root).items():
        (root/name).write_text(text)
