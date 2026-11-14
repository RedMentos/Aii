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

BUILDER = 'scripts/termux_runtime_recovery_candidate_20261112.py'
BUILDER_SHA = 'd081c499e9834b95b44161de463c9f824b4d524b9bc411b781cfa9aa8ab16ed4'
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
        manifest = {
            'status': 'SHADOW_REVIEW_ONLY',
            'source': str(code_dir),
            'builder': BUILDER,
            'builder_sha256': BUILDER_SHA,
            'replaced_files': sorted(replacements),
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
