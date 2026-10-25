#!/usr/bin/env python3
"""Run339 independent read-only raw-score and source receipt audit.

No native optimizer replay or tensor-byte inspection; the original native
Run333 tensor audit remains the only evidence for real selected-only deltas.
"""
import argparse
import json
import math
from pathlib import Path

import native_c3_contrastive_run339 as R
from audit_native_c3_freshcohort_run334 import digest, valid_sha

SCHEMA = 'V13_RUN339_INDEPENDENT_CONTRASTIVE_RAW_SCORE_AUDIT_V1'


def require(cond, message):
    if not cond:
        raise ValueError(message)


def recompute(row, data):
    groups = (('facts', data['facts'], 'keys', 'ok'),
              ('paraphrases', data['paraphrases'], 'keys', 'ok'),
              ('near_miss', data['near_miss'], 'leak_keys', 'leak'),
              ('probes', R.old.PROBES, 'expect', 'ok'))
    require([len(row.get(name, [])) for name, _, _, _ in groups] == [8, 6, 5, 12],
            'Run339 raw denominator')
    scores = {}
    invalid = 0
    for name, items, key_name, flag in groups:
        scores[name] = []
        for observed, expected in zip(row[name], items):
            q = expected.get('q', expected.get('prompt'))
            require(observed.get('q') == q and type(observed.get('a')) is str,
                    'Run339 raw question/order/answer')
            answer = observed['a']
            ok = R.old.hit(answer, expected[key_name])
            strict = R.old.hit(R.old.first_sentence(answer), expected[key_name])
            require(observed.get(flag) == ok and observed.get('strict') == strict,
                    'Run339 raw label drift')
            if name == 'near_miss':
                require(observed.get('abstain') == R.abstain(answer),
                        'Run339 near-miss abstention label drift')
            invalid += answer == R.old.INVALID
            scores[name].append((ok, strict))
    expected = {
        'facts_strict': sum(x[1] for x in scores['facts']),
        'paraphrases_strict': sum(x[1] for x in scores['paraphrases']),
        'near_miss_leak_strict': round(sum(x[1] for x in scores['near_miss']) / 5, 3),
        'near_miss_abstain_strict': sum(x['abstain'] for x in row['near_miss']),
        'probes_ok': sum(x[0] for x in scores['probes']),
        'invalid_outputs': invalid,
        'facts_n': 8, 'paraphrases_n': 6, 'near_miss_n': 5, 'probes_n': 12,
    }
    require(row.get('summary') == expected and row.get('invalid_outputs') == invalid,
            'Run339 raw summary mismatch')
    return expected


def audit(report, root):
    data = R.cohort()
    require(report.get('schema') == R.SCHEMA
            and report.get('status') == 'COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC'
            and report.get('evidence_level') == 'LINUX_NATIVE_C3_FRESH_CONTRASTIVE_TRAIN_EVAL',
            'Run339 native run incomplete')
    require(report.get('cohort_sha256') == R.COHORT_SHA
            and report.get('master_sha256') == R.MASTER_SHA
            and report.get('hf_repo') == R.HF_REPO
            and report.get('hf_revision') == R.HF_REVISION
            and report.get('train') == R.TRAIN and report.get('criteria') == R.CRITERIA,
            'Run339 frozen source/cohort/train/threshold drift')
    require(report.get('gates') == R.GATES
            and report.get('weights_published') is False
            and report.get('model_activated') is False,
            'Run339 original negative gates or activation changed')
    require(report.get('anchors_count') == 6 and valid_sha(report.get('baseline_q4_sha256')),
            'Run339 anchor or baseline quant receipt')
    require(set(report.get('arms', {})) == set(R.ARMS), 'Run339 fixed three arms')
    base = report.get('baseline', {})
    recompute(base, data)
    details = {}
    for name, (contrastive, replay) in R.ARMS.items():
        arm = report['arms'][name]
        require(arm.get('loss_mode') == 'answer'
                and arm.get('contrastive') is contrastive
                and arm.get('replay') is replay
                and arm.get('status') == 'COMPLETE_NATIVE_DIAGNOSTIC'
                and arm.get('native_training_executed') is True
                and arm.get('train_exit') == 0
                and arm.get('weights_published') is False
                and arm.get('weights_retained') is False,
                'Run339 arm mode/native execution/weight publication')
        stream = Path(root)/(name+'.train.txt')
        require(stream.is_file() and not stream.is_symlink()
                and digest(stream) == arm.get('train_stream_sha256'),
                'Run339 train stream missing or hash mismatch')
        for kind in ('stdout', 'stderr'):
            p = Path(root)/name/('train.'+kind+'.log')
            require(p.is_file() and not p.is_symlink()
                    and digest(p) == arm.get('train_'+kind+'_sha256'),
                    'Run339 train log missing or hash mismatch')
        receipts = arm.get('checkpoint_receipts')
        epochs = arm.get('epochs')
        require(isinstance(receipts, list) and len(receipts) == 2
                and isinstance(epochs, list) and len(epochs) == 2,
                'Run339 exact two epoch receipts')
        for i, (receipt, epoch) in enumerate(zip(receipts, epochs), 1):
            require(receipt.get('epoch') == i and epoch.get('epoch') == i
                    and valid_sha(receipt.get('sha256'))
                    and receipt.get('sha256') == epoch.get('source_sha256')
                    and valid_sha(epoch.get('q4_sha256')),
                    'Run339 epoch/source/quant receipt mismatch')
            recompute(epoch.get('evaluation', {}), data)
        require(arm.get('final_master_sha256') == receipts[-1]['sha256'],
                'Run339 final master checkpoint mismatch')
        selection = R.select(base, [x['evaluation'] for x in epochs])
        require(arm.get('selection_report') == selection,
                'Run339 selection or heldout threshold drift')
        tensor = arm.get('tensor_audit', {})
        changes = tensor.get('changes', {})
        require(changes.get('unchanged_nonselected') == 144
                and changes.get('changed_epoch1') and changes.get('changed_epoch2'),
                'Run339 selected-only/nonzero native tensor receipt')
        require(tensor.get('metadata_modes') == ['EXPLICIT_F32', 'OMITTED_EPOCH_ONLY', 'OMITTED_EPOCH_ONLY'],
                'Run339 unexpected GGUF metadata mode')
        metrics = tensor.get('metrics', {})
        for stage in ('baseline_to_epoch1', 'epoch1_to_epoch2'):
            rows = metrics.get(stage, {})
            require(len(rows) == 4 and
                    any(v.get('changed_elements', 0) > 0 and v.get('l2', 0) > 0 for v in rows.values())
                    and all(math.isfinite(v.get('l2', float('nan')))
                            and math.isfinite(v.get('max_abs', float('nan')))
                            for v in rows.values()),
                    'Run339 numerical selected delta receipt invalid')
        details[name] = {'selection': selection['selection'],
                         'selected_epoch': selection['selected_epoch'],
                         'epoch1': selection['rows'][0],
                         'epoch2': selection['rows'][1],
                         'unchanged_nonselected': 144}
    return {'schema': SCHEMA,
            'status': 'PASS_SOURCE_ONLY_REPORT_AUDIT_NOT_NATIVE_REEXECUTION',
            'cohort_sha256': R.COHORT_SHA, 'master_sha256': R.MASTER_SHA,
            'arms': details, 'gates': R.GATES,
            'model_activated': False, 'weights_published': False,
            'claim_limit': 'Stored raw/report consistency only; near-miss abstention trained-set B/C, not unseen generalization; original native GGUF audit separate'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    try:
        result = audit(json.loads(args.report.read_text()), args.root)
    except (ValueError, OSError, TypeError, KeyError, AssertionError) as exc:
        result = {'schema': SCHEMA, 'status': 'FAIL_CLOSED',
                  'error': type(exc).__name__+': '+str(exc)[:350],
                  'model_activated': False, 'weights_published': False, 'gates': R.GATES}
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2)+'\n')
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result['status'] == 'PASS_SOURCE_ONLY_REPORT_AUDIT_NOT_NATIVE_REEXECUTION' else 2)

if __name__ == '__main__':
    main()
