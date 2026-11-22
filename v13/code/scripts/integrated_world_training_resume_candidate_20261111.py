"""Bind the staged Runtime guard to production WorldJEPA training-resume code.

The Store consumer, WorldJEPA and shadow checkpoint now persist optimizer state
in production source. This builder no longer overlays replacement training code;
it only binds the isolated review guard and lineage candidate to those exact
source bytes.
"""
import hashlib
import importlib.util
from pathlib import Path

BASE_SHA = '593a02e3ef4d7ecef8489333883152464b7d697c9f7c2276f98e072149406162'
WORLD_SHA = 'b6dd353497bd08b756a491381ea4484419b0299e6263f5c4bac0ded112c9016a'
CHECKPOINT_SHA = '560653e1a59b48991163a61b01135e2ab6e6d89c85fdeec4a8a40198f9bacf97'
STATE_SHA = '026fc012c91def4b6b21b60bc9c8827c5e418648b04bd0528dbc4b5d9957238b'
# These are the old pins embedded in the base Runtime guard, not current inputs.
GUARD_WORLD_SHA = '14ee7982ab3866a13b2cca83086123281cf112a3c133b91c06df9df3669715fd'
GUARD_CHECKPOINT_SHA = 'f88ad5eea241aacd55e5c3d0f53eb0b132a164a2d49cc0185726f1a0a8a076ae'


def replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('unexpected production training-resume source: ' + label)
    return raw.replace(old, new, 1)


def build_sources(code_dir):
    code_dir = Path(code_dir)
    base_path = code_dir / 'scripts/integrated_context_recall_candidate_20261111.py'
    if base_path.is_symlink() or hashlib.sha256(base_path.read_bytes()).hexdigest() != BASE_SHA:
        raise ValueError('context composition source changed')
    world = (code_dir / 'v13/world_jepa.py').read_bytes()
    checkpoint = (code_dir / 'v13/world_jepa_shadow_checkpoint.py').read_bytes()
    state = (code_dir / 'v13/world_jepa_training_state.py').read_bytes()
    for raw, pin in ((world, WORLD_SHA), (checkpoint, CHECKPOINT_SHA), (state, STATE_SHA)):
        if hashlib.sha256(raw).hexdigest() != pin:
            raise ValueError('production WorldJEPA training-resume input changed')
    if b'_training_state=next_training' not in world or b"meta['training_resume']" not in checkpoint:
        raise ValueError('production WorldJEPA optimizer persistence is not integrated')

    spec = importlib.util.spec_from_file_location('verified_context_composition', base_path)
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    result = base.build_sources(code_dir)

    guard = result['v13/world_jepa_runtime_guard_candidate.py']
    guard = replace(guard, b'from . import world_model\n',
                    b'from . import world_model\nfrom . import world_jepa_training_state as training_state\n',
                    'guard training-state import')
    guard = replace(guard, b"'history', 'enc', 'tgt', 'preds', 'zsd', '_ztrain', '_nn_med'})",
                    b"'history', 'enc', 'tgt', 'preds', 'zsd', '_ztrain', '_nn_med', '_training_state'})",
                    'exact model state fields')
    guard = replace(guard,
                    b"if type(model) is not wj.WorldJEPA or set(model.__dict__) != REQUIRED:\n",
                    b"if (type(model) is not wj.WorldJEPA or not REQUIRED.issubset(model.__dict__)\n"
                    b"            or set(model.__dict__) - REQUIRED - {'_last_gradient_projection'}):\n",
                    'optional projection telemetry field')
    guard = replace(guard,
                    b"    if (type(model.seed) is not int or type(model.ensemble) is not int\n",
                    b"    if '_last_gradient_projection' in model.__dict__:\n"
                    b"        report = model.__dict__['_last_gradient_projection']\n"
                    b"        if (type(report) is not dict or any(\n"
                    b"                type(k) is not str or type(v) not in (bool, int, float, str, type(None))\n"
                    b"                or (type(v) in (int, float) and not np.isfinite(v))\n"
                     b"                or (type(v) is str and (k != 'projection_method' or v not in ('NO_ACTIVE_REFERENCE', 'ALREADY_FEASIBLE', 'ACTIVE_SET_ENUMERATION')))\n"
                    b"                for k, v in report.items())):\n"
                    b"            raise ValueError('unsupported World-JEPA projection telemetry')\n"
                    b"    if (type(model.seed) is not int or type(model.ensemble) is not int\n",
                    'projection telemetry validation')
    guard = replace(guard, b'    clone_meta, clone_arrays = checkpoint._extract(staged, VALIDATION_TAG)\n',
                    b'    staged._training_state=training_state.from_model(model)\n'
                    b'    clone_meta, clone_arrays = checkpoint._extract(staged, VALIDATION_TAG)\n',
                    'detached training state')
    for old, raw in ((GUARD_WORLD_SHA, world), (GUARD_CHECKPOINT_SHA, checkpoint)):
        guard = replace(guard, old.encode(), hashlib.sha256(raw).hexdigest().encode(),
                        'production World/checkpoint pin')
    guard = replace(guard, b'PINS = {\n',
                    b"PINS = {\n    'world_jepa_training_state.py': '" + STATE_SHA.encode() + b"',\n",
                    'production training helper pin')
    guard = replace(guard,
                    b"        return dict(result, source_verified=True, trained=True, active_model_promoted=False,\n",
                    b"        return dict(result, source_verified=True, trained=True, active_model_promoted=False,\n"
                    b"                    optimizer_steps=candidate._training_state['main']['t'],"
                    b"optimizer_state_continued=current is not None,\n",
                    'operator training telemetry')

    lineage = result['v13/world_jepa_lineage_checkpoint_candidate.py']
    lineage = replace(lineage, b"'optimizer_state_persisted': False}\n            finally:",
                      b"'optimizer_state_persisted': saved['optimizer_state_persisted']}\n            finally:",
                      'save state receipt')
    lineage = replace(lineage, b"'optimizer_state_persisted': False,\n                'selection'",
                      b"'optimizer_state_persisted': hasattr(model,'_training_state'),\n                'selection'",
                      'restore state receipt')
    result.update({
        'v13/world_jepa_training_state.py': state,
        'v13/world_jepa_runtime_guard_candidate.py': guard,
        'v13/world_jepa_lineage_checkpoint_candidate.py': lineage,
    })
    return result
