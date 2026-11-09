"""Build the openat-based Body-port diagnostic in a disposable copy only."""
import hashlib
from pathlib import Path


HASHES={'verification.py':'3f22d0e09f79b23f4f71f0743cfeab87b0c03e90042297ac8a1cd0f776ebc908',
        'body_training.py':'08ec4a996048026b8e2a6d81c8ca9cd6c56f9a8159caecce7483ddb24504f9ff'}
OLD=b'from .body_training import inspect_train_port\n'
NEW=b'from .body_port_openat_candidate import inspect_train_port\n'


def build_sources(source_dir):
    source_dir=Path(source_dir)
    sources={}
    for name,sha in HASHES.items():
        raw=(source_dir/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('unsupported Body port source: '+name)
        sources[name]=raw
    if sources['verification.py'].count(OLD)!=1:
        raise ValueError('ambiguous Body port diagnostic import')
    return {'verification.py':sources['verification.py'].replace(OLD,NEW,1)}
