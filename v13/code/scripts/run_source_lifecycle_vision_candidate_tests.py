"""Materialize the exact reviewed lifecycle candidate and run its Runtime tests.

This is a disposable-copy test only. It never patches the checkout or an
installed Termux runtime.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def _load_builder(path: Path):
    spec = importlib.util.spec_from_file_location("v14_source_lifecycle_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source lifecycle candidate builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    code_dir = Path(__file__).resolve().parents[1]
    source_dir = code_dir / "v13"
    builder_path = code_dir / "scripts" / "source_lifecycle_lock_integration_candidate.py"
    test_path = code_dir / "tests" / "source_lifecycle_disposable_cases.py"

    builder = _load_builder(builder_path)
    replacements = builder.build_sources(source_dir)

    with tempfile.TemporaryDirectory(prefix="v14-vision-lifecycle-") as temporary:
        root = Path(temporary)
        staged_v13 = root / "v13"
        shutil.copytree(source_dir, staged_v13)
        specs_dir = code_dir / "specs"
        if specs_dir.is_dir():
            shutil.copytree(specs_dir, root / "specs")
        for relative, data in replacements.items():
            target = staged_v13 / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            print(
                "STAGED",
                relative,
                hashlib.sha256(data).hexdigest(),
                flush=True,
            )

        tests = root / "tests"
        tests.mkdir()
        staged_test = tests / test_path.name
        shutil.copy2(test_path, staged_test)

        env = os.environ.copy()
        env["PYTHONPATH"] = str(root)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        command = [sys.executable, "-m", "pytest", "-q", str(staged_test)]
        print("RUN", " ".join(command), flush=True)
        return subprocess.run(command, cwd=root, env=env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
