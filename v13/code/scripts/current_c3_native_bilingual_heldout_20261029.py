"""Preregistered unseen C3-only Linux-native bilingual heldout source oracle.

Six fixed Project Lumen cases; exact generated-only extraction excludes echoed
prompts and CLI banners. Diagnostic correctness cannot promote any V13 gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

from scripts import current_c3_native_bilingual_source_probe_20261029 as prior
from scripts.native_smoke_io_20261028 import run_one_turn
from v13.common import file_hash
from v13.models import download_file

SCHEMA = 'v13.current_c3_native_bilingual_heldout.v1'
# (id, exact public prompt, oracle amount; None means exact abstention)
CASES = (
    ('en_present', 'Answer in English using only the verified note. Verified note: Project Lumen has a budget of 160 euros. Question: What is the budget of Project Lumen? Give the amount and currency.', 160),
    ('en_absent', 'Answer in English using only verified notes. No verified note gives the budget of Project Lumen. Question: What is the budget of Project Lumen? If it is not stated, answer UNKNOWN.', None),
    ('en_revised', 'Answer in English using the latest verified note. Earlier note: Project Lumen budget was 160 euros. Latest correction: Project Lumen budget is now 75 euros. Question: What is the current budget? Give the amount and currency.', 75),
    ('de_present', 'Antworte auf Deutsch nur anhand der gesicherten Notiz. Gesicherte Notiz: Projekt Lumen hat ein Budget von 160 Euro. Frage: Wie hoch ist das Budget von Projekt Lumen? Nenne Betrag und Waehrung.', 160),
    ('de_absent', 'Antworte auf Deutsch nur anhand gesicherter Notizen. Es gibt keine gesicherte Notiz zum Budget von Projekt Lumen. Frage: Wie hoch ist das Budget? Wenn es nicht genannt wird, antworte UNBEKANNT.', None),
    ('de_revised', 'Antworte auf Deutsch anhand der neuesten gesicherten Notiz. Fruehere Notiz: Projekt Lumen hatte 160 Euro Budget. Neueste Korrektur: Projekt Lumen hat jetzt 75 Euro Budget. Frage: Wie hoch ist das aktuelle Budget? Nenne Betrag und Waehrung.', 75),
)
TIMING = re.compile(r'\n\n\[ Prompt: [0-9]+(?:\.[0-9]+)? t/s \| Generation: [0-9]+(?:\.[0-9]+)? t/s \]')
NUMERIC = re.compile(r'(?<![0-9])\d+(?:[.,]\d+)?(?![0-9])')
EURO = re.compile(r'(?<!\w)euros?(?!\w)', re.IGNORECASE)


def extract_generated(raw, prompt):
    """Fail closed unless one complete exact CLI echo and one timing footer."""
    if type(raw) is not bytes or not 0 < len(raw) < 1024 * 1024:
        raise ValueError('Missing or oversized raw native stdout')
    text = raw.decode('utf-8', errors='strict')
    anchor = '\n\n> ' + prompt + '\n'
    if text.count(anchor) != 1:
        raise ValueError('Missing or duplicated exact prompt echo')
    tail = text.split(anchor, 1)[1]
    matches = list(TIMING.finditer(tail))
    if len(matches) != 1 or 'Exiting...' not in tail[matches[0].end():]:
        raise ValueError('Missing or duplicated complete generation footer')
    generated = tail[:matches[0].start()].strip()
    if not generated or prompt in generated or '\x00' in generated:
        raise ValueError('Missing or echoed generated-only answer')
    return generated


def oracle_correct(name, generated, target):
    """Frozen source-grounded amount/abstention oracle; no prompt text enters."""
    if type(name) is not str or name not in {row[0] for row in CASES}:
        raise ValueError('Unknown fixed heldout case')
    if type(generated) is not str or not generated or len(generated) > 4096:
        return False
    if target is None:
        if not name.endswith('_absent'):
            raise ValueError('Invalid abstention oracle identity')
        normalized = generated.casefold().strip().strip(' .!?;:,')
        return normalized == ('unknown' if name.startswith('en_') else 'unbekannt')
    if type(target) is not int or target not in (160, 75):
        raise ValueError('Invalid registered amount oracle')
    if name.endswith('_absent'):
        raise ValueError('Amount oracle cannot belong to absent case')
    if 'unknown' in generated.casefold() or 'unbekannt' in generated.casefold():
        return False
    return NUMERIC.findall(generated) == [str(target)] and EURO.search(generated) is not None


def run(scratch_home, evidence_dir):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('Linux x86_64 native-only heldout')
    scratch_home, evidence_dir = Path(scratch_home), Path(evidence_dir)
    if scratch_home.exists() or evidence_dir.exists():
        raise FileExistsError('Fresh native scratch and evidence required')
    if shutil.disk_usage(scratch_home.parent).free < 2 * 1024**3:
        raise OSError('Native scratch reserve under 2 GiB')
    meta, model_spec, runner_spec = prior.pinned._catalog()
    scratch_home.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    model = download_file(model_spec, scratch_home / 'C3.gguf', progress=print)
    archive = download_file(runner_spec, scratch_home / 'runner.tar.gz', progress=print)
    if (model.stat().st_size != prior.pinned.MODEL_BYTES
            or file_hash(model) != prior.pinned.MODEL_SHA
            or archive.stat().st_size != prior.pinned.RUNNER_BYTES
            or file_hash(archive) != prior.pinned.RUNNER_SHA
            or model.open('rb').read(4) != b'GGUF'):
        raise ValueError('Pinned model/runner artifact mismatch')
    cli = prior.pinned._extract_runner(archive, scratch_home / 'runner')
    libdirs = sorted({str(p.parent) for p in (scratch_home / 'runner').rglob('*.so*')
                      if p.is_file()})
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join([str(cli.parent), *libdirs,
                                      env.get('LD_LIBRARY_PATH', '')])
    env['OMP_NUM_THREADS'] = '2'
    manifest = [(name, prompt, target) for name, prompt, target in CASES]
    report = {
        'schema': SCHEMA, 'evidence_kind': 'LINUX_NATIVE_C3_HELDOUT_FIXED_ORACLE_ONLY',
        'model_id': meta['model_id'], 'model_revision': meta['revision'],
        'license_id': meta['license_id'],
        'model_sha256': file_hash(model), 'runner_tar_sha256': file_hash(archive),
        'llama_cli_sha256': file_hash(cli),
        'model_catalog_blob': prior.pinned.CATALOG_BLOB,
        'model_manager_blob': prior.pinned.MANAGER_BLOB,
        'cohort_sha256': prior._digest(json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))),
        'n_tokens_max': prior.N_TOKENS, 'context_tokens': prior.N_CTX,
        'temperature': 0, 'cpu_threads': 2,
        'rows': [], 'n_scored': 0, 'n_correct': 0, 'n_unscorable': 6,
        'correct_fraction': 0.,
        'utility_proven': False, 'step2_gate_pass': False,
        'c2_jef_executed': False, 'b1_b2_executed': False,
        'memory_consumer_executed': False, 'redmi_measured': False,
        'tool_authority': False, 'age_authority': 0,
        'negative_gates_unchanged': prior.NEGATIVE_GATES,
    }
    for name, prompt, target in CASES:
        cmd = [str(cli), '-m', str(model), '-p', prompt,
               '-n', str(prior.N_TOKENS), '-c', str(prior.N_CTX),
               '-t', '2', '--temp', '0', '--single-turn']
        row = {'id': name, 'prompt_sha256': prior._digest(prompt),
               'oracle_kind': 'ABSTAIN' if target is None else 'AMOUNT_EURO',
               'oracle_correct': False, 'scorable': False}
        try:
            native = run_one_turn(cmd, evidence_dir, name.upper(), env, timeout=180)
            row.update(native)
            row['status'] = 'NATIVE_FAILED'
            if native['native_smoke_pass']:
                raw = (evidence_dir / (name.upper() + '_STDOUT_RAW.log')).read_bytes()
                try:
                    generated = extract_generated(raw, prompt)
                    row['generated_sha256'] = hashlib.sha256(generated.encode('utf-8')).hexdigest()
                    row['generated_chars'] = len(generated)
                    row['scorable'] = True
                    row['oracle_correct'] = bool(oracle_correct(name, generated, target))
                    row['status'] = 'SCORED'
                except (ValueError, UnicodeError) as exc:
                    row['status'] = 'UNSCORABLE'
                    row['parse_error_type'] = type(exc).__name__
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            row['status'] = 'NATIVE_ERROR'
            row['error_type'] = type(exc).__name__
            row['native_smoke_pass'] = False
        report['rows'].append(row)
        report['n_scored'] = sum(bool(r['scorable']) for r in report['rows'])
        report['n_correct'] = sum(bool(r['oracle_correct']) for r in report['rows'])
        report['n_unscorable'] = len(CASES) - report['n_scored']
        report['correct_fraction'] = report['n_correct'] / len(CASES)
        prior._write_atomic(evidence_dir / 'PROGRESS.json', report)
    report['status'] = ('CLOSED_NATIVE_HELDOUT' if report['n_scored'] == len(CASES)
                        else 'INCOMPLETE_NATIVE_HELDOUT')
    prior._write_atomic(evidence_dir / 'REPORT.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch-home', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    result = run(args.scratch_home, args.evidence_dir)
    print(json.dumps({
        'status': result['status'], 'n_scored': result['n_scored'],
        'n_correct': result['n_correct'],
        'correct_fraction': result['correct_fraction'],
        'utility_proven': False,
    }, sort_keys=True))
    return 0 if result['status'] == 'CLOSED_NATIVE_HELDOUT' else 2


if __name__ == '__main__':
    raise SystemExit(main())
