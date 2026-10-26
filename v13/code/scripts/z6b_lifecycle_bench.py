#!/usr/bin/env python3
"""WP-Z6b / §24.32 Fluid Experience Lifecycle on the real STEP5 route-head learner (Needle embeddings, NumPy worker).

One stream of experiences, replayed identically per policy arm in a fresh home:
  record-only   40 events without feedback (must cause no update)
  phase 1       6 batches x 8 human route corrections (2 per route), all four routes
  phase 2       4 batches x 8 corrections; new evidence: the user now wants "half of X" questions answered 'simple'
                (4 of 8 per batch relabel that pattern; regression evidence for the active head -> L11 reopen)
Policies decide after each batch whether to run a shadow job (L5/L7) and promote an eligible candidate (L9, the
harness plays the human who approves every PENDING_APPROVAL it is shown):
  fixed     shadow after every batch
  adaptive  shadow only when the active head misroutes >= 25 % of the batch's corrected items (or no head exists yet)
  none      never learns (scaffold routes only)
The bench, not the policy, scores every candidate and active head on a fixed held-out set (8 per route plus 8 half-of-X items, new
paraphrases; after the shift the half-of-X items carry the new label). Real Runtime, real learner.shadow(),
Operator ':approve', real rollback (store.rollback) at the end. Criteria: PREREG.md (docs/proofs/continuation-20261026/
z6b-lifecycle). Usage: z6b_lifecycle_bench.py <installed_home> <out.json> [--seed 71]
"""
import argparse
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ROUTE_NAMES = ('simple', 'detail', 'gist', 'both')
FILL = {'a': ['Bus', 'Bahn', 'Python', 'Java', 'Stadt', 'Land', 'Tee', 'Kaffee', 'Sommer', 'Winter', 'Miete', 'Kauf', 'Rad', 'Auto'],
        'n': [12, 18, 24, 36, 48, 60, 72, 84, 96, 120, 140, 160, 180, 200, 240, 300],
        'g': ['Morgen', 'Abend', 'Tag', 'Nacht'], 'name': ['Anna', 'Ben', 'Clara', 'David', 'Emma', 'Finn', 'Greta', 'Hugo', 'Ida', 'Jonas'], 'thing': ['Pflanzen', 'Bäume', 'Katzen', 'Kinder', 'Städte', 'Firmen', 'Vögel', 'Flüsse'],
        'need': ['Wasser', 'Licht', 'Ruhe', 'Pflege', 'Platz', 'Zeit', 'Wärme', 'Regeln']}
TEMPLATES = {
    'simple': ['Guten {g}, {name}, wie geht es dir?', 'Hallo {name}, was machst du heute am {g}?', 'Schönen {g}, {name}! Alles gut bei dir?', 'Hey {name}, wie war dein {g}?'],
    'detail': ['Wie viel sind {n} plus {n2} Euro?', 'Rechne bitte {n} mal 3 aus.', 'Wie viel ist ein Drittel von {n} Euro?', 'Was kostet {n} Euro minus 15 Prozent?'],
    'half':   ['Wie viel ist die Hälfte von {n} Euro?', 'Was ist die Hälfte von {n}?', 'Halbiere bitte {n} Euro.', 'Wie viel ergibt {n} geteilt durch zwei?'],
    'gist':   ['Was ist die Kernaussage: {thing} brauchen {need}.', 'Fasse kurz zusammen: {thing} brauchen {need}.', 'Worum geht es im Kern: {thing} und {need}?', 'Gib mir den Überblick: {thing} brauchen {need}.'],
    'both':   ['Welche Vor- und Nachteile haben {a} und {a2}?', 'Vergleiche {a} mit {a2}.', 'Was spricht für {a}, was für {a2}?', 'Wäge {a} gegen {a2} ab.']}


def make(kind, rng, used):
    for _ in range(500):
        t = rng.choice(TEMPLATES[kind]); a, a2 = rng.sample(FILL['a'], 2); n, n2 = rng.sample(FILL['n'], 2)
        s = t.format(g=rng.choice(FILL['g']), name=rng.choice(FILL['name']), n=n, n2=n2, a=a, a2=a2, thing=rng.choice(FILL['thing']), need=rng.choice(FILL['need']))
        if s not in used: used.add(s); return s
    raise RuntimeError('paraphrase space exhausted for ' + kind)


def stream(seed):
    rng = random.Random(seed); used = set()
    heldout = [(make(k, rng, used), k, k) for k in ('simple', 'detail', 'gist', 'both') for _ in range(8)]
    heldout += [(make('half', rng, used), 'detail', 'simple') for _ in range(8)]   # (text, label before shift, label after)
    record = [make(rng.choice(list(TEMPLATES)), rng, used) for _ in range(40)]
    p1 = [[(make(k if k != 'detail' else rng.choice(('detail', 'half')), rng, used), k) for k in ROUTE_NAMES for _ in range(2)] for _ in range(6)]
    p2 = [[(make('half', rng, used), 'simple') for _ in range(4)] + [(make(k, rng, used), k) for k in ROUTE_NAMES] for _ in range(4)]
    return heldout, record, p1, p2


SUPERSEDE_CMD = ':ersetze route simple hälfte,halbiere,geteilt durch zwei --notiz Hälfte-Fragen jetzt kurz'


def run_arm(installed, policy, seed):
    sup = policy.endswith('+sup') or policy.endswith('+now'); now_rule = policy.endswith('+now'); base_policy = policy.split('+')[0]  # WP-Z6c: '+sup' = the human states the new scope once
    from v13.config import initialize
    from v13.runtime import Runtime
    from v13.operator import Operator
    from v13.learning_worker import features
    import numpy as np
    heldout, record, p1, p2 = stream(seed); log = []
    with tempfile.TemporaryDirectory(prefix='v13-z6b-') as d:
        h = Path(d); initialize(h)
        for n in ('models', 'bin'): shutil.rmtree(h/n); (h/n).symlink_to(installed/n, target_is_directory=True)
        shutil.copyfile(installed/'config/models.json', h/'config/models.json'); r = Runtime(h)
        cache = {}
        def emb(text):
            if text not in cache:
                ref = r.store.source(text, 'USER'); cache[text] = r.learner.embedding(text, ref['source_id'], time.monotonic()+60)
            return cache[text]
        X = features([emb(t) for t, _, _ in heldout])
        def acc(path, shifted):
            lab = [(b if shifted else a) for _, a, b in heldout]
            if path is None:
                from v13.cognition import scaffold_route
                pred = [scaffold_route(t) for t, _, _ in heldout]
            else:
                with np.load(path, allow_pickle=False) as z: pred = [ROUTE_NAMES[i] for i in np.argmax(X@z['route_w'], axis=1)]
            ok = [p == l for p, l in zip(pred, lab)]
            per = {k: round(sum(o for o, (_, a, b) in zip(ok, heldout) if (b if shifted else a) == k and not (shifted and a != b))/max(1, sum(1 for _, a, b in heldout if (b if shifted else a) == k and not (shifted and a != b))), 4) for k in ROUTE_NAMES}
            half = [o for o, (_, a, b) in zip(ok, heldout) if a != b]
            unchanged = [o for o, (_, a, b) in zip(ok, heldout) if a == b]
            return {'all': round(sum(ok)/len(ok), 4), 'per_route': per, 'half_items': round(sum(half)/len(half), 4), 'unchanged': round(sum(unchanged)/len(unchanged), 4)}
        def active_path(): return r.learner.active()
        def runtime_routes():  # WP-Z6d: the real answer-time routing path (Runtime._route), not the head alone
            out = []
            for t, _, _ in heldout:
                e = r.store.event(r.session, t); route, info = r._route(t, e, time.monotonic()+30); out.append((route, (info or {}).get('source')))
            return out
        def runtime_acc(routes):
            ok = [p[0] == b for p, (_, a, b) in zip(routes, heldout)]
            half = [o for o, (_, a, b) in zip(ok, heldout) if a != b]; unchanged = [o for o, (_, a, b) in zip(ok, heldout) if a == b]
            return {'all': round(sum(ok)/len(ok), 4), 'half_items': round(sum(half)/len(half), 4), 'unchanged': round(sum(unchanged)/len(unchanged), 4)}
        runtime_before_rule = None
        def batch_disagreement(batch):
            p = active_path()
            if p is None: return None
            with np.load(p, allow_pickle=False) as z:
                pred = [ROUTE_NAMES[int(np.argmax(features([emb(t)])@z['route_w']))] for t, _ in batch]
            return round(sum(a != l for a, (_, l) in zip(pred, batch))/len(batch), 4)
        try:
            before = r.store.generation_id
            for t in record: r.store.event(r.session, t)       # record-only episodes: captured, no feedback, no learning call
            record_updates = r.store.one('SELECT count(*) AS n FROM updates')['n']
            corrections = 0; promos = []
            for phase, batches in (('p1', p1), ('p2', p2)):
                for bi, batch in enumerate(batches):
                    if sup and phase == 'p2' and bi == 0:
                        if now_rule: runtime_before_rule = runtime_routes()
                        Operator(r).run(SUPERSEDE_CMD + (' --sofort' if now_rule else ''))
                    dis = batch_disagreement(batch)
                    for t, lab in batch:
                        e = r.store.event(r.session, t); r.memory.feedback(e['event_id'], 'route', lab, permission='learn'); corrections += 1
                    shifted = phase == 'p2'; act_before = acc(active_path(), shifted)
                    do = base_policy == 'fixed' or (base_policy == 'adaptive' and (dis is None or dis >= .25))
                    row = {'phase': phase, 'batch': bi, 'corrections': corrections, 'disagreement_before': dis, 'shadow': do, 'active_acc_before': act_before}
                    if do and base_policy != 'none':
                        r.cfg['learning_mode'] = 'SHADOW_UPDATE'
                        try: res = r.learner.shadow(); row['shadow_result'] = res
                        except ValueError as exc: row['shadow_result'] = 'SKIPPED: ' + str(exc)[:120]
                        u = r.store.one('SELECT * FROM updates ORDER BY created DESC LIMIT 1')
                        if u and u['status'] in ('PENDING_APPROVAL', 'EVALUATED_FAIL') and u['id'] not in [x.get('update_id') for x in log]:
                            cand = acc(h/u['path'], shifted); row.update(update_id=u['id'], status=u['status'], candidate_acc=cand,
                                                                         superseded=len(json.loads(u['manifest']).get('superseded_labels', [])))
                            if u['status'] == 'PENDING_APPROVAL':
                                r.cfg['learning_mode'] = 'APPROVED_COMMIT'; Operator(r).run(':approve ' + u['id']); promos.append(u['id'])
                                row['promoted'] = active_path() is not None and r.store.generation_id != before
                        r.cfg['learning_mode'] = 'RECORD_ONLY'
                    row['active_acc_after'] = acc(active_path(), shifted); log.append(row)
                    print(json.dumps({'policy': policy, 'phase': phase, 'batch': bi, 'shadow': do, 'status': row.get('status'),
                                      'acc': row['active_acc_after']['all']}), flush=True)
            runtime = None
            if now_rule or base_policy == 'fixed':
                final_routes = runtime_routes(); runtime = {'final': runtime_acc(final_routes)}
                if now_rule:
                    rid = [x for x in __import__('v13.route_supersede', fromlist=['rules']).rules(r.store) if x.get('apply_now')][-1]['id']
                    runtime['before_rule'] = runtime_acc(runtime_before_rule)
                    Operator(r).run(':ersetze undo ' + rid); after_undo = runtime_routes()
                    half = [i for i, (_, a, b) in enumerate(heldout) if a != b]; same = [i for i in range(len(heldout)) if i not in half]
                    runtime['rule_source_on_half'] = sum(final_routes[i][1] == 'HUMAN_ROUTE_RULE' for i in half)/len(half)
                    runtime['rule_touches_other_items'] = sum(final_routes[i] != after_undo[i] for i in same)  # same head, rule on vs off
                    runtime['rule_source_after_undo'] = sum(x[1] == 'HUMAN_ROUTE_RULE' for x in after_undo)
                    runtime['after_undo'] = runtime_acc(after_undo)
            # rollback of the last promotion must restore the measured parent accuracy (L11 safety path)
            rb = None
            if promos:
                last = promos[-1]; idx = max(i for i, x in enumerate(log) if x.get('update_id') == last)
                expect = log[idx]['active_acc_before']['all']; r.store.rollback(last)
                got = acc(active_path(), log[idx]['phase'] == 'p2')['all']  # same label set as the parent measurement
                rb = {'update_id': last, 'expected_parent_acc': expect, 'after_rollback_acc': got, 'restored': abs(got-expect) < 1e-9}
            session = r.session; r.close(); r = Runtime(h)
            restart_same = r.session == session
        finally:
            r.close()
    return {'policy': policy, 'record_only_updates': record_updates, 'log': log, 'rollback': rb, 'restart_same_session': restart_same, 'runtime': runtime}


def score(arm):
    log = arm['log']; jobs = [x for x in log if x.get('update_id')]
    unnecessary = [x for x in jobs if x['candidate_acc']['all'] - x['active_acc_before']['all'] < .01]
    promoted = [x for x in jobs if x.get('promoted')]
    false_promo = [x for x in promoted if x['active_acc_after']['all'] < x['active_acc_before']['all'] - .01
                   or x['active_acc_after']['unchanged'] < x['active_acc_before']['unchanged'] - .05]
    def first(pred):
        return next((x['corrections'] for x in log if pred(x)), None)
    p1_end = [x for x in log if x['phase'] == 'p1'][-1]['active_acc_after']; final = log[-1]['active_acc_after']
    return {'shadow_jobs': len(jobs), 'unnecessary_updates': len(unnecessary), 'promotions': len(promoted), 'approval_requests': sum(x.get('status') == 'PENDING_APPROVAL' for x in jobs),
            'false_promotions': len(false_promo), 'record_only_updates': arm['record_only_updates'],
            'corrections_to_p1_acc90': first(lambda x: x['phase'] == 'p1' and x['active_acc_after']['all'] >= .9),
            'corrections_to_shift_half80': first(lambda x: x['phase'] == 'p2' and x['active_acc_after']['half_items'] >= .8),
            'p1_end_acc': p1_end['all'], 'final_acc': final['all'], 'final_half_items': final['half_items'],
            'retention_unchanged': round(final['unchanged']/max(1e-9, p1_end['unchanged']), 4) if p1_end['unchanged'] else None,
            'per_route_final': final['per_route'], 'rollback': arm['rollback'], 'restart_same_session': arm['restart_same_session'], 'runtime': arm.get('runtime')}


def criteria(s):
    f, a = s['fixed'], s['adaptive']
    c = {'C1_fewer_unnecessary_updates_30pct': f['unnecessary_updates'] > 0 and a['unnecessary_updates'] <= .7*f['unnecessary_updates'],
         'C2_final_acc_not_worse_3pt': a['final_acc'] >= f['final_acc'] - .03,
         'C3_false_promotions_le_fixed': a['false_promotions'] <= f['false_promotions'],
         'C4_rollback_restores': all(s[k]['rollback'] is not None and s[k]['rollback']['restored'] for k in ('fixed', 'adaptive')),  # Z6b run: rb was never set (bug), C4 not measured
         'C5_retention_ge_90pct': (a['retention_unchanged'] or 0) >= .9,
         'C6_record_only_no_updates': all(s[k]['record_only_updates'] == 0 for k in s)}
    return c, 'Z6B_LIFECYCLE_ADAPTIVE_PASS' if all(c.values()) else 'Z6B_LIFECYCLE_ADAPTIVE_FAIL'


def criteria_z6c(s):
    a = [s['fixed+sup'], s['adaptive+sup']]
    c = {'S1_half_items_learned_ge_80pct': all((x['final_half_items'] or 0) >= .8 for x in a),
         'S2_retention_ge_90pct': all((x['retention_unchanged'] or 0) >= .9 for x in a),
         'S3_rollback_restores': all(x['rollback'] is not None and x['rollback']['restored'] for x in a),
         'S4_no_false_promotion': all(x['false_promotions'] == 0 for x in a),
         'S5_control_without_rule_fails': (s['fixed']['final_half_items'] or 0) < .5}
    return c, 'Z6C_SUPERSEDE_PASS' if all(c.values()) else 'Z6C_SUPERSEDE_FAIL'


def criteria_z6d(s):
    a = [s['fixed+now'], s['adaptive+now']]
    c = {'D1_runtime_half_items_ge_90pct': all(x['runtime']['final']['half_items'] >= .9 for x in a),
         'D2_rule_touches_no_other_item': all(x['runtime']['rule_touches_other_items'] == 0 for x in a),
         'D3_undo_removes_rule_completely': all(x['runtime']['rule_source_after_undo'] == 0 and x['runtime']['rule_source_on_half'] == 1 for x in a),
         'D4_control_without_rule_fails': s['fixed']['runtime']['final']['half_items'] < .5}
    return c, 'Z6D_RULE_ROUTE_PASS' if all(c.values()) else 'Z6D_RULE_ROUTE_FAIL'


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument('installed'); ap.add_argument('out'); ap.add_argument('--seed', type=int, default=71)
    ap.add_argument('--policies', default='none,fixed,adaptive'); a = ap.parse_args(argv)
    from v13.common import atomic_write
    installed = Path(a.installed).expanduser().resolve(); arms = {}; scores = {}
    for p in a.policies.split(','):
        arms[p] = run_arm(installed, p, a.seed); scores[p] = score(arms[p])
    doc = {'kind': 'V13_Z6B_LIFECYCLE_BENCH', 'seed': a.seed, 'scores': scores, 'arms': arms, 'phone_measured': False,
           'prereg': 'docs/proofs/continuation-20261026/z6b-lifecycle/PREREG.md',
           'claim_limit': 'route head only (STEP5 NumPy head on Needle embeddings), generated German paraphrases, harness approves every eligible candidate'}
    if {'fixed', 'adaptive'} <= set(scores):
        doc['criteria'], doc['verdict'] = criteria(scores)
    if {'fixed+now', 'adaptive+now', 'fixed'} <= set(scores):
        doc['criteria_z6d'], doc['verdict_z6d'] = criteria_z6d(scores); doc['prereg'] = 'docs/proofs/continuation-20261026/z6d-rule-route/PREREG.md'
    if {'fixed+sup', 'adaptive+sup', 'fixed'} <= set(scores):
        doc['criteria_z6c'], doc['verdict_z6c'] = criteria_z6c(scores); doc['prereg'] = 'docs/proofs/continuation-20261026/z6c-supersede/PREREG.md'
    atomic_write(Path(a.out), json.dumps(doc, indent=1, ensure_ascii=False))
    print(json.dumps({k: doc.get(k) for k in ('verdict', 'criteria', 'scores')}, indent=1, ensure_ascii=False)); return 0


if __name__ == '__main__':
    sys.exit(main())
