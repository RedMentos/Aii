"""Preregistered rule-transport ablation (source-handoff candidate 2).

The 16-case source-handoff ablation (docs/proofs/continuation-20261012/
source-handoff-ablation-claude-rebound/BEFUND.md) showed that no arm ever
delivered a quote from the earlier source: B2 spent its two short quotes on
current text. This candidate gives B2 a separate, exact-substring-verified
``earlier_quotes`` field for rules from earlier source excerpts. A wholesale
control (complete hash-checked earlier excerpt delivered to C3) bounds what
transport alone can achieve; it deliberately violates the canonical "never
copied wholesale" rule and is therefore a diagnostic upper bound only.

Runtime files are not modified; arm sources are text transforms of the
reviewed runtime, bound by digest in the preregistration before inference.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import source_handoff_ablation as base
from scripts.source_handoff_candidate import ROOT, _replace, sources
from tests.integration_step2_utility import SYSTEM, SCHEMA
from v13.common import atomic_write, digest, dumps, file_hash

ARMS = ('current', 'earlier_quotes', 'wholesale_control')
CONFIG = base.CONFIG | {'observer_tokens': 256}
PARAMETERS = (
    ('Mira', 61, 8, False, (45, 7, True), (55, 4, False), 'prior'),
    ('Lumen', 43, 4, True, (32, 3, False), (39, 4, True), 'current_override'),
    ('Nacre', None, 9, False, (28, 3, True), (37, 4, False), 'missing_rule'),
    ('Tessera', None, 6, True, (25, 2, True), (33, 5, True), 'corrupt_prior'),
    # Held-out cases fixed before any native call of this cohort.
    ('Orrin', 58, 6, True, (41, 5, True), (36, 4, False), 'prior'),
    ('Pelt', 50, 5, False, (47, 6, True), (44, 5, False), 'current_override'),
    ('Quill', None, 7, True, (30, 4, True), (26, 3, True), 'missing_rule'),
    ('Rhea', None, 5, False, (22, 4, False), (29, 3, True), 'corrupt_prior'),
)


def fixtures(parameters=PARAMETERS):
    """Same generator as the 16-case ablation, extended by four held-out cases."""
    rows = []
    for name, budget, deadline, local, a, b, control in parameters:
        prior_budget = budget+19 if control == 'current_override' else 71 if control == 'corrupt_prior' else budget
        prior_deadline = deadline+3 if control == 'current_override' else deadline
        prior_local = not local if control == 'current_override' else local
        prior = f'Project {name}. '+(f'Budget {prior_budget} euros. ' if prior_budget is not None else 'No budget has been supplied. ')+f'Deadline {prior_deadline} days. Local-only requirement: {str(prior_local).lower()}.'
        current = f'Project {name}. Apply earlier project rules. Option A: cost {a[0]} euros, duration {a[1]} days, local {str(a[2]).lower()}. Option B: cost {b[0]} euros, duration {b[1]} days, local {str(b[2]).lower()}. Compute remaining budget and eligibility; choose cheapest eligible.'
        if control == 'current_override':
            current += f' Current rules replace earlier rules: budget {budget} euros, deadline {deadline} days, local-only requirement {str(local).lower()}.'
        options = [{'entity': entity, 'cost': cost, 'remaining': None if budget is None else budget-cost, 'days': days, 'local': is_local,
                    'eligible': None if budget is None else cost <= budget and days <= deadline and (is_local or not local)}
                   for entity, (cost, days, is_local) in zip(('A', 'B'), (a, b))]
        eligible = [o for o in options if o['eligible'] is True]
        action = 'UNKNOWN' if budget is None else min(eligible, key=lambda o: (o['cost'], o['entity']))['entity'] if eligible else 'NONE'
        rows.append({'id': name, 'control': control, 'prior': prior, 'current': current,
                     'oracle': {'project': name, 'action': action, 'options': options}})
    return rows


FIXTURES = fixtures()

EARLIER_SCHEMA = '''

_reviewed_offer_schema = offer_schema
def offer_schema(tokens):
    """Rule-transport candidate: same token budget, re-split so a separate
    earlier_quotes field fits without truncating the JSON."""
    s = _reviewed_offer_schema(tokens); pr = s['properties']; chars = max(110, int((int(tokens)-30)*2.2))
    pr['summary']['maxLength'] = max(48, int(chars*.3)); pr['uncertainty']['maxLength'] = max(16, int(chars*.1))
    pr['quotes']['items']['maxLength'] = max(24, int(chars*.15))
    pr['earlier_quotes'] = {'type': 'array', 'items': {'type': 'string', 'maxLength': max(24, int(chars*.15))}, 'maxItems': 2}
    s['required'] = s['required']+['earlier_quotes']
    return s
'''

EARLIER_REFS = '''        for quote in (obj.get('earlier_quotes') or [])[:2]:  # rule-transport candidate: earlier excerpts only
            match = next(((source, ref) for source, ref in sources[1:] if isinstance(quote, str) and quote and quote in source), None)
            if not match: rejected += 1; continue
            source, base = match; start = base['char_start']+source.index(quote); ref = base | {'char_start': start, 'char_end': start+len(quote)}; self.s.read_source(ref); refs.append(ref)
'''

WHOLESALE = '''            for context_ref in allowed[1:]:  # DIAGNOSTIC UPPER BOUND ONLY: violates canonical no-wholesale transport
                try: context_text = self.s.read_source(context_ref)
                except (ValueError, OSError): continue
                verified.append({'text': context_text, 'source_ref': dict(context_ref), 'verification': 'EXACT_EARLIER_SOURCE_WHOLESALE_CONTROL',
                                 'semantic_truth_authority': False})
'''

QUOTE_LOOP_END = "            source,base=match;start=base['char_start']+source.index(quote);ref=base|{'char_start':start,'char_end':start+len(quote)};self.s.read_source(ref);refs.append(ref)\n"
VERIFIED_END = "                verified.append({'text':text,'source_ref':dict(ref),'verification':'EXACT_SOURCE_SUBSTRING_ONLY',\n                                 'semantic_truth_authority':False})\n"
EARLIER_INSTRUCTION = (" earlier_quotes copies up to two exact substrings of earlier_context exact_source_excerpt that state limits or "
                       "requirements the current text refers to but does not restate; use [] when none apply.")


def arm_sources():
    """Per-arm (cognition, bodyview) text; every arm keeps its own transport class."""
    _, current = sources()
    cognition, bodyview = current['v13/cognition.py'], current['v13/bodyview.py']
    earlier = _replace(cognition, "if set(obj)!=set(OFFER_SCHEMA['required'])",
                       "if set(obj)-{'earlier_quotes'}!=set(OFFER_SCHEMA['required']) or not isinstance(obj.get('earlier_quotes',[]),list)")
    earlier = _replace(earlier, QUOTE_LOOP_END, QUOTE_LOOP_END+EARLIER_REFS)
    earlier = _replace(earlier, "if text not in offer['offer'].get('quotes',[]):",
                       "if text not in offer['offer'].get('quotes',[])+(offer['offer'].get('earlier_quotes') or []):")
    earlier = _replace(earlier, " Quotes may cite only current source text or an exact earlier source excerpt, never own-state or hypotheses.'",
                       " Quotes may cite only current source text or an exact earlier source excerpt, never own-state or hypotheses."+EARLIER_INSTRUCTION+"'")
    earlier += EARLIER_SCHEMA
    wholesale = _replace(cognition, VERIFIED_END, VERIFIED_END+WHOLESALE)
    return {'current': {'cognition': cognition, 'bodyview': bodyview},
            'earlier_quotes': {'cognition': earlier, 'bodyview': bodyview},
            'wholesale_control': {'cognition': wholesale, 'bodyview': bodyview}}


def validators(arms):
    return {arm: base.module('validator_'+arm, code['cognition']).Cognition for arm, code in arms.items()}


def binding(installed):
    found = base.binding(installed)
    path = Path(__file__).resolve()
    found['source_sha256'][str(path.relative_to(ROOT))] = file_hash(path)
    found['source_scope'] = found['source_scope']+'_PLUS_RULE_TRANSPORT_HARNESS'
    return found


def preregistration(installed, previous):
    arms = arm_sources()
    return {'schema': 'RULE_TRANSPORT_ABLATION_PREREGISTRATION_V1', 'fixtures': FIXTURES,
            'fixtures_sha256': digest(dumps(FIXTURES)), 'held_out_fixtures': [p[0] for p in PARAMETERS[4:]],
            'consumer_system': SYSTEM, 'consumer_schema': SCHEMA, 'consumer_schema_sha256': digest(dumps(SCHEMA)),
            'arm_specs': {'current': 'reviewed runtime producer and transport (= 16-case full_candidate)',
                          'earlier_quotes': 'separate exact-verified earlier_quotes field from earlier excerpts; same token budget re-split',
                          'wholesale_control': 'current producer; complete hash-checked earlier excerpt delivered; DIAGNOSTIC UPPER BOUND, not canonical'},
            'arm_order': list(ARMS), 'arm_source_sha256': {arm: {name: digest(text) for name, text in code.items()} for arm, code in arms.items()},
            'config': CONFIG, 'body_sampling_seed': 13, 'consumer_sampling_seed': 13, 'native_oracle_visibility': False,
            'primary_metric': 'rows_with_prior_quote and mean_strict_utility per arm; exact decisions secondary',
            'decision_rule': 'earlier_quotes is an integration candidate only if it delivers prior quotes in >=3/4 prior/current_override rows, never delivers a corrupted prior, and mean strict utility is not below current',
            'scope': 'PRODUCER_RULE_TRANSPORT_DIAGNOSIS_ONLY', 'canonical_gate_pass': False,
            'previous_ablation': previous, 'binding': binding(installed)}


def aggregate(rows):
    out = {}
    for arm in ARMS:
        items = [r for r in rows if r['arm'] == arm]
        transport = [r for r in items if r['control'] in ('prior', 'current_override')]
        out[arm] = {'rows': len(items), 'mean_strict_utility': sum(r['score']['utility'] for r in items)/len(items) if items else None,
                    'exact_decisions': sum(bool(r['score']['exact']) for r in items),
                    'rows_with_prior_quote': sum(bool(r.get('delivered_prior_quotes')) for r in items),
                    'transport_rows_with_prior_quote': sum(bool(r.get('delivered_prior_quotes')) for r in transport),
                    'corrupt_prior_delivered': sum(not r.get('checks', {}).get('corrupt_prior_not_delivered', True) for r in items),
                    'structural_failures': sum(r['status'] != 'RECORDED' for r in items)}
    return out


def validate_resume(report, registration_sha):
    if report.get('preregistration_sha256') != registration_sha: raise ValueError('Resume preregistration changed')
    keys = [(r['fixture'], r['arm']) for r in report['rows']]
    allowed = {(f['id'], a) for f in FIXTURES for a in ARMS}
    if len(keys) != len(set(keys)) or any(k not in allowed for k in keys): raise ValueError('Resume row keys invalid')
    if report.get('row_sha256') != {r['fixture']+'/'+r['arm']: digest(dumps(r)) for r in report['rows']}:
        raise ValueError('Resume recorded row bytes changed')
    return set(keys)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', type=Path, required=True)
    parser.add_argument('--previous-ablation', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--register-only', action='store_true')
    args = parser.parse_args()
    report = json.loads(args.previous_ablation.read_text())
    if report.get('status') != 'RECORDED_DIAGNOSIS': raise ValueError('Previous source-handoff ablation is not a complete recorded diagnosis')
    previous = {'path': str(args.previous_ablation.resolve()), 'sha256': file_hash(args.previous_ablation),
                'status': report['status'], 'summary': report['summary']}
    registration = preregistration(args.installed_home, previous)
    registration_path = args.out.with_suffix('.preregistration.json')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if registration_path.exists():
        if json.loads(registration_path.read_text()) != registration: raise ValueError('Preregistration binding changed; use a fresh output path')
    else: atomic_write(registration_path, dumps(registration))
    registration_sha = file_hash(registration_path)
    if args.register_only:
        print(dumps({'status': 'PREREGISTERED_NO_INFERENCE', 'path': str(registration_path), 'sha256': registration_sha})); return
    if args.out.exists():
        out = json.loads(args.out.read_text()); done = validate_resume(out, registration_sha)
    else:
        out = {'schema': 'RULE_TRANSPORT_ABLATION_V1', 'status': 'RUNNING', 'rows': [], 'row_sha256': {},
               'preregistration_sha256': registration_sha, 'canonical_gate_pass': False,
               'learned_semantic_utility_proven': False, 'phone_measured': False}
        atomic_write(args.out, dumps(out)); done = set()
    arms = arm_sources(); checks = validators(arms)
    work = args.out.with_suffix('.checkpoint'); work.mkdir(exist_ok=True)
    for fixture in FIXTURES:
        for arm in ARMS:
            if (fixture['id'], arm) in done: continue
            if binding(args.installed_home) != registration['binding']:
                out['status'] = 'ARTIFACT_CHANGED'; atomic_write(args.out, dumps(out))
                raise ValueError('Native/source binding changed during ablation')
            home = work/(fixture['id']+'-'+arm)
            if home.exists(): shutil.rmtree(home)  # only an unfinished isolated scratch arm
            row = base.run_row(home, args.installed_home, fixture, arm, arms[arm], checks[arm])
            out['rows'].append(row); out['summary'] = aggregate(out['rows'])
            out['row_sha256'][fixture['id']+'/'+arm] = digest(dumps(row))
            atomic_write(args.out, dumps(out))
            print(dumps({'fixture': fixture['id'], 'arm': arm, 'status': row['status'], 'utility': row['score']['utility'],
                         'prior_quotes': len(row.get('delivered_prior_quotes') or [])}), flush=True)
            if row['status'] == 'INTERRUPTED':
                out['status'] = 'INTERRUPTED'; atomic_write(args.out, dumps(out)); raise KeyboardInterrupt
    out['installed_artifacts_unchanged'] = binding(args.installed_home) == registration['binding']
    out['status'] = ('RECORDED_DIAGNOSIS' if all(r['status'] == 'RECORDED' for r in out['rows']) else 'STRUCTURAL_FAIL') if out['installed_artifacts_unchanged'] else 'ARTIFACT_CHANGED'
    out['summary'] = aggregate(out['rows']); atomic_write(args.out, dumps(out))


if __name__ == '__main__': main()
