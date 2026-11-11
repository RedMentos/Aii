"""F1/F5 and explicit learn consent for direct C3 and SDFT AG6 examples."""
import json

from .body_jepa_runtime_candidate import _EvidenceStore
from .common import dumps
from .memory import Memory

MAX_ITEMS = 256
MAX_CHARS = 8192


def _rows(store, ids):
    if type(ids) is not list or not 0 < len(ids) <= MAX_ITEMS:
        return []
    return store.rows('''SELECT m.id,m.event_id,m.source_id,m.session_id,m.kind,m.scope,
        substr(m.key_text,1,8193) AS key_text,substr(m.value,1,8193) AS value,s.hash,s.chars
        FROM memories m JOIN sources s ON s.id=m.source_id
        WHERE m.id IN (''' + ','.join('?' for _ in ids) + ''') AND m.active=1 AND s.deleted=0''', ids)


def _verified(store, cfg, rows):
    if not rows:
        return {}
    # Verify in small chunks; the reused verifier has a bounded per-event scan.
    result = {}
    for offset in range(0, len(rows), 32):
        chunk = rows[offset:offset + 32]
        proxy = _EvidenceStore(store, {row['event_id'] for row in chunk})
        for row in Memory(proxy, cfg)._verified_rows(chunk):
            feedback = store.rows('SELECT id,permission FROM feedback WHERE source_id=? LIMIT 2', (row['source_id'],))
            if len(feedback) == 1 and feedback[0]['permission'] == 'learn':
                envelope = store.one('SELECT substr(packet,1,16385) AS packet FROM events WHERE id=?', (row['event_id'],))
                ref = json.loads(envelope['packet'])['source_ref']
                prompt = proxy.read_source(ref)
                if len(prompt) <= MAX_CHARS and len(row['value']) <= MAX_CHARS:
                    result[row['id']] = (row, feedback[0]['id'], ref, prompt)
    return result


def candidates(weights, require_replay_pass=True, cap=True):
    done = weights.box.load()[0]['consolidated']
    rows = weights.s.rows('''SELECT m.id FROM memories m JOIN sources s ON s.id=m.source_id
        WHERE m.active=1 AND s.deleted=0 AND m.kind IN ('fact','style','preference')
        AND m.id NOT IN (SELECT value FROM json_each(?))
        AND EXISTS(SELECT 1 FROM feedback f WHERE f.source_id=m.source_id AND f.permission='learn')
        ORDER BY m.created LIMIT ?''', (dumps(done), MAX_ITEMS))
    verified = _verified(weights.s, weights.cfg, _rows(weights.s, [row['id'] for row in rows]))
    passed = weights._replay_passed() if require_replay_pass else None
    result = []
    for row, _, ref, prompt in verified.values():
        if passed is not None and row['event_id'] not in passed:
            continue
        # A legacy custom key without a bound human key decision is not a
        # trustworthy supervised prompt. Retrieval is unchanged.
        if row['key_text'] != prompt and not (row['kind'] == 'style' and row['key_text'] == '*'):
            continue
        result.append({'memory_id': row['id'], 'event_id': row['event_id'], 'kind': row['kind'],
                       'prompt': row['key_text'], 'target': row['value'],
                       'source_ref': {'source_id': row['source_id'], 'sha256': row['hash'],
                                      'char_start': 0, 'char_end': row['chars'], 'modality': 'text'},
                       'source_dependencies': [ref], 'learning_permission': 'learn'})
    return result


def sdft_candidates(weights):
    from .drift import TEACHER_TEMPLATE
    from .memory_trainer import answer_keys
    rows = weights.s.rows('''SELECT m.id FROM memories m JOIN sources s ON s.id=m.source_id
        WHERE m.active=1 AND s.deleted=0 AND m.kind IN ('fact','style','preference')
        AND EXISTS(SELECT 1 FROM feedback f WHERE f.source_id=m.source_id AND f.permission='learn')
        ORDER BY m.created LIMIT ?''', (MAX_ITEMS,))
    verified = _verified(weights.s, weights.cfg, _rows(weights.s, [row['id'] for row in rows]))
    done = weights.box.load()[0]['consolidated']
    result = []
    for row, fid, ref, prompt in verified.values():
        key = 'sdft:' + fid
        if key in done:
            continue
        result.append({'memory_id': key, 'consent_memory_id': row['id'], 'event_id': row['event_id'],
                       'kind': 'sdft', 'prompt': prompt, 'target': None,
                       'teacher_prompt': TEACHER_TEMPLATE.format(question=prompt, correction=row['value']),
                       'target_policy': 'SELF_TEACHER_IN_CONTEXT', 'origin': 'human_replay',
                       'answer_keys': answer_keys({'prompt': prompt, 'target': row['value']}),
                       'source_ref': {'source_id': row['source_id'], 'sha256': row['hash'],
                                      'char_start': 0, 'char_end': row['chars'], 'modality': 'text'},
                       'source_dependencies': [ref], 'learning_permission': 'learn'})
    return result


def check(weights, item, verified=None):
    if item.get('kind') == 'rated_answer':
        return  # The existing exact explicit-note/answer/dependency validator follows.
    if item.get('kind') not in ('fact', 'style', 'preference', 'sdft'):
        raise ValueError('unrecognized C3 consent item kind')
    mid = item.get('consent_memory_id') if item['kind'] == 'sdft' else item.get('memory_id')
    if verified is None:
        verified = _verified(weights.s, weights.cfg, _rows(weights.s, [mid]))
    if mid not in verified:
        raise ValueError('C3 F1/F5 or explicit learn consent changed')
    row, fid, ref, prompt = verified[mid]
    expected_ref = {'source_id': row['source_id'], 'sha256': row['hash'], 'char_start': 0,
                    'char_end': row['chars'], 'modality': 'text'}
    if (item.get('event_id') != row['event_id'] or item.get('source_ref') != expected_ref
            or item.get('source_dependencies') != [ref] or item.get('learning_permission') != 'learn'):
        raise ValueError('C3 consent source binding changed')
    if item['kind'] == 'sdft':
        from .drift import TEACHER_TEMPLATE
        from .memory_trainer import answer_keys
        if (item['memory_id'] != 'sdft:' + fid or item.get('prompt') != prompt or item.get('target') is not None
                or item.get('teacher_prompt') != TEACHER_TEMPLATE.format(question=prompt, correction=row['value'])
                or item.get('target_policy') != 'SELF_TEACHER_IN_CONTEXT' or item.get('origin') != 'human_replay'
                or item.get('answer_keys') != answer_keys({'prompt': prompt, 'target': row['value']})):
            raise ValueError('C3 self-distillation prompt or human correction changed')
    elif (item['kind'] != row['kind'] or item.get('target') != row['value']
          or item.get('prompt') != row['key_text']
          or (row['key_text'] != prompt and not (row['kind'] == 'style' and row['key_text'] == '*'))):
        raise ValueError('C3 direct prompt/target changed')


def training_cancel(weights, items, outer_cancel):
    def cancelled():
        if outer_cancel is not None and (outer_cancel() if callable(outer_cancel) else outer_cancel.is_set()):
            return True
        from .inputs import paused
        if weights.cfg.get('learning_mode') == 'RECORD_ONLY' or paused(weights.s, 'training'):
            raise ValueError('C3 training mode or pause changed')
        ids = list({item.get('consent_memory_id') if item.get('kind') == 'sdft' else item.get('memory_id')
                    for item in items if item.get('kind') != 'rated_answer'})
        verified = _verified(weights.s, weights.cfg, _rows(weights.s, ids))
        for item in items:
            if item.get('kind') == 'rated_answer':
                weights._check_item_sources(item)
            else:
                check(weights, item, verified)
        weights._guard_holdouts(items)
        return False
    return cancelled
