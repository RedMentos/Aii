#!/usr/bin/env python3
"""Install the SHADOW tool-consequence forecast (v13/toolforecast.py) with a bound, parity-checked native encoder.

  build-assets  (once, where the sealed round-7/8 evidence is restored) copies the preregistered pick of each confirmed
                world (tap l_out-11 last token, arm `full`, seed 13; fixed before any live use) into
                specs/tool_forecast/<world>/, writes its held-out test episodes as the parity set, and checks that the
                runtime formula reproduces the measured test MSE of metrics.json from the originally stored taps.
                Writes specs/tool-forecast.json with every hash and the evidence ZIP it came from.
  install       (on each device) verifies the GGUF hash, taps every parity text with the given native_layer_taps build
                and requires, per world and per action, the same predictive gate the candidate passed
                (forecast MSE < .98 x min(copy, mean delta) on its own test partition). Only then writes
                <home>/data/tool_forecast/encoder.json. A rebuilt tap tool is not byte-identical to the capture build
                (other binary, possibly other CPU); the parity record states the measured drift instead of hiding it.
No runtime authority is granted; `:toolforecast shadow` still has to be switched on by the user.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

import numpy as np

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from v13 import toolforecast as tf

PICK = {'layer': 11, 'pooling': 'last', 'arm': 'full', 'seed': 13}
WORLDS = {
    'calc_counter': {'run': 'runs/tool_l11_last/full-seed13', 'results': 'round7-fresh-results', 'raw': 'round7-fresh-raw',
                     'world': 'world/world.json', 'capture': 'capture-tool', 'proof': 'docs/proofs/continuation-20261012/action-jepa-round7-fresh',
                     'results_zip_sha256': '4e66fa5654bdedd0b2d02de9e94d999792a138fbcd9fa2220ae9cc3eb72a51ed',
                     'raw_zip_sha256': 'af3213c11efa2397905ae980f8d277c9989a10ed1ab78c642e9c424213dc4cf3'},
    'note_edit': {'run': 'runs/note_l11_last/full-seed13', 'results': 'round8-note-tool-results', 'raw': 'round8-note-tool-raw',
                  'world': 'world/world.json', 'capture': 'capture', 'proof': 'docs/proofs/continuation-20261012/action-jepa-round8-note-tool',
                  'results_zip_sha256': '330db432371b9a89909575644e25deab101cf0e7181e835dde8613d62d3c6a85',
                  'raw_zip_sha256': 'ff72b0e4d918319d3e21df8402c0f1769260793828fd50227df21c041fbe2c5d'}}
GATE = .98            # action_jepa_round6_ridge: prediction_mse < .98 * min(controls)
DRIFT_SAMPLE = 16     # stored capture taps shipped to measure encoder drift


def episodes(world_doc):
    """Test episodes after the export's partition-crossing exclusion (action_jepa_round5_tools.export)."""
    from export_action_jepa_dataset import source_identity
    eps = world_doc['episodes']
    owner = {}
    for e in eps:
        for t in [e['input'], *e['outcomes'].values()]:
            owner.setdefault(source_identity(t), set()).add(e['partition'])
    crossing = {t for t, parts in owner.items() if len(parts) > 1}
    return [e for e in eps if not any(source_identity(t) in crossing for t in [e['input'], *e['outcomes'].values()])]


def scores(ck, rows, tap_of):
    """Per-action test MSE of forecast and controls in the fixed projection (same formulas as round 6 `score`)."""
    out = {}
    for action in ck.actions:
        sel = [r for r in rows if r['action'] == action]
        acc = {'forecast': [], 'copy': [], 'mean_delta': []}
        for r in sel:
            pred = ck.predict(tap_of(r['input']), action)
            ref = tap_of(r['outcome']) @ ck.p
            for k in acc:
                acc[k].append(np.mean((pred[k] - ref) ** 2))
        out[action] = {k: float(np.mean(v)) for k, v in acc.items()} | {'rows': len(sel)}
    return out


def gate(per_action):
    return all(v['forecast'] < GATE * min(v['copy'], v['mean_delta']) for v in per_action.values())


def build_assets(args):
    restored = Path(args.restored)
    manifest = {'schema': tf.SCHEMA + '-manifest', 'pick': PICK, 'gate': GATE,
                'encoder': {'model_sha256': None, 'layer': PICK['layer'], 'pooling': PICK['pooling'], 'transform': 'rms_normalize',
                            'capture_tool_sha256': None, 'tool_source': 'scripts/native_layer_taps.cpp'},
                'worlds': {}}
    for world, w in WORLDS.items():
        run = restored / w['results'] / w['run']
        dest = APP / 'specs' / 'tool_forecast' / world
        dest.mkdir(parents=True, exist_ok=True)
        for name in ('candidate.npz', 'metrics.json'):
            shutil.copyfile(run / name, dest / name)
        metrics = json.loads((dest / 'metrics.json').read_text())
        cap = restored / w['raw'] / w['capture']
        report = json.loads((cap / 'capture-report.json').read_text())
        meta = json.loads((cap / 'taps.json').read_text())
        texts = (cap / 'inputs.txt').read_text().split('\n')[:-1]
        if len(texts) != meta['texts'] or tf.sha_file(cap / 'taps.bin') != report['raw_bin_sha256']:
            raise ValueError(world + ': capture bytes differ from capture report')
        li = meta['layers'].index(PICK['layer'])
        raw = np.fromfile(cap / 'taps.bin', dtype=np.float32).reshape(meta['texts'], len(meta['layers']), 2, meta['n_embd'])[:, li, 0]
        stored = dict(zip(texts, raw))
        doc = json.loads((restored / w['raw'] / w['world']).read_text())
        rows = [{'input': e['input'], 'action': a, 'outcome': e['outcomes'][a]} for e in episodes(doc)
                if e['partition'] == 'test' for a in metrics['actions']]
        (dest / 'parity.json').write_text(json.dumps({'schema': tf.SCHEMA + '-parity', 'world': world, 'partition': 'test',
                                                       'rows': rows}, indent=0) + '\n')
        sample = texts[:DRIFT_SAMPLE]
        np.savez(dest / 'drift-sample.npz', texts=np.asarray(sample), taps=np.stack([stored[t] for t in sample]))
        entry = {'source': w['proof'] + ' (' + w['run'] + ')', 'results_zip_sha256': w['results_zip_sha256'],
                 'raw_zip_sha256': w['raw_zip_sha256'], 'arm': PICK['arm'], 'actions': metrics['actions'],
                 'checkpoint': 'specs/tool_forecast/%s/candidate.npz' % world, 'checkpoint_sha256': tf.sha_file(dest / 'candidate.npz'),
                 'metrics': 'specs/tool_forecast/%s/metrics.json' % world, 'metrics_sha256': tf.sha_file(dest / 'metrics.json'),
                 'parity': 'specs/tool_forecast/%s/parity.json' % world, 'parity_sha256': tf.sha_file(dest / 'parity.json'),
                 'drift_sample': 'specs/tool_forecast/%s/drift-sample.npz' % world, 'drift_sample_sha256': tf.sha_file(dest / 'drift-sample.npz'),
                 'capture_tool_sha256': report['tool_sha256'], 'model_sha256': report['model_sha256']}
        manifest['worlds'][world] = entry
        for k in ('model_sha256', 'capture_tool_sha256'):
            v = report['tool_sha256' if k == 'capture_tool_sha256' else k]
            if manifest['encoder'][k] not in (None, v):
                raise ValueError('Worlds were captured with different encoders')
            manifest['encoder'][k] = v
        ck = tf.Checkpoint(world, entry)
        got = scores(ck, rows, lambda t: tf.rms_normalize(stored[t]))
        want = {metrics['actions'][int(j)]: v['prediction_mse'] for j, v in metrics['after']['test']['per_action'].items()}
        diff = max(abs(got[a]['forecast'] - want[a]) / want[a] for a in want)
        if diff > 1e-6 or not gate(got):  # float32 RMS summation order differs from the batch export (~1e-7)
            raise ValueError('%s: runtime formula does not reproduce measured test MSE (rel %.3g)' % (world, diff))
        entry['reproduced_test_mse_max_rel_diff'] = diff
        print(json.dumps({'world': world, 'test_rows': len(rows), 'reproduced_max_rel_diff': diff,
                          'ratio_to_best_control': {a: round(v['forecast'] / min(v['copy'], v['mean_delta']), 4) for a, v in got.items()}}))
    tf.MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    return manifest


def install(args):
    manifest = json.loads(tf.MANIFEST.read_text())
    want = manifest['encoder']
    model_sha = tf.sha_file(args.model)
    if model_sha != want['model_sha256']:
        raise SystemExit('GGUF differs from the capture model')
    enc = {'schema': tf.SCHEMA + '-encoder', 'tool_path': str(Path(args.tool).resolve()), 'tool_sha256': tf.sha_file(args.tool),
           'model_path': str(Path(args.model).resolve()), 'model_sha256': model_sha, 'layer': want['layer'], 'pooling': want['pooling'],
           'capture_tool_sha256': want['capture_tool_sha256'], 'backend_dir': str(Path(args.backend_dir).resolve()) if args.backend_dir else None,
           'tool_source_sha256': tf.sha_file(APP / want['tool_source'])}
    taps = tf.NativeLayerTaps(enc, threads=args.threads, timeout_s=3600)
    parity = {'gate': GATE, 'worlds': {}}
    ok = True
    for world, entry in manifest['worlds'].items():
        for k in ('parity', 'drift_sample'):
            if tf.sha_file(APP / entry[k]) != entry[k + '_sha256']:
                raise SystemExit(world + ': ' + k + ' bytes differ from manifest')
        rows = json.loads((APP / entry['parity']).read_text())['rows']
        texts = sorted({t for r in rows for t in (r['input'], r['outcome'])})
        with np.load(APP / entry['drift_sample'], allow_pickle=False) as z:
            sample, stored = [str(t) for t in z['texts']], z['taps']
        got = taps.tap(texts + sample)
        tap_of = dict(zip(texts, (tf.rms_normalize(v) for v in got[:len(texts)])))
        a, b = tf.rms_normalize(stored), tf.rms_normalize(got[len(texts):])
        cos = (a * b).sum(1) / np.linalg.norm(a, axis=1) / np.linalg.norm(b, axis=1)
        per = scores(tf.Checkpoint(world, entry), rows, tap_of.__getitem__)
        passed = gate(per)
        ok &= passed
        parity['worlds'][world] = {'pass': passed, 'texts': len(texts), 'per_action': per,
                                   'ratio_to_best_control': {k: round(v['forecast'] / min(v['copy'], v['mean_delta']), 4) for k, v in per.items()},
                                   'drift_vs_capture': {'bit_identical': bool(np.array_equal(stored, got[len(texts):])),
                                                        'cos_min': float(cos.min()), 'rel_rms_max': float(np.sqrt(((a - b) ** 2).mean(1)).max())}}
    parity['status'] = 'PASS' if ok else 'FAIL'
    enc['parity'] = parity
    out = Path(args.home) / 'data' / 'tool_forecast'
    out.mkdir(parents=True, exist_ok=True)
    target = out / ('encoder.json' if ok else 'encoder-parity-failed.json')
    target.write_text(json.dumps(enc, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'status': parity['status'], 'written': str(target),
                      'worlds': {w: {k: v[k] for k in ('pass', 'ratio_to_best_control', 'drift_vs_capture')} for w, v in parity['worlds'].items()}}, indent=1))
    return 0 if ok else 1


def main():
    root = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = root.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build-assets')
    b.add_argument('--restored', required=True, help='folder with the unzipped round-7/8 results and raw ZIPs')
    i = sub.add_parser('install')
    for name in ('--home', '--tool', '--model'):
        i.add_argument(name, required=True)
    i.add_argument('--threads', type=int, default=4)
    i.add_argument('--backend-dir', help='runner library folder for builds with dynamically loaded ggml backends (b10964 release)')
    args = root.parse_args()
    if args.command == 'build-assets':
        build_assets(args)
        return 0
    return install(args)


if __name__ == '__main__':
    sys.exit(main())
