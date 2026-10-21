#!/usr/bin/env python3
"""WP-Z3c: extensible rule parser (parser_v2) vs. anchored parser (parser_v1) on fresh reworded rules.

Cohorts (PREREG.md): dev = Z3b canonical + Z3b paraphrase; holdout_author = sealed holdout_author.json
(committed before any parser code); holdout_model = B1 rewrites generated only after the parser was frozen
(freeze.json), meaning-audited before the parser saw them. Both parsers are deterministic, so one row per
fixture. Optional c3_probe: C3 classifies single locality / decoy sentences (is reading training worth it?).
Diagnostic, no gate promotion; STEP2 UTILITY_FAIL unchanged.
"""
import argparse
import copy
import importlib.util
import json
import math
from pathlib import Path
import random
import re
import shutil
import sys
import time

HERE = Path(__file__).resolve().parent
APP = HERE.parents[3]
Z3B_DIR = HERE.parent / 'z3b-parser-paraphrase'
sys.path.insert(0, str(APP))
sys.path.insert(0, str(HERE))
from v13.common import atomic_write, dumps, file_hash, digest
from v13.config import save_config
from v13.resources import device
import parser_v2 as P


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = _load('z3b_parser_vs_reader', Z3B_DIR / 'z3b_parser_vs_reader.py')
Z, G, E, A = B.Z, B.G, B.E, B.A

VERSION = 'V13_Z3C_EXTENSIBLE_PARSER_V1'
RULES = B.RULES
COHORTS = ['dev_canonical', 'dev_paraphrase', 'holdout_author', 'holdout_model']
ARMS = ['parser_v1', 'parser_v2']
CONTROL_KINDS = ('missing_rule', 'contradictory_rule', 'decoy_missing')
HOLDOUT_AUTHOR = HERE / 'holdout_author.json'
HOLDOUT_AUTHOR_SHA = 'f8136999ba7c6dc1e30920234b2594f9a502fba397edbb9d5b9b2e06e0f34ba4'
FREEZE = HERE / 'freeze.json'
MODEL_RAW = HERE / 'holdout_model_raw.json'
MODEL_AUDIT = HERE / 'holdout_model_audit.json'
GEN_PROMPT = ('Rewrite this project rule in different words. Keep the meaning and keep every number exactly. '
              'Answer with one sentence.')
GEN_SYSTEM = 'You rewrite one sentence and return the required JSON only.'
GEN_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['sentence'],
              'properties': {'sentence': {'type': 'string', 'minLength': 3, 'maxLength': 240}}}
GEN_SEED, GEN_TEMPERATURE, GEN_ATTEMPTS, GEN_MAX_WORDS = 20261023, 0.7, 3, 30
MIN_MODEL_FIXTURES = 30
PROBE_SEEDS = [13, 14, 15]
PROBE_SYSTEM = ('You read one project rule sentence and return the required JSON only. local_only is true if the '
                'sentence says that only local options are allowed or that the chosen option must be local; false if '
                'it says that non-local or remote options are allowed or that locality does not matter; null if the '
                'sentence does not settle the question.')
PROBE_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['local_only'],
                'properties': {'local_only': {'type': ['boolean', 'null']}}}


# ---------------------------------------------------------------- cohorts

def base_fixtures():
    return [f for f in B.cohorts() if f['cohort'] == 'canonical']


def clauses_of(text):
    """Canonical private source -> (project sentence, [(rule, raw value string)])."""
    m = re.fullmatch(r'Project (\w+)\.((?: [^.]+\.)*)', text)
    if not m:
        raise ValueError('Unexpected canonical source form')
    out = []
    for clause in re.findall(r' ([^.]+\.)', m.group(2)):
        for rule, pattern in G.PATTERNS.items():
            hit = pattern.fullmatch(clause)
            if hit:
                out.append((rule, hit.group(1), clause))
                break
        else:
            raise ValueError('Unknown rule clause: ' + clause)
    return 'Project ' + m.group(1) + '.', out


def _key(rule, value):
    return rule if rule != 'local_only' else 'local_' + value


def reword_author(fixture, holdout, rng, drop=None, extra=None):
    """Reword every rule clause with the sealed author templates.

    drop  (rule, decoy)   the clause of this rule is replaced by the decoy sentence (rule becomes missing)
    extra (rule, decoy)   the decoy sentence is appended to the source holding this rule (rule unchanged)
    """
    used, sources = {}, []

    def pick(key, table):
        choices = [i for i in range(len(table[key])) if i not in used.get(key, set())] or list(range(len(table[key])))
        i = rng.choice(choices)
        used.setdefault(key, set()).add(i)
        return table[key][i]

    for s in fixture['sources']:
        head, cl = clauses_of(s['text'])
        out, i = [head], 0
        while i < len(cl):
            rule, value, _ = cl[i]
            if drop and drop[0] == rule:
                out.append(drop[1])
                i += 1
                continue
            nxt = cl[i + 1] if i + 1 < len(cl) else None
            if (rule == 'deadline' and nxt and nxt[0] == 'local_only' and not (drop and drop[0] == 'local_only')
                    and rng.random() < holdout['combined_rate']):
                out.append(pick('deadline_local_' + nxt[1], holdout['combined']).format(d=value))
                i += 2
                continue
            out.append(pick(_key(rule, value), holdout['templates']).format(v=value))
            i += 1
        if extra and any(r == extra[0] for r, _, _ in cl):
            out.append(extra[1])
            extra = None
        sources.append(G.source(s['owner'], ' '.join(out)))
    return sources


def _derived(f, suffix, cohort, kind, sources, truth):
    p = copy.deepcopy(f)
    for key in ('visibility_proof', 'paired_actions'):
        p.pop(key, None)
    p.update(id=f['id'] + suffix, cohort=cohort, kind=kind, sources=sources, truth_rules=truth, canonical_id=f['id'])
    p['oracle'] = B.oracle_from_truth(p)
    return p


def holdout_author_cohort():
    if file_hash(HOLDOUT_AUTHOR) != HOLDOUT_AUTHOR_SHA:
        raise ValueError('Sealed author holdout changed')
    H = json.loads(HOLDOUT_AUTHOR.read_text())
    rng = random.Random(H['seed'])
    base = base_fixtures()
    out = []
    for f in base:
        p = _derived(f, '_ha', 'holdout_author', f['kind'], reword_author(f, H, rng), f['truth_rules'])
        if p['oracle'] != f['oracle']:
            raise ValueError('Author rewording changed the oracle')
        out.append(p)
    comp = [f for f in base if f['kind'] == 'complementary']
    for i, f in enumerate(comp[:H['decoy_missing_fixtures']]):
        rule = RULES[i % 3]
        decoy = H['decoys'][rule][(i // 3) % 4].format(x=_decoy_number(f, rule))
        truth = dict(f['truth_rules'], **{rule: None})
        out.append(_derived(f, '_hdm', 'holdout_author', 'decoy_missing',
                            reword_author(f, H, rng, drop=(rule, decoy)), truth))
    start = H['decoy_missing_fixtures']
    for i, f in enumerate(comp[start:start + H['decoy_extra_fixtures']]):
        rule = RULES[i % 3]
        decoy = H['decoys'][rule][(i // 3 + 1) % 4].format(x=_decoy_number(f, rule))
        p = _derived(f, '_hdx', 'holdout_author', 'decoy_extra', reword_author(f, H, rng, extra=(rule, decoy)),
                     f['truth_rules'])
        if p['oracle'] != f['oracle']:
            raise ValueError('Extra decoy changed the oracle')
        out.append(p)
    return out


def _decoy_number(f, rule):
    taken = B.numbers([s['text'] for s in f['sources']])
    x = (f['truth_rules'].get(rule) if rule != 'local_only' else 0) or 0
    x += 9 if rule == 'budget' else 5
    while x in taken:
        x += 1
    return x


# ---------------------------------------------------------------- model holdout (after freeze)

def model_clauses():
    """Every rule clause of the base fixtures, in a fixed order: (key, rule, value, canonical clause)."""
    out = []
    for f in base_fixtures():
        for si, s in enumerate(f['sources']):
            for ci, (rule, value, clause) in enumerate(clauses_of(s['text'])[1]):
                out.append({'key': f'{f["id"]}/{si}/{ci}', 'rule': rule, 'value': value, 'clause': clause})
    return out


def number_multiset(text):
    return sorted(int(t) for t in P.tokens(text) if t.isdigit())


def generation_filter(original, sentence):
    reasons = []
    if number_multiset(sentence) != number_multiset(original):
        reasons.append('numbers_changed')
    if any(G.facts([sentence]).values()) or any(E.stated_values(r, sentence) for r in RULES):
        reasons.append('canonical_form')
    if len(P.sentences(sentence)) != 1:
        reasons.append('not_one_sentence')
    if len(sentence.split()) > GEN_MAX_WORDS:
        reasons.append('too_long')
    return reasons


def check_freeze():
    freeze = json.loads(FREEZE.read_text())
    now = {'parser_v2.py': file_hash(HERE / 'parser_v2.py'), 'lexicon.json': file_hash(P.LEXICON_PATH)}
    if freeze['files'] != now:
        raise ValueError('Parser or lexicon changed after freeze')
    return freeze


def _warm_call(runtime, role, messages, seconds, tokens, schema, seed, transcript):
    entry = {'role': role, 'messages': copy.deepcopy(messages), 'seed': seed, 'raw': '', 'status': 'RUNNING'}
    transcript.append(entry)
    runner = runtime.pool.get(role)
    for chunk in runner.generate(messages, runtime.cancel_event, time.monotonic() + seconds, tokens, schema, seed=seed):
        entry['raw'] += chunk
    entry['metrics'] = {k: runner.last_metrics.get(k) for k in ('status', 'actual_model', 'duration_s')}
    if entry['metrics'].get('status') != 'FINAL':
        raise ValueError('Runner did not finish FINAL')
    entry['status'] = 'FINAL'
    return entry['raw']


def generate_model(installed, out):
    """B1 rewrites every base rule clause (only after freeze). Writes holdout_model_raw.json."""
    freeze = check_freeze()
    home = Path(out)
    runtime = Z.prepare_home(home, Path(installed), GEN_SEED)
    save_config(home, A.CONFIG | {'seed': GEN_SEED, 'temperature': GEN_TEMPERATURE})
    runtime.close()
    runtime = Z.Runtime(home)
    cache, items = {}, []
    try:
        for c in model_clauses():
            if c['clause'] not in cache:
                attempts = []
                for attempt in range(GEN_ATTEMPTS):
                    user = GEN_PROMPT + '\nRule: ' + c['clause']
                    messages = [{'role': 'system', 'content': GEN_SYSTEM}, {'role': 'user', 'content': user}]
                    transcript = []
                    try:
                        raw = _warm_call(runtime, 'B1_DETAIL', messages, 60, 96, GEN_SCHEMA, GEN_SEED + attempt, transcript)
                        sentence = A.strict_json(raw)['sentence'].strip()
                        reasons = generation_filter(c['clause'], sentence)
                    except Exception as exc:
                        sentence, reasons = None, ['error:' + type(exc).__name__]
                    attempts.append({'attempt': attempt, 'sentence': sentence, 'rejected': reasons})
                    if not reasons:
                        break
                cache[c['clause']] = attempts
            attempts = cache[c['clause']]
            accepted = next((a['sentence'] for a in attempts if not a['rejected']), None)
            items.append(c | {'attempts': attempts, 'accepted': accepted})
    finally:
        runtime.close()
        shutil.rmtree(home, ignore_errors=True)
    raw = {'schema': VERSION + '_MODEL_RAW', 'freeze_sha256': digest(dumps(freeze)), 'prompt': GEN_PROMPT,
           'system': GEN_SYSTEM, 'seed': GEN_SEED, 'temperature': GEN_TEMPERATURE, 'attempts': GEN_ATTEMPTS,
           'role': 'B1_DETAIL', 'device': device(), 'items': items}
    atomic_write(MODEL_RAW, dumps(raw))
    return raw


def holdout_model_cohort():
    """Fixtures whose every clause has an accepted, audited-'same' rewrite; exclusions counted."""
    raw = json.loads(MODEL_RAW.read_text())
    audit = json.loads(MODEL_AUDIT.read_text())
    if audit['raw_sha256'] != file_hash(MODEL_RAW):
        raise ValueError('Audit does not belong to this generation')
    labels = audit['labels']
    by_key = {i['key']: i for i in raw['items']}
    out, excluded = [], []
    for f in base_fixtures():
        sources, reason = [], None
        for si, s in enumerate(f['sources']):
            head, cl = clauses_of(s['text'])
            parts = [head]
            for ci in range(len(cl)):
                item = by_key[f'{f["id"]}/{si}/{ci}']
                if item['accepted'] is None:
                    reason = reason or 'filter_failed'
                    continue
                label = labels.get(item['accepted'], {}).get('label')
                if label != 'same':
                    reason = reason or ('audit_' + str(label))
                parts.append(item['accepted'])
            sources.append(G.source(s['owner'], ' '.join(parts)))
        if reason:
            excluded.append({'fixture': f['id'], 'reason': reason})
            continue
        out.append(_derived(f, '_hm', 'holdout_model', f['kind'], sources, f['truth_rules']))
    return out, excluded


def all_cohorts(with_model=True):
    z3b = B.cohorts()
    out = [dict(f, cohort='dev_canonical') for f in z3b if f['cohort'] == 'canonical']
    out += [dict(f, cohort='dev_paraphrase') for f in z3b if f['cohort'] == 'paraphrase']
    out += holdout_author_cohort()
    excluded = []
    if with_model:
        model, excluded = holdout_model_cohort()
        out += model
    return out, excluded


# ---------------------------------------------------------------- arms

def decide_v2(fixture, lexicon=None):
    current = G.render_current(fixture['public'])
    texts = [s['text'] for s in fixture['sources']]
    parsed = P.parse([current, *texts], lexicon)
    rules = P.usable(parsed['rules'])
    options = Z.parse_options(current)
    rejected = [r + ':' + str(v) for r, v in parsed['rules'].items() if v in (P.CONFLICT, P.UNREADABLE)]
    if not all(E.option_stated(o, [current]) for o in options):
        rules, rejected = {r: None for r in RULES}, rejected + ['option_not_stated']
    action, out = E.recipe(rules['budget'], rules['deadline'], rules['local_only'], options)
    return {'action': action, 'options': out, 'rejected': rejected, 'rules_read': parsed['rules'],
            'trace': parsed['trace'], 'revision': 'z3c-parser-v2'}


def rows_for(fixture, lexicon=None):
    v1 = B.parser_row(fixture, 0)
    v1_read = B.parser_rules([G.render_current(fixture['public']), *[s['text'] for s in fixture['sources']]])
    result = decide_v2(fixture, lexicon)
    raw = Z.tool_answer(fixture['public']['project'], result)
    base = {'fixture': fixture['id'], 'kind': fixture['kind'], 'cohort': fixture['cohort']}
    truth = fixture['truth_rules']
    return [base | {'arm': 'parser_v1', 'rules_read': v1_read, 'read_ok': _read_ok(v1_read, truth),
                    'answer_action': v1['answer_action'], 'decision_exact': v1['decision_exact'],
                    'wrong_commit': v1['wrong_commit'], 'action_correct': v1['action_correct']},
            base | {'arm': 'parser_v2', 'rules_read': result['rules_read'], 'read_ok': _read_ok(result['rules_read'], truth),
                    'trace': result['trace']}
            | {k: v for k, v in B.summarize_answer(raw, fixture['oracle']).items() if k != 'score'}]


def _read_ok(read, truth):
    """CONFLICT truth: CONFLICT or refusal is right; missing truth: None or refusal is right."""
    out = {}
    for r in RULES:
        got, want = read.get(r), truth[r]
        if want in (None, B.CONFLICT):
            out[r] = got in (None, B.CONFLICT, P.UNREADABLE)
        else:
            out[r] = type(got) is type(want) and got == want
    return out


# ---------------------------------------------------------------- summary and verdict

def wilson(k, n, z=1.96):
    if not n:
        return [0., 0.]
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0., centre - half), min(1., centre + half)]


def arm_stats(rs):
    n = len(rs)
    k_exact, k_wrong = sum(r['decision_exact'] for r in rs), sum(r['wrong_commit'] for r in rs)
    controls = [r for r in rs if r['kind'] in CONTROL_KINDS]
    return {'n': n, 'decision_exact': k_exact / n if n else 0., 'decision_exact_ci95': wilson(k_exact, n),
            'wrong_commit': k_wrong / n if n else 0., 'wrong_commit_ci95': wilson(k_wrong, n),
            'wrong_commit_count': k_wrong, 'exact_count': k_exact,
            'unknown_controls_correct': (sum(r['action_correct'] for r in controls) / len(controls)) if controls else None,
            'n_controls': len(controls),
            'read_ok': {rule: sum(r['read_ok'][rule] for r in rs) / n if n else 0. for rule in RULES},
            'by_kind': {k: {'n': len(g), 'exact': sum(r['decision_exact'] for r in g),
                            'wrong': sum(r['wrong_commit'] for r in g)}
                        for k in sorted({r['kind'] for r in rs}) for g in [[r for r in rs if r['kind'] == k]]}}


def summarize(rows, excluded=(), probe=None):
    stats = {c: {a: arm_stats([r for r in rows if r['cohort'] == c and r['arm'] == a]) for a in ARMS} for c in COHORTS}
    v2 = {c: stats[c]['parser_v2'] for c in COHORTS}

    def carries(c):
        return v2[c]['n'] > 0 and v2[c]['decision_exact'] >= .8 and v2[c]['wrong_commit'] <= .05

    model_ok = v2['holdout_model']['n'] >= MIN_MODEL_FIXTURES
    if v2['dev_canonical']['exact_count'] != v2['dev_canonical']['n'] or v2['dev_canonical']['wrong_commit_count']:
        verdict = 'PARSER_V2_REGRESSION'
    elif any(v2[c]['wrong_commit'] > .05 for c in COHORTS if v2[c]['n']):
        verdict = 'PARSER_V2_UNSAFE'
    elif carries('holdout_author') and model_ok and carries('holdout_model'):
        verdict = 'PARSER_V2_CARRIES'
    elif carries('holdout_author'):
        verdict = 'PARSER_V2_CARRIES_AUTHOR_ONLY'
    else:
        verdict = 'PARSER_V2_SAFE_NOT_SUFFICIENT'
    if probe is None:
        secondary = 'C3_TRAINING_NOT_ASSESSED'
    elif verdict != 'PARSER_V2_CARRIES' and probe['local_correct'] >= .5 and probe['decoy_null'] >= .5:
        secondary = 'C3_TRAINING_WORTH_A_PACKAGE'
    else:
        secondary = 'C3_TRAINING_NOT_NOW'
    return {'cohorts': stats, 'holdout_model_excluded': list(excluded), 'holdout_model_underpowered': not model_ok,
            'carries': {c: carries(c) for c in COHORTS}, 'verdict': verdict, 'secondary': secondary,
            'c3_probe': probe, 'gate_promotion': False, 'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED'}


# ---------------------------------------------------------------- C3 sentence probe (optional)

def probe_items():
    H = json.loads(HOLDOUT_AUTHOR.read_text())
    items = [{'sentence': s, 'want': True, 'kind': 'local'} for s in H['templates']['local_true']]
    items += [{'sentence': s, 'want': False, 'kind': 'local'} for s in H['templates']['local_false']]
    items += [{'sentence': s, 'want': None, 'kind': 'decoy'} for s in H['decoys']['local_only']]
    return items


def run_probe(installed, out):
    out = Path(out)
    rows = []
    for seed in PROBE_SEEDS:
        runtime = Z.prepare_home(out / f'home_s{seed}', Path(installed), seed)
        try:
            for item in probe_items():
                messages = [{'role': 'system', 'content': PROBE_SYSTEM},
                            {'role': 'user', 'content': json.dumps({'sentence': item['sentence']})}]
                calls = []
                try:
                    raw = Z.call(runtime, 'C3_LANGUAGE', messages, time.monotonic() + 60, 32, PROBE_SCHEMA, seed, calls)
                    got = A.strict_json(raw)['local_only']
                    status = 'RECORDED'
                except Exception as exc:
                    got, status = 'ERROR:' + type(exc).__name__, 'ERROR'
                rows.append(item | {'seed': seed, 'got': got, 'status': status,
                                    'correct': status == 'RECORDED' and type(got) is type(item['want']) and got == item['want']})
        finally:
            runtime.close()
        shutil.rmtree(out / f'home_s{seed}', ignore_errors=True)
    local = [r for r in rows if r['kind'] == 'local']
    decoy = [r for r in rows if r['kind'] == 'decoy']
    lexicon = P.load_lexicon()
    parser_local = [P.read_local(P.tokens(i['sentence']), P.match(P.tokens(i['sentence']), P._phrases(lexicon, 'local')))
                    for i in probe_items()]
    summary = {'n_calls': len(rows), 'errors': sum(r['status'] != 'RECORDED' for r in rows),
               'local_correct': sum(r['correct'] for r in local) / len(local),
               'decoy_null': sum(r['got'] is None for r in decoy) / len(decoy),
               'answers': {str(k): sum(1 for r in rows if r['got'] == k and type(r['got']) is type(k))
                           for k in (True, False, None)},
               'parser_v2_sentence_level_note': 'parser read of the bare sentence, decoys not hedge-filtered here',
               'parser_v2_local_correct': sum(v == i['want'] and type(v) is type(i['want'])
                                              for v, i in zip(parser_local, probe_items()) if i['kind'] == 'local')
               / sum(i['kind'] == 'local' for i in probe_items())}
    atomic_write(out / 'probe_rows.json', dumps(rows))
    atomic_write(out / 'probe_summary.json', dumps(summary))
    return summary


# ---------------------------------------------------------------- main

def run(out, probe_path=None):
    freeze = check_freeze()
    fixtures, excluded = all_cohorts(with_model=True)
    lexicon = P.load_lexicon()
    rows = [r for f in fixtures for r in rows_for(f, lexicon)]
    probe = json.loads(Path(probe_path).read_text()) if probe_path else None
    report = {'schema': VERSION + '_REPORT', 'freeze_sha256': digest(dumps(freeze)),
              'cohort_sha256': digest(dumps(fixtures)), 'fixtures': len(fixtures), 'rows': len(rows),
              'device': device(), 'phone_measured': device()['android'], 'summary': summarize(rows, excluded, probe),
              'gate_promotion': False}
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    atomic_write(out / 'rows.json', dumps(rows))
    atomic_write(out / 'cohort.json', dumps(fixtures))
    report['rows_sha256'] = file_hash(out / 'rows.json')
    atomic_write(out / 'report.json', dumps(report))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('freeze')
    g = sub.add_parser('generate-model')
    g.add_argument('--installed', type=Path, required=True)
    g.add_argument('--home', type=Path, required=True)
    p = sub.add_parser('probe')
    p.add_argument('--installed', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    r = sub.add_parser('run')
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--probe', type=Path)
    args = ap.parse_args()
    if args.command == 'freeze':
        if FREEZE.exists():
            raise FileExistsError('Already frozen')
        freeze = {'schema': VERSION + '_FREEZE', 'files': {'parser_v2.py': file_hash(HERE / 'parser_v2.py'),
                                                           'lexicon.json': file_hash(P.LEXICON_PATH)},
                  'holdout_author_sha256': HOLDOUT_AUTHOR_SHA,
                  'note': 'Frozen before holdout_model generation and before any holdout run.'}
        atomic_write(FREEZE, dumps(freeze))
        print(dumps(freeze))
    elif args.command == 'generate-model':
        raw = generate_model(args.installed, args.home)
        print(dumps({'items': len(raw['items']), 'accepted': sum(i['accepted'] is not None for i in raw['items'])}))
    elif args.command == 'probe':
        print(dumps(run_probe(args.installed, args.out)))
    else:
        report = run(args.out, args.probe)
        s = report['summary']
        print(dumps({'verdict': s['verdict'], 'secondary': s['secondary'],
                     'v2': {c: [s['cohorts'][c]['parser_v2'][k] for k in ('n', 'decision_exact', 'wrong_commit')]
                            for c in COHORTS}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
