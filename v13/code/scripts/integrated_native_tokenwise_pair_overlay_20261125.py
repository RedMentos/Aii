"""Pinned V14 tokenwise diagnostic runtime composition.

Applies the Core-owned explicit local probe consumer after the existing
recovery, native receiver, C4, observer, and ActionSelection overlays. The
producer path is diagnostic-only: it does not fit adapters or activate B3.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_PINS = {
    "v13/runners.py": "36fba563a7d7f23b384498ffb1a73b8f80193339",
    "v13/cognition.py": "e2117b3372af325dea23f4e77ed7afd51bc31c7e",
    "v13/callosum.py": "10c25889ed76fc10be51c39d1342fd174aa2607f",
    "v13/native_probe_approval.py": "2a36065b566f49c31cdd9ba7b1e4ba618ad51bc5",
    "v13/latent_adapter.py": "c450377a8263b83570320a1ecabc8f059c266afe",
    "v13/native_input_embedding_tap.py": "36c03f2cb76eca55f5751d8cee944697a8f1c17d",
    "v13/native_tokenwise_pairing.py": "723a26c30524b6bc44794bb34c09c3841b526b56",
    "v13/native_input_embedding_extractor.py": "ff328d40efcd0f3a77a60b5202fd115be041f3ae",
    "v13/native_tokenwise_pair_runtime.py": "bc05fdf4ea378592f8ab7ac0c9d62822862888fb",
    "v13/native_input_embedding_extractor_build.py": "2b1b1b5ff19c94928e80c951339ca3fd9acacb9e",
    "v13/native/input_embedding_extractor/CMakeLists.txt": "a5ed5453adc99d2fd0fb9b26015e0613e70f0642",
    "v13/native/input_embedding_extractor/native_input_embedding_extractor.cpp": "f908d877b2e209f609ae387c05be3fa2407b64c8",
}


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _read_regular(root: Path, relative: str) -> bytes:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ValueError("tokenwise composition input missing or linked: " + relative)
    raw = path.read_bytes()
    expected = SOURCE_PINS.get(relative)
    if expected is not None and _git_blob_sha1(raw) != expected:
        raise ValueError("tokenwise composition source pin changed: " + relative)
    return raw


def _replace_once(raw: bytes, old: bytes, new: bytes, label: str) -> bytes:
    count = raw.count(old)
    if count != 1:
        raise ValueError("tokenwise overlay expected one " + label + " anchor, found " + str(count))
    return raw.replace(old, new, 1)


def apply_staged_tokenwise(code_dir: Path, staging: Path) -> dict[str, bytes]:
    code_dir = Path(code_dir).resolve(strict=True)
    staging = Path(staging).resolve(strict=True)
    for relative in SOURCE_PINS:
        source = _read_regular(code_dir, relative)
        if relative.endswith(".py"):
            compile(source, str(code_dir / relative), "exec")

    runner_path = staging / "v13/runners.py"
    cognition_path = staging / "v13/cognition.py"
    callosum_path = staging / "v13/callosum.py"
    approval_path = staging / "v13/native_probe_approval.py"
    staged = {}
    for path in (runner_path, cognition_path, callosum_path, approval_path):
        if path.is_symlink() or not path.is_file():
            raise ValueError("tokenwise overlay staged target missing or linked: " + str(path))
        staged[str(path.relative_to(staging))] = path.read_bytes()

    runner = staged["v13/runners.py"]
    if b"def tokenize_with_pieces(" in runner:
        raise ValueError("tokenwise tokenizer method already exists; refusing double application")
    runner = _replace_once(
        runner,
        b"from .common import APP,dumps,digest,atomic_write,Cancelled,Unavailable,Limits",
        b"from .common import APP,dumps,digest,atomic_write,file_hash,Cancelled,Unavailable,Limits",
        "LlamaRunner common import",
    )
    tokenizer_method = b'''    def tokenize_with_pieces(self,text,cancel,deadline,max_tokens=64):
        """Return the exact add_special=false token stream and byte pieces.

        A missing with_pieces response is a hard failure: no guessed character
        spans or positional alignment are permitted for the tokenwise path.
        """
        if self.purpose != 'tap':
            raise Unavailable('Exact token-piece tokenization is restricted to a tap runner')
        if type(text) is not str or not text or len(text.encode('utf-8')) > 16384:
            raise ValueError('Exact token-piece input must be bounded nonempty UTF-8 text')
        if type(max_tokens) is not int or not 2 <= max_tokens <= 64:
            raise ValueError('Exact token-piece limit must be 2..64')
        self.load(cancel,deadline)
        try:
            check(cancel,deadline)
            result=self._json('POST','/tokenize',{'content':text,'add_special':False,'with_pieces':True},deadline,timeout_cap=None)
            check(cancel,deadline)
            rows=result.get('tokens') if isinstance(result,dict) else None
            if not isinstance(rows,list) or not 2 <= len(rows) <= max_tokens:
                raise Unavailable('Native tokenizer did not return 2..64 exact content-token pieces')
            token_ids=[];token_pieces=[]
            for row in rows:
                if (not isinstance(row,dict) or type(row.get('id')) is not int
                        or not 0 <= row['id'] <= 2147483647 or 'piece' not in row):
                    raise Unavailable('Native tokenizer token-piece row is not canonical')
                piece=row['piece']
                if not (type(piece) is str or
                        (isinstance(piece,list) and all(type(value) is int and 0 <= value <= 255 for value in piece))):
                    raise Unavailable('Native tokenizer piece must be exact text or UTF-8 bytes')
                token_ids.append(row['id'])
                token_pieces.append({'id':row['id'],'piece':piece})
            tokenizer_revision='llama-server-sha256:'+file_hash(self.binary)
            return {
                'token_ids':token_ids,
                'token_pieces':token_pieces,
                'tokenizer_revision':tokenizer_revision,
                'request':{'add_special':False,'with_pieces':True},
            }
        except BaseException:
            self.unload()
            check(cancel,deadline)
            raise
'''
    runner = _replace_once(
        runner,
        b"    def tap(self,text,cancel,deadline,max_tokens=64):",
        tokenizer_method + b"    def tap(self,text,cancel,deadline,max_tokens=64):",
        "LlamaRunner.tap",
    )
    staged["v13/runners.py"] = runner

    cognition = staged["v13/cognition.py"]
    if b"def native_tokenwise_pair_probe(" in cognition:
        raise ValueError("tokenwise Cognition method already exists; refusing double application")
    cognition_method = b'''    def native_tokenwise_pair_probe(self,sender_role,receiver_role,e,source_ref,lease_token,deadline):
        """Build a local source-bound tokenwise diagnostic; never fit or inject it."""
        import time
        from pathlib import Path
        from .common import file_hash
        from .runners import check
        from .native_probe_approval import KEY,_require_runtime_probe_lease
        from .native_input_embedding_extractor import extract_native_input_embedding_rows
        from .native_input_embedding_tap import build_native_input_embedding_tap_manifest_from_extractor_output
        from .native_tokenwise_pairing import _RECEIVER_TAPS,build_native_tokenwise_pair_record

        _require_runtime_probe_lease(self.r,lease_token)
        approval,_=self.s.state(KEY,None)
        if (not isinstance(approval,dict) or approval.get('status')!='CONSUMED'
                or approval.get('purpose')!='TOKENWISE_PAIR_DIAGNOSTIC'
                or approval.get('sender_role')!=sender_role
                or approval.get('receiver_role')!=receiver_role
                or approval.get('session_id')!=self.r.session
                or approval.get('event_id')!=e.get('event_id')
                or approval.get('brain_generation_id')!=e.get('brain_generation_id')
                or approval.get('source_ref')!=source_ref
                or source_ref!=e.get('source_ref')):
            raise PermissionError('tokenwise pairing approval/source binding changed')
        if sender_role not in {'B1_DETAIL','B2_GIST'} or receiver_role not in _RECEIVER_TAPS or sender_role==receiver_role:
            raise ValueError('tokenwise pairing requires distinct B1/B2 sender and B1/B2/C3 receiver roles')
        source_text=self.s.read_source(source_ref)
        if (source_ref.get('char_start')!=0 or source_ref.get('char_end')!=len(source_text)
                or not source_text):
            raise ValueError('tokenwise pairing requires the exact full source span')
        models=approval.get('models')
        sender_binding=models.get(sender_role) if isinstance(models,dict) else None
        receiver_binding=models.get(receiver_role) if isinstance(models,dict) else None
        if (not isinstance(sender_binding,dict) or not isinstance(receiver_binding,dict)
                or not isinstance(sender_binding.get('sha256'),str)
                or not isinstance(receiver_binding.get('sha256'),str)
                or self.r.models.revision(sender_role)!=sender_binding.get('revision')
                or self.r.models.revision(receiver_role)!=receiver_binding.get('revision')):
            raise PermissionError('tokenwise pairing installed model revisions differ from local approval')
        check(self.r.cancel_event,deadline)

        sender_tap_packet=self.tap(sender_role,e,source_ref,deadline)
        sender_tap_data=self.read_tap(sender_tap_packet)
        sender_runner=self.r.pool.get_tap(sender_role)
        sender_stream=sender_runner.tokenize_with_pieces(source_text,self.r.cancel_event,deadline,max_tokens=64)
        check(self.r.cancel_event,deadline)

        receiver_runner=self.r.pool.get_tap(receiver_role)
        receiver_stream=receiver_runner.tokenize_with_pieces(source_text,self.r.cancel_event,deadline,max_tokens=64)
        receiver_model_path=Path(self.r.models.path_for(receiver_role))
        receiver_model_sha=receiver_binding['sha256']
        if file_hash(receiver_model_path)!=receiver_model_sha:
            raise PermissionError('tokenwise receiver model changed after local approval')
        check(self.r.cancel_event,deadline)

        extractor_output=extract_native_input_embedding_rows(
            Path(self.r.home)/'bin/native_input_embedding_extractor',
            receiver_model_path,
            receiver_binding['revision'],
            receiver_stream['token_ids'],
            model_root=Path(self.r.home)/'models',
            expected_model_sha256=receiver_model_sha,
            prepare_idle=self.r.pool.unload,
            timeout_seconds=min(120,max(1,int(deadline-time.monotonic()))),
            cancel_event=self.r.cancel_event,
        )
        check(self.r.cancel_event,deadline)
        receiver_tap=build_native_input_embedding_tap_manifest_from_extractor_output(
            receiver_role,source_text,receiver_stream['token_ids'],receiver_stream['token_pieces'],
            extractor_output,source_id=source_ref['source_id'],event_id=e['event_id'],
            brain_generation_id=e['brain_generation_id'],model_revision=receiver_binding['revision'],
            model_sha256=receiver_model_sha,tokenizer_revision=receiver_stream['tokenizer_revision'],
        )
        pair_record=build_native_tokenwise_pair_record(
            source_text,source_ref,
            sender_stream['token_ids'],sender_stream['token_pieces'],sender_tap_packet,sender_tap_data,
            receiver_stream['token_ids'],receiver_stream['token_pieces'],extractor_output,
            source_id=source_ref['source_id'],session_id=self.r.session,event_id=e['event_id'],
            brain_generation_id=e['brain_generation_id'],sender_role=sender_role,receiver_role=receiver_role,
            sender_tap_id=sender_tap_packet['tap_id'],receiver_tap_id=_RECEIVER_TAPS[receiver_role],
            sender_model_revision=sender_binding['revision'],receiver_model_revision=receiver_binding['revision'],
            sender_model_sha256=sender_binding['sha256'],receiver_model_sha256=receiver_model_sha,
            sender_tokenizer_revision=sender_stream['tokenizer_revision'],
            receiver_tokenizer_revision=receiver_stream['tokenizer_revision'],
        )
        check(self.r.cancel_event,deadline)
        pairs=pair_record.get('pairs')
        if (pair_record.get('status')!='PAIRED_DIAGNOSTIC' or not isinstance(pairs,list)
                or pair_record.get('pair_count')!=len(pairs) or not pairs):
            raise ValueError('native tokenwise pair record failed its pair-count contract')
        pair_summary={key:value for key,value in pair_record.items() if key!='pairs'}
        manifest=receiver_tap['manifest']
        summary={
            'status':'PAIRED_DIAGNOSTIC',
            'sender_role':sender_role,'receiver_role':receiver_role,
            'source_id':source_ref['source_id'],'event_id':e['event_id'],
            'sender_model_revision':sender_binding['revision'],
            'receiver_model_revision':receiver_binding['revision'],
            'sender_model_sha256':sender_binding['sha256'],
            'receiver_model_sha256':receiver_model_sha,
            'sender_tokenizer_revision':sender_stream['tokenizer_revision'],
            'receiver_tokenizer_revision':receiver_stream['tokenizer_revision'],
            'sender_tap_packet_id':sender_tap_packet['packet_id'],
            'receiver_manifest_sha256':manifest['manifest_sha256'],
            'record_sha256':pair_record['record_sha256'],
            'pair_count':pair_record['pair_count'],
            'minimum_coverage':pair_record['minimum_coverage'],
            'mean_coverage':pair_record['mean_coverage'],
            'metadata_persisted':True,
            'pair_vectors_persisted':False,
            'raw_receiver_rows_persisted':False,
            'production_route':False,
            'semantic_use_proven':False,
            'training_authority':0,
            'native_receiver_authority':0,
            'learning_authority':0,
        }
        state_key='native_tokenwise_pair:'+e['event_id']+':'+sender_role+':'+receiver_role+':'+sender_binding['sha256'][:12]+':'+receiver_model_sha[:12]
        existing,version=self.s.state(state_key,None)
        if isinstance(existing,dict):
            if (existing.get('summary',{}).get('record_sha256')==summary['record_sha256']
                    and existing.get('receiver_manifest',{}).get('manifest_sha256')==manifest['manifest_sha256']):
                return dict(existing['summary'],status='ALREADY_PERSISTED')
            raise RuntimeError('a different tokenwise record already exists for this exact event/model binding')
        bundle={
            'schema':'v14.native-tokenwise-pair-persistence/1',
            'status':'PAIRED_DIAGNOSTIC',
            'source_ref':dict(source_ref),
            'session_id':self.r.session,
            'event_id':e['event_id'],
            'brain_generation_id':e['brain_generation_id'],
            'receiver_manifest':manifest,
            'pair_record':pair_summary,
            'summary':summary,
            'persisted_at_unix':time.time(),
            'raw_receiver_rows_persisted':False,
            'pair_vectors_persisted':False,
            'production_route':False,
            'semantic_use_proven':False,
            'training_authority':0,
            'native_receiver_authority':0,
            'learning_authority':0,
        }
        self.s.set_state(state_key,bundle,expected=version)
        self.s.log('native_tokenwise_pair',e['event_id'],{
            'status':'PAIRED_DIAGNOSTIC','pair_count':pair_record['pair_count'],
            'minimum_coverage':pair_record['minimum_coverage'],
            'mean_coverage':pair_record['mean_coverage'],
        })
        return summary
'''
    cognition = _replace_once(
        cognition,
        b"    def body_context(self,role,e):",
        cognition_method + b"    def body_context(self,role,e):",
        "Cognition.body_context",
    )
    staged["v13/cognition.py"] = cognition

    approval = staged["v13/native_probe_approval.py"]
    if b"purpose='TOKENWISE_PAIR_DIAGNOSTIC'" in approval:
        raise ValueError("tokenwise approval purpose already exists; refusing double application")
    approval = _replace_once(
        approval,
        b"def arm(runtime, sender_role, receiver_role, *, now=None, adapter_name=None):\n    \"\"\"Arm one exact probe only from an interactive local terminal.\"\"\"\n    _require_local_tty()",
        b"def arm(runtime, sender_role, receiver_role, *, now=None, adapter_name=None, purpose='NATIVE_RECEIVER_PROBE'):\n    \"\"\"Arm one exact probe only from an interactive local terminal.\"\"\"\n    if purpose not in {'NATIVE_RECEIVER_PROBE','TOKENWISE_PAIR_DIAGNOSTIC'} or (purpose=='TOKENWISE_PAIR_DIAGNOSTIC' and adapter_name is not None):\n        raise ValueError('native probe purpose/adapter combination is invalid')\n    _require_local_tty()",
        "native probe arm signature",
    )
    approval = _replace_once(
        approval,
        b"    record = {\n        \"schema\": SCHEMA,\n        \"status\": \"PENDING\",",
        b"    record = {\n        \"schema\": SCHEMA,\n        \"purpose\": purpose,\n        \"status\": \"PENDING\",",
        "native probe approval record",
    )
    approval = _replace_once(
        approval,
        b"    result = {\n        \"status\": \"ARMED\",",
        b"    result = {\n        \"status\": \"ARMED\",\n        \"purpose\": purpose,",
        "native probe arm result",
    )
    approval = _replace_once(
        approval,
        b"def consume(runtime, sender_role, receiver_role, event, source_ref, *, now=None, lease_token=None, adapter_name=None):",
        b"def consume(runtime, sender_role, receiver_role, event, source_ref, *, now=None, lease_token=None, adapter_name=None, purpose='NATIVE_RECEIVER_PROBE'):",
        "native probe consume signature",
    )
    approval = _replace_once(
        approval,
        b"    if not isinstance(record, dict) or record.get(\"schema\") != SCHEMA or record.get(\"status\") != \"PENDING\":\n        raise PermissionError(\"native probe requires a fresh local :callosum arm-probe approval\")",
        b"    if not isinstance(record, dict) or record.get(\"schema\") != SCHEMA or record.get(\"status\") != \"PENDING\":\n        raise PermissionError(\"native probe requires a fresh local one-shot approval\")\n    if record.get(\"purpose\",\"NATIVE_RECEIVER_PROBE\") != purpose:\n        raise PermissionError(\"native probe approval purpose differs from the requested diagnostic\")",
        "native probe consume approval check",
    )
    approval = _replace_once(
        approval,
        b"    return {\n        \"approval_id\": record[\"nonce\"][:12],",
        b"    return {\n        \"approval_id\": record[\"nonce\"][:12],\n        \"purpose\": purpose,",
        "native probe consume result",
    )
    approval = _replace_once(
        approval,
        b"def revoke(runtime, *, now=None):",
        b"def revoke(runtime, *, now=None, purpose='NATIVE_RECEIVER_PROBE'):",
        "native probe revoke signature",
    )
    approval = _replace_once(
        approval,
        b"    if not isinstance(record, dict) or record.get(\"status\") != \"PENDING\":\n        return {\"status\": \"NO_PENDING_APPROVAL\"}",
        b"    if (not isinstance(record, dict) or record.get(\"status\") != \"PENDING\"\n            or record.get(\"purpose\",\"NATIVE_RECEIVER_PROBE\") != purpose):\n        return {\"status\": \"NO_PENDING_APPROVAL\"}",
        "native probe revoke purpose check",
    )
    staged["v13/native_probe_approval.py"] = approval

    callosum = staged["v13/callosum.py"]
    dispatch = b'''    if args and args[0] in {"arm-tokenwise","tokenwise-pair","revoke-tokenwise","build-tokenwise-extractor"}:
        from .native_tokenwise_pair_runtime import operator_command as tokenwise_command
        return tokenwise_command(r,args)
'''
    callosum = _replace_once(
        callosum,
        b"    c=controller(r)\n",
        dispatch + b"    c=controller(r)\n",
        "Callosum controller dispatch",
    )
    staged["v13/callosum.py"] = callosum

    for relative, payload in staged.items():
        compile(payload, str(staging / relative), "exec")
    if (b"def tokenize_with_pieces(" not in staged["v13/runners.py"]
            or b"def native_tokenwise_pair_probe(" not in staged["v13/cognition.py"]
            or b"arm-tokenwise" not in staged["v13/callosum.py"]
            or b"TOKENWISE_PAIR_DIAGNOSTIC" not in staged["v13/native_probe_approval.py"]):
        raise ValueError("tokenwise staged consumer did not pass its post-composition checks")
    return staged
