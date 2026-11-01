"""WP-W2: preregistered deterministic eligibility tool vs. model-made decision.

The consumer-model ablation (docs/proofs/continuation-20261012/
consumer-model-ablation/BEFUND.md) showed that no installed model (350M, 0.8B,
1.2B) computes budget/deadline/locality eligibility reliably from complete
rules. Canon §6.5 allows deterministic external tool recipes to stay as recipes;
the cognitive part left to the model is reading the typed values (bounded exact
channel: typed numbers) and choosing which rule is current.

Arms per consumer model (recorded wholesale consumer messages replayed
byte-identically, same as the consumer ablation):
  action_first   reviewed SCHEMA, now sent in its own key order (WP-W1 wire)
  options_first  same constraints, options before action (now effective, WP-W1)
  extract_tool   the model only extracts typed values (EXTRACT_SCHEMA); the
                 deterministic recipe `eligibility` computes remaining,
                 eligibility and the action. Every extracted number must occur
                 as an exact token in the current source or a verified quote,
                 otherwise the value counts as unavailable (UNKNOWN).

Diagnosis only: Linux cloud, no Redmi, no model choice, canonical_gate_pass
false. STEP2 measures two-body utility without a tool; this arm does not change
STEP2 UTILITY_FAIL.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import consumer_model_ablation as consumer
from scripts import source_handoff_ablation as handoff
from scripts.rule_transport_ablation import FIXTURES
from tests.integration_step2_utility import SCHEMA, installed_links
from v13.common import atomic_write, digest, dumps, file_hash
from v13.config import initialize, save_config
from v13.runtime import Runtime
from v13.utility import score_decision

ROOT = Path(__file__).resolve().parents[1]
MODELS = consumer.MODELS
MODES = ('action_first', 'options_first', 'extract_tool')
ARMS = tuple(m+'/'+o for m in MODELS for o in MODES)
CONFIG = consumer.CONFIG
RECIPE = 'eligibility-v1'

_OPTION = {'type': 'object', 'additionalProperties': False, 'required': ['entity', 'cost', 'days', 'local'],
           'properties': {'entity': {'type': 'string', 'enum': ['A', 'B']}, 'cost': {'type': 'integer'},
                          'days': {'type': 'integer'}, 'local': {'type': 'boolean'}}}
EXTRACT_SCHEMA = {'type': 'object', 'additionalProperties': False,
                  'required': ['project', 'options', 'budget', 'deadline', 'local_only'],
                  'properties': {'project': {'type': 'string'},
                                 'options': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': _OPTION},
                                 'budget': {'type': ['integer', 'null']},
                                 'deadline': {'type': ['integer', 'null']},
                                 'local_only': {'type': ['boolean', 'null']}}}


def schema(mode):
    if mode == 'extract_tool': return EXTRACT_SCHEMA
    return consumer.schema(mode)


def eligibility(budget, deadline, local_only, options):
    """Deterministic recipe (same rule as the SYSTEM text): cheapest eligible, A on a tie;
    any missing rule -> UNKNOWN with null remaining/eligible."""
    known = budget is not None and deadline is not None and local_only is not None
    out = []
    for o in options:
        ok = None if not known else o['cost'] <= budget and o['days'] <= deadline and (o['local'] or not local_only)
        out.append({'entity': o['entity'], 'cost': o['cost'], 'remaining': budget-o['cost'] if known else None,
                    'days': o['days'], 'local': o['local'], 'eligible': ok})
    if not known: action = 'UNKNOWN'
    else:
        eligible = [o for o in out if o['eligible']]
        action = min(eligible, key=lambda o: (o['cost'], o['entity']))['entity'] if eligible else 'NONE'
    return action, out


def evidence_text(messages):
    """Only exact evidence: current source and verified quotes (analyst summaries are hypotheses)."""
    user = json.loads(next(m['content'] for m in messages if m['role'] == 'user'))
    texts = [user.get('current_source', '')]
    for analyst in user.get('analysts', []):
        texts += [q['text'] for q in analyst.get('verified_quotes', [])]
    return '\n'.join(texts)


def grounded(value, evidence):
    """Typed-number guard: an integer counts only if it occurs as an exact token in the evidence."""
    return value is None or (type(value) is int and re.search(r'(?<![\d.])'+str(value)+r'(?![\d.])', evidence) is not None)


def run_tool(raw, messages):
    """Extraction -> guard -> recipe -> answer in the reviewed SCHEMA shape."""
    try: x = json.loads(raw)
    except ValueError: return None, {'error': 'invalid_json'}
    if not isinstance(x, dict) or set(x) != set(EXTRACT_SCHEMA['required']): return None, {'error': 'extract_schema'}
    evidence = evidence_text(messages); rejected = []
    rules = {k: x[k] for k in ('budget', 'deadline')}
    for k, v in rules.items():
        if not grounded(v, evidence): rejected.append(k); rules[k] = None
    options = []
    for o in x['options']:
        for k in ('cost', 'days'):
            if not grounded(o[k], evidence): rejected.append(o['entity']+'.'+k)
        options.append(o)
    if any('.' in r for r in rejected): rules['budget'] = None  # an ungrounded option value makes the decision unavailable
    action, opts = eligibility(rules['budget'], rules['deadline'], x['local_only'], options)
    answer = {'project': x['project'], 'action': action, 'options': opts}
    return dumps(answer), {'extracted': x, 'rejected_ungrounded': rejected, 'recipe': RECIPE}


def decision_exact(score):
    """Preregistered secondary: all fields except `project` (models copy 'Project Mira'; BEFUND consumer ablation, point 4)."""
    checks = {k: v for k, v in score.get('field_checks', {}).items() if k != 'project'}
    return bool(checks) and all(checks.values())


def binding(installed):
    found = handoff.binding(installed)
    for path in (Path(__file__).resolve(), ROOT/'scripts/consumer_model_ablation.py', ROOT/'scripts/rule_transport_ablation.py'):
        found['source_sha256'][str(path.relative_to(ROOT))] = file_hash(path)
    found['source_scope'] += '_PLUS_CALC_TOOL_ABLATION_HARNESS'
    return found


def preregistration(installed, report_path):
    report, inputs = consumer.recorded_inputs(report_path)
    return {'schema': 'CALC_TOOL_ABLATION_PREREGISTRATION_V1',
            'source_report': {'path': str(Path(report_path).resolve()), 'sha256': file_hash(report_path),
                              'preregistration_sha256': report['preregistration_sha256'], 'arm': consumer.SOURCE_ARM},
            'consumer_messages_sha256': {k: digest(dumps(v)) for k, v in sorted(inputs.items())},
            'fixtures_sha256': digest(dumps(FIXTURES)), 'arm_order': list(ARMS), 'recipe': RECIPE,
            'schemas_sha256': {m: digest(dumps(schema(m))) for m in MODES}, 'wire': 'WP-W1 runners.wire_json (schema key order kept)',
            'config': CONFIG, 'consumer_sampling_seed': 13, 'native_oracle_visibility': False,
            'primary_metric': 'decision-exact rows (all scored fields except project) per arm; strict exact and mean strict utility also reported',
            'decision_rule': 'an arm passes only with >=3/4 decision-exact on the four rows whose oracle action is A or B and >=3/4 action UNKNOWN on the four missing/corrupt rows',
            'deviation_from_consumer_ablation': 'project string excluded from the primary metric (every earlier row failed it by copying "Project X"); strict exact still reported',
            'scope': 'TOOL_ARM_DIAGNOSIS_ONLY_NOT_A_MODEL_CHOICE_NOT_STEP2', 'canonical_gate_pass': False, 'binding': binding(installed)}


def run_arm(home, installed, arm, inputs, rows_done):
    model_role, mode = arm.split('/')
    initialize(home); save_config(home, CONFIG); installed_links(home, installed)
    r = Runtime(home)
    try:
        target = r.models.path_for(model_role)
        r.models.router = lambda role: target if role == 'C3_LANGUAGE' else None
        for fixture in FIXTURES:
            if (fixture['id'], arm) in rows_done: continue
            messages = inputs[fixture['id']]
            row = {'fixture': fixture['id'], 'arm': arm, 'control': fixture['control'], 'consumer_model_role': model_role,
                   'consumer_model_sha256': file_hash(target), 'mode': mode, 'raw_answer': '', 'status': 'RUNNING',
                   'oracle_visible_to_native': False}
            started = time.monotonic()
            try:
                runner = r.pool.get('C3_LANGUAGE'); deadline = time.monotonic()+CONFIG['deadline_seconds']
                for chunk in runner.generate(messages, r.cancel_event, deadline, CONFIG['answer_tokens'], schema(mode), seed=13):
                    row['raw_answer'] += chunk
                row['consumer_metrics'] = dict(runner.last_metrics)
                answer = row['raw_answer']
                if mode == 'extract_tool':
                    answer, row['tool'] = run_tool(row['raw_answer'], messages)
                    answer = answer or row['raw_answer']
                row['answer'] = answer
                row['score'] = score_decision(answer, fixture['oracle'])
                row['status'] = 'RECORDED' if runner.last_metrics.get('status') == 'FINAL' else 'STRUCTURAL_FAIL'
            except (Exception, KeyboardInterrupt) as exc:
                row.update(status='INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'ERROR', error_type=type(exc).__name__,
                           error=str(exc)[:500], score={'utility': 0., 'exact': False, 'contradictions': ['inference_failed']})
            row['decision_exact'] = decision_exact(row['score'])
            row['elapsed_s'] = time.monotonic()-started
            try: row['action'] = json.loads(row.get('answer') or '').get('action')
            except (ValueError, AttributeError): row['action'] = None
            yield row
            if row['status'] == 'INTERRUPTED': return
    finally:
        r.close()


def aggregate(rows):
    result = {}
    by_id = {f['id']: f for f in FIXTURES}
    for arm in ARMS:
        items = [r for r in rows if r['arm'] == arm]
        decidable = [r for r in items if by_id[r['fixture']]['oracle']['action'] in ('A', 'B')]
        unknown = [r for r in items if by_id[r['fixture']]['oracle']['action'] == 'UNKNOWN']
        exact_decidable = sum(bool(r['decision_exact']) for r in decidable)
        unknown_ok = sum(r.get('action') == 'UNKNOWN' for r in unknown)
        result[arm] = {'rows': len(items), 'mean_strict_utility': sum(r['score']['utility'] for r in items)/len(items) if items else None,
                       'strict_exact': sum(bool(r['score']['exact']) for r in items),
                       'decision_exact': sum(bool(r['decision_exact']) for r in items), 'actions': [r.get('action') for r in items],
                       'decision_exact_on_decidable': exact_decidable, 'unknown_on_missing_or_corrupt': unknown_ok,
                       'passes_decision_rule': len(decidable) == 4 and len(unknown) == 4 and exact_decidable >= 3 and unknown_ok >= 3,
                       'ungrounded_rejections': sum(len((r.get('tool') or {}).get('rejected_ungrounded', [])) for r in items),
                       'structural_failures': sum(r['status'] != 'RECORDED' for r in items)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed-home', type=Path, required=True)
    parser.add_argument('--rule-transport-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--register-only', action='store_true')
    args = parser.parse_args()
    registration = preregistration(args.installed_home, args.rule_transport_report)
    path = args.out.with_suffix('.preregistration.json'); args.out.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text()) != registration: raise ValueError('Preregistration binding changed; use a fresh output path')
    else: atomic_write(path, dumps(registration))
    registration_sha = file_hash(path)
    if args.register_only:
        print(dumps({'status': 'PREREGISTERED_NO_INFERENCE', 'path': str(path), 'sha256': registration_sha})); return
    _, inputs = consumer.recorded_inputs(args.rule_transport_report)
    if args.out.exists():
        out = json.loads(args.out.read_text())
        if out.get('preregistration_sha256') != registration_sha: raise ValueError('Resume preregistration changed')
        if out.get('row_sha256') != {r['fixture']+'/'+r['arm']: digest(dumps(r)) for r in out['rows']}: raise ValueError('Resume recorded row bytes changed')
    else:
        out = {'schema': 'CALC_TOOL_ABLATION_V1', 'status': 'RUNNING', 'rows': [], 'row_sha256': {},
               'preregistration_sha256': registration_sha, 'canonical_gate_pass': False, 'phone_measured': False}
        atomic_write(args.out, dumps(out))
    done = {(r['fixture'], r['arm']) for r in out['rows']}
    work = args.out.with_suffix('.checkpoint'); work.mkdir(exist_ok=True)
    for arm in ARMS:
        if all((f['id'], arm) in done for f in FIXTURES): continue
        if binding(args.installed_home) != registration['binding']:
            out['status'] = 'ARTIFACT_CHANGED'; atomic_write(args.out, dumps(out)); raise ValueError('Binding changed during ablation')
        home = work/arm.replace('/', '-')
        if home.exists(): shutil.rmtree(home)  # only an unfinished isolated scratch arm
        for row in run_arm(home, args.installed_home, arm, inputs, done):
            out['rows'].append(row); out['row_sha256'][row['fixture']+'/'+arm] = digest(dumps(row))
            out['summary'] = aggregate(out['rows']); atomic_write(args.out, dumps(out))
            print(dumps({'fixture': row['fixture'], 'arm': arm, 'status': row['status'], 'action': row.get('action'),
                         'decision_exact': row['decision_exact'], 'utility': row['score']['utility']}), flush=True)
            if row['status'] == 'INTERRUPTED':
                out['status'] = 'INTERRUPTED'; atomic_write(args.out, dumps(out)); raise KeyboardInterrupt
        shutil.rmtree(home, ignore_errors=True)
    out['installed_artifacts_unchanged'] = binding(args.installed_home) == registration['binding']
    out['status'] = ('RECORDED_DIAGNOSIS' if all(r['status'] == 'RECORDED' for r in out['rows']) else 'STRUCTURAL_FAIL') if out['installed_artifacts_unchanged'] else 'ARTIFACT_CHANGED'
    out['summary'] = aggregate(out['rows']); atomic_write(args.out, dumps(out))


if __name__ == '__main__': main()
