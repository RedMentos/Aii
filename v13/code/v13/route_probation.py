"""WP-KL6: probation for a new route head before the human is asked to approve it.

KL2-KL3b showed no fixed threshold on the shadow job's own few corrections both always adopts a changed preference
and never briefly gets worse: the parent is judged on labels it trained on, the candidate out of sample. Probation
judges both prospectively on the next human route corrections, which neither has seen: each new correction scores
one hit for the candidate and/or the active head (or the scaffold if no head is active). Fixed rule, no model:
  READY   after >= MIN_OBSERVED corrections when the candidate is right at least as often as the parent, at least
          MIN_SHARE of the time, and strictly more often unless it was right every time
  REJECT  after >= MIN_OBSERVED corrections otherwise
A newer shadow candidate replaces the running probation. Nothing is promoted here; `:approve` stays with the human.
"""
import json
from .common import now

KEY = 'ROUTE_PROBATION_V1'
MIN_OBSERVED = 8   # BOOT: one batch of corrections
MIN_SHARE = .75    # BOOT: same floor as the shadow gate's accuracy


def state(store):
    return store.state(KEY, None)[0]


def _set(store, st):
    _, v = store.state(KEY, None); store.set_state(KEY, st, expected=v)


def start(r, update_id):
    u = r.store.one('SELECT * FROM updates WHERE id=?', (update_id,))
    if not u or u['status'] != 'PENDING_APPROVAL' or json.loads(u['manifest']).get('component') != 'route':
        raise ValueError('Probation braucht ein offenes Routen-Update (PENDING_APPROVAL)')
    st = {'update_id': update_id, 'path': u['path'], 'parent_generation': r.store.generation_id, 'observed': 0,
          'candidate_hits': 0, 'parent_hits': 0, 'started': now(), 'verdict': 'RUNNING'}
    _set(r.store, st); return st


def _predict(r, path, text, source_id):
    import numpy as np
    from .learning_worker import features
    from .route_features import for_head
    from .learning import ROUTES
    x = features([r.learner.embedding(text, source_id, __import__('time').monotonic() + 60)])
    with np.load(path, allow_pickle=False) as z: w = z['route_w']
    return ROUTES[int(np.argmax(for_head(x, [text], w.shape[0]) @ w))]


def observe(r, event_id, label):
    """Score a new human route correction for the running probation; returns the state or None."""
    st = state(r.store)
    if not st or st['verdict'] != 'RUNNING': return st
    u = r.store.one('SELECT status FROM updates WHERE id=?', (st['update_id'],))
    if not u or u['status'] != 'PENDING_APPROVAL' or r.store.generation_id != st['parent_generation']:
        st['verdict'] = 'STALE'; _set(r.store, st); return st
    e = json.loads(r.store.one('SELECT packet FROM events WHERE id=?', (event_id,))['packet'])
    text = r.store.read_source(e['source_ref']); sid = e['source_ref']['source_id']
    cand = _predict(r, r.home/st['path'], text, sid)
    active = r.learner.active()
    if active is None:
        from .cognition import scaffold_route
        parent = scaffold_route(text)
    else: parent = _predict(r, active, text, sid)
    st['observed'] += 1; st['candidate_hits'] += int(cand == label); st['parent_hits'] += int(parent == label)
    if st['observed'] >= MIN_OBSERVED:
        c, p, n = st['candidate_hits'], st['parent_hits'], st['observed']
        st['verdict'] = 'READY' if c >= p and c / n >= MIN_SHARE and (c > p or c == n) else 'REJECT'
    _set(r.store, st); return st


def operator_command(r, args):
    if not args or args[0] == 'status': return json.dumps(state(r.store), ensure_ascii=False)
    if args[0] == 'start' and len(args) == 2: return json.dumps(start(r, args[1]), ensure_ascii=False)
    raise ValueError(':probation status | :probation start <Update-ID>')
