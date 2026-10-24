"""Isolated Run42 candidate: source-verified Sleep A TTT staging, no training authority.

A drop-in *candidate* for sleep_offline.stage_ttt. Production integration is not
performed here; native_history is the existing V13 lineage authority.
"""
import json
from pathlib import Path


def _stage(store, home, checkpoint, history, compress, write, dumps, state, cap=160, turns=64, limit=256):
    path = Path(home) / 'exports/sleep-ttt-candidates.jsonl'
    rows = []

    def compressed(raw):
        text, _spans, ok = compress(raw, cap)
        return text if ok or len(text) <= cap * 2 else text[:cap * 2]

    # Store.mutex is a re-entrant lock in V13. Keep the source validation and
    # final atomic export in one lock scope so a concurrent source deletion
    # cannot invalidate the checked data before it is exported.
    with store.mutex:
        st, _version = state(store)
        for session in sorted(st['sessions']):
            entries = st['sessions'][session]['entries']
            if not isinstance(entries, list) or any(not isinstance(e, dict) for e in entries):
                continue
            ids = [e.get('event_id') for e in entries]
            # Event identity must be unique within a digest session; a stale
            # duplicate must never borrow another entry's verified row.
            if any(not isinstance(eid, str) or not eid for eid in ids) or len(set(ids)) != len(ids):
                continue
            try:
                records, _refs = history(store, session, '', turns)
            except (ValueError, KeyError, TypeError, OSError, RuntimeError):
                # No fallback to the cached digest after lineage validation fails.
                continue
            by_event = {}
            for row in records:
                if row.get('role') in ('user', 'assistant') and row.get('status') == 'FINAL':
                    by_event.setdefault(row['event_id'], {})[row['role']] = row
            valid = {}
            for pos, e in enumerate(entries):
                try:
                    pair = by_event[e['event_id']]
                    if set(pair) != {'user', 'assistant'}:
                        continue
                    u, a = pair['user'], pair['assistant']
                    if (u['session_id'] != session or a['session_id'] != session
                            or a['id'] != e['msg']
                            or compressed(u['text']) != e['user']
                            or compressed(a['text']) != e['answer']):
                        continue
                    meta = json.loads(a['metadata'])
                    if not isinstance(meta, dict):
                        continue
                    valid[pos] = (u, a, meta)
                except (KeyError, TypeError, ValueError, IndexError):
                    continue
            for i, e in enumerate(entries[1:], 1):
                if checkpoint and i % 16 == 0:
                    checkpoint()
                start = max(0, i - 4)
                context = entries[start:i]
                # All previous turns actually used in the candidate must have
                # fresh, verified lineage; skipping invalid entries silently
                # would change the intended contextual learning target.
                if not context or any(pos not in valid for pos in range(start, i)):
                    continue
                target = valid.get(i)
                if not target or target[2].get('model_generated') is not True:
                    continue
                user, assistant, _meta = target
                ctx = '\n'.join('U: ' + x['user'] + ' | A: ' + x['answer'] for x in context)
                rows.append({'session': session, 'event_id': e['event_id'],
                             'context': ctx, 'input': user['text'], 'target': assistant['text'],
                             'status': 'CANDIDATE_NOT_TRAINED', 'label_source': 'own_final_answer',
                             'origin': 'self', 'requires': 'WP-I retention gate + human approval'})
        # An empty valid set MUST replace a previous export. A stale export
        # must never be interpreted as fresh verified training material.
        rows = rows[-limit:]
        write(path, ''.join(dumps(r) + '\n' for r in rows))
    return {'candidates': len(rows), 'path': str(path),
            'authority': 'STAGING_ONLY_NO_TRAINING'}


def stage_ttt_lineage_candidate(store, home, checkpoint=None):
    """Runtime adapter, intentionally not wired into production in Run42."""
    from v13.history import native_history
    from v13.context_os import compress
    from v13.common import atomic_write, dumps
    from v13.sleep_offline import _load, TURN_CAP, TURNS_MAX, TTT_MAX
    return _stage(store, home, checkpoint, native_history, compress,
                  atomic_write, dumps, _load, TURN_CAP, TURNS_MAX, TTT_MAX)
