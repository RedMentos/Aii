"""Normal-turn consumer contract for consent-leased A5 visual frames."""
import contextlib
import io
import tempfile
import threading
import time
from pathlib import Path

from PIL import Image
import pytest

from v13.attention import Attention
from v13.store import Store
from v13.a5_visual_runtime_consumer import consume_for_turn, set_provider


class Provider:
    def __init__(self, frame=None, observation=None):
        self.lock = threading.RLock()
        self.active = True
        self.callbacks = {}
        self.sequence = 0
        self.frame = frame
        self.observation = observation
        self.approved = True

    def poll_visual_frame(self, *, event_id, generation_id, deadline):
        if not self.approved or self.frame is None:
            return None
        frame, self.frame = self.frame, None
        return {"observation": self.observation, "frame_bytes": frame}

    def consent_check(self, *args):
        with self.lock:
            return self.active

    def consent_guard(self, *args):
        @contextlib.contextmanager
        def held():
            with self.lock:
                yield self.active
        return held()

    def revocation_subscribe(self, source_id, receipt, session_id, on_revoke_requested, on_revoked):
        self.sequence += 1
        key = self.sequence
        self.callbacks[key] = (on_revoke_requested, on_revoked)

        def unsubscribe():
            self.callbacks.pop(key, None)

        return unsubscribe

    def revoke(self):
        callbacks = tuple(self.callbacks.values())
        for request_cancel, _cleanup in callbacks:
            request_cancel()
        with self.lock:
            self.active = False
        for _request_cancel, cleanup in callbacks:
            cleanup()


def observation(**overrides):
    value = {
        "schema": "v14.a5.ui-observation/1",
        "modality": "ui",
        "source_id": "src_runtime_visual_test",
        "capture_session_id": "session_runtime_visual_test",
        "consent_receipt_ref": "receipt_runtime_visual_test",
        "capture_method": "MEDIA_PROJECTION",
        "capture_scope": "FULL_DISPLAY",
        "api_level": 34,
        "clock": "ELAPSED_REALTIME",
        "event_kind": "SCREEN_FRAME_AVAILABLE",
        "start_ms": 100,
        "end_ms": 120,
        "finality": "FINAL",
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }
    value.update(overrides)
    return value


def png_bytes():
    image = Image.new("RGB", (32, 24))
    pixels = image.load()
    for y in range(24):
        for x in range(32):
            pixels[x, y] = ((x * 7) % 256, (y * 11) % 256, ((x + y) * 5) % 256)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class RuntimeStub:
    def __init__(self, home, store, event):
        self.home = home
        self.store = store
        self.turn_event = None
        self.current = None
        self.cancel_event = threading.Event()
        self.attention = Attention(store)
        self.lock = threading.RLock()
        self.closed = False


@pytest.fixture
def runtime_fixture():
    temp = tempfile.TemporaryDirectory()
    home = Path(temp.name)
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    (home / "data" / "vision").mkdir(parents=True)
    store = Store(home)
    session = store.new_session("A5 Runtime consumer test")
    event = dict(store.event(session, "what is on my screen?"))
    event["brain_generation_id"] = "gen_runtime_visual_test"
    runtime = RuntimeStub(home, store, event)
    yield runtime, event, home
    runtime.current = None
    runtime.turn_event = None
    adapter = getattr(runtime, "_a5_visual_adapter", None)
    if adapter is not None:
        adapter.close()
    store.close()
    temp.cleanup()


def attach(runtime, provider):
    assert set_provider(runtime, provider) == "ATTACHED_UNVERIFIED"


def activate(runtime, event):
    runtime.turn_event = event
    runtime.current = "turn"


def test_one_shot_frame_reaches_a4_and_normal_c3_context_without_disk_capture(runtime_fixture):
    runtime, event, home = runtime_fixture
    frame = png_bytes()
    provider = Provider(frame=frame, observation=observation())
    attach(runtime, provider)
    activate(runtime, event)

    with contextlib.ExitStack() as stack:
        result = consume_for_turn(
            runtime, event, "what is on my screen?", stack, time.monotonic() + 5.0
        )
        assert result is not None
        assert result["audit"]["status"] == "CONSUMED_UNVERIFIED"
        assert result["prompt_context"]["modality"] == "visual"
        assert result["prompt_context"]["source_ref"]["source_id"] == "src_runtime_visual_test"
        assert result["prompt_context"]["raw_capture_persisted"] is False
        assert result["prompt_context"]["action_authority"] is False
        assert result["prompt_context"]["learning_authority"] is False
        assert result["prompt_context"]["a4_visual_salience"] >= result["prompt_context"]["a4_base_salience"]
        assert result["audit"]["feature_count"] > 0
        assert len(result["audit"]["feature_sha256"]) == 64
        assert frame.hex() not in repr(result["prompt_context"])
        assert runtime._a5_visual_adapter._packets
        assert runtime._a5_visual_adapter._features
        assert runtime.store.one(
            "SELECT id FROM sources WHERE id=?", ("src_runtime_visual_test",)
        ) is None
        assert runtime.store.one(
            "SELECT id FROM sources WHERE hash=?", (result["audit"]["raw_frame_sha256"],)
        ) is None
        blob_names = {path.name for path in (home / "data" / "blobs").iterdir()}
        assert result["audit"]["raw_frame_sha256"] not in blob_names

    assert runtime._a5_visual_adapter._packets == {}
    assert runtime._a5_visual_adapter._features == {}
    assert runtime._a5_visual_adapter._owned_sources == set()
    assert provider.callbacks == {}


def test_no_pending_user_approved_frame_is_a_noop(runtime_fixture):
    runtime, event, _home = runtime_fixture
    provider = Provider(frame=png_bytes(), observation=observation())
    provider.approved = False
    attach(runtime, provider)
    activate(runtime, event)
    with contextlib.ExitStack() as stack:
        assert consume_for_turn(
            runtime, event, "hello", stack, time.monotonic() + 5.0
        ) is None
    assert not hasattr(runtime, "_a5_visual_adapter")


def test_provider_cannot_change_during_active_turn(runtime_fixture):
    runtime, _event, _home = runtime_fixture
    provider = Provider(frame=png_bytes(), observation=observation())
    activate(runtime, _event)
    with pytest.raises(RuntimeError, match="during an active"):
        set_provider(runtime, provider)


def test_invalid_or_unapproved_receipt_fails_closed(runtime_fixture):
    runtime, event, _home = runtime_fixture
    provider = Provider(frame=png_bytes(), observation=observation())
    provider.active = False
    attach(runtime, provider)
    activate(runtime, event)
    with contextlib.ExitStack() as stack:
        with pytest.raises(PermissionError, match="current OS observe_ui grant"):
            consume_for_turn(
                runtime, event, "what is on my screen?", stack, time.monotonic() + 5.0
            )
    assert runtime._a5_visual_adapter._packets == {}
    assert runtime._a5_visual_adapter._features == {}


def test_revocation_cancels_the_same_turn_and_clears_visual_buffers(runtime_fixture):
    runtime, event, _home = runtime_fixture
    provider = Provider(frame=png_bytes(), observation=observation())
    attach(runtime, provider)
    activate(runtime, event)
    with contextlib.ExitStack() as stack:
        result = consume_for_turn(
            runtime, event, "what is on my screen?", stack, time.monotonic() + 5.0
        )
        assert result is not None
        provider.revoke()
        assert runtime.cancel_event.is_set()
        assert runtime._a5_visual_adapter._packets == {}
        assert runtime._a5_visual_adapter._features == {}
    assert provider.callbacks == {}


def test_provider_payload_must_be_exact_and_bounded(runtime_fixture):
    runtime, event, _home = runtime_fixture

    class InvalidProvider(Provider):
        def poll_visual_frame(self, *, event_id, generation_id, deadline):
            return {
                "observation": observation(),
                "frame_bytes": png_bytes(),
                "extra": "not allowed",
            }

    provider = InvalidProvider()
    attach(runtime, provider)
    activate(runtime, event)
    with contextlib.ExitStack() as stack:
        with pytest.raises(ValueError, match="exactly observation and frame_bytes"):
            consume_for_turn(
                runtime, event, "what is on my screen?", stack, time.monotonic() + 5.0
            )


def test_provider_can_be_detached_only_between_turns(runtime_fixture):
    runtime, _event, _home = runtime_fixture
    provider = Provider(frame=png_bytes(), observation=observation())
    runtime.current = None
    assert set_provider(runtime, provider) == "ATTACHED_UNVERIFIED"
    assert set_provider(runtime, None) == "DETACHED"
    assert runtime._a5_visual_provider is None
