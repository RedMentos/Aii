"""Hash-bound staged A5 RAW-EAR -> B1/B2/C3 consumer overlay.

The frozen source Runtime is never edited. This overlay runs only after the
existing integrated candidate builder has validated and composed its pinned
runtime/world/arithmetic chain. PCM16 and consent callbacks remain process-local.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

SOURCE_BLOBS = {
    "v13/runtime.py": "30360f40eb784be5ea975ee85e94a57f0b154164",
    "v13/cognition.py": "90138474db6f7c0b66cea24f52d22cd7a6e2f87b",
    "v13/audio_perception_bridge.py": "719034281ee32af4207c8ec407fbf358b9800ad7",
    "v13/audio_ear.py": "86e93ae5b55e76ecd68864a7f51bd477e601e9b6",
    "v13/audio_percept_contract.py": "f3ee37426fc3e3a8cf70f8a107e7074783118a66",
    "v13/a5_audio_admission_bridge.py": "6d8790f29525b4c32c84b5b63d834cfd70a7037e",
    "v13/percept_admission.py": "4f44dc42e8784d1ae3aa71b3cc3c8cb184de8ea4",
    "v13/attention.py": "0f6a81e7380aa6716bbac4e4ef5834d108601a70",
    "v13/contracts.py": "7b21d9c5076015716851b5d432a5730e4e17da92",
}


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _replace(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError("audio candidate semantic anchor mismatch: " + label + " count=" + str(count))
    return raw.replace(old, new, 1)


def _compile(raw: bytes, name: str) -> None:
    compile(raw, name, "exec")


def apply_sources(code_dir: Path, sources: dict[str, bytes]) -> dict[str, bytes]:
    code_dir = Path(code_dir).resolve(strict=True)
    for relative, expected in SOURCE_BLOBS.items():
        path = code_dir / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("audio source missing or symlink: " + relative)
        if _git_blob_sha1(path.read_bytes()) != expected:
            raise ValueError("audio source blob changed: " + relative)

    result = dict(sources)
    runtime = result.get("v13/runtime.py")
    if not isinstance(runtime, bytes):
        raise ValueError("upstream integrated Runtime candidate missing")
    required = (
        b"arithmetic_answer",
        b"LOCAL_EXACT_ARITHMETIC",
        b"source_recall_refs",
        b"latewatch.start",
    )
    if any(marker not in runtime for marker in required):
        raise ValueError("upstream Runtime is not the reviewed arithmetic/context/observer composition")

    runtime = _replace(
        runtime,
        b"class Runtime:\n",
        b'''_AUDIO_WINDOW_FIELDS = {
    "pcm16", "sample_rate", "start_ms", "source_id",
    "consent_receipt", "consent_check",
}


def _validate_audio_window(value):
    """Validate a caller-supplied <=1s PCM16 window without persisting raw audio."""
    if type(value) is not dict or set(value) != _AUDIO_WINDOW_FIELDS:
        raise ValueError("audio_window must use the exact PCM16/consent fields")
    pcm = value["pcm16"]
    rate = value["sample_rate"]
    start = value["start_ms"]
    source_id = value["source_id"]
    receipt = value["consent_receipt"]
    if type(pcm) is not bytes or not pcm or len(pcm) % 2:
        raise ValueError("audio_window requires complete mono PCM16 bytes")
    if type(rate) is not int or not 8000 <= rate <= 48000 or len(pcm) > rate * 2:
        raise ValueError("audio_window exceeds the one-second 8kHz..48kHz limit")
    if type(start) is not int or start < 0:
        raise ValueError("audio_window start_ms must be a nonnegative integer")
    if type(source_id) is not str or not source_id.strip() or len(source_id) > 128:
        raise ValueError("audio_window source_id is invalid")
    if type(receipt) is not str or not receipt.strip() or len(receipt) > 256:
        raise ValueError("audio_window consent receipt is required")
    if not callable(value["consent_check"]):
        raise ValueError("audio_window requires a live consent provider")
    return {key: value[key] for key in _AUDIO_WINDOW_FIELDS}


class Runtime:
''',
        "Runtime audio validator",
    )
    runtime = _replace(
        runtime,
        b"    def submit(self,text):\n        b=len(text.encode())\n",
        b"    def submit(self,text,*,audio_window=None):\n        if audio_window is not None:audio_window=_validate_audio_window(audio_window)\n        b=len(text.encode())+(len(audio_window['pcm16']) if audio_window is not None else 0)\n",
        "submit audio queue bounds",
    )
    runtime = _replace(
        runtime,
        b"            e=self.store.accept_turn(self.session,text,self.cfg['queue_count'],self.cfg['queue_bytes'],self.cfg['input_bytes']);self.jobs.put_nowait(('turn',e,b,time.monotonic()));self.queued_bytes+=b\n",
        b"            e=self.store.accept_turn(self.session,text,self.cfg['queue_count'],self.cfg['queue_bytes'],self.cfg['input_bytes'])\n            if audio_window is not None:e['_audio_window']=audio_window\n            self.jobs.put_nowait(('turn',e,b,time.monotonic()));self.queued_bytes+=b\n",
        "process-local audio queue handoff",
    )
    runtime = _replace(
        runtime,
        b"                    if kind=='turn':self.turn_event=None\n",
        b"                    if kind=='turn':\n                        getattr(self,'_audio_contexts',{}).pop(payload['event_id'],None)\n                        self.turn_event=None\n",
        "audio context lifecycle cleanup",
    )
    runtime = _replace(
        runtime,
        b"    def _turn(self,e):\n        eid=e['event_id']",
        b"    def _audio_context_record(self,eid,audio_result,audio_window):\n"
        b"        \"\"\"Persist derived acoustic features; keep PCM and consent callback process-local.\"\"\"\n"
        b"        if not isinstance(audio_result,dict):return None\n"
        b"        admission=audio_result.get('c3_admission');packet_value=audio_result.get('packet')\n"
        b"        selected=getattr(admission,'selected',()) if admission is not None else ()\n"
        b"        if (getattr(admission,'status',None)!='ADMITTED' or not selected or not isinstance(packet_value,dict)):return None\n"
        b"        source=packet_value.get('source_ref');segments_value=packet_value.get('segments')\n"
        b"        if (type(source) is not dict or type(segments_value) is not list or len(segments_value)!=1\n"
        b"                or packet_value.get('event_id')!=eid or packet_value.get('brain_generation_id')!=self.store.generation_id):return None\n"
        b"        receipt=segments_value[0].get('consent_receipt_ref') if type(segments_value[0]) is dict else None\n"
        b"        check_consent=audio_window.get('consent_check') if type(audio_window) is dict else None\n"
        b"        try:current=check_consent(source.get('source_id'),receipt) if callable(check_consent) else False\n"
        b"        except Exception:current=False\n"
        b"        if current is not True:\n"
        b"            self.store.log('audio_input_unavailable',eid,{'stage':'context_record_consent','reason':'REVOKED_OR_UNAVAILABLE'});return None\n"
        b"        observations=[]\n"
        b"        for item in selected:\n"
        b"            summary=getattr(item,'summary',None);start=getattr(item,'start_ms',None);end=getattr(item,'end_ms',None)\n"
        b"            if (getattr(item,'source_id',None)!=source.get('source_id') or getattr(item,'modality',None)!='audio'\n"
        b"                    or type(summary) is not str or not summary or len(summary)>256 or type(start) is not int\n"
        b"                    or type(end) is not int or start<0 or end<=start or end-start>1000):continue\n"
        b"            observations.append({'source_id':getattr(item,'source_id',None),'modality':'audio','start_ms':start,\n"
        b"                                 'end_ms':end,'summary':summary,'priority':getattr(item,'priority',0)})\n"
        b"        if not observations:return None\n"
        b"        body={'schema':'v14.raw-ear-acoustic-context/1','audio_packet_id':packet_value.get('packet_id'),\n"
        b"              'audio_source_ref':source,'observations':observations,'authority':'ACOUSTIC_FEATURES_ONLY',\n"
        b"              'transcript':None,'learning_authority':False,'action_authority':False}\n"
        b"        summary_ref=self.store.source(dumps(body),'AUDIO_ACOUSTIC_CONTEXT')\n"
        b"        context={'body':body,'summary_source_ref':summary_ref,'source_id':source.get('source_id'),\n"
        b"                 'receipt':receipt,'consent_check':check_consent}\n"
        b"        if not hasattr(self,'_audio_contexts'):self._audio_contexts={}\n"
        b"        self._audio_contexts[eid]=context\n"
        b"        return context\n"
        b"    def _audio_context_view(self,eid,consumer='C3'):\n"
        b"        \"\"\"Revalidate consent and immutable summary provenance at each consumer.\"\"\"\n"
        b"        context=getattr(self,'_audio_contexts',{}).get(eid)\n"
        b"        if not isinstance(context,dict):return None\n"
        b"        check_consent=context.get('consent_check')\n"
        b"        try:current=check_consent(context.get('source_id'),context.get('receipt')) if callable(check_consent) else False\n"
        b"        except Exception:current=False\n"
        b"        if current is not True:\n"
        b"            self.store.log('audio_input_unavailable',eid,{'stage':'consumer_consent','consumer':str(consumer)[:32],\n"
        b"                                                          'reason':'REVOKED_OR_UNAVAILABLE'});return None\n"
        b"        try:\n"
        b"            stored=json.loads(self.store.read_source(context['summary_source_ref']))\n"
        b"            if stored!=context['body']:raise ValueError('audio summary source mismatch')\n"
        b"        except Exception as exc:\n"
        b"            self.store.log('audio_input_unavailable',eid,{'stage':'consumer_source','consumer':str(consumer)[:32],\n"
        b"                                                          'error':type(exc).__name__});return None\n"
        b"        return context['body']|{'summary_source_ref':context['summary_source_ref']}\n"
        b"    def _audio_prompt_layer(self,eid):\n"
        b"        view=self._audio_context_view(eid,'C3')\n"
        b"        if not view:return None,None\n"
        b"        return ('RAW_EAR_ACOUSTIC','\\nRAW_EAR_ACOUSTIC (consent-bound; acoustic features only; not a transcript):',view),view['summary_source_ref']\n"
        b"    def _turn(self,e):\n        audio_window=e.pop('_audio_window',None);audio_result=None;audio_source_ref=None\n        eid=e['event_id']",
        "audio context methods and turn entry",
    )
    runtime = _replace(
        runtime,
        b"                except Exception as exc:self.store.log('attention_unavailable',eid,{'error':type(exc).__name__})\n            exec_state=self.executive.begin",
        b"                except Exception as exc:self.store.log('attention_unavailable',eid,{'error':type(exc).__name__})\n"
        b"            if audio_window is not None and not fixed_policy and arithmetic_answer is None:\n"
        b"                try:\n"
        b"                    from .audio_perception_bridge import consume_pcm16_window\n"
        b"                    audio_result=consume_pcm16_window(self,audio_window['pcm16'],sample_rate=audio_window['sample_rate'],\n"
        b"                        start_ms=audio_window['start_ms'],event_id=eid,generation_id=g,source_id=audio_window['source_id'],\n"
        b"                        consent_receipt=audio_window['consent_receipt'],consent_check=audio_window['consent_check'],token_budget=512)\n"
        b"                    meta['audio_input']={'status':'A5_A4_C3_ADMISSION','packet_id':audio_result['packet']['packet_id'],\n"
        b"                        'source_id':audio_window['source_id'],'capture_authority':'CALLER_SUPPLIED_PCM16',\n"
        b"                        'learning_authority':False,'action_authority':False}\n"
        b"                    audio_context=self._audio_context_record(eid,audio_result,audio_window)\n"
        b"                    meta['audio_input']['context_recorded']=bool(audio_context)\n"
        b"                except Exception as exc:\n"
        b"                    self.store.log('audio_input_unavailable',eid,{'stage':'a5_a4_admission','error':type(exc).__name__})\n"
        b"            elif audio_window is not None:\n"
        b"                meta['audio_input']={'status':'SKIPPED_EXACT_FASTPATH'}\n"
        b"            exec_state=self.executive.begin",
        "A5 admission in the normal turn",
    )
    runtime = _replace(
        runtime,
        b"                volatile=[]\n",
        b"                volatile=[]\n"
        b"                if audio_result is not None:\n"
        b"                    audio_layer,audio_source_ref=self._audio_prompt_layer(eid)\n"
        b"                    admission=audio_result.get('c3_admission')\n"
        b"                    meta['audio_admission']={'status':getattr(admission,'status','UNAVAILABLE'),\n"
        b"                        'selected_count':len(getattr(admission,'selected',()) or ()),\n"
        b"                        'omitted_count':len(getattr(admission,'omitted',()) or ()),\n"
        b"                        'used_tokens_upper_bound':getattr(admission,'used_tokens_upper_bound',0),\n"
        b"                        'c3_prompt_included':bool(audio_layer)}\n"
        b"                    if audio_layer:\n"
        b"                        volatile.append(audio_layer);meta['audio_source_refs']=[audio_source_ref]\n",
        "C3 acoustic context layer",
    )
    runtime = _replace(
        runtime,
        b"provenance=[e['source_ref']]+meta.get('source_recall_refs',[]),budget_scale=body['modulation'].get('context_budget_scale',1.))",
        b"provenance=[e['source_ref']]+meta.get('source_recall_refs',[])+([audio_source_ref] if audio_source_ref else []),budget_scale=body['modulation'].get('context_budget_scale',1.))",
        "Context OS audio provenance",
    )
    runtime = _replace(
        runtime,
        b"                if 'audio_admission' in meta:\n"
        b"                    included=any('RAW_EAR_ACOUSTIC' in (m.get('content') or '') for m in messages)\n"
        b"                    meta['audio_admission']['c3_prompt_included']=included\n"
        b"                    if not included:meta.pop('audio_source_refs',None);audio_source_ref=None\n"
        b"                try:save_context(self.store,self.session,eid,runner.role,messages)  # WP-V5 :context\n",
        b"                except Exception as exc:self.store.log('context_os_unavailable',eid,{'stage':'plan','error':type(exc).__name__})\n"
        b"                if 'audio_admission' in meta:\n"
        b"                    included=any('RAW_EAR_ACOUSTIC' in (m.get('content') or '') for m in messages)\n"
        b"                    meta['audio_admission']['c3_prompt_included']=included\n"
        b"                    if not included:meta.pop('audio_source_refs',None);audio_source_ref=None\n"
        b"                try:save_context",
        "Context OS admission receipt",
    )
    runtime = _replace(
        runtime,
        b"context_refs=[e['source_ref'],*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[]),*meta.get('source_recall_refs',[])]",
        b"context_refs=[e['source_ref'],*meta.get('audio_source_refs',[]),*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[]),*meta.get('source_recall_refs',[])]",
        "C3 context source lineage",
    )

    cognition = (code_dir / "v13/cognition.py").read_bytes()
    cognition = _replace(
        cognition,
        b"    def offer(self,role,e,version,deadline,peer=None,*,valid_until=None,focus=None):\n",
        b"    def _audio_context_query(self,e,role):\n"
        b"        \"\"\"Return consent-rechecked acoustic context separately from quotable text evidence.\"\"\"\n"
        b"        view=self.r._audio_context_view(e['event_id'],consumer=role)\n"
        b"        if not view:return None,[]\n"
        b"        ref=view.get('summary_source_ref')\n"
        b"        if type(ref) is not dict:return None,[]\n"
        b"        return view,[ref]\n"
        b"    def offer(self,role,e,version,deadline,peer=None,*,valid_until=None,focus=None):\n",
        "body audio context accessor",
    )
    cognition = _replace(
        cognition,
        b"        query={'source_segments':view,'peer_message':peer,'prior_hypothesis':prior if policy=='B1_DETAIL' else ''}\n",
        b"        query={'source_segments':view,'peer_message':peer,'prior_hypothesis':prior if policy=='B1_DETAIL' else ''}\n"
        b"        audio_context,audio_context_refs=self._audio_context_query(e,role)\n"
        b"        if audio_context:\n"
        b"            query['audio_context']=audio_context\n"
        b"            instructions+=' audio_context is consent-bound acoustic features only, not a transcript or semantic truth; do not quote it as textual evidence, infer speaker identity, or treat it as learning/action authority.'\n",
        "B1/B2 audio query",
    )
    cognition = _replace(
        cognition,
        b"query_packet.update(context_offer_ids=[x['offer_id'] for x in context],context_source_refs=[x['source_ref'] for x in context],context_chars=len(dumps(query.get('earlier_context',query.get('recent_source')))) if context else 0,state_policy='B2_BOUNDED_SOURCE_CONTEXT' if role=='B2_GIST' else 'B1_SHORT_WINDOW')",
        b"query_packet.update(context_offer_ids=[x['offer_id'] for x in context],context_source_refs=[x['source_ref'] for x in context],context_chars=len(dumps(query.get('earlier_context',query.get('recent_source')))) if context else 0,state_policy='B2_BOUNDED_SOURCE_CONTEXT' if role=='B2_GIST' else 'B1_SHORT_WINDOW',audio_context_refs=audio_context_refs)",
        "QueryPacket audio refs",
    )
    cognition = _replace(
        cognition,
        b"query_packet['provenance'] += query_packet['context_source_refs']+bv_refs+enlightened_refs\n",
        b"query_packet['provenance'] += query_packet['context_source_refs']+bv_refs+enlightened_refs+audio_context_refs\n",
        "QueryPacket provenance",
    )
    cognition = _replace(
        cognition,
        b"'context_chars':query_packet['context_chars'],'state_policy':query_packet['state_policy']})",
        b"'context_chars':query_packet['context_chars'],'audio_context_count':len(audio_context_refs),'state_policy':query_packet['state_policy']})",
        "body offer telemetry",
    )
    cognition = _replace(
        cognition,
        b"                 enlightened_source_refs=enlightened_refs)\n",
        b"                 enlightened_source_refs=enlightened_refs,\n"
        b"                 audio_context_refs=query_packet.get('audio_context_refs',[]))\n",
        "OfferPacket audio refs",
    )
    cognition = _replace(
        cognition,
        b"        p['provenance'] += query_packet['context_source_refs']+enlightened_refs\n",
        b"        p['provenance'] += query_packet['context_source_refs']+enlightened_refs+query_packet.get('audio_context_refs',[])\n",
        "OfferPacket provenance",
    )
    cognition = _replace(
        cognition,
        b"                    or query.get('enlightened_source_refs',[])!=offer.get('enlightened_source_refs',[])):\n",
        b"                    or query.get('enlightened_source_refs',[])!=offer.get('enlightened_source_refs',[])\n"
        b"                    or query.get('audio_context_refs',[])!=offer.get('audio_context_refs',[])):\n",
        "analyst audio scope binding",
    )
    cognition = _replace(
        cognition,
        b"                raise ValueError('Consumer query scope changed')\n            allowed=[e['source_ref']]+query.get('context_source_refs',[])+query.get('enlightened_source_refs',[])\n",
        b"                raise ValueError('Consumer query scope changed')\n"
        b"            for audio_ref in query.get('audio_context_refs',[]):\n"
        b"                audio_text=self.s.read_source(audio_ref)\n"
        b"                audio_context=query.get('audio_context')\n"
        b"                if not isinstance(audio_context,dict):raise ValueError('Consumer audio context missing')\n"
        b"                supplied={k:v for k,v in audio_context.items() if k!='summary_source_ref'}\n"
        b"                if json.loads(audio_text)!=supplied:raise ValueError('Consumer audio context source mismatch')\n"
        b"            allowed=[e['source_ref']]+query.get('context_source_refs',[])+query.get('enlightened_source_refs',[])\n",
        "analyst audio source verification",
    )

    arithmetic = result.get("v13/arithmetic_reflex.py")
    if not isinstance(arithmetic, bytes):
        arithmetic = (code_dir / "v13/arithmetic_reflex.py").read_bytes()
    arithmetic = _replace(
        arithmetic,
        b"(?:what\\s+is|what's|was\\s+ist|berechne|calculate)",
        b"(?:what\\s+is|what's|was\\s+ist|berechne|calculate|compute|wie\\s+viel\\s+ist|wieviel\\s+ist)",
        "explicit arithmetic prefix",
    )
    arithmetic = _replace(
        arithmetic,
        b"    match = _PATTERN.fullmatch(text)\n",
        b"    # Bare subtraction shaped like a calendar date is ambiguous. Require an explicit math cue.\n"
        b"    explicit = re.match(r\"\\s*(?:what\\s+is|what's|was\\s+ist|berechne|calculate|compute|wie\\s+viel\\s+ist|wieviel\\s+ist)\\s+\", text, re.IGNORECASE)\n"
        b"    date_shape = re.fullmatch(r\"\\s*(?:\\d{4}\\s*-\\s*\\d{1,2}|\\d{1,2}\\s*-\\s*\\d{1,2})\\s*\\??\\s*\", text)\n"
        b"    if date_shape and explicit is None:\n"
        b"        return None\n"
        b"    match = _PATTERN.fullmatch(text)\n",
        "date-shaped subtraction abstention",
    )

    _compile(runtime, "v13/runtime.py")
    _compile(cognition, "v13/cognition.py")
    _compile(arithmetic, "v13/arithmetic_reflex.py")
    result.update({
        "v13/runtime.py": runtime,
        "v13/cognition.py": cognition,
        "v13/arithmetic_reflex.py": arithmetic,
    })
    return result
