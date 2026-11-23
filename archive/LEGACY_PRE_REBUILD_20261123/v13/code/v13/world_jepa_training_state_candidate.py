"""Numeric-only World-JEPA optimizer/inverse/RNG state for the staged Runtime.

Preserves successive fit calls, including their bootstrap schedule. This is not
an assertion that differently partitioned fit calls have identical semantics.
"""
import hashlib
import io
import json
import math
import os
import stat
import zipfile

import numpy as np

from . import world_jepa as wj

SCHEMA = 'v13.world-jepa.training-state.v1'
PREFIX = 'training__'
MAX_STEPS = 10**9


def objective(seed, ensemble):
    value = [SCHEMA, wj.REVISION, seed, ensemble, wj.H, wj.Z, wj.HP,
             wj.LR, wj.TAU, wj.VAR_W, wj.COV_W, wj.INV_W, wj.BATCH]
    return hashlib.sha256(json.dumps(value, allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def _rng(value):
    if (type(value) is not dict or set(value) != {'bit_generator', 'state', 'has_uint32', 'uinteger'}
            or value['bit_generator'] != 'PCG64' or type(value['state']) is not dict
            or set(value['state']) != {'state', 'inc'}
            or any(type(value['state'][k]) is not int or not 0 <= value['state'][k] < 2**128
                   for k in ('state', 'inc')) or value['state']['inc'] % 2 != 1
            or type(value['has_uint32']) is not int or value['has_uint32'] not in (0, 1)
            or type(value['uinteger']) is not int or not 0 <= value['uinteger'] < 2**32):
        raise ValueError('invalid World-JEPA training RNG')
    return {'bit_generator': 'PCG64', 'state': dict(value['state']),
            'has_uint32': value['has_uint32'], 'uinteger': value['uinteger']}


def _shapes(d, actions):
    enc = {'W1': (wj.H, d), 'b1': (wj.H,), 'W2': (wj.Z, wj.H), 'b2': (wj.Z,)}
    pred = {'P1': (wj.HP, wj.Z + actions), 'c1': (wj.HP,),
            'P2': (wj.Z, wj.HP), 'c2': (wj.Z,)}
    inverse = {'Q1': (wj.HP, 2 * wj.Z), 'd1': (wj.HP,),
               'Q2': (actions, wj.HP), 'd2': (actions,)}
    main = {prefix + key: shape for prefix, group in (('e', enc), ('p', pred), ('i', inverse))
            for key, shape in group.items()}
    return main, pred, inverse


def _arrays(values, shapes, nonnegative=False):
    if type(values) is not dict or set(values) != set(shapes):
        raise ValueError('invalid World-JEPA optimizer parameter layout')
    result = {}
    for key, shape in shapes.items():
        value = values[key]
        if (type(value) is not np.ndarray or value.dtype != np.dtype('float64')
                or value.shape != shape or not np.isfinite(value).all()
                or (nonnegative and np.any(value < 0))):
            raise ValueError('invalid World-JEPA optimizer tensor: ' + key)
        result[key] = np.array(value, copy=True, order='C', subok=False)
    return result


def _adam(value, shapes, upper, exact=None):
    if (type(value) is not dict or set(value) != {'t', 'lr', 'm', 'v'}
            or type(value['t']) is not int or not 0 <= value['t'] <= upper
            or (exact is not None and value['t'] != exact)
            or type(value['lr']) is not float or value['lr'] != wj.LR):
        raise ValueError('invalid World-JEPA optimizer step/config')
    result = {'t': value['t'], 'lr': value['lr'],
              'm': _arrays(value['m'], shapes), 'v': _arrays(value['v'], shapes, True)}
    if result['t'] == 0 and any(np.any(a) for group in ('m', 'v') for a in result[group].values()):
        raise ValueError('zero-step World-JEPA optimizer has nonzero moments')
    return result


def validate(state, d, actions, seed, ensemble, steps):
    if (type(d) is not int or not 1 <= d <= 4096 or type(actions) is not int or not 1 <= actions <= 64
            or type(seed) is not int or not 0 <= seed <= 2**63 - 1
            or type(ensemble) is not int or not 1 <= ensemble <= 16
            or type(steps) is not int or not 0 <= steps <= MAX_STEPS):
        raise ValueError('invalid World-JEPA training dimensions')
    if (type(state) is not dict or set(state) != {'schema', 'objective', 'inverse', 'main', 'rng', 'bootstrap'}
            or state['schema'] != SCHEMA or state['objective'] != objective(seed, ensemble)
            or type(state['bootstrap']) is not list or len(state['bootstrap']) != ensemble - 1):
        raise ValueError('missing or incompatible World-JEPA training state')
    main, pred, inverse = _shapes(d, actions)
    result = {'schema': SCHEMA, 'objective': state['objective'],
              'inverse': _arrays(state['inverse'], inverse),
              'main': _adam(state['main'], main, steps, exact=steps),
              'rng': _rng(state['rng']), 'bootstrap': []}
    for member in state['bootstrap']:
        if type(member) is not dict or set(member) != {'adam', 'rng'}:
            raise ValueError('invalid World-JEPA bootstrap state')
        result['bootstrap'].append({'adam': _adam(member['adam'], pred, steps // 2),
                                    'rng': _rng(member['rng'])})
    return result


def from_model(model):
    return validate(getattr(model, '_training_state', None), len(model.mu), len(model._action_counts),
                    model.seed, model.ensemble, model._fit_steps)


def snapshot(adam):
    if type(adam) is not wj.Adam:
        raise ValueError('reviewed World-JEPA Adam required')
    return {'t': adam.t, 'lr': adam.lr,
            'm': {k: v.copy() for k, v in adam.m.items()},
            'v': {k: v.copy() for k, v in adam.v.items()}}


def restore_adam(adam, state):
    checked = _adam(state, {k: v.shape for k, v in adam.p.items()}, MAX_STEPS)
    adam.t, adam.lr, adam.m, adam.v = checked['t'], checked['lr'], checked['m'], checked['v']


def capture(opt, inverse, rng, bootstrap, d, actions, seed, ensemble, steps):
    return validate({'schema': SCHEMA, 'objective': objective(seed, ensemble), 'main': snapshot(opt),
                     'inverse': inverse, 'rng': rng.bit_generator.state, 'bootstrap': bootstrap},
                    d, actions, seed, ensemble, steps)


def pack(model):
    state = from_model(model)
    arrays = {}
    def adam(value, name):
        for group in ('m', 'v'):
            for key, array in value[group].items():
                arrays[PREFIX + name + '__' + group + '__' + key] = array
        return {'t': value['t'], 'lr': value['lr']}
    for key, array in state['inverse'].items():
        arrays[PREFIX + 'inverse__' + key] = array
    meta = {'schema': SCHEMA, 'objective': state['objective'], 'rng': state['rng'],
            'main': adam(state['main'], 'main'), 'bootstrap': []}
    for i, value in enumerate(state['bootstrap']):
        meta['bootstrap'].append({'adam': adam(value['adam'], 'boot' + str(i)), 'rng': value['rng']})
    return meta, arrays


def unpack(meta, arrays, base_meta, base_arrays):
    if (type(base_meta.get('fit_steps')) is not int or not 1 <= base_meta['fit_steps'] <= MAX_STEPS
            or type(meta) is not dict or set(meta) != {'schema', 'objective', 'rng', 'main', 'bootstrap'}
            or type(meta['bootstrap']) is not list or len(meta['bootstrap']) != base_meta['ensemble'] - 1):
        raise ValueError('invalid World-JEPA training metadata')
    main, pred, inverse = _shapes(len(base_arrays['mu']), len(base_arrays['action_counts']))
    expected = set()
    def get(name):
        name = PREFIX + name; expected.add(name)
        if name not in arrays:
            raise ValueError('missing World-JEPA optimizer tensor')
        return arrays[name]
    def adam(value, name, shapes):
        if type(value) is not dict or set(value) != {'t', 'lr'}:
            raise ValueError('invalid World-JEPA optimizer metadata')
        return dict(value, **{group: {key: get(name + '__' + group + '__' + key) for key in shapes}
                              for group in ('m', 'v')})
    state = {'schema': meta['schema'], 'objective': meta['objective'], 'rng': meta['rng'],
             'inverse': {key: get('inverse__' + key) for key in inverse},
             'main': adam(meta['main'], 'main', main), 'bootstrap': []}
    for i, member in enumerate(meta['bootstrap']):
        if type(member) is not dict or set(member) != {'adam', 'rng'}:
            raise ValueError('invalid World-JEPA bootstrap metadata')
        state['bootstrap'].append({'adam': adam(member['adam'], 'boot' + str(i), pred), 'rng': member['rng']})
    if set(arrays) != expected:
        raise ValueError('unexpected World-JEPA optimizer tensors')
    return validate(state, len(base_arrays['mu']), len(base_arrays['action_counts']),
                    base_meta['seed'], base_meta['ensemble'], base_meta['fit_steps'])


def validate_payload(meta, arrays, source_meta, model_arrays):
    return unpack(meta, arrays, source_meta, model_arrays)


def read_checkpoint(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= limit:
            raise ValueError('unsafe or oversized World-JEPA checkpoint')
        chunks, size = [], 0
        while True:
            chunk = os.read(fd, min(65536, limit - size + 1))
            if not chunk:
                break
            chunks.append(chunk); size += len(chunk)
            if size > limit:
                raise ValueError('World-JEPA checkpoint grew beyond limit')
        current = os.fstat(fd); named = os.stat(path, follow_symlinks=False)
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if size != info.st_size or identity(info) != identity(current) or identity(current) != identity(named):
            raise ValueError('World-JEPA checkpoint changed while reading')
        return b''.join(chunks)
    finally:
        os.close(fd)


def validate_archive(raw):
    # Check declared NPY allocation sizes against actual members before np.load.
    # ZIP size limits alone do not constrain a malicious NPY shape header.
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for member in archive.infolist():
            with archive.open(member) as source:
                version = np.lib.format.read_magic(source)
                if version not in ((1, 0), (2, 0)):
                    raise ValueError('unsupported World-JEPA tensor encoding')
                header = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                          else np.lib.format.read_array_header_2_0)
                shape, _, dtype = header(source, max_header_size=4096)
                if (len(shape) > 2 or any(type(n) is not int or n < 0 for n in shape)
                        or dtype not in (np.dtype('float64'), np.dtype('int64'), np.dtype('uint8'))
                        or source.tell() + math.prod(shape) * dtype.itemsize != member.file_size):
                    raise ValueError('World-JEPA tensor header exceeds actual payload')
