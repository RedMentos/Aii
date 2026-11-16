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

BASE = '5d9a86176edb45565af482644ee80dbd622d5614'
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
def local_fetch(root, branch):
    ref = 'refs/remotes/origin/' + branch
    u.git(root, 'fetch', '--no-tags', str(remote),
          'refs/heads/' + branch + ':' + ref, timeout=90)
    return u.git(root, 'rev-parse', ref)

# Only the remote transport, exact-SHA CI response and live stop are simulated.
u._fetch = local_fetch
u.ci_passed = lambda commit, scope='runtime': True
u._runtime_active = lambda: False
d._check_stopped = lambda home: None
if sys.argv[2] == 'old':
    p.set_enabled(True)
result = p.run_cycle(force=True, manual=False, target='all')
print(json.dumps({'result': result, 'profile': d.BUILD_PROFILE,
                  'module_path': str(Path(d.__file__).resolve())}))
"""


def test_old_to_new_worker_installs_integrated_runtime_from_two_git_checkouts():
    repo = Path(run('git', 'rev-parse', '--show-toplevel', cwd=CODE))
    target = git('rev-parse', 'HEAD', cwd=repo)
    assert git('merge-base', BASE, target, cwd=repo) == BASE
    with tempfile.TemporaryDirectory(prefix='v13-migration-proof-') as temp:
        root = Path(temp)
        home = root / 'home'
        home.mkdir()
        remote = root / 'remote.git'
        # A shared local bare remote avoids copying the entire source history.
        git('clone', '--bare', '--shared', str(repo), str(remote))
        git('--git-dir', remote, 'update-ref', 'refs/heads/' + RELEASE_BRANCH, BASE)
        agent = home / '.v13-agent-source'
        runtime = home / '.v13-runtime-source'
        for checkout in (agent, runtime):
            git('clone', '--shared', '--branch', RELEASE_BRANCH, '--single-branch',
                str(remote), str(checkout))
            git('remote', 'set-url', 'origin', TRUSTED_ORIGIN, cwd=checkout)

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
            target, BASE)
        env = dict(os.environ, HOME=str(home), PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPATH=str(agent / 'v13/code'))

        def worker(which):
            return json.loads(run(sys.executable, '-c', WORKER, str(remote), which,
                                  cwd=home, env=env))

        old = worker('old')
        assert old['module_path'].startswith(str(agent) + os.sep)
        assert old['profile'] == 'raw-runtime-plain-ui-history-recovery-v1'
        assert old['result']['last_result'] == 'UPDATED', old
        assert old['result']['runtime'] == old['result']['dashboard'] == 'UPDATED'
        for checkout in (agent, runtime):
            assert git('rev-parse', 'HEAD', cwd=checkout) == target
        marker = home / '.v13-private/runtime-active.json'
        old_receipt = json.loads(marker.read_text(encoding='utf-8'))
        assert old_receipt['build_profile'] == old['profile']
        assert (home / '.v13-private/pipeline-bridge-refresh').is_file()

        # Simulate the existing relay's exec/reload using a new interpreter.
        # A forced second cycle avoids sleeping through the real 15-minute timer.
        new = worker('new')
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
