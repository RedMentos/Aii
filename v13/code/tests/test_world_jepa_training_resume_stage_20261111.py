"""Exercise optimizer-bound World-JEPA through the single current stager."""
import importlib.util
import hashlib
import re
import os
from pathlib import Path
import shutil
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_world_jepa_training_state_in_real_staged_runtime(tmp_path):
    spec = importlib.util.spec_from_file_location('resume_stage', CODE / 'scripts/stage_integrated_candidate.py')
    stager = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stager)
    dest = tmp_path / 'candidate'
    stager.stage(CODE, dest)
    (dest / 'tests').mkdir(exist_ok=True)
    for name in ('integrated_jepa_disposable_cases.py', 'world_jepa_training_resume_disposable_cases_20261111.py'):
        shutil.copyfile(CODE / 'tests' / name, dest / 'tests' / name)
    shutil.copyfile(CODE / 'tests' / 'test_v14_world_jepa_postcommit_runtime.py',
                    dest / 'tests' / 'test_v14_world_jepa_postcommit_runtime.py')
    result = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-s',
                             'tests/world_jepa_training_resume_disposable_cases_20261111.py'],
                            cwd=dest, capture_output=True, text=True, timeout=120,
                            env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout)
    staged_consumer = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '-s',
         'tests/test_v14_world_jepa_postcommit_runtime.py'],
        cwd=dest, capture_output=True, text=True, timeout=120,
        env=dict(os.environ, PYTHONPATH=str(dest), PYTHONDONTWRITEBYTECODE='1'))
    assert staged_consumer.returncode == 0, staged_consumer.stdout + staged_consumer.stderr
    print(staged_consumer.stdout)



def test_world_jepa_source_builder_pin_chain_is_exact():
    """Keep the nested immutable source/build chain bound to exact current bytes."""
    def read(relative):
        return (CODE / relative).read_bytes()

    def sha(relative):
        return hashlib.sha256(read(relative)).hexdigest()

    def pin(relative, pattern):
        source = read(relative).decode("utf-8")
        match = re.search(pattern, source)
        assert match is not None, (relative, pattern)
        return match.group(1)

    lifecycle = "scripts/source_lifecycle_lock_integration_candidate.py"
    lifecycle_bytes = read(lifecycle)
    assert b"source=self.s.one('SELECT hash FROM sources WHERE id=?',(sid,))" in lifecycle_bytes
    assert b"cleanup_unreferenced(self.s,sid)" in lifecycle_bytes
    assert b"src=self.s.one('SELECT hash FROM sources WHERE id=?',(sid,))" not in lifecycle_bytes
    assert pin(lifecycle, r"'memory[.]py': '([0-9a-f]{64})'") == sha("v13/memory.py")
    assert pin(lifecycle, r"GUARD_SCRIPT_SHA = '([0-9a-f]{64})'") == sha("scripts/archive_reader_guard_integration_candidate.py")

    memory_world = "scripts/integrated_memory_world_candidate_20261111.py"
    feedback = "scripts/integrated_feedback_bootstrap_candidate_20261111.py"
    context = "scripts/integrated_context_recall_candidate_20261111.py"
    training = "scripts/integrated_world_training_resume_candidate_20261111.py"
    termux12 = "scripts/termux_runtime_recovery_candidate_20261112.py"
    termux21 = "scripts/termux_runtime_recovery_candidate_20261121.py"
    stage = "scripts/stage_integrated_candidate.py"
    deploy = "v13/runtime_deploy.py"

    assert pin(memory_world, r"LIFECYCLE_BUILDER_SHA = '([0-9a-f]{64})'") == sha(lifecycle)
    assert pin(feedback, r"BASE_BUILDER_SHA = '([0-9a-f]{64})'") == sha(memory_world)
    assert pin(context, r"BASE_BUILDER_SHA = '([0-9a-f]{64})'") == sha(feedback)
    assert pin(training, r"BASE_SHA = '([0-9a-f]{64})'") == sha(context)
    assert pin(termux12, r"integrated_world_training_resume_candidate_20261111[.]py': '([0-9a-f]{64})'") == sha(training)
    guard_builder = "scripts/record_only_controller_guard_20261116.py"
    assert pin(termux12, r"record_only_controller_guard_20261116[.]py',\s*'([0-9a-f]{64})'") == sha(guard_builder)

    base = read(termux12)
    git_blob = hashlib.sha1(b"blob " + str(len(base)).encode("ascii") + bytes([0]) + base).hexdigest()
    assert pin(termux21, r'BASE_BUILDER_BLOB_SHA1 = "([0-9a-f]{40})"') == git_blob
    assert pin(stage, r"BUILDER_SHA = '([0-9a-f]{64})'") == sha(termux21)
    assert pin(deploy, r'STAGER_SHA256 = "([0-9a-f]{64})"') == sha(stage)
