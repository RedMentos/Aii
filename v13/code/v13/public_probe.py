"""Closed public-console view for native probe diagnostics.

The complete probe artifact stays local and source-bound. This module exposes
only fixed labels, bounded numeric metrics and opaque digests to console paths.
"""

def public_probe_summary(report):
    """Return a closed-grammar console view; never echo untrusted diagnostic strings."""
    if type(report) is not dict or report.get('proof_kind') != 'NATIVE_SMOKE':
        raise ValueError('Expected a native smoke report')

    import math

    roles = frozenset({'C2_CONTROL', 'C3_LANGUAGE', 'B1_DETAIL', 'B2_GIST'})
    top_statuses = frozenset({'SMOKE_PASS', 'SMOKE_PARTIAL', 'SMOKE_ERROR'})
    metric_statuses = frozenset({
        'FINAL', 'TIME_BUDGET', 'DEADLINE', 'CANCELLED', 'ERROR',
        'UNAVAILABLE', 'SKIPPED', 'RUNNING',
    })
    phases = frozenset({'load', 'template', 'prefill', 'stream'})
    error_kinds = frozenset({
        'ERROR', 'TIMEOUT', 'DEADLINE', 'CANCELLED', 'UNAVAILABLE',
        'PERMISSION_ERROR', 'PROBE_ERROR',
    })
    duration_keys = frozenset({
        'load_s', 'template_s', 'prefill_to_first_token_s', 'stream_s',
    })
    admission_revision = 'v13.native-prompt-admission/1'
    admission_statuses = frozenset({'ADMITTED', 'UNSATISFIED'})
    removed_layers = frozenset({
        'C3_LAYER_TASK_CONTEXT', 'C3_LAYER_DIGEST', 'C3_LAYER_USER_MODEL',
        'OLD_NATIVE_HISTORY', 'BODY_SOURCE_ADDRESS_METADATA',
        'BODY_DUPLICATE_EXECUTIVE_SOURCE_REFS',
    })
    missing_proof_codes = {
        'sustained thermal/energy': 'SUSTAINED_THERMAL_ENERGY',
        'target-phone RSS/KV growth under pressure': 'TARGET_PHONE_RSS_KV_PRESSURE',
        'native sparse body training': 'NATIVE_SPARSE_BODY_TRAINING',
        'B3 receiver-effect ablations': 'B3_RECEIVER_EFFECT_ABLATIONS',
        'long-term retention': 'LONG_TERM_RETENTION',
    }
    safe_proof_codes = frozenset(missing_proof_codes.values())

    def number(value):
        if type(value) not in (int, float):
            return False
        try:
            n = float(value)
        except (OverflowError, ValueError):
            return False
        return math.isfinite(n) and 0 <= n <= 1e12

    def count(value):
        return type(value) is int and 0 <= value <= 1_000_000_000

    def digest(value):
        return (type(value) is str and len(value) == 64
                and all(ch in '0123456789abcdef' for ch in value))

    def metric_view(metrics):
        if type(metrics) is not dict:
            return {}
        out = {}
        value = metrics.get('status')
        if type(value) is str and value in metric_statuses:
            out['status'] = value
        value = metrics.get('role')
        if type(value) is str and value in roles:
            out['role'] = value
        value = metrics.get('last_phase')
        if type(value) is str and value in phases:
            out['last_phase'] = value
        value = metrics.get('error_kind')
        if type(value) is str and value in error_kinds:
            out['error_kind'] = value
        for key in (
            'prompt_tokens', 'generated_tokens', 'requested_tokens',
            'input_message_count', 'duration_s', 'ttft_s',
            'elapsed_in_last_phase_s', 'tokens_per_second',
            'n_ctx', 'n_batch', 'threads', 'context_tokens',
        ):
            value = metrics.get(key)
            if number(value):
                out[key] = value
        durations = metrics.get('stage_durations_s')
        if type(durations) is dict:
            out['stage_durations_s'] = {
                key: value for key, value in durations.items()
                if key in duration_keys and number(value)
            }
        admission = metrics.get('prompt_admission')
        if type(admission) is dict:
            safe_admission = {}
            if admission.get('revision') == admission_revision:
                safe_admission['revision'] = admission_revision
            value = admission.get('status')
            if type(value) is str and value in admission_statuses:
                safe_admission['status'] = value
            for key in ('original_prompt_tokens', 'prompt_tokens', 'target_tokens'):
                value = admission.get(key)
                if number(value):
                    safe_admission[key] = value
            if type(admission.get('source_text_rewritten')) is bool:
                safe_admission['source_text_rewritten'] = admission['source_text_rewritten']
            layers = admission.get('removed_layers')
            if type(layers) is list:
                safe_admission['removed_layers'] = [
                    value for value in layers
                    if type(value) is str and value in removed_layers
                ][:32]
            out['prompt_admission'] = safe_admission
        return out

    safe_roles = {}
    raw_roles = report.get('roles')
    if type(raw_roles) is dict:
        for role in roles:
            entry = raw_roles.get(role)
            if type(entry) is not dict:
                continue
            safe = {}
            if type(entry.get('ok')) is bool:
                safe['ok'] = entry['ok']
            if number(entry.get('duration_s')):
                safe['duration_s'] = entry['duration_s']
            if type(entry.get('metrics')) is dict:
                safe['metrics'] = metric_view(entry['metrics'])
            if 'error' in entry:
                safe['error_kind'] = 'ERROR'
            offer = entry.get('structured_offer')
            if type(offer) is dict:
                safe['offer'] = {
                    'present': True,
                    'verified_quote_count': offer.get('verified_quote_count', 0)
                        if count(offer.get('verified_quote_count')) else 0,
                    'rejected_quote_count': offer.get('rejected_quote_count', 0)
                        if count(offer.get('rejected_quote_count')) else 0,
                }
            if count(entry.get('embedding_dim')):
                safe['embedding_dim'] = entry['embedding_dim']
            if number(entry.get('embedding_squared_norm')):
                safe['embedding_squared_norm'] = entry['embedding_squared_norm']
            if digest(entry.get('embedding_hash')):
                safe['embedding_hash'] = entry['embedding_hash']
            if type(entry.get('confidence_calibrated')) is bool:
                safe['confidence_calibrated'] = entry['confidence_calibrated']
            safe_roles[role] = safe

    config = report.get('effective_config')
    safe_config = {}
    if type(config) is dict:
        for key in (
            'answer_tokens', 'body_residency_mb', 'context_tokens',
            'control_seconds', 'deadline_seconds', 'observer_seconds',
            'observer_tokens', 'output_adapter_seconds', 'retrieval_seconds',
            'threads',
        ):
            value = config.get(key)
            if number(value):
                safe_config[key] = value

    revisions = report.get('model_revisions')
    safe_revisions = {}
    if type(revisions) is dict:
        safe_revisions = {
            role: value for role, value in revisions.items()
            if role in roles and digest(value)
        }

    missing = report.get('missing_proofs')
    safe_missing = []
    if type(missing) is list:
        for value in missing:
            code = missing_proof_codes.get(value) if type(value) is str else None
            if code is None and type(value) is str and value in safe_proof_codes:
                code = value
            if code is not None and code not in safe_missing:
                safe_missing.append(code)
            if len(safe_missing) >= 32:
                break

    status = report.get('status')
    return {
        'schema': 'v13.public-native-probe/1',
        'proof_kind': 'NATIVE_SMOKE',
        'status': status if type(status) is str and status in top_statuses else 'UNKNOWN',
        'phone_measured': report.get('phone_measured') if type(report.get('phone_measured')) is bool else False,
        'full_runner_proof': report.get('full_runner_proof') if type(report.get('full_runner_proof')) is bool else False,
        'model_revisions': safe_revisions,
        'effective_config': safe_config,
        'roles': safe_roles,
        'missing_proofs': safe_missing,
        'raw_artifact': 'exports/native-probe.json',
        'redaction': {
            'model_outputs': 'REDACTED_FROM_CONSOLE',
            'body_offer_hypotheses': 'REDACTED_FROM_CONSOLE',
            'control_payloads': 'REDACTED_FROM_CONSOLE',
            'raw_artifact_retained_locally': True,
        },
    }

def public_probe_error_report():
    """Constant error receipt; never serialize exception or runner stderr text."""
    return {
        'schema': 'v13.public-native-probe/1',
        'proof_kind': 'NATIVE_SMOKE',
        'status': 'SMOKE_ERROR',
        'phone_measured': False,
        'full_runner_proof': False,
        'model_revisions': {},
        'effective_config': {},
        'roles': {},
        'missing_proofs': ['PROBE_EXECUTION_ERROR'],
    }


def public_probe_error_telemetry():
    """Fixed telemetry record for a failed probe; no exception message."""
    return {'kind': 'probe', 'error': 'PROBE_ERROR'}
