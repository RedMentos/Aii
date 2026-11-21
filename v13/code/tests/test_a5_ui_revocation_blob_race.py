"""Race regression: A5 source publication and consent-revocation unlink serialize.

This exercises the real SQLite Store and the Perception-owned A5 producer.
The test uses separate threads so the producer can be observed waiting on the
shared Store mutex while revocation is paused at the actual blob unlink.
"""
import threading
from pathlib import Path
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


def test_revoke_unlink_serializes_with_concurrent_a5_shared_source_publication(tmp_path):
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
    unlink_entered = threading.Event()
    allow_unlink = threading.Event()
    producer_started = threading.Event()
    producer_done = threading.Event()
    results = {}
    errors = []

    _persist_source_and_packet(runtime, first, summary, _packet("packet-first", first))
    assert blob.is_file()

    original_unlink = Path.unlink

    def pause_before_blob_unlink(path, *args, **kwargs):
        if path == blob:
            unlink_entered.set()
            if not allow_unlink.wait(5):
                raise TimeoutError("test did not release the revocation unlink")
        return original_unlink(path, *args, **kwargs)

    def revoke():
        try:
            results["revocation"] = revoke_ui_observation(runtime, first["source_id"])
        except BaseException as exc:
            errors.append(("revoke", repr(exc)))

    def publish_second_a5_source():
        producer_started.set()
        try:
            _persist_source_and_packet(
                runtime, second, summary, _packet("packet-second", second)
            )
        except BaseException as exc:
            errors.append(("publish", repr(exc)))
        finally:
            producer_done.set()

    revoker = threading.Thread(target=revoke, name="a5-ui-source-revoker")
    producer = threading.Thread(target=publish_second_a5_source, name="a5-ui-source-producer")
    try:
        with patch.object(Path, "unlink", pause_before_blob_unlink):
            revoker.start()
            assert unlink_entered.wait(2), "revocation did not reach the blob unlink"

            # The revoker must still own Store.mutex here. The A5 producer must
            # block, then recreate the digest blob after the old source is gone.
            producer.start()
            assert producer_started.wait(2), "A5 producer thread did not start"
            assert not producer_done.wait(0.1), (
                "A5 source publication passed the revocation blob critical section"
            )

            allow_unlink.set()
            revoker.join(2)
            producer.join(2)
            assert not revoker.is_alive(), "revocation worker did not finish"
            assert not producer.is_alive(), "A5 producer did not finish after revocation"

        assert not errors, f"concurrent A5 source/revoke operation raised: {errors!r}"
        assert results["revocation"]["source_tombstoned"] is True
        assert results["revocation"]["blob_removed"] is True
        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (first["source_id"],)
        )["deleted"] == 1
        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (second["source_id"],)
        )["deleted"] == 0
        assert store.read_source(second) == summary
        assert blob.is_file(), "new live A5 source must own a readable recreated blob"
    finally:
        allow_unlink.set()
        if revoker.is_alive():
            revoker.join(2)
        if producer.is_alive():
            producer.join(2)
        store.close()
