"""Race regression: A5 source publication and consent-revocation unlink serialize.

This exercises the real SQLite Store and the Perception-owned A5 producer.
A tracking RLock makes the producer's lock attempt observable, so the test
proves ordering without relying on scheduler timing or a sleep-based race.
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
    producer_lock_attempted = threading.Event()
    producer_blob_check = threading.Event()
    producer_done = threading.Event()
    results = {}
    errors = []

    _persist_source_and_packet(runtime, first, summary, _packet("packet-first", first))
    assert blob.is_file()

    original_mutex = store.mutex
    original_unlink = Path.unlink
    original_exists = Path.exists

    class TrackingRLock:
        """Expose the producer's lock attempt while preserving RLock behavior."""

        def acquire(self, *args, **kwargs):
            if threading.current_thread().name == "a5-ui-source-producer":
                producer_lock_attempted.set()
            return original_mutex.acquire(*args, **kwargs)

        def release(self):
            return original_mutex.release()

        def __enter__(self):
            self.acquire()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.release()
            return False

    def pause_before_blob_unlink(path, *args, **kwargs):
        if path == blob:
            unlink_entered.set()
            if not allow_unlink.wait(5):
                raise TimeoutError("test did not release the revocation unlink")
        return original_unlink(path, *args, **kwargs)

    def observe_producer_blob_check(path, *args, **kwargs):
        if path == blob and threading.current_thread().name == "a5-ui-source-producer":
            producer_blob_check.set()
        return original_exists(path, *args, **kwargs)

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
    store.mutex = TrackingRLock()
    try:
        with (
            patch.object(Path, "exists", observe_producer_blob_check),
            patch.object(Path, "unlink", pause_before_blob_unlink),
        ):
            revoker.start()
            assert unlink_entered.wait(2), "revocation did not reach the blob unlink"

            # The revoker still owns the underlying RLock. Wait until the
            # producer demonstrably attempts that same lock, then prove it has
            # not reached blob.exists() or completed its publication.
            producer.start()
            assert producer_started.wait(2), "A5 producer thread did not start"
            assert producer_lock_attempted.wait(2), "A5 producer did not request the Store lock"
            assert not producer_blob_check.is_set(), (
                "A5 producer checked blob existence before acquiring the shared Store lock"
            )
            assert not producer_done.is_set(), (
                "A5 producer completed while revocation still owned the Store lock"
            )

            allow_unlink.set()
            assert producer_blob_check.wait(2), "A5 producer did not resume after revocation"
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
        store.mutex = original_mutex
        store.close()
