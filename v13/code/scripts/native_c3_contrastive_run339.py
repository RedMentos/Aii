#!/usr/bin/env python3
"""Run339 preregistered fresh contrastive C3 fact/near-miss native diagnostic.

Isolated synthetic training only. Never installs weights or changes V13 gates.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import time

import native_c3_freshcohort_run334 as old
from v13.common import atomic_write, dumps

SCHEMA = 'V13_RUN339_FRESH_C3_CONTRASTIVE_NATIVE_EPOCH_V1'
COHORT_SHA = '68c872c9666da20ef7e4f6c7fa6212fd859768948d1b4b3554eb46ff1684d731'
COHORT_PATH = (Path(__file__).resolve().parents[1] /
               'docs/proofs/continuation-20261025/run339-c3-contrastive-abstention/RUN339_FRESH_CONTRASTIVE_COHORT.json')
MASTER_SHA = old.MASTER_SHA
HF_REPO, HF_REVISION, LLAMA_SHA = old.HF_REPO, old.HF_REVISION, old.LLAMA_SHA
GATES = dict(old.GATES)
ARMS = {'A_ANSWER_FACTS_ONLY': (False, False),
        'B_ANSWER_FACTS_NEGATIVE': (True, False),
        'C_ANSWER_FACTS_NEGATIVE_REPLAY': (True, True)}
TRAIN = {'lr': 1e-5, 'epochs': 2, 'reps': 12, 'seed': 53,
         'threads': 4, 'ctx': 256, 'batch': 256, 'ubatch': 256}
CRITERIA = {'facts_strict_min': 4, 'paraphrases_strict_min': 2,
            'near_miss_leak_strict_max': 0.2, 'near_miss_abstain_strict_min': 3,
            'forgotten_baseline_probes_max': 0, 'invalid_outputs_max': 0}
ABSTAIN_PREFIXES = ('i do not know', "i don't know", 'unknown', 'not specified',
                    'cannot determine', 'i cannot determine')


def require(cond, message):
    if not cond:
        raise ValueError(message)


def cohort():
    require(old.digest(COHORT_PATH) == COHORT_SHA, 'Run339 frozen cohort SHA drift')
    data = json.loads(COHORT_PATH.read_text())
    require(data.get('schema') == 'V13_RUN339_FRESH_SYNTHETIC_C3_CONTRASTIVE_COHORT_V1'
            and data.get('seed') == TRAIN['seed']
            and data.get('authority') == 'SYNTHETIC_TEST_ONLY', 'Run339 cohort metadata')
    facts, para, near = (data[k] for k in ('facts', 'paraphrases', 'near_miss'))
    require((len(facts), len(para), len(near), len(old.PROBES)) == (8, 6, 5, 12),
            'Run339 frozen cohort denominator')
    for prefix, group in (('F', facts), ('P', para), ('N', near)):
        require([x.get('id') for x in group] == [prefix+str(i) for i in range(1,len(group)+1)],
                'Run339 cohort ID/order drift')
    questions = [x['q'] for group in (facts, para, near) for x in group]
    require(len(set(questions)) == len(questions), 'Run339 duplicate question')
    for x in facts:
        require(type(x.get('a')) is str and x['a'].strip() and
                type(x.get('keys')) is list and len(x['keys']) == 1 and
                x['keys'][0].lower() in x['a'].lower(), 'Run339 fact answer/key')
    for x in para:
        require(type(x.get('keys')) is list and len(x['keys']) == 1,
                'Run339 paraphrase key')
    for x in near:
        require(type(x.get('leak_keys')) is list and len(x['leak_keys']) == 1 and
                x['leak_keys'][0] not in x['q'].lower() and
                x['leak_keys'][0] not in x['a'].lower() and
                x['a'] == 'I do not know the answer for that fictional item.',
                'Run339 near-miss abstention target or leak')
    return data


def verify_sources(master, manifest):
    base = Path(old.__file__).resolve().parent
    for name in ('lora_bench.py', 'native_lfm2_finetune_bench.py', 'native_cache_bench.py'):
        require(old.digest(base/name) == old.PINNED_SHA[name],
                'Run339 frozen source drift: '+name)
    require(old.digest(master) == MASTER_SHA, 'Run339 exact FP32 master SHA')
    source = json.loads(Path(manifest).read_text())
    require(source.get('hf_repo') == HF_REPO and source.get('hf_revision') == HF_REVISION
            and source.get('master_sha256') == MASTER_SHA
            and source.get('llama_source_sha256') == LLAMA_SHA
            and source.get('conversion_outtype') == 'f32', 'Run339 model provenance')
    return cohort()


def make_stream(server, facts, near, contrastive, replay, anchors):
    """All answers are marked; only B/C include known near-miss abstention labels."""
    require(type(contrastive) is bool and type(replay) is bool and
            len(facts) == 8 and len(near) == 5 and len(anchors) in (0, 6)
            and (len(anchors) == 6) == replay, 'Run339 unregistered stream recipe')
    rng = random.Random(TRAIN['seed'])
    chunks = []
    for rep in range(TRAIN['reps']):
        rows = [(r['q'], r['a']) for r in facts]
        if contrastive:
            rows.extend((r['q'], r['a']) for r in near)
        if replay:
            rows.append(anchors[rep % len(anchors)])
        rng.shuffle(rows)
        for q, a in rows:
            prompt, answer, sep = old.turn(server, q, a)
            chunks.append(prompt + '\x01' + answer + '\x02' + sep)
    return ''.join(chunks)


def abstain(answer):
    sentence = old.first_sentence(answer).strip().casefold()
    return any(sentence.startswith(p) for p in ABSTAIN_PREFIXES)


def evaluate(server, model, log, data):
    result = old.evaluate(server, model, log, data)
    for row in result['near_miss']:
        row['abstain'] = abstain(row['a'])
    result['summary']['near_miss_abstain_strict'] = sum(x['abstain'] for x in result['near_miss'])
    return result


def select(base, epochs):
    require(len(base['probes']) == 12 and len(epochs) == 2,
            'Run339 baseline/epoch denominator')
    rows = []
    for i, row in enumerate(epochs, 1):
        require((len(row['facts']), len(row['paraphrases']), len(row['near_miss']),
                 len(row['probes'])) == (8, 6, 5, 12), 'Run339 epoch denominator')
        s = row['summary']
        forgotten = [x['q'] for x, y in zip(base['probes'], row['probes'])
                     if x['ok'] and not y['ok']]
        measured = {'epoch': i, 'facts_strict': s['facts_strict'],
                    'paraphrases_strict': s['paraphrases_strict'],
                    'near_miss_leak_strict': s['near_miss_leak_strict'],
                    'near_miss_abstain_strict': s['near_miss_abstain_strict'],
                    'forgotten_baseline_probes': len(forgotten),
                    'forgotten_questions': forgotten,
                    'invalid_outputs': row['invalid_outputs']}
        measured['diagnostic_pass'] = bool(
            measured['facts_strict'] >= CRITERIA['facts_strict_min']
            and measured['paraphrases_strict'] >= CRITERIA['paraphrases_strict_min']
            and measured['near_miss_leak_strict'] <= CRITERIA['near_miss_leak_strict_max']
            and measured['near_miss_abstain_strict'] >= CRITERIA['near_miss_abstain_strict_min']
            and measured['forgotten_baseline_probes'] <= CRITERIA['forgotten_baseline_probes_max']
            and measured['invalid_outputs'] == 0)
        rows.append(measured)
    selected = next((r['epoch'] for r in rows if r['diagnostic_pass']), None)
    return {'criteria': dict(CRITERIA), 'rows': rows, 'selected_epoch': selected,
            'selection': 'CANDIDATE_ONLY_NO_ACTIVATION' if selected else 'NONE',
            'AG6_promoted': False, 'Body_JEPA_promoted': False}


def run(tool_dir, server, master, manifest, out):
    tool_dir, server, master, manifest, out = map(Path, (tool_dir, server, master, manifest, out))
    if out.exists():
        raise FileExistsError('Run339 output already exists')
    for p in (server, master, manifest, tool_dir/'native-answer-epoch-checkpoint-run319',
              tool_dir/'llama-quantize'):
        require(p.is_file() and not p.is_symlink(), 'Run339 pinned binary/source required')
    data = verify_sources(master, manifest)
    out.mkdir(parents=True)
    report = {'schema': SCHEMA, 'status': 'INCOMPLETE',
              'evidence_level': 'LINUX_NATIVE_PENDING',
              'cohort_sha256': COHORT_SHA, 'master_sha256': MASTER_SHA,
              'hf_repo': HF_REPO, 'hf_revision': HF_REVISION,
              'model_license': 'LFM Open License v1.0',
              'train': dict(TRAIN), 'criteria': dict(CRITERIA),
              'gates': dict(GATES), 'weights_published': False,
              'model_activated': False, 'arms': {},
              'claim_limit': 'Synthetic near-miss targets are trained in B/C; no unseen uncertainty generalization, AG6, Body-JEPA, Redmi or V13 promotion'}
    report_path = out/'RUN339_REPORT.json'
    def save():
        atomic_write(report_path, (dumps(report)+'\n').encode())
    save()
    try:
        s = old.Server(server, master, ['--cache-ram', '0'], out/'template.log')
        try:
            anchors = old.get_anchors(s)
            streams = {name: make_stream(s, data['facts'], data['near_miss'],
                                         contrastive, replay, anchors if replay else [])
                       for name, (contrastive, replay) in ARMS.items()}
        finally:
            s.stop()
        report['anchors_count'] = len(anchors)
        report['anchor_prompt_sha256'] = hashlib.sha256(
            json.dumps([q for q, _ in anchors], sort_keys=True).encode()).hexdigest()
        for name, stream in streams.items():
            (out/(name+'.train.txt')).write_text(stream)
        baseline_q4 = out/'baseline-q4.gguf'
        old.quantize(tool_dir, master, baseline_q4, old.FFN_LATE)
        report['baseline_q4_sha256'] = old.digest(baseline_q4)
        baseline = evaluate(server, baseline_q4, out/'eval-baseline.log', data)
        report['baseline'] = baseline
        report['status'] = 'BASELINE_EVALUATED'
        save()
        for name, (contrastive, replay) in ARMS.items():
            arm_dir = out/name
            arm_dir.mkdir()
            trained = arm_dir/'trained-f32.gguf'
            stream = out/(name+'.train.txt')
            row = {'loss_mode': 'answer', 'contrastive': contrastive, 'replay': replay,
                   'train_stream_sha256': old.digest(stream), 'status': 'INCOMPLETE',
                   'native_training_executed': False, 'checkpoint_receipts': [],
                   'epochs': [], 'weights_published': False}
            report['arms'][name] = row
            save()
            env = dict(os.environ, V13_TRAIN_TENSORS=','.join(old.FFN_LATE),
                       V13_EPOCH_CHECKPOINTS='1', V13_LOSS_MODE='answer', V13_KL_WEIGHT='0')
            cmd = [str(tool_dir/'native-answer-epoch-checkpoint-run319'),
                   '-m', str(master), '-f', str(stream), '-o', str(trained),
                   '-c', '256', '-b', '256', '-ub', '256', '--epochs', '2',
                   '-lr', '1e-5', '-t', '4', '-s', '53']
            start = time.monotonic()
            try:
                p = subprocess.run(cmd, env=env, capture_output=True, text=True,
                                   errors='replace', timeout=1000)
                stdout, stderr, rc = p.stdout, p.stderr, p.returncode
            except subprocess.TimeoutExpired as exc:
                stdout = (exc.stdout or b'').decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
                stderr = (exc.stderr or b'').decode(errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
                rc = 124
            (arm_dir/'train.stdout.log').write_text(stdout)
            (arm_dir/'train.stderr.log').write_text(stderr)
            row.update({'train_exit': rc, 'train_wall_s': round(time.monotonic()-start, 2),
                        'train_stdout_sha256': old.digest(arm_dir/'train.stdout.log'),
                        'train_stderr_sha256': old.digest(arm_dir/'train.stderr.log')})
            row['status'] = 'TRAIN_FAILED' if rc else 'TRAIN_FINISHED'
            save()
            if rc:
                raise ValueError('Run339 native optimizer failed: '+name)
            receipts = old.validate_receipts(stdout, trained, epochs=2)
            row['checkpoint_receipts'] = receipts
            row['native_training_executed'] = True
            row['final_master_sha256'] = old.digest(trained)
            require(row['final_master_sha256'] == receipts[-1]['sha256'],
                    'Run339 final epoch SHA mismatch')
            row['status'] = 'CHECKPOINTS_VERIFIED'
            save()
            candidates = []
            for epoch in (1, 2):
                source = Path(str(trained)+'.epoch'+str(epoch)+'.gguf')
                require(old.digest(source) == receipts[epoch-1]['sha256'],
                        'Run339 epoch SHA drift')
                q4 = arm_dir/('epoch'+str(epoch)+'-q4.gguf')
                old.quantize(tool_dir, source, q4, old.FFN_LATE)
                evaluated = evaluate(server, q4, arm_dir/('eval-epoch'+str(epoch)+'.log'), data)
                candidates.append(evaluated)
                row['epochs'].append({'epoch': epoch, 'source_sha256': old.digest(source),
                                      'q4_sha256': old.digest(q4), 'evaluation': evaluated})
                row['status'] = 'EPOCH_'+str(epoch)+'_EVALUATED'
                save()
            row['selection_report'] = select(baseline, candidates)
            row['tensor_audit'] = old.tensor_audit(master,
                Path(str(trained)+'.epoch1.gguf'), Path(str(trained)+'.epoch2.gguf'))
            row['status'] = 'COMPLETE_NATIVE_DIAGNOSTIC'
            row['weights_retained'] = False
            save()
            for temporary in (trained, Path(str(trained)+'.epoch1.gguf'),
                              Path(str(trained)+'.epoch2.gguf'),
                              arm_dir/'epoch1-q4.gguf', arm_dir/'epoch2-q4.gguf'):
                temporary.unlink(missing_ok=True)
        baseline_q4.unlink(missing_ok=True)
        report['status'] = 'COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC'
        report['evidence_level'] = 'LINUX_NATIVE_C3_FRESH_CONTRASTIVE_TRAIN_EVAL'
        save()
        return report
    except BaseException as exc:
        report['status'] = 'FAIL_CLOSED'
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:350]}
        save()
        return report


def main():
    ap = argparse.ArgumentParser()
    for name in ('tool-dir', 'server', 'master', 'source-manifest', 'out-dir'):
        ap.add_argument('--'+name, required=True)
    args = ap.parse_args()
    result = run(args.tool_dir, args.server, args.master, args.source_manifest, args.out_dir)
    print(dumps({'status': result['status'],
                 'arms': {k: v.get('selection_report', {}).get('selection')
                          for k, v in result.get('arms', {}).items()}}))
    raise SystemExit(0 if result['status'] == 'COMPLETE_NATIVE_THREE_ARM_DIAGNOSTIC' else 2)

if __name__ == '__main__':
    main()
