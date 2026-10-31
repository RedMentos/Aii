"""Default-OFF JEF→C3 JSON-schema formatter adapter, source-rechecking SHADOW.

This is a software callback boundary, not native execution, TTY permission,
model quality proof, output dispatch, or a training/age promotion.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

from .common import dumps
from .jef_c3_typed_envelope_candidate import build_jef_c3_typed_envelope

SCHEMA = {'type':'object', 'properties':{'action':{'type':'string','enum':['A','B','NONE']}},
          'required':['action'], 'additionalProperties':False}
SCHEMA_SHA256 = hashlib.sha256(dumps(SCHEMA).encode('utf-8')).hexdigest()
MAX_NATIVE_BYTES = 1024
TABLES = ('sources','events','memories','actions','messages','packets')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _unique(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('DUPLICATE_JSON_KEY')
        out[k]=v
    return out


def _parse(raw):
    if type(raw) is not str or not 0<len(raw.encode('utf-8'))<=MAX_NATIVE_BYTES:
        return None
    try:
        parsed=json.loads(raw,object_pairs_hook=_unique,
                          parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE')))
    except (ValueError,TypeError,UnicodeError):
        return None
    if type(parsed) is not dict or set(parsed)!={'action'} or type(parsed['action']) is not str:
        return None
    return parsed['action'] if parsed['action'] in ('A','B','NONE') else None


def _footprint(memory):
    store=memory.s
    return tuple(store.one('SELECT COUNT(*) AS n FROM '+table)['n'] for table in TABLES)


def _mutation_epoch(memory):
    """Detect writes, including UPDATE-without-count-change and external commits.

    This is detection, NOT a sandbox: a callback's writes are not rolled back.
    Only isolated/trusted callbacks should receive access to the Store.
    """
    db=memory.s.db
    return (db.total_changes, db.execute('PRAGMA data_version').fetchone()[0],
            db.in_transaction)


def _result(status, **kw):
    return {'schema':'v13.jef_c3_schema_source_recheck_shadow.v1',
            'status':status, 'delivery_authority':0, 'output_committed':False,
            'tool_dispatches':0, 'learning_authority':0,
            'real_tty_approved':False, 'native_proof':False,
            'age0':'RECORD_ONLY', 'step2':'UTILITY_FAIL',
            'b3':'NO_PROMOTION', 'body_jepa':'UNAVAILABLE',
            'world_jepa':'SHADOW', 'jepa_weight':0,
            'redmi_measured':False, 'whole_system_complete':False,
            'callback_invoked':False, 'source_rechecked':False,
            'schema_sha256':SCHEMA_SHA256, **kw}


def format_schema_shadow(memory,session,event_id,current_ref,memory_ids,generate,
                         *,operator_opt_in=False,callback_opt_in=False,
                         approval_receipt=None):
    """Return only a source-bound SHADOW verdict; never commit model text."""
    if operator_opt_in is not True or callback_opt_in is not True:
        return _result('OFF')
    if approval_receipt is not None:
        return _result('REAL_TTY_APPROVAL_UNSUPPORTED')
    if not callable(generate):
        return _result('INVALID_CALLBACK')
    try:
        before=build_jef_c3_typed_envelope(memory,session,event_id,current_ref,
                                           memory_ids,operator_opt_in=True)
        if before.get('status')!='JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL':
            return _result('SOURCE_ADMISSION_RED',admission_status=before.get('status'))
        if _sha(dumps(before['messages']).encode('utf-8'))!=before['messages_sha256']:
            return _result('ENVELOPE_HASH_RED')
        before_dump=dumps(before)
        footprint=_footprint(memory)
        epoch=_mutation_epoch(memory)
        if epoch[2]:
            return _result('SOURCE_INTEGRITY_RED')
        action=before['typed_jef_action']
        refs=list(before['source_ref_sha256'])
        current_sha=before['current_source_sha256']
        prompt_sha=before['messages_sha256']
    except Exception:
        return _result('SOURCE_INTEGRITY_RED')
    called=True
    try:
        raw=generate(deepcopy(before['messages']),deepcopy(SCHEMA))
    except Exception as exc:
        return _result('CALLBACK_RED',callback_invoked=called,error_type=type(exc).__name__)
    try:
        if dumps(before)!=before_dump:
            return _result('CALLBACK_MUTATED_ENVELOPE_RED',callback_invoked=called)
        if (_footprint(memory)!=footprint or _mutation_epoch(memory)!=epoch):
            return _result('CALLBACK_STORE_MUTATION_RED',callback_invoked=called)
        after=build_jef_c3_typed_envelope(memory,session,event_id,current_ref,
                                          memory_ids,operator_opt_in=True)
        if (after.get('status')!='JEF_C3_TYPED_ENVELOPE_SHADOW_NO_MODEL_CALL'
                or dumps(after)!=before_dump
                or after['messages_sha256']!=prompt_sha
                or after['source_ref_sha256']!=refs
                or after['current_source_sha256']!=current_sha):
            return _result('POST_CALLBACK_SOURCE_RED',callback_invoked=called)
        if (_footprint(memory)!=footprint or _mutation_epoch(memory)!=epoch):
            return _result('POST_CALLBACK_STORE_MUTATION_RED',callback_invoked=called)
        base={'callback_invoked':called,'source_rechecked':True,
              'messages_sha256':prompt_sha,'source_ref_sha256':refs,
              'current_source_sha256':current_sha,'typed_jef_action':action}
        if type(raw) is not str or not 0<len(raw.encode('utf-8'))<=MAX_NATIVE_BYTES:
            return _result('FORMATTER_OUTPUT_SHAPE_RED',**base)
        parsed=_parse(raw)
        base.update(output_sha256=_sha(raw.encode('utf-8')),
                    output_bytes=len(raw.encode('utf-8')))
        if parsed is None:
            return _result('FORMATTER_JSON_RED',source_only_fallback=True,**base)
        if parsed!=action:
            return _result('FORMATTER_ACTION_MISMATCH_RED',parsed_action=parsed,
                           source_only_fallback=True,**base)
        return _result('FORMATTER_MATCH_SHADOW',parsed_action=parsed,
                       formatter_match=True,source_only_fallback=False,**base)
    except Exception as exc:
        return _result('POST_CALLBACK_INTEGRITY_RED',callback_invoked=called,
                       error_type=type(exc).__name__)
