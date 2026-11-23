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


    policy_anchor = (
        b"            monitor.start()\\n"
        b"            check(self.cancel_event,deadline);resource=self.resources();state=self.guard.update(resource)\\n"
    )
    policy_inserted = b"""            monitor.start()
            check(self.cancel_event,deadline)
            from .output_policy import match
            mark('policy_check');fixed_policy=match(self.store,text)
            check(self.cancel_event,deadline)
            if fixed_policy is None:
                from .fast_greeting import is_text_only_event, match_unclaimed
                if is_text_only_event(e):
                    greeting=match_unclaimed(text,policy_match_ok=True,fixed_policy=None)
                    if greeting is not None:
                        answer_ref=self.store.source(greeting['reply'],'BUILTIN_GREETING_ACK')
                        fixed_policy={
                            'kind':'FIXED_EXACT',
                            'rule_id':greeting['rule_id'],
                            'rule_version':'builtin-v1',
                            'query_ref':e['source_ref'],
                            'answer_ref':answer_ref,
                            'answer':greeting['reply'],
                        }
                        meta.update(
                            output_policy_owner='SYSTEM_BUILTIN',
                            fastpath={
                                'kind':'EXACT_GREETING_ACK',
                                'normalized_input':greeting['normalized'],
                                'skipped_organs':[
                                    'A1','A2','A3','A4','B1_DETAIL','B2_GIST',
                                    'B3_ENLIGHTENED_SPACE','C2','C3_LANGUAGE',
                                    'C4_FOCAL_LOOP','JEPA',
                                ],
                            },
                            skip_online_world_update=True,
                            learning_authority=0,
                            experience_eligible=False,
                            external_action_authority=False,
                            model_generated=False,
                        )
            resource=self.resources();state=self.guard.update(resource)
"""
    runtime = _replace_once(runtime, policy_anchor, policy_inserted, "policy-first greeting admission")
    runtime = _replace_once(
        runtime,
        b"            if state=='CRITICAL':",
        b"            if state=='CRITICAL' and not meta.get('fastpath'):",
        "critical resource guard",
    )
    runtime = _replace_once(
        runtime,
        b"            from .output_policy import match\\n            mark('policy_check');fixed_policy=match(self.store,text)\\n            mark('perception_and_state')\\n",
        b"            mark('perception_and_state')\\n",
        "remove duplicate policy check",
    )
    runtime = _replace_once(
        runtime,
        b"                meta['context_source_refs']=refs\\n",
        b"                meta['context_source_refs']=refs\\n"
        b"                if meta.get('fastpath',{}).get('kind') == 'EXACT_GREETING_ACK':\\n"
        b"                    meta['route']={'source':'BUILTIN_GREETING_ACK'}\\n"
        b"                    meta['skipped_native_stages']=[\\n"
        b"                        'SEGMENTATION','TEACHER_ALIGNMENT','STUDENT_ALIGNMENT','SALIENCE',\\n"
        b"                        'MEMORY_RECALL','B1_DETAIL','B2_GIST','B3_ENLIGHTENED_SPACE',\\n"
        b"                        'C2_CONTROL','C3_DECODE','C4_FOCAL_LOOP','WORLD_JEPA_PREDICTION',\\n"
        b"                        'TOOL_PLANNING',\\n"
        b"                    ]\\n",
        "fastpath route and skipped-stage telemetry",
    )
    runtime = _replace_once(
        runtime,
        b"            if not meta.get('skill'):route=agi_live.skill_route(self,e,text,route,direct,meta)  # WP-N13 AG4 -> C5\\n",
        b"            if meta.get('experience_eligible') is not False and not meta.get('skill'):route=agi_live.skill_route(self,e,text,route,direct,meta)  # WP-N13 AG4 -> C5\\n",
        "skip greeting skill learning",
    )
    runtime = _replace_once(
        runtime,
        b"            agi_live.expect(self,e,aid,predicted_role,route)  # WP-N13 AG2 prediction before acting\\n",
        b"            if meta.get('experience_eligible') is not False:agi_live.expect(self,e,aid,predicted_role,route)  # WP-N13 AG2 prediction before acting\\n",
        "skip greeting action prediction",
    )
    runtime = _replace_once(
        runtime,
        b"                txctl.commit_output(self.store,mid,eid,meta);meta['first_output_monotonic_ns']=time.monotonic_ns();self.store.append_message(mid,output);meta['direct_source_copy']=True\\n",
        b"                committed=txctl.commit_output(self.store,mid,eid,meta)\\n"
        b"                if meta.get('fastpath',{}).get('kind') == 'EXACT_GREETING_ACK' and (committed is not True or not txctl.has_output_commit(self.store,mid,eid)):\\n"
        b"                    raise Unavailable('Greeting output commit was not durably recorded')\\n"
        b"                meta['first_output_monotonic_ns']=time.monotonic_ns();self.store.append_message(mid,output);meta['direct_source_copy']=True\\n",
        "durable direct-output commit guard",
    )
    runtime = _replace_once(
        runtime,
        b"            self.store.add_packet('ExperienceRecord',packet('ExperienceRecord','F1_EPISODIC',eid,g,[e['source_ref']],source_ref=e['source_ref'],self_candidate_hash=meta['self_candidate_hash'],outcome=status,teacher_seen_before_commit=False))\\n"
        b"            agi_live.after_turn(self,e,meta,status,aid)  # WP-N13 AG2 outcome, AG4 skill outcome, AG0 slots\\n",
        b"            if meta.get('experience_eligible') is not False:\\n"
        b"                self.store.add_packet('ExperienceRecord',packet('ExperienceRecord','F1_EPISODIC',eid,g,[e['source_ref']],source_ref=e['source_ref'],self_candidate_hash=meta['self_candidate_hash'],outcome=status,teacher_seen_before_commit=False))\\n"
        b"                agi_live.after_turn(self,e,meta,status,aid)  # WP-N13 AG2 outcome, AG4 skill outcome, AG0 slots\\n",
        "gate experience record and AGI after-turn",
    )
    runtime = _replace_once(
        runtime,
        b"\\n    def _teacher",
        b"\\n        if meta.get('fastpath',{}).get('kind') == 'EXACT_GREETING_ACK':\\n"
        b"            return {'skip_online_world_update': True, 'fastpath': 'EXACT_GREETING_ACK'}\\n"
        b"\\n    def _teacher",
        "return skip marker after normal finalizer",
    )
    compile(runtime, RUNTIME_PATH, "exec")

    result = dict(sources)
    result[RUNTIME_PATH] = runtime
    result[FAST_GREETING_PATH] = greeting_raw
    return result
