"""WP-BP4: expression-aware, option-bound scorer and fixture generator for the STEP2 retest (software only, no model).

Why: the native v3 lexical scorer (GPT, 2026-10-30) gave 'MISSING' to correct C3-only outputs that wrote the arithmetic
('214 - 127 = 87'). This scorer reads the claim per option: the remainder counts if it is stated as a result next to the
option name (plain number, 'left/remain', or 'a - b = r'). A wrong result for an option is a contradiction (no credit,
counted as wrong_commit). Fixtures are generated from a seed, German or English, never leak the expected remainders.
Arms (see bp4 VORABPRUEFUNG): c3_only, one_body, two_same_weights, two_distinct_weights (the run itself is not here).
"""
import random
import re

ARMS = ('c3_only', 'one_body', 'two_same_weights', 'two_distinct_weights')
NAMES = ('Amber', 'Indigo', 'Pine', 'Slate', 'Pearl', 'Copper', 'Moss', 'Coral', 'Silver', 'Onyx', 'Ruby', 'Topaz', 'Ash', 'Birch', 'Cobalt', 'Ivory')
PROJECTS = ('Meridian', 'Boreal', 'Nimbus', 'Delta', 'Orchid', 'Prism', 'Summit', 'Fjord', 'Helix', 'Quartz')


def make_fixtures(seed, n=9, language='de'):
    rng = random.Random(seed)
    projects = rng.sample(PROJECTS, min(n, len(PROJECTS)))
    out = []
    for i in range(n):
        p = projects[i % len(projects)] + ('' if i < len(projects) else str(i))
        a, b = rng.sample(NAMES, 2)
        budget = rng.randint(150, 450)
        ca = rng.randint(budget // 2, budget - 20)
        cb = rng.randint(budget // 2, budget - 5)
        if ca == cb:
            cb -= 1
        da, db = rng.randint(1, 9), rng.randint(1, 9)
        if language == 'de':
            rule = 'Projekt %s hat ein Budget von %d Euro, lokal und ohne Cloud.' % (p, budget)
            opts = 'Option %s kostet %d Euro und dauert %d Tage. Option %s kostet %d Euro und dauert %d Tage.' % (a, ca, da, b, cb, db)
            q = 'Wie viel Budget bleibt bei Option %s und bei Option %s?' % (a, b)
        else:
            rule = 'Project %s has a budget of %d euros, local and without cloud.' % (p, budget)
            opts = 'Option %s costs %d euros and takes %d days. Option %s costs %d euros and takes %d days.' % (a, ca, da, b, cb, db)
            q = 'How much budget is left with option %s and with option %s?' % (a, b)
        out.append({'id': 'bp4-%d-%d' % (seed, i), 'project': p, 'rule': rule, 'options': opts, 'question': q,
                    'expected': {a: budget - ca, b: budget - cb}, 'budget': budget, 'costs': {a: ca, b: cb}})
    return out


def _num(v):
    return r'(?<![\d.,])' + str(v) + r'(?![\d])'


def score_option(answer, name, expected, budget, cost):
    """-> 'ok' | 'wrong' | 'missing'. The window around the option name (up to the next option name or sentence end) decides."""
    text = answer or ''
    for m in re.finditer(r'\b' + re.escape(name) + r'\b', text):
        seg = text[m.end():m.end() + 90]
        seg = re.split(r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])|\bOption\b|\boption\b', seg)[0]
        # arithmetic claim 'budget - cost = r'
        am = re.search(r'(\d+)\s*[-−–]\s*(\d+)\s*=\s*(\d+)', seg)
        if am:
            return 'ok' if int(am.group(3)) == expected and int(am.group(1)) == budget and int(am.group(2)) == cost else 'wrong'
        nums = [int(x) for x in re.findall(r'(?<![\d.,])\d+(?![\d])', seg)]
        if re.search(_num(expected), seg) and re.search(r'left|remain|over|bleibt|verbleib|übrig|rest|noch', seg, re.I):
            return 'ok'
        if nums and re.search(r'left|remain|bleibt|verbleib|übrig|rest', seg, re.I) and expected not in nums:
            return 'wrong'
    return 'missing'


def score(fixture, answer):
    res = {n: score_option(answer, n, v, fixture['budget'], fixture['costs'][n]) for n, v in fixture['expected'].items()}
    return {'per_option': res, 'ok': sum(v == 'ok' for v in res.values()), 'wrong_commit': sum(v == 'wrong' for v in res.values()), 'max': len(res)}


def summarize(fixtures, answers):
    sc = [score(f, a) for f, a in zip(fixtures, answers)]
    return {'ok': sum(s['ok'] for s in sc), 'wrong_commit': sum(s['wrong_commit'] for s in sc), 'max': sum(s['max'] for s in sc)}


def verdict(per_arm, margin=3):
    """Preregistered rule: success only if two_distinct_weights beats two_same_weights by >= margin option-points (of max)
    and has no more wrong commits; otherwise STEP2 stays a one-body finding."""
    d, s = per_arm['two_distinct_weights'], per_arm['two_same_weights']
    if d['ok'] - s['ok'] >= margin and d['wrong_commit'] <= s['wrong_commit']:
        return 'DISTINCT_BODIES_SUPPORTED'
    if s['ok'] - per_arm['one_body']['ok'] >= margin:
        return 'COMBINATION_ONLY'
    return 'NO_GAIN'
