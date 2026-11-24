"""WP-W2b: preregistered follow-up, rule values bound to their exact source span.

WP-W2 (docs/proofs/continuation-20261012/calc-tool-ablation/BEFUND.md): with the
deterministic eligibility recipe all three small models pass, but every UNKNOWN
came from the token guard, because no model returns null for a missing rule
(they invent budgets such as 50 or 100). A token guard fails when an invented
value happens to occur elsewhere in the evidence (e.g. equals an option cost).

extract_span: the model returns, for each rule value, the exact quote it read it
from. A value counts only if that quote is an exact substring of the current
source or a verified quote, names the rule (budget / deadline / local-only) and
contains the value as a token. Option values keep the token guard (they come
from the current source).

Cases: the 8 recorded wholesale messages of WP-W2 (exposed) plus 8 new cases
fixed in this file before any inference. The new consumer messages are
constructed in the recorded format (system text, one analyst with a fixed
hypothesis, wholesale verified earlier quote unless the prior is corrupt). Four
new cases are adversarial for the token guard (an option cost of 50 or 100 with
a missing budget), two carry a budget number only in the analyst hypothesis.

Diagnosis only: Linux cloud, no Redmi, no model choice, canonical_gate_pass
false, STEP2 UTILITY_FAIL unchanged.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import calc_tool_ablation as w2
from scripts import consumer_model_ablation as consumer
from scripts.rule_transport_ablation import FIXTURES as RECORDED_FIXTURES, fixtures
from tests.integration_step2_utility import SYSTEM, installed_links
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision

ROOT = Path(__file__).resolve().parents[1]
MODELS = consumer.MODELS
MODES = ('action_first', 'extract_tool', 'extract_span')
ARMS = tuple(m+'/'+o for m in MODELS for o in MODES)
CONFIG = consumer.CONFIG
RECIPE = 'eligibility-v1'
GUARD = 'span-bound-v1'

NEW_PARAMETERS = (
    ('Sable', 74, 9, False, (52, 8, True), (61, 6, False), 'prior'),
    ('Tarn', 40, 5, True, (38, 6, True), (35, 4, True), 'prior'),
    ('Umber', 48, 6, False, (50, 5, True), (41, 6, False), 'current_override'),
    ('Vale', 35, 7, True, (31, 5, False), (34, 6, True), 'current_override'),
    ('Wren', None, 8, False, (50, 4, True), (57, 5, False), 'missing_rule'),
    ('Yarrow', None, 6, True, (100, 3, True), (45, 5, True), 'missing_rule'),
    ('Zinc', None, 7, False, (26, 2, True), (31, 3, False), 'corrupt_prior'),
    ('Alder', None, 5, True, (50, 4, True), (39, 3, True), 'corrupt_prior'),
)
NEW_FIXTURES = fixtures(NEW_PARAMETERS)
HYPOTHESIS_NUMBER = {'Yarrow', 'Zinc'}  # analyst hypothesis names a budget that is not evidence
FIXTURE_ORDER = [f['id'] for f in RECORDED_FIXTURES]+[f['id'] for f in NEW_FIXTURES]
ALL_FIXTURES = {f['id']: f for f in RECORDED_FIXTURES+NEW_FIXTURES}


def constructed_messages(fixture):
    """Recorded wholesale format; earlier source delivered whole unless the prior is corrupt."""
    summary = ('The budget is probably 80 euros.' if fixture['id'] in HYPOTHESIS_NUMBER
               else 'Earlier project rules may apply to this decision.')
    quotes = [] if fixture['control'] == 'corrupt_prior' else [
        {'semantic_truth_authority': False, 'text': fixture['prior'], 'verification': 'EXACT_EARLIER_SOURCE_WHOLESALE_CONTROL'}]
    user = {'analysts': [{'hypothesis': {'needs_reentry': True, 'summary': summary, 'uncertainty': 'high'},
                          'hypothesis_authority': 'MODEL_HYPOTHESIS_NOT_FACT', 'role': 'B2_GIST', 'verified_quotes': quotes}],
            'current_source': fixture['current']}
    return [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': dumps(user)}]


_OPTIONS = w2.EXTRACT_SCHEMA['properties']['options']
_QUOTE = {'type': ['string', 'null']}
SPAN_SCHEMA = {'type': 'object', 'additionalProperties': False,
               'required': ['project', 'options', 'budget_quote', 'budget', 'deadline_quote', 'deadline', 'local_only_quote', 'local_only'],
               'properties': {'project': {'type': 'string'}, 'options': _OPTIONS,
                              'budget_quote': _QUOTE, 'budget': {'type': ['integer', 'null']},
                              'deadline_quote': _QUOTE, 'deadline': {'type': ['integer', 'null']},
                              'local_only_quote': _QUOTE, 'local_only': {'type': ['boolean', 'null']}}}
RULE_WORD = {'budget': r'\bbudget\b', 'deadline': r'\bdeadline\b', 'local_only': r'\blocal-only\b'}


def schema(mode):
    return SPAN_SCHEMA if mode == 'extract_span' else w2.schema(mode)


def evidence_spans(messages):
    user = json.loads(next(m['content'] for m in messages if m['role'] == 'user'))
    texts = [user.get('current_source', '')]
    for analyst in user.get('analysts', []):
        texts += [q['text'] for q in analyst.get('verified_quotes', [])]
    return texts


def span_bound(name, value, quote, texts):
    """Value counts only with an exact evidence quote that names the rule and contains the value."""
    if value is None: return True
    if not isinstance(quote, str) or not quote.strip() or not any(quote in t for t in texts): return False
    if not re.search(RULE_WORD[name], quote, re.I): return False
    token = str(value).lower() if isinstance(value, bool) else str(value) if type(value) is int else None
    return token is not None and re.search(r'(?<![\w.])'+re.escape(token)+r'(?!\w|\.\d)', quote, re.I) is not None


def run_span_tool(raw, messages):
    try: x = json.loads(raw)
    except ValueError: return None, {'error': 'invalid_json'}
    if not isinstance(x, dict) or set(x) != set(SPAN_SCHEMA['required']): return None, {'error': 'extract_schema'}
    texts = evidence_spans(messages); evidence = '\n'.join(texts); rejected = []
    rules = {}
    for k in ('budget', 'deadline', 'local_only'):
        ok = span_bound(k, x[k], x[k+'_quote'], texts)
        rules[k] = x[k] if ok else None
        if not ok: rejected.append(k)
    for o in x['options']:
        for k in ('cost', 'days'):
            if not w2.grounded(o[k], evidence): rejected.append(o['entity']+'.'+k)
    if any('.' in r for r in rejected): rules['budget'] = None
    action, opts = w2.eligibility(rules['budget'], rules['deadline'], rules['local_only'], x['options'])
    return dumps({'project': x['project'], 'action': action, 'options': opts}), {'extracted': x, 'rejected_unbound': rejected,
                                                                                 'recipe': RECIPE, 'guard': GUARD}


def binding(installed):
    found = w2.binding(installed)
    found['source_sha256'][str(Path(__file__).resolve().relative_to(ROOT))] = file_hash(Path(__file__).resolve())
    found['source_scope'] += '_PLUS_SPAN_FOLLOW_UP'
    return found


def inputs_for(report_path):
    _, recorded = consumer.recorded_inputs(report_path)
    return recorded | {f['id']: constructed_messages(f) for f in NEW_FIXTURES}


def preregistration(installed, report_path, w2_report):
    previous = json.loads(Path(w2_report).read_text())
    if previous.get('status') != 'RECORDED_DIAGNOSIS': raise ValueError('WP-W2 ablation is not a complete recorded diagnosis')
    inputs = inputs_for(report_path)
    return {'schema': 'CALC_TOOL_SPAN_ABLATION_PREREGISTRATION_V1',
            'source_report': {'path': str(Path(report_path).resolve()), 'sha256': file_hash(report_path)},
            'previous_w2_report': {'path': str(Path(w2_report).resolve()), 'sha256': file_hash(w2_report)},
            'consumer_messages_sha256': {k: digest(dumps(inputs[k])) for k in FIXTURE_ORDER},
            'fixture_order': FIXTURE_ORDER, 'new_fixtures_sha256': digest(dumps(NEW_FIXTURES)),
            'recorded_fixtures_sha256': digest(dumps(RECORDED_FIXTURES)), 'hypothesis_number_cases': sorted(HYPOTHESIS_NUMBER),
            'arm_order': list(ARMS), 'recipe': RECIPE, 'guard': GUARD,
            'schemas_sha256': {m: digest(dumps(schema(m))) for m in MODES}, 'wire': 'WP-W1 runners.wire_json (schema key order kept)',
            'config': CONFIG, 'consumer_sampling_seed': 13, 'native_oracle_visibility': False,
            'primary_metric': 'decision-exact rows (all scored fields except project) per arm, separately on the 8 new cases',
            'decision_rule': 'on the 8 NEW cases an arm passes only with >=3/4 decision-exact on oracle A/B rows and >=3/4 action UNKNOWN on missing/corrupt rows; the 8 recorded cases are exposed and reported only',
            'secondary': 'UNKNOWN rows split into model-null vs guard-rejected; token-guard acceptance of invented values on the four adversarial cases',
            'scope': 'TOOL_GUARD_DIAGNOSIS_ONLY_NOT_A_MODEL_CHOICE_NOT_STEP2', 'canonical_gate_pass': False, 'binding': binding(installed)}


def run_arm(home, installed, arm, inputs, rows_done):
    model_role, mode = arm.split('/')
    initialize(home); save_config(home, CONFIG); installed_links(home, installed)
    r = Runtime(home)
    try:
        target = r.models.path_for(model_role)
        r.models.router = lambda role: target if role == 'C3_LANGUAGE' else None
        for fid in FIXTURE_ORDER:
            if (fid, arm) in rows_done: continue
            fixture = ALL_FIXTURES[fid]; messages = inputs[fid]
            row = {'fixture': fid, 'arm': arm, 'set': 'new' if fid in {f['id'] for f in NEW_FIXTURES} else 'recorded_exposed',
                   'control': fixture['control'], 'consumer_model_role': model_role, 'consumer_model_sha256': file_hash(target),
                   'mode': mode, 'raw_answer': '', 'status': 'RUNNING', 'oracle_visible_to_native': False}
            started = time.monotonic()
            try:
                runner = r.pool.get('C3_LANGUAGE'); deadline = time.monotonic()+CONFIG['deadline_seconds']
                for chunk in runner.generate(messages, r.cancel_event, deadline, CONFIG['answer_tokens'], schema(mode), seed=13):
                    row['raw_answer'] += chunk
                row['consumer_metrics'] = dict(runner.last_metrics)
                answer = row['raw_answer']
                if mode == 'extract_tool': answer, row['tool'] = w2.run_tool(answer, messages)
                elif mode == 'extract_span': answer, row['tool'] = run_span_tool(answer, messages)
                row['answer'] = answer or row['raw_answer']
                row['score'] = score_decision(row['answer'], fixture['oracle'])
                row['status'] = 'RECORDED' if runner.last_metrics.get('status') == 'FINAL' else 'STRUCTURAL_FAIL'
            except (Exception, KeyboardInterrupt) as exc:
                row.update(status='INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'ERROR', error_type=type(exc).__name__,
                           error=str(exc)[:500], score={'utility': 0., 'exact': False, 'contradictions': ['inference_failed']})
            row['decision_exact'] = w2.decision_exact(row['score'])
            row['elapsed_s'] = time.monotonic()-started
            try: row['action'] = json.loads(row.get('answer') or '').get('action')
            except (ValueError, AttributeError): row['action'] = None
            yield row
            if row['status'] == 'INTERRUPTED': return
    finally:
        r.close()


def _summary(items):
    decidable = [r for r in items if ALL_FIXTURES[r['fixture']]['oracle']['action'] in ('A', 'B')]
    unknown = [r for r in items if ALL_FIXTURES[r['fixture']]['oracle']['action'] == 'UNKNOWN']
    exact_decidable = sum(bool(r['decision_exact']) for r in decidable)
    unknown_ok = sum(r.get('action') == 'UNKNOWN' for r in unknown)
    model_null = sum(r.get('action') == 'UNKNOWN' and (r.get('tool') or {}).get('extracted', {}).get('budget') is None for r in unknown)
    return {'rows': len(items), 'decision_exact': sum(bool(r['decision_exact']) for r in items),
            'strict_exact': sum(bool(r['score']['exact']) for r in items),
            'mean_strict_utility': sum(r['score']['utility'] for r in items)/len(items) if items else None,
            'actions': [r.get('action') for r in items], 'decision_exact_on_decidable': exact_decidable,
            'unknown_on_missing_or_corrupt': unknown_ok, 'unknown_by_model_null_budget': model_null,
            'passes_decision_rule': len(decidable) == 4 and len(unknown) == 4 and exact_decidable >= 3 and unknown_ok >= 3,
            'structural_failures': sum(r['status'] != 'RECORDED' for r in items)}


def aggregate(rows):
    return {arm: {s: _summary([r for r in rows if r['arm'] == arm and r['set'] == s]) for s in ('new', 'recorded_exposed')}
            for arm in ARMS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', type=Path, required=True)
    parser.add_argument('--rule-transport-report', type=Path, required=True)
    parser.add_argument('--w2-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--register-only', action='store_true')
    args = parser.parse_args()
    registration = preregistration(args.installed_home, args.rule_transport_report, args.w2_report)
    path = args.out.with_suffix('.preregistration.json'); args.out.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != registration: raise ValueError('Preregistration binding changed; use a fresh output path')
    else: atomic_write(path, dumps(registration))
    registration_sha = file_hash(path)
    if args.register_only:
        print(dumps({'status': 'PREREGISTERED_NO_INFERENCE', 'path': str(path), 'sha256': registration_sha})); return
    inputs = inputs_for(args.rule_transport_report)
    if args.out.exists():
        out = json.loads(args.out.read_text())
        if out.get('preregistration_sha256') != registration_sha: raise ValueError('Resume preregistration changed')
        if out.get('row_sha256') != {r['fixture']+'/'+r['arm']: digest(dumps(r)) for r in out['rows']}: raise ValueError('Resume recorded row bytes changed')
    else:
        out = {'schema': 'CALC_TOOL_SPAN_ABLATION_V1', 'status': 'RUNNING', 'rows': [], 'row_sha256': {},
               'preregistration_sha256': registration_sha, 'canonical_gate_pass': False, 'phone_measured': False}
        atomic_write(args.out, dumps(out))
    done = {(r['fixture'], r['arm']) for r in out['rows']}
    work = args.out.with_suffix('.checkpoint'); work.mkdir(exist_ok=True)
    for arm in ARMS:
        if all((f, arm) in done for f in FIXTURE_ORDER): continue
        if binding(args.installed_home) != registration['binding']:
            out['status'] = 'ARTIFACT_CHANGED'; atomic_write(args.out, dumps(out)); raise ValueError('Binding changed during ablation')
        home = work/arm.replace('/', '-')
        if home.exists(): shutil.rmtree(home)
        for row in run_arm(home, args.installed_home, arm, inputs, done):
            out['rows'].append(row); out['row_sha256'][row['fixture']+'/'+arm] = digest(dumps(row))
            out['summary'] = aggregate(out['rows']); atomic_write(args.out, dumps(out))
            print(dumps({'fixture': row['fixture'], 'arm': arm, 'status': row['status'], 'action': row.get('action'),
                         'decision_exact': row['decision_exact']}), flush=True)
            if row['status'] == 'INTERRUPTED':
                out['status'] = 'INTERRUPTED'; atomic_write(args.out, dumps(out)); raise KeyboardInterrupt
        shutil.rmtree(home, ignore_errors=True)
    shutil.rmtree(work, ignore_errors=True)
    out['installed_artifacts_unchanged'] = binding(args.installed_home) == registration['binding']
    out['status'] = ('RECORDED_DIAGNOSIS' if all(r['status'] == 'RECORDED' for r in out['rows']) else 'STRUCTURAL_FAIL') if out['installed_artifacts_unchanged'] else 'ARTIFACT_CHANGED'
    out['summary'] = aggregate(out['rows']); atomic_write(args.out, dumps(out))


if __name__ == '__main__': main()
