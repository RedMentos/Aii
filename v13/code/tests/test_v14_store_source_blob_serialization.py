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


def test_staged_store_read_open_is_linearized_with_revocation(tmp_path):
    """An authorized reader opens its blob before a concurrent forget can unlink."""
    import importlib.util
    import os
    import shutil
    import subprocess
    import sys
    import textwrap

    code_dir = Path(__file__).resolve().parents[1]
    builder_path = code_dir / "scripts" / "source_lifecycle_lock_integration_candidate.py"
    spec = importlib.util.spec_from_file_location("source_lifecycle_read_candidate", builder_path)
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    replacements = builder.build_sources(code_dir / "v13")

    runtime_root = tmp_path / "runtime"
    shutil.copytree(code_dir / "v13", runtime_root / "v13",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name, payload in replacements.items():
        (runtime_root / "v13" / name).write_bytes(payload)

    child = textwrap.dedent(
        r'''
        import os
        import sys
        import threading
        from pathlib import Path
        from unittest.mock import patch

        from v13.store import Store
        from v13.source_lifecycle_candidate import cleanup_unreferenced

        root = Path(sys.argv[1])
        home = root / "home"
        (home / "data" / "db").mkdir(parents=True)
        (home / "data" / "blobs").mkdir(parents=True)
        store = Store(home)
        summary = "source payload survives a concurrent forget after open"
        ref = store.source(summary)
        blob = home / "data" / "blobs" / ref["sha256"]

        open_entered = threading.Event()
        allow_open = threading.Event()
        file_opened = threading.Event()
        revoker_lock_attempted = threading.Event()
        revocation_done = threading.Event()
        errors = []
        result = {}
        original_mutex = store.mutex
        original_open = os.open
        original_fdopen = os.fdopen

        class TrackingRLock:
            def acquire(self, *args, **kwargs):
                if threading.current_thread().name == "revoker":
                    revoker_lock_attempted.set()
                return original_mutex.acquire(*args, **kwargs)
            def release(self):
                return original_mutex.release()
            def __enter__(self):
                self.acquire()
                return self
            def __exit__(self, exc_type, exc_value, traceback):
                self.release()
                return False
            def __getattr__(self, name):
                return getattr(original_mutex, name)

        class WaitForRevocation:
            def __init__(self, file):
                self.file = file
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_value, traceback):
                return self.file.__exit__(exc_type, exc_value, traceback)
            def read(self, *args, **kwargs):
                file_opened.set()
                if not revocation_done.wait(5):
                    raise TimeoutError("revocation did not unlink before read")
                return self.file.read(*args, **kwargs)
            def __getattr__(self, name):
                return getattr(self.file, name)

        def pause_blob_open(path, flags, *args, **kwargs):
            if path == ref["sha256"] and threading.current_thread().name == "reader":
                open_entered.set()
                if not allow_open.wait(5):
                    raise TimeoutError("test did not release the reader open")
            return original_open(path, flags, *args, **kwargs)

        def pause_read_until_revocation(fd, mode="r", *args, **kwargs):
            file = original_fdopen(fd, mode, *args, **kwargs)
            if threading.current_thread().name == "reader":
                return WaitForRevocation(file)
            return file

        def read():
            try:
                result["text"] = store.read_source(ref)
            except BaseException as exc:
                errors.append(("reader", repr(exc)))

        def revoke():
            try:
                with store.tx() as conn:
                    conn.execute("UPDATE sources SET deleted=1 WHERE id=?", (ref["source_id"],))
                result["cleanup"] = cleanup_unreferenced(store, ref["source_id"])
            except BaseException as exc:
                errors.append(("revoker", repr(exc)))
            finally:
                revocation_done.set()

        store.mutex = TrackingRLock()
        reader = threading.Thread(target=read, name="reader")
        revoker = threading.Thread(target=revoke, name="revoker")
        try:
            with patch.object(os, "open", pause_blob_open), patch.object(os, "fdopen", pause_read_until_revocation):
                reader.start()
                assert open_entered.wait(5), "reader did not reach blob open"
                revoker.start()
                assert revoker_lock_attempted.wait(5), "revoker did not request Store lock"
                assert not revocation_done.is_set(), "revocation passed while reader held Store lock"
                allow_open.set()
                assert file_opened.wait(5), "reader did not retain the opened file descriptor"
                assert revocation_done.wait(5), "revocation did not finish after FD acquisition"
                assert not blob.exists(), "revocation did not unlink the blob before read"
                reader.join(5)
                revoker.join(5)
            assert not reader.is_alive() and not revoker.is_alive(), "workers did not finish"
            assert not errors, f"concurrent read/revoke raised: {errors!r}"
            assert result["text"] == summary, "opened descriptor did not survive unlink"
            assert result["cleanup"] == "REMOVED"

            denied = store.source("already revoked source")
            with store.tx() as conn:
                conn.execute("UPDATE sources SET deleted=1 WHERE id=?", (denied["source_id"],))
            cleanup_unreferenced(store, denied["source_id"])
            try:
                store.read_source(denied)
            except ValueError:
                pass
            else:
                raise AssertionError("a read started after revocation returned source bytes")
        finally:
            allow_open.set()
            if reader.is_alive():
                reader.join(5)
            if revoker.is_alive():
                revoker.join(5)
            store.mutex = original_mutex
            store.close()
        '''
    )
    result = subprocess.run(
        [sys.executable, "-c", child, str(tmp_path)],
        env={**os.environ, "PYTHONPATH": str(runtime_root), "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, (
        f"staged Store read/revoke race failed: {result.stdout}\n{result.stderr}"
    )
