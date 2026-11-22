"""Prove migration from the old worker through two real Git checkouts.

No Android hardware or native model inference is claimed. Network transport,
CI lookup and the managed process stop are simulated; Git and stage are real.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PREVIOUS_RELEASE = '5d9a86176edb45565af482644ee80dbd622d5614'
CURRENT_RELEASE = 'cbe1af572025c2984b5b0e47fe3f7f1b6080570d'
RELEASE_BRANCH = 'gpt6/v13-private-remote-bridge-20261111'
TRUSTED_ORIGIN = 'https://github.com/RedMentos/Aii.git'
CODE = Path(__file__).resolve().parents[1]


def run(*args, cwd=None, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, check=False,
                            capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, (
        f'{args!r} exited {result.returncode}\n{result.stdout}\n{result.stderr}'
    )
    return result.stdout.strip()


def git(*args, cwd=None):
    return run('git', *map(str, args), cwd=cwd)


# Imported in separate processes from each checkout, as the real relay does
# after os.execv. The old worker cannot accidentally import the new module.
WORKER = r"""
import json, os, sys
from pathlib import Path
from v13 import pipeline_agent as p
from v13 import source_updater as u
from v13 import runtime_deploy as d

remote = Path(sys.argv[1])
fetches = []
def local_fetch(root, branch):
    ref = 'refs/remotes/origin/' + branch
    before = u.git(root, 'rev-parse', ref)
    remote_head = u.git(remote, 'rev-parse', 'refs/heads/' + branch)
    import subprocess
    # The original phone checkout is shallow. Without --update-shallow Git
    # can exit 0 yet reject the tracking-ref update, and the previous worker
    # falsely says UP_TO_DATE. Simulate Git transport faithfully and fail if
    # the caller ever mistakes that no-op for a completed update.
    fetched=subprocess.run(['git','-C',str(root),'fetch','--no-tags',
                            '--update-shallow',str(remote),
                            'refs/heads/' + branch + ':' + ref],
                           capture_output=True,text=True,timeout=90,check=False)
    after = u.git(root, 'rev-parse', ref)
    fetches.append({'root':Path(root).name,'before':before[:12],
                    'remote':remote_head[:12],'after':after[:12],
                    'fetch_rc':fetched.returncode,
                    'fetch_stderr':fetched.stderr[:500]})
    if fetched.returncode != 0 or after != remote_head:
        raise RuntimeError('Shallow Git fetch did not update remote tracking ref')
    return after

# Only the remote transport, exact-SHA CI response and live stop are simulated.
u._fetch = local_fetch
u.ci_passed = lambda commit, scope='runtime': True
u._runtime_active = lambda: False
d._check_stopped = lambda home: None
if sys.argv[2] == 'old':
    p.set_enabled(True)
    result = p.run_cycle(force=True, manual=False, target='all')
else:
    from v13 import owner_read_bridge as relay
    if sys.argv[2] == 'new_disabled':
        p.set_enabled(False)
    elif sys.argv[2] == 'new':
        # Simulates the user's explicit decision to turn auto-update back on.
        p.set_enabled(True)
    result = relay._run_pending_migration_after_reload(p)
print(json.dumps({'result': result, 'profile': d.BUILD_PROFILE,
                  'module_path': str(Path(d.__file__).resolve()),
                  'fetches': fetches, 'same_source_updater':p.updates is u,
                  'home': str(Path.home())}))
"""


def exercise_worker_migration(base):
    repo = Path(run('git', 'rev-parse', '--show-toplevel', cwd=CODE))
    target = git('rev-parse', 'HEAD', cwd=repo)
    assert git('merge-base', base, target, cwd=repo) == base
    with tempfile.TemporaryDirectory(prefix='v13-migration-proof-') as temp:
        root = Path(temp)
        home = root / 'home'
        home.mkdir()
        remote = root / 'remote.git'
        # A shared local bare remote avoids copying the entire source history.
        git('clone', '--bare', '--shared', str(repo), str(remote))
        git('--git-dir', remote, 'update-ref', 'refs/heads/' + RELEASE_BRANCH, base)
        agent = home / '.v13-agent-source'
        runtime = home / '.v13-runtime-source'
        for checkout in (agent, runtime):
            git('clone', '--shared', '--sparse', '--branch', RELEASE_BRANCH, '--single-branch',
                str(remote), str(checkout))
            git('remote', 'set-url', 'origin', TRUSTED_ORIGIN, cwd=checkout)
        git('sparse-checkout', 'set', '--no-cone', 'v13/code/v13/', cwd=agent)
        git('sparse-checkout', 'set', '--no-cone', 'v13/code/v13/', 'v13/code/scripts/',
            'v13/code/specs/', 'v13/code/docs/canon/', cwd=runtime)

        data = home / 'v13'
        (data / 'bin').mkdir(parents=True)
        (data / 'models').mkdir()
        (data / 'data/db').mkdir(parents=True)
        launcher = data / 'bin/v13'
        launcher.write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        launcher.chmod(0o700)
        model = data / 'models/test.gguf'
        database = data / 'data/db/test.sqlite3'
        model.write_bytes(b'GGUF_SENTINEL_UNCHANGED')
        database.write_bytes(b'SQLITE_SENTINEL_UNCHANGED')

        # Publish the already checked-out target into the local remote.
        git('--git-dir', remote, 'update-ref', 'refs/heads/' + RELEASE_BRANCH,
            target, base)
        env = dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPATH=str(agent / 'v13/code'))

        def worker(which):
            return json.loads(run(sys.executable, '-c', WORKER, str(remote), which,
                                  cwd=home, env=env))

        old = worker('old')
        assert old['module_path'].startswith(str(agent) + os.sep)
        assert old['profile'] == 'raw-runtime-plain-ui-history-recovery-v1'
        print('V13_TWO_CHECKOUT_MIGRATION_OLD=' + json.dumps({
            'last_result': old['result'].get('last_result'),
            'runtime': old['result'].get('runtime'),
            'dashboard': old['result'].get('dashboard'),
            'last_error': old['result'].get('last_error'),
            'fetches': old.get('fetches'),
        }, sort_keys=True), flush=True)
        # The legacy updater can finish the Git fast-forward but fail to stage
        # the newer integrated runtime. The new post-reload worker must recover
        # this explicit PARTIAL state; do not pretend the old deploy succeeded.
        assert old['result']['last_result'] in ('UPDATED', 'PARTIAL'), old
        assert old['result']['runtime'] in ('UPDATED', 'UP_TO_DATE', 'ERROR'), old
        assert old['result']['dashboard'] in ('UPDATED', 'UP_TO_DATE', 'ERROR'), old
        assert old['result']['last_error'] in ('NONE', 'UPDATE'), old
        # Diagnose a mismatched source/receipt without confusing launcher activation
        # with an actual Git checkout advance. The text is only local synthetic
        # clone refs and bounded update states; no user data or tokens.
        diagnostic = {
            'base': base[:12], 'target': target[:12],
            'old_result': {k: old['result'].get(k) for k in
                           ('last_result','runtime','dashboard','last_error','updated_commit')},
            'old_fetches': old.get('fetches'), 'same_source_updater':old.get('same_source_updater'),
            'worker_home':old.get('home'),
            'checkouts': {checkout.name: {
                'head': git('rev-parse', 'HEAD', cwd=checkout)[:12],
                'tracked': git('rev-parse',
                    'refs/remotes/origin/' + RELEASE_BRANCH,
                    cwd=checkout)[:12]}
                for checkout in (agent, runtime)},
            'bare': git('--git-dir', remote, 'rev-parse',
                        'refs/heads/' + RELEASE_BRANCH)[:12],
        }
        print('V13_TWO_CHECKOUT_MIGRATION_DIAG=' +
              json.dumps(diagnostic, sort_keys=True), flush=True)
        # Historical updaters can behave differently on GitHub-hosted and
        # local Git alternates: they may correctly advance both checkouts,
        # or silently keep the base when a shallow tracking-ref update is
        # rejected. We must prove that an out-of-process Termux bootstrap can
        # recover EITHER state without discarding local user data.
        assert old.get('same_source_updater') is True
        assert old.get('fetches')
        pre_bootstrap = {}
        for checkout in (agent, runtime):
            local = git('rev-parse', 'HEAD', cwd=checkout)
            tracking = git('rev-parse',
                           'refs/remotes/origin/' + RELEASE_BRANCH,
                           cwd=checkout)
            assert local in (base, target), (checkout.name, local)
            assert tracking in (base, target), (checkout.name, tracking)
            pre_bootstrap[checkout.name] = {
                'local': local[:12], 'tracking': tracking[:12]}
        print('V13_MIGRATION_PRE_BOOTSTRAP=' +
              json.dumps(pre_bootstrap, sort_keys=True), flush=True)

        # The phone's one-command shell script independently fetches the
        # requested branch to FETCH_HEAD and fast-forwards from the *actual*
        # resulting SHA. This works even when the old Python updater was
        # unable to update its own tracking ref. Running twice is harmless.
        for checkout in (agent, runtime):
            git('fetch', '--no-tags', str(remote),
                'refs/heads/' + RELEASE_BRANCH, cwd=checkout)
            assert git('rev-parse', 'FETCH_HEAD', cwd=checkout) == target
            if git('rev-parse', 'HEAD', cwd=checkout) != target:
                git('merge', '--ff-only', 'FETCH_HEAD', cwd=checkout)
            assert git('rev-parse', 'HEAD', cwd=checkout) == target
            assert git('branch', '--show-current', cwd=checkout) == RELEASE_BRANCH

        # The legacy worker may have staged BASE as the current runtime.
        # Bootstrap must never touch model/user database, and the *new*
        # imported worker must still independently activate TARGET.
        assert model.read_bytes() == b'GGUF_SENTINEL_UNCHANGED'
        assert database.read_bytes() == b'SQLITE_SENTINEL_UNCHANGED'
        assert (agent / 'v13/code/v13/mobile_dashboard.html').is_file()
        assert (agent / 'v13/code/v13/mobile_dashboard.py').is_file()
        for name in ('mobile_dashboard.py', 'mobile_dashboard.html'):
            path = 'v13/code/v13/' + name
            assert git('rev-parse', 'HEAD:' + path, cwd=agent) == git(
                'rev-parse', target + ':' + path, cwd=repo), path
        marker = home / '.v13-private/runtime-active.json'
        marker_before = marker.read_bytes() if marker.is_file() else None
        if marker_before is not None:
            old_receipt = json.loads(marker_before.decode('utf-8'))
            assert old_receipt['build_profile'] == old['profile']
        assert (home / '.v13-private/pipeline-bridge-refresh').is_file()

        # The new relay must not migrate when the owner's consent is off,
        # even when the legacy worker left a recoverable PARTIAL state.
        disabled = worker('new_disabled')
        assert disabled['result'] is None
        marker_after_disabled = marker.read_bytes() if marker.is_file() else None
        assert marker_after_disabled == marker_before
        assert model.read_bytes() == b'GGUF_SENTINEL_UNCHANGED'
        assert database.read_bytes() == b'SQLITE_SENTINEL_UNCHANGED'

        # Simulate relay exec/reload with a new interpreter and consent enabled.
        # The one-shot helper must finish the integrated runtime after PARTIAL.
        new = worker('new')
        print('V13_TWO_CHECKOUT_MIGRATION_NEW=' + json.dumps({
            key: new['result'].get(key) for key in
            ('last_result', 'runtime', 'dashboard', 'last_error',
             'last_error_detail', 'updated_commit')
        }, sort_keys=True), flush=True)
        if new['result'].get('runtime') == 'ERROR':
            diagnostic_script = """
import json, sys
from pathlib import Path
from tempfile import TemporaryDirectory
from v13 import runtime_deploy as deploy
try:
    root, code, commit = deploy._source(Path(sys.argv[1]))
    with TemporaryDirectory(prefix='v13-migration-stage-diagnostic-') as temp:
        target = Path(temp) / 'code'
        deploy._stage_integrated_runtime(code, target, expected_commit=commit)
        try:
            deploy._selftest(target)
            result = {'phase': 'complete', 'status': 'PASS'}
        except BaseException as exc:
            result = {'phase': 'selftest', 'type': type(exc).__name__,
                      'message': str(exc)[:240]}
except BaseException as exc:
    result = {'phase': 'stage', 'type': type(exc).__name__,
              'message': str(exc)[:240]}
print('V13_MIGRATION_STAGE_DIAGNOSTIC=' + json.dumps(result, sort_keys=True))
"""
            diagnostic = subprocess.run(
                [sys.executable, '-c', diagnostic_script, str(runtime)],
                cwd=home, capture_output=True, text=True, timeout=180, env=env)
            print(diagnostic.stdout, flush=True)
            assert diagnostic.returncode == 0, diagnostic.stderr[-1000:]
        assert new['profile'] == 'integrated-runtime-source-pinned-v2'
        assert new['module_path'].startswith(str(agent) + os.sep)
        assert new['result']['last_result'] == 'UPDATED', new
        assert new['result']['runtime'] == 'UPDATED', new
        assert new['result']['dashboard'] == 'UP_TO_DATE', new
        receipt = json.loads(marker.read_text(encoding='utf-8'))
        assert receipt['commit'] == target
        assert receipt['build_profile'] == new['profile']
        staged = Path(receipt['code'])
        manifest_bytes = (staged / 'INTEGRATION_STAGE.json').read_bytes()
        assert hashlib.sha256(manifest_bytes).hexdigest() == receipt['stage_manifest_sha256']
        manifest = json.loads(manifest_bytes)
        assert manifest['status'] == 'SHADOW_REVIEW_ONLY'
        assert (staged / 'v13/runtime.py').read_bytes() != (runtime / 'v13/code/v13/runtime.py').read_bytes()
        assert str(staged).encode() in launcher.read_bytes()
        assert model.read_bytes() == b'GGUF_SENTINEL_UNCHANGED'
        assert database.read_bytes() == b'SQLITE_SENTINEL_UNCHANGED'
        # The migration is not repeated at every subsequent relay startup.
        again = worker('new_again')
        assert again['result'] is None
        assert json.loads(marker.read_text(encoding='utf-8')) == receipt


def test_migration_from_previous_phone_release():
    exercise_worker_migration(PREVIOUS_RELEASE)


def test_migration_from_current_phone_release():
    exercise_worker_migration(CURRENT_RELEASE)
