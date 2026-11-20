"""Read-only opt-in GGUF probe. A successful process exit is not an answer."""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

def validate_model(registry, role, model_path):
    record = registry['models'][role]
    file = next((f for f in record['files'] if f['local_name'] == Path(model_path).name), None)
    if file is None:
        raise ValueError('unregistered model filename for role')
    if not Path(model_path).is_file() or Path(model_path).is_symlink():
        raise ValueError('model missing or symlink')
    if Path(model_path).stat().st_size != file['size']:
        raise ValueError('model size mismatch')
    with open(model_path, 'rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != file['sha256']:
        raise ValueError('model sha256 mismatch')
    for key in ('model_id', 'revision', 'license_id'):
        if not record.get(key):
            raise ValueError('missing registry provenance: ' + key)
    return {'role': role, 'model_id': record['model_id'], 'revision': record['revision'], 'license_id': record['license_id'], 'sha256': digest}

def evaluate_output(output, prompt, expected=None):
    """Conservative visible-output evidence; never infer tokens from exit status."""
    clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', output)
    # llama-cli may echo the prompt; do not count its answer-looking suffix.
    if prompt and prompt in clean:
        clean = clean.split(prompt, 1)[1]
    clean = re.split(r'\n(?:llama_perf_|main:|sampling time|prompt eval time|eval time)', clean, 1)[0]
    visible = clean.strip()
    if not visible:
        return {'status': 'NO_VISIBLE_OUTPUT', 'has_output': False, 'correct': None}
    if expected is None:
        return {'status': 'OUTPUT_UNGRADED', 'has_output': True, 'correct': None}
    # Explicit exact answer grading: do not accept 2, 24, or a correct digit inside an explanation.
    correct = visible == expected.strip()
    return {'status': 'ANSWER_CORRECT' if correct else 'ANSWER_INCORRECT',
            'has_output': True, 'correct': correct}

def probe(binary, model, prompt, timeout, threads, predict, expected=None):
    if not 0 < timeout <= 300 or not 1 <= threads <= 16 or not 1 <= predict <= 512:
        raise ValueError('invalid resource limits')
    if len(prompt) > 2048:
        raise ValueError('prompt too long')
    cmd = [str(binary), '-m', str(model), '-p', prompt, '-t', str(threads), '-n', str(predict)]
    start = time.monotonic()
    # Disk-backed capture avoids unbounded RAM use and never publishes raw model text.
    with tempfile.TemporaryFile(mode='w+b') as out:
        try:
            run = subprocess.run(cmd, stdout=out, stderr=subprocess.DEVNULL,
                                 stdin=subprocess.DEVNULL, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            return {'status': 'TIMEOUT', 'elapsed_s': round(time.monotonic()-start, 3)}
        elapsed = round(time.monotonic()-start, 3)
        if run.returncode != 0:
            return {'status': 'PROCESS_FAIL', 'returncode': run.returncode, 'elapsed_s': elapsed}
        size = out.tell()
        if size > 65536:
            return {'status': 'OUTPUT_TOO_LARGE', 'returncode': 0, 'elapsed_s': elapsed}
        out.seek(0)
        result = evaluate_output(out.read().decode('utf-8', errors='replace'), prompt, expected)
        return {**result, 'returncode': 0, 'elapsed_s': elapsed, 'output_bytes': size}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--registry', required=True)
    p.add_argument('--role', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--binary', required=True)
    p.add_argument('--prompt', default='Reply with exactly four: 2+2=')
    p.add_argument('--expected', default='4')
    p.add_argument('--timeout', type=float, default=40)
    p.add_argument('--threads', type=int, default=2)
    p.add_argument('--predict', type=int, default=32)
    a = p.parse_args()
    if not 0 < a.timeout <= 300 or not 1 <= a.threads <= 16 or not 1 <= a.predict <= 512:
        p.error('invalid resource limits')
    registry = json.loads(Path(a.registry).read_text())
    proof = validate_model(registry, a.role, a.model)
    if not Path(a.binary).is_file() or Path(a.binary).is_symlink() or not os.access(a.binary, os.X_OK):
        p.error('binary not executable')
    print(json.dumps({'model': proof, 'probe': probe(a.binary, a.model, a.prompt, a.timeout, a.threads, a.predict, a.expected)}, sort_keys=True))

if __name__ == '__main__':
    main()
