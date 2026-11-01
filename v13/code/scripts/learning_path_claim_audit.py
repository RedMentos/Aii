"""Read-only, source-bound inspection of LoRA latent-alignment evidence.

This never runs a model or promotes a gate. A retrospectively supplied binding
ties audit inputs together; it does not prove which source produced an old run.
Only the reviewed trainer bytes have known semantics. Stdlib only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

SCHEMA = 'V13_LEARNING_PATH_AUDIT_V1'
SOURCE_SHA256 = '45ee09f701239d2a09285edcc970d87652e2cadc17f43bc3c4fe3b546d8895cb'
SOURCE_REVISION = 'v13-lora-trainer-v1'


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Input must be a regular non-symlink file')
    return path.read_bytes()


def _json(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('Duplicate JSON key')
            out[key] = value
        return out
    value = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError('Expected a JSON object')
    return value


def _finite(value):
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def audit(trainer, manifest, binding=None):
    source_raw, manifest_raw = _read(trainer), _read(manifest)
    source_sha = hashlib.sha256(source_raw).hexdigest()
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    doc = _json(manifest_raw)
    metrics = doc.get('metrics')
    if not isinstance(metrics, dict):
        raise ValueError('Manifest requires a metrics object')
    errors = []
    notes = []
    def error(code):
        if code not in errors:
            errors.append(code)
    supported = source_sha == SOURCE_SHA256
    if not supported:
        error('UNSUPPORTED_SOURCE')
    if metrics.get('revision') != SOURCE_REVISION:
        error('UNSUPPORTED_MANIFEST_REVISION')
    dataset_hash = metrics.get('dataset_hash')
    if not isinstance(dataset_hash, str) or not re.fullmatch(r'[0-9a-f]{24}', dataset_hash):
        error('INVALID_DATASET_LABEL')
        dataset_hash = None
    binding_status = 'UNBOUND_HISTORICAL_RUN'
    input_binding_matches = None
    binding_sha = None
    if binding is not None:
        raw = _read(binding)
        binding_sha = hashlib.sha256(raw).hexdigest()
        bound = _json(raw)
        if bound.get('schema') != 'V13_LEARNING_PATH_AUDIT_INPUTS_V1':
            error('INVALID_BINDING_SCHEMA')
        for name, actual in (('trainer_sha256', source_sha), ('manifest_sha256', manifest_sha),
                             ('dataset_hash', dataset_hash)):
            if actual is None or bound.get(name) != actual:
                error('BINDING_MISMATCH_' + name.upper())
        input_binding_matches = not any(code.startswith(('BINDING_MISMATCH_', 'INVALID_BINDING_')) for code in errors)
        binding_status = 'MATCHED_AUDIT_INPUTS' if input_binding_matches else 'BINDING_REJECTED'

    weight = metrics.get('jepa_weight')
    weight_ok = _finite(weight) and weight >= 0
    if not weight_ok:
        error('INVALID_OR_MISSING_JEPA_WEIGHT')
    steps = metrics.get('steps')
    if type(steps) is not int or steps < 0:
        error('INVALID_OR_MISSING_STEPS')
    count = metrics.get('trainable_parameter_count')
    if type(count) is not int or count < 0:
        error('INVALID_OR_MISSING_PARAMETER_COUNT')
    if 'anchor_weight' in metrics and (not _finite(metrics['anchor_weight']) or metrics['anchor_weight'] < 0):
        error('INVALID_ANCHOR_WEIGHT')
    before, after = metrics.get('body_jepa_cos_before'), metrics.get('body_jepa_cos_after')
    cosine_ok = all(_finite(x) and -1.00001 <= x <= 1.00001 for x in (before, after))
    if not cosine_ok:
        error('INVALID_OR_MISSING_COSINE')
    history = metrics.get('loss_history')
    history_status = 'NOT_RECORDED'
    if history is not None:
        if not isinstance(history, list):
            error('INVALID_HISTORY')
        else:
            history_status = 'REPORTED_COMPONENT_LOSSES_ONLY'
            if not history and type(steps) is int and steps > 0:
                error('EMPTY_HISTORY_WITH_REPORTED_STEPS')
                history_status = 'INCOMPLETE'
            previous = 0
            for row in history:
                if not isinstance(row, dict):
                    error('INVALID_HISTORY_ROW')
                    continue
                step = row.get('step')
                if type(step) is not int or step <= previous or type(steps) is not int or step > steps:
                    error('INVALID_HISTORY_STEP')
                else:
                    previous = step
                for key in ('ce', 'anchor_kl'):
                    if not _finite(row.get(key)):
                        error('INVALID_COMPONENT_LOSS')
                loss = row.get('jepa')
                if weight_ok and weight == 0 and loss is not None:
                    error('JEPA_LOSS_RECORDED_WHILE_DISABLED')
                elif weight_ok and weight > 0 and (not _finite(loss) or not -0.00001 <= loss <= 2.00001):
                    error('INVALID_OR_MISSING_JEPA_LOSS')
    else:
        notes.append('NO_COMPONENT_LOSS_HISTORY')
    if weight_ok and weight == 0:
        configured = 'DISABLED'
        notes.append('COSINE_CHANGE_CANNOT_ESTABLISH_JEPA_TRAINING')
    elif weight_ok:
        configured = 'CONFIGURED_POSITIVE_WEIGHT'
    else:
        configured = 'UNKNOWN'
    if steps == 0:
        notes.append('NO_OPTIMIZER_STEPS_REPORTED')
    if count == 0 and type(steps) is int and steps > 0:
        error('STEPS_WITHOUT_TRAINABLE_PARAMETERS')
    # Do not ingest claimed EMA/gradient/utility evidence from another path.
    if any(key in doc for key in ('gradient_evidence', 'ema_evidence', 'utility_evidence')):
        notes.append('EXTERNAL_CLAIMS_NOT_VALIDATED_BY_THIS_AUDITOR')
    mechanism = None
    if supported:
        mechanism = {
            'objective': 'PROMPT_TO_FIXED_BASE_ANSWER_COSINE',
            'target': 'PRE_ADAPTER_BASE_ANSWER_TOKEN_MEAN',
            'target_stop_gradient': True,
            'target_ema_update': False,
            'separate_predictor': False,
            'trainable_parts': 'PEFT_LORA_PARAMETERS',
            'cosine_also_measured_when_jepa_disabled': True,
        }
    return {
        'schema': SCHEMA,
        'status': 'INPUT_REJECTED' if errors else 'AUDIT_REVIEW_ONLY',
        'errors': errors, 'notes': notes,
        'inputs': {'trainer_sha256': source_sha, 'manifest_sha256': manifest_sha,
                   'binding_sha256': binding_sha, 'dataset_hash_label': dataset_hash},
        'binding_status': binding_status,
        'input_binding_matches': input_binding_matches,
        'historical_run_source_verified': False,
        'dataset_bytes_verified': False,
        'source_mechanism': mechanism,
        'reported_run': {'jepa_configuration': configured,
                         'jepa_weight': weight if weight_ok else None,
                         'steps': steps if type(steps) is int and steps >= 0 else None,
                         'component_history': history_status,
                         'cosine_delta': round(after - before, 8) if cosine_ok else None},
        'jepa_component_gradient_contribution': 'UNMEASURED',
        'deployed_utility_attributable_to_jepa': 'UNMEASURED',
        'body_world_jepa_established': False,
        'activation_or_gate_changes': False,
        'claim_limit': 'Inspects reported configuration and known source semantics; no historical source attestation, model execution, gradient measurement or utility gate.',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trainer', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--binding')
    args = parser.parse_args(argv)
    try:
        report = audit(args.trainer, args.manifest, args.binding)
    except (ValueError, OSError, UnicodeError):
        report = {'schema': SCHEMA, 'status': 'INPUT_REJECTED',
                  'errors': ['UNREADABLE_OR_MALFORMED_INPUT'], 'activation_or_gate_changes': False}
    print(json.dumps(report, sort_keys=True, indent=2, allow_nan=False))
    return 2 if report['status'] == 'INPUT_REJECTED' else 0


if __name__ == '__main__':
    sys.exit(main())
