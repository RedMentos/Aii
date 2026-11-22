"""Synthetic source-bound RAW EYE → A5 → A4 → bounded C3 admission tests."""
from io import BytesIO
import threading
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from v13 import vision
from v13.attention import Attention
from v13.store import Store
from v13.vision_a5_bridge import consume_visual_source


def image_bytes():
    image = Image.new("RGB", (64, 64), (18, 18, 18))
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 20, 58, 50), fill=(240, 24, 20))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def make_runtime(tmp_path):
    (tmp_path / "data" / "db").mkdir(parents=True)
    store = Store(tmp_path)
    store.ensure_generation_snapshot({}, {})
    session = store.new_session("RAW EYE visual A5 bridge test")
    event = store.event(session, "What is visible in this image?")
    runtime = SimpleNamespace(
        home=tmp_path,
        store=store,
        turn_event=event,
        attention=Attention(store, None, None),
    )
    return runtime, event


def add_image(runtime):
    return vision.ingest(runtime.store, image_bytes(), label="synthetic red rectangle")


def test_stored_image_reaches_source_bound_a5_a4_and_c3_candidate(tmp_path):
    runtime, event = make_runtime(tmp_path)
    record = add_image(runtime)
    prompt = "What is visible in this image? Keep uncertainty explicit."
    try:
        result = consume_visual_source(
            runtime,
            record["ref"],
            consent=True,
            current_source=prompt,
            goal="red object on the right",
        )
        packet = result["packet"]
        assert result["status"] == "WIRED_SOURCE_BOUND"
        assert packet["producer_component"] == "A5_RAW_EYE"
        assert packet["modality"] == "visual"
        assert packet["source_ref"] == record["ref"]
        assert packet["temporal_status"] == "STATIC_UNTIMED"
        assert packet["capture_time_status"] == "UNKNOWN"
        assert len(packet["segments"]) == 17  # global image + all 16 grid tiles
        assert all(seg["authority"] == "RAW_FEATURE_MEASUREMENT" for seg in packet["segments"])
        assert all(seg["time_basis"] == "STATIC_IMAGE_UNTIMED" for seg in packet["segments"])
        assert all(seg["learning_authority"] is False and seg["action_authority"] is False
                   for seg in packet["segments"])
        assert result["a4"]["truth_authority"] == 0
        assert result["a4"]["requests"] == []  # no high-resolution image provider is claimed
        assert len(result["a4"]["segments"]) == 17
        assert result["admission"].status == "ADMITTED"
        assert result["context_envelope"].current_source == prompt
        assert "RAW_EYE" in result["context_envelope"].optional_context
        assert result["context_budget_kind"] == "CHARACTER_PREFILTER_NOT_NATIVE_TOKENIZER"
        assert result["raw_image_source_persisted"] is True
        assert result["derived_packet_persisted"] is False
        assert result["teacher_used"] is False
        assert result["student_projector_used"] is False
        assert result["learning_authority"] is False
        assert result["action_authority"] is False
        assert not runtime.store.rows(
            "SELECT id FROM packets WHERE kind='PerceptPacket' AND event_id=?",
            (event["event_id"],),
        )
    finally:
        runtime.store.close()


def test_visual_ingress_requires_explicit_consent_and_exact_image_ref(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    record = add_image(runtime)
    try:
        with pytest.raises(PermissionError, match="consent"):
            consume_visual_source(
                runtime, record["ref"], consent=False,
                current_source="Describe this image.",
            )
        wrong = dict(record["ref"])
        wrong["modality"] = "text"
        with pytest.raises(ValueError, match="modality"):
            consume_visual_source(
                runtime, wrong, consent=True,
                current_source="Describe this image.",
            )
    finally:
        runtime.store.close()


def test_forgotten_or_unbound_image_source_is_rejected(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    record = add_image(runtime)
    try:
        vision.forget(runtime.store, record)
        with pytest.raises(ValueError, match="missing, forgotten"):
            consume_visual_source(
                runtime, record["ref"], consent=True,
                current_source="Describe this image.",
            )
    finally:
        runtime.store.close()


def test_visual_ingress_requires_active_turn_and_preserves_prompt_when_budget_zero(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    record = add_image(runtime)
    prompt = "Do not truncate this exact current user source."
    try:
        runtime.turn_event = None
        with pytest.raises(ValueError, match="active Runtime"):
            consume_visual_source(
                runtime, record["ref"], consent=True,
                current_source=prompt,
            )
        runtime.turn_event = {
            "event_id": "evt_00000000000000000000000000000001",
            "brain_generation_id": "gen_00000000000000000000000000000001",
        }
        result = consume_visual_source(
            runtime, record["ref"], consent=True,
            current_source=prompt, token_budget=0, context_budget_chars=0,
        )
        assert result["admission"].status == "EMPTY_OR_UNAUTHORIZED"
        assert result["context_envelope"].current_source == prompt
        assert result["context_envelope"].optional_context == ""
        assert len(result["packet"]["segments"]) == 17
    finally:
        runtime.store.close()


def test_visual_a5_consumption_is_serialized_with_source_forget(tmp_path, monkeypatch):
    runtime, _ = make_runtime(tmp_path)
    record = add_image(runtime)
    prompt = "Describe this exact image without losing the current prompt."
    feature_entered = threading.Event()
    release_feature = threading.Event()
    forget_started = threading.Event()
    forget_done = threading.Event()
    results = []
    errors = []
    original_tile_features = vision.tile_features
    first = True

    def paused_tile_features(image, px=32):
        nonlocal first
        if first:
            first = False
            feature_entered.set()
            if not release_feature.wait(5):
                raise TimeoutError("test did not release the visual feature stage")
        return original_tile_features(image, px)

    monkeypatch.setattr(vision, "tile_features", paused_tile_features)

    def consume():
        try:
            results.append(consume_visual_source(
                runtime, record["ref"], consent=True, current_source=prompt,
            ))
        except BaseException as exc:
            errors.append(exc)

    def forget():
        forget_started.set()
        vision.forget(runtime.store, record)
        forget_done.set()

    reader = threading.Thread(target=consume, daemon=True)
    revoker = threading.Thread(target=forget, daemon=True)
    try:
        reader.start()
        assert feature_entered.wait(3), "visual A5 path did not reach feature extraction"
        revoker.start()
        assert forget_started.wait(3), "forget thread did not start"
        assert not forget_done.wait(0.1), "source forget raced through an active visual A5 consumer"
        release_feature.set()
        reader.join(5)
        revoker.join(5)
        assert not reader.is_alive() and not revoker.is_alive()
        assert not errors, errors
        assert len(results) == 1 and results[0]["status"] == "WIRED_SOURCE_BOUND"
        assert results[0]["context_envelope"].current_source == prompt
        assert forget_done.is_set()
        with pytest.raises(ValueError, match="Dangling|gelöschter"):
            vision.read_image(runtime.store, record["ref"])
    finally:
        release_feature.set()
        runtime.store.close()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
