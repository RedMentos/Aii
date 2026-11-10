"""Bounded private JEPA checkpoint generations, rollback and tamper controls."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from v13 import world_jepa_runtime_checkpoint as lifecycle


def _fake_save(model, path, source):
    path.write_bytes(model.encode())
    return {'sha256': 'b'*64}


def _fake_load(path, source, digest):
    if path.is_symlink() or not path.is_file() or digest != 'b'*64:
        raise ValueError('invalid checkpoint')
    return path.read_bytes().decode()


def test_private_generations_are_bounded_and_rollback_is_explicit(tmp_path):
    runtime=SimpleNamespace(home=str(tmp_path),_world_jepa_source_sha='a'*64,
                            _world_jepa_online='first')
    with patch.object(lifecycle.checkpoint,'save',side_effect=_fake_save), \
         patch.object(lifecycle.checkpoint,'load',side_effect=_fake_load):
        lifecycle.save(runtime)
        home=tmp_path/'world_jepa_online'
        assert len(list(home.glob('jepa-*.npz')))==1
        runtime._world_jepa_online='second'
        lifecycle.save(runtime)
        assert len(list(home.glob('jepa-*.npz')))==2
        restored=SimpleNamespace(home=str(tmp_path))
        assert lifecycle.rollback(restored)['active_model_promoted'] is False
        assert restored._world_jepa_online=='first'
        runtime._world_jepa_online='third'
        lifecycle.save(runtime)
        assert len(list(home.glob('jepa-*.npz')))==2
        restored2=SimpleNamespace(home=str(tmp_path))
        lifecycle.rollback(restored2)
        assert restored2._world_jepa_online=='second'
        lifecycle.restore(restored2)
        assert restored2._world_jepa_online=='third'


def test_bad_previous_manifest_rejected_before_new_active(tmp_path):
    runtime=SimpleNamespace(home=str(tmp_path),_world_jepa_source_sha='a'*64,
                            _world_jepa_online='first')
    with patch.object(lifecycle.checkpoint,'save',side_effect=_fake_save), \
         patch.object(lifecycle.checkpoint,'load',side_effect=_fake_load):
        lifecycle.save(runtime)
        active=tmp_path/'world_jepa_online'/'active.json'
        original=active.read_bytes()
        meta=json.loads(original)
        meta['filename']='../../outside.npz'
        active.write_text(json.dumps(meta))
        runtime._world_jepa_online='second'
        with pytest.raises(ValueError,match='Invalid JEPA manifest'):
            lifecycle.save(runtime)
        assert active.read_text()==json.dumps(meta)
        assert not (tmp_path/'world_jepa_online'/'previous.json').exists()


def test_corrupt_active_manifest_does_not_leave_orphan_snapshot(tmp_path):
    runtime=SimpleNamespace(home=str(tmp_path),_world_jepa_source_sha='a'*64,
                            _world_jepa_online='first')
    with patch.object(lifecycle.checkpoint,'save',side_effect=_fake_save), \
         patch.object(lifecycle.checkpoint,'load',side_effect=_fake_load):
        lifecycle.save(runtime)
        home=tmp_path/'world_jepa_online'
        active=home/'active.json'
        meta=json.loads(active.read_text())
        meta['filename']='../../escape.npz'
        active.write_text(json.dumps(meta))
        runtime._world_jepa_online='second'
        before={p.name for p in home.iterdir()}
        with pytest.raises(ValueError,match='Invalid JEPA manifest'):
            lifecycle.save(runtime)
        assert {p.name for p in home.iterdir()}==before


def test_checkpoint_save_failure_removes_partial_unpublished_file(tmp_path):
    runtime=SimpleNamespace(home=str(tmp_path),_world_jepa_source_sha='a'*64,
                            _world_jepa_online='first')
    def interrupted(model,path,source):
        path.write_bytes(b'incomplete')
        raise OSError('disk full')
    with patch.object(lifecycle.checkpoint,'save',side_effect=interrupted):
        with pytest.raises(OSError,match='disk full'):
            lifecycle.save(runtime)
    home=tmp_path/'world_jepa_online'
    assert list(home.glob('jepa-*.npz'))==[]
    assert not (home/'active.json').exists()


def test_failed_manifest_publication_does_not_delete_last_good_checkpoint(tmp_path):
    runtime=SimpleNamespace(home=str(tmp_path),_world_jepa_source_sha='a'*64,
                            _world_jepa_online='first')
    with patch.object(lifecycle.checkpoint,'save',side_effect=_fake_save), \
         patch.object(lifecycle.checkpoint,'load',side_effect=_fake_load):
        lifecycle.save(runtime)
        home=tmp_path/'world_jepa_online'
        active_before=(home/'active.json').read_bytes()
        first_files={p.name for p in home.glob('jepa-*.npz')}
        runtime._world_jepa_online='second'
        original=lifecycle._write_manifest
        def reject_active(directory,name,manifest):
            if name=='active.json':
                raise OSError('manifest write failed')
            return original(directory,name,manifest)
        with patch.object(lifecycle,'_write_manifest',side_effect=reject_active):
            with pytest.raises(OSError,match='manifest write failed'):
                lifecycle.save(runtime)
        assert (home/'active.json').read_bytes()==active_before
        assert {p.name for p in home.glob('jepa-*.npz')}==first_files
        restored=SimpleNamespace(home=str(tmp_path))
        lifecycle.restore(restored)
        assert restored._world_jepa_online=='first'
