#!/usr/bin/env python3
"""WP-Z7 Handy-Paket für alle Handy-Pflichtmessungen: ein Befehl auf dem Redmi (Termux), ein Ergebnis-ZIP in Downloads.

Thin orchestration around existing, unchanged measurement scripts; it adds no gate, plan or authority. Steps run one
after another, each with its own deadline and folder; a finished step is skipped on the next start (resume), `--neu`
starts over. Order = importance for the open §100/STEP7 gates:
  ram          scripts/ram_budget_bench.py single,variants,combo        WP-R / §24.33 RSS, "braucht AGI 8 GB?"
  residenz     scripts/z7_residency_bench.py --mode schedules           §24.33 scheduling/residency + §24.14 overhead
  wiederholung scripts/z7_residency_bench.py --mode repeat              proceduralization latency (G-PROCEDURALIZATION-004)
  werkzeug     scripts/werkzeug_handy.py kurz                           tool forecast on the device
  langlauf     scripts/longrun_soak.py --native                         G-MOBILE-LONGRUN-001 (software + native, simulated days)
  training     scripts/train_runner_proof.py                            G-TRAIN-RUNNER-PROOF-001 for the STEP5 route-head runner
Uses the precheck, wake lock, system trace and ZIP collector of scripts/werkzeug_handy.py.
  bash HANDY_PFLICHT.sh [kurz|voll] [--nur ram,residenz] [--neu] [--trotzdem]
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP/'scripts'))
import werkzeug_handy as W  # noqa: E402

SCHEMA = 'V13_HANDY_PFLICHT_V1'
# step -> (title, {stage: (argv builder, deadline s)})
STEPS = ('ram', 'training', 'residenz', 'wiederholung', 'werkzeug', 'langlauf')
TITLES = {'ram': 'RAM aller Modelle (WP-R, §24.33)', 'residenz': 'Beobachter-Reihenfolge und Residenz (§24.33, §24.14)',
          'wiederholung': 'Wiederholte Aufgaben: wird es schneller? (Proceduralization)', 'werkzeug': 'Werkzeug-Vorhersage',
          'langlauf': 'Langlauf über mehrere simulierte Tage (G-MOBILE-LONGRUN-001)', 'training': 'Trainings-Nachweis Routen-Kopf (G-TRAIN-RUNNER-PROOF-001)'}


def commands(step, stage, home, out):
    py = sys.executable; s = APP/'scripts'; quick = stage == 'kurz'
    if step == 'ram':
        return [py, str(s/'ram_budget_bench.py'), '--binary', str(home/'bin/llama-server'), '--models-dir', str(home/'models'),
                '--out', str(out/'ram-budget.json'), '--scenarios', 'single,variants,combo', '--turns', '2' if quick else '3'], 3*3600
    if step == 'residenz':
        return [py, str(s/'z7_residency_bench.py'), str(home), str(out/'residency.json'), '--mode', 'schedules',
                '--per-kind', '1' if quick else '3'], (3 if quick else 8)*3600
    if step == 'wiederholung':
        return [py, str(s/'z7_residency_bench.py'), str(home), str(out/'repeat.json'), '--mode', 'repeat', '--repeat', '12' if quick else '24'], (2 if quick else 5)*3600
    if step == 'werkzeug':
        return [py, str(s/'werkzeug_handy.py'), 'kurz', '--installed-home', str(home), '--no-setup', '--target-dir', str(out)], 5*3600
    if step == 'langlauf':
        return [py, str(s/'longrun_soak.py'), '--home', str(out/'soak-home'), '--days', '2' if quick else '7', '--native', '--models-from', str(home)], (3 if quick else 10)*3600
    if step == 'training':
        return [py, str(s/'train_runner_proof.py'), '--installed-home', str(home), '--out', str(out), '--kills', '24' if quick else '64'], 2*3600
    return None, 0


def run_step(step, stage, home, folder, log):
    folder.mkdir(parents=True, exist_ok=True)
    cmd, deadline = commands(step, stage, home, folder)
    if cmd is None:
        return {'step': step, 'status': 'NOT_BUILT', 'reason': 'TrainRunnerProof (cancel/crash/resume/rollback/retention/energy) ist noch nicht gebaut; '
                'kommt als eigenes Paket. Kein Ersatzwert.'}
    t0 = time.monotonic(); env = dict(os.environ, PYTHONPATH=str(APP), V13_HOME=str(home))
    with open(log, 'ab') as fh:
        fh.write(('\n== %s %s ==\n%s\n' % (step, time.strftime('%Y-%m-%d %H:%M:%S'), ' '.join(cmd))).encode())
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env, start_new_session=True)
        try:
            rc = proc.wait(timeout=deadline); status = 'DONE' if rc == 0 else 'FAILED'
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, 15)
            try: proc.wait(60)
            except subprocess.TimeoutExpired: os.killpg(proc.pid, 9); proc.wait()
            rc, status = None, 'DEADLINE'
        except KeyboardInterrupt:
            os.killpg(proc.pid, 2); proc.wait(); rc, status = None, 'INTERRUPTED'
    if step == 'werkzeug':  # its own result ZIP lands here; unpack the small text reports so the outer ZIP carries them
        import zipfile
        for zp in folder.glob('V13-Werkzeug-Ergebnis-*.zip'):
            with zipfile.ZipFile(zp) as z:
                for n in z.namelist():
                    if Path(n).suffix in W.COLLECT_SUFFIXES and not Path(n).is_absolute() and '..' not in Path(n).parts:
                        z.extract(n, folder/'ergebnis')
    return {'step': step, 'status': status, 'exit_code': rc, 'minutes': round((time.monotonic()-t0)/60, 1), 'deadline_h': deadline/3600}


def enable_eligibility(home):
    """User decision 2026-10-22 („Ja, beide an im Handy-Paket“): the eligibility tool is enabled in the installed home before
    the measurements (Age 0 = SHADOW with comparison; rules only from the fixed reader). Same call as `:growth enable eligibility`."""
    try:
        from v13.runtime import Runtime
        from v13.agi import hub
        r = Runtime(home)
        try:
            hub(r).tools.enable('eligibility'); return {'eligibility_enabled': True, 'eligibility_reader': r.cfg.get('eligibility_reader'),
                                                         'tool_answer_first': r.cfg.get('tool_answer_first')}
        finally:
            r.close()
    except Exception as exc:
        return {'eligibility_enabled': False, 'error': str(exc)[:200]}


def short_text(stage, check, results, trace):
    lines = ['V13 Handy-Pflichtmessungen', '==========================', '', 'Stufe: %s' % stage]
    mem = check.get('mem', {})
    lines.append('Gerät: %s CPU-Kerne, RAM gesamt %s MB, frei vor Start %s MB' % (check.get('cpu_count'), mem.get('MemTotal'), mem.get('MemAvailable')))
    if trace.get('mem_available_min_mb') is not None: lines.append('Kleinster freier RAM: %d MB' % trace['mem_available_min_mb'])
    if trace.get('battery_temp_max_c') is not None: lines.append('Höchste Akku-Temperatur: %.1f °C' % trace['battery_temp_max_c'])
    lines.append('')
    word = {'DONE': 'fertig', 'FAILED': 'Fehler', 'DEADLINE': 'Zeit abgelaufen (Teilergebnis)', 'INTERRUPTED': 'abgebrochen',
            'NOT_BUILT': 'noch nicht gebaut', 'SKIPPED_DONE': 'schon fertig (übersprungen)'}
    for r in results:
        lines.append('- %s: %s%s' % (TITLES[r['step']], word.get(r['status'], r['status']), ', %.0f min' % r['minutes'] if r.get('minutes') else ''))
    lines += ['', 'Nur Messung: nichts wurde eingeschaltet, keine Lernrechte vergeben.', 'Bitte diese ZIP-Datei in den Claude-Chat hochladen.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', nargs='?', default='kurz', choices=('kurz', 'voll'))
    ap.add_argument('--installed-home'); ap.add_argument('--nur', default='', help='nur diese Schritte, z. B. ram,residenz')
    ap.add_argument('--neu', action='store_true', help='fertige Schritte nicht überspringen')
    ap.add_argument('--trotzdem', action='store_true'); ap.add_argument('--target-dir'); ap.add_argument('--no-setup', action='store_true')
    a = ap.parse_args(argv)
    steps = [s for s in (a.nur.split(',') if a.nur else STEPS) if s]
    if any(s not in STEPS for s in steps): ap.error('Schritte: ' + ','.join(STEPS))
    from v13.config import home_path
    home = home_path(a.installed_home); check = W.precheck(home, a.stage)
    for t in check['warnings']: print('Hinweis: ' + t, flush=True)
    if not check['installed']:
        if a.no_setup or check['problems'] or W.run_setup(home) != 0:
            print('STOPP: V13 ist nicht eingerichtet. Zuerst `bash setup.sh` ausführen.', flush=True); return 2
        check = W.precheck(home, a.stage)
    if check['problems']:
        for t in check['problems']: print(('WARNUNG: ' if a.trotzdem else 'STOPP: ') + t, flush=True)
        if check['chat_running'] or not a.trotzdem: return 2
    root = home/'exports'/('handy-pflicht-' + a.stage); root.mkdir(parents=True, exist_ok=True)
    state_path = root/'zustand.json'
    state = json.loads(state_path.read_text()) if state_path.exists() and not a.neu else {'steps': {}}
    print('\nHandy-Pflichtmessungen starten (Stufe %s, Schritte: %s). Handy am Ladegerät, Termux offen lassen.\n'
          'Abbrechen mit Strg+C; fertige Schritte bleiben, ein neuer Start macht weiter.\n' % (a.stage, ', '.join(steps)), flush=True)
    tools = enable_eligibility(home); print('Eignungs-Werkzeug: %s' % ('an (SHADOW bei Age 0)' if tools.get('eligibility_enabled') else 'nicht aktiviert: ' + tools.get('error', '')), flush=True)
    locked = W.wake_lock(True); results = []
    try:
        with W.SystemTrace(every=30.) as trace:
            for step in steps:
                if state['steps'].get(step, {}).get('status') == 'DONE':
                    results.append({'step': step, 'status': 'SKIPPED_DONE'}); continue
                print('Schritt: %s ...' % TITLES[step], flush=True)
                res = run_step(step, a.stage, home, root/step, root/'ablauf.log'); results.append(res)
                state['steps'][step] = res; state_path.write_text(json.dumps(state, indent=1))
                print('  -> %s' % res['status'], flush=True)
                if res['status'] == 'INTERRUPTED': break
    finally:
        if locked: W.wake_lock(False)
    traced = trace.summary(); stamp = time.strftime('%Y%m%d-%H%M%S')
    text = short_text(a.stage, check, results, traced)
    receipt = {'schema': SCHEMA, 'stage': a.stage, 'precheck': check, 'tools': tools, 'results': results, 'state': state, 'system_trace': traced, 'authority': 0}
    target = Path(a.target_dir).expanduser() if a.target_dir else W.downloads_dir(home)
    zp = W.collect(root, target/('V13-Pflicht-Ergebnis-%s-%s.zip' % (a.stage, stamp)),
                   {'KURZ.txt': text, 'paket-bericht.json': json.dumps(receipt, indent=2, sort_keys=True)+'\n'})
    print('\n' + text + '\nErgebnis-ZIP: %s' % zp, flush=True)
    return 0 if all(r['status'] in ('DONE', 'SKIPPED_DONE', 'NOT_BUILT') for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
