#!/usr/bin/env python3
"""Handy-Paket Werkzeug-Vorhersage: one command on the Redmi (Termux), result ZIP in Downloads.

Thin orchestration around the existing, unchanged device path. It adds no forecast, plan, gate or authority:
1. Vorprüfung: Termux?, RAM (MemTotal/MemAvailable), freier Speicher, Installation (B2-GGUF), kein laufender Chat.
2. Falls V13 noch nicht eingerichtet ist: `setup.sh` (ohne Chat-Autostart) und erneute Vorprüfung.
3. `termux-wake-lock` (falls vorhanden), dann scripts/tool_forecast_bounded_phone_candidate.py mit Frist
   (stufe paritaet = --skip-live, kurz = Parität + 245 Live-Aufrufe, voll = zusätzlich 610 Lern-Aufrufe).
   Nebenher alle 10 s MemAvailable / Akku-Temperatur (nur lesbare Quellen) als Systemverlauf.
4. Ergebnis-ZIP (nur Berichte/Logs, keine Modelle, keine Taps) nach ~/storage/downloads, dazu KURZ.txt auf Deutsch.
The model report device-check/report.json stays the only source of PASS/FAIL; this file never rewrites it.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
import zipfile

APP = Path(__file__).resolve().parents[1]
BOUNDED = APP / 'scripts/tool_forecast_bounded_phone_candidate.py'
SCHEMA = 'V13_WERKZEUG_HANDY_PACKAGE_V1'
STAGES = {  # stage -> (extra driver flags, deadline seconds)
    'paritaet': (['--skip-live'], 2 * 3600),
    'kurz': ([], 4 * 3600),
    'voll': (['--with-learning'], 10 * 3600),
}
MIN_AVAILABLE_MB = 1500      # tap process peaks at ~1 GB RSS (cloud); below this the run is not meaningful
MIN_FREE_DISK_MB = 1024      # results are small; the native taps build needs some room
SETUP_FREE_DISK_MB = 3072    # first install: ~0.9 GB models + llama.cpp source/build
COLLECT_MAX_BYTES = 8 << 20  # per file; logs/reports only
COLLECT_SUFFIXES = {'.json', '.log', '.txt', '.md'}
OK_STATUSES = {'PARITY_PASS_NO_LIVE', 'LIVE_PATH_CONFIRMED', 'LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED'}


def meminfo(path='/proc/meminfo'):
    out = {}
    try:
        for line in Path(path).read_text().splitlines():
            key, _, rest = line.partition(':')
            if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
                out[key] = int(rest.split()[0]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return out


def battery_temperature(root='/sys/class/power_supply'):
    """Battery temperature in °C if the kernel exposes it to the app (often not on Android 10+); else None."""
    for name in ('battery', 'Battery', 'bms'):
        try:
            return int(Path(root, name, 'temp').read_text().strip()) / 10.
        except (OSError, ValueError):
            continue
    return None


def is_termux():
    return 'com.termux' in os.environ.get('PREFIX', '')


def installed(home):
    """(True, path) if the B2 GGUF the forecast needs is installed with its recorded size, else (False, reason)."""
    if not (home / 'bin/v13').is_file():
        return False, 'V13 ist noch nicht eingerichtet (kein ' + str(home / 'bin/v13') + ')'
    try:
        from v13.models import ModelManager
        return True, str(ModelManager(home).path_for('B2_GIST'))
    except Exception as exc:  # Unavailable or a damaged installation record
        return False, 'B2-Modell fehlt: ' + str(exc)[:200]


def chat_running(home):
    path = home / 'data/coordinator.lock'
    if not path.exists():
        return False
    with path.open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True
        fcntl.flock(lock, fcntl.LOCK_UN)
    return False


def precheck(home, stage):
    mem = meminfo()
    probe = home if home.exists() else home.parent
    free_mb = shutil.disk_usage(probe).free // (1 << 20)
    ok, model = installed(home)
    check = {'termux': is_termux(), 'stage': stage, 'mem': mem, 'disk_free_mb': free_mb,
             'installed': ok, 'model': model if ok else None, 'chat_running': ok and chat_running(home),
             'battery_temp_c': battery_temperature(), 'cpu_count': os.cpu_count(), 'problems': [], 'warnings': []}
    if not check['termux']:
        check['warnings'].append('Kein Termux erkannt (Linux-Probelauf).')
    if not ok:
        check['warnings'].append(model)
        if free_mb < SETUP_FREE_DISK_MB:
            check['problems'].append('Zu wenig Speicher für die Einrichtung: %d MB frei, %d MB nötig.' % (free_mb, SETUP_FREE_DISK_MB))
    elif free_mb < MIN_FREE_DISK_MB:
        check['problems'].append('Zu wenig freier Speicher: %d MB frei, %d MB nötig.' % (free_mb, MIN_FREE_DISK_MB))
    if check['chat_running']:
        check['problems'].append('Ein V13-Chat oder anderer Test läuft noch. Dort :shutdown eingeben, dann erneut starten.')
    available = mem.get('MemAvailable')
    if available is not None and available < MIN_AVAILABLE_MB:
        check['problems'].append('Nur %d MB RAM frei, mindestens %d MB nötig. Andere Apps schließen (Browser, Spiele) und erneut starten.'
                                 % (available, MIN_AVAILABLE_MB))
    return check


class SystemTrace:
    """Samples MemAvailable and battery temperature every `every` seconds while the check runs."""

    def __init__(self, every=10.):
        self.every, self.rows, self.stop = every, [], threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.t0 = time.monotonic()

    def _run(self):
        while True:
            mem = meminfo()
            self.rows.append({'t': round(time.monotonic() - self.t0, 1), 'mem_available_mb': mem.get('MemAvailable'),
                              'swap_free_mb': mem.get('SwapFree'), 'battery_temp_c': battery_temperature()})
            if self.stop.wait(self.every):
                return

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(5)

    def summary(self):
        mem = [r['mem_available_mb'] for r in self.rows if r['mem_available_mb'] is not None]
        temp = [r['battery_temp_c'] for r in self.rows if r['battery_temp_c'] is not None]
        return {'samples': len(self.rows), 'mem_available_min_mb': min(mem) if mem else None,
                'battery_temp_max_c': max(temp) if temp else None, 'rows': self.rows}


def wake_lock(on):
    tool = 'termux-wake-lock' if on else 'termux-wake-unlock'
    if shutil.which(tool):
        subprocess.run([tool], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return True
    return False


def downloads_dir(home):
    for path in (Path.home() / 'storage/downloads', Path('/sdcard/Download')):
        if path.is_dir() and os.access(path, os.W_OK):
            return path
    return home / 'exports'


def ratio_line(ratios):
    return ', '.join('%s %.2f' % (k, v) for k, v in sorted(ratios.items()) if isinstance(v, (int, float)))


def summarize(stage, check, wrapper, child, trace):
    """German short text for the user. Reads reports only; never decides PASS itself."""
    status = (child or {}).get('status', 'KEIN_BERICHT')
    lines = ['V13 Werkzeug-Vorhersage auf dem Handy', '======================================', '',
             'Stufe: %s' % stage, 'Gesamtstatus: %s' % status,
             'Ablauf: %s (Exit %s, %.0f Minuten)' % (wrapper.get('status'), wrapper.get('driver_exit_code'),
                                                    (wrapper.get('elapsed_seconds') or 0) / 60.)]
    mem = check.get('mem', {})
    lines.append('Gerät: %s CPU-Kerne, RAM gesamt %s MB, frei vor Start %s MB, Termux %s'
                 % (check.get('cpu_count'), mem.get('MemTotal'), mem.get('MemAvailable'), 'ja' if check.get('termux') else 'nein'))
    if trace.get('mem_available_min_mb') is not None:
        lines.append('Kleinster freier RAM während der Prüfung: %d MB' % trace['mem_available_min_mb'])
    if trace.get('battery_temp_max_c') is not None:
        lines.append('Höchste Akku-Temperatur: %.1f °C' % trace['battery_temp_max_c'])
    if child:
        parity = child.get('parity') or {}
        if parity:
            lines += ['', 'Parität (eigener Tap-Build gegen den Erfassungs-Encoder): %s, %s s'
                      % (parity.get('status'), child.get('parity_seconds'))]
            for world, w in sorted((parity.get('worlds') or {}).items()):
                lines.append('  %s: %s, Verhältnis zur besten Kontrolle %s (kleiner = besser, Grenze %s)'
                             % (world, 'PASS' if w.get('pass') else 'FAIL', ratio_line(w.get('ratio_to_best_control') or {}), parity.get('gate')))
        live = child.get('live') or {}
        if live:
            lines += ['', 'Live-Prüfung (245 feste Aufrufe): %s, Median %s s je Aufruf, Spitzen-RAM Tap-Prozess %s MB'
                      % (live.get('verdict'), live.get('seconds_per_call_median'), live.get('tap_process_max_rss_mb')),
                      '  Aufruf-Status: %s' % json.dumps(live.get('statuses'), sort_keys=True)]
            for arm, actions in sorted((live.get('arms') or {}).items()):
                lines.append('  %s: %s' % (arm, ratio_line({a: v.get('ratio_to_best_control') for a, v in actions.items()})))
        learning = child.get('learning') or {}
        if learning:
            integrity = learning.get('integrity')
            integrity = 'fehlt' if not isinstance(integrity, dict) else 'PASS' if integrity.get('pass') is True else 'FAIL'
            lines += ['', 'Lern-Prüfung (610 feste Aufrufe): %s, %s Minuten, Integrität %s'
                      % (learning.get('verdict'), learning.get('minutes'), integrity)]
            for world, w in sorted((learning.get('worlds') or {}).items()):
                lines.append('  %s: %s, verbesserte Handlungen %s' % (world, 'PASS' if w.get('pass') else 'FAIL', w.get('shift_actions_improved')))
        if child.get('error'):
            lines += ['', 'Fehler: ' + child['error']]
    lines += ['', 'Nur SHADOW-Messung: keine Autorität, nichts wurde aktiviert.',
              'Bitte diese ZIP-Datei in den Claude-Chat hochladen.']
    return '\n'.join(lines) + '\n'


def collect(out, target, extra):
    """ZIP small text reports/logs from the run folder plus `extra` {name: text}. Never models, taps or npz."""
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + '.part')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, text in extra.items():
            archive.writestr(name, text)
        for path in sorted(out.rglob('*')):
            if path.is_file() and not path.is_symlink() and path.suffix in COLLECT_SUFFIXES and path.stat().st_size <= COLLECT_MAX_BYTES:
                archive.write(path, 'lauf/' + path.relative_to(out).as_posix())
    os.replace(temporary, target)
    return target


def run_setup(home):
    env = dict(os.environ, V13_HOME=str(home), V13_NO_AUTOSTART='1')
    print('\nV13 ist noch nicht eingerichtet. Einrichtung startet (lädt ca. 0,9 GB, kann lange dauern) ...\n', flush=True)
    return subprocess.run(['bash', str(APP / 'setup.sh')], env=env, stdin=subprocess.DEVNULL).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', nargs='?', default='kurz', choices=sorted(STAGES))
    ap.add_argument('--installed-home', default=None)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--no-setup', action='store_true', help='never run setup.sh, stop instead')
    ap.add_argument('--trotzdem', action='store_true', help='start despite failed RAM/disk precheck (result is marked)')
    ap.add_argument('--target-dir', default=None, help='where the result ZIP goes (default ~/storage/downloads)')
    args = ap.parse_args(argv)
    if not 1 <= args.threads <= 32:
        ap.error('threads 1..32')
    from v13.config import home_path
    home = home_path(args.installed_home)
    stamp = time.strftime('%Y%m%d-%H%M%S')
    check = precheck(home, args.stage)
    for text in check['warnings']:
        print('Hinweis: ' + text, flush=True)
    if not check['installed']:
        if args.no_setup or check['problems']:
            for text in check['problems']:
                print('STOPP: ' + text, flush=True)
            print('STOPP: V13 ist nicht eingerichtet. Zuerst `bash setup.sh` ausführen.', flush=True)
            return 2
        if run_setup(home) != 0:
            print('STOPP: Einrichtung fehlgeschlagen. Ausgabe oben prüfen; erneut starten setzt fertige Downloads fort.', flush=True)
            return 2
        check = precheck(home, args.stage)
        if not check['installed']:
            print('STOPP: ' + '; '.join(check['warnings']), flush=True)
            return 2
    if check['problems']:
        for text in check['problems']:
            print(('WARNUNG: ' if args.trotzdem else 'STOPP: ') + text, flush=True)
        if check['chat_running'] or not args.trotzdem:
            return 2
    check['forced'] = bool(check['problems'])
    flags, deadline = STAGES[args.stage]
    out = home / 'exports' / ('werkzeug-handy-%s-%s' % (args.stage, stamp))
    print('\nPrüfung startet (Stufe %s, höchstens %d Stunden). Handy am Ladegerät lassen, Termux offen lassen.\n'
          'Abbrechen mit Strg+C (Lautstärke-runter + C); Teilergebnisse bleiben erhalten.\n' % (args.stage, deadline // 3600), flush=True)
    locked = wake_lock(True)
    rc = 1
    try:
        with SystemTrace() as trace:
            command = [sys.executable, str(BOUNDED), '--installed-home', str(home), '--out-dir', str(out),
                       '--timeout-seconds', str(deadline), '--threads', str(args.threads)] + flags
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL)
            try:
                rc = proc.wait()
            except KeyboardInterrupt:   # the bounded wrapper got SIGINT too and cleans up its own process group
                rc = proc.wait()
    finally:
        if locked:
            wake_lock(False)
    def read(path):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return None
    wrapper = read(out / 'wrapper-report.json') or {'status': 'WRAPPER_REPORT_MISSING'}
    child = read(out / 'device-check/report.json')
    traced = trace.summary()
    text = summarize(args.stage, check, wrapper, child, traced)
    receipt = {'schema': SCHEMA, 'stage': args.stage, 'precheck': check, 'bounded_exit_code': rc,
               'wrapper_status': wrapper.get('status'), 'device_status': (child or {}).get('status'),
               'device_checks_confirmed': (child or {}).get('status') in OK_STATUSES and rc == 0,
               'receiver_authority': 0, 'learn_authority': 0, 'system_trace': traced}
    target = Path(args.target_dir).expanduser() if args.target_dir else downloads_dir(home)
    zip_path = collect(out, target / ('V13-Werkzeug-Ergebnis-%s-%s.zip' % (args.stage, stamp)),
                       {'KURZ.txt': text, 'paket-bericht.json': json.dumps(receipt, indent=2, sort_keys=True) + '\n'})
    print('\n' + text)
    print('Ergebnis-ZIP: %s' % zip_path, flush=True)
    return 0 if receipt['device_checks_confirmed'] else 1


if __name__ == '__main__':
    sys.exit(main())
