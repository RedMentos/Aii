"""Verify the native receiver overlay is present in the exact final staged runtime."""
import hashlib
import importlib.util
import json
import os
import pytest
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
    overlay_path = CODE / "scripts/integrated_native_probe_approval_candidate_20261122.py"
    overlay_spec = importlib.util.spec_from_file_location("v14_native_probe_approval_overlay", overlay_path)
    overlay = importlib.util.module_from_spec(overlay_spec)
    overlay_spec.loader.exec_module(overlay)
    with pytest.raises(ValueError, match="separate from source tree"):
        overlay.apply_staged(CODE, CODE)
    callosum_path = destination / "v13/callosum.py"
    operator_path = destination / "v13/operator.py"
    callosum_before = callosum_path.read_bytes()
    operator_before = operator_path.read_bytes()
    manifest = overlay.apply_staged(CODE, destination)
    approval_meta = manifest["native_probe_approval_overlay"]
    assert approval_meta["status"] == "SHADOW_REVIEW_ONLY"
    assert approval_meta["composition_mode"] == "PRECOMPOSED_VERIFIED"
    assert approval_meta["model_byte_integrity_verified"] is True
    assert approval_meta["replaced_files"] == []
    assert approval_meta["ttl_seconds"] == 120
    assert callosum_path.read_bytes() == callosum_before
    assert operator_path.read_bytes() == operator_before
    cognition = (destination / "v13/cognition.py").read_text(encoding="utf-8")
    callosum = (destination / "v13/callosum.py").read_text(encoding="utf-8")
    operator_help = (destination / "v13/operator.py").read_text(encoding="utf-8")
    assert "def native_receive(" in cognition
    assert "native-probe" in callosum
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
    assert "arm-probe <sender> <receiver>" in callosum
    assert "local_approval_consumed" in callosum
    assert all(marker in operator_help for marker in ("arm-probe", "native-probe", "revoke-probe"))
    assert (destination / "v13/native_probe_approval.py").is_file()
    env = dict(os.environ)
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run(
        [sys.executable, "-m", "pytest", "-q",
         str(CODE / "tests/test_native_latent_receiver.py"),
         str(CODE / "tests/test_native_latent_receiver_runtime.py"),
         str(CODE / "tests/test_callosum.py"),
         str(CODE / "tests/test_native_latent_receiver_approval.py"),
         str(CODE / "tests/observer_fair_budget_disposable_cases_20261116.py")],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=150,
    )
    assert run.returncode == 0, run.stdout + run.stderr


def _minimal_overlay_stage(tmp_path, overlay):
    code_dir = tmp_path / "source"
    source_v13 = code_dir / "v13"
    source_v13.mkdir(parents=True)
    approval_source = (
        b"def _file_sha256(path):\n    return 'digest'\n"
        b"def _model_binding(path, resolved, digest, models_root):\n"
        b"    actual_digest = _file_sha256(resolved)\n"
        b"    if actual_digest != digest:\n        raise PermissionError()\n"
        b"    if not resolved.is_relative_to(models_root):\n        raise PermissionError()\n"
        b"    if path.resolve(strict=True) != resolved:\n        raise PermissionError()\n"
        b"def arm():\n    return None\n"
    )
    (source_v13 / "native_probe_approval.py").write_bytes(approval_source)

    stage_dir = tmp_path / "stage"
    staged_v13 = stage_dir / "v13"
    staged_v13.mkdir(parents=True)
    callosum = (
        "def operator_command(r,args):\n"
        + overlay.OPERATOR_HELP_OLD
        + overlay.OPERATOR_PREFIX_OLD
        + "    if not args or args==['status']:return None\n"
        + overlay.OPERATOR_ERROR_OLD
    ).encode("utf-8")
    operator = ("HELP = " + repr(overlay.HELP_OLD) + "\n").encode("utf-8")
    (staged_v13 / "callosum.py").write_bytes(callosum)
    (staged_v13 / "operator.py").write_bytes(operator)
    (staged_v13 / "native_probe_approval.py").write_bytes(approval_source)
    manifest = {
        "status": "SHADOW_REVIEW_ONLY",
        "source": str(code_dir),
        "files_sha256": {
            "v13/callosum.py": hashlib.sha256(callosum).hexdigest(),
            "v13/operator.py": hashlib.sha256(operator).hexdigest(),
            "v13/native_probe_approval.py": hashlib.sha256(approval_source).hexdigest(),
        },
    }
    (stage_dir / "INTEGRATION_STAGE.json").write_text(json.dumps(manifest), encoding="utf-8")
    return code_dir, stage_dir


def test_native_probe_overlay_rejects_partial_precomposition_without_writing(tmp_path):
    overlay_path = CODE / "scripts/integrated_native_probe_approval_candidate_20261122.py"
    spec = importlib.util.spec_from_file_location("v14_native_probe_partial_overlay", overlay_path)
    overlay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    code_dir, stage_dir = _minimal_overlay_stage(tmp_path, overlay)
    callosum_path = stage_dir / "v13/callosum.py"
    callosum = callosum_path.read_bytes() + b"\\n# arm-probe\\n"
    callosum_path.write_bytes(callosum)
    manifest_path = stage_dir / "INTEGRATION_STAGE.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files_sha256"]["v13/callosum.py"] = hashlib.sha256(callosum).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    before = callosum_path.read_bytes()
    with pytest.raises(ValueError, match="composition is partial or inconsistent"):
        overlay.apply_staged(code_dir, stage_dir)
    assert callosum_path.read_bytes() == before


def test_native_probe_overlay_rejects_symlinked_stage_parent_without_writing_outside(tmp_path):
    overlay_path = CODE / "scripts/integrated_native_probe_approval_candidate_20261122.py"
    spec = importlib.util.spec_from_file_location("v14_native_probe_symlink_overlay", overlay_path)
    overlay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    code_dir, stage_dir = _minimal_overlay_stage(tmp_path, overlay)
    outside = tmp_path / "outside-v13"
    (stage_dir / "v13").rename(outside)
    (stage_dir / "v13").symlink_to(outside, target_is_directory=True)
    before = (outside / "callosum.py").read_bytes()
    with pytest.raises(ValueError, match="symlink"):
        overlay.apply_staged(code_dir, stage_dir)
    assert (outside / "callosum.py").read_bytes() == before
    assert (outside / "operator.py").read_bytes() == (stage_dir / "v13" / "operator.py").read_bytes()


def test_native_probe_overlay_rejects_wrong_manifest_source_before_writing(tmp_path):
    overlay_path = CODE / "scripts/integrated_native_probe_approval_candidate_20261122.py"
    spec = importlib.util.spec_from_file_location("v14_native_probe_manifest_overlay", overlay_path)
    overlay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    code_dir, stage_dir = _minimal_overlay_stage(tmp_path, overlay)
    manifest_path = stage_dir / "INTEGRATION_STAGE.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source"] = str(tmp_path / "wrong-source")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    callosum_path = stage_dir / "v13/callosum.py"
    before = callosum_path.read_bytes()
    with pytest.raises(ValueError, match="source tree differs"):
        overlay.apply_staged(code_dir, stage_dir)
    assert callosum_path.read_bytes() == before


def test_native_probe_overlay_rejects_tampered_stage_bytes_before_writing(tmp_path):
    overlay_path = CODE / "scripts/integrated_native_probe_approval_candidate_20261122.py"
    spec = importlib.util.spec_from_file_location("v14_native_probe_hash_overlay", overlay_path)
    overlay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(overlay)
    code_dir, stage_dir = _minimal_overlay_stage(tmp_path, overlay)
    callosum_path = stage_dir / "v13/callosum.py"
    callosum_path.write_bytes(callosum_path.read_bytes() + b"\n# tampered\n")
    before = callosum_path.read_bytes()
    with pytest.raises(ValueError, match="integrity mismatch"):
        overlay.apply_staged(code_dir, stage_dir)
    assert callosum_path.read_bytes() == before
