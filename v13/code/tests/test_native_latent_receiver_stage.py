"""Verify the native receiver overlay is present in the exact final staged runtime."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]


def test_native_receiver_is_composed_and_runtime_contracts_pass(tmp_path):
    builder_path = CODE / "scripts/stage_integrated_candidate.py"
    spec = importlib.util.spec_from_file_location("v14_native_receiver_stage", builder_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    destination = tmp_path / "stage"
    manifest = builder.stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert "v13/native_latent_receiver.py" in manifest["files_sha256"]
    assert "v13/native/latent_receiver/native_latent_receiver.cpp" in manifest["files_sha256"]
    cognition = (destination / "v13/cognition.py").read_text(encoding="utf-8")
    callosum = (destination / "v13/callosum.py").read_text(encoding="utf-8")
    assert "def native_receive(" in cognition
    assert "native-probe" in callosum
    assert (destination / "v13/native_probe_approval.py").is_file()
    operator = (destination / "v13/operator.py").read_text(encoding="utf-8")
    assert "arm-probe" in operator
    assert "native_probe_approval import operator_command" in operator
    assert "production_route=False" in cognition
    assert "semantic_use_proven=False" in cognition
    assert "import time" in callosum
    assert "if len(args)==5 and args[0]=='native-probe'" in callosum
    assert callosum.index("if len(args)==5 and args[0]=='native-probe'") < callosum.index("if not args or args==['status']")
    assert "return dumps({'direction':args[1],'level':b3degrade.promote(r,args[1],'EXPLICIT_HUMAN')})" in callosum
    assert "native_receiver_probe" in callosum
    staged_budget = (destination / "v13/native_turn_budget.py").read_text(encoding="utf-8")
    staged_schedule = (destination / "v13/observer_schedule.py").read_text(encoding="utf-8")
    assert "minimum_role_slice_s" in staged_budget
    assert "budgeted=False" in staged_schedule
    assert "native_body_budgeted_for_c3" in cognition
    assert "'native_receiver_probe':self.native_receiver_probe()" in callosum
    assert "G-CALLOSUM-UTILITY-002: LATENT blocked for production" in callosum
    assert "native-probe <sender> <receiver>" in callosum
    env = dict(os.environ)
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         str(CODE / "tests/test_native_latent_receiver.py"),
         str(CODE / "tests/test_native_latent_receiver_runtime.py"),
         str(CODE / "tests/test_native_latent_receiver_approval.py"),
         str(CODE / "tests/test_callosum.py"),
         str(CODE / "tests/observer_fair_budget_disposable_cases_20261116.py")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=150,
    )
    assert run.returncode == 0, run.stdout + run.stderr
