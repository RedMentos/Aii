"""Preregistered unseen German C3 BASE vs one-line FORMAT native pilot.

New Projekt Solis 180->65 Euro and absent cases. C3-only, six bounded native
calls; strict generated-only oracle, no production prompt change or gate pass.
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

from scripts import current_c3_native_bilingual_heldout_20261029 as heldout
from scripts.native_smoke_io_20261028 import run_one_turn
from v13.common import file_hash
from v13.models import download_file

SCHEMA = 'v13.current_c3_native_german_format_pair.v1'
CASES = (
    ('de_base_present', 'Antworte auf Deutsch nur anhand der gesicherten Notiz. Gesicherte Notiz: Projekt Solis hat ein Budget von 180 Euro. Frage: Wie hoch ist das Budget von Projekt Solis? Nenne Betrag und Waehrung.', 180, 'BASE'),
    ('de_format_present', 'Antworte auf Deutsch nur anhand der gesicherten Notiz. Gesicherte Notiz: Projekt Solis hat ein Budget von 180 Euro. Frage: Wie hoch ist das Budget von Projekt Solis? Antworte in genau einer Zeile im Format <Zahl> Euro. Keine weiteren Woerter, Felder oder Zahlen.', 180, 'FORMAT'),
    ('de_base_absent', 'Antworte auf Deutsch nur anhand gesicherter Notizen. Es gibt keine gesicherte Notiz zum Budget von Projekt Solis. Frage: Wie hoch ist das Budget? Wenn es nicht genannt wird, antworte UNBEKANNT.', None, 'BASE'),
    ('de_format_absent', 'Antworte auf Deutsch nur anhand gesicherter Notizen. Es gibt keine gesicherte Notiz zum Budget von Projekt Solis. Frage: Wie hoch ist das Budget? Antworte mit genau einem Wort: UNBEKANNT. Keine weiteren Woerter, Felder oder Zahlen.', None, 'FORMAT'),
    ('de_base_revised', 'Antworte auf Deutsch anhand der neuesten gesicherten Notiz. Fruehere Notiz: Projekt Solis hatte 180 Euro Budget. Neueste Korrektur: Projekt Solis hat jetzt 65 Euro Budget. Frage: Wie hoch ist das aktuelle Budget? Nenne Betrag und Waehrung.', 65, 'BASE'),
    ('de_format_revised', 'Antworte auf Deutsch anhand der neuesten gesicherten Notiz. Fruehere Notiz: Projekt Solis hatte 180 Euro Budget. Neueste Korrektur: Projekt Solis hat jetzt 65 Euro Budget. Frage: Wie hoch ist das aktuelle Budget? Antworte in genau einer Zeile im Format <Zahl> Euro. Keine weiteren Woerter, Felder oder Zahlen.', 65, 'FORMAT'),
)


def oracle_correct(name, generated, target):
    if name not in {row[0] for row in CASES}:
        raise ValueError('Unregistered paired case')
    if type(generated) is not str or not generated or len(generated) > 4096:
        return False
    if target is None:
        if not name.endswith('_absent'):
            raise ValueError('Invalid absent oracle')
        return generated.casefold().strip().strip(' .!?;:,') == 'unbekannt'
    if type(target) is not int or target not in (180, 65) or name.endswith('_absent'):
        raise ValueError('Invalid numeric oracle')
    if 'unknown' in generated.casefold() or 'unbekannt' in generated.casefold():
        return False
    return heldout.NUMERIC.findall(generated) == [str(target)] and heldout.EURO.search(generated) is not None


def run(scratch_home, evidence_dir):
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64', 'amd64'):
        raise ValueError('Linux x86_64 native-only German paired pilot')
    scratch_home, evidence_dir = Path(scratch_home), Path(evidence_dir)
    if scratch_home.exists() or evidence_dir.exists():
        raise FileExistsError('Fresh native scratch and evidence required')
    if shutil.disk_usage(scratch_home.parent).free < 2 * 1024**3:
        raise OSError('Native scratch reserve under 2 GiB')
    meta, model_spec, runner_spec = heldout.prior.pinned._catalog()
    scratch_home.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)
    model = download_file(model_spec, scratch_home / 'C3.gguf', progress=print)
    archive = download_file(runner_spec, scratch_home / 'runner.tar.gz', progress=print)
    if (model.stat().st_size != heldout.prior.pinned.MODEL_BYTES
            or file_hash(model) != heldout.prior.pinned.MODEL_SHA
            or archive.stat().st_size != heldout.prior.pinned.RUNNER_BYTES
            or file_hash(archive) != heldout.prior.pinned.RUNNER_SHA
            or model.open('rb').read(4) != b'GGUF'):
        raise ValueError('Pinned model/runner artifact mismatch')
    cli = heldout.prior.pinned._extract_runner(archive, scratch_home / 'runner')
    libdirs = sorted({str(p.parent) for p in (scratch_home / 'runner').rglob('*.so*')
                      if p.is_file()})
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = ':'.join([str(cli.parent), *libdirs,
                                      env.get('LD_LIBRARY_PATH', '')])
    env['OMP_NUM_THREADS'] = '2'
    report = {
        'schema': SCHEMA, 'evidence_kind': 'LINUX_NATIVE_C3_GERMAN_FORMAT_PAIR_ONLY',
        'model_id': meta['model_id'], 'model_revision': meta['revision'],
        'license_id': meta['license_id'],
        'model_sha256': file_hash(model), 'runner_tar_sha256': file_hash(archive),
        'llama_cli_sha256': file_hash(cli),
        'model_catalog_blob': heldout.prior.pinned.CATALOG_BLOB,
        'model_manager_blob': heldout.prior.pinned.MANAGER_BLOB,
        'cohort_sha256': heldout.prior._digest(json.dumps(CASES, ensure_ascii=False, separators=(',', ':'))),
        'n_tokens_max': heldout.prior.N_TOKENS, 'context_tokens': heldout.prior.N_CTX,
        'temperature': 0, 'cpu_threads': 2,
        'rows': [], 'n_scored': 0, 'base_correct': 0, 'format_correct': 0,
        'paired_gain': None, 'utility_proven': False, 'step2_gate_pass': False,
        'c2_jef_executed': False, 'b1_b2_executed': False,
        'memory_consumer_executed': False, 'redmi_measured': False,
        'tool_authority': False, 'age_authority': 0,
        'negative_gates_unchanged': heldout.prior.NEGATIVE_GATES,
    }
    for name, prompt, target, arm in CASES:
        cmd = [str(cli), '-m', str(model), '-p', prompt,
               '-n', str(heldout.prior.N_TOKENS), '-c', str(heldout.prior.N_CTX),
               '-t', '2', '--temp', '0', '--single-turn']
        row = {'id': name, 'arm': arm, 'prompt_sha256': heldout.prior._digest(prompt),
               'oracle_kind': 'ABSTAIN' if target is None else 'AMOUNT_EURO',
               'oracle_correct': False, 'scorable': False}
        try:
            native = run_one_turn(cmd, evidence_dir, name.upper(), env, timeout=180)
            row.update(native)
            row['status'] = 'NATIVE_FAILED'
            if native['native_smoke_pass']:
                raw = (evidence_dir / (name.upper() + '_STDOUT_RAW.log')).read_bytes()
                try:
                    generated = heldout.extract_generated(raw, prompt)
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
        report['base_correct'] = sum(bool(r['oracle_correct']) for r in report['rows'] if r['arm']=='BASE')
        report['format_correct'] = sum(bool(r['oracle_correct']) for r in report['rows'] if r['arm']=='FORMAT')
        heldout.prior._write_atomic(evidence_dir / 'PROGRESS.json', report)
    if report['n_scored'] == len(CASES):
        report['status'] = 'CLOSED_NATIVE_PAIRED'
        report['paired_gain'] = report['format_correct'] - report['base_correct']
    else:
        report['status'] = 'INCOMPLETE_NATIVE_PAIRED'
    heldout.prior._write_atomic(evidence_dir / 'REPORT.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch-home', required=True, type=Path)
    parser.add_argument('--evidence-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    r = run(args.scratch_home, args.evidence_dir)
    print(json.dumps({'status':r['status'], 'n_scored':r['n_scored'],
                      'base_correct':r['base_correct'],
                      'format_correct':r['format_correct'],
                      'paired_gain':r['paired_gain'],
                      'utility_proven':False}, sort_keys=True))
    return 0 if r['status']=='CLOSED_NATIVE_PAIRED' else 2


if __name__ == '__main__':
    raise SystemExit(main())
