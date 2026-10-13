#!/usr/bin/env python3
"""Install the SHADOW tool-consequence forecast (v13/toolforecast.py) with a bound, parity-checked native encoder.

  build-assets  (once, where the sealed round-7/8 evidence is restored) copies the preregistered pick of each confirmed
                world (tap l_out-11 last token, arm `full`, seed 13; fixed before any live use) into
                specs/tool_forecast/<world>/, writes its held-out test episodes as the parity set, and checks that the
                runtime formula reproduces the measured test MSE of metrics.json from the originally stored taps.
                Writes specs/tool-forecast.json with every hash and the evidence ZIP it came from.
  build-replay  (once, after build-assets) adds per world the candidate's own training pairs as float16 taps, which
                `:toolforecast learn` replays next to the live experience.
  build-competence  (once, after build-assets) adds per world the pre-effect domain reference: training context
                taps and a threshold calibrated on the calibration partition (never the test partition).
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


COMPETENCE_K = 5           # nearest training contexts averaged
COMPETENCE_QUANTILE = .99  # of calibration-partition distances


def build_competence(args):
    """Add each world's pre-effect domain reference (training context taps + calibrated threshold) to the manifest.

    Uses only the train and calibration partitions of the stored capture (never test): training contexts are the
    reference set, the threshold is the 99th percentile of the calibration contexts' mean cosine distance to their
    5 nearest training contexts. Existing assets and hashes stay untouched."""
    restored = Path(args.restored)
    manifest = json.loads(tf.MANIFEST.read_text())
    out = {}
    for world, w in WORLDS.items():
        entry = manifest['worlds'][world]
        cap = restored / w['raw'] / w['capture']
        report = json.loads((cap / 'capture-report.json').read_text())
        meta = json.loads((cap / 'taps.json').read_text())
        texts = (cap / 'inputs.txt').read_text().split('\n')[:-1]
        if (len(texts) != meta['texts'] or tf.sha_file(cap / 'taps.bin') != report['raw_bin_sha256']
                or report['tool_sha256'] != entry['capture_tool_sha256']):
            raise ValueError(world + ': capture bytes/encoder differ from manifest')
        li = meta['layers'].index(PICK['layer'])
        both = np.fromfile(cap / 'taps.bin', dtype=np.float32).reshape(meta['texts'], len(meta['layers']), 2, meta['n_embd'])[:, li]
        stored, stored_mean = dict(zip(texts, both[:, 0])), dict(zip(texts, both[:, 1]))
        eps = episodes(json.loads((restored / w['raw'] / w['world']).read_text()))
        part = lambda name: sorted({e['input'] for e in eps if e['partition'] == name})
        train = np.stack([tf.rms_normalize(stored[t]) for t in part('train')]).astype(np.float32)
        train_mean = np.stack([tf.rms_normalize(stored_mean[t]) for t in part('train')]).astype(np.float32)
        dest = APP / 'specs' / 'tool_forecast' / world / 'competence.npz'
        arrays = {'train_taps': train, 'train_taps_mean': train_mean, 'k': np.asarray(COMPETENCE_K)}
        np.savez(dest, **arrays, threshold=np.asarray(1.), threshold_mean=np.asarray(1.))
        entry['competence'], entry['competence_sha256'] = 'specs/tool_forecast/%s/competence.npz' % world, tf.sha_file(dest)
        ck = tf.Checkpoint(world, entry)   # thresholds 1.0: score = raw distances, to calibrate both
        cal = [ck.competence(tf.rms_normalize(stored[t]), tf.rms_normalize(stored_mean[t])) for t in part('calibration')]
        threshold = float(np.quantile([c['distance'] for c in cal], COMPETENCE_QUANTILE))
        threshold_mean = float(np.quantile([c['distance_mean'] for c in cal], COMPETENCE_QUANTILE))
        np.savez(dest, **arrays, threshold=np.asarray(threshold), threshold_mean=np.asarray(threshold_mean))
        entry['competence_sha256'] = tf.sha_file(dest)
        entry['competence_reference'] = {'train_contexts': len(train), 'calibration_contexts': len(cal), 'k': COMPETENCE_K,
                                         'quantile': COMPETENCE_QUANTILE, 'threshold': threshold, 'threshold_mean': threshold_mean,
                                         'signal': 'knn%d_cosine_last_or_mean' % COMPETENCE_K,
                                         'calibration_distance_median': float(np.median([c['distance'] for c in cal])),
                                         'calibration_distance_mean_median': float(np.median([c['distance_mean'] for c in cal])),
                                         'partitions_used': ['train', 'calibration'],
                                         'previous': {'signal': 'knn5_cosine_distance (last token only)', 'used_until': 'abe6cc5'}}
        out[world] = entry['competence_reference']
    tf.MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    print(json.dumps(out, indent=1))
    return out


def build_replay(args):
    """Add each world's replay set: the candidate's own training pairs (train partition only), float16 taps.

    `:toolforecast learn` refits on replay + live experience so new regions are learned next to the old one instead
    of overwriting it (interleaved replay, Canon §15). Existing assets and hashes stay untouched."""
    restored = Path(args.restored)
    manifest = json.loads(tf.MANIFEST.read_text())
    out = {}
    for world, w in WORLDS.items():
        entry = manifest['worlds'][world]
        cap = restored / w['raw'] / w['capture']
        report = json.loads((cap / 'capture-report.json').read_text())
        meta = json.loads((cap / 'taps.json').read_text())
        texts = (cap / 'inputs.txt').read_text().split('\n')[:-1]
        if (len(texts) != meta['texts'] or tf.sha_file(cap / 'taps.bin') != report['raw_bin_sha256']
                or report['tool_sha256'] != entry['capture_tool_sha256']):
            raise ValueError(world + ': capture bytes/encoder differ from manifest')
        li = meta['layers'].index(PICK['layer'])
        raw = np.fromfile(cap / 'taps.bin', dtype=np.float32).reshape(meta['texts'], len(meta['layers']), 2, meta['n_embd'])[:, li, 0]
        stored = dict(zip(texts, raw))
        eps = [e for e in episodes(json.loads((restored / w['raw'] / w['world']).read_text())) if e['partition'] == 'train']
        pairs = [(e['input'], e['outcomes'][a], j) for e in eps for j, a in enumerate(entry['actions'])]
        uniq = sorted({t for i, o, _ in pairs for t in (i, o)})
        index = {t: k for k, t in enumerate(uniq)}
        dest = APP / 'specs' / 'tool_forecast' / world / 'replay.npz'
        np.savez(dest, taps=np.stack([tf.rms_normalize(stored[t]) for t in uniq]).astype(np.float16),
                 context=np.asarray([index[i] for i, _, _ in pairs]), outcome=np.asarray([index[o] for _, o, _ in pairs]),
                 action=np.asarray([j for _, _, j in pairs]))
        entry['replay'], entry['replay_sha256'] = 'specs/tool_forecast/%s/replay.npz' % world, tf.sha_file(dest)
        entry['replay_reference'] = {'pairs': len(pairs), 'texts': len(uniq), 'partition': 'train', 'dtype': 'float16'}
        out[world] = entry['replay_reference']
    tf.MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + '\n')
    print(json.dumps(out, indent=1))
    return out


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
    retention = {}
    ok = True
    out = Path(args.home) / 'data' / 'tool_forecast'
    out.mkdir(parents=True, exist_ok=True)
    # Retention taps go to new generation-named files; the live encoder.json and the files it names stay untouched until
    # every world passed, then encoder.json is switched atomically and only then are unreferenced generations removed.
    gen = tf.uid('ret')
    written = []
    try:
        ok = _parity_worlds(args, manifest, taps, out, gen, written, parity, retention)
    except BaseException:
        for f in written:
            f.unlink(missing_ok=True)
        raise
    parity['status'] = 'PASS' if ok else 'FAIL'
    enc['parity'] = parity
    enc['retention'] = retention   # retention reference for `:toolforecast learn`
    if not ok:
        for f in written:          # a failed install never replaces nor leaves retention files
            f.unlink(missing_ok=True)
        enc['retention'] = {w: v | {'written': False} for w, v in retention.items()}
    target = out / ('encoder.json' if ok else 'encoder-parity-failed.json')
    tf.atomic_write(target, json.dumps(enc, indent=1, sort_keys=True) + '\n')
    if ok:
        keep = {Path(v['path']).name for v in retention.values()}
        for f in out.glob('retention-*.npz'):
            if f.name not in keep:
                f.unlink(missing_ok=True)
    print(json.dumps({'status': parity['status'], 'written': str(target),
                      'worlds': {w: {k: v[k] for k in ('pass', 'ratio_to_best_control', 'drift_vs_capture')} for w, v in parity['worlds'].items()}}, indent=1))
    return 0 if ok else 1


def _parity_worlds(args, manifest, taps, out, gen, written, parity, retention):
    ok = True
    for world, entry in manifest['worlds'].items():
        for k in ('parity', 'drift_sample'):
            if tf.sha_file(APP / entry[k]) != entry[k + '_sha256']:
                raise SystemExit(world + ': ' + k + ' bytes differ from manifest')
        rows = json.loads((APP / entry['parity']).read_text())['rows']
        texts = sorted({t for r in rows for t in (r['input'], r['outcome'])})
        with np.load(APP / entry['drift_sample'], allow_pickle=False) as z:
            sample, stored = [str(t) for t in z['texts']], z['taps']
        got, got_mean = taps.tap_both(texts + sample)
        tap_of = dict(zip(texts, (tf.rms_normalize(v) for v in got[:len(texts)])))
        a, b = tf.rms_normalize(stored), tf.rms_normalize(got[len(texts):])
        cos = (a * b).sum(1) / np.linalg.norm(a, axis=1) / np.linalg.norm(b, axis=1)
        per = scores(tf.Checkpoint(world, entry), rows, tap_of.__getitem__)
        ret = out / ('retention-%s-%s.npz' % (world, gen))
        written.append(ret)
        tf.save_npz(ret, texts=np.asarray(texts), taps=np.stack([tap_of[t] for t in texts]).astype(np.float32),
                    taps_mean=tf.rms_normalize(got_mean[:len(texts)]).astype(np.float32))
        retention[world] = {'path': str(ret.resolve()), 'sha256': tf.sha_file(ret), 'texts': len(texts),
                            'partition': 'test (the candidate\'s own held-out episodes, this device\'s encoder)'}
        passed = gate(per)
        ok &= passed
        parity['worlds'][world] = {'pass': passed, 'texts': len(texts), 'per_action': per,
                                   'ratio_to_best_control': {k: round(v['forecast'] / min(v['copy'], v['mean_delta']), 4) for k, v in per.items()},
                                   'drift_vs_capture': {'bit_identical': bool(np.array_equal(stored, got[len(texts):])),
                                                        'cos_min': float(cos.min()), 'rel_rms_max': float(np.sqrt(((a - b) ** 2).mean(1)).max())}}
    return ok


def main():
    root = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = root.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build-assets')
    b.add_argument('--restored', required=True, help='folder with the unzipped round-7/8 results and raw ZIPs')
    c = sub.add_parser('build-competence')
    c.add_argument('--restored', required=True, help='as build-assets; adds competence.npz per world (train/calibration only)')
    rp = sub.add_parser('build-replay')
    rp.add_argument('--restored', required=True, help='as build-assets; adds replay.npz per world (train partition only)')
    i = sub.add_parser('install')
    for name in ('--home', '--tool', '--model'):
        i.add_argument(name, required=True)
    i.add_argument('--threads', type=int, default=4)
    i.add_argument('--backend-dir', help='runner library folder for builds with dynamically loaded ggml backends (b10964 release)')
    args = root.parse_args()
    if args.command == 'build-assets':
        build_assets(args)
        return 0
    if args.command == 'build-competence':
        build_competence(args)
        return 0
    if args.command == 'build-replay':
        build_replay(args)
        return 0
    return install(args)


if __name__ == '__main__':
    sys.exit(main())
