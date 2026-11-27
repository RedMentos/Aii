from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


CODE_DIR = Path(__file__).resolve().parents[1]
BUILDER_PATH = CODE_DIR / "scripts" / "integrated_native_latent_receiver_candidate_20261122.py"
SPEC = spec_from_file_location("native_receiver_pin_builder", BUILDER_PATH)
assert SPEC is not None and SPEC.loader is not None
BUILDER = module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


def test_current_callosum_source_is_accepted_by_exact_pin_set():
    callosum = CODE_DIR / "v13" / "callosum.py"
    accepted = BUILDER.BASE_PINS["v13/callosum.py"]
    assert accepted == frozenset({
        "f07fba55eac93af5f855a20c7ac136d15a2fa44315d0878d41b8090ddd905748",
        "40f5e0f623ffcbcffba901bc4bfba9fe289b1e9410b764db9f1a2193e3b0c348",
    })
    assert BUILDER._matches_base_pin(callosum, accepted)


def test_callosum_pin_negative_control_rejects_unlisted_hash():
    callosum = CODE_DIR / "v13" / "callosum.py"
    assert not BUILDER._matches_base_pin(callosum, frozenset({"0" * 64}))
