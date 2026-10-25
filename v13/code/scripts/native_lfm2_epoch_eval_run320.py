"""Run320 preregistered pinned native LFM2 two-epoch training/evaluation.

Actual model weights remain in an isolated local workdir, never in GitHub
artifacts. Fixture tests of selectors/receipts are NOT native training evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13.common import atomic_write, dumps
from native_cache_bench import Server
from native_lfm2_finetune_bench import FFN_LATE, train_text, evaluate, quantize
from lora_bench import FACTS, PARAPHRASES, NEAR_MISS, PROBES

SCHEMA = 'V13_RUN320_PINNED_NATIVE_LFM2_EPOCH_EVAL_V1'
HF_REPO = 'LiquidAI/LFM2.5-350M'
HF_REVISION = '9e6c6ccf47cd318696e137d381a7ded8fe4df09f'
PINNED_SHA = {
    'lora_bench.py': '313bc41c447640241b00319932469345c801f089dae0b949f1f6ebda26d3d53f',
    'native_lfm2_finetune_bench.py': 'dfb46beb7b5be571c364ac3cab04379d411fd54ae5d0005d094f1f5a11e94397',
    'native_cache_bench.py': '0c8506397728d6084d3e6aa05a46d8434c7ec8a637861372c9c4c967611bfe00',
}
TRAIN = {'variant': 'ffn_late_all', 'tensor_keys': list(FFN_LATE),
         'learning_rate': 1e-5, 'epochs': 2, 'reps': 12,
         'seed': 13, 'threads': 4, 'ctx': 256, 'batch': 256,
         'ubatch': 256, 'loss_mode': 'all', 'anchors': 0}
GATES = {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
         'Body_JEPA': 'UNAVAILABLE', 'jepa_weight': 0, 'V13': 'INCOMPLETE'}
CRITERIA = {'facts_strict_min': 2, 'paraphrases_strict_min': 1,
            'near_miss_leak_strict_max': 0.2,
            'forgotten_baseline_probes_max': 0, 'invalid_outputs_max': 0}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def verify_sources():
    base = Path(__file__).resolve().parent
    for name, expected in PINNED_SHA.items():
        if digest(base / name) != expected:
            raise ValueError('frozen Run320 source cohort drift: ' + name)
    if (len(FACTS), len(PARAPHRASES), len(NEAR_MISS), len(PROBES)) != (8, 6, 5, 12):
        raise ValueError('frozen Run320 cohort denominator drift')
    if FFN_LATE != ['blk.12.ffn_down', 'blk.13.ffn_down', 'blk.14.ffn_down', 'blk.15.ffn_down']:
        raise ValueError('Run320 tensor selection drift')


def select(base, rows):
    """Strict preregistered earliest passing epoch, never promote authority."""
    if len(base.get('probes', [])) != len(PROBES):
        raise ValueError('baseline probe denominator')
    result = []
    for epoch, candidate in enumerate(rows, start=1):
        if (len(candidate.get('facts', [])) != len(FACTS)
                or len(candidate.get('paraphrases', [])) != len(PARAPHRASES)
                or len(candidate.get('near_miss', [])) != len(NEAR_MISS)
                or len(candidate.get('probes', [])) != len(PROBES)):
            raise ValueError('epoch cohort denominator')
        forgotten = [x['q'] for x, y in zip(base['probes'], candidate['probes'])
                     if x.get('ok') and not y.get('ok')]
        summary = candidate['summary']
        measured = {
            'epoch': epoch,
            'facts_strict': summary['facts_strict'],
            'paraphrases_strict': summary['para_strict'],
            'near_miss_leak_strict': summary['near_miss_leak_strict'],
            'forgotten_baseline_probes': len(forgotten),
            'forgotten_questions': forgotten,
            'invalid_outputs': candidate['invalid_outputs'],
        }
        passed = (
            measured['facts_strict'] >= CRITERIA['facts_strict_min']
            and measured['paraphrases_strict'] >= CRITERIA['paraphrases_strict_min']
            and measured['near_miss_leak_strict'] <= CRITERIA['near_miss_leak_strict_max']
            and measured['forgotten_baseline_probes'] <= CRITERIA['forgotten_baseline_probes_max']
            and measured['invalid_outputs'] <= CRITERIA['invalid_outputs_max']
        )
        measured['diagnostic_pass'] = bool(passed)
        result.append(measured)
    first = next((x['epoch'] for x in result if x['diagnostic_pass']), None)
    return {'criteria': dict(CRITERIA), 'rows': result,
            'selected_epoch': first, 'selection': 'CANDIDATE_ONLY_NO_ACTIVATION' if first else 'NONE',
            'AG6_promoted': False, 'body_jepa_promoted': False}


def validate_receipts(stdout, output, epochs=2):
    lines = re.findall(r'^V13_EPOCH_CHECKPOINT (\{.*\})$', stdout, re.MULTILINE)
    if len(lines) != epochs:
        raise ValueError('missing or extra native checkpoint receipts')
    rows = [json.loads(x) for x in lines]
    for i, row in enumerate(rows, start=1):
        path = Path(str(output) + '.epoch' + str(i) + '.gguf')
        if row.get('epoch') != i or row.get('out') != str(path):
            raise ValueError('native checkpoint receipt epoch/path mismatch')
        if not path.is_file() or path.is_symlink() or path.stat().st_size != row.get('bytes') or row['bytes'] < 1024:
            raise ValueError('native checkpoint missing or byte count mismatch')
        row['sha256'] = digest(path)
    return rows


def run(tool_dir, server, master, source_manifest, out_dir):
    verify_sources()
    tool_dir, server, master, source_manifest, out_dir = map(Path, (tool_dir, server, master, source_manifest, out_dir))
    if out_dir.exists():
        raise FileExistsError('Run320 output already exists; refuse overwrite')
    if any(p.is_symlink() or not p.is_file() for p in (server, master, source_manifest)):
        raise ValueError('regular source/model files required')
    if master.stat().st_size < 500_000_000:
        raise ValueError('FP32 master suspiciously small')
    manifest = json.loads(source_manifest.read_text())
    if (manifest.get('hf_repo') != HF_REPO or manifest.get('hf_revision') != HF_REVISION
            or manifest.get('master_sha256') != digest(master)
            or manifest.get('conversion_outtype') != 'f32'
            or manifest.get('llama_source_sha256') != '4c96d72c40cefdacf621457d8a12fe5673b8de5b640ff7fe6d342ea1c579a9fe'):
        raise ValueError('pinned model/master/conversion manifest mismatch')
    binary = tool_dir / 'native-answer-epoch-checkpoint-run319'
    quantizer = tool_dir / 'llama-quantize'
    if any(not p.is_file() or p.is_symlink() for p in (binary, quantizer)):
        raise ValueError('native trainer or quantizer missing')
    out_dir.mkdir(parents=True)
    weights = out_dir / 'weights'
    weights.mkdir()
    report_file = out_dir / 'RUN320_EPOCH_EVAL.json'
    report = {
        'schema': SCHEMA, 'status': 'INCOMPLETE', 'evidence_level': 'LINUX_NATIVE_PENDING',
        'hf_repo': HF_REPO, 'hf_revision': HF_REVISION,
        'model_license': 'LFM Open License v1.0',
        'master_sha256': manifest['master_sha256'],
        'source_manifest_sha256': digest(source_manifest),
        'native_binary_sha256': digest(binary),
        'quantizer_sha256': digest(quantizer),
        'server_sha256': digest(server),
        'train': dict(TRAIN), 'criteria': dict(CRITERIA),
        'gates': dict(GATES), 'native_training_executed': False,
        'selection': 'NONE', 'weights_published': False,
        'claim_limit': 'Two synthetic Linux-native C3 epochs only; no AG6, Body-JEPA, Redmi or activation',
    }
    def save():
        atomic_write(report_file, (dumps(report) + '\n').encode())
    save()
    try:
        stream_path = out_dir / 'train.txt'
        s = Server(server, master, ['--cache-ram', '0'], out_dir / 'template.log')
        try:
            train = train_text(s, TRAIN['reps'], TRAIN['seed'], 'all', [])
        finally:
            s.stop()
        stream_path.write_text(train)
        report['train_stream_sha256'] = digest(stream_path)
        report['status'] = 'TRAIN_STREAM_CLOSED'
        save()

        trained = weights / 'trained-f32.gguf'
        cmd = [str(binary), '-m', str(master), '-f', str(stream_path),
               '-o', str(trained), '-c', '256', '-b', '256', '-ub', '256',
               '--epochs', '2', '-lr', '1e-5', '-t', '4', '-s', '13']
        env = dict(os.environ, V13_TRAIN_TENSORS=','.join(FFN_LATE),
                   V13_EPOCH_CHECKPOINTS='1', V13_KL_WEIGHT='0')
        start = time.monotonic()
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True,
                                    errors='replace', timeout=1000)
            out, err, rc = result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or b'').decode(errors='replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
            err = (exc.stderr or b'').decode(errors='replace') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
            rc = 124
        (out_dir / 'train.stdout.log').write_text(out)
        (out_dir / 'train.stderr.log').write_text(err)
        report['train_exit'] = rc
        report['train_wall_s'] = round(time.monotonic() - start, 2)
        report['train_stdout_sha256'] = digest(out_dir / 'train.stdout.log')
        report['train_stderr_sha256'] = digest(out_dir / 'train.stderr.log')
        report['status'] = 'TRAIN_FINISHED' if rc == 0 else 'TRAIN_FAILED'
        save()
        if rc:
            return report
        receipts = validate_receipts(out, trained, epochs=2)
        report['checkpoint_receipts'] = receipts
        report['final_master_sha256'] = digest(trained)
        report['final_matches_last_epoch_sha256'] = report['final_master_sha256'] == receipts[-1]['sha256']
        report['native_training_executed'] = True
        report['status'] = 'NATIVE_CHECKPOINTS_VERIFIED'
        save()

        base_q = weights / 'baseline-q4.gguf'
        quantize(tool_dir, master, base_q, FFN_LATE)
        report['baseline_q4_sha256'] = digest(base_q)
        base = evaluate(server, base_q, out_dir / 'eval-baseline.log')
        report['baseline'] = base
        report['status'] = 'BASELINE_EVALUATED'
        save()
        candidates = []
        for i in (1, 2):
            source = Path(str(trained) + '.epoch' + str(i) + '.gguf')
            quantized = weights / ('epoch' + str(i) + '-q4.gguf')
            quantize(tool_dir, source, quantized, FFN_LATE)
            candidate = evaluate(server, quantized, out_dir / ('eval-epoch' + str(i) + '.log'))
            candidates.append(candidate)
            report.setdefault('epochs', []).append({
                'epoch': i, 'source_sha256': digest(source),
                'q4_sha256': digest(quantized), 'evaluation': candidate,
            })
            report['status'] = 'EPOCH_' + str(i) + '_EVALUATED'
            save()
        report['selection_report'] = select(base, candidates)
        report['selection'] = report['selection_report']['selection']
        report['status'] = 'COMPLETE_NATIVE_EVALUATION'
        report['evidence_level'] = 'LINUX_NATIVE_C3_TRAIN_AND_EVAL'
        save()
        return report
    except BaseException as exc:
        report['status'] = 'ERROR'
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:500]}
        save()
        return report


def main():
    ap = argparse.ArgumentParser()
    for name in ('tool-dir', 'server', 'master', 'source-manifest', 'out-dir'):
        ap.add_argument('--' + name, required=True)
    a = ap.parse_args()
    r = run(a.tool_dir, a.server, a.master, a.source_manifest, a.out_dir)
    print(dumps({'status': r['status'], 'selection': r['selection'],
                 'native_training_executed': r['native_training_executed'],
                 'selection_report': r.get('selection_report')}))
    if r['status'] != 'COMPLETE_NATIVE_EVALUATION':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
