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
BUILDER_SHA = 'c80391e271b4d66db8fa3291f075710ed2e9d966846a41101402674c2b5dace0'
ARITHMETIC_OVERLAY = 'scripts/integrated_arithmetic_guard_candidate_20261121.py'
ARITHMETIC_OVERLAY_GIT_BLOB = '88c179a71387c5caba7bbd645f868a7cccf39d30'
OUTPUT_PRIVACY_OVERLAY = 'scripts/integrated_output_privacy_overlay_20261123.py'
OUTPUT_PRIVACY_OVERLAY_GIT_BLOB = '997d7511df957146dca1cae8ee07e45f86dda8a2'
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

        output_privacy_overlay_path = code_dir / OUTPUT_PRIVACY_OVERLAY
        if output_privacy_overlay_path.is_symlink() or not output_privacy_overlay_path.is_file():
            raise ValueError('output-privacy overlay missing or unsafe')
        output_privacy_overlay_raw = output_privacy_overlay_path.read_bytes()
        output_privacy_overlay_blob = hashlib.sha1(
            b'blob ' + str(len(output_privacy_overlay_raw)).encode('ascii') + b'\0' + output_privacy_overlay_raw
        ).hexdigest()
        if output_privacy_overlay_blob != OUTPUT_PRIVACY_OVERLAY_GIT_BLOB:
            raise ValueError('output-privacy overlay source changed')
        output_privacy_overlay_spec = importlib.util.spec_from_file_location(
            'v14_checked_output_privacy_overlay', output_privacy_overlay_path)
        if output_privacy_overlay_spec is None or output_privacy_overlay_spec.loader is None:
            raise RuntimeError('output-privacy overlay is not loadable')
        output_privacy_overlay_module = importlib.util.module_from_spec(output_privacy_overlay_spec)
        output_privacy_overlay_spec.loader.exec_module(output_privacy_overlay_module)
        output_privacy_files = output_privacy_overlay_module.apply_staged_output_privacy(
            code_dir, staging,
            expected_staged_runtime=(staging / 'v13/runtime.py').read_bytes(),
            expected_staged_verification=(code_dir / 'v13/verification.py').read_bytes(),
            expected_staged_cli=(code_dir / 'v13/__main__.py').read_bytes(),
            expected_staged_prompts=(code_dir / 'v13/prompts.py').read_bytes(),
        )
        expected_privacy_paths = {'v13/verification.py', 'v13/runtime.py', 'v13/__main__.py', 'v13/prompts.py'}
        if not isinstance(output_privacy_files, dict) or set(output_privacy_files) != expected_privacy_paths:
            raise ValueError('output-privacy overlay produced an unexpected staged file set')
        for relative, payload in output_privacy_files.items():
            target = staging / relative
            if target.is_symlink() or not target.is_file() or not isinstance(payload, bytes):
                raise ValueError('unsafe output-privacy overlay output')
            target.write_bytes(payload)

        replaced_files = sorted(set(replacements) | set(arithmetic_files) | set(output_privacy_files))
        arithmetic_overlay_manifest = {
            'name': ARITHMETIC_OVERLAY,
            'git_blob_sha1': ARITHMETIC_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'source_pins': arithmetic_overlay_module.SOURCE_PINS,
            'replaced_files': sorted(arithmetic_files),
        }
        output_privacy_overlay_manifest = {
            'name': OUTPUT_PRIVACY_OVERLAY,
            'git_blob_sha1': OUTPUT_PRIVACY_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'source_pins': output_privacy_overlay_module.SOURCE_PINS,
            'replaced_files': sorted(output_privacy_files),
        }
        manifest = {
            'status': 'SHADOW_REVIEW_ONLY',
            'source': str(code_dir),
            'builder': BUILDER,
            'builder_sha256': BUILDER_SHA,
            'replaced_files': replaced_files,
            'arithmetic_overlay': arithmetic_overlay_manifest,
            'output_privacy_overlay': output_privacy_overlay_manifest,
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
