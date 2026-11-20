"""Read-only, opt-in GGUF role comparison. No downloads, manifest edits or swaps."""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path


def validate_model(registry, role, model_path):
    record = registry['models'][role]
    file = next((f for f in record['files'] if f['local_name'] == Path(model_path).name), None)
    if file is None:
        raise ValueError('unregistered model filename for role')
    if not Path(model_path).is_file():
        raise ValueError('model file missing')
    if Path(model_path).stat().st_size != file['size']:
        raise ValueError('model size mismatch')
    with open(model_path, 'rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != file['sha256']:
        raise ValueError('model sha256 mismatch')
    return {'role': role, 'model_id': record['model_id'], 'revision': record['revision'], 'license_id': record['license_id'], 'sha256': digest}


def probe(binary, model, prompt, timeout, threads, predict):
    cmd = [str(binary), '-m', str(model), '-p', prompt, '-t', str(threads), '-n', str(predict)]
    start = time.monotonic()
    try:
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return {'status': 'TIMEOUT', 'elapsed_s': round(time.monotonic()-start, 3)}
    return {'status': 'PASS' if run.returncode == 0 else 'FAIL', 'returncode': run.returncode, 'elapsed_s': round(time.monotonic()-start, 3), 'output_chars': len(run.stdout), 'stderr_tail': run.stderr[-1200:]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', required=True)
    p.add_argument('--role', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--binary', required=True)
    p.add_argument('--prompt', default='Reply with exactly four: 2+2=')
    p.add_argument('--timeout', type=float, default=40)
    p.add_argument('--threads', type=int, default=2)
    p.add_argument('--predict', type=int, default=32)
    a = p.parse_args()
    if a.timeout <= 0 or a.threads < 1 or not 1 <= a.predict <= 512:
        p.error('invalid resource limits')
    registry = json.loads(Path(a.registry).read_text())
    proof = validate_model(registry, a.role, a.model)
    if not Path(a.binary).is_file() or not os.access(a.binary, os.X_OK):
        p.error('binary not executable')
    print(json.dumps({'model': proof, 'probe': probe(a.binary, a.model, a.prompt, a.timeout, a.threads, a.predict)}, sort_keys=True))


if __name__ == '__main__':
    main()
