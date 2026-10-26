#!/usr/bin/env python3
"""Run471: read-only exact B3 bridge identity candidate, NOT production authority.

Existing BodyPort.bridge_valid checks revisions only; that is insufficient for
IH-H21 if a model SHA, tokenizer, dimensions or capabilities change under the
same revision. Legacy manifests have no exact bridge keys and fail closed here.
This candidate does not rewrite a manifest or enable B3 L1/latent messages.
"""
import argparse
import json
import re
import stat
import zipfile
from pathlib import Path

DIRECTIONS = {'B1_TO_B2': ('B1_DETAIL', 'B2_GIST'),
              'B2_TO_B1': ('B2_GIST', 'B1_DETAIL')}
HEX = re.compile(r'[a-f0-9]{64}\Z')
REQUIRED_SPEC = ('model_id', 'revision', 'sha256', 'dims', 'tokenizer', 'capabilities')


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def exact_identity(manifest, specs):
    """Fail closed on missing exact serving identity; does not grant authority."""
    from v13.bodyport import bridge_key
    require(type(manifest) is dict and type(specs) is dict, 'BRIDGE_INPUT_NOT_OBJECT')
    direction = manifest.get('direction')
    require(type(direction) is str and direction in DIRECTIONS, 'BRIDGE_DIRECTION_INVALID')
    sender, receiver = DIRECTIONS[direction]
    require(set(specs) == {sender, receiver}, 'BRIDGE_SERVING_ROLES_INVALID')
    for role, side in ((sender, 'sender'), (receiver, 'receiver')):
        spec = specs[role]
        require(type(spec) is dict and all(k in spec for k in REQUIRED_SPEC),
                'BRIDGE_SPEC_INCOMPLETE:' + role)
        require(type(spec['model_id']) is str and bool(spec['model_id']) and
                type(spec['revision']) is str and bool(spec['revision']) and
                type(spec['sha256']) is str and HEX.fullmatch(spec['sha256']) and
                type(spec['dims']) is int and spec['dims'] > 0 and
                type(spec['tokenizer']) is str and bool(spec['tokenizer']) and
                type(spec['capabilities']) in (list, tuple) and
                bool(spec['capabilities']) and
                all(type(x) is str and bool(x) for x in spec['capabilities']) and
                len(set(spec['capabilities'])) == len(spec['capabilities']),
                'BRIDGE_SPEC_NOT_EXACT:' + role)
        require(manifest.get(side + '_revision') == spec['revision'],
                'BRIDGE_REVISION_CHANGED:' + side)
        stored = manifest.get(side + '_bridge_key')
        require(type(stored) is str and HEX.fullmatch(stored),
                'BRIDGE_EXACT_KEY_MISSING:' + side)
        require(stored == bridge_key(role, spec),
                'BRIDGE_EXACT_KEY_MISMATCH:' + side)
    require(type(manifest.get('sha256')) is str and HEX.fullmatch(manifest['sha256']),
            'BRIDGE_WEIGHTS_DIGEST_MISSING')
    return {'direction': direction, 'sender_role': sender, 'receiver_role': receiver,
            'sender_bridge_key': manifest['sender_bridge_key'],
            'receiver_bridge_key': manifest['receiver_bridge_key'],
            'bridge_weights_sha256': manifest['sha256'],
            'identity_compatible': True, 'latent_authority': 0,
            'canonical_gate_pass': False, 'b3_l1': 'FAIL',
            'claim_limit': 'Exact identity only; no native receiver utility, L1 calibration/retention, or activation.'}


def verify_file(path, specs):
    """Read-only local artifact proof; no hostile-concurrent-rename guarantee."""
    from v13.b3bridge import Bridge
    path = Path(path)
    if path.suffix in ('.json', '.npz'):
        path = path.with_suffix('')
    manpath, weightpath = path.with_suffix('.json'), path.with_suffix('.npz')
    for item in (manpath, weightpath):
        require(item.is_file() and not item.is_symlink(), 'BRIDGE_FILE_MISSING_OR_SYMLINK')
        info = item.stat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                'BRIDGE_FILE_HARDLINK_OR_NONREGULAR')
    manifest = json.loads(manpath.read_bytes())
    result = exact_identity(manifest, specs)
    require(path.name == manifest['direction'], 'BRIDGE_PATH_DIRECTION_MISMATCH')
    sender, receiver = DIRECTIONS[manifest['direction']]
    bridge = Bridge.load(path, specs[sender]['revision'], specs[receiver]['revision'])
    # An attacker can re-key an arbitrary serving spec and re-sign the manifest
    # while retaining an incompatible NPZ. Keys and digests alone do not prove
    # that the loaded tensor geometry can consume the claimed sender tap.
    require(bridge.d == specs[sender]['dims'],
            'BRIDGE_SENDER_DIM_MISMATCH')
    expected = {
        'Q': (bridge.K, bridge.d), 'P': (bridge.d, bridge.r),
        'Pr': (bridge.K * bridge.r, bridge.h),
        'gamma': (1,), 'Wu': (bridge.h, bridge.classes),
    }
    if bridge.aux:
        expected['Wa'] = (bridge.h, bridge.aux)
    for key, shape in expected.items():
        require(key in bridge.p and bridge.p[key].shape == shape,
                'BRIDGE_TENSOR_SHAPE_MISMATCH:' + key)
    require(bridge.in_mu.shape == (bridge.d,) and
            bridge.in_sd.shape == (bridge.d,),
            'BRIDGE_INPUT_NORM_SHAPE_MISMATCH')
    if bridge.head is not None:
        require(bridge.head[0].shape == (bridge.h, bridge.classes) and
                bridge.head[1].shape == (bridge.classes,),
                'BRIDGE_HEAD_SHAPE_MISMATCH')
    if bridge.cal is not None:
        require(bridge.cal['mu'].shape == (bridge.K * bridge.r,) and
                bridge.cal['sd'].shape == (bridge.K * bridge.r,),
                'BRIDGE_CAL_SHAPE_MISMATCH')
    require(bridge.digest() == result['bridge_weights_sha256'],
            'BRIDGE_WEIGHTS_NOT_ATTESTED')
    require((manifest.get('calibrated') is True) == (bridge.cal is not None),
            'BRIDGE_CALIBRATION_FLAG_MISMATCH')
    result.update(run='Run471', status='RUN471_EXACT_BRIDGE_IDENTITY_NO_AUTHORITY',
                  calibrated=bridge.cal is not None,
                  l1_verdict=(manifest.get('l1_gate') or {}).get('verdict'),
                  native_execution_performed=False, redmi_measured=False,
                  jepa_weight=0)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bridge', type=Path, required=True)
    p.add_argument('--serving-specs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    try:
        result = verify_file(a.bridge, json.loads(a.serving_specs.read_bytes()))
        rc = 0
    except (OSError, ValueError, TypeError, KeyError, IndexError,
            json.JSONDecodeError, zipfile.BadZipFile, EOFError) as exc:
        result = {'run': 'Run471', 'status': 'RUN471_BRIDGE_IDENTITY_RED',
                  'errors': [type(exc).__name__ + ': ' + str(exc)[:300]],
                  'identity_compatible': False, 'latent_authority': 0,
                  'canonical_gate_pass': False, 'b3_l1': 'FAIL',
                  'redmi_measured': False, 'jepa_weight': 0}
        rc = 2
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'latent_authority': 0,
                      'canonical_gate_pass': False, 'b3_l1': 'FAIL'}))
    raise SystemExit(rc)


if __name__ == '__main__':
    main()
