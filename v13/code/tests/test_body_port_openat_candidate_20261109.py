"""Deterministic artifact path-swap counterexamples; no native trainer run."""
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import test_body_training_port as fixtures
from v13 import body_training,body_port_openat_candidate as candidate


@pytest.fixture
def port(tmp_path):
    home=tmp_path/'home';home.mkdir()
    return home,fixtures.BodyTrainingPortContract().make(home)


def test_regular_bound_files_keep_zero_authority(port):
    home,_=port
    result=candidate.inspect_train_port(home,'B1_DETAIL')
    assert result['reason']=='PORT_BOUND_PROOF_REQUIRED' and result['port_bound']
    assert result['update_authority']==0 and not result['available']


def test_original_check_can_bind_symlink_swapped_before_hash(port,tmp_path):
    home,d=port
    target=home/d['master_artifact'];outside=tmp_path/'outside-master';outside.write_bytes(target.read_bytes())
    real=body_training.file_hash
    def replace_before_hash(path):
        if path==target:path.unlink();path.symlink_to(outside)
        return real(path)
    with patch.object(body_training,'file_hash',side_effect=replace_before_hash):
        result=body_training.inspect_train_port(home,'B1_DETAIL')
    assert result['port_bound'] and result['update_authority']==0 and target.is_symlink()


def test_swapped_file_during_hash_is_not_bound(port,tmp_path):
    home,d=port
    target=home/d['master_artifact'];outside=tmp_path/'outside-master';outside.write_bytes(target.read_bytes())
    real=candidate._stream
    def replace_during_hash(fd,relative,limit=None):
        if relative==d['master_artifact']:
            target.unlink();target.symlink_to(outside)
        return real(fd,relative,limit)
    with patch.object(candidate,'_stream',side_effect=replace_during_hash):
        result=candidate.inspect_train_port(home,'B1_DETAIL')
    assert result['reason']=='ARTIFACT_CHANGED_DURING_INSPECTION'
    assert not result.get('port_bound',False) and result['update_authority']==0


def test_swapped_parent_directory_during_hash_is_not_bound(port):
    home,d=port
    real=candidate._stream
    def swap_parent(fd,relative,limit=None):
        if relative==d['master_artifact']:
            (home/'models').rename(home/'models-original')
            (home/'models').symlink_to(home/'models-original',target_is_directory=True)
        return real(fd,relative,limit)
    with patch.object(candidate,'_stream',side_effect=swap_parent):
        result=candidate.inspect_train_port(home,'B1_DETAIL')
    assert result['reason']=='ARTIFACT_CHANGED_DURING_INSPECTION'
    assert not result.get('port_bound',False)


def test_symlink_and_special_file_are_rejected_without_opening_pipe(port):
    home,d=port;master=home/d['master_artifact']
    real=home/'real-master';master.rename(real);master.symlink_to(real)
    assert candidate.inspect_train_port(home,'B1_DETAIL')['reason']=='UNSAFE_ARTIFACT_PATH'
    master.unlink();os.mkfifo(master)
    assert candidate.inspect_train_port(home,'B1_DETAIL')['reason']=='UNSAFE_ARTIFACT_TYPE'


def test_descriptor_replacement_during_other_artifact_hash_is_detected(port):
    home,d=port;descriptor=home/'config/native-body-train-port.json'
    replacement=descriptor.read_bytes();real=candidate._stream
    def replace_descriptor(fd,relative,limit=None):
        if relative==d['master_artifact']:
            descriptor.unlink();descriptor.write_bytes(replacement)
        return real(fd,relative,limit)
    with patch.object(candidate,'_stream',side_effect=replace_descriptor):
        result=candidate.inspect_train_port(home,'B1_DETAIL')
    assert result['reason']=='ARTIFACT_CHANGED_DURING_INSPECTION'


def test_in_place_mutation_during_read_is_detected(port):
    home,d=port;master=home/d['master_artifact'];real=candidate._stream
    def mutate_after_read(fd,relative,limit=None):
        result=real(fd,relative,limit)
        if relative==d['master_artifact']:master.write_bytes(b'X'*len(master.read_bytes()))
        return result
    with patch.object(candidate,'_stream',side_effect=mutate_after_read):
        result=candidate.inspect_train_port(home,'B1_DETAIL')
    assert result['reason']=='ARTIFACT_CHANGED_DURING_INSPECTION'
    assert not result.get('port_bound',False)


def test_descriptor_symlink_is_rejected_and_path_hash_is_not_used(port,tmp_path):
    home,_=port
    with patch.object(body_training,'file_hash',side_effect=AssertionError('path-based hash called')):
        assert candidate.inspect_train_port(home,'B1_DETAIL')['port_bound']
    descriptor=home/'config/native-body-train-port.json'
    outside=tmp_path/'external-descriptor';outside.write_bytes(descriptor.read_bytes())
    descriptor.unlink();descriptor.symlink_to(outside)
    assert candidate.inspect_train_port(home,'B1_DETAIL')['reason']=='UNSAFE_ARTIFACT_PATH'


def test_invalid_descriptor_never_raises_or_grants_authority(port):
    home,d=port;path=home/'config/native-body-train-port.json'
    d['trainable_parameter_ids']=[{'not':'a string'}];path.write_text(json.dumps(d))
    result=candidate.inspect_train_port(home,'B1_DETAIL')
    assert result['reason']=='INVALID_TRAINABLE_PARAMETER_SET' and result['update_authority']==0
    path.write_text('{"role":"spoof",'+json.dumps(d)[1:])
    assert candidate.inspect_train_port(home,'B1_DETAIL')['reason']=='INVALID_TRAIN_PORT_DESCRIPTOR'


def test_requantizer_exception_and_runner_permissions(port):
    home,d=port;d.update(requantizer_artifact=None,requantizer_sha256=None,master_dtype='float32',
                         trainable_parameter_ids=['norm.weight'],fp32_inference_parameter_ids=['norm.weight'])
    (home/'config/native-body-train-port.json').write_text(json.dumps(d))
    result=candidate.inspect_train_port(home,'B1_DETAIL')
    assert result['requantization']=='NOT_APPLICABLE_FP32_SLICES' and result['update_authority']==0
    (home/d['runner_artifact']).chmod(0o644)
    assert candidate.inspect_train_port(home,'B1_DETAIL')['reason']=='TRAIN_RUNNER_NOT_EXECUTABLE'


def test_unsafe_descriptor_and_missing_artifact_are_closed(port):
    home,d=port
    assert candidate.inspect_train_port(home,'B1_DETAIL',descriptor='../outside')['reason']=='INVALID_ARTIFACT_BINDING'
    (home/d['master_artifact']).unlink()
    assert candidate.inspect_train_port(home,'B1_DETAIL')['reason']=='MISSING_MASTER_ARTIFACT'
