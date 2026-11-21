"""Store source publication must serialize with A5 consent revocation."""
from pathlib import Path
import threading
from unittest.mock import patch

from v13.common import digest
from v13.store import Store
from v13.a5_ui_admission_bridge import _persist_source_and_packet, revoke_ui_observation


def test_store_source_publication_waits_for_a5_revocation_unlink(tmp_path):
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
    source_ref = {
        "source_id": "src_ui_before_generic_publish",
        "sha256": digest(summary.encode("utf-8")),
        "char_start": 0,
        "char_end": len(summary),
        "modality": "ui",
    }
    percept_packet = {
        "packet_id": "packet_ui_before_generic_publish",
        "event_id": "event_ui_blob_race",
        "brain_generation_id": "generation_ui_blob_race",
        "source_ref": source_ref,
    }
    _persist_source_and_packet(runtime, source_ref, summary, percept_packet)
    blob = home / "data" / "blobs" / source_ref["sha256"]
    assert blob.is_file()

    unlink_entered = threading.Event()
    allow_unlink = threading.Event()
    producer_started = threading.Event()
    producer_lock_attempted = threading.Event()
    producer_blob_check = threading.Event()
    producer_done = threading.Event()
    errors = []
    result = {}

    original_mutex = store.mutex
    original_unlink = Path.unlink
    original_exists = Path.exists

    class TrackingRLock:
        """Expose the producer lock attempt while preserving Store RLock behavior."""

        def acquire(self, *args, **kwargs):
            if threading.current_thread().name == "generic-source-producer":
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

    def observe_producer_blob_check(path, *args, **kwargs):
        if path == blob and threading.current_thread().name == "generic-source-producer":
            producer_blob_check.set()
        return original_exists(path, *args, **kwargs)

    def pause_before_unlink(path, *args, **kwargs):
        if path == blob:
            unlink_entered.set()
            if not allow_unlink.wait(5):
                raise TimeoutError("test did not release the revocation unlink")
        return original_unlink(path, *args, **kwargs)

    def revoke():
        try:
            result["revocation"] = revoke_ui_observation(runtime, source_ref["source_id"])
        except BaseException as exc:
            errors.append(("revoke", repr(exc)))

    def publish_generic_source():
        producer_started.set()
        try:
            result["source_ref"] = store.source(summary, kind="USER")
        except BaseException as exc:
            errors.append(("publish", repr(exc)))
        finally:
            producer_done.set()

    revoker = threading.Thread(target=revoke, name="a5-ui-revoker")
    producer = threading.Thread(target=publish_generic_source, name="generic-source-producer")
    store.mutex = TrackingRLock()
    try:
        with patch.object(Path, "exists", observe_producer_blob_check), \
             patch.object(Path, "unlink", pause_before_unlink):
            revoker.start()
            assert unlink_entered.wait(2), "revocation did not reach blob unlink"
            producer.start()
            assert producer_started.wait(2), "generic source producer did not start"
            assert producer_lock_attempted.wait(2), "generic source producer did not request the Store lock"
            assert not producer_blob_check.is_set(), (
                "generic Store.source() checked blob existence before acquiring the shared Store lock"
            )
            assert not producer_done.is_set(), (
                "generic Store.source() completed while revocation still owned the Store lock"
            )
            allow_unlink.set()
            assert producer_blob_check.wait(2), "generic source producer did not resume after revocation"
            revoker.join(2)
            producer.join(2)
            assert not revoker.is_alive(), "revocation worker did not finish"
            assert not producer.is_alive(), "source producer did not finish after unlink"
        assert not errors, f"concurrent source/revoke operation raised: {errors!r}"
        source = result["source_ref"]
        assert store.one(
            "SELECT deleted FROM sources WHERE id=?", (source["source_id"],)
        )["deleted"] == 0
        assert store.read_source(source) == summary
        assert blob.is_file()
        assert result["revocation"]["source_tombstoned"] is True
        assert result["revocation"]["blob_removed"] is True
    finally:
        allow_unlink.set()
        if revoker.is_alive():
            revoker.join(2)
        if producer.is_alive():
            producer.join(2)
        store.mutex = original_mutex
        store.close()
