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
BUILDER_SHA = '109e47c7763515fb09e3a8198fef65abaaa8317c59a16fa0bebce299f8b1a030'
ARITHMETIC_OVERLAY = 'scripts/integrated_arithmetic_guard_candidate_20261121.py'
ARITHMETIC_OVERLAY_GIT_BLOB = '94cf14f671f695efc1544f50c8edbc8d462c0cd5'
NATIVE_PROBE_OVERLAY = 'scripts/integrated_native_probe_approval_overlay_20261123.py'
NATIVE_PROBE_OVERLAY_GIT_BLOB = '8b38e484172d1db863ceb4e4ed383f8508281851'
RUNTIME_CLOSE_OVERLAY = 'scripts/integrated_native_probe_runtime_close_overlay_20261124.py'
RUNTIME_CLOSE_OVERLAY_GIT_BLOB = 'fc32dc9c350e36b76c54bf8f1e26186370ccb133'
ACTION_SELECTION_LINEAGE_OVERLAY = 'scripts/integrated_actionselection_broadcast_lineage_candidate_20261125.py'
ACTION_SELECTION_LINEAGE_OVERLAY_GIT_BLOB = '8b527bdcf5447ae1058ef9b3e9126dd706e2e37d'
TOKENWISE_PAIR_OVERLAY = 'scripts/integrated_native_tokenwise_pair_overlay_20261125.py'
TOKENWISE_PAIR_OVERLAY_GIT_BLOB = '7a19de1970251ef6f3cecd260cafaa37f1a720af'
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
    close_overlay_path = code_dir / RUNTIME_CLOSE_OVERLAY
    if close_overlay_path.is_symlink() or not close_overlay_path.is_file():
        raise ValueError('native-probe Runtime close overlay missing or unsafe')
    close_overlay_raw = close_overlay_path.read_bytes()
    close_overlay_blob = hashlib.sha1(
        b'blob ' + str(len(close_overlay_raw)).encode('ascii') + b'\0' + close_overlay_raw
    ).hexdigest()
    if close_overlay_blob != RUNTIME_CLOSE_OVERLAY_GIT_BLOB:
        raise ValueError('native-probe Runtime close overlay source changed')
    runtime_payload = replacements.get('v13/runtime.py')
    if not isinstance(runtime_payload, bytes) or b'guard_runtime_close(self)' not in runtime_payload:
        raise ValueError('integrated Runtime lacks the native-probe close barrier')
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
        staged_runtime = staging / 'v13/runtime.py'
        if staged_runtime.is_symlink() or not staged_runtime.is_file() or b'guard_runtime_close(self)' not in staged_runtime.read_bytes():
            raise ValueError('arithmetic overlay removed the native-probe Runtime close barrier')
        native_probe_overlay_path = code_dir / NATIVE_PROBE_OVERLAY
        if native_probe_overlay_path.is_symlink() or not native_probe_overlay_path.is_file():
            raise ValueError('native-probe approval overlay missing or unsafe')
        native_probe_overlay_raw = native_probe_overlay_path.read_bytes()
        native_probe_overlay_blob = hashlib.sha1(
            b'blob ' + str(len(native_probe_overlay_raw)).encode('ascii') + b'\0' + native_probe_overlay_raw
        ).hexdigest()
        if native_probe_overlay_blob != NATIVE_PROBE_OVERLAY_GIT_BLOB:
            raise ValueError('native-probe approval overlay source changed')
        native_probe_overlay_spec = importlib.util.spec_from_file_location(
            'v14_checked_native_probe_overlay', native_probe_overlay_path)
        if native_probe_overlay_spec is None or native_probe_overlay_spec.loader is None:
            raise RuntimeError('native-probe approval overlay is not loadable')
        native_probe_overlay_module = importlib.util.module_from_spec(native_probe_overlay_spec)
        native_probe_overlay_spec.loader.exec_module(native_probe_overlay_module)
        expected_staged_operator = replacements.get('v13/operator.py')
        if expected_staged_operator is None:
            expected_staged_operator = (code_dir / 'v13/operator.py').read_bytes()
        if not isinstance(expected_staged_operator, bytes):
            raise ValueError('pinned recovery builder did not emit a valid operator source')
        native_probe_files = native_probe_overlay_module.apply_staged_native_probe(
            code_dir, staging, expected_staged_operator=expected_staged_operator,
        )
        if not isinstance(native_probe_files, dict) or set(native_probe_files) != {'v13/operator.py'}:
            raise ValueError('native-probe overlay produced an unexpected staged file set')
        for relative, payload in native_probe_files.items():
            target = staging / relative
            if target.is_symlink() or not target.is_file() or not isinstance(payload, bytes):
                raise ValueError('unsafe native-probe approval overlay output')
            target.write_bytes(payload)
        native_probe_overlay_manifest = {
            'name': NATIVE_PROBE_OVERLAY,
            'git_blob_sha1': NATIVE_PROBE_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'source_pins': native_probe_overlay_module.SOURCE_PINS,
            'replaced_files': sorted(native_probe_files),
            'staged_operator_git_blob_sha1': native_probe_overlay_module._git_blob_sha1(expected_staged_operator),
            'production_route': False,
            'training_authority': 0,
            'native_receiver_authority': 0,
        }
        action_lineage_path = code_dir / ACTION_SELECTION_LINEAGE_OVERLAY
        if action_lineage_path.is_symlink() or not action_lineage_path.is_file():
            raise ValueError('ActionSelection lineage overlay missing or unsafe')
        action_lineage_raw = action_lineage_path.read_bytes()
        action_lineage_blob = hashlib.sha1(
            b'blob ' + str(len(action_lineage_raw)).encode('ascii') + b'\0' + action_lineage_raw
        ).hexdigest()
        if action_lineage_blob != ACTION_SELECTION_LINEAGE_OVERLAY_GIT_BLOB:
            raise ValueError('ActionSelection lineage overlay source changed')
        action_lineage_spec = importlib.util.spec_from_file_location(
            'v14_checked_actionselection_lineage_overlay', action_lineage_path)
        if action_lineage_spec is None or action_lineage_spec.loader is None:
            raise RuntimeError('ActionSelection lineage overlay is not loadable')
        action_lineage_module = importlib.util.module_from_spec(action_lineage_spec)
        action_lineage_spec.loader.exec_module(action_lineage_module)
        staged_focal_before = (staging / 'v13/focal.py').read_bytes()
        action_lineage_files = action_lineage_module.apply_staged_actionselection_lineage(code_dir, staging)
        if not isinstance(action_lineage_files, dict) or set(action_lineage_files) != {'v13/focal.py'}:
            raise ValueError('ActionSelection lineage overlay produced an unexpected staged file set')
        for relative, payload in action_lineage_files.items():
            target = staging / relative
            if target.is_symlink() or not target.is_file() or not isinstance(payload, bytes):
                raise ValueError('unsafe ActionSelection lineage overlay output')
            target.write_bytes(payload)
        staged_focal_after = (staging / 'v13/focal.py').read_bytes()
        if staged_focal_after == staged_focal_before:
            raise ValueError('ActionSelection lineage overlay did not change staged focal consumer')
        action_selection_lineage_overlay_manifest = {
            'name': ACTION_SELECTION_LINEAGE_OVERLAY,
            'git_blob_sha1': ACTION_SELECTION_LINEAGE_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'replaced_files': sorted(action_lineage_files),
            'source_focal_sha256': hashlib.sha256((code_dir / 'v13/focal.py').read_bytes()).hexdigest(),
            'staged_before_sha256': hashlib.sha256(staged_focal_before).hexdigest(),
            'staged_after_sha256': hashlib.sha256(staged_focal_after).hexdigest(),
            'source_file_preserved': True,
            'production_route': False,
            'training_authority': 0,
            'world_learning_eligible': False,
        }
        tokenwise_overlay_path = code_dir / TOKENWISE_PAIR_OVERLAY
        if tokenwise_overlay_path.is_symlink() or not tokenwise_overlay_path.is_file():
            raise ValueError('native tokenwise runtime overlay missing or unsafe')
        tokenwise_overlay_raw = tokenwise_overlay_path.read_bytes()
        tokenwise_overlay_blob = hashlib.sha1(
            b'blob ' + str(len(tokenwise_overlay_raw)).encode('ascii') + b'\\0' + tokenwise_overlay_raw
        ).hexdigest()
        if tokenwise_overlay_blob != TOKENWISE_PAIR_OVERLAY_GIT_BLOB:
            raise ValueError('native tokenwise runtime overlay source changed')
        tokenwise_overlay_spec = importlib.util.spec_from_file_location(
            'v14_checked_native_tokenwise_overlay', tokenwise_overlay_path)
        if tokenwise_overlay_spec is None or tokenwise_overlay_spec.loader is None:
            raise RuntimeError('native tokenwise runtime overlay is not loadable')
        tokenwise_overlay_module = importlib.util.module_from_spec(tokenwise_overlay_spec)
        tokenwise_overlay_spec.loader.exec_module(tokenwise_overlay_module)
        tokenwise_files = tokenwise_overlay_module.apply_staged_tokenwise(code_dir, staging)
        expected_tokenwise_files = {
            'v13/runners.py', 'v13/cognition.py', 'v13/callosum.py', 'v13/native_probe_approval.py'
        }
        if not isinstance(tokenwise_files, dict) or set(tokenwise_files) != expected_tokenwise_files:
            raise ValueError('native tokenwise runtime overlay produced an unexpected staged file set')
        for relative, payload in tokenwise_files.items():
            target = staging / relative
            if target.is_symlink() or not target.is_file() or not isinstance(payload, bytes):
                raise ValueError('unsafe native tokenwise runtime overlay output')
            target.write_bytes(payload)
        tokenwise_overlay_manifest = {
            'name': TOKENWISE_PAIR_OVERLAY,
            'git_blob_sha1': TOKENWISE_PAIR_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'source_pins': tokenwise_overlay_module.SOURCE_PINS,
            'replaced_files': sorted(tokenwise_files),
            'production_route': False,
            'semantic_use_proven': False,
            'training_authority': 0,
            'native_receiver_authority': 0,
            'pair_vectors_persisted': False,
            'raw_receiver_rows_persisted': False,
        }
        native_probe_close_overlay_manifest = {
            'name': RUNTIME_CLOSE_OVERLAY,
            'git_blob_sha1': RUNTIME_CLOSE_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'replaced_files': ['v13/runtime.py'],
        }
        replaced_files = sorted(set(replacements) | set(arithmetic_files) | set(native_probe_files) | set(action_lineage_files) | set(tokenwise_files))
        arithmetic_overlay_manifest = {
            'name': ARITHMETIC_OVERLAY,
            'git_blob_sha1': ARITHMETIC_OVERLAY_GIT_BLOB,
            'status': 'SHADOW_REVIEW_ONLY',
            'source_pins': arithmetic_overlay_module.SOURCE_PINS,
            'replaced_files': sorted(arithmetic_files),
        }
        manifest = {
            'status': 'SHADOW_REVIEW_ONLY',
            'source': str(code_dir),
            'builder': BUILDER,
            'builder_sha256': BUILDER_SHA,
            'replaced_files': replaced_files,
            'arithmetic_overlay': arithmetic_overlay_manifest,
            'native_probe_overlay': native_probe_overlay_manifest,
            'native_probe_close_overlay': native_probe_close_overlay_manifest,
            'action_selection_lineage_overlay': action_selection_lineage_overlay_manifest,
            'native_tokenwise_pair_overlay': tokenwise_overlay_manifest,
            'files_sha256': {str(path.relative_to(staging)): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in sorted(staging.rglob('*')) if path.is_file()},
            'limitations': ['not a production Runtime promotion', 'no Android evidence',
                            'native input extractor must be explicitly built locally before use',
                            'tokenwise pair vectors are not persisted or fitted',
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
