"""Run117AH default-OFF exact Store source-ID Body selection SHADOW.

The model chooses an opaque candidate ID, never emits a trusted quote. Exact
text is rehydrated only from persisted USER SourceRefs. Model selection is
a fallible hypothesis; no output, tool, approval, learning or truth authority.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re
import time

from .b1b2_c3_source_envelope_candidate import _latest_authoritative_user
from .common import dumps
from .contracts import packet as make_packet
from .jef_b1b2_c3_role_postgen_shadow_candidate import _epoch

SCHEMA = "v13.body_source_id_selection_shadow.v1"
KIND = "BodySourceIdSelection"
SYSTEM = (
    "You are a source-ID selector in a non-delivering SHADOW experiment. "
    "Select only the opaque span_id that answers the role's selection task. "
    "Earlier archive drafts are not binding. Do not rewrite source text, "
    "compute an answer, approve, dispatch, learn or deliver output. "
    "Reply only JSON with one key span_id; NONE means uncertain."
)
POLICY = re.compile(
    r"Binding policy: budget [1-9][0-9]{0,5} euros; "
    r"deadline [1-9][0-9]{0,5} days; local-only (?:true|false)\.")
OPTIONS = re.compile(
    r"Option A: cost [1-9][0-9]{0,5} euros, duration [1-9][0-9]{0,5} days, "
    r"local (?:true|false)\. Option B: cost [1-9][0-9]{0,5} euros, "
    r"duration [1-9][0-9]{0,5} days, local (?:true|false)\.")
ARCHIVE = re.compile(r"Archive memo [1-9][0-9]*: .*?draft was withdrawn\.")
QUESTION = "Compare these two offers against the saved binding policy, not the archive draft."
ROLES = {"B1_DETAIL":("current options",OPTIONS),
         "B2_GIST":("binding policy",POLICY)}


def _receipt(status, **extra):
    return {
        "schema":SCHEMA,"status":status,"model_called":False,
        "native_model_proven":False,"selected_quote_truth":False,
        "source_semantic_truth_authority":False,
        "output_committed":False,"tool_dispatches":0,
        "delivery_authority":0,"learning_authority":0,
        "age0":"RECORD_ONLY","step2_exit":"EVIDENCE_NOT_PASSING",
        "b3":"NO_PROMOTION","body_jepa":"UNAVAILABLE",
        "jepa_weight":0,"redmi_measured":False,
        "whole_system_complete":False,**extra,
    }


def _pair(pairs):
    out={}
    for key,value in pairs:
        if key in out:
            raise ValueError("DUPLICATE_JSON_RED")
        out[key]=value
    return out


def _parse(raw, ids):
    if type(raw) is not str or len(raw.encode("utf-8")) > 256:
        return None
    try:
        value=json.loads(raw,object_pairs_hook=_pair,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             ValueError("NONFINITE_RED")))
        if (type(value) is not dict or set(value)!={"span_id"}
                or type(value["span_id"]) is not str
                or value["span_id"] not in set(ids)|{"NONE"}):
            return None
        return value["span_id"]
    except (ValueError,TypeError,OverflowError,UnicodeError):
        return None


def _span(ref, text, start, end):
    r=dict(ref)
    r["char_start"],r["char_end"]=start,end
    return {"text":text[start:end],"source_ref":r,
            "origin":"STORE_EXACT_USER_NOT_MODEL_QUOTE"}


def _candidates(runtime,event,role):
    if role not in ROLES:
        raise ValueError("ROLE_RED")
    stored_event=runtime.store.one(
        "SELECT session_id FROM events WHERE id=?", (event.get("event_id"),))
    if (event.get("brain_generation_id") != runtime.store.generation_id
            or stored_event is None
            or stored_event["session_id"] != runtime.session
            or _latest_authoritative_user(runtime.store,runtime.session)
            != event.get("event_id")):
        raise ValueError("STALE_USER_EVENT_RED")
    ref=event["source_ref"]
    source=runtime.store.read_source(ref)
    if (type(source) is not str or not 100 <= len(source) <= 2048
            or not source.startswith("Project ")):
        raise ValueError("SOURCE_SHAPE_RED")
    target=list(ROLES[role][1].finditer(source))
    if len(target)!=1:
        raise ValueError("TARGET_ANCHOR_RED")
    if role=="B2_GIST":
        distractors=list(ARCHIVE.finditer(source))
        if len(distractors)!=1:
            raise ValueError("ARCHIVE_ANCHOR_RED")
        distractor=(distractors[0].start(),distractors[0].end())
    else:
        start=source.find(QUESTION)
        if start<0 or source.count(QUESTION)!=1:
            raise ValueError("QUESTION_ANCHOR_RED")
        distractor=(start,start+len(QUESTION))
    ranges=[(target[0].start(),target[0].end()),distractor]
    if ranges[0][0]<ranges[1][1] and ranges[1][0]<ranges[0][1]:
        raise ValueError("OVERLAP_RED")
    spans=[_span(ref,source,*rng) for rng in ranges]
    for span in spans:
        if runtime.store.read_source(span["source_ref"])!=span["text"]:
            raise ValueError("SOURCE_SPAN_RED")
    # IDs are opaque and order is deterministic per source, not semantic.
    ids=["s"+sha256(
        (role+"|"+ref["sha256"]+"|"+str(start)+"|"+str(end)).encode()
    ).hexdigest()[:12] for start,end in ranges]
    if ids[0]==ids[1]:
        raise ValueError("ID_COLLISION_RED")
    order=([1,0] if int(ref["sha256"][-1],16)%2 else [0,1])
    return source,[(ids[i],spans[i]) for i in order],ids[0]


def select(runtime,event,role,generator,*,operator_opt_in=False,
           callback_opt_in=False,approval_receipt=None):
    if operator_opt_in is not True or callback_opt_in is not True:
        return _receipt("OFF")
    if approval_receipt is not None:
        return _receipt("REAL_TTY_APPROVAL_UNSUPPORTED_RED")
    if not callable(generator):
        return _receipt("INVALID_GENERATOR_RED")
    try:
        source,candidates,target=_candidates(runtime,event,role)
        user={
            "schema":"v13.body_source_id_selection_user_data.v1",
            "source_role":"UNTRUSTED_EXACT_USER",
            "role":role,"selection_task":ROLES[role][0],
            "candidates":[{"span_id":key,**span}
                          for key,span in candidates],
            "none_allowed":True,
        }
        messages=[{"role":"system","content":SYSTEM},
                  {"role":"user","content":dumps(user)}]
        if any(span["text"] in SYSTEM for _,span in candidates):
            return _receipt("SYSTEM_SOURCE_LEAK_RED")
        frozen=dumps(messages)
        epoch=_epoch(runtime.store)
        revision=runtime.models.revision(role)
    except Exception:
        return _receipt("SOURCE_PREFLIGHT_RED")
    prompt=deepcopy(messages)
    try:
        result=generator(prompt)
    except Exception as exc:
        return _receipt("CALLBACK_EXCEPTION_RED",model_called=True,
                        error_type=type(exc).__name__)
    try:
        if dumps(prompt)!=frozen:
            return _receipt("CALLBACK_PROMPT_MUTATED_RED",model_called=True)
        if _epoch(runtime.store)!=epoch:
            return _receipt("CALLBACK_STORE_CHANGED_RED",model_called=True)
        after,again,again_target=_candidates(runtime,event,role)
        if (after!=source or dumps(again)!=dumps(candidates)
                or again_target!=target
                or runtime.models.revision(role)!=revision
                or _epoch(runtime.store)!=epoch):
            return _receipt("POSTGEN_SOURCE_CHANGED_RED",model_called=True)
        raw=result["raw"] if type(result) is dict else result
        selected=_parse(raw,[x[0] for x in candidates])
        if selected is None:
            return _receipt("MODEL_JSON_RED",model_called=True)
        reported_metrics=result.get("metrics",{}) if type(result) is dict else {}
        if type(reported_metrics) is not dict:
            return _receipt("METRICS_SHAPE_RED",model_called=True)
        metrics={k:reported_metrics.get(k) for k in
                 ("status","actual_model","role","generated_tokens")}
        if len(dumps(metrics))>1024:
            return _receipt("METRICS_SIZE_RED",model_called=True)
        chosen=next((span for key,span in candidates if key==selected),None)
        status=("SHADOW_ABSTAIN_RECORDED" if selected=="NONE"
                else "SHADOW_SOURCE_ID_SELECTED" if selected==target
                else "SHADOW_WRONG_SOURCE_ID_RECORDED")
        packet=make_packet(KIND,role,event["event_id"],
            runtime.store.generation_id,[event["source_ref"]],
            role=role,model_revision=revision,
            "source_ref":event["source_ref"],
            "candidates":[{"span_id":key,**span}
                          for key,span in candidates],
            "selected_id":selected,"selected_span":chosen,
            "selection_correct_shadow":selected==target,
            "raw_output_sha256":sha256(raw.encode()).hexdigest(),
            "raw_output_bytes":len(raw.encode()),
            "model_metrics_reported_unverified":metrics,
            "source_semantic_truth_authority":False,
            "model_hypothesis_not_fact":True,
            "delivery_authority":0,"learning_authority":0,
            output_committed=False,
        )
        runtime.store.add_packet(KIND,packet)
        stored=runtime.store.one(
            "SELECT payload FROM packets WHERE id=? AND kind=?",
            (packet["packet_id"],KIND))
        if stored is None or json.loads(stored["payload"])!=packet:
            return _receipt("PERSISTENCE_RED",model_called=True)
        return _receipt(status,model_called=True,
                        packet_id=packet["packet_id"],
                        selected_id=selected,
                        selection_correct_shadow=selected==target,
                        source_ref=event["source_ref"],
                        model_revision=revision,
                        raw_output_sha256=packet["raw_output_sha256"])
    except Exception:
        return _receipt("POSTGEN_INTEGRITY_RED",model_called=True)
