"""Negative tests for atomic generation member integrity (software-only)."""
import os
import pytest
from v13 import world_jepa_generation as generation
from v13.world_jepa_replay import ReplaySession


def test_mismatched_model_hash_never_publishes(tmp_path, monkeypatch):
    def dishonest_save(model, path, source):
        path.write_bytes(b'changed-model')
        return {'sha256': generation._sha(b'other-model')}
    monkeypatch.setattr(generation.checkpoint, 'save', dishonest_save)
    dest = tmp_path / 'new-generation'
    with pytest.raises(ValueError, match='model checkpoint bytes/hash mismatch'):
        generation.save(object(), ReplaySession('a' * 64), dest)
    assert not dest.exists()
    assert not list(tmp_path.glob('.jepa-generation-*'))


def test_unsafe_generation_members_rejected_before_loading(tmp_path, monkeypatch):
    def fake_save(model, path, source):
        path.write_bytes(b'model')
        return {'sha256': generation._sha(b'model')}
    monkeypatch.setattr(generation.checkpoint, 'save', fake_save)
    dest = tmp_path / 'generation'
    generation.save(object(), ReplaySession('a' * 64), dest)
    # A FIFO would hang a naive read_bytes() call.
    (dest / 'replay.json').unlink()
    os.mkfifo(dest / 'replay.json')
    with pytest.raises(ValueError, match='unsafe or oversized'):
        generation.load(dest, 'a' * 64)


def test_oversized_replay_rejected_before_read(tmp_path, monkeypatch):
    def fake_save(model, path, source):
        path.write_bytes(b'model')
        return {'sha256': generation._sha(b'model')}
    monkeypatch.setattr(generation.checkpoint, 'save', fake_save)
    dest = tmp_path / 'generation'
    generation.save(object(), ReplaySession('a' * 64), dest)
    with (dest / 'replay.json').open('wb') as out:
        out.truncate(generation.MAX_JOURNAL_BYTES + 1)
    with pytest.raises(ValueError, match='unsafe or oversized'):
        generation.load(dest, 'a' * 64)
