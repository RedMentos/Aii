#!/usr/bin/env python3
"""Bounded, resumable measurements around the existing native sustained probe.

No sensor estimate can satisfy an unavailable hardware gate. Raw measurements
are flushed continuously; each native batch keeps its own report and log.
"""
import argparse
import datetime
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.common import APP, atomic_write, file_hash
from v13.resources import device, process_memory, snapshot

SCHEMA = 'V13_PHONE_EPOCH_V1'


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def read_number(path):
    try:
        return number(path.read_text().strip())
    except OSError:
        return None


def battery_sysfs(root=Path('/sys')):
    """Linux power_supply ABI units: microamp, microvolt, microwatt, microwatthour."""
    batteries = []
    for base in sorted((root / 'class/power_supply').glob('*')):
        try:
            kind = (base / 'type').read_text().strip().lower()
            status = (base / 'status').read_text().strip()
        except OSError:
            continue
        if kind != 'battery':
            continue
        current = read_number(base / 'current_now')
        voltage = read_number(base / 'voltage_now')
        native_power = read_number(base / 'power_now')
        derived = abs(current * voltage) / 1e12 if current is not None and voltage is not None else None
        power = abs(native_power) / 1e6 if native_power is not None else derived
        # Driver-reported battery flow, not application-attributed energy.
        if power is not None and not 0 <= power <= 100:
            power = None
        batteries.append({'path': str(base), 'status': status,
                          'capacity_percent': read_number(base / 'capacity'),
                          'temperature_c': (lambda x: None if x is None else x / 10)(read_number(base / 'temp')),
                          'current_microamp': current, 'voltage_microvolt': voltage,
                          'power_microwatt': native_power, 'discharge_power_w': power if status == 'Discharging' else None,
                          'power_source': 'power_now' if native_power is not None else 'current_now*voltage_now',
                          'charge_microamp_hour': read_number(base / 'charge_now'),
                          'energy_microwatt_hour': read_number(base / 'energy_now')})
    return batteries


def thermal_sysfs(root=Path('/sys')):
    rows = []
    for base in sorted((root / 'class/thermal').glob('thermal_zone*')):
        value = read_number(base / 'temp')
        try:
            name = (base / 'type').read_text().strip()
        except OSError:
            name = None
        temperature = value / 1000 if value is not None else None
        if temperature is not None and -20 <= temperature <= 150:
            rows.append({'path': str(base), 'type': name, 'temperature_c': temperature})
    return rows


def termux_battery(enabled, android, executable=None):
    if not enabled or not android:
        return {'status': 'DISABLED', 'raw': None}
    executable = executable or shutil.which('termux-battery-status')
    if not executable:
        return {'status': 'UNAVAILABLE', 'raw': None}
    try:
        result = subprocess.run([executable], capture_output=True, text=True, timeout=2)
        raw = json.loads(result.stdout) if result.returncode == 0 else None
        if not isinstance(raw, dict):
            return {'status': 'INVALID_OR_DENIED', 'raw': None, 'exit_code': result.returncode}
        # Keep original field names and values. No guessed current/energy unit.
        return {'status': 'OBSERVED', 'raw': raw}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {'status': 'UNAVAILABLE_OR_DENIED', 'raw': None}


def descendants(pid, proc_root=Path('/proc')):
    """Read only this process tree. start_ticks guards against PID reuse."""
    rows = []
    pending = [pid]
    seen = set()
    while pending and len(seen) < 128:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        try:
            stat = (proc_root / str(current) / 'stat').read_text().rsplit(')', 1)[1].split()
            memory = process_memory(current)
            memory.update(start_ticks=int(stat[19]), command=None)
            try:
                memory['command'] = (proc_root / str(current) / 'comm').read_text().strip()
            except OSError:
                pass
            rows.append(memory)
            # Runners are often spawned by a coordinator thread, so all tasks
            # matter. A kernel without the children ABI still permits root RSS.
            for task in (proc_root / str(current) / 'task').glob('*'):
                try:
                    pending.extend(int(x) for x in (task / 'children').read_text().split())
                except (OSError, ValueError):
                    pass
        except (OSError, ValueError, IndexError):
            continue
    return rows


def measure(home, child_pid=None, include_termux=False):
    measured = snapshot(home)
    try:
        proc_self_pid = int(Path('/proc/self/stat').read_text().split()[0])
    except (OSError, ValueError, IndexError):
        proc_self_pid = None
    measured.update(monotonic_s=time.monotonic(), android=device()['android'],
                    batteries=battery_sysfs(), thermal_zones=thermal_sysfs(),
                    termux_battery=termux_battery(include_termux, device()['android']),
                    subprocess_tree=descendants(child_pid) if child_pid else [],
                    collector_proc_memory=process_memory('self'),
                    proc_pid_namespace_matches=None if proc_self_pid is None else proc_self_pid == os.getpid())
    values = [x['rss_bytes'] for x in measured['subprocess_tree'] if x.get('rss_bytes') is not None]
    measured['subprocess_tree_rss_sum_bytes'] = sum(values) if values else None
    measured['kv_cache_bytes'] = None
    return measured


class Summary:
    """Online descriptive statistics; never infer a leak from differing process lifetimes."""
    def __init__(self, interval):
        self.interval = interval
        self.samples = 0
        self.rss_peak = None
        self.thermal_peak = None
        self.energy_joules = 0.0
        self.energy_intervals = 0
        self.energy_seconds = 0.0
        self.previous = None
        self.started = self.ended = None
        self.processes = {}
        self.namespace_mismatch = False
        self.collector_rss_peak = None

    def add(self, row):
        self.samples += 1
        now = row['monotonic_s']
        if self.started is None:
            self.started = now
        self.ended = now
        self.namespace_mismatch |= row.get('proc_pid_namespace_matches') is False
        own_rss = number(row.get('collector_proc_memory', {}).get('rss_bytes'))
        if own_rss is not None:
            self.collector_rss_peak = max(self.collector_rss_peak or 0, own_rss)
        rss = number(row.get('subprocess_tree_rss_sum_bytes'))
        if rss is not None:
            self.rss_peak = max(self.rss_peak or 0, rss)
        temps = [number(x.get('temperature_c')) for x in row.get('thermal_zones', []) + row.get('batteries', [])]
        temps = [x for x in temps if x is not None]
        if temps:
            self.thermal_peak = max(self.thermal_peak if self.thermal_peak is not None else -100, max(temps))
        # Exactly one battery and valid adjacent discharging samples. Do not bridge
        # missing/charging samples, suspend, cancellation or another boot/run.
        current = row.get('batteries', [])
        if self.previous is not None:
            prior = self.previous.get('batteries', [])
            dt = now - self.previous['monotonic_s']
            if len(current) == len(prior) == 1 and current[0]['path'] == prior[0]['path'] and 0 < dt <= self.interval * 2.5:
                a, b = number(prior[0].get('discharge_power_w')), number(current[0].get('discharge_power_w'))
                if a is not None and b is not None:
                    self.energy_joules += (a + b) / 2 * dt
                    self.energy_intervals += 1
                    self.energy_seconds += dt
        for p in row.get('subprocess_tree', []):
            value = number(p.get('rss_bytes'))
            if value is None:
                continue
            key = str(p['pid']) + ':' + str(p.get('start_ticks'))
            state = self.processes.get(key)
            if state is None:
                if len(self.processes) >= 2048:
                    continue
                self.processes[key] = state = {'pid': p['pid'], 'start_ticks': p.get('start_ticks'), 'command': p.get('command'),
                                               'samples': 0, 'first_rss_bytes': value, 'last_rss_bytes': value,
                                               'peak_rss_bytes': value, 'first_monotonic_s': now, 'last_monotonic_s': now}
            state.update(samples=state['samples'] + 1, last_rss_bytes=value,
                         peak_rss_bytes=max(state['peak_rss_bytes'], value), last_monotonic_s=now)
        self.previous = row

    def report(self):
        rows = []
        for value in self.processes.values():
            row = dict(value)
            row['observed_rss_delta_bytes'] = row['last_rss_bytes'] - row['first_rss_bytes'] if row['samples'] >= 2 else None
            duration = row['last_monotonic_s'] - row['first_monotonic_s']
            row['endpoint_rss_delta_bytes_per_second'] = row['observed_rss_delta_bytes'] / duration if duration > 0 else None
            rows.append(row)
        return {'samples': self.samples, 'subprocess_tree_rss_sum_peak_bytes': self.rss_peak,
                'thermal_sensor_peak_c': self.thermal_peak,
                'battery_discharge_energy_joules_observed_intervals': self.energy_joules if self.energy_intervals else None,
                'energy_observed_seconds': self.energy_seconds, 'energy_intervals': self.energy_intervals,
                'sampled_duration_s': 0 if self.started is None else self.ended - self.started,
                'collector_rss_peak_bytes': self.collector_rss_peak,
                'proc_pid_namespace_mismatch_observed': self.namespace_mismatch,
                'process_lifetimes': rows, 'kv_cache_bytes': None,
                'claim_limit': 'Endpoint RSS differences are descriptive, not a leak test. RSS sums can double-count shared pages. Battery discharge energy is device-wide, not application-attributed.'}


def source_identity():
    paths = list((APP / 'v13').glob('*.py')) + list((APP / 'specs').glob('*.json')) + [Path(__file__).resolve(), APP / 'TESTEN_LONG.sh',
                                             APP / 'docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md']
    return {str(p.relative_to(APP)): file_hash(p) for p in sorted(paths) if p.is_file()}


def model_identity(home):
    """Hash installed artifacts, once per collector invocation; no downloaded substitutes."""
    manifest = home / 'config/models.json'
    files = {}
    installed = json.loads(manifest.read_text()) if manifest.is_file() else {}
    paths = {home / row['path'] for model in installed.values() for row in model.get('files', {}).values()}
    # Executed native ports and their linked libraries, without hashing build trees.
    paths.update(p for p in (home / 'bin').glob('*') if p.is_file() and (p.suffix == '.so' or p.name in {'llama-server', 'needle-worker', 'native-tap-worker', 'output-adapter-worker'}))
    runner = Path(os.environ.get('V13_LLAMA_SERVER', str(home / 'bin/llama-server'))).expanduser().resolve()
    # Shared libraries next to the effective server include CPU-specific ports.
    paths.update(p for p in runner.parent.glob('*.so*') if p.is_file())
    external = {}
    if runner.is_file() and not runner.is_relative_to(home):
        external[str(runner)] = file_hash(runner)
    elif runner.is_file():
        paths.add(runner)
    for p in sorted(paths):
        if not p.resolve().is_relative_to(home):
            if p.parent == runner.parent:
                external[str(p)] = file_hash(p)
                continue
            raise ValueError('Installed model path escapes home')
        files[str(p.relative_to(home))] = file_hash(p) if p.is_file() else None
    return {'manifest_sha256': file_hash(manifest) if manifest.exists() else None,
            'settings_sha256': file_hash(home / 'config/settings.json') if (home / 'config/settings.json').is_file() else None,
            'artifact_sha256': files, 'effective_external_runner_sha256': external}


def stop_child(proc):
    if proc and proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGINT)
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=10)
        except ProcessLookupError:
            pass


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installed-home', required=True)
    p.add_argument('--out', help='New result directory; existing directories are never overwritten')
    p.add_argument('--resume', help='Resume an interrupted directory with identical source/model hashes')
    p.add_argument('--archive-dir', help='Mirror each completed checkpoint, raw samples and batch proof')
    p.add_argument('--cycles-per-batch', type=int, default=12)
    p.add_argument('--batches', type=int, default=4)
    p.add_argument('--duration-seconds', type=float, default=3600)
    p.add_argument('--sample-seconds', type=float, default=2)
    p.add_argument('--max-samples', type=int, default=20000)
    p.add_argument('--sensors-only', action='store_true', help='Exercise collector without claiming native inference')
    p.add_argument('--termux-battery', action='store_true', help='Use already installed Termux:API battery command')
    p.add_argument('--source-zip', help='Copy existing source ZIP and bind its SHA; never package user state')
    a = p.parse_args(argv)
    if not 4 <= a.cycles_per_batch <= 128 or not 1 <= a.batches <= 32:
        p.error('cycles-per-batch: 4..128; batches: 1..32')
    if not math.isfinite(a.duration_seconds) or not 1 <= a.duration_seconds <= 86400 or not math.isfinite(a.sample_seconds) or not .25 <= a.sample_seconds <= 60 or not 10 <= a.max_samples <= 100000:
        p.error('duration-seconds: 1..86400; sample-seconds: .25..60; max-samples: 10..100000')
    if a.out and a.resume:
        p.error('--out and --resume are mutually exclusive')
    home = Path(a.installed_home).expanduser().resolve()
    if not home.is_dir():
        p.error('installed-home does not exist; run STARTEN.sh first')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out = Path(a.resume or a.out or home / 'exports' / ('phone-epoch-' + stamp)).expanduser().resolve()
    identity = {'source_hashes': source_identity(), 'installed_models': model_identity(home)}
    settings = {k: getattr(a, k) for k in ('cycles_per_batch', 'batches', 'duration_seconds', 'sample_seconds', 'max_samples', 'sensors_only', 'termux_battery')}
    if a.resume:
        report = json.loads((out / 'summary.json').read_text())
        if report.get('schema') != SCHEMA or report.get('identity') != identity or report.get('settings') != settings or report.get('installed_home') != str(home):
            p.error('Resume requires the same source, installed model artifacts, home and collector settings')
        if report['status'] in {'COLLECTION_COMPLETE', 'PHONE_BOUNDED_COLLECTION_PASS', 'NON_PHONE_BOUNDED_COLLECTION_PASS'}:
            p.error('Completed runs are immutable; start a new run')
        for row in report['attempts']:
            if row.get('artifact_sha256') and file_hash(out / row['artifact']) != row['artifact_sha256']:
                p.error('Stored native proof changed; resume refused')
            if row['status'] == 'RUNNING':
                row.update(status='INTERRUPTED_BY_RESTART', error='Previous collector did not finish this attempt')
        for row in report['invocations']:
            if row.get('samples_sha256') and file_hash(out / row['samples_file']) != row['samples_sha256']:
                p.error('Stored sensor evidence changed; resume refused')
            if row['status'] == 'RUNNING':
                row['status'] = 'INTERRUPTED_BY_RESTART'
                recovered_raw = out / row['samples_file']
                if recovered_raw.is_file():
                    row['recovered_raw_sha256'] = file_hash(recovered_raw)
                    row['recovery_index_may_omit_last_sample'] = True
    else:
        out.mkdir(parents=True, exist_ok=False)
        report = {'schema': SCHEMA, 'status': 'RUNNING', 'created_utc': stamp, 'device': device(),
                  'installed_home': str(home), 'identity': identity, 'settings': settings,
                  'attempts': [], 'invocations': [], 'hardware_epoch_complete': False,
                  'canonical_architecture_complete': False}
    archive = Path(a.archive_dir).expanduser().resolve() if a.archive_dir else None
    if archive and (archive == out or archive.is_relative_to(out) or out.is_relative_to(archive)):
        p.error('archive-dir must be separate from the result directory')
    if archive:
        archive.mkdir(parents=True, exist_ok=True)
        if any(archive.iterdir()) and not a.resume:
            p.error('New archive-dir must be empty')
    if a.source_zip:
        source_zip = Path(a.source_zip).expanduser().resolve()
        if source_zip == out / 'source.zip':
            p.error('source-zip must be outside the result directory')
        digest = file_hash(source_zip)
        if report.get('source_zip_sha256') not in {None, digest}:
            p.error('Resume source ZIP hash changed')
        shutil.copyfile(source_zip, out / 'source.zip')
        report['source_zip_sha256'] = digest
    cancelled = [False]
    old_handlers = {}
    for sig in (signal.SIGINT, signal.SIGTERM):
        old_handlers[sig] = signal.signal(sig, lambda signum, frame: cancelled.__setitem__(0, True))
    index = len(report['invocations'])
    raw_path = out / f'samples-{index:03d}.jsonl'
    state = Summary(a.sample_seconds)
    invocation = {'index': index, 'started_utc': stamp, 'status': 'RUNNING', 'samples_file': raw_path.name}
    report['invocations'].append(invocation)
    report['status'] = 'RUNNING'
    proc = None
    started = time.monotonic()
    end = started + a.duration_seconds
    next_sample = started
    raw = raw_path.open('x', encoding='utf-8')

    def save():
        raw.flush()
        os.fsync(raw.fileno())
        invocation['observations'] = state.report()
        atomic_write(out / 'summary.json', json.dumps(report, ensure_ascii=False, indent=2))
        if archive:
            for f in out.iterdir():
                if f.is_file() and f.name != 'summary.json':
                    target = archive / f.name
                    if f.suffix in {'.jsonl', '.log'}:
                        # These files only grow; avoid copying their entire history
                        # every sample. Publish the index only after durable bytes.
                        offset = target.stat().st_size if target.exists() else 0
                        if offset > f.stat().st_size:
                            raise ValueError('Archive append-only evidence exceeds source')
                        with f.open('rb') as src, target.open('ab') as dst:
                            src.seek(offset)
                            shutil.copyfileobj(src, dst)
                            dst.flush()
                            os.fsync(dst.fileno())
                    elif not target.exists():
                        atomic_write(target, f.read_bytes())
            atomic_write(archive / 'summary.json', json.dumps(report, ensure_ascii=False, indent=2))

    def sample():
        nonlocal next_sample
        row = measure(home, proc.pid if proc and proc.poll() is None else None, a.termux_battery)
        row['invocation'] = index
        raw.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
        state.add(row)
        next_sample = time.monotonic() + a.sample_seconds
        save()

    def expired():
        return cancelled[0] or time.monotonic() >= end or state.samples >= a.max_samples

    try:
        save()
        sample()
        completed = {x['batch'] for x in report['attempts'] if x.get('status') == 'PASS'}
        if a.sensors_only:
            while not expired():
                if time.monotonic() >= next_sample:
                    sample()
                time.sleep(min(.1, a.sample_seconds))
            report['status'] = 'INTERRUPTED' if cancelled[0] else ('SAMPLE_LIMIT_PARTIAL' if state.samples >= a.max_samples and time.monotonic() < end else 'COLLECTION_COMPLETE')
        else:
            for batch in range(a.batches):
                if batch in completed:
                    continue
                if expired():
                    break
                attempt_index = len(report['attempts'])
                prefix = f'batch-{batch:03d}-attempt-{attempt_index:03d}'
                row = {'batch': batch, 'attempt': attempt_index, 'status': 'RUNNING', 'log': prefix + '.log',
                       'artifact': prefix + '.json', 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
                report['attempts'].append(row)
                save()
                # Existing native implementation and its exact existing gates.
                source = home / 'exports/sustained-proof.json'
                old_source = file_hash(source) if source.exists() else None
                command = [sys.executable, '-m', 'v13', '--home', str(home), 'probe', 'sustained', '--cycles', str(a.cycles_per_batch)]
                print(f'Native Messung {batch + 1}/{a.batches}; Fortschritt: {out}', flush=True)
                with (out / row['log']).open('xb') as log:
                    proc = subprocess.Popen(command, cwd=APP, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                    while proc.poll() is None and not expired():
                        if time.monotonic() >= next_sample:
                            sample()
                        time.sleep(.1)
                    if proc.poll() is None:
                        stop_child(proc)
                    row['exit_code'] = proc.returncode
                proc = None
                if source.is_file() and file_hash(source) != old_source:
                    shutil.copyfile(source, out / row['artifact'])
                    row['artifact_sha256'] = file_hash(out / row['artifact'])
                    data = json.loads((out / row['artifact']).read_text())
                    row['observed_status'] = data.get('status')
                    row['restarts'] = data.get('restarts', [])
                    row['native_turns'] = len(data.get('turns', []))
                    row['status'] = 'PASS' if row['exit_code'] == 0 and data.get('status') == 'BOUNDED_STABILITY_PASS' and data.get('phone_measured') == report['device']['android'] and data.get('requested_cycles') == a.cycles_per_batch else 'FAIL'
                else:
                    row['status'] = 'FAIL'
                    row['error'] = 'No new native sustained artifact; no stale result accepted'
                if cancelled[0]:
                    row['status'] = 'INTERRUPTED'
                save()
                if row['status'] != 'PASS':
                    break
            passed = {x['batch'] for x in report['attempts'] if x['status'] == 'PASS'}
            report['status'] = ('PHONE_BOUNDED_COLLECTION_PASS' if report['device']['android'] else 'NON_PHONE_BOUNDED_COLLECTION_PASS') if len(passed) == a.batches else ('INTERRUPTED' if cancelled[0] else 'PARTIAL')
        invocation['status'] = report['status']
    except Exception as exc:
        stop_child(proc)
        report['status'] = invocation['status'] = 'FAILED'
        invocation['error'] = type(exc).__name__ + ': ' + str(exc)[:500]
    finally:
        stop_child(proc)
        invocation['duration_s'] = time.monotonic() - started
        invocation['observations'] = state.report()
        report['gates'] = {'target_phone': report['device']['android'],
                           'native_sustained_batches': not a.sensors_only and len({x['batch'] for x in report['attempts'] if x['status'] == 'PASS'}) == a.batches,
                           'thermal_sensor_observed': any(x.get('observations', {}).get('thermal_sensor_peak_c') is not None for x in report['invocations']),
                           'battery_energy_intervals_observed': any(x.get('observations', {}).get('energy_intervals', 0) > 0 for x in report['invocations']),
                           'native_runner_rss_observed': any(any(p.get('command') in {'llama-server', 'needle-worker', 'native-tap-work', 'output-adapter-'} for p in x.get('observations', {}).get('process_lifetimes', [])) for x in report['invocations']),
                           'native_kv_growth_measured': False, 'long_term_retention_proven': False,
                           'source_unchanged_during_collection': source_identity() == identity['source_hashes'],
                           'installed_artifacts_unchanged_during_collection': model_identity(home) == identity['installed_models']}
        if not report['gates']['source_unchanged_during_collection'] or not report['gates']['installed_artifacts_unchanged_during_collection']:
            report['status'] = invocation['status'] = 'SOURCE_CHANGED_PARTIAL'
        report['missing_proofs'] = [k for k, v in report['gates'].items() if not v]
        report['claim_limits'] = ['This collection never completes the full STEP7 hardware epoch.',
                                 'Linux is not Redmi; prior phone SMOKE_PASS is not this new source proof.',
                                 'Missing or denied sensors stay null. Battery energy is device-wide.',
                                 'Current sustained probe sets history_turns=0 and route=simple. It does not test persistent KV growth, B1/B2 residency or all routing paths.',
                                 'Independent process lifetimes are not stitched into a memory-leak trend.',
                                 'Interrupted samples and failed attempts are retained; resume does not change their result.']
        save()
        raw.close()
        report['invocations'][-1]['samples_sha256'] = file_hash(raw_path)
        # Final raw-file hash is part of the same durable summary checkpoint.
        atomic_write(out / 'summary.json', json.dumps(report, ensure_ascii=False, indent=2))
        if archive:
            shutil.copyfile(out / 'summary.json', archive / 'summary.json')
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
    print(report['status'] + '\nBerichte: ' + str(out) + '\nFehlende Proofs: ' + ', '.join(report['missing_proofs']), flush=True)
    return 130 if report['status'] == 'INTERRUPTED' else (0 if report['status'] in {'COLLECTION_COMPLETE', 'PHONE_BOUNDED_COLLECTION_PASS', 'NON_PHONE_BOUNDED_COLLECTION_PASS'} else 2)


if __name__ == '__main__':
    sys.exit(main())
