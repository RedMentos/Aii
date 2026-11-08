"""Core AG6 real-weight-learning preflight: missing resources are explicit."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from v13.agi import trainers
from v13.common import file_hash


class State:
    def __init__(self,state):self.state=state
    def load(self):return self.state,0


def runtime(tmp_path):
    return SimpleNamespace(store=object(),home=tmp_path)


def requirements(tmp_path,**changes):
    base={'master':str(tmp_path/'master'),'master_ok':False,'arch_match':None,
          'torch':False,'torch_sparse':False,'c3_gguf':None,
          'runner_ok':False,'memory_server_ok':False}
    base.update(changes)
    return base


def preflight(tmp_path,req,state=None,probe=(['anchor'],['holdout'])):
    state=state or {'master':None,'master_sha256':None}
    with patch.object(trainers,'_box',return_value=State(state)), \
         patch.object(trainers,'requirements',return_value=req), \
         patch.object(trainers,'probes',return_value=probe):
        return trainers.training_readiness(runtime(tmp_path))


def test_missing_model_and_trainer_are_reported_without_mutation(tmp_path):
    result=preflight(tmp_path,requirements(tmp_path))
    assert not result['ready']
    assert 'MASTER_WEIGHTS_MISSING' in result['reasons']
    assert 'MASTER_CONFIG_MISSING' in result['reasons']
    assert 'DEPLOYED_C3_MISSING' in result['reasons']
    assert 'TRAINER_DEPENDENCIES_MISSING' in result['reasons']
    assert 'LIVE_EVALUATOR_MISSING' in result['reasons']
    assert not (tmp_path/'training').exists()


def test_unverified_architecture_is_not_treated_as_ready(tmp_path):
    master=tmp_path/'master';master.mkdir()
    (master/'model.safetensors').write_bytes(b'weights')
    (master/'config.json').write_text('{"hidden_size":512,"num_hidden_layers":12}')
    req=requirements(tmp_path,master_ok=True,c3_gguf='model.gguf',torch=True,runner_ok=True)
    result=preflight(tmp_path,req,{'master':str(master),'master_sha256':file_hash(master/'model.safetensors')})
    assert not result['ready']
    assert result['reasons']==['MASTER_GGUF_ARCH_UNVERIFIED']


def test_pinned_master_hash_change_blocks_learning(tmp_path):
    master=tmp_path/'master';master.mkdir()
    (master/'model.safetensors').write_bytes(b'changed')
    (master/'config.json').write_text('{"hidden_size":512,"num_hidden_layers":12}')
    req=requirements(tmp_path,master_ok=True,arch_match=True,c3_gguf='model.gguf',torch=True,runner_ok=True)
    result=preflight(tmp_path,req,{'master':str(master),'master_sha256':'wrong-hash'})
    assert not result['ready']
    assert result['reasons']==['MASTER_HASH_CHANGED']


def test_verified_real_trainer_prerequisites_can_pass(tmp_path):
    master=tmp_path/'master';master.mkdir()
    (master/'model.safetensors').write_bytes(b'weights')
    (master/'config.json').write_text('{"hidden_size":512,"num_hidden_layers":12}')
    req=requirements(tmp_path,master_ok=True,arch_match=True,c3_gguf='model.gguf',torch=True,runner_ok=True)
    result=preflight(tmp_path,req,{'master':str(master),'master_sha256':file_hash(master/'model.safetensors')})
    assert result['ready'] and result['reasons']==[]
    assert 'not trained' in result['claims']


def test_empty_retention_probes_block_ready(tmp_path):
    master=tmp_path/'master';master.mkdir()
    (master/'model.safetensors').write_bytes(b'weights')
    (master/'config.json').write_text('{"hidden_size":512,"num_hidden_layers":12}')
    req=requirements(tmp_path,master_ok=True,arch_match=True,c3_gguf='model.gguf',torch=True,runner_ok=True)
    result=preflight(tmp_path,req,{'master':str(master),'master_sha256':file_hash(master/'model.safetensors')},probe=([],[]))
    assert 'RETENTION_PROBES_EMPTY' in result['reasons']


def test_invalid_kind_rejected(tmp_path):
    with pytest.raises(ValueError):trainers.training_readiness(runtime(tmp_path),'shadow')


def test_unpinned_master_is_not_eligible_for_real_weight_training(tmp_path):
    master=tmp_path/'master';master.mkdir()
    (master/'model.safetensors').write_bytes(b'weights')
    (master/'config.json').write_text('{"hidden_size":512,"num_hidden_layers":12}')
    req=requirements(tmp_path,master_ok=True,arch_match=True,c3_gguf='model.gguf',torch=True,runner_ok=True)
    result=preflight(tmp_path,req)
    assert not result['ready']
    assert 'MASTER_HASH_NOT_PINNED' in result['reasons']


def test_invalid_pretrained_architecture_config_blocks_training(tmp_path):
    master=tmp_path/'master';master.mkdir()
    (master/'model.safetensors').write_bytes(b'weights')
    (master/'config.json').write_text('{"hidden_size":0,"num_hidden_layers":12}')
    req=requirements(tmp_path,master_ok=True,arch_match=True,c3_gguf='model.gguf',torch=True,runner_ok=True)
    result=preflight(tmp_path,req,{'master':str(master),'master_sha256':file_hash(master/'model.safetensors')})
    assert not result['ready']
    assert 'MASTER_CONFIG_INVALID' in result['reasons']


def test_sparse_learning_requires_serving_path(tmp_path):
    master=tmp_path/'master';master.mkdir()
    (master/'model.safetensors').write_bytes(b'weights')
    (master/'config.json').write_text('{"hidden_size":512,"num_hidden_layers":12}')
    req=requirements(tmp_path,master_ok=True,arch_match=True,c3_gguf='model.gguf',
                     torch_sparse=True,memory_server_ok=False)
    state={'master':str(master),'master_sha256':file_hash(master/'model.safetensors')}
    with patch.object(trainers,'_box',return_value=State(state)), \
         patch.object(trainers,'requirements',return_value=req), \
         patch.object(trainers,'probes',return_value=(['anchor'],['holdout'])):
        result=trainers.training_readiness(runtime(tmp_path),'sparse')
    assert not result['ready']
    assert result['reasons']==['SPARSE_SERVING_UNAVAILABLE']
