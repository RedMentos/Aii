#!/usr/bin/env python3
"""Tool-consequence forecast on the installed device (Redmi/Termux or Linux): build, parity gate, live check, report.

1. Builds scripts/native_layer_taps.cpp against the installed, pinned llama.cpp runner (same pinned source archive,
   header hashes and exact shared libraries as test_native_prefill_port.prepare_worker).
2. install_tool_forecast.install with the installed B2 GGUF (must be the capture model): the candidate's own gate on
   its test partition with this device's encoder. Only a PASS writes <home>/data/tool_forecast/encoder.json, which
   is what lets `:toolforecast shadow` forecast in the chat.
3. tool_forecast_live_check.run with the fixed plan specs/tool_forecast/live-plan.json (same 245 calls as the
   preregistered cloud check) in a throwaway store under the export folder.
4. with --with-learning: tool_forecast_learning_check.run with the fixed plan specs/tool_forecast/learning-plan.json
   (the preregistered round-2 learning check, 610 calls: experience outside the world, `learn` region mode, fresh test).
Everything lands in <home>/exports/tool-forecast-<time>/ (report.json is the file to upload). No authority is granted.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
import traceback

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / 'scripts'))
import install_tool_forecast as installer
import test_native_prefill_port as port
import tool_forecast_learning_check as learning
import tool_forecast_live_check as live
from v13 import toolforecast as tf
from v13.common import file_hash
from v13.config import home_path
from v13.models import ModelManager, catalog
from v13.resources import device

SOURCE = APP / 'scripts/native_layer_taps.cpp'


def build_taps(home, identity, runner, cancel, out):
    """Compile the tap reader with the pinned runner's command line (source and output swapped), cached by identity."""
    _, base = port.prepare_worker(home, identity, runner, cancel, out)
    key = {'base_identity': base['identity_key'], 'source_sha256': file_hash(SOURCE), 'helper_sha256': file_hash(Path(__file__))}
    binary = home / 'bin/native-layer-taps'
    marker = home / 'config/native-layer-taps.json'
    prior = json.loads(marker.read_text()) if marker.exists() else {}
    if binary.is_file() and prior.get('identity_key') == key and prior.get('binary_sha256') == file_hash(binary):
        return binary, prior
    temporary = binary.with_name(binary.name + '.new')
    worker_src, worker_out = str(APP / 'scripts/native_prefill_worker.cpp'), str(home / 'bin/native-prefill-worker.new')
    if worker_src not in base['command'] or worker_out not in base['command']:
        raise RuntimeError('Pinned worker command has an unexpected shape')
    command = [str(SOURCE) if x == worker_src else str(temporary) if x == worker_out else x for x in base['command']]
    build = port.bounded_process(command, out / 'taps-build.log', cancel, 300)
    port.save(out / 'taps-build-attempt.json', {'command': command, 'identity_key': key, 'build': build})
    if build['exit_code'] or build['stop_reason'] or not temporary.is_file():
        raise RuntimeError('native_layer_taps compilation failed; see taps-build.log')
    temporary.chmod(0o700)
    os.replace(temporary, binary)
    result = {'schema': 'V13_NATIVE_LAYER_TAPS_BUILD_V1', 'identity_key': key, 'command': command, 'build': build,
              'binary_sha256': file_hash(binary)}
    port.save(marker, result)
    return binary, result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--installed-home', default=None)
    parser.add_argument('--out-dir', default=None)
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--skip-live', action='store_true', help='build + parity gate only')
    parser.add_argument('--with-learning', action='store_true', help='also run the 610-call learning check (long)')
    args = parser.parse_args()
    home = home_path(args.installed_home)
    out = Path(args.out_dir).resolve() if args.out_dir else home / 'exports' / ('tool-forecast-' + time.strftime('%Y%m%d-%H%M%S'))
    if out.exists() and any(out.iterdir()):
        parser.error('Fresh output folder required')
    out.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'V13_TOOL_FORECAST_DEVICE_REPORT_V1', 'status': 'PREPARING', 'device': device(),
              'receiver_authority': 0, 'learn_authority': 0, 'mode_after': 'unchanged (switch on with :toolforecast shadow)'}
    path = out / 'report.json'
    port.save(path, report)
    cancel = threading.Event()
    handlers = {sig: signal.signal(sig, lambda *_: cancel.set()) for sig in [signal.SIGINT, signal.SIGTERM]}
    lock = None
    try:
        lock = (home / 'data/coordinator.lock').open('a+')
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)   # never next to a running chat or another heavy job
        specs = catalog()
        model = ModelManager(home).path_for('B2_GIST')
        want = json.loads(tf.MANIFEST.read_text())['encoder']['model_sha256']
        if file_hash(model) != want:
            raise RuntimeError('Installed B2 GGUF is not the capture model ' + want[:12])
        identity = port.installed_identity(home, model, specs['runner'])
        binary, build = build_taps(home, identity, specs['runner'], cancel, out)
        report['build'] = {k: build[k] for k in ('binary_sha256', 'identity_key')}
        report['status'] = 'PARITY'
        port.save(path, report)
        t0 = time.monotonic()
        rc = installer.install(argparse.Namespace(home=str(home), tool=str(binary), model=str(model), threads=args.threads,
                                                  backend_dir=identity['library_directory']))
        report['parity_seconds'] = round(time.monotonic() - t0, 1)
        enc_path = home / 'data/tool_forecast' / ('encoder.json' if rc == 0 else 'encoder-parity-failed.json')
        enc = json.loads(enc_path.read_text())
        report['parity'] = enc['parity']
        if rc != 0:
            report['status'] = 'PARITY_FAIL'
            return 1
        if args.skip_live:
            report['status'] = 'PARITY_PASS_NO_LIVE'
            return 0
        report['status'] = 'LIVE'
        port.save(path, report)
        live_rc = live.run(argparse.Namespace(plan=str(APP / 'specs/tool_forecast/live-plan.json'), restored=None, out=str(out / 'live'),
                                    encoder_home=None), encoder_json=enc_path)
        got = json.loads((out / 'live/report.json').read_text())
        report['live'] = {k: got[k] for k in ('verdict', 'statuses', 'seconds_per_call_median', 'tap_process_max_rss_mb', 'arms')}
        report['status'] = got['verdict']
        if args.with_learning:
            port.save(path, report)
            learning_rc = learning.run(argparse.Namespace(plan=str(APP / 'specs/tool_forecast/learning-plan.json'), restored=None,
                                            out=str(out / 'learning'), encoder_home=str(home), round=2))
            lg = json.loads((out / 'learning/report.json').read_text())
            report['learning'] = {'verdict': lg['verdict'], 'minutes': lg['minutes'], 'statuses': lg['statuses'],
                                  'integrity': lg.get('integrity', {'pass': False}), 'analysis_ran': lg.get('analysis_ran', False),
                                  'worlds': {w: {k: v[k] for k in ('pass', 'learn', 'shift_actions_improved')} for w, v in lg['worlds'].items()}}
            report['status'] = got['verdict'] + '+' + lg['verdict']
            return 0 if (live_rc == 0 and got['verdict'] == 'LIVE_PATH_CONFIRMED'
                         and learning_rc == 0 and lg['verdict'] == 'CONTINUAL_LEARNING_CONFIRMED'
                         and lg.get('integrity', {}).get('pass') is True and lg.get('analysis_ran') is True) else 1
        return 0 if live_rc == 0 and got['verdict'] == 'LIVE_PATH_CONFIRMED' else 1
    except Exception as exc:
        report['status'] = 'ERROR'
        report['error'] = type(exc).__name__ + ': ' + str(exc)[:500]
        (out / 'error.txt').write_text(traceback.format_exc())
        return 1
    finally:
        port.save(path, report)
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
        if lock:
            lock.close()
        print('\nBericht: %s (Status %s)' % (path, report['status']))


if __name__ == '__main__':
    sys.exit(main())
