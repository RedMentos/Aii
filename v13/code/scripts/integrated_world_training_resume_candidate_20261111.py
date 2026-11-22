"""Bind the staged Runtime guard to production WorldJEPA training-resume code.

The Store consumer, WorldJEPA and shadow checkpoint now persist optimizer state
in production source. This builder no longer overlays replacement training code;
it only binds the isolated review guard and lineage candidate to those exact
source bytes.
"""
import hashlib
import importlib.util
from pathlib import Path

BASE_SHA = '6230cc60d35968b0711ebe98b697fd6f0653f2932578f0c262a6c61589d8f0a3'
WORLD_SHA = 'bfb79304f9919760d1943a139677b0c986b9500d7f544bdb137991f5ab30b91d'
CHECKPOINT_SHA = '350ddef23530b551314a6ef30292e7a809c9691911d4993c33847f733aabed9f'
STATE_SHA = '9a43d11e194b82e4f1a4fecd56f2bd345ad352d5645f59e45219815df674fa1f'
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
