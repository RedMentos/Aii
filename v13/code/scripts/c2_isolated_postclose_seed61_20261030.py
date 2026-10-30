"""Preregistered seed61: disjoint isolated-final-role Body/C2 native utility cohort.

Fresh Age0 homes; native release receipts are captured after Runtime.close().
Never alter original seed53/59, their raw rows, or STEP2/JEPA/B3 gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import time
import traceback

from v13.cognition import scaffold_route
from v13.config import initialize, save_config
from v13.models import ModelManager, model_key
from v13.proofs import audit_event
from v13.runtime import Runtime
from scripts.c2_body_controlled_utility_seed53_20261030 import (
    score_pair, valid_control_evidence, BODY_MODEL, GIST_MODEL, LANGUAGE_MODEL,
)

SCHEMA = "v13.c2_body.isolated_postclose.seed61.v1"
SEED = 61
ARMS = ("A_C3_ONLY", "B_B1_ONLY", "C_B2_ONLY", "D_DISTINCT_BOTH",
        "E_SHARED_DUAL_COLD", "F_NATIVE_AUTO")
ARM_ORDER = tuple(ARMS[i:] + ARMS[:i] for i in range(4))
FIXTURES = (
    {"project": "Birch61", "budget": 391, "a": "Maple", "a_cost": 238, "a_days": 6,
     "b": "Finch", "b_cost": 329, "b_days": 3},
    {"project": "Delta61", "budget": 308, "a": "Rowan", "a_cost": 174, "a_days": 4,
     "b": "Quartz", "b_cost": 269, "b_days": 9},
    {"project": "Mosaic61", "budget": 463, "a": "Slate", "a_cost": 286, "a_days": 8,
     "b": "Pearl", "b_cost": 378, "b_days": 5},
    {"project": "Nova61", "budget": 347, "a": "Cypress", "a_cost": 201, "a_days": 7,
     "b": "Lumen", "b_cost": 288, "b_days": 2},
)
FIXTURE_SHA256 = "bf4c4da0de4c79bb66555f6e442fe9daacb0affa34b4cf9126bb51d4a83e5bf3"
ROUTES = {"A_C3_ONLY": "simple", "B_B1_ONLY": "detail", "C_B2_ONLY": "gist",
          "D_DISTINCT_BOTH": "both", "E_SHARED_DUAL_COLD": "both", "F_NATIVE_AUTO": "auto"}
FINAL_ROLES = {"simple": ("C3_LANGUAGE",), "detail": ("B1_DETAIL",),
               "gist": ("B2_GIST",), "both": ("B1_DETAIL", "B2_GIST")}
BODY_ROLES = {"B1_DETAIL", "B2_GIST"}


def fixture_hash():
    return hashlib.sha256(json.dumps(FIXTURES, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def prompt(f):
    return (f"For {f['project']}, I have a spending ceiling of {f['budget']} Euro. "
            f"{f['a']} uses {f['a_cost']} Euro and needs {f['a_days']} days. "
            f"{f['b']} uses {f['b_cost']} Euro and needs {f['b_days']} days. "
            "Everything stays local on my device; no cloud. How many Euro "
            "would remain after each named choice, and which one finishes sooner?")


def validate_fixtures():
    if fixture_hash() != FIXTURE_SHA256 or len(FIXTURES) != 4:
        raise ValueError("FIXTURE_PIN_CHANGED")
    if len(set(f['project'] for f in FIXTURES)) != 4 or len(set(ARMS)) != 6:
        raise ValueError("IDENTITY_COLLISION")
    for f in FIXTURES:
        if scaffold_route(prompt(f)) != "simple":
            raise ValueError("SCAFFOLD_NOT_SIMPLE")
        if not (0 < f['a_cost'] < f['budget'] and 0 < f['b_cost'] < f['budget']
                and f['a'] != f['b'] and f['a_days'] != f['b_days']):
            raise ValueError("INVALID_FIXTURE")
        for remainder in (f['budget']-f['a_cost'], f['budget']-f['b_cost']):
            if re.search(rf"(?<!\d){remainder}(?!\d)", prompt(f)):
                raise ValueError("ANSWER_LEAKED_IN_PROMPT")
    return True


def expected_offers(arm, route):
    if arm in ARMS[:3]:
        return set()
    return set(FINAL_ROLES.get(route, ())) & BODY_ROLES


def role_model(role, shared):
    if role == "C3_LANGUAGE":
        return LANGUAGE_MODEL
    if role == "B2_GIST" and not shared:
        return GIST_MODEL
    if role in BODY_ROLES:
        return BODY_MODEL
    raise ValueError("UNKNOWN_FINAL_ROLE")


def row_evidence(audit, arm, preclose, postclose, *, native_context=None,
                 native_alive=False, native_reaped=False, native_pid=None,
                 source_exact=False, session=None, event_id=None, source_text=None):
    """Fail-closed: final role isolation, offers, and actual post-close reaping."""
    meta = audit.get('output_metadata') if isinstance(audit, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    route_info = meta.get('route') if isinstance(meta.get('route'), dict) else {}
    c2 = meta.get('c2_packet') if isinstance(meta.get('c2_packet'), dict) else {}
    route = c2.get('route')
    runner = meta.get('runner') if isinstance(meta.get('runner'), dict) else {}
    checks = audit.get('checks') if isinstance(audit, dict) else None
    checks_ok = bool(isinstance(checks, dict) and checks and
                     all(v is True for v in checks.values()) and audit.get('source_errors') == [])
    offers = [p.get('role') for p in audit.get('offers', []) if isinstance(p, dict)] if isinstance(audit, dict) else []
    offer_roles = set(offers)
    required = expected_offers(arm, route)
    observer_ok = offer_roles == required and (not offers if arm in ARMS[:3] else True)
    native = False
    if arm == 'F_NATIVE_AUTO' and isinstance(native_context, dict):
        e = {'event_id': event_id, 'session_id': session,
             'source_ref': native_context.get('query_ref')}
        metrics = route_info.get('native_control_metrics') or {}
        memory = metrics.get('memory') if isinstance(metrics, dict) else {}
        memory = memory if isinstance(memory, dict) else {}
        native = bool(source_exact and native_alive and native_reaped
                      and type(native_pid) is int and native_pid == memory.get('pid')
                      and valid_control_evidence(e, source_text, route, route_info,
                                                 context_packet=native_context))
    selected = bool(native and route_info.get('source') == 'NATIVE_C2_ADVISORY')
    route_ok = (route == ROUTES[arm] and route_info == {'source': 'OPERATOR_ROUTE_OVERRIDE'}) if arm != 'F_NATIVE_AUTO' else (
        native and route in FINAL_ROLES and
        route_info.get('source') in ('BOOT_SCAFFOLD', 'NATIVE_C2_ADVISORY'))
    final_role = runner.get('role')
    final_model = runner.get('actual_model')
    shared = arm == 'E_SHARED_DUAL_COLD'
    final_ok = (final_role in FINAL_ROLES.get(route, ()) and
                final_model == role_model(final_role, shared)) if final_role in ('C3_LANGUAGE', *BODY_ROLES) else False
    pre = [x for x in preclose if isinstance(x, dict)]
    post = [x for x in postclose if isinstance(x, dict)]
    post_roles = {x.get('role') for x in post}
    # Every role which actually offered or produced FINAL must have a reaped
    # receipt, including final-role reuse which may only unload in close().
    needed = required | {final_role}
    # Exact process identity, not just role labels: a post-close release must
    # match the FINAL runner PID and every source-bound OfferPacket runner PID.
    receipts = {(x.get('role'), (x.get('before') or {}).get('pid')) for x in post}
    final_memory = runner.get('memory') if isinstance(runner.get('memory'), dict) else {}
    final_pid = final_memory.get('pid')
    offer_pids = set()
    for offer in audit.get('offers', []) if isinstance(audit, dict) else []:
        native_metrics = offer.get('native_metrics') if isinstance(offer, dict) else None
        native_memory = native_metrics.get('memory') if isinstance(native_metrics, dict) else None
        pid = native_memory.get('pid') if isinstance(native_memory, dict) else None
        offer_pids.add((offer.get('role'), pid))
    release_ok = bool(post and needed <= post_roles and
                      type(final_pid) is int and (final_role, final_pid) in receipts and
                      all(type(pid) is int and (role, pid) in receipts for role, pid in offer_pids) and
                      all(x.get('process_reaped') is True for x in post) and
                      not (post_roles & BODY_ROLES) - (needed & BODY_ROLES) and
                      all(x in post for x in pre))
    if arm in ARMS[:3]:
        # No observer body in a single-final-role arm; only the final model may run.
        release_ok = release_ok and not (post_roles & BODY_ROLES) - ({final_role} & BODY_ROLES)
    output_ok = bool(checks_ok and meta.get('model_generated') is True and
                     isinstance(audit.get('output'), str) and audit['output'].strip() and final_ok)
    valid = bool(route_ok and observer_ok and release_ok and output_ok)
    return {'valid_native': valid, 'route_valid': bool(route_ok),
            'native_c2_invocation': native, 'native_c2_selected': selected,
            'source_exact': bool(source_exact) if arm == 'F_NATIVE_AUTO' else checks_ok,
            'observer_isolated': observer_ok, 'postclose_release_valid': release_ok,
            'body_offer_roles': sorted(offer_roles), 'expected_offer_roles': sorted(required),
            'preclose_release_roles': [x.get('role') for x in pre],
            'postclose_release_roles': [x.get('role') for x in post],
            'final_runner_pid': final_pid, 'final_pid_reaped': (final_role, final_pid) in receipts,
            'offer_pid_count': len(offer_pids),
            'output_valid': output_ok, 'runner_role': final_role,
            'runner_model': final_model, 'route': route,
            'route_source': route_info.get('source')}


def pilot_signals(totals, valid, selected):
    if type(valid) is not bool or type(selected) is not int or type(totals) is not dict or set(totals) != set(ARMS):
        return {'distinct_vs_single_shared': False, 'native_auto_vs_forced': False}
    if any(type(v) is not int or v < 0 or v > 8 for v in totals.values()):
        return {'distinct_vs_single_shared': False, 'native_auto_vs_forced': False}
    return {
        'distinct_vs_single_shared': bool(valid and totals['D_DISTINCT_BOTH'] >=
             max(totals[k] for k in ARMS[:3]) + 2 and
             totals['D_DISTINCT_BOTH'] >= totals['E_SHARED_DUAL_COLD'] + 2),
        'native_auto_vs_forced': bool(valid and selected >= 1 and
             totals['F_NATIVE_AUTO'] >= max(totals['A_C3_ONLY'], totals['D_DISTINCT_BOTH']) + 2),
    }


def fresh_turn(base_home, base_cfg, fixture, arm, index, out):
    text = prompt(fixture)
    with tempfile.TemporaryDirectory(dir=base_home / 'tmp', prefix='c2-isolated-seed61-') as td:
        home = Path(td)
        cfg = initialize(home)
        cfg.update(base_cfg)
        cfg.update(learning_mode='RECORD_ONLY', system_stage=0, user_stage_cap=0,
                   teacher_enabled=False, latents_enabled=False, jepa_weight=0,
                   seed=SEED, history_turns=0, route_override=ROUTES[arm],
                   observer_mode=('off' if arm in ARMS[:3] else 'background'),
                   b2_control=('shared_body_dual_state' if arm == 'E_SHARED_DUAL_COLD' else 'two_body'),
                   control_seconds=20.0)
        save_config(home, cfg)
        for name in ('models', 'bin'):
            shutil.rmtree(home / name)
            (home / name).symlink_to(base_home / name, target_is_directory=True)
        shutil.copyfile(base_home / 'config/models.json', home / 'config/models.json')
        runtime = Runtime(home)
        if runtime.models.b2_control != cfg['b2_control']:
            runtime.close()
            raise ValueError('B2_CONTROL_CONFIG_MISMATCH')
        record = None
        needle_proc = None
        postclose = None
        try:
            if arm == 'A_C3_ONLY':
                runtime.models.installed.pop('body', None)
                runtime.models.installed.pop('gist', None)
                runtime.models.save()
            event_id = runtime.submit(text)
            end = time.monotonic() + runtime.cfg['deadline_seconds'] + 2 * runtime.cfg['observer_seconds'] + 15
            while not runtime.idle():
                if time.monotonic() > end:
                    runtime.cancel()
                    raise TimeoutError('NATIVE_ISOLATED_TURN_DEADLINE')
                time.sleep(.05)
            audit = audit_event(runtime.store, event_id)
            meta = audit.get('output_metadata') or {}
            route_info = meta.get('route') or {}
            context_id = route_info.get('executive_control_context_id')
            row = (runtime.store.one("SELECT payload FROM packets WHERE id=? AND kind='ExecutiveControlContext'",
                                     (context_id,)) if context_id else None)
            context = json.loads(row['payload']) if row else None
            source_exact = bool(context and runtime.store.read_source(context['query_ref']) == text)
            needle_proc = runtime.needle.proc
            needle_alive = needle_proc is not None and needle_proc.poll() is None
            record = {'index': index, 'fixture': fixture['project'], 'arm': arm,
                      'prompt': text, 'event_id': event_id, 'session_id': runtime.session,
                      'route_info': route_info, 'context_packet': context,
                      'observer_mode': cfg['observer_mode'],
                      'b2_control': runtime.models.b2_control,
                      'b1_model_key': model_key('B1_DETAIL', runtime.models.b2_control),
                      'b2_model_key': model_key('B2_GIST', runtime.models.b2_control),
                      'b1_revision': runtime.models.revision('B1_DETAIL'),
                      'b2_revision': runtime.models.revision('B2_GIST'),
                      'raw_audit': audit, 'preclose_releases': list(runtime.pool.release_history),
                      'final_output': audit.get('output', ''),
                      'learning_mode': 'RECORD_ONLY', 'jepa_weight': 0,
                      'step2_gate_promoted': False, 'b3_promoted': False,
                      'body_jepa_available': False, 'redmi_measured': False,
                      'whole_system_complete': False,
                      '_native_alive_before_close': needle_alive,
                      '_source_exact_before_close': source_exact}
        finally:
            runtime.close()
            postclose = list(runtime.pool.release_history)
        if record is None:
            raise ValueError('MISSING_NATIVE_ROW')
        record['postclose_releases'] = postclose
        record['native_c2_process_reaped'] = bool(needle_proc is not None and needle_proc.poll() is not None)
        record['native_c2_pid'] = needle_proc.pid if needle_proc is not None else None
        record['native_c2_alive_before_close'] = record.pop('_native_alive_before_close')
        record['native_c2_source_exact_before_close'] = record.pop('_source_exact_before_close')
        flags = row_evidence(record['raw_audit'], arm, record['preclose_releases'], postclose,
                             native_context=record['context_packet'],
                             native_alive=record['native_c2_alive_before_close'],
                             native_reaped=record['native_c2_process_reaped'],
                             native_pid=record['native_c2_pid'],
                             source_exact=record['native_c2_source_exact_before_close'],
                             session=record['session_id'], event_id=record['event_id'],
                             source_text=text)
        record['flags'] = flags
        record['score'] = (score_pair(fixture, record['final_output'])
                           if flags['valid_native'] else {'a': False, 'b': False,
                                                          'correct': 0, 'out_of': 2})
        (out / 'raw' / f'{index:02d}_{arm}.json').write_text(
            json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
        return {k: v for k, v in record.items() if k not in
                ('raw_audit', 'context_packet', 'prompt', 'route_info')}


def run(base_home, out):
    base_home, out = Path(base_home).resolve(), Path(out).resolve()
    if out.exists():
        raise FileExistsError('FRESH_OUTPUT_DIRECTORY_REQUIRED')
    validate_fixtures()
    out.mkdir(parents=True)
    (out / 'raw').mkdir()
    report = {'schema': SCHEMA, 'status': 'INCOMPLETE', 'seed': SEED,
              'fixture_sha256': FIXTURE_SHA256, 'fixtures': FIXTURES,
              'arms': ARMS, 'arm_order': ARM_ORDER, 'rows': [],
              'learning_mode': 'RECORD_ONLY', 'jepa_weight': 0,
              'step2_gate_promoted': False, 'b3_promoted': False,
              'body_jepa_available': False, 'redmi_measured': False,
              'whole_system_complete': False, 'comparative_utility_proven': False,
              'claim_limit': '24-turn small Linux-native seed61 pilot; not STEP2 gate'}
    try:
        cfg = initialize(base_home)
        if cfg['learning_mode'] != 'RECORD_ONLY' or cfg['system_stage'] != 0 or cfg['latents_enabled'] or cfg.get('jepa_weight', 0) != 0:
            raise ValueError('BASE_NOT_AGE0')
        verified = ModelManager(base_home).verify(deep=True)
        roles = ('needle', 'language', 'body', 'gist')
        if not all(verified.get(k, {}).get('ok') is True and
                   verified[k].get('hash_checked') is True for k in roles):
            raise ValueError('MODEL_PINS_UNVERIFIED')
        report['model_verification'] = {k: {'ok': verified[k]['ok'],
                                            'hash_checked': verified[k]['hash_checked']} for k in roles}
        for i, fixture in enumerate(FIXTURES):
            for arm in ARM_ORDER[i]:
                index = len(report['rows'])
                try:
                    row = fresh_turn(base_home, cfg, fixture, arm, index, out)
                except BaseException as exc:
                    traceback.print_exc()
                    row = {'index': index, 'fixture': fixture['project'], 'arm': arm,
                           'error_type': type(exc).__name__, 'error': str(exc)[:320],
                           'flags': {'valid_native': False, 'native_c2_invocation': False,
                                     'native_c2_selected': False},
                           'score': {'a': False, 'b': False, 'correct': 0, 'out_of': 2}}
                    (out / 'raw' / f'{index:02d}_{arm}.json').write_text(
                        json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')
                report['rows'].append(row)
                (out / 'progress.json').write_text(json.dumps(report, indent=2, sort_keys=True,
                                                   ensure_ascii=False, allow_nan=False) + '\n')
        totals = {arm: sum(row['score']['correct'] for row in report['rows'] if row['arm'] == arm)
                  for arm in ARMS}
        valid = len(report['rows']) == 24 and all(
            row['flags'].get('valid_native') is True for row in report['rows'])
        selected = sum(bool(row['flags'].get('native_c2_selected')) for row in report['rows']
                       if row['arm'] == 'F_NATIVE_AUTO')
        report['score_totals_out_of_8'] = totals
        report['native_c2_invocations'] = sum(bool(row['flags'].get('native_c2_invocation'))
                                              for row in report['rows'] if row['arm'] == 'F_NATIVE_AUTO')
        report['native_c2_selected'] = selected
        report['pilot_signals_not_gates'] = pilot_signals(totals, valid, selected)
        report['status'] = 'PILOT_COMPLETE_NO_GATE' if valid else 'PILOT_PARTIAL_RED'
    except BaseException as exc:
        traceback.print_exc()
        report.update(status='PILOT_ERROR', error_type=type(exc).__name__, error=str(exc)[:320])
    finally:
        (out / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True,
                                           ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'status': report['status'], 'scores': report.get('score_totals_out_of_8'),
                      'native_c2_selected': report.get('native_c2_selected', 0),
                      'signals_not_gates': report.get('pilot_signals_not_gates', {})}, sort_keys=True))
    return report['status'] == 'PILOT_COMPLETE_NO_GATE'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    return 0 if run(a.home, a.out) else 2


if __name__ == '__main__':
    raise SystemExit(main())