"""Generation integrity tests: stub IO is not model-training evidence."""
import pytest
from v13 import world_jepa_generation as generation
from v13.world_jepa_replay import ReplaySession


def test_generation_roundtrip_and_tamper(tmp_path, monkeypatch):
    def fake_save(model, path, source):
        path.write_bytes(b'model-test')
        return {'sha256': generation._sha(b'model-test')}
    def fake_load(path, source, expected):
        assert generation._sha(path.read_bytes()) == expected
        return 'restored-model'
    monkeypatch.setattr(generation.checkpoint, 'save', fake_save)
    monkeypatch.setattr(generation.checkpoint, 'load', fake_load)
    replay = ReplaySession('a' * 64)
    replay.seen['id'] = 'b' * 64
    path = tmp_path / 'generation-1'
    result = generation.save(object(), replay, path)
    assert result['optimizer_state_persisted'] is False
    model, restored, manifest = generation.load(path, 'a' * 64)
    assert model == 'restored-model'
    assert restored.snapshot() == replay.snapshot()
    with pytest.raises(ValueError):
        generation.save(object(), replay, path)
    with pytest.raises(ValueError):
        generation.load(path, 'c' * 64)
    (path / 'replay.json').write_text('{}')
    with pytest.raises(ValueError, match='hash mismatch'):
        generation.load(path, 'a' * 64)


def test_generation_does_not_publish_on_failed_checkpoint(tmp_path, monkeypatch):
    def fail(*args):
        raise RuntimeError('checkpoint failure')
    monkeypatch.setattr(generation.checkpoint, 'save', fail)
    with pytest.raises(RuntimeError):
        generation.save(object(), ReplaySession('a' * 64), tmp_path / 'generation')
    assert not (tmp_path / 'generation').exists()
    assert not list(tmp_path.glob('.jepa-generation-*'))
