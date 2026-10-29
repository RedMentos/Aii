"""Six fixed public C3-only bilingual source/absence/revision Linux-native probes.

No native model weights, private user data, memory, JEF/C2, B1/B2, learning,
semantic score, Redmi proof or gate promotion are exported. The existing
current-catalog C3 smoke owns all artifact pins and safe runner extraction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile

from scripts import current_c3_native_linux_smoke_20261028 as pinned
from scripts.native_smoke_io_20261028 import run_one_turn
from v13.common import file_hash
from v13.models import download_file

SCHEMA = 'v13.current_c3_native_bilingual_source.v1'
N_TOKENS = 48
N_CTX = 512
CASES = (
    ('en_present', 'Answer in English using only the verified note. Verified note: Project Aurora has a budget of 120 euros. Question: What is the budget of Project Aurora? Give the amount and currency.'),
    ('en_absent', 'Answer in English using only verified notes. No verified note gives the budget of Project Aurora. Question: What is the budget of Project Aurora? If it is not stated, answer UNKNOWN.'),
    ('en_revised', 'Answer in English using the latest verified note. Earlier note: Project Aurora budget was 120 euros. Latest correction: Project Aurora budget is now 90 euros. Question: What is the current budget? Give the amount and currency.'),
    ('de_present', 'Antworte auf Deutsch nur anhand der gesicherten Notiz. Gesicherte Notiz: Projekt Aurora hat ein Budget von 120 Euro. Frage: Wie hoch ist das Budget von Projekt Aurora? Nenne Betrag und Waehrung.'),
    ('de_absent', 'Antworte auf Deutsch nur anhand gesicherter Notizen. Es gibt keine gesicherte Notiz zum Budget von Projekt Aurora. Frage: Wie hoch ist das Budget? Wenn es nicht genannt wird, antworte UNBEKANNT.'),
    ('de_revised', 'Antworte auf Deutsch anhand der neuesten gesicherten Notiz. Fruehere Notiz: Projekt Aurora hatte 120 Euro Budget. Neueste Korrektur: Projekt Aurora hat jetzt 90 Euro Budget. Frage: Wie hoch ist das aktuelle Budget? Nenne Betrag und Waehrung.'),
)
NEGATIVE_GATES = {
    'age0': 'RECORD_ONLY', 'step2': 'UTILITY_FAIL',
    'b3_l1': 'FAIL', 'body_jepa': 'UNAVAILABLE',
    'lp3': 'FAIL', 'jepa_weight': 0, 'redmi_measured': False,
    'whole_system_complete': False,
}


def _digest(raw):
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _write_atomic(path, payload):
    fd, temp = tempfile.mkstemp(prefix='.report-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, sort_keys=True, allow_nan=False)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def run(scratch_home, evidence_dir):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('Linux x86_64 native-only probe')
    scratch_home, evidence_dir = Path(scratch_home), Path(evidence_dir)
    if scratch_home.exists() or evidence_dir.exists():
        raise FileExistsError('Fresh scratch and evidence directories required')
    if shutil.disk_usage(scratch_home.parent).free < 2 * 1024**3:
        raise OSError('Native scratch disk reserve under 2 GiB')
    meta, model_spec, runner_spec = pinned._catalog()
    scratch_home.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    model = download_file(model_spec, scratch_home / 'C3.gguf', progress=print)
    archive = download_file(runner_spec, scratch_home / 'runner.tar.gz', progress=print)
    if (model.stat().st_size != pinned.MODEL_BYTES
            or file_hash(model) != pinned.MODEL_SHA
            or archive.stat().st_size != pinned.RUNNER_BYTES
            or file_hash(archive) != pinned.RUNNER_SHA
            or model.open('rb').read(4) != b'GGUF'):
        raise ValueError('Official pinned native artifact mismatch')
    cli = pinned._extract_runner(archive, scratch_home / 'runner')
    libdirs = sorted({str(p.parent) for p in (scratch_home / 'runner').rglob('*.so*')
                      if p.is_file()})
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join([str(cli.parent), *libdirs,
                                      env.get('LD_LIBRARY_PATH', '')])
    env['OMP_NUM_THREADS'] = '2'
    report = {
        'schema': SCHEMA, 'evidence_kind': 'LINUX_NATIVE_C3_ONLY',
        'platform': platform.platform(),
        'model_id': meta['model_id'], 'model_revision': meta['revision'],
        'license_id': meta['license_id'],
        'model_sha256': file_hash(model),
        'runner_tar_sha256': file_hash(archive),
        'llama_cli_sha256': file_hash(cli),
        'model_catalog_blob': pinned.CATALOG_BLOB,
        'model_manager_blob': pinned.MANAGER_BLOB,
        'n_tokens_max': N_TOKENS, 'context_tokens': N_CTX,
        'temperature': 0, 'cpu_threads': 2,
        'prompt_set_sha256': _digest(json.dumps(CASES, ensure_ascii=False, separators=(',', ':'))),
        'rows': [], 'all_native_generated': False,
        'semantic_score': 'UNSCORED_NATIVE_OBSERVATION',
        'utility_proven': False, 'c2_jef_executed': False,
        'b1_b2_executed': False, 'memory_consumer_executed': False,
        'native_executed': True, 'redmi_measured': False,
        'tool_authority': False, 'age_authority': 0,
        'negative_gates_unchanged': NEGATIVE_GATES,
    }
    for name, prompt in CASES:
        cmd = [str(cli), '-m', str(model), '-p', prompt, '-n', str(N_TOKENS),
               '-c', str(N_CTX), '-t', '2', '--temp', '0', '--single-turn']
        try:
            raw = run_one_turn(cmd, evidence_dir, name.upper(), env, timeout=180)
            row = {
                'id': name, 'prompt_sha256': _digest(prompt),
                **raw, 'status': 'NATIVE_GENERATED' if raw['native_smoke_pass'] else 'NATIVE_FAILED',
            }
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            row = {
                'id': name, 'prompt_sha256': _digest(prompt),
                'status': 'NATIVE_ERROR', 'error_type': type(exc).__name__,
                'native_smoke_pass': False,
            }
        report['rows'].append(row)
        # Each completed attempt is durably recorded before the next native job.
        progress = evidence_dir / 'PROGRESS.json'
        _write_atomic(progress, report)
    report['all_native_generated'] = len(report['rows']) == len(CASES) and all(
        row['native_smoke_pass'] for row in report['rows'])
    report['status'] = ('NATIVE_GENERATED_UNSCORED' if report['all_native_generated']
                        else 'NATIVE_INCOMPLETE')
    _write_atomic(evidence_dir / 'REPORT.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch-home', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    report = run(args.scratch_home, args.evidence_dir)
    print(json.dumps({
        'status': report['status'], 'rows': len(report['rows']),
        'native_generated': sum(r['native_smoke_pass'] for r in report['rows']),
        'semantic_score': report['semantic_score'], 'utility_proven': False,
    }, sort_keys=True))
    return 0 if report['all_native_generated'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
