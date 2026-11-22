"""Exercise the exact staged Runtime's source-bound sender model identity."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

CODE = Path(__file__).resolve().parents[1]
STAGER = CODE / "scripts" / "stage_integrated_candidate.py"


def test_staged_latent_tap_carries_exact_model_identity_and_rejects_stale_use(tmp_path):
    spec = importlib.util.spec_from_file_location("v14_latent_tap_stage", STAGER)
    if spec is None or spec.loader is None:
        raise RuntimeError("V14 integrated stage builder unavailable")
    stage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(stage)
    destination = tmp_path / "staged-runtime"
    manifest = stage.stage(CODE, destination)
    assert manifest["status"] == "SHADOW_REVIEW_ONLY"
    assert "v13/cognition.py" in manifest["files_sha256"]
    assert "v13/contracts.py" in manifest["files_sha256"]

    runtime_home = tmp_path / "runtime-home"
    script = r'''
import hashlib
import time
from pathlib import Path
from v13.runtime import Runtime
from v13.models import model_key
from v13.contracts import validate

home = Path(__RUNTIME_HOME__)
class FakeTapRunner:
    tap_id = "lfm2.result_norm.final.v1"
    tap_dim = 2
    def tap(self, text, cancel, deadline):
        return {
            "tap_id": self.tap_id,
            "token_ids": [101, 202],
            "vectors": [[0.25, 0.5], [0.75, 1.0]],
            "metrics": {"tap_id": self.tap_id},
        }

def install(runtime, path, revision, declared_hash, tokenizer_revision):
    key = model_key("B1_DETAIL", runtime.models.b2_control)
    runtime.models.installed[key] = {
        "download_complete": True,
        "exact_revision": revision,
        "main_file": path.name,
        "files": {path.name: {"sha256": declared_hash}},
        "tokenizer_revision": tokenizer_revision,
    }
    runtime.models.path_for = lambda role: path
    runtime.models.revision = lambda role: revision

runtime = Runtime(home)
runtime.sleep.cycle.set_policy("enabled", "off")
model_path = home / "models" / "body.gguf"
model_path.parent.mkdir(parents=True, exist_ok=True)
model_path.write_bytes(b"installed-body-model")
digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
install(runtime, model_path, "body-rev-1", digest, "tokenizer-rev-1")
runner = FakeTapRunner()
runtime.pool.get_tap = lambda role: runner
runtime.learner.predict_states = lambda *args: None
event = runtime.store.event(runtime.session, "local tap provenance fixture")
tap = runtime.cognition.tap("B1_DETAIL", event, event["source_ref"], time.monotonic() + 10)
validate("LatentTapPacket", tap)
assert tap["sender_model_sha256"] == digest
assert tap["model_revision"] == "body-rev-1"
assert tap["tokenizer_revision"] == "tokenizer-rev-1"
assert runtime.cognition.read_tap(tap)["vectors"] == [[0.25, 0.5], [0.75, 1.0]]

runtime.models.revision = lambda role: "body-rev-2"
try:
    runtime.cognition.read_tap(tap)
    raise AssertionError("stale model revision was accepted")
except ValueError as exc:
    assert "provenance is stale" in str(exc)
runtime.models.revision = lambda role: "body-rev-1"
model_path.write_bytes(b"tampered-body-model")
try:
    runtime.cognition.read_tap(tap)
    raise AssertionError("changed sender model file was accepted")
except ValueError as exc:
    assert "differs from stored provenance" in str(exc)
runtime.close()

bad_home = home.parent / "bad-runtime-home"
bad = Runtime(bad_home)
bad.sleep.cycle.set_policy("enabled", "off")
bad_model = bad_home / "models" / "body.gguf"
bad_model.parent.mkdir(parents=True, exist_ok=True)
bad_model.write_bytes(b"actual-model")
install(bad, bad_model, "body-rev-1", "f" * 64, None)
calls = []
bad.pool.get_tap = lambda role: (calls.append(role) or runner)
bad_event = bad.store.event(bad.session, "bad manifest hash fixture")
try:
    bad.cognition.tap("B1_DETAIL", bad_event, bad_event["source_ref"], time.monotonic() + 10)
    raise AssertionError("manifest/file mismatch was accepted")
except ValueError as exc:
    assert "differs from installed manifest" in str(exc)
assert calls == [], "native tap must not run before sender identity is verified"
bad.close()
'''.replace("__RUNTIME_HOME__", repr(str(runtime_home)))

    env = dict(os.environ)
    env["PYTHONPATH"] = str(destination)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=150,
    )
    assert run.returncode == 0, run.stdout + run.stderr
