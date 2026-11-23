"""Stage the pinned, integrated V13 candidate in an isolated working directory.

NOT a release promotion: no model downloads, native execution, learning or permissions.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile

BUILDER = 'scripts/termux_runtime_recovery_candidate_20261121.py'
BUILDER_SHA = '16fc4a35ad94b6f7ee0cb4ed06b622e4c19a3887081225ed69e516236b10a41f'
ARITHMETIC_OVERLAY = 'scripts/integrated_arithmetic_guard_candidate_20261121.py'
ARITHMETIC_OVERLAY_GIT_BLOB = '88c179a71387c5caba7bbd645f868a7cccf39d30'
CONSOLE_PRIVACY_OVERLAY = 'scripts/integrated_console_probe_privacy_overlay_20261123.py'
CONSOLE_PRIVACY_OVERLAY_GIT_BLOB = 'd2af3b90d85d739c1773fe326d4ca3c4f6cdab36'
IGNORED = ('__pycache__', '*.pyc', '*.db', '*.sqlite', '*.sqlite3', '*.gguf',
           '*.safetensors', '*.pt', '*.pth', '*.log')


def _publish(staging, destination):
    """Linux no-clobber publication, including another writer's empty directory."""
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        rename = libc.renameat2
    except AttributeError as exc:
        raise OSError('atomic no-clobber staging unsupported') from exc
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(staging), -100, os.fsencode(destination), 1) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


def stage(code_dir: Path, destination: Path) -> dict:
    code_dir = code_dir.resolve(strict=True)
    if destination.is_symlink():
        raise ValueError('destination cannot be a symlink')
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError('destination must not exist (never overwrite a prior candidate)')
    if code_dir == destination or code_dir in destination.parents:
        raise ValueError('destination overlaps source tree')
    builder = code_dir / BUILDER
    if builder.is_symlink() or hashlib.sha256(builder.read_bytes()).hexdigest() != BUILDER_SHA:
        raise ValueError('integrated builder hash mismatch')
    spec = importlib.util.spec_from_file_location('v13_pinned_integrated_builder', builder)
    if spec is None or spec.loader is None:
        raise RuntimeError('integrated builder is not loadable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Validate source pins before creating the destination.
    replacements = module.build_sources(code_dir)
    for relative, payload in replacements.items():
        target = Path(relative)
        if (target.is_absolute() or '..' in target.parts or not target.parts
                or target.parts[0] not in {'v13', 'tests', 'specs'} or not isinstance(payload, bytes)):
            raise ValueError('unsafe integrated replacement path or payload')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.v13-integrated-', dir=destination.parent))
    try:
        if any((code_dir / name).is_symlink() for name in ('v13', 'specs', 'scripts')):
            raise ValueError('staging source directory cannot be a symlink')
        shutil.copytree(code_dir / 'v13', staging / 'v13', symlinks=True,
                        ignore=shutil.ignore_patterns(*IGNORED))
        if (code_dir / 'specs').is_dir():
            shutil.copytree(code_dir / 'specs', staging / 'specs', symlinks=True,
                            ignore=shutil.ignore_patterns(*IGNORED))
        # Runtime commands import scripts.ask_verified_budget and native
        # helper modules. A runnable staged copy must retain those paths.
        if (code_dir / 'scripts').is_dir():
            shutil.copytree(code_dir / 'scripts', staging / 'scripts', symlinks=True,
                            ignore=shutil.ignore_patterns(*IGNORED))
        if any(path.is_symlink() for path in staging.rglob('*')):
            raise ValueError('staging source contains a symlink')
        for relative, payload in replacements.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        arithmetic_overlay_path = code_dir / ARITHMETIC_OVERLAY
        if arithmetic_overlay_path.is_symlink() or not arithmetic_overlay_path.is_file():
            raise ValueError('arithmetic guard overlay missing or unsafe')
        arithmetic_overlay_raw = arithmetic_overlay_path.read_bytes()
        arithmetic_overlay_blob = hashlib.sha1(
            b'blob ' + str(len(arithmetic_overlay_raw)).encode('ascii') + b'\0' + arithmetic_overlay_raw
        ).hexdigest()
        if arithmetic_overlay_blob != ARITHMETIC_OVERLAY_GIT_BLOB:
            raise ValueError('arithmetic guard overlay source changed')
        arithmetic_overlay_spec = importlib.util.spec_from_file_location(
            'v14_checked_arithmetic_guard', arithmetic_overlay_path)
        if arithmetic_overlay_spec is None or arithmetic_overlay_spec.loader is None:
            raise RuntimeError('arithmetic guard overlay is not loadable')
        arithmetic_overlay_module = importlib.util.module_from_spec(arithmetic_overlay_spec)
        arithmetic_overlay_spec.loader.exec_module(arithmetic_overlay_module)
        arithmetic_files = arithmetic_overlay_module.apply_staged_arithmetic(code_dir, staging)
        if not isinstance(arithmetic_files, dict) or not arithmetic_files:
            raise ValueError('arithmetic guard overlay produced no staged files')
        for relative, payload in arithmetic_files.items():
            target = staging / relative
            if target.is_symlink() or not target.is_file() or not isinstance(payload, bytes):
                raise ValueError('unsafe arithmetic guard output')
            target.write_bytes(payload)
        console_privacy_overlay_path = code_dir / CONSOLE_PRIVACY_OVERLAY
        if console_privacy_overlay_path.is_symlink() or not console_privacy_overlay_path.is_file():
            raise ValueError('console privacy overlay missing or unsafe')
        console_privacy_overlay_raw = console_privacy_overlay_path.read_bytes()
        console_privacy_overlay_blob = hashlib.sha1(
            b'blob ' + str(len(console_privacy_overlay_raw)).encode('ascii') + b'\0' + console_privacy_overlay_raw
        ).hexdigest()
        if console_privacy_overlay_blob != CONSOLE_PRIVACY_OVERLAY_GIT_BLOB:
            raise ValueError('console privacy overlay source changed')
        console_privacy_spec = importlib.util.spec_from_file_location(
            'v14_checked_console_probe_privacy', console_privacy_overlay_path)
        if console_privacy_spec is None or console_privacy_spec.loader is None:
            raise RuntimeError('console privacy overlay is not loadable')
        console_privacy_module = importlib.util.module_from_spec(console_privacy_spec)
        console_privacy_spec.loader.exec_module(console_privacy_module)
        expected_staged_files = {
            'v13/runtime.py': arithmetic_files.get(
                'v13/runtime.py', replacements.get('v13/runtime.py', (code_dir / 'v13/runtime.py').read_bytes())),
            'v13/__main__.py': arithmetic_files.get(
                'v13/__main__.py', replacements.get('v13/__main__.py', (code_dir / 'v13/__main__.py').read_bytes())),
        }
        console_privacy_files = console_privacy_module.apply_staged_console_probe_privacy(
            code_dir, staging, expected_staged_files=expected_staged_files,
        )
        if not isinstance(console_privacy_files, dict) or set(console_privacy_files) != {
                'v13/runtime.py', 'v13/__main__.py'}:
            raise ValueError('console privacy overlay produced an unexpected staged file set')
        for relative, payload in console_privacy_files.items():
            target = staging / relative
            if target.is_symlink() or not target.is_file() or not isinstance(payload, bytes):
                raise ValueError('unsafe console privacy overlay output')
            target.write_bytes(payload)
        replaced_files = sorted(set(replacements) | set(arithmetic_files) | set(console_privacy_files))
        arithmetic_overlay_manifest = {
            'name': ARITHMETIC_OVERLAY,
            'git_blob_sha1': ARITHMETIC_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'source_pins': arithmetic_overlay_module.SOURCE_PINS,
            'replaced_files': sorted(arithmetic_files),
        }
        console_privacy_manifest = {
            'name': CONSOLE_PRIVACY_OVERLAY,
            'git_blob_sha1': CONSOLE_PRIVACY_OVERLAY_GIT_BLOB,
            'status': 'PUBLIC_CONSOLE_ALLOWLIST',
            'source_pins': console_privacy_module.SOURCE_PINS,
            'replaced_files': sorted(console_privacy_files),
            'raw_artifact_retained_locally': True,
        }
        manifest = {
            'status': 'SHADOW_REVIEW_ONLY',
            'source': str(code_dir),
            'builder': BUILDER,
            'builder_sha256': BUILDER_SHA,
            'replaced_files': replaced_files,
            'arithmetic_overlay': arithmetic_overlay_manifest,
            'console_probe_privacy': console_privacy_manifest,
            'files_sha256': {str(path.relative_to(staging)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sorted(staging.rglob('*')) if path.is_file()},
            'limitations': ['not a production Runtime promotion', 'no Android evidence',
                            'no automatic learning permission'],
        }
        (staging / 'INTEGRATION_STAGE.json').write_text(json.dumps(manifest, indent=2) + '\n')
        _publish(staging, destination)
        return manifest
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-dir', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = stage(args.code_dir, args.output)
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        parser.exit(2, f'BLOCKED: {exc}\n')
    print(json.dumps({'output': str(args.output.resolve()), 'status': result['status'],
                      'builder': result['builder'], 'builder_sha256': result['builder_sha256'],
                      'files': len(result['files_sha256']),
                      'manifest': str(args.output.resolve() / 'INTEGRATION_STAGE.json')}, indent=2))


if __name__ == '__main__':
    main()
