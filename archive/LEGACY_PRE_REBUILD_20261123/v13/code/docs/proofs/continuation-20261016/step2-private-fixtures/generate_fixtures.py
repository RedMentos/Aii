#!/usr/bin/env python3
"""New STEP2 fixture geometry only: complementary private evidence, no runtime or native run.

Sources, prompt builders and scoring oracles are separate. Completion witnesses
are finite-world proofs about these generated constraints, not model outcomes.
The original 10-fixture/70-row cohort and its negative gates are untouched.
"""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import re


SCHEMA = 'V13_STEP2_PRIVATE_FIXTURES_V1'
ROLES = ('B1_DETAIL', 'B2_GIST')
REQUIRED = ('budget', 'deadline', 'local_only')
DOMAINS = {'budget': list(range(161)), 'deadline': list(range(13)), 'local_only': [False, True]}
SYSTEM = (
    'Make a source-grounded project decision. Current option facts and supplied exact source quotations are evidence. '
    'Each option is eligible if cost <= budget, days <= deadline, and local if local-only is required. '
    'Choose the cheapest eligible option, choosing A on a cost tie; choose NONE if neither is eligible. '
    'Return project, action (A, B, NONE, UNKNOWN) and options with entity, cost, remaining, days, local, eligible. '
    'remaining = budget - cost even for an ineligible option. All rules are same-revision claims: '
    'if any required rule is missing or contradicts another supplied source, action must be UNKNOWN '
    'and remaining and eligible must be null for both options. Never infer a missing rule from a source identifier.'
)
PRODUCER_SYSTEM = (
    'Read only the supplied current source and private source. Quote the private project rules exactly. '
    'Do not guess the other analyst\'s private rules. A summary is a hypothesis, not evidence. '
    'This is reading supplied text, not executing an external action.'
)
PATTERNS = {'budget': re.compile(r'\bBudget (\d+) euros\.'),
            'deadline': re.compile(r'\bDeadline (\d+) days\.'),
            'local_only': re.compile(r'\bLocal-only requirement: (true|false)\.')}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def source(owner, text):
    sha = digest(text)
    return {'owner': owner, 'source_id': 'src_' + sha[:24], 'sha256': sha, 'text': text}


def render_current(public):
    text = 'Project ' + public['project'] + '. Decide from the private project rules supplied by the analysts. '
    for option in public['options']:
        text += ('Option {entity}: cost {cost} euros, duration {days} days, local {local}. '
                 .format(**(option | {'local': str(option['local']).lower()})))
    return text + 'Compute each remaining budget and eligibility; choose cheapest eligible.'


def checked_source(value):
    if digest(value['text']) != value['sha256'] or value['source_id'] != 'src_' + value['sha256'][:24]:
        raise ValueError('Source identity mismatch')
    return value


def producer_messages(fixture, role):
    """Only its own source reaches a producer. No oracle, peer source or completed rule map."""
    if role not in ROLES:
        raise ValueError('Unknown producer role')
    private = [checked_source(s) for s in fixture['sources'] if s['owner'] == role]
    return [{'role': 'system', 'content': PRODUCER_SYSTEM},
            {'role': 'user', 'content': canonical({'role': role, 'current_source': render_current(fixture['public']),
                                                 'private_sources': [{'source_id': s['source_id'], 'sha256': s['sha256'],
                                                                      'text': s['text']} for s in private]})}]


def exact_quotes(fixture, roles=ROLES):
    """Deterministic exact-source control; not a model-authored Offer or utility result."""
    return [{k: s[k] for k in ('source_id', 'sha256', 'text')} for s in fixture['sources'] if s['owner'] in roles]


def validate_quotes(fixture, quotes):
    sources = {s['source_id']: checked_source(s) for s in fixture['sources']}
    seen = set()
    result = []
    for quote in quotes:
        if set(quote) != {'source_id', 'sha256', 'text'}:
            raise ValueError('Only source identity and quoted text may be delivered')
        match = sources.get(quote['source_id'])
        if match is None or quote['sha256'] != match['sha256'] or not quote['text'] or quote['text'] not in match['text']:
            raise ValueError('Quotation is not bound to supplied source bytes')
        key = canonical(quote)
        if key in seen:
            raise ValueError('Duplicate quotation')
        seen.add(key)
        result.append(dict(quote))
    return result


def consumer_messages(fixture, quotes=()):
    """C3 sees public options plus explicitly delivered valid quotes; never full hidden sources or oracle."""
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': canonical({'current_source': render_current(fixture['public']),
                                                 'verified_quotes': validate_quotes(fixture, quotes)})}]


def facts(texts):
    values = {field: set() for field in REQUIRED}
    for text in texts:
        for field, pattern in PATTERNS.items():
            for raw in pattern.findall(text):
                values[field].add(raw == 'true' if field == 'local_only' else int(raw))
    return values


def solve(public, rule):
    options = []
    for option in public['options']:
        eligible = (option['cost'] <= rule['budget'] and option['days'] <= rule['deadline']
                    and (option['local'] or not rule['local_only']))
        options.append(dict(option, remaining=rule['budget'] - option['cost'], eligible=eligible))
    eligible = [option for option in options if option['eligible']]
    action = min(eligible, key=lambda o: (o['cost'], o['entity']))['entity'] if eligible else 'NONE'
    return {'project': public['project'], 'action': action, 'options': options}


def oracle_for_quotes(fixture, quotes):
    values = facts(q['text'] for q in validate_quotes(fixture, quotes))
    if any(len(values[field]) != 1 for field in REQUIRED):
        return {'project': fixture['public']['project'], 'action': 'UNKNOWN',
                'options': [dict(option, remaining=None, eligible=None) for option in fixture['public']['options']]}
    return solve(fixture['public'], {field: next(iter(values[field])) for field in REQUIRED})


def completion_witnesses(fixture, roles):
    """Exhaust all declared discrete rule completions consistent with the visible private sources.

    Returns a witness world per possible *action*. Thus two witnesses with
    different actions prove decision insufficiency, not merely a missing field.
    """
    observed = facts(s['text'] for s in fixture['sources'] if s['owner'] in roles)
    if any(len(observed[field]) > 1 for field in REQUIRED):
        return {}
    candidates = [sorted(observed[field]) if observed[field] else DOMAINS[field] for field in REQUIRED]
    witnesses = {}
    for values in itertools.product(*candidates):
        rule = dict(zip(REQUIRED, values))
        answer = solve(fixture['public'], rule)
        witnesses.setdefault(answer['action'], {'rules': rule, 'answer': answer})
    return witnesses


def seal(fixture):
    fixture['oracle'] = oracle_for_quotes(fixture, exact_quotes(fixture))
    fixture['visibility_proof'] = {
        role: {'actions': sorted(witnesses := completion_witnesses(fixture, [role])),
               'witnesses': witnesses} for role in ROLES}
    fixture['paired_actions'] = sorted(completion_witnesses(fixture, ROLES))
    fixture['current'] = render_current(fixture['public'])
    return fixture


def generate(seed=20261016, primary_count=30):
    if type(primary_count) is not int or primary_count < 3 or primary_count % 3:
        raise ValueError('Primary count must be a positive multiple of three')
    rng = random.Random(seed)
    primary = []
    used = set()
    for index in range(primary_count):
        project = ''.join(rng.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(8))
        if project in used:
            raise ValueError('Generated project identity collision')
        used.add(project)
        cheap = rng.randint(15, 55)
        expensive = cheap + rng.randint(12, 35)
        quick = rng.randint(1, 4)
        slow = quick + rng.randint(2, 5)
        case = ('cheapest', 'deadline', 'interaction_none')[index % 3]
        local_only = rng.choice((False, True))
        budget = rng.randint(cheap, expensive - 1) if case == 'interaction_none' else expensive + rng.randint(1, 20)
        deadline = slow if case == 'cheapest' else quick
        options = [{'entity': 'A', 'cost': cheap, 'days': slow, 'local': case == 'cheapest' and local_only},
                   {'entity': 'B', 'cost': expensive, 'days': quick, 'local': True}]
        if rng.choice((False, True)):
            options = [dict(options[1], entity='A'), dict(options[0], entity='B')]
        fixture = {'id': 'private_' + project.lower(), 'kind': 'complementary',
                   'public': {'project': project, 'options': options},
                   'sources': [source('B1_DETAIL', f'Project {project}. Budget {budget} euros.'),
                               source('B2_GIST', f'Project {project}. Deadline {deadline} days. Local-only requirement: {str(local_only).lower()}.')]}
        primary.append(seal(fixture))
    # Dedicated negative controls: remove one required clause, or introduce a
    # same-revision disagreement. Neither is counted as paired solvability.
    controls = []
    for original in primary[:3]:
        missing = copy.deepcopy(original)
        missing.update(id=original['id'] + '_missing', kind='missing_rule')
        old = missing['sources'][1]
        missing['sources'][1] = source(old['owner'], re.sub(r' Local-only requirement: (?:true|false)\.', '', old['text']))
        controls.append(seal(missing))
        conflict = copy.deepcopy(original)
        conflict.update(id=original['id'] + '_conflict', kind='contradictory_rule')
        old = conflict['sources'][1]
        budget = next(iter(facts([conflict['sources'][0]['text']])['budget']))
        conflict['sources'][1] = source(old['owner'], old['text'] + f' Budget {budget + 7} euros.')
        controls.append(seal(conflict))
        exact = copy.deepcopy(original)
        exact.update(id=original['id'] + '_exact', kind='exact_control')
        controls.append(seal(exact))
    rng.shuffle(primary)
    return {'schema': SCHEMA, 'seed': seed, 'status': 'FIXTURE_GEOMETRY_ONLY_NOT_PREREGISTERED',
            'historical_step2_utility': 'UTILITY_FAIL_UNCHANGED', 'gate_promotion': False,
            'native_runs': 0, 'domains': DOMAINS, 'fixtures': primary + controls,
            'variant_mapping': {'b1_only': ['B1_DETAIL'], 'b2_only': ['B2_GIST'],
                                'both_none': list(ROLES), 'both_exact': list(ROLES),
                                'both_control': list(ROLES), 'same_policy_dual': ['B1_DETAIL', 'B1_DETAIL']},
            'mapping_limit': 'Views only. Existing harness gives both bodies the same source; a future explicitly owned adapter must enforce private visibility. Channel comparisons and prompt_only_dual retention disablement are not implemented here.'}


def export(output, seed=20261016, primary_count=30):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    result = generate(seed, primary_count)
    fixtures = result['fixtures']
    visibility = {'schema': SCHEMA + '_PROMPTS', 'fixtures': [
        {'id': f['id'], 'kind': f['kind'], 'producers': {role: producer_messages(f, role) for role in ROLES},
         'consumer_current_only': consumer_messages(f),
         'consumer_exact_control': consumer_messages(f, exact_quotes(f))} for f in fixtures]}
    for name, value in [('fixtures.json', result), ('prompt-views.json', visibility)]:
        (output / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
    manifest = {'schema': SCHEMA + '_MANIFEST', 'generator_sha256': digest(Path(__file__).read_bytes()),
                'files': {name: digest((output / name).read_bytes()) for name in ('fixtures.json', 'prompt-views.json')},
                'primary_count': primary_count, 'control_count': len(fixtures) - primary_count,
                'model_runs': 0, 'gate_promotion': False}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=20261016)
    parser.add_argument('--primary-count', type=int, default=30)
    args = parser.parse_args()
    print(canonical(export(args.out, args.seed, args.primary_count)))
