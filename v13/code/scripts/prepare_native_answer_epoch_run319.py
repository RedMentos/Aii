"""Run319: prepare a bounded per-epoch native finetune candidate in isolated temp.

The original registered C++ source is NEVER edited. This is source preparation,
not a native optimizer execution, training proof or permission grant.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ORIGINAL_SHA256 = '401b95c5c6f4262eb8ea58bdab0af2b79f5d7032951ba45198ab2e13f102858c'
SCHEMA = 'V13_RUN319_NATIVE_EPOCH_SOURCE_PREP_V1'
GATES = {'STEP2': 'UTILITY_FAIL', 'B3_L1': 'FAIL',
         'Body_JEPA': 'UNAVAILABLE', 'jepa_weight': 0, 'V13': 'INCOMPLETE'}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def prepare(source, patch, out_dir):
    source, patch, out_dir = map(Path, (source, patch, out_dir))
    if source.is_symlink() or patch.is_symlink() or not source.is_file() or not patch.is_file():
        raise ValueError('regular source and patch files required')
    if digest(source) != ORIGINAL_SHA256:
        raise ValueError('original native answer finetune SHA drift')
    original = source.read_bytes()
    if not patch.read_text(encoding='utf-8').startswith('--- a/scripts/native_answer_finetune.cpp\n'):
        raise ValueError('patch must target only the expected original source')
    if out_dir.exists():
        raise FileExistsError('candidate output directory exists; refuse overwrite')
    out_dir.mkdir(parents=True)
    candidate = out_dir / 'scripts/native_answer_finetune.cpp'
    candidate.parent.mkdir()
    shutil.copyfile(source, candidate)
    cmd = ['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-d', str(out_dir), '-i', str(patch.resolve())]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        raise ValueError('exact-source candidate patch failed: ' + (proc.stderr or proc.stdout)[-500:])
    if source.read_bytes() != original or digest(source) != ORIGINAL_SHA256:
        raise ValueError('original registered source was mutated')
    text = candidate.read_text(encoding='utf-8')
    required = (
        'V13_EPOCH_CHECKPOINTS', 'V13_EPOCH_CHECKPOINT',
        'lr.epochs > 8', 'std::filesystem::is_symlink',
        'std::filesystem::file_size', 'llama_model_save_to_file(model, path.c_str())',
    )
    if any(x not in text for x in required) or text.count('V13_EPOCH_CHECKPOINTS') != 2:
        raise ValueError('candidate checkpoint controls missing or drifted')
    report = {
        'schema': SCHEMA, 'status': 'SOURCE_PREPARED_NO_NATIVE_TRAINING',
        'original_sha256': ORIGINAL_SHA256,
        'original_unchanged': True,
        'patch_sha256': digest(patch),
        'candidate_sha256': digest(candidate),
        'candidate_path': str(candidate),
        'checkpoint_mode_default': 'OFF',
        'max_epochs_when_enabled': 8,
        'overwrite_allowed': False,
        'native_compiled': False,
        'native_trained': False,
        'model_weight_activation': False,
        'gates': dict(GATES),
    }
    (out_dir / 'RUN319_PREP.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True)
    ap.add_argument('--patch', required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()
    print(json.dumps(prepare(args.source, args.patch, args.out_dir), sort_keys=True))


if __name__ == '__main__':
    main()
