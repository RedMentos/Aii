"""Tool-consequence forecast in the live tool path (IH-H29 `predicted`, §7.2, §13; Action-JEPA rounds 7/8). SHADOW only.

Rounds 7 and 8 confirmed (24/24 each, preregistered) one narrow claim: a fixed per-action mean delta plus a closed-form
ridge residual on frozen native Qwen3.5-0.8B `l_out-11` last-token taps predicts the tap of the observed outcome text of
real `calc` / `sandbox_note` calls better than all controls. This module puts that measured candidate into the live
ToolRegistry path without giving it any authority:

  before the effect   a live call that maps onto a confirmed world (calc counter: N*2, N+15, N/4, N-7; sandbox note
                      edits: append " Done.", prefix "Urgent: ", uppercase) gets a forecast. The pre-state text is
                      tapped natively, the bound checkpoint predicts the outcome latent; the forecast (with both
                      controls, copy and mean delta) is persisted and its id goes into the call's IH-H29 `predicted`
                      field, so it is committed with the action transaction before the effect.
  after the effect    the outcome text is rebuilt from the tool's own result (calc) or the note file read back (note),
                      tapped with the same encoder and scored: squared error of the forecast vs. copy and mean-delta
                      controls in the checkpoint's fixed projection. Aggregates per world/action, telemetry
                      `tool_forecast`.

Nothing reads the forecast to decide anything: no gate, no wake, no answer text, no learning step. Calls that do not
map onto a confirmed world, or a missing/unverified encoder, are recorded as such and never get a made-up prediction.
The encoder is the rebuilt tap tool + GGUF named in `<home>/data/tool_forecast/encoder.json`, written only by
`scripts/install_tool_forecast.py` after a parity check against taps stored with the checkpoint.
Mode OFF (default; every forecast costs a native prefill subprocess) or SHADOW (`:toolforecast shadow`).
"""
import hashlib
import json
import math
import re
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np

from .agi.base import StateBox
from .common import APP, dumps, uid

SCHEMA = 'v13-tool-forecast-v1'
KEY = 'TOOL_FORECAST'
REVISION = 1
OBJECTIVE = 'mean-delta-ridge-residual-shadow-v1'   # scripts/action_jepa_round6_ridge.py
MANIFEST = APP / 'specs' / 'tool-forecast.json'
PENDING_MAX = 64      # open forecasts kept (oldest dropped as EXPIRED_CAPACITY)
HISTORY = 200         # scored forecasts kept with their vectors
TAP_TIMEOUT_S = 120.

# Worlds exactly as the rounds that confirmed them wrote state and outcome texts (round 5 v2 / round 8 templates).
CALC_ACTIONS = {'double': (r'([1-9]\d{0,5})\*2', 'After doubling, the counter shows {n}.'),
                'add_15': (r'([1-9]\d{0,5})\+15', 'After adding 15, the counter shows {n}.'),
                'quarter': (r'([1-9]\d{0,5})/4', 'After dividing by 4, the counter shows {n}.'),
                'subtract_7': (r'([1-9]\d{0,5})-7', 'After subtracting 7, the counter shows {n}.')}
CALC_STATE = 'The counter shows {n}.'
CALC_RANGE = (1, 999)  # start values the round-7 world drew from
NOTE_STATE = 'The note reads: {c}'
NOTE_OUTCOME = {'append_done': 'After appending, the note reads: {c}', 'prefix_urgent': 'After adding a prefix, the note reads: {c}',
                'uppercase': 'After uppercasing, the note reads: {c}'}
# Round-8 note vocabulary (10 verbs x 10 objects x 6 times); live notes outside it are out of the measured world.
VERBS = ('call', 'email', 'visit', 'pay', 'thank', 'meet', 'ask', 'remind', 'help', 'invite')
OBJECTS = ('the plumber', 'the bank', 'the dentist', 'grandma', 'the landlord', 'the school', 'the neighbour',
           'the doctor', 'the team', 'the library')
WHEN = ('today', 'tomorrow', 'on Monday', 'on Friday', 'next week', 'this evening')
NOTE_WORLD = frozenset(f'{v.capitalize()} {o} {w}.' for v in VERBS for o in OBJECTS for w in WHEN)
NOTE_EDIT = {'append_done': lambda c: c + ' Done.', 'prefix_urgent': lambda c: 'Urgent: ' + c, 'uppercase': lambda c: c.upper()}


def sha_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def vec_sha(v):
    return hashlib.sha256(np.asarray(v, dtype='<f8').tobytes()).hexdigest()


def rms_normalize(x):
    """Same transform as action_jepa_objective.load_dataset: float32 tap / RMS, then float64."""
    x = np.asarray(x, dtype=np.float32)
    return (x / np.maximum(np.sqrt(np.mean(x * x, axis=-1, keepdims=True)), 1e-8)).astype(np.float64)


def note_text(home, name):
    """Current content of a sandbox note, or None (same path rule as transaction.sandbox_note_tool)."""
    from .transaction import NAME
    if not isinstance(name, str) or not NAME.match(name):
        return None
    p = Path(home) / 'data' / 'tool_sandbox' / (name + '.txt')
    return p.read_text() if p.exists() else None


def classify(tool, args, home):
    """Map a live call onto a confirmed world: {'world','action','state_text',...} or {'unmapped': reason}."""
    if tool == 'calc':
        expr = str((args or {}).get('expression', ''))
        for action, (pattern, _) in CALC_ACTIONS.items():
            m = re.fullmatch(pattern, expr)
            if m:
                n = int(m.group(1))
                return {'world': 'calc_counter', 'action': action, 'state_text': CALC_STATE.format(n=n), 'value': n,
                        'in_world_range': CALC_RANGE[0] <= n <= CALC_RANGE[1]}
        return {'unmapped': 'CALC_EXPRESSION_NOT_IN_WORLD'}
    if tool == 'sandbox_note':
        name, text = (args or {}).get('name'), (args or {}).get('text')
        old = note_text(home, name)
        if old is None or not isinstance(text, str):
            return {'unmapped': 'NOTE_NOT_AN_EDIT_OF_EXISTING_NOTE'}
        if '\n' in old or '\n' in text or not old.strip():
            return {'unmapped': 'NOTE_NOT_SINGLE_LINE'}
        for action, edit in NOTE_EDIT.items():
            if text == edit(old) and text != old:
                return {'world': 'note_edit', 'action': action, 'state_text': NOTE_STATE.format(c=old), 'name': name,
                        'in_world_range': old in NOTE_WORLD}
        return {'unmapped': 'NOTE_EDIT_NOT_IN_WORLD'}
    return {'unmapped': 'TOOL_WITHOUT_WORLD'}


def outcome_text(world, action, tx, home):
    """Outcome text from the effect itself (tool result / note read back), never from a model."""
    if world == 'calc_counter':
        if tx.get('result') is None:
            return None, 'NO_RESULT'
        return CALC_ACTIONS[action][1].format(n=tx['result']), None
    if world == 'note_edit':
        content = note_text(home, (tx.get('args') or {}).get('name'))
        if content is None:
            return None, 'NOTE_MISSING_AFTER_EFFECT'
        if content != (tx.get('args') or {}).get('text'):
            return None, 'NOTE_CHANGED_AFTER_EFFECT'   # someone else wrote it; not the observed outcome of this call
        return NOTE_OUTCOME[action].format(c=content), None
    return None, 'UNKNOWN_WORLD'


class Checkpoint:
    """Measured round-7/8 candidate, loaded only when bytes, report and encoder identity match the manifest."""
    def __init__(self, world, entry, root=APP):
        self.world = world
        self.entry = entry
        ck, mt = root / entry['checkpoint'], root / entry['metrics']
        if sha_file(ck) != entry['checkpoint_sha256'] or sha_file(mt) != entry['metrics_sha256']:
            raise ValueError(world + ': checkpoint/metrics bytes differ from manifest')
        report = json.loads(mt.read_text())
        if report.get('checkpoint_sha256') != entry['checkpoint_sha256'] or report.get('candidate_gate_pass') is not True:
            raise ValueError(world + ': measured report does not bind a passing candidate')
        with np.load(ck, allow_pickle=False) as z:
            meta = json.loads(str(z['metadata']))
            self.p, self.mean_delta, self.centre, self.weight = (np.asarray(z[k], dtype=np.float64) for k in
                                                                 ('projector', 'mean_delta', 'centre', 'weight'))
        if meta['schema'] != OBJECTIVE or meta['config']['arm'] != entry['arm'] or meta['actions'] != entry['actions']:
            raise ValueError(world + ': objective/arm/actions differ from manifest')
        self.actions = meta['actions']
        self.arm = meta['config']['arm']
        self.width = self.p.shape[0]

    def predict(self, x, action):
        """Same formula as round6 predict_state for one row: x@p + mean_delta[a] + (f - centre[a]) @ W[a]."""
        j = self.actions.index(action)
        f = x if self.arm == 'full' else x @ self.p
        return {'forecast': x @ self.p + self.mean_delta[j] + (f - self.centre[j]) @ self.weight[j],
                'copy': x @ self.p, 'mean_delta': x @ self.p + self.mean_delta[j]}


class NativeLayerTaps:
    """scripts/native_layer_taps.cpp as a subprocess: one read-only prefill per text, l_out-<layer> last/mean token."""
    def __init__(self, enc, threads=4, timeout_s=TAP_TIMEOUT_S):
        self.enc = enc
        self.threads = threads
        self.timeout_s = timeout_s

    def tap(self, texts):
        layer, pooling = int(self.enc['layer']), self.enc['pooling']
        if any('\n' in t or not t for t in texts):
            raise ValueError('Tap texts must be non-empty single lines')
        with tempfile.TemporaryDirectory(prefix='v13-tap-') as d:
            d = Path(d)
            (d / 'in.txt').write_text(''.join(t + '\n' for t in texts))
            proc = subprocess.run([self.enc['tool_path'], self.enc['model_path'], str(layer), str(d / 'in.txt'), str(d / 'out'),
                                   str(self.threads)], capture_output=True, timeout=self.timeout_s)
            if proc.returncode != 0:
                raise RuntimeError('native tap tool exit %d' % proc.returncode)
            meta = json.loads((d / 'out.json').read_text())
            raw = np.fromfile(d / 'out.bin', dtype=np.float32)
        n = meta['n_embd']
        if meta['texts'] != len(texts) or meta['layers'] != [layer] or raw.size != len(texts) * 2 * n or not np.isfinite(raw).all():
            raise RuntimeError('native tap output shape mismatch')
        return raw.reshape(len(texts), 2, n)[:, 0 if pooling == 'last' else 1]


def load_encoder(home, verify=True):
    """encoder.json from install_tool_forecast.py; file hashes are re-checked once per (path, size, mtime)."""
    p = Path(home) / 'data' / 'tool_forecast' / 'encoder.json'
    if not p.exists():
        return None, 'NO_ENCODER_INSTALLED'
    enc = json.loads(p.read_text())
    if enc.get('schema') != SCHEMA + '-encoder' or enc.get('parity', {}).get('status') != 'PASS':
        return None, 'ENCODER_PARITY_NOT_PASSED'
    if verify:
        for k in ('tool', 'model'):
            path = Path(enc[k + '_path'])
            if not path.exists():
                return None, 'ENCODER_FILE_MISSING'
            st = path.stat()
            cache_key = (str(path), st.st_size, st.st_mtime_ns)
            if _HASHED.get(cache_key) is None:
                _HASHED[cache_key] = sha_file(path)
            if _HASHED[cache_key] != enc[k + '_sha256']:
                return None, 'ENCODER_FILE_CHANGED'
    return enc, None


_HASHED = {}


class ToolForecast:
    def __init__(self, store, home, taps=None, manifest=MANIFEST, root=APP, clock=time.time):
        self.s = store
        self.home = Path(home)
        self.clock = clock
        self.box = StateBox(store, KEY, REVISION, lambda: {'mode': 'OFF', 'pending': {}, 'scored': [], 'stats': {}, 'counts': {}})
        self.manifest = json.loads(Path(manifest).read_text())
        self.root = Path(root)
        self._taps = taps          # injectable for tests; else built from encoder.json
        self._checkpoints = {}

    # -- configuration ------------------------------------------------------------------------------------------
    def mode(self):
        return self.box.load()[0]['mode']

    def set_mode(self, mode):
        if mode not in ('OFF', 'SHADOW'):
            raise ValueError('Modus OFF|SHADOW (keine Autorität: ACTIVE gibt es nicht)')
        self.box.mutate(lambda st: st.update(mode=mode))
        return mode

    def checkpoint(self, world):
        if world not in self._checkpoints:
            self._checkpoints[world] = Checkpoint(world, self.manifest['worlds'][world], self.root)
        return self._checkpoints[world]

    def encoder(self, world):
        """(tap provider, encoder record) or (None, reason). Encoder must match the checkpoint's capture encoder."""
        enc, why = load_encoder(self.home) if self._taps is None else ({'model_sha256': self.manifest['encoder']['model_sha256'],
                                                                          'layer': self.manifest['encoder']['layer'],
                                                                          'pooling': self.manifest['encoder']['pooling'],
                                                                          'tool_sha256': 'INJECTED'}, None)
        if enc is None:
            return None, why
        want = self.manifest['encoder']
        if enc['model_sha256'] != want['model_sha256'] or int(enc['layer']) != want['layer'] or enc['pooling'] != want['pooling']:
            return None, 'ENCODER_NOT_CHECKPOINT_ENCODER'
        return (self._taps or NativeLayerTaps(enc)), enc

    def _count(self, st, k):
        st['counts'][k] = st['counts'].get(k, 0) + 1

    def _note(self, event_id, status, extra=None):
        self.box.mutate(lambda st: self._count(st, status))
        self.s.log('tool_forecast', event_id, {'status': status} | (extra or {}))

    # -- before the effect --------------------------------------------------------------------------------------
    def predict(self, tool, args, event_id=None):
        """IH-H29 `predicted` value for a call, or None (OFF / not in a confirmed world / no encoder). Never raises."""
        try:
            if self.mode() != 'SHADOW':
                return None
            c = classify(tool, args, self.home)
            if 'unmapped' in c:
                self._note(event_id, c['unmapped'], {'tool': tool})
                return None
            ck = self.checkpoint(c['world'])
            taps, enc = self.encoder(c['world'])
            if taps is None:
                self._note(event_id, enc, {'tool': tool, 'world': c['world']})
                return None
            t0 = time.monotonic()
            x = rms_normalize(taps.tap([c['state_text']])[0])
            if x.shape != (ck.width,):
                raise ValueError('tap width differs from checkpoint')
            out = ck.predict(x, c['action'])
            fid = uid('tfc')
            rec = {'id': fid, 'world': c['world'], 'action': c['action'], 'tool': tool, 'event_id': event_id, 'created': self.clock(),
                   'state_text': c['state_text'], 'in_world_range': c.get('in_world_range', True),
                   'checkpoint_sha256': ck.entry['checkpoint_sha256'], 'tool_sha256': enc['tool_sha256'],
                   'tap_s': round(time.monotonic() - t0, 3)} | {k: [float(v) for v in out[k]] for k in ('forecast', 'copy', 'mean_delta')}

            def f(st):
                st['pending'][fid] = rec
                for k in sorted(st['pending'], key=lambda k: st['pending'][k]['created'])[:max(0, len(st['pending']) - PENDING_MAX)]:
                    del st['pending'][k]
                    self._count(st, 'EXPIRED_CAPACITY')
                self._count(st, 'FORECAST')
            self.box.mutate(f)
            self.s.log('tool_forecast', event_id, {'status': 'FORECAST', 'world': c['world'], 'action': c['action'], 'tap_s': rec['tap_s']})
            return {'schema': SCHEMA, 'forecast_id': fid, 'world': c['world'], 'action': c['action'], 'latent_dim': len(rec['forecast']),
                    'forecast_sha256': vec_sha(out['forecast']), 'checkpoint_sha256': rec['checkpoint_sha256'],
                    'encoder': {'model_sha256': enc['model_sha256'], 'layer': enc['layer'], 'pooling': enc['pooling']},
                    'authority': 'LOCAL_PREDICTION_HYPOTHESIS', 'future_observed': False, 'used_for_decision': False}
        except Exception as exc:
            try:
                self._note(event_id, 'FORECAST_FAILED', {'tool': tool, 'error': type(exc).__name__})
            except Exception:
                pass
            return None

    # -- after the effect ---------------------------------------------------------------------------------------
    def observe(self, tx):
        """Score a forecast against the observed outcome of its call. Idempotent per forecast; never raises."""
        pred = tx.get('predicted')
        if not is_forecast(pred) or tx.get('status') != 'EXECUTED':   # a deduplicated call had no new effect
            return None
        fid = pred['forecast_id']
        try:
            st = self.box.load()[0]
            rec = st['pending'].get(fid)
            if rec is None:
                return None   # already scored, expired or from another store
            text, why = outcome_text(rec['world'], rec['action'], tx, self.home)
            if text is None:
                return self._close(fid, rec, why, tx)
            taps, enc = self.encoder(rec['world'])
            if taps is None:
                return None   # stays pending; `:toolforecast score` retries once an encoder is installed
            if enc['tool_sha256'] != rec['tool_sha256']:
                return self._close(fid, rec, 'ENCODER_CHANGED_SINCE_FORECAST', tx)
            ck = self.checkpoint(rec['world'])
            y = rms_normalize(taps.tap([text])[0])
            ref = y @ ck.p
            err = {k: float(np.mean((np.asarray(rec[k]) - ref) ** 2)) for k in ('forecast', 'copy', 'mean_delta')}
            return self._close(fid, rec, 'SCORED', tx, text=text, err=err)
        except Exception as exc:
            self._note(tx.get('event_id'), 'OBSERVE_FAILED', {'error': type(exc).__name__})
            return None

    def _close(self, fid, rec, status, tx, text=None, err=None):
        done = {'id': fid, 'world': rec['world'], 'action': rec['action'], 'status': status, 'tool_call': tx.get('id'),
                'action_tx': tx.get('action_tx'), 'in_world_range': rec['in_world_range'], 'scored_at': self.clock()}
        if err is not None:
            best = min(err['copy'], err['mean_delta'])
            done |= {'outcome_text': text, 'mse': {k: round(v, 8) for k, v in err.items()},
                     'ratio_to_best_control': round(err['forecast'] / best, 6) if best > 0 else None,
                     'beats_controls': err['forecast'] < best}

        def f(st):
            if fid not in st['pending']:
                return False
            del st['pending'][fid]
            st['scored'] = (st['scored'] + [done])[-HISTORY:]
            self._count(st, status)
            if err is not None:
                key = rec['world'] + ':' + rec['action']
                a = st['stats'].setdefault(key, {'n': 0, 'wins': 0, 'sum_log_ratio': 0., 'in_range': 0})
                a['n'] += 1
                a['wins'] += int(done['beats_controls'])
                a['in_range'] += int(rec['in_world_range'])
                if done['ratio_to_best_control']:
                    a['sum_log_ratio'] += math.log(done['ratio_to_best_control'])
            return True
        if self.box.mutate(f):
            self.s.log('tool_forecast', tx.get('event_id'), {'status': status, 'world': rec['world'], 'action': rec['action']}
                       | ({'ratio': done['ratio_to_best_control'], 'beats_controls': done['beats_controls']} if err else {}))
            return done
        return None

    def score_pending(self, calls):
        """Retry pending forecasts whose calls already executed (e.g. after an encoder install or restart)."""
        by_fid = {c['predicted']['forecast_id']: c for c in calls if is_forecast(c.get('predicted'))}
        out = []
        for fid in list(self.box.load()[0]['pending']):
            if fid in by_fid:
                r = self.observe(by_fid[fid])
                if r:
                    out.append(r)
        return out

    def report(self):
        st = self.box.load()[0]
        stats = {k: v | {'win_rate': round(v['wins'] / v['n'], 4),
                         'geo_mean_ratio_to_best_control': round(math.exp(v['sum_log_ratio'] / v['n']), 4)} for k, v in st['stats'].items() if v['n']}
        enc, why = load_encoder(self.home, verify=False) if self._taps is None else ({'tool_sha256': 'INJECTED'}, None)
        return {'schema': SCHEMA, 'mode': st['mode'], 'encoder': (enc or {}).get('tool_sha256') and 'INSTALLED' or why,
                'worlds': {w: {'actions': e['actions'], 'source': e['source']} for w, e in self.manifest['worlds'].items()},
                'pending': len(st['pending']), 'counts': st['counts'], 'stats': stats, 'recent': st['scored'][-5:],
                'claim_limit': 'SHADOW measurement of a narrow candidate (closed worlds of rounds 7/8); no gate, answer, wake or learning '
                               'reads it. Live calls outside those worlds get no forecast. Redmi latency/RSS unmeasured.'}


def is_forecast(pred):
    return isinstance(pred, dict) and pred.get('schema') == SCHEMA and isinstance(pred.get('forecast_id'), str)


def for_runtime(r):
    tf = getattr(r, 'tool_forecast', None)
    if tf is None:
        tf = r.tool_forecast = ToolForecast(r.store, r.home)
    return tf


def operator_command(r, args):
    """:toolforecast [status|shadow|off|score]"""
    tf = for_runtime(r)
    if not args or args == ['status']:
        return dumps(tf.report())
    if args == ['shadow']:
        return dumps({'mode': tf.set_mode('SHADOW')})
    if args == ['off']:
        return dumps({'mode': tf.set_mode('OFF')})
    if args == ['score']:
        from .agi import hub
        return dumps({'scored': tf.score_pending(hub(r).tools.box.load()[0]['calls'])})
    raise ValueError(':toolforecast [status|shadow|off|score]')
