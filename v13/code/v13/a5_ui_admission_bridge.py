"""A5 UI observation ingress with a source-bound, revocable OS grant lease.

This is a Runtime-side contract, not an Android capture implementation. The
trusted companion must supply an OS-issued observe_ui receipt and a provider
whose guard serializes with revocation. No screenshot, UI text, node tree,
package name, or notification content is accepted or persisted here.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
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
MAX_UI_CONTEXT_PACKETS = 64
MAX_UI_CONTEXT_PACKETS_PER_SOURCE = 8



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



def _cached_ui_packet_source_id(item):
    if type(item) is not dict:
        return None
    source_ref = item.get("source_ref")
    if type(source_ref) is not dict:
        return None
    source_id = source_ref.get("source_id")
    return source_id if type(source_id) is str and source_id else None


def _cache_ui_context_packet(cache, percept_packet, source_id):
    """Append one source-bound packet while keeping frame history strictly bounded."""
    if type(cache) is not dict:
        raise ValueError("Runtime A5 UI cache has an invalid type")
    if type(source_id) is not str or not source_id:
        raise ValueError("UI packet source id is required")
    packet_id = percept_packet.get("packet_id") if type(percept_packet) is dict else None
    if type(packet_id) is not str or not packet_id:
        raise ValueError("UI PerceptPacket id is required")
    if _cached_ui_packet_source_id(percept_packet) != source_id:
        raise PermissionError("UI PerceptPacket source binding does not match its lease")
    cache_key = (source_id, packet_id)
    if cache_key in cache:
        raise ValueError("duplicate UI PerceptPacket id for this source")
    cache[cache_key] = percept_packet
    source_keys = [
        key for key, item in cache.items()
        if key == source_id or _cached_ui_packet_source_id(item) == source_id
    ]
    while len(source_keys) > MAX_UI_CONTEXT_PACKETS_PER_SOURCE:
        cache.pop(source_keys.pop(0), None)
    while len(cache) > MAX_UI_CONTEXT_PACKETS:
        cache.pop(next(iter(cache)))
    return cache_key


def _clear_cached_ui_packets(cache, source_id):
    """Remove every legacy or multi-frame packet derived from one revoked source."""
    if type(cache) is not dict:
        return 0
    stale = [
        key for key, item in cache.items()
        if key == source_id or _cached_ui_packet_source_id(item) == source_id
    ]
    for key in stale:
        cache.pop(key, None)
    return len(stale)


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

    def active_for(self, runtime, generation_id):
        active_event = getattr(runtime, "turn_event", None)
        cancel_event = getattr(runtime, "cancel_event", None)
        is_set = getattr(cancel_event, "is_set", None)
        return bool(
            self._token is _UI_LEASE_TOKEN
            and self._active is True
            and self._thread_id == threading.get_ident()
            and self.runtime is runtime
            and self.generation_id == generation_id
            and isinstance(active_event, dict)
            and active_event.get("brain_generation_id") == generation_id
            and getattr(runtime, "current", None) == "turn"
            and callable(is_set)
            and not is_set()
        )

    def matches(self, runtime, observation, generation_id):
        return bool(
            self.active_for(runtime, generation_id)
            and self.source_id == observation.get("source_id")
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


def _request_ui_revoke_cancel(runtime, generation_id):
    """Non-blocking first phase: cancel only the turn that owns this lease."""
    active = getattr(runtime, "turn_event", None)
    if (not isinstance(active, dict)
            or active.get("brain_generation_id") != generation_id
            or getattr(runtime, "current", None) != "turn"):
        return False
    cancel_event = getattr(runtime, "cancel_event", None)
    setter = getattr(cancel_event, "set", None)
    if not callable(setter):
        return False
    # Event.set() is deliberately the only operation here: no Runtime lock,
    # Store transaction, provider guard, logging or subscription mutation.
    setter()
    return True


@contextmanager
def ui_observation_lease(runtime, observation, generation_id, consent_check,
                         consent_guard, revocation_subscribe, revoke_callback=None):
    """Hold the provider grant across UI consumption with two-phase revocation.

    The provider must register both callbacks before returning:
      * on_revoke_requested: called BEFORE it waits for/acquires consent_guard;
        this callback only sets Runtime.cancel_event for this generation.
      * on_revoked: called AFTER releasing consent_guard AND its subscription
        registry lock; this callback tombstones the source and clears caches.

    consent_guard shares its synchronization primitive with revocation and
    yields literal True only while the OS grant is active. The lease stays held
    through downstream reads/generation; pre-lock cancellation lets C3 exit
    before the provider can acquire the guard and run post-lock cleanup.
    """
    observation = validate_ui_observation(observation)
    if type(generation_id) is not str or not generation_id:
        raise ValueError("active Runtime generation required")
    if getattr(runtime, "current", None) != "turn":
        raise PermissionError("A5 UI lease requires an active Runtime turn")
    cancel_event = getattr(runtime, "cancel_event", None)
    if not callable(getattr(cancel_event, "set", None)):
        raise PermissionError("Runtime cancellation event is required for revocable UI")
    if not callable(consent_check) or not callable(consent_guard) or not callable(revocation_subscribe):
        raise PermissionError("current check, linearizable guard and two-phase revocation subscription are required")
    args = _provider_args(observation)
    try:
        current = consent_check(*args)
    except Exception:
        current = False
    if current is not True:
        raise PermissionError("current OS observe_ui grant is not active")

    def request_cancel():
        return _request_ui_revoke_cancel(runtime, generation_id)

    def cleanup():
        return (revoke_callback or (lambda sid: revoke_ui_observation(runtime, sid)))(observation["source_id"])

    try:
        unsubscribe = revocation_subscribe(
            observation["source_id"], observation["consent_receipt_ref"],
            observation["capture_session_id"], request_cancel, cleanup,
        )
    except Exception:
        raise PermissionError("two-phase UI revocation subscription is unavailable") from None
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
    """Persist source bytes and their rows under the Store's shared blob lock.

    Store.tx() takes the same re-entrant mutex. Keeping the outer lock across
    blob existence/write and the SQL commit prevents a concurrent revocation
    from unlinking a blob after a new source has reused it but before that
    source row becomes visible to the revoker's reference count.
    """
    store = runtime.store
    raw = summary.encode("utf-8")
    blob = Path(store.home) / "data/blobs" / source_ref["sha256"]
    with store.mutex:
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
    """Tombstone one A5 UI source and remove all derived packet/cache references."""
    if type(source_id) is not str or not source_id:
        raise ValueError("UI source id required")
    subscriptions = getattr(runtime, "_a5_ui_unsubscribe", None)
    unsubscribe = subscriptions.pop(source_id, None) if type(subscriptions) is dict else None
    cache = getattr(runtime, "_a5_ui_context_cache", None)
    cache_cleared = _clear_cached_ui_packets(cache, source_id) > 0
    store = getattr(runtime, "store", None)
    if store is None:
        if callable(unsubscribe):
            unsubscribe()
        return {
            "source_tombstoned": False, "packets_deleted": 0,
            "cache_cleared": cache_cleared, "blob_removed": False,
        }
    blob_hash = None
    source_tombstoned = False
    active = 1
    deleted_ids = []
    blob_removed = False
    try:
        # The same RLock protects producers' blob existence/write + row insert.
        # Hold it until the post-tombstone refcount check and unlink are complete.
        with store.mutex:
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
                            payload = json.loads(packet_row["payload"])
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
            if blob_hash and active == 0:
                blob = Path(store.home) / "data/blobs" / blob_hash
                try:
                    blob.unlink(missing_ok=True)
                    blob_removed = not blob.exists()
                except OSError:
                    pass
    except BaseException:
        if callable(unsubscribe) and type(subscriptions) is dict:
            subscriptions[source_id] = unsubscribe
        raise
    finally:
        # Cache revocation is independent of Store cleanup. A missing/failed
        # Store must never leave a derived packet visible to a later consumer.
        cache_cleared = (_clear_cached_ui_packets(cache, source_id) > 0) or cache_cleared
    if callable(unsubscribe):
        unsubscribe()
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

    def cache_packet(self, percept_packet, consent_lease):
        """Append one source-bound frame packet under its active observation lease."""
        event = getattr(self.runtime, "turn_event", None)
        generation_id = event.get("brain_generation_id") if isinstance(event, dict) else None
        if (type(consent_lease) is not UIObservationLease
                or not consent_lease.active_for(self.runtime, generation_id)):
            raise PermissionError("active UI observation lease is required for packet caching")
        source_id = _cached_ui_packet_source_id(percept_packet)
        if source_id != consent_lease.source_id:
            raise PermissionError("UI packet source is not bound to the active lease")
        if (percept_packet.get("event_id") != event.get("event_id")
                or percept_packet.get("brain_generation_id") != generation_id
                or percept_packet.get("modality") != "ui"):
            raise ValueError("UI PerceptPacket event/generation binding mismatch")
        if (percept_packet.get("raw_capture_persisted") is not False
                or percept_packet.get("derived_packet_persisted") is not False
                or percept_packet.get("action_authority") is not False
                or percept_packet.get("learning_authority") is not False
                or percept_packet.get("truth_authority") != 0):
            raise PermissionError("UI PerceptPacket attempted persistence or authority escalation")
        return _cache_ui_context_packet(
            self.runtime._a5_ui_context_cache, percept_packet, source_id,
        )

    def context(self, event_id, grants):
        """Return FINAL UI packets only while their matching lease(s) are held."""
        if type(event_id) is not str or not event_id:
            raise ValueError("event id required")
        if type(grants) is UIObservationLease:
            grants = (grants,)
        elif type(grants) not in (tuple, list):
            raise PermissionError("active UI observation lease is required for context reads")
        if not grants:
            raise PermissionError("at least one active UI observation lease is required")
        event = getattr(self.runtime, "turn_event", None)
        generation_id = event.get("brain_generation_id") if isinstance(event, dict) else None
        subscriptions = getattr(self.runtime, "_a5_ui_unsubscribe", None)
        if type(subscriptions) is not dict:
            raise PermissionError("UI observation subscriptions are unavailable")
        allowed_sources = set()
        for grant in grants:
            if (type(grant) is not UIObservationLease
                    or not grant.active_for(self.runtime, generation_id)
                    or grant.source_id not in subscriptions):
                raise PermissionError("UI context lease is stale, revoked, or not bound to this turn")
            allowed_sources.add(grant.source_id)
        packets = []
        for item in self.runtime._a5_ui_context_cache.values():
            # PerceptPacket stores identity in source_ref; never infer a top-level source_id.
            source_ref = item.get("source_ref")
            if (
                isinstance(source_ref, dict)
                and source_ref.get("source_id") in allowed_sources
                and item.get("event_id") == event_id
                and item.get("brain_generation_id") == generation_id
                and item.get("modality") == "ui"
                and item.get("finality") == "FINAL"
            ):
                packets.append(item)
        return tuple(packets)

    def revoke(self, source_id):
        try:
            return revoke_ui_observation(self.runtime, source_id)
        finally:
            # Direct Core callers use this adapter rather than the scoped
            # Perception helper. Clear frame-difference state on every revoke,
            # including Store cleanup failures and the no-Store fast path.
            from .vision_temporal_attention import reset_runtime_ui_temporal_attention
            reset_runtime_ui_temporal_attention(self.runtime, source_id)

    def close(self):
        """Clear local UI state after provider revocation and Runtime worker exit.

        The OS provider must revoke its session first (pre-lock cancel, then
        post-lock cleanup). If a turn is still active, request cancellation but
        fail closed: the caller must wait for worker exit and retry before Store
        shutdown. This method does not revoke an Android OS permission itself.
        """
        active = getattr(self.runtime, "turn_event", None)
        cancel_event = getattr(self.runtime, "cancel_event", None)
        if (isinstance(active, dict)
                and type(active.get("brain_generation_id")) is str
                and getattr(self.runtime, "current", None) == "turn"):
            setter = getattr(cancel_event, "set", None)
            if callable(setter):
                setter()
            raise RuntimeError("A5 UI close requires provider revocation and Runtime turn exit")
        try:
            return tuple(self.revoke(source_id) for source_id in list(self.runtime._a5_ui_unsubscribe))
        finally:
            # Clear orphaned descriptors too, even if no subscription entry
            # remains or one source's Store cleanup raises.
            from .vision_temporal_attention import reset_runtime_ui_temporal_attention
            reset_runtime_ui_temporal_attention(self.runtime)
