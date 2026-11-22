from pathlib import Path
from types import SimpleNamespace

import pytest

from v13.models import model_key
from v13.callosum import _native_probe_route_bindings


def make_runtime(tmp_path):
    home = tmp_path / "brain"
    models_root = home / "models"
    sender = models_root / "gist" / "sender.gguf"
    receiver = models_root / "language" / "receiver.gguf"
    sender.parent.mkdir(parents=True)
    receiver.parent.mkdir(parents=True)
    sender.write_bytes(b"sender-model")
    receiver.write_bytes(b"receiver-model")

    paths = {"B2_GIST": sender, "C3_LANGUAGE": receiver}
    installed = {}
    for role, path, revision in (
        ("B2_GIST", sender, "sender-r1"),
        ("C3_LANGUAGE", receiver, "receiver-r1"),
    ):
        key = model_key(role, "two_body")
        installed[key] = {
            "download_complete": True,
            "exact_revision": revision,
            "main_file": path.name,
            "files": {
                path.name: {
                    "path": str(path.relative_to(home)),
                    "sha256": "a" * 64,
                    "size": path.stat().st_size,
                }
            },
        }

    class Models:
        b2_control = "two_body"

        def __init__(self):
            self.installed = installed

        def path_for(self, role):
            return paths[role]

        def revision(self, role):
            key = model_key(role, self.b2_control)
            return self.installed[key]["exact_revision"]

    return SimpleNamespace(home=home, models=Models()), paths


def test_native_probe_route_binding_accepts_exact_manifest_paths(tmp_path):
    runtime, paths = make_runtime(tmp_path)

    routes = _native_probe_route_bindings(runtime, "B2_GIST", "C3_LANGUAGE")

    assert routes["B2_GIST"]["path"] == str(paths["B2_GIST"].resolve())
    assert routes["C3_LANGUAGE"]["path"] == str(paths["C3_LANGUAGE"].resolve())
    assert routes["B2_GIST"]["model_key"] == "gist"
    assert routes["C3_LANGUAGE"]["model_key"] == "language"


def test_native_probe_route_binding_rejects_byte_identical_path_for_alias(tmp_path):
    runtime, paths = make_runtime(tmp_path)
    alias = paths["B2_GIST"].with_name("same-bytes.gguf")
    alias.write_bytes(paths["B2_GIST"].read_bytes())

    runtime.models.path_for = lambda role: alias if role == "B2_GIST" else paths[role]

    with pytest.raises(PermissionError, match="path differs"):
        _native_probe_route_bindings(runtime, "B2_GIST", "C3_LANGUAGE")


def test_native_probe_route_binding_rejects_symlinked_model_route(tmp_path):
    runtime, paths = make_runtime(tmp_path)
    alias = paths["B2_GIST"].with_name("sender-link.gguf")
    alias.symlink_to(paths["B2_GIST"])
    runtime.models.path_for = lambda role: alias if role == "B2_GIST" else paths[role]

    with pytest.raises(PermissionError, match="linked"):
        _native_probe_route_bindings(runtime, "B2_GIST", "C3_LANGUAGE")


def test_native_probe_route_binding_rejects_manifest_path_escape(tmp_path):
    runtime, paths = make_runtime(tmp_path)
    outside = tmp_path / "outside.gguf"
    outside.write_bytes(paths["B2_GIST"].read_bytes())
    runtime.models.path_for = lambda role: outside if role == "B2_GIST" else paths[role]

    with pytest.raises(PermissionError, match="path differs"):
        _native_probe_route_bindings(runtime, "B2_GIST", "C3_LANGUAGE")
