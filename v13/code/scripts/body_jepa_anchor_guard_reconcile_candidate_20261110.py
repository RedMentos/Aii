"""Reconcile two reviewed Body-JEPA lineages only in a disposable copy.

Input: exact #1663 source. Base: exact #1641 source, #1646 token boundary,
#1643 fail-atomic optimizer/EMA. Add #1662's per-anchor metrics while retaining
#1641's scalar anchor_retention_kl API. Original frozen files stay untouched.
"""
import hashlib
import json
from pathlib import Path
import tempfile


PINS = {
    'v13/body_jepa.py': 'c050037928bc6e4b89fbeddea54fc358e8c418688bdb32e1e32630bc3b2b707c',
    'v13/lora_trainer.py': '6383f957060116d3750f5c266cc83bac414fc9d6136eac0c4cd4317fbbb9f3f4',
    'v13/body_jepa_checkpoint.py': '0e8dbb0ec83acc5aa00d6a049e7571b2561e831caf7a7f7817ad2b476290f3f0',
    'v13/common.py': '0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a',
    'v13/agi/trainers.py': '67a4ff83cf536ddd2171b0262d1b03b73a72c5adac120456c269e06f95b2dc98',
    'v13/body_jepa_atomic_step_candidate.py': 'ef584ec96d7930ee6216f162e62069b57d6a8b5b75b399cf10d699c1a22e75c4',
    'tests/test_body_anchor_retention.py': '6a14792d70affe32911ef99b7446caee87986af280481509a1538694426836ae',
    'tests/test_body_jepa_checkpoint_fit.py': 'eb7a51ff43d8d6aaeda943a64fd6c1a8a6110bce0e6a91d0ae56d0f6420f5080',
}
MANIFEST_SHA = 'b98d80d30ff38d69760f7e7e689e2ca0bb70f684de2c1fcbba737c2546695c03'
SOURCE_1646_SHA = 'df2629ac13e9951a737f4baacff5786ada8d4b56d435a5a50475b56472cd041f'
ASSET_DIR = Path(__file__).resolve().parents[1] / 'candidates/body_anchor_guard_20261110'

PAD_OLD = b'''            or any(type(token) is not int or token < 0 for s in seqs for token in s)
            or type(pad_id) is not int or pad_id < 0):
'''
PAD_NEW = b'''            or any(type(token) is not int or not 0 <= token <= (1 << 63) - 1 for s in seqs for token in s)
            or type(pad_id) is not int or not 0 <= pad_id <= (1 << 63) - 1):
'''
FN_HEADER = b'def anchor_retention_kl(torch, model, anchor_seqs, anchor_logp):'
FN_VALUES = b'def anchor_retention_values(torch, model, anchor_seqs, anchor_logp):'
WRAPPER = b'''\n\ndef anchor_retention_kl(torch, model, anchor_seqs, anchor_logp):
    """Compatibility: rounded mean KL from the #1641 scalar contract."""
    values = anchor_retention_values(torch, model, anchor_seqs, anchor_logp)
    return round(sum(values) / len(values), 8) if values else None
'''
FINAL_OLD = b'        final_anchor_kl = anchor_retention_kl(torch, model, anchor_seqs, anchor_logp)\n'
FINAL_NEW = b'''        retention_kl = anchor_retention_values(torch, model, anchor_seqs, anchor_logp)
        final_anchor_kl = round(sum(retention_kl)/len(retention_kl),8) if retention_kl else None
'''
METRICS_OLD = b"'final_anchor_kl':final_anchor_kl,'retention_probe_count':len(anchor_seqs),"
METRICS_NEW = b"""'final_anchor_kl':final_anchor_kl,'retention_probe_count':len(anchor_seqs),
                 'retention_anchor_count':len(retention_kl),'retention_anchor_kl_mean':round(sum(retention_kl)/len(retention_kl),7) if retention_kl else None,
                 'retention_anchor_kl_max':round(max(retention_kl),7) if retention_kl else None,"""
TEST_OLD = b'from v13.body_jepa import anchor_retention_kl\n'
TEST_NEW = b'from v13.body_jepa import anchor_retention_values as anchor_retention_kl\n'


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _replace_once(data, old, new, label):
    if data.count(old) != 1:
        raise ValueError('ambiguous reconciliation anchor: ' + label)
    return data.replace(old, new, 1)


def _assets():
    manifest_raw = (ASSET_DIR / 'manifest.json').read_bytes()
    if _hash(manifest_raw) != MANIFEST_SHA:
        raise ValueError('body asset manifest hash mismatch')
    manifest = json.loads(manifest_raw)
    if manifest.get('schema') != 'v13-body-anchor-guard-assets-v1':
        raise ValueError('unsupported body asset manifest')
    values = {}
    for name, record in manifest['entries'].items():
        path = (ASSET_DIR / name).resolve()
        if not path.is_relative_to(ASSET_DIR.resolve()):
            raise ValueError('invalid body asset path')
        data = path.read_bytes()
        if _hash(data) != record['sha256']:
            raise ValueError('body asset hash mismatch: ' + name)
        values[name] = data
    return values


def build_sources(code_dir):
    """Return overlaid sources/tests after exact upstream and asset checks."""
    code_dir = Path(code_dir)
    originals = {}
    for path, expected in PINS.items():
        data = (code_dir / path).read_bytes()
        if _hash(data) != expected:
            raise ValueError('unsupported integrated Body-JEPA source: ' + path)
        originals[path] = data
    assets = _assets()
    base = assets['body_jepa_1641.py.txt']
    token_guarded = _replace_once(base, PAD_OLD, PAD_NEW, 'token range')
    if _hash(token_guarded) != SOURCE_1646_SHA:
        raise ValueError('unexpected #1646 token-range source')
    namespace = {'__name__': '_reviewed_atomic_builder'}
    exec(compile(assets['atomic_builder_1643.py.txt'], '<pinned-1643-builder>', 'exec'), namespace)
    with tempfile.TemporaryDirectory(prefix='v13-body-source-reconcile-') as home:
        source = Path(home) / 'body_jepa.py'
        source.write_bytes(base)
        body = namespace['build_sources'](source.parent)['body_jepa.py']
    body = _replace_once(body, PAD_OLD, PAD_NEW, 'atomic token range')
    start = body.index(FN_HEADER)
    end = body.index(b'\n\n# -- trainer', start)
    fn = body[start:end]
    fn = _replace_once(fn, FN_HEADER, FN_VALUES, 'retention function')
    fn = _replace_once(fn, b'    if not anchor_seqs:\n        return None\n',
                       b'    if not anchor_seqs:\n        return []\n', 'empty anchors')
    fn = _replace_once(fn, b'    return round(sum(values) / len(values), 8)\n',
                       b'    return values\n', 'per-anchor values')
    body = body[:start] + fn + WRAPPER + body[end:]
    body = _replace_once(body, FINAL_OLD, FINAL_NEW, 'retention measurement')
    body = _replace_once(body, METRICS_OLD, METRICS_NEW, 'retention metrics')
    # #1663 introduced a list-returning function under the old scalar name.
    # Update its own test to use the explicitly named values API; leave #1641's
    # scalar compatibility API and tests unchanged.
    anchor_test = _replace_once(originals['tests/test_body_anchor_retention.py'],
                                TEST_OLD, TEST_NEW, 'new retention API')
    result = {'v13/body_jepa.py': body,
              'tests/test_body_anchor_retention.py': anchor_test}
    for name, data in assets.items():
        if name.startswith('tests/') and name.endswith('.py.txt'):
            result[name[:-4]] = data
    return result
