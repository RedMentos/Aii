"""Explicit preparation of the existing pinned causal C3 stream, without inference."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import signal
import threading
import time
import uuid

from .common import atomic_write, dumps, file_hash, Unavailable
from .config import home_path, initialize, save_config
from .models import ModelManager, catalog


def check_prepared(home):
    """Return the exact existing stream binding. Never download, compile or infer.

    Raises Unavailable for absent/stale installations. The consuming runtime must
    hold its normal coordinator lock; this read-only function takes no lock.
    """
    from scripts.native_prefill_stream_client import STREAM_ABI, bind_installed
    home = Path(home).expanduser().resolve()
    try:
        binding = bind_installed(home)
        marker = json.loads((home / 'config/native-prefill-stream.json').read_text())
        key = marker['identity_key']
        base = key['base_build_identity']
        runner = catalog()['runner']
        source = {'url': runner['source_url'], 'size': runner['source_size'],
                  'sha256': runner['source_sha256']}
        if (key.get('feature_abi') != STREAM_ABI or
                base.get('source_archive') != source or
                base.get('machine') != platform.machine() or
                base.get('build_flags') != ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror'] or
                not os.access(binding['binary'], os.X_OK)):
            raise Unavailable('Pinned causal build ABI/source/platform differs')
        return binding
    except (OSError, KeyError, ValueError, Unavailable) as exc:
        raise Unavailable('Causal C3 nicht vorbereitet oder verändert: ' + str(exc) +
                          '; Chat schließen, dann bash VORBEREITEN_CAUSAL.sh') from exc


def prepare_causal_stream(home, *, cancel=None, out_dir=None, enable=False):
    """Compile using unchanged build_stream; validate guards; preserve old caches.

    This explicit operator action may retrieve the exact manifest-pinned source
    archive. It never installs/replaces model weights or runs model inference.
    Coordinator exclusion covers compilation, final identity check and optional
    opt-in settings write. Failed attempts remain as visible reports/logs.
    """
    from scripts import test_native_prefill_port as port
    from scripts.test_native_prefill_stream import build_stream
    home = Path(home).expanduser().resolve()
    cancel = cancel if cancel is not None else threading.Event()
    out = (Path(out_dir).expanduser().resolve() if out_dir is not None else
           home / 'exports' / ('causal-prepare-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:8]))
    if out.exists() and any(out.iterdir()):
        raise Unavailable('Fresh causal preparation attempt directory required')
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / 'report.json'
    report = {'schema': 'V13_CAUSAL_PREPARATION_V1', 'status': 'PREPARING',
              'native_inference_performed': False, 'model_weights_modified': False,
              'enable_requested': enable, 'runtime_enabled': False,
              'scope': 'Pinned stream compilation and command guards only; no latency, learning or phone proof'}
    atomic_write(report_path, dumps(report))
    lock = None
    try:
        # Creating the lock directory is safe before initialization; do not
        # rewrite settings while another runtime/installer owns the coordinator.
        (home / 'data').mkdir(parents=True, exist_ok=True)
        lock = (home / 'data/coordinator.lock').open('a+')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Unavailable('V13 läuft oder baut bereits; Chat/Installer zuerst schließen') from exc
        cfg = initialize(home)
        if cancel.is_set():
            raise Unavailable('Causal preparation cancelled before build')
        specs = catalog()
        manager = ModelManager(home)
        model = manager.path_for('C3_LANGUAGE')
        if (file_hash(model) != specs['models']['language']['files'][0]['sha256'] or
                manager.revision('C3_LANGUAGE') != specs['models']['language']['revision']):
            raise Unavailable('Exact installed pinned C3 required; run existing STARTEN.sh setup first')
        identity = port.installed_identity(home, model, specs['runner'])
        binary, build = build_stream(home, identity, specs['runner'], cancel, out)
        report['build'] = build
        atomic_write(report_path, dumps(report))
        if cancel.is_set():
            raise Unavailable('Causal preparation cancelled after build')
        guards = port.bounded_process([str(binary), '--guard-test'], out / 'command-guards.log', cancel, 10)
        report['command_guard_process'] = guards
        if guards['exit_code'] or guards['stop_reason'] or not guards['process_reaped']:
            raise Unavailable('Compiled causal command guards failed; preserved attempt logs')
        native_guards = json.loads((out / 'command-guards.log').read_text())
        checks = native_guards.get('checks')
        if (native_guards.get('schema') != 'V13_CAUSAL_STREAM_GUARDS_V2' or
                native_guards.get('status') != 'GUARD_PASS' or
                native_guards.get('native_inference_performed') is not False or
                not isinstance(checks, dict) or not checks or
                not all(value is True for value in checks.values())):
            raise Unavailable('Unexpected causal command guard result')
        report['command_guards'] = native_guards
        binding = check_prepared(home)
        if binding['identity'] != identity:
            raise Unavailable('Installed native/model identity changed during preparation')
        report['feature_abi'] = binding['feature_abi']
        report['binary_sha256'] = binding['binary_sha256']
        if enable:
            cfg['c3_decode_mode'] = 'same_causal_zero'
            report['previous_answer_tokens'] = cfg['answer_tokens']
            if cfg['answer_tokens'] not in (64, 128):
                cfg['answer_tokens'] = 64
            report['configured_answer_tokens'] = cfg['answer_tokens']
            save_config(home, cfg)
            report['runtime_enabled'] = True
        report['status'] = 'CAUSAL_PREPARED_NO_MODEL_INFERENCE'
        atomic_write(report_path, dumps(report))
        return report
    except BaseException as exc:
        report.update(status='CAUSAL_PREPARATION_FAILED', error_type=type(exc).__name__,
                      error=str(exc)[:1000])
        atomic_write(report_path, dumps(report))
        raise Unavailable(str(exc) + '; Bericht: ' + str(report_path)) from exc
    finally:
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home')
    parser.add_argument('--out-dir')
    parser.add_argument('--check', action='store_true', help='Read-only exact installation check')
    parser.add_argument('--enable', action='store_true', help='Opt in to causal runtime after successful preparation')
    args = parser.parse_args()
    if args.check and (args.enable or args.out_dir):
        parser.error('--check cannot enable or create preparation artifacts')
    cancel = threading.Event()
    handlers = {sig: signal.signal(sig, lambda *_: cancel.set()) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        if args.check:
            binding = check_prepared(home_path(args.home))
            print(dumps({'status': 'CAUSAL_PREPARED_READ_ONLY_CHECK', 'native_inference_performed': False,
                         'feature_abi': binding['feature_abi'], 'binary_sha256': binding['binary_sha256']}))
        else:
            print(dumps(prepare_causal_stream(home_path(args.home), cancel=cancel,
                                            out_dir=args.out_dir, enable=args.enable)))
        return 0
    except Exception as exc:
        print(dumps({'status': 'CAUSAL_PREPARATION_FAILED', 'error': str(exc),
                     'native_inference_performed': False}))
        return 1
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
