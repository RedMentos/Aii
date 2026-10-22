"""Isolated, inactive ToolForecast binding/publication candidate for Thread M review.

No monkeypatch, runtime registration or measured-cohort integration. Callers must
capture bindings BEFORE a new fit/forecast; legacy learn receipts are rejected,
never retroactively blessed. Tests use synthetic taps and prove lifecycle only.
"""
import copy
import json
import os
from pathlib import Path
import re
import shutil
import sys
import types
import uuid
from zipfile import BadZipFile

import numpy as np

from v13 import toolforecast as tf
from v13.common import atomic_write

SCHEMA = 'v13-toolforecast-binding-candidate-v1'
ARTIFACTS = ('checkpoint', 'metrics', 'competence', 'parity', 'replay')
PINNED_RUNTIME_SHA256 = 'be56e1e22d5ce0886d4c0db719fe92815838c4fc2074578aca0406f5f90e241d'


def load_encoder_safely(home, verify=True):
    """Damaged/partial configs remain unavailable instead of breaking status."""
    try:
        enc, reason = tf.load_encoder(home, verify=verify)
        if enc is None:
            return enc, reason
        required = ('tool_path', 'model_path', 'tool_sha256', 'model_sha256', 'layer', 'pooling')
        if any(name not in enc for name in required):
            return None, 'ENCODER_CONFIG_INVALID'
        if any(not isinstance(enc[name], str) or not enc[name] for name in required if name != 'layer'):
            return None, 'ENCODER_CONFIG_INVALID'
        if not isinstance(enc['layer'], int) or isinstance(enc['layer'], bool):
            return None, 'ENCODER_CONFIG_INVALID'
        return enc, reason
    except OSError:
        return None, 'ENCODER_CONFIG_UNREADABLE'
    except (ValueError, KeyError, TypeError, AttributeError):
        return None, 'ENCODER_CONFIG_INVALID'


def unlink_evicted_contexts(pending_dir, ids):
    """Only coordinator-owned forecast filenames, only after state commit."""
    failures = []
    for fid in ids:
        if not isinstance(fid, str) or re.fullmatch(r'tfc_[0-9a-f]{32}', fid) is None:
            failures.append({'id': str(fid), 'reason': 'INVALID_FORECAST_ID'})
            continue
        try:
            (Path(pending_dir) / (fid + '.npy')).unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            failures.append({'id': fid, 'reason': type(exc).__name__})
    return failures


def source_binding(ck):
    """Bind each used measured asset and current runtime/installer source bytes."""
    assets = {}
    for name in ARTIFACTS:
        declared = ck.entry.get(name + '_sha256')
        path = ck.entry.get(name)
        if path is not None:
            if declared is None or tf.sha_file(ck.root / path) != declared:
                raise ValueError('SOURCE_ASSET_CHANGED:' + name)
        elif declared is not None:
            raise ValueError('SOURCE_ASSET_MISSING:' + name)
        assets[name + '_sha256'] = declared
    return {'schema': SCHEMA, 'world': ck.world, 'actions': list(ck.actions), 'arm': ck.arm,
            'assets': assets, 'runtime_source_sha256': tf.sha_file(Path(tf.__file__)),
            'installer_source_sha256': tf.sha_file(tf.APP / 'scripts/install_tool_forecast.py'),
            'candidate_source_sha256': tf.sha_file(Path(__file__))}


def encoder_binding(enc, ck, *, verify_files=True):
    """Capture actual binaries plus capture coordinates; synthetic tests opt out of file checks."""
    if enc.get('schema') != tf.SCHEMA + '-encoder' or enc.get('parity', {}).get('status') != 'PASS':
        raise ValueError('ENCODER_NOT_PARITY_PASSED')
    want = json.loads(tf.MANIFEST.read_text())['encoder']
    if (enc.get('model_sha256') != ck.entry.get('model_sha256') or enc.get('model_sha256') != want['model_sha256']
            or enc.get('layer') != want['layer'] or enc.get('pooling') != want['pooling']):
        raise ValueError('ENCODER_NOT_CHECKPOINT_ENCODER')
    if verify_files:
        for name in ('tool', 'model'):
            if tf.sha_file(enc[name + '_path']) != enc[name + '_sha256']:
                raise ValueError('ENCODER_FILE_CHANGED:' + name)
    if not enc.get('tool_sha256'):
        raise ValueError('ENCODER_TOOL_ID_MISSING')
    return {k: enc.get(k) for k in ('tool_sha256', 'model_sha256', 'layer', 'pooling', 'capture_tool_sha256',
                                   'tool_source_sha256')} | {'transform': want['transform']}


def forecast_binding(ck, enc, *, verify_files=True):
    return source_binding(ck) | {'encoder': encoder_binding(enc, ck, verify_files=verify_files)}


def learning_binding(ck, enc, *, verify_files=True):
    bound = forecast_binding(ck, enc, verify_files=verify_files)
    ret = (enc.get('retention') or {}).get(ck.world)
    if not ret or tf.sha_file(ret['path']) != ret.get('sha256'):
        raise ValueError('RETENTION_REFERENCE_CHANGED')
    return bound | {'retention_sha256': ret['sha256'],
                    'learning_protocol': {'modes': list(tf.LEARN_MODES), 'retention_max': tf.RETENTION_MAX,
                                          'min_rows': tf.LEARN_MIN_ROWS, 'scales': list(tf.LEARN_SCALES),
                                          'weights': list(tf.LEARN_WEIGHTS)}}


def stamp_new_learning_report(report, before_binding, ck, enc, *, verify_files=True):
    """Stamp a NEW result only when its pre-fit snapshot still matches after fitting.

    This function deliberately does not write anything. Thread M must call it in
    the fitting transaction with the snapshot captured before the fit; it is not
    a migration utility for old passing receipts.
    """
    current = learning_binding(ck, enc, verify_files=verify_files)
    if before_binding != current:
        raise ValueError('LEARNING_BINDING_CHANGED_DURING_FIT')
    if (report.get('schema') != tf.SCHEMA + '-learn' or report.get('world') != ck.world
            or report.get('tool_sha256') != enc['tool_sha256']
            or report.get('pass') is not True or report.get('checkpoint_sha256') != ck.entry['checkpoint_sha256']
            or report.get('mode') not in tf.LEARN_MODES):
        raise ValueError('LEARNING_RECEIPT_NOT_PASSING')
    return copy.deepcopy(report) | {'binding': current}


def load_bound_adapted(home, ck, enc, *, verify_files=True):
    """Return verified weight/mode, else None; damaged/legacy receipts fail closed."""
    try:
        npz, js = tf.adapted_paths(home, ck.world)
        rep = json.loads(js.read_text())
        if (rep.get('schema') != tf.SCHEMA + '-learn' or rep.get('world') != ck.world
                or rep.get('tool_sha256') != enc['tool_sha256']
                or rep.get('pass') is not True or rep.get('mode') not in tf.LEARN_MODES
                or rep.get('checkpoint_sha256') != ck.entry['checkpoint_sha256']
                or rep.get('adapted_sha256') != tf.sha_file(npz)
                or rep.get('binding') != learning_binding(ck, enc, verify_files=verify_files)):
            return None
        with np.load(npz, allow_pickle=False) as z:
            weight = np.asarray(z['weight'], dtype=np.float64)
        if weight.shape != ck.weight.shape or not np.isfinite(weight).all():
            return None
        return {'weight': weight, 'mode': rep['mode']}
    except (OSError, ValueError, KeyError, TypeError, EOFError, BadZipFile):
        return None


def validate_pending_record(rec, ck, enc, *, verify_files=True):
    """Before outcome tapping/scoring: preserve source attribution across restart."""
    if rec.get('checkpoint_sha256') != ck.entry['checkpoint_sha256']:
        return False, 'CHECKPOINT_CHANGED_SINCE_FORECAST'
    try:
        if rec.get('binding') != forecast_binding(ck, enc, verify_files=verify_files):
            return False, 'FORECAST_BINDING_MISSING_OR_CHANGED'
    except (OSError, ValueError, KeyError, TypeError):
        return False, 'FORECAST_BINDING_UNAVAILABLE'
    return True, None


def validate_experience(exp, ck, enc):
    try:
        if json.loads(str(exp.get('binding', ''))) != forecast_binding(ck, enc):
            return 'EXPERIENCE_BINDING_MISSING_OR_CHANGED'
    except (OSError, ValueError, TypeError, KeyError):
        return 'EXPERIENCE_BINDING_MISSING_OR_CHANGED'
    return None


def bound_experience_add(experience, world, x, y, action_index, fid, x_mean=None, *, binding):
    """New buffers carry provenance; legacy or changed cohorts are never mixed."""
    old = experience.load(world)
    encoded = json.dumps(binding, sort_keys=True, separators=(',', ':'))
    new = {'x': np.asarray([x], np.float32), 'y': np.asarray([y], np.float32),
           'action': np.asarray([action_index], np.int64), 'id': np.asarray([fid]),
           'xm': np.asarray([x_mean if x_mean is not None else np.full(len(x), np.nan)], np.float32)}
    if old is not None:
        if str(old.get('binding', '')) != encoded:
            raise ValueError('EXPERIENCE_BINDING_MISSING_OR_CHANGED')
        if fid in set(old['id'].tolist()):
            return
        new = {k: np.concatenate([old[k], new[k]])[-tf.EXPERIENCE_MAX:] for k in new}
    tf.save_npz(experience.path(world), **new, binding=np.asarray(encoded))


def materialize_runtime(*, expected_sha256=PINNED_RUNTIME_SHA256):
    """Compile an isolated source-bound copy with actual lifecycle hooks.

    Never edits or replaces M's module, never registers with the live Runtime.
    Exact one-hit replacements fail when the pinned source changes. Relative
    imports resolve through v13; caller explicitly constructs this copy's class.
    Source/installer files remain byte unchanged and official measured gates are
    retained. Legacy raw buffers are refused rather than silently reclassified.
    """
    source = Path(tf.__file__)
    if tf.sha_file(source) != expected_sha256:
        raise ValueError('RUNTIME_SOURCE_NOT_PINNED')
    text = source.read_text()

    def replace(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError('PATCH_SITE_NOT_UNIQUE:' + old[:60])
        text = text.replace(old, new, 1)

    a = text.index('def load_encoder(home, verify=True):')
    b = text.index('\n\n_HASHED = {}', a)
    text = text[:a] + '''def load_encoder(home, verify=True):
    return _binding_candidate.load_encoder_safely(home, verify=verify)
''' + text[b:]

    a = text.index('    def add(self, world, x, y, action_index, fid, x_mean=None):')
    b = text.index('\n\ndef adapted_paths', a)
    text = text[:a] + '''    def add(self, world, x, y, action_index, fid, x_mean=None, *, binding):
        return _binding_candidate.bound_experience_add(self, world, x, y, action_index, fid, x_mean, binding=binding)
''' + text[b:]
    a = text.index('def load_adapted(home, ck):')
    b = text.index('\n\ndef learn(', a)
    text = text[:a] + '''def load_adapted(home, ck, enc):
    return _binding_candidate.load_bound_adapted(home, ck, enc)
''' + text[b:]
    replace("    report['experience_rows'] = int(len(exp['x']))", """    incompatible = _binding_candidate.validate_experience(exp, ck, enc)
    if incompatible:
        report['reason'] = incompatible
        return report
    before_binding = _binding_candidate.learning_binding(ck, enc)
    report['experience_rows'] = int(len(exp['x']))""")
    replace("    atomic_write(js, json.dumps(report, indent=1, sort_keys=True) + '\\n')",
            "    report = _binding_candidate.stamp_new_learning_report(report, before_binding, ck, enc)\n"
            "    atomic_write(js, json.dumps(report, indent=1, sort_keys=True) + '\\n')")
    replace('            t0 = time.monotonic()\n            if hasattr(taps,',
            '            forecast_snapshot = _binding_candidate.forecast_binding(ck, enc)\n'
            '            t0 = time.monotonic()\n            if hasattr(taps,')
    replace('            adapted = load_adapted(self.home, ck)', '            adapted = load_adapted(self.home, ck, enc)')
    replace("            fid = uid('tfc')", """            if forecast_snapshot != _binding_candidate.forecast_binding(ck, enc):
                raise ValueError('FORECAST_BINDING_CHANGED_DURING_TAP')
            fid = uid('tfc')""")
    replace("                   'checkpoint_sha256': ck.entry['checkpoint_sha256'], 'tool_sha256': enc['tool_sha256'],",
            "                   'checkpoint_sha256': ck.entry['checkpoint_sha256'], 'tool_sha256': enc['tool_sha256'],\n"
            "                   'binding': forecast_snapshot,")
    replace("            ck = self.checkpoint(rec['world'])\n            y = rms_normalize",
            """            ck = self.checkpoint(rec['world'])
            compatible, why = _binding_candidate.validate_pending_record(rec, ck, enc)
            if not compatible:
                return self._close(fid, rec, why, tx)
            y = rms_normalize""")
    replace("            y = rms_normalize(taps.tap([text])[0])\n            ref = y @ ck.p",
            """            y = rms_normalize(taps.tap([text])[0])
            compatible, why = _binding_candidate.validate_pending_record(rec, ck, enc)
            if not compatible:
                return self._close(fid, rec, why, tx)
            ref = y @ ck.p""")
    replace("                                          None if np.isnan(ctx[1]).any() else ctx[1])",
            "                                          None if np.isnan(ctx[1]).any() else ctx[1], binding=rec['binding'])")
    replace("""            def f(st):
                st['pending'][fid] = rec
                for k in sorted(st['pending'], key=lambda k: st['pending'][k]['created'])[:max(0, len(st['pending']) - PENDING_MAX)]:
                    del st['pending'][k]
                    self._count(st, 'EXPIRED_CAPACITY')
                self._count(st, 'FORECAST')
            self.box.mutate(f)""", """            def f(st):
                evicted = []
                st['pending'][fid] = rec
                for k in sorted(st['pending'], key=lambda k: st['pending'][k]['created'])[:max(0, len(st['pending']) - PENDING_MAX)]:
                    del st['pending'][k]
                    evicted.append(k)
                    self._count(st, 'EXPIRED_CAPACITY')
                self._count(st, 'FORECAST')
                return evicted
            evicted = self.box.mutate(f)
            cleanup_failures = _binding_candidate.unlink_evicted_contexts(self.pending_dir, evicted)
            if cleanup_failures:
                self.s.log('tool_forecast', event_id, {'status': 'CONTEXT_CLEANUP_FAILED', 'failures': cleanup_failures})""")
    module = types.ModuleType('v13._toolforecast_binding_candidate_runtime')
    module.__package__ = 'v13'
    module.__file__ = str(source)
    module.__dict__['_binding_candidate'] = sys.modules[__name__]
    exec(compile(text, str(source) + ':isolated-binding-candidate', 'exec'), module.__dict__)
    module.__dict__['_isolated_source_sha256'] = tf.sha_file(source)
    module.__dict__['_patched_source_sha256'] = __import__('hashlib').sha256(text.encode()).hexdigest()
    return module


def publish_verified_encoder(home, enc, *, before_assets, checkpoint_of, replace_pointer=atomic_write):
    """Publish a passing install without overwriting the last passing retention.

    `enc.retention` points to private, already staged files; never the current
    live generation. `before_assets` is {world: source_binding(ck)} captured
    BEFORE parity inference. This routine validates all bytes, seals a fresh
    immutable generation, then atomically changes the single encoder pointer.
    Failed parity makes zero writes. Crash before pointer commit leaves only
    an unreferenced generation; previous encoder + retention stay byte intact.
    The caller owns the existing coordinator lock; no inference runs here.
    """
    worlds = (enc.get('parity') or {}).get('worlds', {})
    retention = enc.get('retention') or {}
    if (enc.get('schema') != tf.SCHEMA + '-encoder' or enc.get('parity', {}).get('status') != 'PASS'
            or not retention or set(worlds) != set(retention)
            or set(before_assets) != set(retention) or not all(v.get('pass') is True for v in worlds.values())):
        return {'published': False, 'reason': 'PARITY_NOT_PASSED'}
    # Complete preflight before creating a generation or changing a pointer.
    sources = {}
    for world, ret in retention.items():
        ck = checkpoint_of(world)
        current = source_binding(ck)
        if before_assets[world] != current:
            raise ValueError('INSTALL_SOURCE_CHANGED_DURING_PARITY:' + world)
        encoder_binding(enc, ck)
        source = Path(ret['path'])
        if tf.sha_file(source) != ret['sha256']:
            raise ValueError('STAGED_RETENTION_CHANGED:' + world)
        sources[world] = source
    base = Path(home) / 'data/tool_forecast'
    generations = base / 'generations'
    generations.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    staging, final = generations / ('.staging-' + token), generations / token
    staging.mkdir()
    updated = copy.deepcopy(enc)
    try:
        for world, source in sources.items():
            filename = 'retention-' + world + '.npz'
            atomic_write(staging / filename, source.read_bytes())
            if tf.sha_file(staging / filename) != retention[world]['sha256']:
                raise ValueError('PUBLISHED_RETENTION_CHANGED:' + world)
            updated['retention'][world]['path'] = str((final / filename).resolve())
        updated['install_source_binding'] = before_assets
        os.replace(staging, final)
        # Durably seal the generation directory before publishing its pointer.
        for directory in (final, generations):
            fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        replace_pointer(base / 'encoder.json', json.dumps(updated, indent=1, sort_keys=True, allow_nan=False) + '\n')
        return {'published': True, 'generation': token}
    finally:
        if staging.exists():
            shutil.rmtree(staging)
