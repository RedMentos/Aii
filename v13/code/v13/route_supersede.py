"""WP-Z6c: the human can let newer route corrections replace older contradicting ones (§24.32 L11 re-open).

Z6b showed the route head never adopts changed human evidence: old and new labels for the same kind of question stay
together in the training and validation set and block every candidate. Similarity of the native embeddings cannot find
"the same kind of question" (Z6b addendum), so the scope comes from the human, read by a fixed rule, never by a model:

  :ersetze route <Route> <Wort>[,<Wort>...] [--notiz Text]   older route labels whose question contains one of the words
                                                              (case-insensitive, whole substring) and that carry a
                                                              different route no longer train or validate the head
  :ersetze list / :ersetze undo <Id>
  --sofort                                                    WP-Z6d: the same words also route matching questions to <Route>
                                                              at answer time (fixed rule before scaffold/head; source
                                                              HUMAN_ROUTE_RULE), because the head may not be able to learn
                                                              the new boundary (Z6c)

  :ersetze pruefe <Id>                                        WP-Z6i: does the active learned head already do what the rule says?
  :ersetze gelernt <Id>                                       hand the rule over to the learned head (only after the check passed)
  :ersetze zurueck <Id>                                       take the handover back; the rule routes again
  --lehre                                                     WP-Z6i: with --sofort, questions the rule routed may also train
                                                              the head (label = the rule's route; a human correction on the
                                                              same question always wins). Off unless the human says so.

Nothing is deleted: feedback rows, sources and learning traces stay; the shadow manifest names every superseded label.
Only labels older than the rule are affected; a newer contradicting label wins again. Removing the rule restores them.

WP-Z6i lifecycle (rule -> learned): every time a --sofort rule matches a question, the active route head is asked in
shadow what it would do, and the answer is kept with the head's update id. A rule counts as learned for that head only
after HANDOVER_N matching questions in a row on which that exact head agreed. After the human hands the rule over, the
rule stops routing while the current head keeps agreeing; it routes again by itself as soon as the head disagrees once,
is rolled back, or is replaced by a new head that has not yet shown HANDOVER_N agreements (safety net, no new consent
needed to fall back, consent stays for the next head).
"""
import json
from .common import now
from .agi.base import new_id

KEY = 'ROUTE_SUPERSEDE_V1'
HANDOVER_N = 8      # BOOT: matching questions in a row the same head must route like the rule
OBS_KEEP = 32
ROUTES = ('simple', 'detail', 'gist', 'both')


def rules(store):
    return list((store.state(KEY)[0] or {}).get('rules', []))


def _mutate(store, fn):
    for attempt in (0, 1):
        st, v = store.state(KEY, None)
        st = st or {'rules': []}; out = fn(st)
        try:
            store.set_state(KEY, st, expected=v); return out
        except ValueError:
            if attempt: raise


def add(store, route, words, note='', apply_now=False, teach=False):
    if route not in ROUTES: raise ValueError('Route: ' + '|'.join(ROUTES))
    words = sorted({w.strip().lower() for w in words if w.strip()})
    if not words or any(len(w) < 3 for w in words): raise ValueError('Mindestens ein Wort mit 3+ Zeichen')
    rule = {'id': new_id('rsup'), 'route': route, 'words': words, 'note': note[:200], 'created': now(), 'origin': 'OPERATOR_TTY', 'apply_now': bool(apply_now)}
    if teach:
        if not apply_now: raise ValueError('--lehre nur zusammen mit --sofort')
        rule['teach'] = True
    _mutate(store, lambda st: st['rules'].append(rule)); return rule


def remove(store, rule_id):
    def fn(st):
        n = len(st['rules']); st['rules'] = [r for r in st['rules'] if r['id'] != rule_id]
        if len(st['rules']) == n: raise ValueError('Unbekannte Regel')
    _mutate(store, fn)


def superseded_by(text, label, created, active):
    """The rule that retires this label, or None. Fixed substring reader; newest matching rule decides."""
    t = text.lower()
    for r in sorted(active, key=lambda x: -x['created']):
        if r['created'] > created and any(w in t for w in r['words']):
            return r if label != r['route'] else None
    return None


def rule_route(store, text):
    """WP-Z6d: newest --sofort rule whose words occur in the question, or None (fixed reader, no model)."""
    t = text.lower()
    for r in sorted(rules(store), key=lambda x: -x['created']):
        if r.get('apply_now') and any(w in t for w in r['words']): return r
    return None


def _find(st, rule_id):
    for r in st['rules']:
        if r['id'] == rule_id: return r
    raise ValueError('Unbekannte Regel')


def learned(rule, head_id):
    """WP-Z6i: the last HANDOVER_N observations under exactly this head all agreed with the rule."""
    if not head_id: return False
    obs = [o for o in rule.get('obs', []) if o['head'] == head_id][-HANDOVER_N:]
    return len(obs) >= HANDOVER_N and all(o['agree'] for o in obs)


def observe(store, rule_id, head_route, head_id, event_id=None):
    """Record what the active head would do on a question the rule matched; returns the updated rule."""
    def fn(st):
        r = _find(st, rule_id); o = {'head': head_id, 'route': head_route, 'agree': head_route == r['route'], 'at': now(), 'event': event_id}
        r['obs'] = (r.get('obs', []) + [o])[-OBS_KEEP:]; return dict(r)
    return _mutate(store, fn)


def decide(store, text, head=None, event_id=None):
    """(rule, info) for the answer-time path. rule is None when no --sofort rule matches or a handed-over rule is
    carried by the current head. head: callable -> (route or None, head update id) or None, asked only on a match."""
    r = rule_route(store, text)
    if r is None: return None, None
    info = {'source': 'HUMAN_ROUTE_RULE', 'rule': r['id'], 'words': r['words'], 'authority': 'EXPLICIT_HUMAN_RULE'}
    if head is None:
        if r.get('teach') and event_id: observe(store, r['id'], None, None, event_id)
        return r, info
    try: h = head()
    except Exception as exc: h = None; info['head_shadow_error'] = type(exc).__name__
    if not h or not h[1]:
        if r.get('teach') and event_id: observe(store, r['id'], None, None, event_id)  # no head yet: still a teaching item
        return r, info
    r = observe(store, r['id'], h[0], h[1], event_id); info['head_shadow'] = {'route': h[0], 'head': h[1], 'agree': h[0] == r['route']}
    if r.get('handover') and learned(r, h[1]): return None, info | {'source': 'RULE_CARRIED_BY_HEAD'}
    return r, info


def status(store, rule_id, head_id):
    r = _find({'rules': rules(store)}, rule_id); obs = [o for o in r.get('obs', []) if o['head'] == head_id]
    run = 0
    for o in reversed(obs):
        if not o['agree']: break
        run += 1
    out = {'rule': rule_id, 'head': head_id, 'observed': len(obs), 'agree_in_a_row': run, 'needed': HANDOVER_N,
           'learned': learned(r, head_id), 'handover': bool(r.get('handover'))}
    if out['learned'] and not out['handover']: out['next'] = ':ersetze gelernt ' + rule_id
    elif r.get('teach') and obs and not obs[-1]['agree']: out['next'] = ':learn route'  # WP-Z6i2: learn while the head still disagrees
    return out


def set_handover(store, rule_id, on, head_id=None):
    def fn(st):
        r = _find(st, rule_id)
        if not r.get('apply_now'): raise ValueError('Nur --sofort-Regeln routen; nichts zu übergeben')
        if on and not learned(r, head_id): raise ValueError('Der gelernte Kopf hat die Regel noch nicht gezeigt (:ersetze pruefe)')
        r['handover'] = bool(on); r['handover_at'] = now(); r['handover_head'] = head_id if on else None
    _mutate(store, fn)


def taught(store, limit=32):
    """WP-Z6i --lehre: [(event_id, route, rule_id)] of the newest questions --lehre rules routed (newest last)."""
    out = {}
    for r in rules(store):
        if not (r.get('teach') and r.get('apply_now')): continue
        for o in r.get('obs', []):
            if o.get('event'): out[o['event']] = (o['at'], r['route'], r['id'])
    return [(ev, route, rid) for ev, (_, route, rid) in sorted(out.items(), key=lambda x: x[1][0])][-limit:]


def apply(store, data):
    """data: [(text, (feedback_row, event))] -> (kept, dropped) for learner.shadow()."""
    active = rules(store)
    if not active: return data, []
    kept, dropped = [], []
    for text, (row, e) in data:
        r = superseded_by(text, row['value'], row['created'], active)
        if r: dropped.append({'feedback_source_id': row['source_id'], 'label': row['value'], 'rule': r['id'], 'route': r['route']})
        else: kept.append((text, (row, e)))
    return kept, dropped


def operator_command(r, args):
    s = r.store
    if not args or args[0] == 'list': return json.dumps({'rules': rules(s)}, ensure_ascii=False, indent=1)
    if args[0] == 'undo' and len(args) == 2: remove(s, args[1]); return 'Ersetzungs-Regel entfernt; alte Korrekturen zählen wieder.'
    if args[0] in ('pruefe', 'gelernt', 'zurueck') and len(args) == 2:
        head = (s.components().get('route') or {}).get('update_id')
        if args[0] == 'gelernt':
            set_handover(s, args[1], True, head)
            return 'Regel %s an den gelernten Kopf übergeben. Sie greift wieder von selbst, sobald der Kopf einmal anders routet oder wechselt. Rücknahme: :ersetze zurueck %s' % (args[1], args[1])
        if args[0] == 'zurueck': set_handover(s, args[1], False); return 'Regel %s routet wieder selbst.' % args[1]
        st = status(s, args[1], head); return json.dumps(st, ensure_ascii=False)
    if args[0] == 'route' and len(args) >= 3:
        note = ''; now_ = '--sofort' in args; teach = '--lehre' in args
        args = [x for x in args if x not in ('--sofort', '--lehre')]
        if '--notiz' in args:
            i = args.index('--notiz'); note = ' '.join(args[i+1:]); args = args[:i]
        rule = add(s, args[1], ' '.join(args[2:]).split(','), note, now_, teach)
        return 'Regel %s: ältere Routen-Korrekturen mit %s zählen nicht mehr, wenn sie nicht "%s" sind.%s Rücknahme: :ersetze undo %s' % (
            rule['id'], ', '.join(rule['words']), rule['route'], (' Solche Fragen gehen ab jetzt direkt auf "%s".' % rule['route'] if now_ else '') + (' Sie dürfen den gelernten Kopf mit trainieren.' if teach else ''), rule['id'])
    raise ValueError(':ersetze route <Route> <Wort>[,<Wort>] [--sofort [--lehre]] [--notiz Text] | :ersetze list | :ersetze undo <Id> | :ersetze pruefe|gelernt|zurueck <Id>')
