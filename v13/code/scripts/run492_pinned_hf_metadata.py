#!/usr/bin/env python3
"""Run492: fail-closed primary-source pinned HF model metadata preflight.

Metadata only: no model bytes, no license acceptance, no native/model inference.
"""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request

SPECS = {
    'B1_DETAIL': {
        'repo': 'LiquidAI/LFM2.5-1.2B-Instruct-GGUF',
        'revision': '6767265158422fb8a19c62ceb45f16f05363615b',
        'file': 'LFM2.5-1.2B-Instruct-QAD-Q4_0.gguf',
        'size': 695755488,
        'sha256': 'bb741ebb106d543e9de114b843a3d3d73d51c74b5801e69da2abde821a0cb3e1',
        'license': 'lfm1.0',
    },
    'B2_GIST': {
        'repo': 'ggml-org/Qwen3.5-0.8B-GGUF',
        'revision': '8fea620810c4afa23dd6443f999a48574c1611a3',
        'file': 'Qwen3.5-0.8B-Q4_0.gguf',
        'size': 563036064,
        'sha256': '57d1997790d1744fba5b40a7317df71ea5e2acee28c47e78f0cce39c0703f8cf',
        'license': 'apache-2.0',
    },
    'C3_LANGUAGE': {
        'repo': 'LiquidAI/LFM2.5-350M-GGUF',
        'revision': '657e078c94084481950a2d555a941481f715536b',
        'file': 'LFM2.5-350M-QAD-Q4_0.gguf',
        'size': 219312832,
        'sha256': '3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d',
        'license': 'lfm1.0',
    },
}


def require(ok, why):
    if not ok:
        raise ValueError(why)


def api_url(spec):
    require(len(spec['revision']) == 40 and
            all(c in '0123456789abcdef' for c in spec['revision']),
            'REVISION_NOT_PINNED')
    return ('https://huggingface.co/api/models/' +
            urllib.parse.quote(spec['repo'], safe='/') +
            '/revision/' + spec['revision'] + '?blobs=true')


def verify_model(role, payload, response_sha256):
    require(role in SPECS and type(payload) is dict, 'MODEL_METADATA_SCHEMA')
    spec = SPECS[role]
    require(payload.get('id') == spec['repo'] and
            payload.get('sha') == spec['revision'], 'MODEL_REPO_OR_REVISION_CHANGED')
    require(payload.get('private') is False and
            payload.get('gated') in (False, None), 'MODEL_NOT_PUBLIC_UNGATED')
    card = payload.get('cardData') or {}
    require(type(card) is dict, 'LICENSE_CARD_SCHEMA')
    card_license = str(card.get('license') or '').lower()
    tags = payload.get('tags') or []
    require(type(tags) is list, 'LICENSE_TAG_SCHEMA')
    tagged = [str(t).lower().removeprefix('license:') for t in tags
              if str(t).lower().startswith('license:')]
    licenses = {card_license, *tagged}
    require(spec['license'] in licenses, 'MODEL_LICENSE_METADATA_CHANGED')
    siblings = payload.get('siblings')
    require(type(siblings) is list, 'MODEL_SIBLINGS_MISSING')
    matches = [f for f in siblings if type(f) is dict and f.get('rfilename') == spec['file']]
    require(len(matches) == 1, 'PINNED_MODEL_FILENAME_MISSING_OR_DUPLICATE')
    entry = matches[0]
    lfs = entry.get('lfs')
    require(type(lfs) is dict, 'MODEL_LFS_SHA256_UNAVAILABLE')
    sha = lfs.get('sha256') or str(lfs.get('oid') or '').removeprefix('sha256:')
    size = lfs.get('size') if lfs.get('size') is not None else entry.get('size')
    require(type(sha) is str and sha == spec['sha256'], 'PINNED_MODEL_LFS_SHA256_CHANGED')
    require(type(size) is int and size == spec['size'], 'PINNED_MODEL_SIZE_CHANGED')
    require(type(response_sha256) is str and len(response_sha256) == 64,
            'API_RESPONSE_SHA256_MISSING')
    return {'role': role, 'repo': spec['repo'], 'revision': spec['revision'],
            'filename': spec['file'], 'sha256': sha, 'size': size,
            'license_metadata': spec['license'], 'license_accepted_by_user': None,
            'source': api_url(spec), 'api_response_sha256': response_sha256,
            'status': 'PUBLIC_PINNED_LFS_METADATA_MATCH'}


def fetch_model(spec):
    request = urllib.request.Request(
        api_url(spec),
        headers={'Accept': 'application/json',
                 'User-Agent': 'V13-Run492-Public-Model-Metadata-Preflight/1.0'})
    with urllib.request.urlopen(request, timeout=40) as response:
        require(response.status == 200, 'MODEL_METADATA_HTTP_NOT_200')
        raw = response.read(4_000_001)
    require(len(raw) <= 4_000_000, 'MODEL_METADATA_RESPONSE_TOO_LARGE')
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def audit(fetcher=fetch_model):
    out = {}
    for role, spec in SPECS.items():
        payload, response_sha256 = fetcher(spec)
        out[role] = verify_model(role, payload, response_sha256)
    require(set(out) == set(SPECS), 'MODEL_PREFLIGHT_INCOMPLETE')
    return {'schema': 'V13_RUN492_PINNED_PUBLIC_MODEL_METADATA_V1',
            'status': 'PINNED_PUBLIC_MODEL_METADATA_VERIFIED',
            'models': out, 'model_bytes_downloaded': 0,
            'native_executed': False, 'runner_verified': False,
            'license_accepted_by_user': None,
            'canonical_gate_pass': False, 'step2_exit': 'UTILITY_FAIL',
            'b3_l1': 'FAIL', 'body_jepa': 'UNAVAILABLE',
            'jepa_weight': 0, 'redmi_measured': False,
            'claim_limit': 'Pinned public API LFS metadata only; not a model-byte SHA or license acceptance or native/Redmi proof.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'REFUSE_OVERWRITE_PREVIOUS_MODEL_PREFLIGHT')
    result = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': result['status'], 'models': sorted(result['models']),
                      'model_bytes_downloaded': 0, 'native_executed': False}))


if __name__ == '__main__':
    main()
