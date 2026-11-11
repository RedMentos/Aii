"""Connect bounded archived source excerpts to the integrated ContextOS copy."""
import hashlib
import importlib.util
from pathlib import Path

BASE_BUILDER_SHA = '6a2c476980556fda69bd9a3da6d7d8743969997b8f4a196614cbc2fe747816e1'
RECALL_SHA = '56282c1d95610ce3c3266d63f48b78362d0bf32e2a7291b90a3f55e386aa1f64'
BUDGET_SHA = 'a9fdddeb9ff67b5bb733e86bc845508d8d883afed2a035b42fc39ebc0a11526a'
CONTEXT_SHA = '2fe8bfc4c7857f24411fea71038485900ca6fcbad2ec3361fa4ede080657861f'
STREAM_SHA = 'e7c9d57b999ab93f628ec07f6dc9d467d886f9a26535a161386a52f102afd6a1'
REUSE_SHA = '52de26b95606b8038b109886d81a00c2f31ad9152c81384980c9615463f5a91b'
STORE_SHA = 'f405894f5d61ceacce2495f4d76d003d4b500945c6d081ee561a62efd7acf11f'

OPERATOR_ANCHOR = b'''def operator_command(r,args):
    c=controller(r)
'''
OPERATOR_ADDED = OPERATOR_ANCHOR + b'''    if args and args[0]=='recall':
        from . import context_source_recall_candidate as source_recall
        if args in (['recall'],['recall','status']):return dumps(source_recall.status(r))
        if args in (['recall','on'],['recall','off']):
            source_recall.set_enabled(r.store,r.session,args[1]=='on','EXPLICIT_HUMAN')
            return dumps(source_recall.status(r))
        raise ValueError(':ctxos recall [status|on|off]')
'''
RUNTIME_ANCHOR = b"                sys=stable+''.join(head+dumps(body) for _,head,body in volatile)\n"
RUNTIME_ADDED = b'''                source_recall_items=[]
                try:
                    from . import context_source_recall_candidate as source_recall
                    restored=source_recall.prepare(self,eid,text,stable,volatile,history_records,
                        budget_scale=body['modulation'].get('context_budget_scale',1.),deadline=deadline)
                    source_recall_items=restored['items']
                    meta['source_recall']={'status':restored['status'],'count':len(source_recall_items)}
                    if source_recall_items:
                        volatile.append(('SOURCE_LINKS',source_recall.HEADER,source_recall_items))
                        meta['source_recall_refs']=restored['source_refs']
                except Exception as exc:
                    meta['source_recall']={'status':'UNAVAILABLE','reason':type(exc).__name__,'count':0}
''' + RUNTIME_ANCHOR
SAVE_ANCHOR = b"                try:save_context(self.store,self.session,eid,runner.role,messages)  # WP-V5 :context\n"
VERIFY_SAVE = b'''                if source_recall_items:source_recall.verify_before_use(self,source_recall_items,deadline)
''' + SAVE_ANCHOR
NATIVE_ANCHOR = b"                mark('native_answer')\n"
VERIFY_NATIVE = b'''                if source_recall_items:source_recall.verify_before_use(self,source_recall_items,deadline)
''' + NATIVE_ANCHOR


def _replace(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('unexpected context recall ' + label + ' source')
    return data.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    builder = code_dir / 'scripts/integrated_feedback_bootstrap_candidate_20261111.py'
    if hashlib.sha256(builder.read_bytes()).hexdigest() != BASE_BUILDER_SHA:
        raise ValueError('feedback/bootstrap builder source changed')
    recall = (code_dir / 'v13/context_source_recall_candidate.py').read_bytes()
    budget = (code_dir / 'v13/source_read_budget_candidate.py').read_bytes()
    reuse = (code_dir / 'v13/source_reuse_archive_candidate.py').read_bytes()
    context = (code_dir / 'v13/context_os.py').read_bytes()
    for raw, expected in ((recall, RECALL_SHA), (budget, BUDGET_SHA), (context, CONTEXT_SHA), (reuse, REUSE_SHA)):
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('context recall input source changed')
    spec = importlib.util.spec_from_file_location('verified_feedback_builder', builder)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.build_sources(code_dir)
    store = result['v13/store.py']
    if hashlib.sha256(store).hexdigest() != STORE_SHA:
        raise ValueError('context recall Store source changed')
    source_import = b'from .source_lifecycle_candidate import verify_or_create_blob'
    if store.count(source_import) != 2:
        raise ValueError('unexpected text source publication imports')
    store = store.replace(source_import, b'from .source_reuse_archive_candidate import verify_or_create_text_blob as verify_or_create_blob')
    store = _replace(store, b'verify_or_create_blob(p,b,h)\n', b'verify_or_create_blob(p,b,h,kind=kind)\n', 'text source kind')
    new_store_sha = hashlib.sha256(store).hexdigest().encode()
    old_semantic_sha = hashlib.sha256(result['v13/world_semantic_evidence_candidate.py']).hexdigest().encode()
    for name in ('v13/archive_reader_guard_candidate.py', 'v13/world_jepa_runtime_guard_candidate.py',
                 'v13/world_semantic_evidence_candidate.py'):
        result[name] = _replace(result[name], STORE_SHA.encode(), new_store_sha, name + ' Store pin')
    result['v13/local_error_route_shadow_candidate.py'] = _replace(
        result['v13/local_error_route_shadow_candidate.py'], old_semantic_sha,
        hashlib.sha256(result['v13/world_semantic_evidence_candidate.py']).hexdigest().encode(), 'semantic source pin')
    stream = result['v13/archive_stream_range_candidate.py']
    if hashlib.sha256(stream).hexdigest() != STREAM_SHA:
        raise ValueError('context recall streaming source changed')
    stream = _replace(stream, STORE_SHA.encode(), new_store_sha, 'stream Store pin')
    stream = _replace(stream, b'import zlib\n', b'import zlib\nimport time\nfrom .source_read_budget_candidate import Budget\n', 'stream import')
    stream = _replace(stream, b'max_archive_bytes=DEFAULT_SOURCE_LIMIT, max_chars=MAX_RETURN_CHARS):',
                      b'max_archive_bytes=DEFAULT_SOURCE_LIMIT, max_chars=MAX_RETURN_CHARS,\n              should_continue=None, deadline=None, clock=time.monotonic):', 'stream signature')
    stream = _replace(stream, b"    key = ref['sha256']\n", b"    budget = Budget(deadline,should_continue,clock)\n    key = ref['sha256']\n", 'stream budget')
    stream = _replace(stream, b'        with store.tx() as conn:\n', b'        with budget.transaction(store) as conn:\n', 'source transaction')
    stream = _replace(stream, b'                while True:\n                    input_budget',
                      b'                while True:\n                    budget.check()\n                    input_budget', 'input cancellation')
    stream = _replace(stream, b'                    while data:\n                        old_len',
                      b'                    while data:\n                        budget.check()\n                        old_len', 'inflate cancellation')
    stream = _replace(stream, b"                result = ''.join(pieces)\n", b"                budget.check()\n                result = ''.join(pieces)\n", 'final cancellation')
    context = _replace(context, OPERATOR_ANCHOR, OPERATOR_ADDED, 'operator')
    context = _replace(context, b'USAGE=\':ctxos [status|last|shadow|active|',
                       b'USAGE=\':ctxos [status|last|shadow|active|recall status|on|off|', 'usage')
    runtime = result['v13/runtime.py']
    runtime = _replace(runtime, RUNTIME_ANCHOR, RUNTIME_ADDED, 'runtime retrieval')
    runtime = _replace(runtime, b"provenance=[e['source_ref']],budget_scale=body['modulation']",
                       b"provenance=[e['source_ref']]+meta.get('source_recall_refs',[]),budget_scale=body['modulation']", 'plan lineage')
    runtime = _replace(runtime, SAVE_ANCHOR, VERIFY_SAVE, 'context save validation')
    runtime = _replace(runtime, b"*meta.get('duplex_handoff_refs',[])]\n",
                       b"*meta.get('duplex_handoff_refs',[]),*meta.get('source_recall_refs',[])]\n", 'answer lineage')
    runtime = _replace(runtime, NATIVE_ANCHOR, VERIFY_NATIVE, 'model validation')
    result['v13/operator.py'] = _replace(result['v13/operator.py'],
        b':ctxos [status|last|shadow|active|layout ', b':ctxos [status|last|shadow|active|recall status|on|off|layout ', 'operator help')
    for old, raw in ((CONTEXT_SHA, context), (STREAM_SHA, stream)):
        recall = _replace(recall, old.encode(), hashlib.sha256(raw).hexdigest().encode(), 'source pin')
    recall = _replace(recall, STORE_SHA.encode(), new_store_sha, 'recall Store pin')
    result.update({'v13/runtime.py': runtime, 'v13/context_os.py': context, 'v13/store.py': store,
                   'v13/archive_stream_range_candidate.py': stream,
                   'v13/context_source_recall_candidate.py': recall,
                   'v13/source_read_budget_candidate.py': budget,
                   'v13/source_reuse_archive_candidate.py': reuse})
    return result
