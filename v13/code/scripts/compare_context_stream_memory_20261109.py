"""Synthetic tracemalloc comparison. Select source tree with PYTHONPATH."""
import hashlib
import json
import sys
import tempfile
import time
import tracemalloc
import zlib
from pathlib import Path

variant = sys.argv[1]
assert variant in ('1650', '1651')
source_bytes = 64 * 1024 * 1024
chunk = b'A' * (1024 * 1024)
hasher = hashlib.sha256()
compressor = zlib.compressobj(9)
with tempfile.TemporaryDirectory(prefix='v13-stream-comparison-') as name:
    root = Path(name)
    zpath = root / 'sample.z'
    with zpath.open('wb') as output:
        for _ in range(64):
            hasher.update(chunk)
            output.write(compressor.compress(chunk))
        output.write(compressor.flush())
    key = hasher.hexdigest()
    compressed_bytes = zpath.stat().st_size
    if variant == '1650':
        from v13.source_slice import verified_source_slice
        tracemalloc.start()
        result = verified_source_slice(zpath, key, 0, 8, compressed=True)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    else:
        from v13.runtime import Runtime
        from v13.archive_stream_range_candidate import read_span
        runtime = Runtime(root / 'runtime')
        runtime.sleep.cycle.set_policy('enabled', 'off')
        try:
            zpath.rename(runtime.home / 'data/blobs' / (key + '.z'))
            sid = 'src_synthetic_stream_comparison'
            with runtime.store.tx() as conn:
                conn.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,0)',
                             (sid, key, 'USER', source_bytes, source_bytes, time.time()))
            ref = {'source_id': sid, 'sha256': key, 'char_start': 0, 'char_end': 8, 'modality': 'text'}
            tracemalloc.start()
            result = read_span(runtime.store, ref)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        finally:
            runtime.close()
    assert result == 'A' * 8
    print(json.dumps({'variant': variant, 'source_bytes': source_bytes, 'compressed_bytes': compressed_bytes,
                      'returned_chars': len(result), 'traced_peak_bytes': peak}, sort_keys=True))
