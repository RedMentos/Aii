"""Read-only ToolForecast lifecycle audit; synthetic taps, no model invocation."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import numpy as np

HERE = Path(__file__).resolve()
REPO = next((p for p in HERE.parents if (p / 'v13/code/v13/toolforecast.py').is_file()), HERE.parent.parent / 'Aii')
APP = REPO / 'v13/code'
sys.path[:0] = [str(APP), str(APP / 'scripts')]
from v13 import toolforecast as F
import install_tool_forecast as installer


class Store:
    def __init__(self):
        self.values = {}
        self.logs = []

    def state(self, key, default):
        return copy.deepcopy(self.values.get(key, (default, None)))

    def set_state(self, key, value, expected=None):
        old = self.values.get(key, (None, None))[1]
        assert old == expected
        self.values[key] = (copy.deepcopy(value), (old or 0) + 1)

    def log(self, kind, event, payload):
        self.logs.append([kind, event, payload])


def changed_gate_reuses_old_adaptation():
    """Use actual v2 reference; simulate v1 by omitting the added mean test."""
    manifest = json.loads(F.MANIFEST.read_text())
    ck2 = F.Checkpoint('calc_counter', manifest['worlds']['calc_counter'])
    ck1 = copy.copy(ck2)
    ck1.reference = {k: v for k, v in ck2.reference.items() if k not in ('taps_mean', 'threshold_mean')}
    x = min(ck1.reference['taps'][:20], key=lambda x: ck1.competence(x)['distance'])
    xm = F.rms_normalize(np.random.default_rng(41).normal(size=ck2.width))
    assert ck1.competence(x, xm)['in_domain']
    assert not ck2.competence(x, xm)['in_domain']
    with tempfile.TemporaryDirectory() as d:
        npz, js = F.adapted_paths(d, ck1.world)
        F.save_npz(npz, weight=ck1.weight + .01)
        report = {'pass': True, 'checkpoint_sha256': ck1.entry['checkpoint_sha256'],
                  'adapted_sha256': F.sha_file(npz), 'tool_sha256': 'PRIOR-DEVICE-ENCODER', 'mode': 'region'}
        js.write_text(json.dumps(report))
        accepted = F.load_adapted(d, ck2)
        assert accepted is not None
        # Current predict's exact activation condition, formerly false and now true.
        before = not ck1.competence(x, xm)['in_domain']
        after = not ck2.competence(x, xm)['in_domain']
        return {'old_gate_in_domain': not before, 'v2_gate_in_domain': not after,
                'old_adaptation_accepted_after_gate_change': accepted is not None,
                'adaptation_activated_on_unvalidated_region': after,
                'receipt_bound_keys': sorted(report)}


def failed_reinstall_breaks_last_passing_retention():
    manifest = json.loads(F.MANIFEST.read_text())
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        model, tool = home / 'dummy-model', home / 'dummy-tool'
        model.write_bytes(b'no inference model')
        tool.write_bytes(b'no inference tool')
        manifest['encoder']['model_sha256'] = F.sha_file(model)
        mp = home / 'manifest.json'
        mp.write_text(json.dumps(manifest))
        data = home / 'data/tool_forecast'
        data.mkdir(parents=True)
        retention = {}
        for world in manifest['worlds']:
            p = data / ('retention-%s.npz' % world)
            F.save_npz(p, texts=np.asarray(['last passing retention']), taps=np.ones((1, 1024), dtype=np.float32))
            retention[world] = {'path': str(p), 'sha256': F.sha_file(p)}
        enc = {'schema': F.SCHEMA + '-encoder', 'parity': {'status': 'PASS'}, 'retention': retention,
               'tool_path': str(tool), 'tool_sha256': F.sha_file(tool), 'model_path': str(model),
               'model_sha256': F.sha_file(model), 'layer': 11, 'pooling': 'last'}
        ep = data / 'encoder.json'
        ep.write_text(json.dumps(enc))
        before = ep.read_bytes()

        class Taps:
            def __init__(self, *args, **kwargs):
                pass

            def tap_both(self, texts):
                a = np.ones((len(texts), 1024), dtype=np.float32)
                return a, a

        # Scores deliberately fail; native tap method replaced, no executable is run.
        bad_scores = lambda ck, *args: {a: {'forecast': 2., 'copy': 1., 'mean_delta': 1., 'rows': 1} for a in ck.actions}
        with patch.object(F, 'MANIFEST', mp), patch.object(F, 'NativeLayerTaps', Taps), patch.object(installer, 'scores', bad_scores):
            rc = installer.install(argparse.Namespace(home=home, model=model, tool=tool, threads=1, backend_dir=None))
        active, why = F.load_encoder(home)
        changed = {w: F.sha_file(v['path']) != v['sha256'] for w, v in retention.items()}
        assert rc == 1 and ep.read_bytes() == before and active is not None and all(changed.values())
        return {'installer_exit': rc, 'old_encoder_json_byte_unchanged': ep.read_bytes() == before,
                'old_encoder_still_accepted': active is not None, 'retention_hash_mismatch': changed}


def pending_scores_across_checkpoint_change():
    manifest = json.loads(F.MANIFEST.read_text())
    ck = F.Checkpoint('calc_counter', manifest['worlds']['calc_counter'])
    class Taps:
        def tap(self, texts):
            return np.stack([np.random.default_rng(int(hashlib.sha256(t.encode()).hexdigest()[:10], 16)).normal(size=ck.width) for t in texts])
    with tempfile.TemporaryDirectory() as d:
        store, taps = Store(), Taps()
        before = F.ToolForecast(store, d, taps=taps)
        before.set_mode('SHADOW')
        pred = before.predict('calc', {'expression': '37*2'}, 'event')
        assert pred is not None
        # A replacement measured checkpoint has the same width but a changed projection/identity.
        # Injecting this exact object isolates observe's missing snapshot-identity guard.
        after_ck = copy.copy(ck)
        after_ck.entry = dict(ck.entry, checkpoint_sha256='NEW-CHECKPOINT-IDENTITY')
        after_ck.p = ck.p * 2
        restart = F.ToolForecast(store, d, taps=taps)
        restart._checkpoints['calc_counter'] = after_ck
        tx = {'predicted': pred, 'status': 'EXECUTED', 'result': 74, 'event_id': 'event', 'id': 'tx'}
        got = restart.observe(tx)
        assert got['status'] == 'SCORED'
        return {'pending_checkpoint': pred['checkpoint_sha256'], 'current_checkpoint': after_ck.entry['checkpoint_sha256'],
                'status_despite_changed_checkpoint_projection': got['status'],
                'experience_rows_in_new_checkpoint_world': len(F.Experience(d).load(ck.world)['x'])}


def corrupted_install_breaks_status():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'data/tool_forecast/encoder.json'
        p.parent.mkdir(parents=True)
        p.write_text('{')
        tf = F.ToolForecast(Store(), d)
        try:
            tf.report()
        except Exception as e:
            assert type(e).__name__ == 'JSONDecodeError'
            return {'status_raises': type(e).__name__}
        raise AssertionError('unexpected successful report')


def expired_context_files_accumulate():
    manifest = json.loads(F.MANIFEST.read_text())
    ck = F.Checkpoint('calc_counter', manifest['worlds']['calc_counter'])
    class Taps:
        def tap(self, texts):
            return np.ones((len(texts), ck.width))
    with tempfile.TemporaryDirectory() as d:
        tf = F.ToolForecast(Store(), d, taps=Taps())
        tf.set_mode('SHADOW')
        for i in range(F.PENDING_MAX + 2):
            assert tf.predict('calc', {'expression': '37*2'}, str(i)) is not None
        pending = len(tf.box.load()[0]['pending'])
        files = len(list(tf.pending_dir.glob('*.npy')))
        assert pending == F.PENDING_MAX and files == F.PENDING_MAX + 2
        return {'pending_state_rows': pending, 'context_files': files, 'orphan_files': files - pending}


if __name__ == '__main__':
    out = {'evidence': 'SYNTHETIC_NO_INFERENCE', 'source_sha256': F.sha_file(APP / 'v13/toolforecast.py'),
           'installer_sha256': F.sha_file(APP / 'scripts/install_tool_forecast.py'),
           'findings': {'stale_adaptation': changed_gate_reuses_old_adaptation(),
                        'failed_reinstall': failed_reinstall_breaks_last_passing_retention(),
                        'pending_checkpoint_change': pending_scores_across_checkpoint_change(),
                        'corrupt_status': corrupted_install_breaks_status(),
                        'orphan_pending_files': expired_context_files_accumulate()}}
    target = Path(__file__).with_name('result.json')
    target.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out, indent=2))
