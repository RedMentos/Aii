"""A5 UI observation ingress with a source-bound, revocable OS grant lease.

This is a Runtime-side contract, not an Android capture implementation. The
trusted companion must supply an OS-issued observe_ui receipt and a provider
whose guard serializes with revocation. No screenshot, UI text, node tree,
package name, or notification content is accepted or persisted here.
"""
from __future__ import annotations

from contextlib import contextmanager
import re
import threading
from pathlib import Path

from . import attention as attctl
from .common import atomic_write, digest, dumps, now
from .contracts import packet, validate
from .percept_admission import Percept, admit

_SCHEMA = "v14.a5.ui-observation/1"
_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
_RECEIPT = re.compile(r"[A-Za-z0-9._:-]{1,128}\Z")
_METHODS = {
    "APP_INTENT", "CONTENT_PROVIDER", "NOTIFICATION_LISTENER",
    "ACCESSIBILITY_ASSISTIVE", "MEDIA_PROJECTION",
}
_EVENT_BY_METHOD = {
    "APP_INTENT": {"APP_INTENT_RESULT"},
    "CONTENT_PROVIDER": {"CONTENT_PROVIDER_UPDATE"},
    "NOTIFICATION_LISTENER": {"NOTIFICATION_POSTED", "NOTIFICATION_REMOVED"},
    "ACCESSIBILITY_ASSISTIVE": {
        "WINDOW_STATE_CHANGED", "WINDOW_CONTENT_CHANGED", "VIEW_CLICKED", "VIEW_FOCUSED",
    },
    "MEDIA_PROJECTION": {"SCREEN_FRAME_AVAILABLE"},
}
_SCOPE_BY_METHOD = {
    "APP_INTENT": {"APP_DATA"},
    "CONTENT_PROVIDER": {"APP_DATA"},
    "NOTIFICATION_LISTENER": {"NOTIFICATION"},
    "ACCESSIBILITY_ASSISTIVE": {"ACCESSIBILITY_TREE"},
    "MEDIA_PROJECTION": {"FULL_DISPLAY", "APP_WINDOW"},
}
_REQUIRED = {
    "schema", "modality", "source_id", "capture_session_id", "consent_receipt_ref",
    "capture_method", "capture_scope", "api_level", "clock", "event_kind", "start_ms", "end_ms",
    "finality", "action_authority", "learning_authority", "raw_capture_persisted",
}
_OPTIONAL = {"accessibility_purpose"}
_UI_LEASE_TOKEN = object()
_RUNTIME_CACHE_INIT_LOCK = threading.Lock()


def validate_ui_observation(observation: dict) -> dict:
    """Validate a metadata-only UI event and reject raw UI content fields."""
    if type(observation) is not dict:
        raise ValueError("UI observation must be an object")
    keys = set(observation)
    if not _REQUIRED.issubset(keys) or keys - (_REQUIRED | _OPTIONAL):
        raise ValueError("UI observation fields are incomplete or contain raw/untrusted content")
    if observation.get("schema") != _SCHEMA or observation.get("modality") != "ui":
        raise ValueError("UI observation schema/modality mismatch")
    for key in ("source_id", "capture_session_id"):
        value = observation.get(key)
        if type(value) is not str or not _ID.fullmatch(value):
            raise ValueError("invalid UI observation identity: " + key)
    receipt = observation.get("consent_receipt_ref")
    if type(receipt) is not str or not _RECEIPT.fullmatch(receipt):
        raise PermissionError("opaque current observe_ui receipt required")
    method = observation.get("capture_method")
    scope = observation.get("capture_scope")
    event_kind = observation.get("event_kind")
    if type(method) is not str or type(scope) is not str or type(event_kind) is not str:
        raise ValueError("UI capture method/scope/event must be strings")
    if method not in _METHODS or scope not in _SCOPE_BY_METHOD[method]:
        raise ValueError("unsupported UI capture method/scope")
    if event_kind not in _EVENT_BY_METHOD[method]:
        raise ValueError("UI event kind does not match capture method")
    api = observation.get("api_level")
    if type(api) is not int or not 1 <= api <= 99:
        raise ValueError("invalid Android API level")
    if observation.get("clock") != "ELAPSED_REALTIME":
        raise ValueError("UI observation timestamps must use Android elapsed realtime")
    if method == "NOTIFICATION_LISTENER" and api < 18:
        raise ValueError("NotificationListenerService requires API 18+")
    if method == "MEDIA_PROJECTION":
        if api < 21:
            raise ValueError("MediaProjection requires API 21+")
        if scope == "APP_WINDOW" and api < 34:
            raise ValueError("app-window MediaProjection is unavailable before API 34")
    if method == "ACCESSIBILITY_ASSISTIVE":
        if api < 4 or observation.get("accessibility_purpose") != "DISABILITY_ASSISTANCE":
            raise PermissionError("AccessibilityService is accepted only for a declared disability-assistance use case")
    elif "accessibility_purpose" in observation:
        raise ValueError("accessibility_purpose is only valid for ACCESSIBILITY_ASSISTIVE")
    start, end = observation.get("start_ms"), observation.get("end_ms")
    if (type(start) is not int or type(end) is not int or start < 0 or end <= start
            or end - start > 5000):
        raise ValueError("UI observation interval must be a positive bounded monotonic window")
    if type(observation.get("finality")) is not str or observation.get("finality") not in {"PROVISIONAL", "FINAL"}:
        raise ValueError("invalid UI observation finality")
    if (observation.get("action_authority") is not False
            or observation.get("learning_authority") is not False
            or observation.get("raw_capture_persisted") is not False):
        raise PermissionError("UI observation cannot grant action/learning authority or persist raw capture")
    return dict(observation)


def _summary(observation: dict) -> str:
    """A deliberately content-free event summary for the A-plane and Store."""
    return (
        "ui event=" + observation["event_kind"]
        + " method=" + observation["capture_method"]
        + " scope=" + observation["capture_scope"]
        + " api=" + str(observation["api_level"])
        + " clock=ELAPSED_REALTIME"
        + " interval_ms=" + str(observation["end_ms"] - observation["start_ms"])
    )


def _provider_args(observation: dict) -> tuple:
    return (
        observation["source_id"], observation["consent_receipt_ref"],
        observation["capture_session_id"], "observe_ui", observation["capture_method"],
        observation["capture_scope"], observation["api_level"],
    )


class UIObservationLease:
    """Ephemeral thread-bound handle for one OS-issued UI observation grant."""
    __slots__ = (
        "_token", "runtime", "source_id", "generation_id", "receipt",
        "capture_session_id", "capture_method", "capture_scope", "api_level",
        "_active", "_thread_id",
    )

    def __init__(self, runtime, observation, generation_id, *, _token=None):
        if _token is not _UI_LEASE_TOKEN:
            raise PermissionError("UIObservationLease must be created by ui_observation_lease")
        self._token = _token
        self.runtime = runtime
        self.source_id = observation["source_id"]
        self.generation_id = generation_id
        self.receipt = observation["consent_receipt_ref"]
        self.capture_session_id = observation["capture_session_id"]
        self.capture_method = observation["capture_method"]
        self.capture_scope = observation["capture_scope"]
        self.api_level = observation["api_level"]
        self._active = True
        self._thread_id = threading.get_ident()

    @property
    def active(self):
        return self._active is True

    def matches(self, runtime, observation, generation_id):
        return bool(
            self._token is _UI_LEASE_TOKEN
            and self._active is True
            and self._thread_id == threading.get_ident()
            and self.runtime is runtime
            and self.source_id == observation.get("source_id")
            and self.generation_id == generation_id
            and self.receipt == observation.get("consent_receipt_ref")
            and self.capture_session_id == observation.get("capture_session_id")
            and self.capture_method == observation.get("capture_method")
            and self.capture_scope == observation.get("capture_scope")
            and self.api_level == observation.get("api_level")
        )

    def __repr__(self):
        return f"<UIObservationLease active={self.active}>"

    def __reduce__(self):
        raise TypeError("UIObservationLease is ephemeral and cannot be serialized")

    def __copy__(self):
        raise TypeError("UIObservationLease cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("UIObservationLease cannot be copied")


@contextmanager
def ui_observation_lease(runtime, observation, generation_id, consent_check,
                         consent_guard, revocation_subscribe, revoke_callback=None):
    """Hold the provider's revocation lock for capture/admission/context use.

    consent_guard must share its synchronization primitive with revocation and
    yield literal True only while the OS grant is active. The revocation
    subscriber MUST deliver its callback after releasing that same guard;
    the callback tombstones the source and clears Runtime's UI cache.
    """
    observation = validate_ui_observation(observation)
    if type(generation_id) is not str or not generation_id:
        raise ValueError("active Runtime generation required")
    if not callable(consent_check) or not callable(consent_guard) or not callable(revocation_subscribe):
        raise PermissionError("current check, linearizable guard and revocation subscription are required")
    args = _provider_args(observation)
    try:
        current = consent_check(*args)
    except Exception:
        current = False
    if current is not True:
        raise PermissionError("current OS observe_ui grant is not active")
    try:
        unsubscribe = revocation_subscribe(
            observation["source_id"], observation["consent_receipt_ref"],
            observation["capture_session_id"],
            lambda: (revoke_callback or (lambda sid: revoke_ui_observation(runtime, sid)))(observation["source_id"]),
        )
    except Exception:
        raise PermissionError("UI revocation subscription is unavailable") from None
    if not callable(unsubscribe):
        raise PermissionError("UI revocation subscription must return an unsubscribe callback")
    acquired = False
    try:
        manager = consent_guard(*args)
        if not hasattr(manager, "__enter__") or not hasattr(manager, "__exit__"):
            raise PermissionError("UI consent guard must return a context manager")
        with manager as active:
            if active is not True:
                raise PermissionError("UI observation grant was revoked before lease acquisition")
            subscriptions = getattr(runtime, "_a5_ui_unsubscribe", None)
            if subscriptions is None:
                subscriptions = {}
                runtime._a5_ui_unsubscribe = subscriptions
            if type(subscriptions) is not dict or observation["source_id"] in subscriptions:
                raise ValueError("duplicate or invalid UI revocation subscription")
            subscriptions[observation["source_id"]] = unsubscribe
            acquired = True
            lease = UIObservationLease(runtime, observation, generation_id, _token=_UI_LEASE_TOKEN)
            try:
                yield lease
            finally:
                lease._active = False
    finally:
        # Successful subscriptions remain live after the Runtime lease exits.
        # They are removed only by provider revocation or Runtime shutdown.
        if not acquired:
            unsubscribe()


def _persist_source_and_packet(runtime, source_ref, summary, percept_packet):
    """Atomically persist the minimal source record and PerceptPacket."""
    store = runtime.store
    raw = summary.encode("utf-8")
    blob = Path(store.home) / "data/blobs" / source_ref["sha256"]
    if not blob.exists():
        atomic_write(blob, raw)
    try:
        with store.tx() as connection:
            if connection.execute("SELECT 1 FROM sources WHERE id=?", (source_ref["source_id"],)).fetchone():
                raise ValueError("duplicate UI source id")
            connection.execute(
                "INSERT INTO sources VALUES (?,?,?,?,?,?,0)",
                (source_ref["source_id"], source_ref["sha256"], "A5_UI_EVENT",
                 len(raw), len(summary), now()),
            )
            connection.execute(
                "INSERT INTO packets VALUES (?,?,?,?,?,?)",
                (percept_packet["packet_id"], "PerceptPacket", percept_packet["event_id"],
                 percept_packet["brain_generation_id"], dumps(percept_packet), now()),
            )
    except BaseException:
        referenced = store.one("SELECT 1 FROM sources WHERE hash=? AND deleted=0 LIMIT 1", (source_ref["sha256"],))
        if not referenced:
            try:
                blob.unlink(missing_ok=True)
            except OSError:
                pass
        raise


def consume_ui_observation(runtime, observation, *, consent_lease: UIObservationLease,
                           goal="", token_budget=512, priority=0):
    """Persist one metadata-only A5 packet, drive A4 and return bounded admission.

    The caller must keep the outer UIObservationLease open through every later
    consumer that can read this source (including C3 generation).
    """
    observation = validate_ui_observation(observation)
    event = getattr(runtime, "turn_event", None)
    if not isinstance(event, dict):
        raise ValueError("UI observations must attach to an active Runtime turn")
    event_id = event.get("event_id")
    generation_id = event.get("brain_generation_id")
    if type(event_id) is not str or not event_id or type(generation_id) is not str or not generation_id:
        raise ValueError("active Runtime turn identity is incomplete")
    if not isinstance(consent_lease, UIObservationLease) or not consent_lease.matches(
        runtime, observation, generation_id
    ):
        raise PermissionError("a live source/generation/receipt-bound UI lease is required")
    if type(priority) is not int or not -100 <= priority <= 100:
        raise ValueError("invalid UI admission priority")
    if type(token_budget) is not int or token_budget < 0:
        raise ValueError("invalid UI token budget")
    if type(goal) is not str:
        raise ValueError("UI attention goal must be text")

    summary = _summary(observation)
    source_ref = {
        "source_id": observation["source_id"],
        "sha256": digest(summary.encode("utf-8")),
        "char_start": 0,
        "char_end": len(summary),
        "modality": "ui",
    }
    segment = {
        "text": summary,
        "source_ref": source_ref,
        "start_ms": observation["start_ms"],
        "end_ms": observation["end_ms"],
        "clock": observation["clock"],
        "finality": observation["finality"],
        "event_kind": observation["event_kind"],
        "capture_method": observation["capture_method"],
        "capture_scope": observation["capture_scope"],
        "consent_receipt_ref": observation["consent_receipt_ref"],
        "action_authority": False,
        "learning_authority": False,
        "raw_capture_persisted": False,
    }
    percept_packet = packet(
        "PerceptPacket", "A5_UI", event_id, generation_id, [source_ref],
        source_ref=source_ref, segments=[segment], modality="ui",
        capture_session_id=observation["capture_session_id"],
        consent_receipt_ref=observation["consent_receipt_ref"],
        capture_method=observation["capture_method"],
        capture_scope=observation["capture_scope"], clock=observation["clock"],
        finality=observation["finality"],
        action_authority=False, learning_authority=False,
    )
    validate("PerceptPacket", percept_packet)
    _persist_source_and_packet(runtime, source_ref, summary, percept_packet)

    cache = getattr(runtime, "_a5_ui_context_cache", None)
    if cache is None:
        with _RUNTIME_CACHE_INIT_LOCK:
            cache = getattr(runtime, "_a5_ui_context_cache", None)
            if cache is None:
                cache = {}
                runtime._a5_ui_context_cache = cache
    if type(cache) is not dict:
        raise ValueError("Runtime A5 UI cache has an invalid type")
    cache[observation["source_id"]] = percept_packet
    while len(cache) > 64:
        cache.pop(next(iter(cache)))

    attention = attctl.controller(runtime)
    a4 = attention.perceive(
        event_id, [segment], goal=goal,
        file_requests=observation["finality"] == "FINAL",
    )
    candidate = Percept(
        observation["source_id"], "ui", observation["start_ms"], observation["end_ms"],
        summary, True, observation["finality"] == "FINAL", priority,
    )
    admission = admit((candidate,), token_budget)
    return {
        "status": "WIRED_SYNTHETIC",
        "packet": percept_packet,
        "source_ref": source_ref,
        "a4": a4,
        "admission": admission,
        "raw_capture_persisted": False,
        "action_authority": False,
        "learning_authority": False,
    }


def ui_to_admission(observation, *, runtime, consent_lease, goal="", token_budget=512, priority=0):
    """Strict lease-bound Runtime consumer entrypoint."""
    return consume_ui_observation(
        runtime, observation, consent_lease=consent_lease,
        goal=goal, token_budget=token_budget, priority=priority,
    )


def revoke_ui_observation(runtime, source_id):
    """Tombstone one A5 UI source and remove every derived packet/cache reference."""
    if type(source_id) is not str or not source_id:
        raise ValueError("UI source id required")
    subscriptions = getattr(runtime, "_a5_ui_unsubscribe", None)
    unsubscribe = subscriptions.pop(source_id, None) if type(subscriptions) is dict else None
    cache = getattr(runtime, "_a5_ui_context_cache", None)
    store = getattr(runtime, "store", None)
    if store is None:
        if callable(unsubscribe):
            unsubscribe()
        return {"source_tombstoned": False, "packets_deleted": 0, "cache_cleared": False, "blob_removed": False}
    blob_hash = None
    source_tombstoned = False
    active = 1
    deleted_ids = []
    try:
        with store.tx() as connection:
            row = connection.execute(
                "SELECT hash,deleted FROM sources WHERE id=? AND kind='A5_UI_EVENT'",
                (source_id,),
            ).fetchone()
            if row:
                blob_hash = row["hash"]
                source_tombstoned = row["deleted"] == 0

                def contains_source(value):
                    if isinstance(value, dict):
                        if value.get("source_id") == source_id:
                            return True
                        return any(contains_source(child) for child in value.values())
                    if isinstance(value, list):
                        return any(contains_source(child) for child in value)
                    return False

                for packet_row in connection.execute("SELECT id,payload FROM packets").fetchall():
                    try:
                        payload = __import__("json").loads(packet_row["payload"])
                    except (TypeError, ValueError):
                        continue
                    if contains_source(payload):
                        deleted_ids.append(packet_row["id"])
                for packet_id in set(deleted_ids):
                    connection.execute("DELETE FROM packets WHERE id=?", (packet_id,))
                connection.execute(
                    "UPDATE sources SET deleted=1 WHERE id=? AND kind='A5_UI_EVENT' AND deleted=0",
                    (source_id,),
                )
                active = connection.execute(
                    "SELECT COUNT(*) FROM sources WHERE hash=? AND deleted=0",
                    (blob_hash,),
                ).fetchone()[0]
    except BaseException:
        if callable(unsubscribe) and type(subscriptions) is dict:
            subscriptions[source_id] = unsubscribe
        raise
    cache_cleared = cache.pop(source_id, None) is not None if type(cache) is dict else False
    if callable(unsubscribe):
        unsubscribe()
    blob_removed = False
    if blob_hash and active == 0:
        blob = Path(store.home) / "data/blobs" / blob_hash
        try:
            blob.unlink(missing_ok=True)
            blob_removed = not blob.exists()
        except OSError:
            pass
    return {
        "source_tombstoned": source_tombstoned,
        "packets_deleted": len(set(deleted_ids)),
        "cache_cleared": cache_cleared,
        "blob_removed": blob_removed,
    }


class A5UIRuntimeAdapter:
    """Perception adapter that consumes an existing Runtime/Store/A4 instance."""

    def __init__(self, runtime):
        self.runtime = runtime
        for name in ("_a5_ui_context_cache", "_a5_ui_unsubscribe"):
            value = getattr(runtime, name, None)
            if value is None:
                setattr(runtime, name, {})
            elif type(value) is not dict:
                raise ValueError("Runtime A5 UI state is invalid")

    @contextmanager
    def lease(self, observation, consent_check, consent_guard, revocation_subscribe):
        event = getattr(self.runtime, "turn_event", None)
        if not isinstance(event, dict) or type(event.get("brain_generation_id")) is not str:
            raise ValueError("UI observation requires an active Runtime turn")
        with ui_observation_lease(
            self.runtime, observation, event["brain_generation_id"],
            consent_check, consent_guard, revocation_subscribe,
            revoke_callback=self.revoke,
        ) as grant:
            yield grant

    def ingest(self, observation, grant, goal="", token_budget=512, priority=0):
        return consume_ui_observation(
            self.runtime, observation, consent_lease=grant,
            goal=goal, token_budget=token_budget, priority=priority,
        )

    def context(self, event_id):
        if type(event_id) is not str or not event_id:
            raise ValueError("event id required")
        return tuple(
            packet for packet in self.runtime._a5_ui_context_cache.values()
            if packet.get("event_id") == event_id
            and packet.get("modality") == "ui"
            and packet.get("finality") == "FINAL"
        )

    def revoke(self, source_id):
        return revoke_ui_observation(self.runtime, source_id)

    def close(self):
        """Call before Runtime Store close to revoke every outstanding UI session."""
        return tuple(self.revoke(source_id) for source_id in list(self.runtime._a5_ui_unsubscribe))
