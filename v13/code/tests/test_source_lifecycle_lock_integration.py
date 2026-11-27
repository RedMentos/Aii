from pathlib import Path
import importlib.util


def test_lifecycle_lock_accepts_current_perception_vision_source():
    code_dir = Path(__file__).resolve().parents[1]
    source_dir = code_dir / "v13"
    builder_path = code_dir / "scripts" / "source_lifecycle_lock_integration_candidate.py"
    spec = importlib.util.spec_from_file_location("v14_source_lifecycle_lock_test", builder_path)
    assert spec is not None and spec.loader is not None
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)

    composed = builder.build_sources(source_dir)
    vision = composed["vision.py"].decode("utf-8")

    assert "from .source_lifecycle_candidate import vision_ingest" in vision
    assert "from .source_lifecycle_candidate import vision_forget" in vision
    assert "load_vision_state" in vision
    assert "save_vision_state" in vision
    # The source-disjoint A3 OOD gate must survive lifecycle composition.
    assert "ood_threshold" in vision
    assert "standardized_distance" in vision
