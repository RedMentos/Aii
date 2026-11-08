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


def test_real_numpy_jepa_generation_resume_without_duplicate_gradient(tmp_path):
    from v13.world_jepa import WorldJEPA
    from v13 import world_model
    routes = tuple(world_model.ACTIONS)
    records = [{'action_id': f'event-{i:04d}',
                's': [float(i % 13), float(i % 7), float(i % 5), float(i % 3)],
                'a': routes[i % len(routes)],
                'y': [float(i % 2), float(i % 3), float(i % 7)]}
               for i in range(96)]
    replay = ReplaySession('a' * 64)
    model = WorldJEPA(seed=11, ensemble=1)
    first = replay.update(model, records, steps=2)
    assert first['updated'] and first['new_rows'] > 0
    path = tmp_path / 'real-generation'
    generation.save(model, replay, path)
    restored_model, restored_replay, manifest = generation.load(path, 'a' * 64)
    assert restored_model._fit_steps == model._fit_steps
    assert not restored_replay.update(restored_model, records, steps=2)['updated']
    assert restored_model._fit_steps == model._fit_steps
    assert manifest['active_model_promoted'] is False
    # A later committed generation must learn only genuinely new train IDs.
    extended = records + [{'action_id': f'event-{i:04d}',
                           's': [float(i % 13), float(i % 7), float(i % 5), float(i % 3)],
                           'a': routes[i % len(routes)],
                           'y': [float(i % 2), float(i % 3), float(i % 7)]}
                          for i in range(96, 120)]
    next_result = restored_replay.update(restored_model, extended, steps=2)
    assert next_result['updated'] and next_result['new_rows'] > 0
    assert restored_model._fit_steps == model._fit_steps + 2
    next_path = tmp_path / 'real-generation-2'
    generation.save(restored_model, restored_replay, next_path)
    resumed_model, resumed_replay, _ = generation.load(next_path, 'a' * 64)
    assert resumed_model._fit_steps == restored_model._fit_steps
    assert not resumed_replay.update(resumed_model, extended, steps=2)['updated']


def test_generation_rejects_manifest_rewrite_and_extra_files(tmp_path, monkeypatch):
    def fake_save(model, path, source):
        path.write_bytes(b'model')
        return {'sha256': generation._sha(b'model')}
    monkeypatch.setattr(generation.checkpoint, 'save', fake_save)
    path = tmp_path / 'generation'
    generation.save(object(), ReplaySession('a' * 64), path)
    (path / 'unexpected.txt').write_text('x')
    with pytest.raises(ValueError, match='incomplete generation'):
        generation.load(path, 'a' * 64)
    (path / 'unexpected.txt').unlink()
    raw = (path / 'manifest.json').read_text()
    (path / 'manifest.json').write_text(raw + ' ')
    with pytest.raises(ValueError, match='manifest mismatch'):
        generation.load(path, 'a' * 64)
