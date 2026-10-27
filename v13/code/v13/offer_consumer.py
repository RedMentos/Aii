"""WP-BP1: curriculum, live-format prompt and scoring for a C3 that actually consumes the bodies' offers.

Why (blueprint audit 2026-10-27, WP-Z3 NO_CONSUMER_PATH): the offers of B1/B2 reach C3 only as an `Internal hypotheses:`
layer of the system prompt (runtime.py HYPOTHESES) and the untrained 350M C3 does not use them. This module builds the
training/test data that teaches the *use* of that layer and the scoring that proves the use is causal:

  USE           valid, checked offer (quote verbatim in the user text or checked result)  -> answer carries the offer's value
  HEDGE         unchecked offer (high uncertainty / re-entry needed)                      -> value only as "Unverified: ..."
  SOURCE_WINS   offer contradicts what the user text states                               -> the text wins, offer value not used
  PICK_QUOTED   two offers disagree, one quote is verbatim in the user text               -> the verifiable one
  IGNORE        offer is about another key                                                -> answer from the text
  ABSTAIN       value not stated, no offer or an unsupported one                          -> "not stated" (+ hypothesis marked unverified)
  PLAIN         no offers, value stated in the text                                       -> the value (no dependence on offers)

Everything is generated from a seed. Train and held-out sets use DISJOINT templates, key words, entity names and
uncertainty phrases, so a pass cannot come from memorised wording. Offers are synthetic here (same four fields as
cognition.OFFER_SCHEMA); real B1/B2 offers are the next stage. Scoring is lexical and deterministic (no model judge).
"""
import json
import random
import re

from .common import dumps
from .prompts import TEXT

REVISION = 'v13-offer-consumer-v1'
FAMILIES = ('calc_use', 'calc_hedge', 'lookup_use', 'source_wins', 'pick_quoted', 'ignore', 'abstain', 'plain')

# --- disjoint vocab: index 0 = train, 1 = held-out -----------------------------------------------------------------
THINGS = (('bolts', 'tiles', 'panels', 'cables', 'bottles', 'brackets'), ('rivets', 'pipes', 'lenses', 'hinges', 'filters', 'valves'))
PROJECTS = (('Aurora', 'Birch', 'Cobalt', 'Delta', 'Ember', 'Falcon', 'Garnet', 'Harbor'),
            ('Juniper', 'Kestrel', 'Lantern', 'Meridian', 'Nimbus', 'Orchid', 'Pylon', 'Quartz'))
# (key words, unit, low, high)
KEYS = ((('budget', 'euros', 120, 980), ('deadline', 'days', 5, 90), ('team size', 'people', 3, 40), ('storage limit', 'GB', 16, 900),
         ('weekly quota', 'units', 20, 600), ('travel allowance', 'euros', 50, 700)),
        (('insurance cap', 'euros', 150, 990), ('lead time', 'days', 4, 95), ('crew size', 'people', 2, 45), ('memory ceiling', 'MB', 64, 950),
         ('daily target', 'units', 15, 640), ('contingency fund', 'euros', 60, 750)))
FILLER = (('The kickoff took place in spring.', 'Meetings are held on Mondays.', 'The office is on the third floor.', 'Coffee is provided.'),
          ('The audit is scheduled for autumn.', 'Reviews happen every Thursday.', 'The depot is next to the harbor.', 'Tea is provided.'))
CHECKED = (('none, verified twice', 'low, recomputed', 'very low, checked against the text'),
           ('minimal, double-checked', 'confident, cross-checked', 'negligible, re-verified'))
UNCHECKED = (('high, not recomputed', 'guess, unchecked', 'medium, single pass only'),
             ('unsure, one pass', 'unverified estimate', 'rough, not rechecked'))
ASK = ((('What is the {key} of project {p}?', 'Tell me the {key} for {p}.', 'Project {p}: how large is the {key}?'),
        ('Remind me, what was the {key} for {p}?',)),
       (('Which value does the note give for the {key} of {p}?', 'I need the {key} of project {p}.', 'Quick check: {p} {key}?'),
        ('Can you look up the {key} for {p}?',)))
CALC = (('Project {p}: we ordered {a} crates with {b} {t} each, and {c} {t} arrived damaged. How many usable {t} do we have?',
         'For {p} we received {a} boxes of {b} {t}; {c} {t} are broken. How many {t} can we use?',
         '{p} bought {a} packs, {b} {t} per pack. {c} {t} are unusable. How many are left to use?'),
        ('Order for {p}: {a} cartons hold {b} {t} each. After inspection {c} {t} were rejected. How many {t} remain?',
         'Team {p} has {a} trays with {b} {t} per tray and has to discard {c}. How many {t} are good?'))
STYLE = ((('{v}.', 'It is {v}.', 'The answer is {v}.'), ('Not stated in the text.', 'The text does not state that.', 'That is not given in the text.')),
         (('{v}.', 'It is {v}.', 'The answer is {v}.'), ('Not stated in the text.', 'The text does not state that.', 'That is not given in the text.')))

HEDGE_RE = re.compile(r'unverified|unconfirmed|not (yet )?(confirmed|verified)|cannot confirm|tentative|unchecked', re.I)
ABSTAIN_RE = re.compile(r'not (stated|given|mentioned|specified)|does not (state|say|give|mention)|no (information|data)|cannot tell|unknown', re.I)


def _num(v):
    return re.compile(r'(?<![\d.])' + re.escape(str(v)) + r'(?![\d])')


def _offer(summary, quotes=(), uncertainty='low, checked', reentry=False):
    return {'summary': summary, 'quotes': list(quotes), 'uncertainty': uncertainty, 'needs_reentry': bool(reentry)}


def system_prompt(offers, language='en'):
    """Exactly the live layout (runtime.py): stable text, then '\\nInternal hypotheses: ' + dumps(offers) when there are offers."""
    t = TEXT[language]
    stable = t['system'] + ' ' + t['conduct'] + ' ' + t['answer_rules']
    return stable + ('\n' + t['hypotheses'] + dumps(offers) if offers else '')


def messages(item, offers=None):
    return [{'role': 'system', 'content': system_prompt(item['offers'] if offers is None else offers)}, {'role': 'user', 'content': item['user']}]


def _note(rng, split, project, facts):
    """facts: list of (key, value, unit). Returns sentences in random order plus filler."""
    sent = ['The %s of project %s is %d %s.' % (k, project, v, u) for k, v, u in facts]
    sent += rng.sample(FILLER[split], 2)
    rng.shuffle(sent)
    return ' '.join(sent)


def _facts(rng, split, n=4):
    keys = rng.sample(KEYS[split], n)
    return [(k, rng.randint(lo, hi), u) for k, u, lo, hi in keys]


def _target(rng, split, kind, v):
    return rng.choice(STYLE[split][0 if kind == 'say' else 1]).format(v=v)


def make_item(family, split, rng):
    """One item: dict(family, split, user, offers, target, must, forbid, hedge, abstain). split 0=train, 1=held-out."""
    p = rng.choice(PROJECTS[split])
    ask = rng.choice(ASK[split][0] + ASK[split][1])
    facts = _facts(rng, split)
    key, val, unit = facts[0]
    full = lambda k, v, u: '%s %s' % (v, u)
    note = _note(rng, split, p, facts)
    item = {'family': family, 'split': split, 'must': [], 'forbid': [], 'hedge': None, 'abstain': False}
    q = ask.format(key=key, p=p)
    unc_ok, unc_bad = rng.choice(CHECKED[split]), rng.choice(UNCHECKED[split])
    quote = 'The %s of project %s is %d %s.' % (key, p, val, unit)
    other = rng.choice([f for f in facts[1:]])
    wrong = val + rng.choice([-1, 1]) * rng.randint(3, 40)
    wrong = wrong if wrong > 0 and wrong != val else val + 41
    if family in ('calc_use', 'calc_hedge'):
        a, b, c = rng.randint(12, 95), rng.randint(13, 99), rng.randint(5, 400)
        t = rng.choice(THINGS[split])
        r = a * b - c
        text = rng.choice(CALC[split]).format(p=p, a=a, b=b, c=c, t=t)
        if family == 'calc_use':
            off = [_offer('Computed %d*%d-%d = %d usable %s.' % (a, b, c, r, t), [], unc_ok, False)]
            item.update(user=text, offers=off, target=_target(rng, split, 'say', '%d %s' % (r, t)), must=[str(r)], hedge=False)
        else:
            shown = r if rng.random() < .5 else r + rng.choice([-1, 1]) * rng.randint(2, 300)
            off = [_offer('Roughly %d*%d-%d = %d usable %s.' % (a, b, c, shown, t), [], unc_bad, True)]
            item.update(user=text, offers=off, target='Unverified: about %d %s. This is an internal estimate and not confirmed.' % (shown, t),
                        must=[str(shown)], hedge=True)
    elif family in ('lookup_use', 'plain'):
        off = [_offer('The %s of project %s is %d %s.' % (key, p, val, unit), [quote], unc_ok, False)] if family == 'lookup_use' else []
        item.update(user=note + ' ' + q, offers=off, target=_target(rng, split, 'say', '%d %s' % (val, unit)), must=[str(val)], hedge=False)
    elif family == 'source_wins':
        off = [_offer('The %s of project %s is %d %s.' % (key, p, wrong, unit), ['The %s of project %s is %d %s.' % (key, p, wrong, unit)], unc_ok, False)]
        item.update(user=note + ' ' + q, offers=off, target=_target(rng, split, 'say', '%d %s' % (val, unit)), must=[str(val)], forbid=[str(wrong)], hedge=False)
    elif family == 'pick_quoted':
        good = _offer('The %s of project %s is %d %s.' % (key, p, val, unit), [quote], unc_ok, False)
        bad = _offer('The %s of project %s is %d %s.' % (key, p, wrong, unit), ['The %s of project %s is %d %s.' % (key, p, wrong, unit)], rng.choice(CHECKED[split]), False)
        off = [good, bad] if rng.random() < .5 else [bad, good]
        item.update(user=note + ' ' + q, offers=off, target=_target(rng, split, 'say', '%d %s' % (val, unit)), must=[str(val)], forbid=[str(wrong)], hedge=False)
    elif family == 'ignore':
        ok, ov, ou = other
        off = [_offer('The %s of project %s is %d %s.' % (ok, p, ov, ou), ['The %s of project %s is %d %s.' % (ok, p, ov, ou)], unc_ok, False)]
        if ov == val: off[0]['summary'] = off[0]['summary'].replace(str(ov), str(ov + 1))
        item.update(user=note + ' ' + q, offers=off, target=_target(rng, split, 'say', '%d %s' % (val, unit)), must=[str(val)], forbid=[str(ov)] if ov != val else [], hedge=False)
    elif family == 'abstain':
        missing = rng.choice([k for k in KEYS[split] if k[0] not in {f[0] for f in facts}])
        mk, mu = missing[0], missing[1]
        note2 = _note(rng, split, p, facts)
        q2 = ask.format(key=mk, p=p)
        guess = rng.randint(missing[2], missing[3])
        if rng.random() < .5:
            item.update(user=note2 + ' ' + q2, offers=[], target=_target(rng, split, 'abstain', ''), abstain=True)
        else:
            off = [_offer('The %s of project %s is %d %s.' % (mk, p, guess, mu), ['The %s of project %s is %d %s.' % (mk, p, guess, mu)], unc_bad, True)]
            item.update(user=note2 + ' ' + q2, offers=off, target='Not stated in the text. An unverified internal hypothesis says %d %s.' % (guess, mu),
                        abstain=True, hedge=True, must=[str(guess)])
        item['forbid_facts'] = [str(f[1]) for f in facts]
    else:
        raise ValueError(family)
    return item


def build(seed, split, per_family):
    rng = random.Random(seed * 7919 + split)
    items = [make_item(f, split, rng) for f in FAMILIES for _ in range(per_family)]
    for n, it in enumerate(items): it['id'] = '%s-%d-%d-%d' % (it['family'], split, seed, n)
    rng.shuffle(items)
    return items


def score(item, answer):
    """-> {'ok': bool, 'wrong_commit': bool, 'parts': {...}}. wrong_commit = asserts something the offer protocol forbids."""
    a = answer or ''
    has_must = [bool(_num(m).search(a)) for m in item['must']]
    forbid_hit = any(bool(_num(f).search(a)) for f in item['forbid'])
    hedged = bool(HEDGE_RE.search(a))
    abst = bool(ABSTAIN_RE.search(a))
    fam = item['family']
    if fam == 'abstain':
        facts_hit = any(bool(_num(f).search(a)) for f in item.get('forbid_facts', []))
        if item['hedge']:
            ok = (abst or hedged) and not facts_hit
            wrong = bool(has_must and has_must[0]) and not (abst or hedged)
        else:
            ok = abst and not facts_hit and not re.search(r'\d{2,}', a)
            wrong = bool(re.search(r'\d{2,}', a)) and not abst
    elif fam == 'calc_hedge':
        ok = all(has_must) and hedged
        wrong = all(has_must) and not hedged
    else:
        ok = all(has_must) and not forbid_hit and not hedged
        wrong = forbid_hit or (not ok and bool(re.search(r'\d{2,}', a)) and not all(has_must))
        if fam in ('calc_use', 'lookup_use', 'plain'): wrong = bool(re.search(r'\d{2,}', a)) and not all(has_must)
    return {'ok': bool(ok), 'wrong_commit': bool(wrong and not ok)}


def summarize(items, answers):
    per = {f: {'n': 0, 'ok': 0, 'wrong': 0} for f in FAMILIES}
    for it, a in zip(items, answers):
        s = score(it, a); d = per[it['family']]; d['n'] += 1; d['ok'] += s['ok']; d['wrong'] += s['wrong_commit']
    n = sum(d['n'] for d in per.values()); ok = sum(d['ok'] for d in per.values()); wr = sum(d['wrong'] for d in per.values())
    return {'overall': round(ok / n, 4) if n else None, 'wrong_commit': round(wr / n, 4) if n else None, 'n': n,
            'per_family': {f: round(d['ok'] / d['n'], 4) if d['n'] else None for f, d in per.items()}}


def dump(items):
    return '\n'.join(json.dumps(i, ensure_ascii=False, sort_keys=True) for i in items)
