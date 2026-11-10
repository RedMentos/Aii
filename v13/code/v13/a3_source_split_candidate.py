"""Experimental three-way source-group partition for A3, not a runtime gate.

All spans belonging to identical full-source content stay together, even if
stored under different source IDs. Metadata only; raw text is not returned.
The caller must revalidate source/deletion and its own authorization at use.
"""
import copy
import hashlib
import json

SPLITS = ('train', 'validation', 'test')
REVISION = 'a3-source-split-v1'


def _bucket(source_hash):
    value = hashlib.sha256((REVISION + ':' + source_hash).encode('ascii')).digest()
    x = int.from_bytes(value[:8], 'big') % 10
    if x < 2:
        return 'test'
    # On the remaining sources, reproduce student_worker.split's existing
    # validation convention. That allows test sources to stay outside its input.
    worker_hash = hashlib.sha256(source_hash.encode('ascii')).digest()
    return 'validation' if int.from_bytes(worker_hash[:4], 'big') % 4 == 0 else 'train'


def partition(store, source_refs, minimum_groups=(20, 6, 6)):
    """Validate local source refs; assign whole source groups 60/20/20.

    ``minimum_groups`` rejects undersized splits, not an efficacy gate.
    Identical raw full-source hashes form one group. Near duplicates and
    paraphrases from different sources are not detected. The explicit `test`
    partition must be reserved from checkpoint selection by the caller.
    """
    if not isinstance(source_refs, (list, tuple)) or not 1 <= len(source_refs) <= 4096:
        raise ValueError('A3 source refs required')
    if (not isinstance(minimum_groups, (list, tuple)) or len(minimum_groups) != 3
            or any(type(v) is not int or v < 0 for v in minimum_groups)):
        raise ValueError('Invalid split minimums')
    source_refs = copy.deepcopy(source_refs)
    minimum_groups = tuple(minimum_groups)
    parts = {name: [] for name in SPLITS}
    groups = {name: set() for name in SPLITS}
    snapshot_refs = []
    seen_spans = set()
    seen_slice_hashes = set()
    for index, original in enumerate(source_refs):
        if type(original) is not dict:
            raise ValueError('Invalid source reference')
        ref = copy.deepcopy(original)
        source_hash, source_id = ref.get('sha256'), ref.get('source_id')
        start, end = ref.get('char_start'), ref.get('char_end')
        if (not isinstance(source_hash, str) or len(source_hash) != 64
                or any(c not in '0123456789abcdef' for c in source_hash)
                or not isinstance(source_id, str) or not source_id
                or type(start) is not int or type(end) is not int or not 0 <= start < end
                or ref.get('modality') != 'text'):
            raise ValueError('Invalid text source reference')
        text = store.read_source(copy.deepcopy(ref))
        if not isinstance(text, str) or not text or len(text) != end - start:
            raise ValueError('Invalid or empty source slice')
        span_key = (source_hash, start, end)
        if span_key in seen_spans:
            raise ValueError('Duplicate source span')
        seen_spans.add(span_key)
        slice_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        if slice_hash in seen_slice_hashes:
            raise ValueError('Duplicate source slice content')
        seen_slice_hashes.add(slice_hash)
        name = _bucket(source_hash)
        parts[name].append(index)
        groups[name].add(source_hash)
        snapshot_refs.append({'source_id': source_id, 'sha256': source_hash,
                              'char_start': start, 'char_end': end, 'modality': 'text'})
    for name, minimum in zip(SPLITS, minimum_groups):
        if len(groups[name]) < minimum:
            raise ValueError('Insufficient distinct sources for ' + name)
    payload = json.dumps(snapshot_refs, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    result = {'revision': REVISION, 'split_indices': parts,
              'source_group_counts': {name: len(groups[name]) for name in SPLITS},
              'minimum_groups': list(minimum_groups),
              'source_ref_snapshot_sha256': hashlib.sha256(payload).hexdigest(),
              'source_refs': snapshot_refs, 'claim': 'SOURCE_GROUP_SPLIT_ONLY_NO_PROMOTION'}
    manifest = json.dumps(result, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    result['manifest_sha256'] = hashlib.sha256(manifest).hexdigest()
    return result


def worker_indices(manifest):
    """Map non-test rows to the existing A3 worker's train/validation split.

    This is a planning adapter; it does not call or modify the worker, and the
    consumer must use only these returned non-test rows for any fitting.
    The current worker accepts only one row per full-source hash.
    """
    from .student_worker import split
    if type(manifest) is not dict:
        raise ValueError('Invalid partition manifest')
    clean = {k: v for k, v in manifest.items() if k != 'manifest_sha256'}
    encoded = json.dumps(clean, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')
    if hashlib.sha256(encoded).hexdigest() != manifest.get('manifest_sha256'):
        raise ValueError('Partition manifest changed')
    if manifest.get('revision') != REVISION:
        raise ValueError('Partition revision changed')
    refs, parts = manifest['source_refs'], manifest['split_indices']
    non_test = sorted(parts['train'] + parts['validation'])
    all_ids = non_test + parts['test']
    if sorted(all_ids) != list(range(len(refs))):
        raise ValueError('Invalid partition coverage')
    groups = [refs[i]['sha256'] for i in non_test]
    if len(set(groups)) != len(groups):
        raise ValueError('Current A3 worker requires one row per full source')
    train, valid = split(groups)
    if ({non_test[i] for i in train} != set(parts['train']) or
            {non_test[i] for i in valid} != set(parts['validation'])):
        raise ValueError('Worker train/validation partition mismatch')
    return {'worker_source_indices': non_test, 'worker_train_indices': train.tolist(),
            'worker_validation_indices': valid.tolist(),
            'reserved_test_source_indices': list(parts['test']),
            'partition_manifest_sha256': manifest['manifest_sha256']}
