"""Regression for the source-pinned A5 visual Runtime consumer overlay."""
import importlib.util
from pathlib import Path


CODE = Path(__file__).resolve().parents[1]
BUILDER_PATH = CODE / "scripts/termux_runtime_recovery_candidate_20261121.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("core_a5_visual_runtime_composition", BUILDER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_full_pinned_stage_composes_one_shot_a5_visual_into_normal_runtime():
    module = load_builder()
    source_path = CODE / "v13/runtime.py"
    source_before = source_path.read_bytes()

    composed = module.build_sources(CODE)
    runtime = composed["v13/runtime.py"]

    assert b"def set_a5_visual_provider(self, provider):" in runtime
    assert b"consume_for_turn(self,e,text,a5_visual_stack,deadline)" in runtime
    assert runtime.count(b"consume_for_turn(self,e,text,a5_visual_stack,deadline)") == 1
    assert b"if not fixed_policy and getattr(self,'_a5_visual_provider',None) is not None:" in runtime
    assert b"VISUAL_PERCEPTION" in runtime
    assert b"a5_visual_stack.close()" in runtime
    assert b"raw_capture_persisted" not in runtime
    assert b"action_authority" not in runtime[runtime.index(b"VISUAL_PERCEPTION"):runtime.index(b"VISUAL_PERCEPTION") + 500] or b"learning_authority" in runtime
    assert source_path.read_bytes() == source_before

    assert "v13/a5_visual_runtime_consumer.py" not in composed
    assert "v13/a5_visual_frame_bridge.py" not in composed
    assert "v13/a4_visual_salience.py" not in composed
