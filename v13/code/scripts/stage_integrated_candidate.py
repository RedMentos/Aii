"""Stage the pinned, integrated V13 candidate in an isolated working directory.

NOT a release promotion: no model downloads, native execution, learning or permissions.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile

BUILDER = 'scripts/integrated_feedback_bootstrap_candidate_20261111.py'


def stage(code_dir: Path, destination: Path) -> dict:
    code_dir = code_dir.resolve(strict=True)
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError('destination must not exist (never overwrite a prior candidate)')
    if code_dir == destination or (code_dir in destination.parents and destination.name == 'v13'):
        raise ValueError('destination overlaps source tree')
    builder = code_dir / BUILDER
    spec = importlib.util.spec_from_file_location('v13_pinned_integrated_builder', builder)
    if spec is None or spec.loader is None:
        raise RuntimeError('integrated builder is not loadable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Validate source pins before creating the destination.
    replacements = module.build_sources(code_dir)
    for relative, payload in replacements.items():
        target = Path(relative)
        if target.is_absolute() or '..' in target.parts or not isinstance(payload, bytes):
            raise ValueError('unsafe integrated replacement path or payload')
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.v13-integrated-', dir=destination.parent))
    try:
        shutil.copytree(code_dir / 'v13', staging / 'v13',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.db', '*.sqlite', '*.gguf'))
        if (code_dir / 'specs').is_dir():
            shutil.copytree(code_dir / 'specs', staging / 'specs')
        for relative, payload in replacements.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        manifest = {
            'status': 'SHADOW_REVIEW_ONLY',
            'source': str(code_dir),
            'builder': BUILDER,
            'replaced_files': sorted(replacements),
            'limitations': ['not a production Runtime promotion', 'no Android evidence',
                            'no automatic learning permission'],
        }
        (staging / 'INTEGRATION_STAGE.json').write_text(json.dumps(manifest, indent=2) + '\n')
        os.rename(staging, destination)
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
    print(json.dumps({'output': str(args.output.resolve()), **result}, indent=2))


if __name__ == '__main__':
    main()
