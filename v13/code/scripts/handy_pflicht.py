#!/usr/bin/env python3
"""WP-Z7 Handy-Paket für alle Handy-Pflichtmessungen: ein Befehl auf dem Redmi (Termux), ein Ergebnis-ZIP in Downloads.

Thin orchestration around existing, unchanged measurement scripts; it adds no gate, plan or authority. Steps run one
after another, each with its own deadline and folder; a verified finished step is skipped on the next start (resume).
Interrupted/changed work stays preserved and requires explicit `--neu` for a separate new attempt.
Order = importance for the open §100/STEP7 gates:
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
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP)); sys.path.insert(0, str(APP/'scripts'))
import werkzeug_handy as W  # noqa: E402
from v13.common import atomic_write, file_hash  # noqa: E402

SCHEMA = 'V13_HANDY_PFLICHT_V2'
# step -> (title, {stage: (argv builder, deadline s)})
STEPS = ('ram', 'training', 'residenz', 'wiederholung', 'werkzeug', 'langlauf')
TITLES = {'ram': 'RAM aller Modelle (WP-R, §24.33)', 'residenz': 'Beobachter-Reihenfolge und Residenz (§24.33, §24.14)',
          'wiederholung': 'Wiederholte Aufgaben: wird es schneller? (Proceduralization)', 'werkzeug': 'Werkzeug-Vorhersage',
          'langlauf': 'Langlauf über mehrere simulierte Tage (G-MOBILE-LONGRUN-001)', 'training': 'Trainings-Nachweis Routen-Kopf (G-TRAIN-RUNNER-PROOF-001)'}

REPORTS = {'ram': 'ram-budget.json', 'training': 'train-runner-proof.json', 'residenz': 'residency.json',
           'wiederholung': 'repeat.json', 'werkzeug': 'ergebnis/lauf/device-check/report.json',
           'langlauf': 'soak-home/exports/longrun-soak.json'}
# These are outputs of the pinned tool measurement's own build/parity path, not pre-existing inference inputs.
# Its completed step binds their bytes separately; all other config and runner files stay global inputs.
DERIVED_TOOL_FILES = ('bin/native-prefill-worker', 'config/native-prefill-worker.json',
                      'bin/native-layer-taps', 'config/native-layer-taps.json')


class ResumeRefused(RuntimeError):
    pass


def input_binding(home, stage):
    """Bind resumable work to code, installed config/revisions, runner bytes and model file identities.

    Model manifests are hashed; large model payloads use stat identity, not a new multi-GB hash on every step.
    The individual native measurement still owns model integrity/compatibility checks and scientific verdicts.
    """
    sources = {}
    for part in ('v13', 'scripts', 'specs', 'tests'):
        for p in sorted((APP/part).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py', '.json', '.cpp', '.h', '.sh', '.patch'):
                sources[p.relative_to(APP).as_posix()] = file_hash(p)
    for p in sorted(APP.glob('*.sh')):
        sources[p.name] = file_hash(p)
    config = {p.relative_to(home).as_posix(): file_hash(p) for p in sorted((home/'config').rglob('*.json'))
              if p.is_file() and p.relative_to(home).as_posix() not in DERIVED_TOOL_FILES}
    runners = {p.relative_to(home).as_posix(): file_hash(p) for p in sorted((home/'bin').rglob('*'))
               if p.is_file() and p.relative_to(home).as_posix() not in DERIVED_TOOL_FILES}
    models = {}
    for p in sorted((home/'models').rglob('*')):
        if p.is_file():
            st = p.stat()
            models[p.relative_to(home).as_posix()] = {'size': st.st_size, 'mtime_ns': st.st_mtime_ns, 'ctime_ns': st.st_ctime_ns}
    body = {'stage': stage, 'sources': sources, 'config': config, 'runners': runners, 'model_file_identity': models,
            'python': sys.version, 'platform': sys.platform, 'machine': os.uname().machine,
            'derived_measurement_output_paths': list(DERIVED_TOOL_FILES),
            'model_payload_hash_checked_by_wrapper': False}
    return {'sha256': hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(), 'inputs': body}


def archive(path):
    """Move an obsolete/partial run aside without mixing its evidence into a new attempt."""
    if not path.exists():
        return None
    dest = path.parent/(path.name+'-previous-'+uuid.uuid4().hex[:12])
    path.rename(dest)
    return dest


def load_state(path, binding, new=False):
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        state = None
    valid = (isinstance(state, dict) and state.get('schema') == SCHEMA and
             state.get('binding') == binding and isinstance(state.get('steps'), dict))
    exists = path.exists() or (path.parent.exists() and any(path.parent.iterdir()))
    if exists and not valid and not new:
        raise ResumeRefused('Vorhandener Messstand ist unlesbar, älter oder gehört zu anderen Eingaben. '
                            'Bleibt unverändert; neuer getrennter Lauf nur mit --neu.')
    if new or not valid:
        if path.parent.exists():
            archive(path.parent)
        path.parent.mkdir(parents=True, exist_ok=True)
        state = {'schema': SCHEMA, 'binding': binding, 'steps': {}}
        atomic_write(path, json.dumps(state, indent=1))
    return state


def evidence(folder, step):
    """Closed report bytes; completion is an orchestration result, never a science PASS."""
    primary = folder/REPORTS[step]
    try:
        report = json.loads(primary.read_text())
        if primary.is_symlink() or not isinstance(report, dict) or not report:
            return None
        files = {p.relative_to(folder).as_posix(): {'sha256': file_hash(p), 'size': p.stat().st_size}
                 for p in sorted(folder.rglob('*')) if p.is_file() and not p.is_symlink() and p.suffix in W.COLLECT_SUFFIXES}
        return files if REPORTS[step] in files else None
    except (OSError, ValueError):
        return None


def derived_tool_evidence(home):
    return {name: file_hash(home/name) if (home/name).is_file() else None for name in DERIVED_TOOL_FILES}


def resumable(result, folder, step, home):
    return (isinstance(result, dict) and result.get('status') == 'DONE' and
            bool(result.get('evidence')) and evidence(folder, step) == result['evidence'] and
            (step != 'werkzeug' or result.get('derived_runner_evidence') == derived_tool_evidence(home)))


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


def stop_process_group(proc, sig):
    try:
        os.killpg(proc.pid, sig)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, 9)
        except ProcessLookupError:
            pass
        proc.wait(timeout=60)


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
            stop_process_group(proc, 15)
            rc, status = None, 'DEADLINE'
        except KeyboardInterrupt:
            stop_process_group(proc, 2); rc, status = None, 'INTERRUPTED'
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
            'NOT_BUILT': 'noch nicht gebaut', 'SKIPPED_DONE': 'schon fertig (übersprungen)',
            'RETRY_REQUIRED': 'Teilversuch bleibt erhalten (neuer Lauf nur mit --neu)',
            'MISSING_EVIDENCE': 'erforderlicher Bericht fehlt oder ist unlesbar', 'INPUT_CHANGED': 'Messgrundlage verändert'}
    for r in results:
        lines.append('- %s: %s%s' % (TITLES[r['step']], word.get(r['status'], r['status']), ', %.0f min' % r['minutes'] if r.get('minutes') else ''))
    lines += ['', 'Messungen vergeben keine zusätzlichen Lernrechte. Das Eignungs-Werkzeug wird wie freigegeben aktiviert.',
              'Fertig heißt: Messlauf beendet, nicht wissenschaftliches Gate bestanden.',
              'Bitte diese ZIP-Datei in den Claude-Chat hochladen.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage', nargs='?', default='kurz', choices=('kurz', 'voll'))
    ap.add_argument('--installed-home'); ap.add_argument('--nur', default='', help='nur diese Schritte, z. B. ram,residenz')
    ap.add_argument('--neu', action='store_true', help='vorherigen Lauf erhalten und einen getrennten neuen Lauf starten')
    ap.add_argument('--trotzdem', action='store_true'); ap.add_argument('--target-dir'); ap.add_argument('--no-setup', action='store_true')
    a = ap.parse_args(argv)
    steps = [s for s in (a.nur.split(',') if a.nur else STEPS) if s]
    if not steps or len(steps) != len(set(steps)) or any(s not in STEPS for s in steps):
        ap.error('Mindestens ein Schritt, jeder höchstens einmal: ' + ','.join(STEPS))
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
    (home/'exports').mkdir(parents=True, exist_ok=True)
    with (home/'exports/handy-pflicht.lock').open('a+') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print('STOPP: Ein Handy-Pflichtmesslauf läuft bereits.', flush=True)
            return 2
        return measure(a, steps, home, check)


def measure(a, steps, home, check):
    root = home/'exports'/('handy-pflicht-' + a.stage)
    state_path = root/'zustand.json'
    print('\nHandy-Pflichtmessungen starten (Stufe %s, Schritte: %s). Handy am Ladegerät, Termux offen lassen.\n'
          'Abbrechen mit Strg+C; geprüfte fertige Schritte bleiben. Teilversuche bleiben erhalten; neu messen nur mit --neu.\n' % (a.stage, ', '.join(steps)), flush=True)
    tools = enable_eligibility(home); print('Eignungs-Werkzeug: %s' % ('an (SHADOW bei Age 0)' if tools.get('eligibility_enabled') else 'nicht aktiviert: ' + tools.get('error', '')), flush=True)
    binding = input_binding(home, a.stage)
    try:
        state = load_state(state_path, binding, new=a.neu)
    except ResumeRefused as exc:
        print('STOPP: '+str(exc), flush=True)
        return 2
    locked = W.wake_lock(True); results = []
    try:
        with W.SystemTrace(every=30.) as trace:
            for step in steps:
                previous = state['steps'].get(step)
                if resumable(previous, root/step, step, home):
                    results.append({'step': step, 'status': 'SKIPPED_DONE'}); continue
                if previous is not None or (root/step).exists():
                    # A restarted Runtime cannot recreate a lost session/optimizer. Keep the original attempt;
                    # request explicit --neu rather than silently relaunching it and merging measurements.
                    results.append({'step': step, 'status': 'RETRY_REQUIRED', 'reason': 'Teilversuch oder Belege verändert/fehlend; '
                                    'bleibt erhalten. Neuer getrennter Lauf: --neu --nur '+step})
                    print('  -> Teilversuch bleibt erhalten; für neuen Lauf --neu --nur '+step, flush=True)
                    continue
                print('Schritt: %s ...' % TITLES[step], flush=True)
                state['steps'][step] = {'step': step, 'status': 'RUNNING'}
                atomic_write(state_path, json.dumps(state, indent=1))
                res = run_step(step, a.stage, home, root/step, root/'ablauf.log'); results.append(res)
                if res['status'] == 'DONE':
                    res['evidence'] = evidence(root/step, step)
                    if step == 'werkzeug':
                        res['derived_runner_evidence'] = derived_tool_evidence(home)
                    if not res['evidence']:
                        res.update(status='MISSING_EVIDENCE', reason='Messprogramm beendet, aber erforderlicher JSON-Bericht fehlt/ist unlesbar.')
                    if input_binding(home, a.stage) != binding:
                        res.update(status='INPUT_CHANGED', reason='Code, Konfiguration, Runner oder Modelle während der Messung verändert.')
                state['steps'][step] = res
                atomic_write(state_path, json.dumps(state, indent=1))
                print('  -> %s' % res['status'], flush=True)
                if res['status'] in ('INTERRUPTED', 'INPUT_CHANGED'): break
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
