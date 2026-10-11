#!/usr/bin/env python3
"""Independent greedy server check against an existing actual causal turn.

Reuses the exact admitted token IDs; never changes its prompt or scorer.
This comparison establishes decoder agreement, not answer quality.
"""
import argparse
import fcntl
import json
from pathlib import Path
import sys
import threading
import time
import zipfile

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from v13.common import atomic_write, dumps, file_hash
from v13.causal_prepare import check_prepared
from v13.config import initialize
from v13.runners import LlamaRunner


def compare(args):
    args.out.mkdir(parents=True, exist_ok=False)
    original = json.loads((args.proof_dir / 'native-report.json').read_text())
    with zipfile.ZipFile(args.proof_dir / 'native-artifacts.zip') as archive:
        context = json.loads(archive.read('causal-session/context.json'))
    binding = check_prepared(args.home)
    if binding['feature_abi'] != original['binding']['feature_abi']:
        raise ValueError('Original exact native/model/source ABI differs')
    tokens = context['token_ids']
    if not 1 <= len(tokens) <= 512 or any(type(t) is not int for t in tokens):
        raise ValueError('Original admitted native tokens required')
    report = {'status': 'STARTED', 'scope': 'EXACT_ORIGINAL_CONTEXT_DECODER_AGREEMENT_ONLY',
              'prompt_retuned': False, 'model_quality_pass': False,
              'original_report_sha256': file_hash(args.proof_dir / 'native-report.json'),
              'source_sha256': file_hash(Path(__file__)),
              'input_token_ids': tokens, 'checks': {}}
    def save():
        atomic_write(args.out / 'report.json', dumps(report))
    save()
    runner = None
    try:
        cfg = dict(initialize(args.home), context_tokens=2048, threads=2)
        runner = LlamaRunner(args.home, 'C3_LANGUAGE', Path(binding['identity']['model_path']), cfg)
        runner.binary = binding['identity']['server_path']
        cancel = threading.Event()
        deadline = time.monotonic() + 30
        runner.load(cancel, deadline)
        result = runner._json('POST', '/completion', {
            'prompt': tokens, 'n_predict': 64, 'temperature': 0,
            'top_k': 1, 'repeat_penalty': 1, 'seed': 13,
            'cache_prompt': False, 'return_tokens': True, 'stream': False,
        }, deadline, timeout_cap=None)
        atomic_write(args.out / 'actual-server-completion.json', dumps(result))
        native = original['metadata']['runner']['native_token_ids']
        server_ids = result.get('tokens', [])
        # Some server APIs omit the consumed EOS from returned visible IDs.
        # Preserve both sequences and report that difference explicitly.
        report.update(actual_server_output=result.get('content'),
                      actual_causal_output=original['actual_output'],
                      causal_token_ids=native, server_token_ids=server_ids,
                      exact_all_token_ids=server_ids == native,
                      server_omits_last_eos=(server_ids == native[:-1]
                                             and result.get('stop_type') == 'eos'),
                      server_stop_type=result.get('stop_type'))
        report['checks'] = {
            'exact_output_bytes': result.get('content') == original['actual_output'],
            'first_native_token': bool(server_ids) and server_ids[0] == native[0],
            'native_model_unchanged': file_hash(binding['identity']['model_path']) == binding['identity']['model_sha256'],
        }
        report['status'] = 'DECODER_AGREEMENT_PASS' if all(report['checks'].values()) else 'DECODER_AGREEMENT_FAIL'
    except BaseException as exc:
        report.update(status='DECODER_COMPARISON_ERROR', error_type=type(exc).__name__, error=str(exc))
    finally:
        if runner is not None:
            report['server_release'] = runner.unload()
        save()
    print(dumps({'status': report['status'], 'checks': report['checks'],
                 'quality_claim': False, 'report': str(args.out / 'report.json')}), flush=True)
    return 0 if report['status'] == 'DECODER_AGREEMENT_PASS' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, required=True)
    parser.add_argument('--proof-dir', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    # Share the existing Runtime/installer exclusion before any initialization,
    # output creation, model hashing or native work.
    with (args.home / 'data/coordinator.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(dumps({'status': 'DECODER_COMPARISON_REFUSED',
                         'error': 'V13 läuft oder baut bereits; zuerst schließen',
                         'native_inference_performed': False}), flush=True)
            return 2
        try:
            return compare(args)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == '__main__':
    raise SystemExit(main())
