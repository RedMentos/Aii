"""Final-stage Core overlay for a source-only exact text greeting fastpath.

Applied after the pinned A/B/C, audio, C4 and native-receiver builders. It
patches only the composed staged Runtime and adds one small pure matcher.
"""
from __future__ import annotations

import ast
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



def _patch_worker_learning(raw: bytes) -> bytes:
    """Guard the existing post-turn learning dispatch without depending on an old worker layout."""
    if not isinstance(raw, bytes):
        raise TypeError("Runtime source must be bytes")
    try:
        tree = ast.parse(raw.decode("utf-8"))
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError("Runtime source is not parseable UTF-8 Python") from exc

    classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Runtime"]
    if len(classes) != 1:
        raise ValueError("expected one Runtime class")
    workers = [
        node for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "_worker"
    ]
    if len(workers) != 1:
        raise ValueError("expected one Runtime._worker method")
    worker = workers[0]

    parents = {}
    for node in ast.walk(worker):
        for child in ast.iter_child_nodes(node):
            parents[child] = node

    def is_self_call(node, name):
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == name
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
        )

    turn_calls = [
        node for node in ast.walk(worker)
        if is_self_call(node, "_turn")
        and node.args
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "payload"
    ]
    if len(turn_calls) != 1:
        raise ValueError(f"expected one _turn(payload) call in Runtime._worker; found {len(turn_calls)}")
    turn_call = turn_calls[0]
    turn_parent = parents.get(turn_call)
    prefix = b""
    if isinstance(turn_parent, ast.Assign) and turn_parent.value is turn_call:
        if len(turn_parent.targets) != 1 or not isinstance(turn_parent.targets[0], ast.Name):
            raise ValueError("unsupported _turn(payload) assignment target")
        result_name = turn_parent.targets[0].id
    elif (
        isinstance(turn_parent, ast.AnnAssign)
        and turn_parent.value is turn_call
        and isinstance(turn_parent.target, ast.Name)
    ):
        result_name = turn_parent.target.id
    elif isinstance(turn_parent, ast.Expr) and turn_parent.value is turn_call:
        result_name = "_v14_greeting_turn_result"
        prefix = (result_name + "=").encode("ascii")
    else:
        raise ValueError("unsupported _turn(payload) statement shape")

    all_update_calls = [
        node for node in ast.walk(worker)
        if is_self_call(node, "online_world_update")
    ]
    if len(all_update_calls) != 1:
        raise ValueError(
            f"expected one online_world_update call in Runtime._worker; found {len(all_update_calls)}"
        )
    update_call = all_update_calls[0]
    if not any(
        keyword.arg == "limit"
        and isinstance(keyword.value, ast.Constant)
        and keyword.value.value == 64
        for keyword in update_call.keywords
    ):
        raise ValueError("online-world dispatch must retain the existing bounded limit=64")

    def branch_path(node):
        path = set()
        child = node
        parent = parents.get(child)
        while parent is not None and parent is not worker:
            suite = None
            if isinstance(parent, ast.If):
                if child in parent.body:
                    suite = "body"
                elif child in parent.orelse:
                    suite = "orelse"
            elif isinstance(parent, ast.Try):
                if child in parent.body:
                    suite = "try"
                elif child in parent.handlers:
                    suite = "handler"
                elif child in parent.orelse:
                    suite = "else"
                elif child in parent.finalbody:
                    suite = "finally"
            elif isinstance(parent, (ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
                if child in parent.body:
                    suite = "body"
                elif child in parent.orelse:
                    suite = "orelse"
            if suite is not None:
                path.add((id(parent), suite))
            child, parent = parent, parents.get(parent)
        return path

    if not branch_path(turn_call).issubset(branch_path(update_call)):
        raise ValueError("online-world dispatch is not dominated by the same _turn(payload) branch")
    if turn_call.lineno > update_call.lineno:
        raise ValueError("turn result must be produced before online-world dispatch")

    child = update_call
    parent = parents.get(child)
    try_node = None
    while parent is not None:
        if isinstance(parent, ast.Try):
            try_node = parent
            break
        child, parent = parent, parents.get(parent)
    if try_node is None or child not in try_node.body:
        raise ValueError("online-world dispatch must remain inside its existing try body")

    lines = raw.splitlines(keepends=True)
    start_index = try_node.lineno - 1
    end_index = try_node.end_lineno
    first = lines[start_index]
    indent_len = len(first) - len(first.lstrip(b" \t"))
    indent = first[:indent_len]
    if try_node.col_offset != indent_len or not first[indent_len:].startswith(b"try:"):
        raise ValueError("online-world try block must start on its own statement line")

    worker_start = worker.lineno - 1
    worker_end = worker.end_lineno
    worker_bytes = b"".join(lines[worker_start:worker_end])
    if b"skip_online_world_update" in worker_bytes:
        raise ValueError("online-world greeting guard is already present")

    block = lines[start_index:end_index]
    indented = []
    for line in block:
        if line.strip():
            if not line.startswith(indent):
                raise ValueError("unexpected indentation inside online-world try block")
            indented.append(indent + b"    " + line[len(indent):])
        else:
            indented.append(line)

    name = result_name.encode("ascii")
    guard = (
        indent
        + b"if not (isinstance("
        + name
        + b", dict) and "
        + name
        + b".get('skip_online_world_update') is True):\n"
    )
    replacement = guard + b"".join(indented)
    start_offset = sum(len(line) for line in lines[:start_index])
    end_offset = sum(len(line) for line in lines[:end_index])
    patched = raw[:start_offset] + replacement + raw[end_offset:]

    if prefix:
        call_offset = sum(len(line) for line in lines[:turn_call.lineno - 1]) + turn_call.col_offset
        patched = patched[:call_offset] + prefix + patched[call_offset:]

    try:
        compile(patched.decode("utf-8"), "v13/runtime.py", "exec")
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise ValueError("patched Runtime does not compile") from exc
    return patched


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

    runtime = _patch_worker_learning(runtime)


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
