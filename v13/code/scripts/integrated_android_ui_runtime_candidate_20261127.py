"""Pinned overlay for signed MediaProjection UI frames in the ordinary V13 turn.

The source Runtime/Cognition/Operator stay on their reviewed base blobs. This
builder applies the normal-turn consumer only to the isolated staged output,
after the existing arithmetic, observer, audio, C4, native-receiver and
greeting overlays. No screen capture is started here; the companion must
already be paired/trusted and hold a live user-approved OS consent receipt.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_BLOBS = {
    "v13/android_ui_runtime.py": "9df5e5b55bd94e67b12d5467db8ea511a55011d8",
    "v13/android_companion_runtime.py": "a4df8e974ffd46b3a8e56ffce359ac45c6a719a2",
    "v13/android_companion_ui_frames.py": "4d0ec9a7cce593b64f56415a7f48ebe92a68672f",
}
REQUIRED_FILES = (
    "v13/android_companion_transport.py",
    "v13/android_companion_ecdsa.py",
    "v13/android_capabilities.py",
    "v13/android_control.py",
    "v13/android_outcomes.py",
    "v13/a5_ui_admission_bridge.py",
    "v13/vision_ui_frame_ingress.py",
)


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _replace_once(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError(
            "Android UI overlay anchor mismatch: " + label + " count=" + str(count)
        )
    return raw.replace(old, new, 1)


def _append_offer_parameter(raw: bytes) -> bytes:
    marker = b"    def offer("
    if raw.count(marker) != 1:
        raise ValueError("Android UI overlay expected exactly one Cognition.offer")
    start = raw.index(marker)
    end = raw.find(b"):", start)
    if end < 0:
        raise ValueError("Cognition.offer signature is malformed")
    signature = raw[start:end]
    if b"ui_context" in signature:
        raise ValueError("Cognition.offer already has an Android UI parameter")
    return raw[:end] + b",ui_context=None" + raw[end:]


def _bind_ui_offer_scope(raw: bytes) -> bytes:
    """Bind UI metadata without dropping the audio-source lineage added upstream."""
    base_anchor = (
        b"                    or query.get('enlightened_source_refs',[])!=offer.get('enlightened_source_refs',[])):\n"
    )
    audio_anchor = (
        b"                    or query.get('enlightened_source_refs',[])!=offer.get('enlightened_source_refs',[])\n"
        b"                    or query.get('audio_context_refs',[])!=offer.get('audio_context_refs',[])):\n"
    )
    base_count = raw.count(base_anchor)
    audio_count = raw.count(audio_anchor)
    if audio_count == 1 and base_count == 0:
        anchor = audio_anchor
    elif base_count == 1 and audio_count == 0:
        anchor = base_anchor
    else:
        raise ValueError(
            "Android UI overlay anchor mismatch: source-bound query/offer scope "
            + f"base={base_count} audio={audio_count}"
        )
    replacement = (
        b"                    or query.get('enlightened_source_refs',[])!=offer.get('enlightened_source_refs',[])\n"
        b"                    or query.get('audio_context_refs',[])!=offer.get('audio_context_refs',[])\n"
        b"                    or query.get('ephemeral_ui_binding')!=offer.get('ephemeral_ui_binding')\n"
        b"                    or query.get('ephemeral_ui_source_refs',[])!=offer.get('ephemeral_ui_source_refs',[])):\n"
    )
    return raw.replace(anchor, replacement, 1)




def _ask_block_bounds(raw: bytes) -> tuple[int, int]:
    marker = b"                def ask("
    if raw.count(marker) != 1:
        raise ValueError("Android UI overlay expected exactly one normal B1/B2 ask function")
    start = raw.index(marker)
    line_end = raw.find(b"\n", start)
    if line_end < 0:
        raise ValueError("Android UI overlay B1/B2 ask signature is unterminated")
    signature = raw[start:line_end]
    prefix = b"                def ask(role,focus=None,use_peer=True"
    if not signature.startswith(prefix) or not signature.endswith(b"):"):
        raise ValueError("Android UI overlay B1/B2 ask signature changed")
    params = signature[len(b"                def ask("):-2].split(b",")
    if params[:3] != [b"role", b"focus=None", b"use_peer=True"]:
        raise ValueError("Android UI overlay B1/B2 ask parameters changed")
    extras = params[3:]
    allowed = {b"role_end=None", b"preanswer_budgeted=True"}
    if any(item not in allowed for item in extras) or len(set(extras)) != len(extras):
        raise ValueError("Android UI overlay B1/B2 ask has unsupported optional parameters")
    end = raw.find(b"\n                sched=", line_end)
    if end < 0:
        raise ValueError("Android UI overlay cannot bound the B1/B2 ask function")
    return start, end


def _patch_runtime(raw: bytes) -> bytes:
    if b"ui_frame_stack" in raw or b"current_turn_context" in raw:
        raise ValueError("Android UI Runtime overlay is already present")
    if b"import contextlib\n" not in raw:
        raise ValueError("Runtime lacks the reviewed ExitStack dependency")

    raw = _replace_once(
        raw,
        b"        self.turn_event=e;self.bodies.begin_turn(eid)\n",
        b"        self.turn_event=e;self.bodies.begin_turn(eid)\n"
        b"        ui_frame_stack=contextlib.ExitStack();ui_context=None\n",
        "turn-scoped UI lease stack",
    )
    raw = _replace_once(
        raw,
        b"            mark('preanswer_observers')\n",
        b"            mark('preanswer_observers')\n"
        b"            if not direct:\n"
        b"                try:\n"
        b"                    from .android_ui_runtime import current_turn_context\n"
        b"                    ui_context=ui_frame_stack.enter_context(current_turn_context(self,text,goal=text))\n"
        b"                    if ui_context:meta['ui_observation']=dict(ui_context['audit'])\n"
        b"                except Cancelled:raise\n"
        b"                except Exception as exc:\n"
        b"                    if self.cancel_event.is_set():raise Cancelled('Android UI observation revoked') from exc\n"
        b"                    self.store.log('android_ui_context_unavailable',eid,{'error':type(exc).__name__})\n",
        "open consent-bound A5 UI scope before body observers",
    )

    start, end = _ask_block_bounds(raw)
    block = raw[start:end]
    if block.count(b"valid_until=deadline") != 1 or b"ui_context=ui_context" in block:
        raise ValueError("Android UI overlay B1/B2 call is changed or ambiguous")
    block = block.replace(
        b"valid_until=deadline",
        b"valid_until=deadline,ui_context=ui_context",
        1,
    )
    raw = raw[:start] + block + raw[end:]

    raw = _replace_once(
        raw,
        b"                mark('native_answer')\n",
        b"                if runner is not None and runner.role=='C3_LANGUAGE' and ui_context is not None and ui_context.get('text'):\n"
        b"                    from .android_ui_runtime import append_c3_ui_context\n"
        b"                    messages=append_c3_ui_context(messages,ui_context,eid,g)\n"
        b"                    if isinstance(meta.get('ui_observation'),dict):meta['ui_observation']['c3_context_attached']=True\n"
        b"                mark('native_answer')\n",
        "same-turn C3 context read before native generation",
    )
    raw = _replace_once(
        raw,
        b"        finally:\n            meta['native_pressure']=monitor.stop()\n",
        b"        finally:\n"
        b"            try:ui_frame_stack.close()\n"
        b"            except Exception as close_exc:self.store.log('android_ui_context_close_failed',eid,{'error':type(close_exc).__name__})\n"
        b"            meta['native_pressure']=monitor.stop()\n",
        "release UI lease after C3 and other turn consumers",
    )
    raw = _replace_once(
        raw,
        b"            self.jobs.task_done()\n"
        b"        self.pool.unload();self.needle.unload();self.memory.semantic_keys.encoder.unload();self.store.close();self.closed=True\n",
        b"            self.jobs.task_done()\n"
        b"        controller=getattr(self,'_android_companion_controller',None)\n"
        b"        if controller is not None:\n"
        b"            try:controller.close()\n"
        b"            except Exception as exc:self.store.log('android_companion_close_failed',None,{'error':type(exc).__name__})\n"
        b"        self.pool.unload();self.needle.unload();self.memory.semantic_keys.encoder.unload();self.store.close();self.closed=True\n",
        "close companion provider on Runtime shutdown",
    )
    return raw


def _patch_cognition(raw: bytes) -> bytes:
    if b"ui_binding=None;ui_refs=[]" in raw or b"ephemeral_ui_binding" in raw:
        raise ValueError("Android UI Cognition overlay is already present")
    raw = _append_offer_parameter(raw)
    raw = _replace_once(
        raw,
        b"        query={'source_segments':view,'peer_message':peer,'prior_hypothesis':prior if policy=='B1_DETAIL' else ''}\n",
        b"        query={'source_segments':view,'peer_message':peer,'prior_hypothesis':prior if policy=='B1_DETAIL' else ''}\n"
        b"        ui_binding=None;ui_refs=[]\n"
        b"        if ui_context is not None:\n"
        b"            from .android_ui_runtime import body_ui_query\n"
        b"            ui_query,ui_binding,ui_refs=body_ui_query(ui_context,e['event_id'],e['brain_generation_id'])\n"
        b"            if ui_query:\n"
        b"                query.update(ui_query)\n"
        b"                instructions+=' current_ui_observation is a transient low-level RAW-EYE feature summary, not OCR or object recognition. Treat it as uncertain visual context; never quote it as source text and never infer action or learning permission from it.'\n",
        "source-bound transient UI features for B1/B2",
    )
    raw = _replace_once(
        raw,
        b"        query_packet.update(compute_deadline_monotonic_ns=int(deadline*1e9),offer_valid_until_monotonic_ns=int(valid_until*1e9))\n",
        b"        query_packet.update(compute_deadline_monotonic_ns=int(deadline*1e9),offer_valid_until_monotonic_ns=int(valid_until*1e9))\n"
        b"        if ui_binding is not None:\n"
        b"            query_packet['ephemeral_ui_binding']=ui_binding\n"
        b"            query_packet['ephemeral_ui_source_refs']=ui_refs\n",
        "bind UI receipt to the exact body query",
    )
    raw = _replace_once(
        raw,
        b"        if wide:p['quote_context_chars']=wide  # analyst_context accepts the widened spans only for this offer\n",
        b"        if wide:p['quote_context_chars']=wide  # analyst_context accepts the widened spans only for this offer\n"
        b"        if ui_binding is not None:\n"
        b"            p['ephemeral_ui_binding']=ui_binding\n"
        b"            p['ephemeral_ui_source_refs']=ui_refs\n",
        "bind UI receipt to the exact body offer",
    )
    raw = _bind_ui_offer_scope(raw)
    raw = _replace_once(
        raw,
        b"                'hypothesis_authority':'MODEL_HYPOTHESIS_NOT_FACT','verified_quotes':verified})\n",
        b"                'hypothesis_authority':'MODEL_HYPOTHESIS_NOT_FACT','verified_quotes':verified,\n"
        b"                'ui_observation_binding':offer.get('ephemeral_ui_binding')})\n",
        "retain content-free UI provenance in the selected body output",
    )
    return raw


def _patch_operator(raw: bytes) -> bytes:
    newline = bytes((10,))
    has_route = b"if cmd=='android':" in raw
    has_help = b":android status|capabilities|" in raw
    if has_route and has_help:
        return raw
    if has_route or has_help:
        raise ValueError("Android operator route/help is only partially present")

    help_line = (
        b":android status|capabilities|pair|trust <key-id> --confirm|launch <package> --confirm|poll <action-id>|cancel <action-id>|pending|history [1..50]|frame-status|stop (separate companion; default OFF; visible OS/per-action consent)"
        + newline
    )
    help_matches = [
        line for line in raw.splitlines(keepends=True)
        if line.lstrip().startswith(b":ctxos ")
    ]
    if len(help_matches) != 1:
        raise ValueError(
            "Android UI overlay anchor mismatch: Context OS help line count="
            + str(len(help_matches))
        )
    help_anchor = help_matches[0]
    if not help_anchor.endswith(newline):
        help_anchor += newline
    raw = raw.replace(help_matches[0], help_anchor + help_line, 1)

    callosum = (
        b"        if cmd=='callosum':" + newline
        + b"            from .callosum import operator_command" + newline
        + b"            return operator_command(r,args)" + newline
    )
    android = (
        b"        if cmd=='android':" + newline
        + b"            from .android_companion_runtime import operator_command" + newline
        + b"            return operator_command(r,args)" + newline
    )
    raw = _replace_once(
        raw,
        callosum,
        callosum + android,
        "dispatch local Android companion controls",
    )
    return raw


def apply_sources(code_dir: Path, sources: dict[str, bytes]) -> dict[str, bytes]:
    root = Path(code_dir)
    if root.is_symlink():
        raise ValueError("Android UI overlay source root cannot be a symlink")
    root = root.resolve(strict=True)
    for relative, expected in SOURCE_BLOBS.items():
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("Android UI overlay source missing or unsafe: " + relative)
        if _git_blob_sha1(path.read_bytes()) != expected:
            raise ValueError("Android UI overlay source blob changed: " + relative)
    for relative in REQUIRED_FILES:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("Android UI runtime dependency missing or unsafe: " + relative)

    result = dict(sources)
    for relative in ("v13/runtime.py", "v13/cognition.py", "v13/operator.py"):
        if not isinstance(result.get(relative), bytes):
            raise ValueError("Android UI overlay requires composed source bytes: " + relative)
    result["v13/runtime.py"] = _patch_runtime(result["v13/runtime.py"])
    result["v13/cognition.py"] = _patch_cognition(result["v13/cognition.py"])
    result["v13/operator.py"] = _patch_operator(result["v13/operator.py"])
    for relative in ("v13/runtime.py", "v13/cognition.py", "v13/operator.py"):
        compile(result[relative], relative, "exec")
    return result
