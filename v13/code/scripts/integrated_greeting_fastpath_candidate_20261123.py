"""Final-stage Core overlay for a source-only exact text greeting fastpath.

Applied after the pinned A/B/C, audio, C4 and native-receiver builders. It
patches only the composed staged Runtime and adds one small pure matcher.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

FAST_GREETING_PATH = "v13/fast_greeting.py"
FAST_GREETING_BLOB_SHA1 = "54c0a8ccdeb94dbca0a93eefb89d1f495ea26a67"
RUNTIME_PATH = "v13/runtime.py"


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _replace_once(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError(f"greeting overlay expected one {label}; found {count}")
    return raw.replace(old, new, 1)


def apply_sources(code_dir: Path, sources: dict[str, bytes]) -> dict[str, bytes]:
    """Return a new composed source map; never mutate the caller's map or checkout."""
    code_dir = Path(code_dir).resolve(strict=True)
    greeting_path = code_dir / FAST_GREETING_PATH
    if greeting_path.is_symlink() or not greeting_path.is_file():
        raise ValueError("pinned fast-greeting matcher missing or unsafe")
    greeting_raw = greeting_path.read_bytes()
    if _git_blob_sha1(greeting_raw) != FAST_GREETING_BLOB_SHA1:
        raise ValueError("pinned fast-greeting matcher changed")

    runtime = sources.get(RUNTIME_PATH)
    if not isinstance(runtime, bytes):
        raise ValueError("composed Runtime source missing")
    if b"EXACT_GREETING_ACK" in runtime:
        raise ValueError("greeting fastpath is already present")

    worker_old = (
        b"                        self._turn(payload)\n"
        b"                        # Local plasticity runs after the turn's committed action\n"
        b"                        # record, never on an uncommitted prediction. Failure is\n"
        b"                        # isolated from user-visible output and logged for repair.\n"
        b"                        try:self.online_world_update(limit=64)\n"
        b"                        except Exception as exc:\n"
        b"                            self.store.log('online_world_learning_error',payload['event_id'],\n"
        b"                                           {'error':type(exc).__name__})\n"
    )
    worker_new = (
        b"                        turn_result=self._turn(payload)\n"
        b"                        # A source-only greeting has no action-conditioned transition.\n"
        b"                        if not (isinstance(turn_result,dict) and turn_result.get('skip_online_world_update') is True):\n"
        b"                            # Local plasticity runs after the turn's committed action\n"
        b"                            # record, never on an uncommitted prediction. Failure is\n"
        b"                            # isolated from user-visible output and logged for repair.\n"
        b"                            try:self.online_world_update(limit=64)\n"
        b"                            except Exception as exc:\n"
        b"                                self.store.log('online_world_learning_error',payload['event_id'],\n"
        b"                                               {'error':type(exc).__name__})\n"
    )
    runtime = _replace_once(runtime, worker_old, worker_new, "post-turn learning dispatch")

    marker = b"        mark('ingress')\n        monitor=NativePressureMonitor"
    inserted = """        mark('ingress')
        # Exact acknowledgements are plain-text only and never bypass RAW EAR.
        greeting=None
        from .fast_greeting import is_text_only_event
        if is_text_only_event(e):
            from .fast_greeting import match as match_greeting, match_unclaimed
            candidate=match_greeting(text)
            if candidate is not None:
                mark('policy_check')
                policy_match_ok=True
                fixed_policy=None
                try:
                    from .output_policy import match as match_output_policy
                    fixed_policy=match_output_policy(self.store,text)
                except Exception as exc:
                    policy_match_ok=False
                    self.store.log('output_policy_unavailable',eid,{'stage':'early_policy_check','error':type(exc).__name__})
                greeting=match_unclaimed(
                    text,policy_match_ok=policy_match_ok,fixed_policy=fixed_policy)
        if greeting:
            # Cancellation/deadline and the durable IH-H12 commit remain mandatory.
            check(self.cancel_event,deadline)
            mark('greeting_fastpath')
            source_ref=e['source_ref']
            answer_ref=self.store.source(greeting['reply'],'BUILTIN_GREETING_ACK')
            meta.update(
                output_authority='APPROVED_FIXED_RULE',
                output_policy={
                    'kind':'BUILTIN_GREETING_ACK',
                    'rule_id':greeting['rule_id'],
                    'rule_version':'1',
                    'query_ref':source_ref,
                    'answer_ref':answer_ref,
                },
                output_policy_owner='SYSTEM_BUILTIN',
                exact_policy_matched=True,
                route={'source':'BUILTIN_GREETING_ACK'},
                fastpath={
                    'kind':'EXACT_GREETING_ACK',
                    'normalized_input':greeting['normalized'],
                    'skipped_organs':[
                        'A1','A2','A3','A4','A5','B1_DETAIL','B2_GIST',
                        'B3_ENLIGHTENED_SPACE','C2','C3_LANGUAGE','C4_FOCAL_LOOP','JEPA',
                    ],
                },
                skipped_native_stages=[
                    'SEGMENTATION','NATIVE_ALIGNMENT','SALIENCE','PERCEPTION_PACKET',
                    'MEMORY_RECALL','B1_B2_OBSERVERS','C2_CONTROL','C4_FOCAL_LOOP',
                    'C3_DECODE','WORLD_JEPA_PREDICTION','B3_LATENT_EXCHANGE','TOOL_PLANNING',
                ],
                context_source_refs=[source_ref,answer_ref],
            )
            decision=packet(
                'OutputPolicyDecision','C5_REPORT_BROKER',eid,g,
                [source_ref,answer_ref],
                rule_id=greeting['rule_id'],rule_version='1',
                query_ref=source_ref,answer_ref=answer_ref,
                output_authority='APPROVED_FIXED_RULE',model_generated=False,
            )
            self.store.add_packet('OutputPolicyDecision',decision)
            committed=txctl.commit_output(self.store,mid,eid,meta)
            if committed is not True or not txctl.has_output_commit(self.store,mid,eid):
                raise RuntimeError('Greeting output commit was not durably recorded')
            meta['first_output_monotonic_ns']=time.monotonic_ns()
            self.store.append_message(mid,greeting['reply'])
            meta.update(
                self_candidate_hash=digest(greeting['reply']),
                duration_s=time.monotonic()-start,
                characters=len(greeting['reply']),
                model_generated=False,
                fastpath_kind='EXACT_GREETING_ACK',
                skip_online_world_update=True,
                learning_authority=0,
                experience_eligible=False,
                external_action_authority=False,
            )
            self.store.finish_message(mid,'FINAL',meta)
            try:txctl.settle_turn(self,eid,'FINAL')
            except Exception as exc:self.store.log('provisional_unavailable',eid,{'error':type(exc).__name__})
            try:self.executive.update(e,self.session,status='FINAL')
            except Exception as exc:self.store.log('executive_finish_deferred',eid,{'error':type(exc).__name__})
            try:
                from .broker import Broker
                broker_result=Broker(self).finalize(
                    e,mid,meta,'FINAL',greeting['reply'],
                    direct=True,exact_requested=False,clarify=False,
                    tool_result=None,pending=None,
                )
                if broker_result.get('egress_ok') is not True:
                    self.store.log('greeting_egress_blocked',eid,{'reason':'C7_NOT_CONFIRMED'})
            except Exception as exc:self.store.log('broker_unavailable',eid,{'error':type(exc).__name__})
            self.store.log('turn_finished',eid,meta|{'status':'FINAL'})
            self.notice('Antwort gespeichert · FINAL')
            self.turn_event=None
            return {'skip_online_world_update':True,'fastpath':'EXACT_GREETING_ACK'}
        monitor=NativePressureMonitor""".encode("utf-8")
    runtime = _replace_once(runtime, marker, inserted, "early Runtime ingress hook")
    compile(runtime, RUNTIME_PATH, "exec")

    result = dict(sources)
    result[RUNTIME_PATH] = runtime
    result[FAST_GREETING_PATH] = greeting_raw
    return result
