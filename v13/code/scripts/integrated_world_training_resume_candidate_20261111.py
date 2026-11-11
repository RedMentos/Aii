"""Keep real World-JEPA training state in the existing integrated review tree."""
import hashlib
import importlib.util
from pathlib import Path

BASE_SHA = '168d6003db2c871599e70922619cfc416882b137ce05704b5c7b4d35037f6c0f'
WORLD_SHA = '14ee7982ab3866a13b2cca83086123281cf112a3c133b91c06df9df3669715fd'
CHECKPOINT_SHA = 'f88ad5eea241aacd55e5c3d0f53eb0b132a164a2d49cc0185726f1a0a8a076ae'
STATE_SHA = '19e522c9f6af61f366044b355c42c3c6ef4da1d0f7301b6e71ec96adb1a23e29'


def replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('unexpected training-resume source: ' + label)
    return raw.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    path = code_dir / 'scripts/integrated_context_recall_candidate_20261111.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError('context composition source changed')
    state = (code_dir / 'v13/world_jepa_training_state_candidate.py').read_bytes()
    world = (code_dir / 'v13/world_jepa.py').read_bytes()
    checkpoint = (code_dir / 'v13/world_jepa_shadow_checkpoint.py').read_bytes()
    for raw, pin in ((state, STATE_SHA), (world, WORLD_SHA), (checkpoint, CHECKPOINT_SHA)):
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError('training-resume input source changed')
    spec = importlib.util.spec_from_file_location('verified_context_composition', path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    result = base.build_sources(code_dir)

    world = replace(world, b'import numpy as np\n',
                    b'import numpy as np\nfrom . import world_jepa_training_state_candidate as training_state\n', 'World import')
    world = replace(world, b"REVISION = 'z12b-world-jepa-v1'", b"REVISION = 'z12b-world-jepa-training-resume-v1'", 'World revision')
    world = replace(world, b"            prior = ({'mu':self.mu.copy()",
                    b"            saved_training = training_state.from_model(self) if warm_start else None\n            prior = ({'mu':self.mu.copy()", 'locked training snapshot')
    world = replace(world, b"            enc=prior['enc'];pred=prior['pred'];tgt=prior['tgt']\n",
                    b"            enc=prior['enc'];pred=prior['pred'];tgt=prior['tgt']\n            inv=saved_training['inverse']\n            rng.bit_generator.state=saved_training['rng']\n", 'inverse and RNG continuation')
    anchor = b"        opt = Adam({**{'e'+k: v for k, v in enc.items()}, **{'p'+k: v for k, v in pred.items()}, **{'i'+k: v for k, v in inv.items()}}, LR)\n"
    world = replace(world, anchor, anchor + b"        if saved_training is not None:training_state.restore_adam(opt,saved_training['main'])\n", 'main optimizer')
    world = replace(world, b'        preds = [pred]\n', b'        preds = [pred]\n        bootstrap_training=[]\n', 'bootstrap state list')
    anchor = b'            idx = r2.integers(0, len(x), len(x))\n'
    world = replace(world, anchor, b"            if saved_training is not None:\n                training_state.restore_adam(o,saved_training['bootstrap'][e-1]['adam'])\n                r2.bit_generator.state=saved_training['bootstrap'][e-1]['rng']\n" + anchor, 'bootstrap optimizer and RNG')
    world = replace(world, b'            preds.append(p)\n',
                    b"            preds.append(p)\n            bootstrap_training.append({'adam':training_state.snapshot(o),'rng':r2.bit_generator.state})\n", 'bootstrap capture')
    anchor = b"        total_steps=(getattr(self,'_fit_steps',0)+steps) if warm_start else steps\n"
    world = replace(world, anchor, anchor + b'        next_training=training_state.capture(opt,inv,rng,bootstrap_training,X.shape[1],A.shape[1],self.seed,self.ensemble,total_steps)\n', 'validated state publication')
    world = replace(world, b'            self.__dict__.update(_fit_steps=total_steps,',
                    b'            self.__dict__.update(_training_state=next_training,_fit_steps=total_steps,', 'atomic training publication')

    checkpoint = replace(checkpoint,
                         b'Private inference-only checkpoint for fitted NumPy WorldJEPA SHADOW.\n\nNo optimizer/EMA training resume, runtime hook, age authority or gate promotion.',
                         b'Private fitted NumPy WorldJEPA checkpoint in the integrated review copy.\n\nOptional numeric training state shares the bound archive; no added age authority.', 'checkpoint documentation')
    checkpoint = replace(checkpoint, b'from v13 import world_jepa as wj\n',
                         b'from v13 import world_jepa as wj\nfrom . import world_jepa_training_state_candidate as training_state\n', 'checkpoint import')
    checkpoint = replace(checkpoint, b'    return meta, arrays\n',
                         b"    if hasattr(model,'_training_state'):\n        meta['training_resume'],extra=training_state.pack(model)\n        arrays.update(extra)\n    return meta, arrays\n", 'checkpoint extraction')
    anchor = b'def _validate(meta, arrays, source_sha256):\n'
    checkpoint = replace(checkpoint, anchor, anchor + b"    if type(meta) is dict and 'training_resume' in meta:\n        numeric_meta={k:v for k,v in meta.items() if k!='training_resume'}\n        numeric={k:v for k,v in arrays.items() if not k.startswith(training_state.PREFIX)}\n        extra={k:v for k,v in arrays.items() if k.startswith(training_state.PREFIX)}\n        _validate(numeric_meta,numeric,source_sha256)\n        training_state.validate_payload(meta['training_resume'],extra,numeric_meta,numeric)\n        return True\n", 'checkpoint state validation')
    checkpoint = replace(checkpoint, b"            'optimizer_state_persisted': False}",
                         b"            'optimizer_state_persisted': hasattr(model,'_training_state')}", 'checkpoint receipt')
    checkpoint = replace(checkpoint, b"'scope': 'PRIVATE_INFERENCE_ONLY_SHADOW'",
                         b"'scope': ('PRIVATE_SHADOW_TRAINING_RESUME' if hasattr(model,'_training_state') else 'PRIVATE_INFERENCE_ONLY_SHADOW')", 'checkpoint scope')
    checkpoint = replace(checkpoint, b'model.history = []  # training history/optimizer not present: inference-only',
                         b'model.history = []  # diagnostic log omitted; optional training state restored below', 'checkpoint history note')
    checkpoint = replace(checkpoint, b'    raw = path.read_bytes()\n',
                         b'    raw = training_state.read_checkpoint(path,MAX_BYTES)\n', 'bounded checkpoint read')
    checkpoint = replace(checkpoint, b'len(info) > 128', b'len(info) > 512', 'bounded extra NPZ members')
    checkpoint = replace(checkpoint, b'    with np.load(io.BytesIO(raw), allow_pickle=False) as archive:\n',
                         b'    training_state.validate_archive(raw)\n    with np.load(io.BytesIO(raw), allow_pickle=False) as archive:\n', 'NPY allocation preflight')
    checkpoint = replace(checkpoint, b'    return model\n',
                         b"    if 'training_resume' in meta:\n        model._training_state=training_state.unpack(meta['training_resume'],\n            {k:v for k,v in arrays.items() if k.startswith(training_state.PREFIX)},\n            {k:v for k,v in meta.items() if k!='training_resume'},\n            {k:v for k,v in arrays.items() if not k.startswith(training_state.PREFIX)})\n    return model\n", 'loaded training state')

    guard = result['v13/world_jepa_runtime_guard_candidate.py']
    guard = replace(guard, b'from . import world_model\n',
                    b'from . import world_model\nfrom . import world_jepa_training_state_candidate as training_state\n', 'guard import')
    guard = replace(guard, b"'history', 'enc', 'tgt', 'preds', 'zsd', '_ztrain', '_nn_med'})",
                    b"'history', 'enc', 'tgt', 'preds', 'zsd', '_ztrain', '_nn_med', '_training_state'})", 'exact model state fields')
    guard = replace(guard, b'    clone_meta, clone_arrays = checkpoint._extract(staged, VALIDATION_TAG)\n',
                    b'    staged._training_state=training_state.from_model(model)\n    clone_meta, clone_arrays = checkpoint._extract(staged, VALIDATION_TAG)\n', 'detached training state')
    for old, raw in ((WORLD_SHA, world), (CHECKPOINT_SHA, checkpoint)):
        guard = replace(guard, old.encode(), hashlib.sha256(raw).hexdigest().encode(), 'World/checkpoint pin')
    guard = replace(guard, b'PINS = {\n', b"PINS = {\n    'world_jepa_training_state_candidate.py': '" + STATE_SHA.encode() + b"',\n", 'training helper pin')
    guard = replace(guard, b"        return dict(result, source_verified=True, trained=True, active_model_promoted=False,\n",
                    b"        return dict(result, source_verified=True, trained=True, active_model_promoted=False,\n                    optimizer_steps=candidate._training_state['main']['t'],optimizer_state_continued=current is not None,\n", 'operator training telemetry')
    lineage = result['v13/world_jepa_lineage_checkpoint_candidate.py']
    lineage = replace(lineage, b"'optimizer_state_persisted': False}\n            finally:",
                      b"'optimizer_state_persisted': saved['optimizer_state_persisted']}\n            finally:", 'save state receipt')
    lineage = replace(lineage, b"'optimizer_state_persisted': False,\n                'selection'",
                      b"'optimizer_state_persisted': hasattr(model,'_training_state'),\n                'selection'", 'restore state receipt')
    result.update({'v13/world_jepa.py': world, 'v13/world_jepa_shadow_checkpoint.py': checkpoint,
                   'v13/world_jepa_runtime_guard_candidate.py': guard,
                   'v13/world_jepa_lineage_checkpoint_candidate.py': lineage,
                   'v13/world_jepa_training_state_candidate.py': state})
    return result
