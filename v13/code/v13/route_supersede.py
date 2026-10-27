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

Nothing is deleted: feedback rows, sources and learning traces stay; the shadow manifest names every superseded label.
Only labels older than the rule are affected; a newer contradicting label wins again. Removing the rule restores them.
"""
import json
from .common import now
from .agi.base import new_id

KEY = 'ROUTE_SUPERSEDE_V1'
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


def add(store, route, words, note='', apply_now=False):
    if route not in ROUTES: raise ValueError('Route: ' + '|'.join(ROUTES))
    words = sorted({w.strip().lower() for w in words if w.strip()})
    if not words or any(len(w) < 3 for w in words): raise ValueError('Mindestens ein Wort mit 3+ Zeichen')
    rule = {'id': new_id('rsup'), 'route': route, 'words': words, 'note': note[:200], 'created': now(), 'origin': 'OPERATOR_TTY', 'apply_now': bool(apply_now)}
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
    if args[0] == 'route' and len(args) >= 3:
        note = ''; now_ = '--sofort' in args
        args = [x for x in args if x != '--sofort']
        if '--notiz' in args:
            i = args.index('--notiz'); note = ' '.join(args[i+1:]); args = args[:i]
        rule = add(s, args[1], ' '.join(args[2:]).split(','), note, now_)
        return 'Regel %s: ältere Routen-Korrekturen mit %s zählen nicht mehr, wenn sie nicht "%s" sind.%s Rücknahme: :ersetze undo %s' % (
            rule['id'], ', '.join(rule['words']), rule['route'], ' Solche Fragen gehen ab jetzt direkt auf "%s".' % rule['route'] if now_ else '', rule['id'])
    raise ValueError(':ersetze route <Route> <Wort>[,<Wort>] [--sofort] [--notiz Text] | :ersetze list | :ersetze undo <Id>')
