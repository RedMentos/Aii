"""Hash-bound staged A5 RAW-EAR -> B1/B2/C3 consumer overlay.

The frozen source Runtime is never edited. This overlay runs only after the
existing integrated candidate builder has validated and composed its pinned
runtime/world/arithmetic chain. PCM16 and consent callbacks remain process-local.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_BLOBS = {
    "v13/runtime.py": "30360f40eb784be5ea975ee85e94a57f0b154164",
    "v13/cognition.py": "06de0acf2c6d30d50301d5073f5569822edff813",
    "v13/audio_perception_bridge.py": "719034281ee32af4207c8ec407fbf358b9800ad7",
    "v13/audio_voice_cues.py": "4c5641adf6758762ce0fdf616a9b2a798e6de408",
    "v13/audio_speaker_evidence.py": "37aa9c392bbb68d60ccff9749c75b41b8783c539",
    "v13/audio_temporal_evidence.py": "098ce2ec6bb0b744166d711a3401b7acf0252de1",
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
        b'''_AUDIO_WINDOW_REQUIRED_FIELDS = {
    "pcm16", "sample_rate", "start_ms", "source_id",
    "consent_receipt", "consent_check", "consent_guard", "finality",
}
# Optional only for text-only fallback; when supplied, the callback must register both revoke phases.
_AUDIO_WINDOW_OPTIONAL_FIELDS = {"consent_revocation_subscribe"}


def _validate_audio_window(value):
    """Validate bounded caller PCM16 and process-local consent callbacks."""
    if (type(value) is not dict
            or not _AUDIO_WINDOW_REQUIRED_FIELDS.issubset(value)
            or set(value) - _AUDIO_WINDOW_REQUIRED_FIELDS - _AUDIO_WINDOW_OPTIONAL_FIELDS):
        raise ValueError("audio_window must use the exact PCM16/consent fields")
    pcm = value["pcm16"]
    rate = value["sample_rate"]
    start = value["start_ms"]
    source_id = value["source_id"]
    receipt = value["consent_receipt"]
    finality = value["finality"]
    if type(finality) is not str or finality not in ("PROVISIONAL", "FINAL"):
        raise ValueError("audio_window finality must be PROVISIONAL or FINAL")
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
    if not callable(value["consent_guard"]):
        raise ValueError("audio_window requires a linearizable consent guard")
    if ("consent_revocation_subscribe" in value
            and not callable(value["consent_revocation_subscribe"])):
        raise ValueError("audio_window revocation subscription must be callable")
    result = {key: value[key] for key in _AUDIO_WINDOW_REQUIRED_FIELDS}
    if "consent_revocation_subscribe" in value:
        result["consent_revocation_subscribe"] = value["consent_revocation_subscribe"]
    return result


class Runtime:
''',
        "Runtime audio validator",
    )
    runtime = _replace(
        runtime,
        b"    def submit(self,text):\n        b=len(text.encode())\n",
        b"    def submit(self,text,*,audio_window=None):\n        if audio_window is not None:audio_window=_validate_audio_window(audio_window)\n        text_bytes=len(text.encode())\n        b=text_bytes+(len(audio_window['pcm16']) if audio_window is not None else 0)\n",
        "submit audio queue bounds",
    )
    runtime = _replace(
        runtime,
        b"        if b>self.cfg['input_bytes']:raise Limits('Eingabe zu lang: '+str(self.cfg['input_bytes'])+' Bytes')\n",
        b"        if text_bytes>self.cfg['input_bytes']:raise Limits('Eingabe zu lang: '+str(self.cfg['input_bytes'])+' Bytes')\n",
        "text-only input byte limit",
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
        b"                    if kind=='turn':\n                        try:\n                            from .audio_context_store import finish_turn\n                            finish_turn(self,payload['event_id'])\n                        except Exception as exc:self.store.log('audio_context_cleanup_failed',payload['event_id'],{'error':type(exc).__name__})\n                        self.turn_event=None\n",
        "audio context lifecycle cleanup",
    )
    runtime = _replace(
        runtime,
        b"    def _turn(self,e):\n        eid=e['event_id']",
        b"    def _audio_context_record(self,eid,audio_result,audio_window):\n"
        b"        from .audio_context_store import record\n"
        b"        return record(self,eid,audio_result,audio_window)\n"
        b"    def _audio_context_view(self,eid,consumer='C3'):\n"
        b"        from .audio_context_store import view\n"
        b"        return view(self,eid,consumer)\n"
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
        b"                    from .audio_voice_cues import consume_pcm16_voice_window\n"
        b"                    audio_result=consume_pcm16_voice_window(self,audio_window['pcm16'],sample_rate=audio_window['sample_rate'],\n"
        b"                        start_ms=audio_window['start_ms'],event_id=eid,generation_id=g,source_id=audio_window['source_id'],\n"
        b"                        consent_receipt=audio_window['consent_receipt'],consent_check=audio_window['consent_check'],consent_guard=audio_window['consent_guard'],consent_lease=audio_window.get('_consent_lease'),\n"
        b"                        token_budget=512,finality=audio_window['finality'])\n"
        b"                    meta['audio_input']={'status':'A5_A4_C3_VOICE_CUE_ADMISSION','packet_id':audio_result['packet']['packet_id'],\n"
        b"                        'voice_activity_hint':audio_result['a4']['voice_activity_hint'],\n"
        b"                        'voice_cue_method':audio_result['a4']['voice_cues']['method'],\n"
        b"                        'source_id':audio_window['source_id'],'finality':audio_window['finality'],\n"
        b"                        'capture_authority':'CALLER_SUPPLIED_PCM16',\n"
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
        b"                try:save_context(self.store,self.session,eid,runner.role,messages)  # WP-V5 :context\n",
        b"                if 'audio_admission' in meta:\n"
        b"                    included=any('RAW_EAR_ACOUSTIC' in (m.get('content') or '') for m in messages)\n"
        b"                    meta['audio_admission']['c3_prompt_included']=included\n"
        b"                    if not included:meta.pop('audio_source_refs',None);audio_source_ref=None\n"
        b"                try:save_context(self.store,self.session,eid,runner.role,messages)  # WP-V5 :context\n",
        "Context OS admission receipt",
    )
    runtime = _replace(
        runtime,
        b"                try:save_context(self.store,self.session,eid,runner.role,messages)  # WP-V5 :context\n",
        b"                if audio_source_ref is not None and self._audio_context_view(eid,'C3_NATIVE_DISPATCH') is None:\n"
        b"                    volatile=[item for item in volatile if item[0]!='RAW_EAR_ACOUSTIC']\n"
        b"                    try:\n"
        b"                        cplan=ctxos.controller(self).plan(eid,runner.role,stable,volatile,history_records,text,verdicts=[x['verdict'] for x in focal_run['inquisition']] if focal_run else [],warm_ids=warm_ids,provenance=[e['source_ref']],budget_scale=body['modulation'].get('context_budget_scale',1.))\n"
        b"                        messages=cplan['messages'];meta['context_plan']={'packet_id':cplan['packet_id'],'applied':cplan['applied']}\n"
        b"                    except Exception as exc:\n"
        b"                        self.store.log('context_os_unavailable',eid,{'stage':'audio_revocation_rebuild','error':type(exc).__name__})\n"
        b"                        sys=stable+''.join(head+dumps(value) for _,head,value in volatile)\n"
        b"                        messages=[{'role':'system','content':sys}]+history+[{'role':'user','content':text}]\n"
        b"                    try:save_context(self.store,self.session,eid,runner.role,messages)\n"
        b"                    except Exception as exc:self.store.log('context_save_failed',eid,{'stage':'audio_revocation_rebuild','error':type(exc).__name__})\n"
        b"                    if 'audio_admission' in meta:meta['audio_admission'].update(status='REVOKED_BEFORE_C3_DISPATCH',c3_prompt_included=False)\n"
        b"                    meta.pop('audio_source_refs',None);audio_source_ref=None\n"
        b"                    if 'audio_input' in meta:meta['audio_input']['context_revoked_before_c3']=True\n"
        b"                try:save_context(self.store,self.session,eid,runner.role,messages)  # WP-V5 :context\n",
        "C3 revoke-before-dispatch rebuild",
    )
    runtime = _replace(
        runtime,
        b"context_refs=[e['source_ref'],*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[]),*meta.get('source_recall_refs',[])]",
        b"context_refs=[e['source_ref'],*meta.get('audio_source_refs',[]),*self.consolidation.source_refs(memories),*history_refs,*meta.get('duplex_handoff_refs',[]),*meta.get('source_recall_refs',[])]",
        "C3 context source lineage",
    )

    cognition_base = (code_dir / "v13/cognition.py").read_bytes()
    # Preserve upstream Cognition overlays (notably fair B1/B2 recovery scheduling).
    cognition = result.get("v13/cognition.py", cognition_base)
    if not isinstance(cognition, bytes):
        raise ValueError("upstream integrated Cognition candidate missing")
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
        b"audio_context_packet = ({'body': {k:v for k,v in audio_context.items() if k!='summary_source_ref'}, 'summary_source_ref': audio_context['summary_source_ref']} if audio_context else None)\n"
        b"        query_packet.update(context_offer_ids=[x['offer_id'] for x in context],context_source_refs=[x['source_ref'] for x in context],context_chars=len(dumps(query.get('earlier_context',query.get('recent_source')))) if context else 0,state_policy='B2_BOUNDED_SOURCE_CONTEXT' if role=='B2_GIST' else 'B1_SHORT_WINDOW',audio_context_refs=audio_context_refs,audio_context=audio_context_packet)",
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
        b"        self.s.add_packet('QueryPacket',query_packet)\n",
        b"        if query_packet.get('audio_context_refs'):\n"
        b"            current_audio,current_audio_refs=self._audio_context_query(e,role)\n"
        b"            if current_audio_refs!=query_packet.get('audio_context_refs',[]):\n"
        b"                removed_audio_refs=query_packet.get('audio_context_refs',[])\n"
        b"                query.pop('audio_context',None);query_packet.pop('audio_context',None)\n"
        b"                query_packet['audio_context_refs']=[];query_packet['audio_context_count']=0\n"
        b"                query_packet['provenance']=[ref for ref in query_packet.get('provenance',[]) if ref not in removed_audio_refs]\n"
        b"                audio_context_refs=[]\n"
        b"                self.s.log('audio_offer_omitted',e['event_id'],{'role':role,'reason':'CONSENT_REVOKED_BEFORE_DISPATCH'})\n"
        b"        self.s.add_packet('QueryPacket',query_packet)\n",
        "B1/B2 pre-dispatch consent recheck",
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
        b"            audio_context,current_audio_refs=self._audio_context_query(e,offer['role'])\n"
        b"            if current_audio_refs!=query.get('audio_context_refs',[]):\n"
        b"                self.s.log('audio_offer_omitted',e['event_id'],{'role':offer['role'],'reason':'CONSENT_OR_SOURCE_REVOKED'});continue\n"
        b"            persisted_audio_context=query.get('audio_context')\n"
        b"            if current_audio_refs:\n"
        b"                expected_audio_context={'body':{k:v for k,v in audio_context.items() if k!='summary_source_ref'},'summary_source_ref':current_audio_refs[0]}\n"
        b"                if persisted_audio_context!=expected_audio_context:\n"
        b"                    self.s.log('audio_offer_omitted',e['event_id'],{'role':offer['role'],'reason':'QUERY_CONTEXT_MISMATCH'});continue\n"
        b"            elif persisted_audio_context is not None:\n"
        b"                self.s.log('audio_offer_omitted',e['event_id'],{'role':offer['role'],'reason':'UNEXPECTED_QUERY_CONTEXT'});continue\n"
        b"            audio_context_valid=True\n"
        b"            for audio_ref in query.get('audio_context_refs',[]):\n"
        b"                try:\n"
        b"                    audio_text=self.s.read_source(audio_ref)\n"
        b"                    supplied={k:v for k,v in audio_context.items() if k!='summary_source_ref'}\n"
        b"                    if json.loads(audio_text)!=supplied:audio_context_valid=False;break\n"
        b"                except Exception:audio_context_valid=False;break\n"
        b"            if not audio_context_valid:\n"
        b"                self.s.log('audio_offer_omitted',e['event_id'],{'role':offer['role'],'reason':'STORED_SOURCE_MISMATCH'});continue\n"
        b"            # Acoustic refs are provenance only; they are never quotable text evidence.\n"
        b"            allowed=[e['source_ref']]+query.get('context_source_refs',[])+query.get('enlightened_source_refs',[])\n",
        "analyst audio source verification",
    )

    arithmetic = result.get("v13/arithmetic_reflex.py")
    if not isinstance(arithmetic, bytes):
        arithmetic = (code_dir / "v13/arithmetic_reflex.py").read_bytes()
    if (b"def exact_arithmetic(" not in arithmetic
            or b"Fraction" not in arithmetic or b"eval(" in arithmetic):
        raise ValueError("arithmetic source module lacks the bounded exact-arithmetic contract")


    runtime += b'''
# The provider lease spans producer -> derived context -> B1/B2 -> full C3 generation.
_AUDIO_ORIGINAL_TURN = Runtime._turn


def _audio_lease_turn(self, event):
    from .audio_context_store import sweep_revoked, revoke_source, has_context

    try:
        sweep_revoked(self)
    except Exception as exc:
        self.store.log("audio_input_unavailable", event.get("event_id"),
                       {"stage": "pre_turn_revocation_sweep", "error": type(exc).__name__})

    window = event.get("_audio_window")
    if type(window) is not dict:
        return _AUDIO_ORIGINAL_TURN(self, event)

    source_id = window.get("source_id")
    receipt = window.get("consent_receipt")
    event_id = event.get("event_id")
    generation_id = self.store.generation_id
    self.turn_event = event
    subscribe = window.get("consent_revocation_subscribe")
    unsubscribe = None
    request_seen = threading.Event()
    lease_active = threading.Event()

    # One provider subscription must register both phases: request-cancel
    # before waiting for the guard, then tombstone cleanup after guard release.
    if not callable(subscribe):
        event.pop("_audio_window", None)
        self.store.log("audio_input_unavailable", event_id,
                       {"stage": "two_phase_revocation_subscription_required"})
        return _AUDIO_ORIGINAL_TURN(self, event)

    def on_revoke_requested():
        request_seen.set()
        if lease_active.is_set():
            active = getattr(self, "turn_event", None)
            if (getattr(self, "current", None) == "turn"
                    and isinstance(active, dict)
                    and active.get("event_id") == event_id
                    and self.store.generation_id == generation_id):
                self.cancel_event.set()

    def on_revoked():
        return revoke_source(self, source_id, receipt)

    try:
        unsubscribe = subscribe(
            source_id, receipt, generation_id, on_revoke_requested, on_revoked,
        )
        if not callable(unsubscribe):
            raise TypeError("two-phase consent revocation subscription must return unsubscribe")
        window["_consent_revocation_unsubscribe"] = unsubscribe
    except Exception as exc:
        if callable(unsubscribe):
            try:
                unsubscribe()
            except Exception:
                pass
        event.pop("_audio_window", None)
        self.store.log("audio_input_unavailable", event_id,
                       {"stage": "revocation_subscription", "error": type(exc).__name__})
        return _AUDIO_ORIGINAL_TURN(self, event)

    from .audio_voice_cues import audio_consent_lease
    try:
        manager = audio_consent_lease(
            self, source_id, generation_id, receipt,
            window.get("consent_check"), window.get("consent_guard"),
        )
        lease = manager.__enter__()
        lease_active.set()
        if request_seen.is_set():
            self.cancel_event.set()
    except Exception as exc:
        lease_active.clear()
        if callable(unsubscribe):
            try:
                unsubscribe()
            except Exception:
                pass
        event.pop("_audio_window", None)
        self.store.log("audio_input_unavailable", event_id,
                       {"stage": "runtime_consent_lease", "error": type(exc).__name__})
        return _AUDIO_ORIGINAL_TURN(self, event)

    window["_consent_lease"] = lease
    try:
        try:
            result = _AUDIO_ORIGINAL_TURN(self, event)
        except BaseException as exc:
            manager.__exit__(type(exc), exc, exc.__traceback__)
            lease_active.clear()
            raise
        else:
            manager.__exit__(None, None, None)
            lease_active.clear()
            return result
    finally:
        lease_active.clear()
        window.pop("_consent_lease", None)
        try:
            sweep_revoked(self)
        except Exception as exc:
            self.store.log("audio_input_unavailable", event_id,
                           {"stage": "post_turn_revocation_sweep", "error": type(exc).__name__})
        if callable(unsubscribe) and not has_context(self, event_id):
            try:
                unsubscribe()
            except Exception as exc:
                self.store.log("audio_input_unavailable", event_id,
                               {"stage": "revocation_unsubscribe", "error": type(exc).__name__})


Runtime._turn = _audio_lease_turn

_AUDIO_ORIGINAL_CLOSE = Runtime.close


def _audio_lease_close(self, *args, **kwargs):
    if getattr(self, "closed", False):
        return None
    # First stop/cancel and join the real worker. Never tombstone an acoustic
    # source while C3 may still be reading it under the provider lease.
    with self.lock:
        self.stop.set()
        self.cancel_event.set()
        self.wake.set()
    worker = getattr(self, "worker", None)
    if worker is threading.current_thread():
        raise RuntimeError("Runtime.close cannot clean audio from its worker thread; Store remains open")
    if worker is not None:
        worker.join(6)
        if worker.is_alive():
            self.pool.unload()
            self.needle.unload()
            kill_process(self.learner.proc)
            worker.join(4)
        if worker.is_alive():
            raise RuntimeError("Worker beendet sich noch; Store bleibt zum Schutz offen")
    # The iterator and consent guard are now released; Store is still open.
    from .audio_context_store import close_runtime
    close_runtime(self)
    return _AUDIO_ORIGINAL_CLOSE(self, *args, **kwargs)


Runtime.close = _audio_lease_close
'''

    _compile(runtime, "v13/runtime.py")
    _compile(cognition, "v13/cognition.py")
    _compile(arithmetic, "v13/arithmetic_reflex.py")

    result["v13/audio_context_store.py"] = b'''"""Process-local consent-bound acoustic context with revocation tombstones."""
import json
import threading
from pathlib import Path

from .common import dumps

_MAX_REVOCATION_CONTEXTS = 64


def _lock(runtime):
    lock = getattr(runtime, "_audio_context_lock", None)
    if lock is None:
        lock = threading.RLock()
        runtime._audio_context_lock = lock
    return lock


def _lease(window, runtime, source_id, receipt):
    lease = None
    if type(window) is dict:
        lease = window.get("_consent_lease") or window.get("consent_lease")
    from .audio_voice_cues import AudioConsentLease
    if not isinstance(lease, AudioConsentLease) or not lease.matches(
        runtime, source_id, runtime.store.generation_id, receipt,
    ):
        raise PermissionError("a live Runtime-wide source-bound audio consent lease is required")
    return lease


def _revoke(runtime, event_id, context):
    """Delete persisted packet/context references bound to a revoked audio source."""
    store = getattr(runtime, "store", None)
    if store is None:
        return False
    ref = context.get("summary_source_ref") if type(context) is dict else None
    derived_id = ref.get("source_id") if type(ref) is dict else None
    blob_hash = ref.get("sha256") if type(ref) is dict else None
    source_id = context.get("source_id") if type(context) is dict else None
    source_ids = {value for value in (source_id, derived_id) if type(value) is str and value}
    if (type(blob_hash) is not str or len(blob_hash) != 64
            or any(char not in "0123456789abcdef" for char in blob_hash)):
        blob_hash = None

    deleted_packet_ids = set()
    active_blob_refs = None
    blob_removed = False

    def contains_source(value):
        if isinstance(value, dict):
            if value.get("source_id") in source_ids:
                return True
            return any(contains_source(child) for child in value.values())
        if isinstance(value, list):
            return any(contains_source(child) for child in value)
        return False

    # Store.mutex is an RLock: hold it across the transaction and final unlink
    # so Store.source() cannot create a live reference between count and unlink.
    with store.mutex:
        with store.tx() as connection:
            for packet_row in connection.execute("SELECT id,payload FROM packets").fetchall():
                try:
                    payload = json.loads(packet_row["payload"])
                except (TypeError, ValueError):
                    continue
                if contains_source(payload):
                    deleted_packet_ids.add(packet_row["id"])
            for packet_id in deleted_packet_ids:
                connection.execute("DELETE FROM packets WHERE id=?", (packet_id,))
            if type(derived_id) is str and blob_hash:
                connection.execute(
                    "UPDATE sources SET deleted=1 "
                    "WHERE id=? AND hash=? AND kind='AUDIO_ACOUSTIC_CONTEXT' AND deleted=0",
                    (derived_id, blob_hash),
                )
                active_blob_refs = connection.execute(
                    "SELECT COUNT(*) FROM sources WHERE hash=? AND deleted=0",
                    (blob_hash,),
                ).fetchone()[0]
        if blob_hash and active_blob_refs == 0:
            blob_root = Path(store.home) / "data/blobs"
            for blob_path in (blob_root / blob_hash, blob_root / (blob_hash + ".z")):
                try:
                    existed = blob_path.exists()
                    blob_path.unlink(missing_ok=True)
                    blob_removed = blob_removed or (existed and not blob_path.exists())
                except OSError as exc:
                    store.log(
                        "audio_context_cleanup_failed", event_id,
                        {"stage": "blob_unlink", "error": type(exc).__name__},
                    )

    try:
        from .inputs import CONTEXT_KEY
        key = CONTEXT_KEY + runtime.session
        saved, version = store.state(key, None)
        if isinstance(saved, dict) and saved.get("event_id") == event_id:
            saved_messages = dumps(saved.get("messages"))
            preview = saved.get("preview")
            if "RAW_EAR_ACOUSTIC" in saved_messages or (
                isinstance(preview, str) and "RAW_EAR_ACOUSTIC" in preview
            ):
                store.set_state(
                    key,
                    {"event_id": event_id, "role": saved.get("role"),
                     "messages": None, "truncated": False, "chars": 0, "preview": ""},
                    expected=version,
                )
    except Exception as exc:
        store.log(
            "audio_context_cleanup_failed", event_id,
            {"stage": "last_native_context", "error": type(exc).__name__},
        )

    with _lock(runtime):
        active = getattr(runtime, "_audio_contexts", None)
        if isinstance(active, dict) and active.get(event_id) is context:
            active.pop(event_id, None)
        registry = getattr(runtime, "_audio_revocation_contexts", None)
        if isinstance(registry, dict) and registry.get(event_id) is context:
            registry.pop(event_id, None)
    unsubscribe = context.get("consent_revocation_unsubscribe") if type(context) is dict else None
    if callable(unsubscribe):
        try:
            unsubscribe()
        except Exception as exc:
            store.log(
                "audio_context_cleanup_failed", event_id,
                {"stage": "revocation_unsubscribe", "error": type(exc).__name__},
            )
    store.log(
        "audio_context_revoked", event_id,
        {"packets_deleted": len(deleted_packet_ids),
         "blob_removed": blob_removed,
         "active_blob_refs": active_blob_refs if active_blob_refs is not None else 0},
    )
    return True

def _remember(runtime, event_id, context):
    evicted = []
    with _lock(runtime):
        registry = getattr(runtime, "_audio_revocation_contexts", None)
        if not isinstance(registry, dict):
            registry = {}
            runtime._audio_revocation_contexts = registry
        registry[event_id] = context
        while len(registry) > _MAX_REVOCATION_CONTEXTS:
            old_event, old_context = next(iter(registry.items()))
            registry.pop(old_event, None)
            evicted.append((old_event, old_context))
    for old_event, old_context in evicted:
        _revoke(runtime, old_event, old_context)


def revoke_source(runtime, source_id, receipt):
    """Tombstone every derived context bound to one revoked source receipt."""
    with _lock(runtime):
        registry = getattr(runtime, "_audio_revocation_contexts", {})
        contexts = list(registry.items()) if isinstance(registry, dict) else []
    revoked = 0
    for event_id, context in contexts:
        if context.get("source_id") == source_id and context.get("receipt") == receipt:
            _revoke(runtime, event_id, context)
            revoked += 1
    return revoked


def sweep_revoked(runtime):
    """Recheck prior receipts outside any held lease and remove revoked context."""
    with _lock(runtime):
        registry = getattr(runtime, "_audio_revocation_contexts", {})
        contexts = list(registry.items()) if isinstance(registry, dict) else []
    revoked = 0
    for event_id, context in contexts:
        check = context.get("consent_check")
        try:
            active = callable(check) and check(context.get("source_id"), context.get("receipt")) is True
        except Exception:
            active = False
        if not active:
            _revoke(runtime, event_id, context)
            revoked += 1
    return revoked


def has_context(runtime, event_id):
    with _lock(runtime):
        registry = getattr(runtime, "_audio_revocation_contexts", {})
        return isinstance(registry, dict) and event_id in registry


def finish_turn(runtime, event_id):
    """Remove the turn-only reader cache but retain a revocation handle."""
    with _lock(runtime):
        contexts = getattr(runtime, "_audio_contexts", None)
        if isinstance(contexts, dict):
            contexts.pop(event_id, None)


def close_runtime(runtime):
    """Tombstone contexts only after the Runtime worker has released every reader lease."""
    worker = getattr(runtime, "worker", None)
    if worker is not None and worker.is_alive():
        raise RuntimeError("cannot tombstone audio context while Runtime worker is active")
    with _lock(runtime):
        registry = getattr(runtime, "_audio_revocation_contexts", {})
        contexts = list(registry.items()) if isinstance(registry, dict) else []
    for event_id, context in contexts:
        _revoke(runtime, event_id, context)
    return len(contexts)


def record(runtime, event_id, audio_result, audio_window):
    if not isinstance(audio_result, dict) or type(audio_window) is not dict:
        return None
    admission = audio_result.get("c3_admission")
    packet_value = audio_result.get("packet")
    selected = getattr(admission, "selected", ()) if admission is not None else ()
    if getattr(admission, "status", None) != "ADMITTED" or not selected or not isinstance(packet_value, dict):
        return None
    source = packet_value.get("source_ref")
    segments_value = packet_value.get("segments")
    if (type(source) is not dict or type(segments_value) is not list or len(segments_value) != 1
            or packet_value.get("event_id") != event_id
            or packet_value.get("brain_generation_id") != runtime.store.generation_id):
        return None
    segment = segments_value[0]
    if type(segment) is not dict or segment.get("finality") != "FINAL":
        runtime.store.log("audio_input_unavailable", event_id,
                          {"stage": "context_record_finality", "reason": "PROVISIONAL_OR_INVALID"})
        return None
    try:
        from .audio_voice_cues import validate_voice_cues
        voice_cues = validate_voice_cues((segment.get("acoustic") or {}).get("voice_cues"))
    except Exception:
        runtime.store.log("audio_input_unavailable", event_id,
                          {"stage": "voice_cue_validation", "reason": "MISSING_OR_INVALID"})
        return None
    receipt = segment.get("consent_receipt_ref")
    source_id = source.get("source_id")
    if source_id != audio_window.get("source_id") or receipt != audio_window.get("consent_receipt"):
        return None
    try:
        lease = _lease(audio_window, runtime, source_id, receipt)
        observations = []
        for item in selected:
            summary = getattr(item, "summary", None)
            start = getattr(item, "start_ms", None)
            end = getattr(item, "end_ms", None)
            if (getattr(item, "source_id", None) != source_id
                    or getattr(item, "modality", None) != "audio"
                    or type(summary) is not str or not summary or len(summary) > 256
                    or type(start) is not int or type(end) is not int
                    or start < 0 or end <= start or end - start > 1000):
                continue
            observations.append({
                "source_id": source_id, "modality": "audio",
                "start_ms": start, "end_ms": end,
                "summary": summary, "priority": getattr(item, "priority", 0),
            })
        if not observations:
            return None
        body = {
            "schema": "v14.raw-ear-acoustic-context/1",
            "audio_packet_id": packet_value.get("packet_id"),
            "audio_source_ref": source,
            "observations": observations,
            "voice_cues": voice_cues,
            "authority": "ACOUSTIC_FEATURES_ONLY",
            "transcript": None,
            "learning_authority": False,
            "action_authority": False,
        }
        summary_ref = runtime.store.source(dumps(body), "AUDIO_ACOUSTIC_CONTEXT")
        context = {
            "body": body, "summary_source_ref": summary_ref,
            "source_id": source_id, "receipt": receipt,
            "consent_check": audio_window.get("consent_check"),
            "consent_lease": lease,
            "consent_revocation_unsubscribe": audio_window.get("_consent_revocation_unsubscribe"),
        }
        with _lock(runtime):
            if not hasattr(runtime, "_audio_contexts"):
                runtime._audio_contexts = {}
            runtime._audio_contexts[event_id] = context
        _remember(runtime, event_id, context)
        return context
    except Exception as exc:
        runtime.store.log("audio_input_unavailable", event_id,
                          {"stage": "context_record_consent", "reason": type(exc).__name__})
        return None


def view(runtime, event_id, consumer="C3"):
    with _lock(runtime):
        context = getattr(runtime, "_audio_contexts", {}).get(event_id)
    if not isinstance(context, dict):
        return None
    try:
        _lease(context, runtime, context.get("source_id"), context.get("receipt"))
        stored = json.loads(runtime.store.read_source(context["summary_source_ref"]))
        if stored != context["body"]:
            raise ValueError("audio summary source mismatch")
        return context["body"] | {"summary_source_ref": context["summary_source_ref"]}
    except Exception as exc:
        _revoke(runtime, event_id, context)
        runtime.store.log(
            "audio_input_unavailable", event_id,
            {"stage": "consumer_consent", "consumer": str(consumer)[:32],
             "reason": "REVOKED_OR_UNAVAILABLE" if isinstance(exc, PermissionError) else "SOURCE_REVOKED_OR_MISMATCH"},
        )
        return None
'''

    result.update({
        "v13/runtime.py": runtime,
        "v13/cognition.py": cognition,
        "v13/arithmetic_reflex.py": arithmetic,
    })
    return result
