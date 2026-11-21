"""Race regression: source publication and consent-revocation blob unlink must serialize."""
import threading
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from v13.common import digest
from v13.store import Store
from v13.a5_ui_admission_bridge import _persist_source_and_packet, revoke_ui_observation


def _source(source_id, summary):
    return {
        "source_id": source_id,
        "sha256": digest(summary.encode("utf-8")),
        "char_start": 0,
        "char_end": len(summary),
        "modality": "ui",
    }


def _packet(packet_id, source_ref):
    return {
        "packet_id": packet_id,
        "event_id": "event-" + packet_id,
        "brain_generation_id": "generation-race",
        "source_ref": source_ref,
    }


def test_revoke_blob_unlink_is_serialized_with_new_shared_source_publication(tmp_path):
    home = Path(tmp_path)
    (home / "data" / "db").mkdir(parents=True)
    (home / "data" / "blobs").mkdir(parents=True)
    store = Store(home)
    runtime = type("RuntimeStub", (), {})()
    runtime.store = store
    runtime._a5_ui_context_cache = {}
    runtime._a5_ui_unsubscribe = {}

    summary = (
        "ui event=APP_INTENT_RESULT method=APP_INTENT scope=APP_DATA "
        "api=33 clock=ELAPSED_REALTIME interval_ms=20"
    )
    first = _source("src_ui_first", summary)
    second = _source("src_ui_second", summary)
    blob = home / "data" / "blobs" / first["sha256"]
    entered_unlink = threading.Event()
    allow_unlink = threading.Event()
    errors = []

    _persist_source_and_packet(runtime, first, summary, _packet("packet-first", first))
    assert blob.is_file()

    original_unlink = Path.unlink

    def pause_before_blob_unlink(path, *args, **kwargs):
        if path == blob:
            entered_unlink.set()
            if not allow_unlink.wait(5):
                raise TimeoutError("test did not release the revocation unlink")
        return original_unlink(path, *args, **kwargs)

    def revoke():
        try:
            revoke_ui_observation(runtime, first["source_id"])
        except BaseException as exc:
            errors.append(exc)

    worker = threading.Thread(target=revoke, name="ui-source-revoker")
    try:
        with patch.object(Path, "unlink", pause_before_blob_unlink):
            worker.start()
            assert entered_unlink.wait(2), "revocation did not reach its post-transaction blob unlink"

            # This is the exact producer path. The same summary has the same hash,
            # so it observes the still-present blob and skips atomic_write before
            # inserting a second live source row.
            _persist_source_and_packet(runtime, second, summary, _packet("packet-second", second))

            allow_unlink.set()
            worker.join(2)
            assert not worker.is_alive(), "revocation worker did not finish"

        assert not errors, f"revocation raised unexpectedly: {errors!r}"
        # A live source must always retain a readable content-addressed blob.
        # Current implementation can delete it after the second source commits.
        assert store.one("SELECT deleted FROM sources WHERE id=?", (second["source_id"],))["deleted"] == 0
        assert store.read_source(second) == summary
    finally:
        allow_unlink.set()
        if worker.is_alive():
            worker.join(2)
        store.close()
