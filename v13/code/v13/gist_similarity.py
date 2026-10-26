"""Read-only, same-session B2 latent tap similarity (Run616, SHADOW).

Only previously observed native final-token states; no automatic model call, factual
promotion, cross-session search, training, or receiver injection.
"""
import json
import math

import numpy as np

REVISION = 'run616-b2-final-token-similarity-v1'
MAX_SCAN = 64
MAX_RESULTS = 5
EXCERPT_CHARS = 160


class SimilarityUnavailable(ValueError):
    pass


def last_vector(data, expected_dim=None):
    vectors = data.get('vectors') if isinstance(data, dict) else None
    if not isinstance(vectors, list) or not vectors:
        raise SimilarityUnavailable('Empty native tap')
    vec = np.asarray(vectors[-1], dtype=np.float64)
    if vec.ndim != 1 or vec.size < 1 or (expected_dim is not None and vec.size != expected_dim):
        raise SimilarityUnavailable('Native tap dimension mismatch')
    if not np.isfinite(vec).all():
        raise SimilarityUnavailable('Nonfinite native state')
    norm = float(np.linalg.norm(vec))
    if not math.isfinite(norm) or norm <= 1e-10:
        raise SimilarityUnavailable('Zero or overflowing native state')
    return vec / norm


def event_bound(r, p):
    """A tap may be an exact event-source subspan, never a foreign source."""
    event = r.store.one('SELECT session_id,source_id,generation_id,packet FROM events WHERE id=?',
                        (p['event_id'],))
    if not event:
        raise SimilarityUnavailable('Missing native tap event')
    origin = json.loads(event['packet'])['source_ref']
    ref = p['source_ref']
    if (event['session_id'] != r.session or event['source_id'] != ref['source_id'] or
        event['generation_id'] != p['brain_generation_id'] or
        ref['source_id'] != origin['source_id'] or ref['sha256'] != origin['sha256'] or
        ref.get('modality') != origin.get('modality') or
        ref['char_start'] < origin['char_start'] or ref['char_end'] > origin['char_end'] or
        ref['char_start'] >= ref['char_end']):
        raise SimilarityUnavailable('Tap event/source/session binding mismatch')
    return True


def lookup(r, limit=MAX_RESULTS):
    if type(limit) is not int or not 1 <= limit <= MAX_RESULTS:
        raise ValueError(':gist similar [1..5]')
    # CASE avoids SQLite JSON exceptions from malformed historical packets.
    rows = r.store.rows("""SELECT p.id,p.payload,p.generation_id,p.event_id
        FROM packets p JOIN events e ON e.id=p.event_id
        WHERE e.session_id=? AND p.kind='LatentTapPacket'
          AND (CASE WHEN json_valid(p.payload) THEN json_extract(p.payload,'$.role') END)='B2_GIST'
        ORDER BY p.rowid DESC LIMIT ?""", (r.session, MAX_SCAN))
    if not rows:
        return {'revision': REVISION, 'status': 'NO_B2_TAP', 'authority': 'SHADOW_READ_ONLY',
                'matches': [], 'receiver_read_authority': 0, 'receiver_injection_authority': 0,
                'body_learning_authority': 0}
    current_revision = r.models.revision('B2_GIST')
    query = json.loads(rows[0]['payload'])
    if (query.get('packet_id') != rows[0]['id'] or query.get('brain_generation_id') != r.store.generation_id or
        query.get('model_revision') != current_revision or query.get('role') != 'B2_GIST'):
        raise SimilarityUnavailable('Latest B2 tap has stale model or brain generation')
    event_bound(r, query)
    query_data = r.cognition.read_tap(query)
    q = last_vector(query_data)
    query_ref = query['source_ref']
    seen = {query_ref['source_id']}
    found = []
    skipped = 0
    for row in rows[1:]:
        try:
            p = json.loads(row['payload'])
            if (p.get('packet_id') != row['id'] or p.get('brain_generation_id') != query['brain_generation_id'] or
                p.get('model_revision') != current_revision or p.get('tap_id') != query.get('tap_id') or
                p.get('role') != 'B2_GIST'):
                skipped += 1
                continue
            ref = p['source_ref']
            if ref['source_id'] in seen:
                continue
            event_bound(r, p)
            data = r.cognition.read_tap(p)
            v = last_vector(data, q.size)
            text = r.store.read_source(ref)
            score = float(np.dot(q, v))
            if not math.isfinite(score):
                raise SimilarityUnavailable('Invalid cosine')
            seen.add(ref['source_id'])
            found.append({'packet_id': p['packet_id'], 'source_ref': ref,
                          'excerpt': text[:EXCERPT_CHARS], 'cosine': round(max(-1., min(1., score)), 6)})
        except (KeyError, ValueError, TypeError, OSError, OverflowError):
            skipped += 1
    found.sort(key=lambda x: -x['cosine'])  # stable, latest tap wins ties
    out = {'revision': REVISION, 'status': 'READ_ONLY', 'authority': 'SHADOW_READ_ONLY',
           'query_packet_id': query['packet_id'], 'model_revision': current_revision,
           'scanned': len(rows), 'excluded': skipped, 'matches': found[:limit],
           'receiver_read_authority': 0, 'receiver_injection_authority': 0,
           'body_learning_authority': 0}
    r.store.log('gist_similarity', query['event_id'], {'scanned': len(rows), 'excluded': skipped,
                                                      'returned': len(out['matches']), 'authority': out['authority']})
    return out


def operator_command(r, args):
    if len(args) > 1:
        raise ValueError(':gist similar [1..5]')
    try:
        limit = int(args[0]) if args else MAX_RESULTS
    except (ValueError, TypeError):
        raise ValueError(':gist similar [1..5]') from None
    from .common import dumps
    return dumps(lookup(r, limit))
