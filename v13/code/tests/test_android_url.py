import hashlib
import json

import pytest

from v13.android_control import AndroidControlBroker, CAPABILITIES, ControlDenied, _canonical
from v13.android_url import UnsafeAndroidUrl, https_host, validate_https_url


VALID_URLS = (
    "https://example.com",
    "https://example.com/path?q=1#section",
    "https://example.com:443/a",
    "https://xn--bcher-kva.example/",
)
INVALID_URLS = (
    "http://example.com",
    "javascript:alert(1)",
    "intent://example.com/#Intent;scheme=https;end",
    "file:///etc/passwd",
    "https://user:pass@example.com/",
    "https://example.com:444/",
    "https://example.com:/",
    "https://example.com/a b",
    "https://example.com/%zz",
    "https://example.com\\\\@evil.test",
    "https://éxample.com/",
)


@pytest.mark.parametrize("url", VALID_URLS)
def test_valid_https_urls_are_preserved_exactly(url):
    assert validate_https_url(url) == url


@pytest.mark.parametrize("url", INVALID_URLS)
def test_non_https_credential_and_ambiguous_urls_are_rejected(url):
    with pytest.raises(UnsafeAndroidUrl):
        validate_https_url(url)


def test_host_projection_does_not_return_path_query_or_fragment():
    assert https_host("https://Example.com/private/path?token=secret#frag") == "example.com"


def test_open_url_digest_is_cross_runtime_canonical():
    url = "https://example.com/path?q=1"
    canonical = _canonical("open_url", {"url": url})
    expected = json.dumps(
        {"args": {"url": url}, "capability": "open_url"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    assert canonical == expected
    assert hashlib.sha256(canonical.encode("ascii")).hexdigest()


def test_open_url_is_not_persisted_but_dispatched_receipt_survives_restart(tmp_path):
    db_path = tmp_path / "open-url.sqlite"
    url = "https://example.com/path?session_token=private"
    source_ref = {
        "source_id": "event-source-1",
        "sha256": "a" * 64,
        "char_start": 0,
        "char_end": 12,
        "modality": "text",
    }
    assert "open_url" in CAPABILITIES

    first = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    first.start()
    proposal = first.propose(
        "open_url", {"url": url}, ttl=30,
        event_id="event-1", source_ref=source_ref,
    )
    assert proposal.args == {"url": url}
    row = first.db.execute(
        "SELECT args_json,state FROM control_actions WHERE action_id=?",
        (proposal.action_id,),
    ).fetchone()
    assert row == (None, "PROPOSED")
    first.approve(proposal.action_id, confirmed_by_local_ui=True)
    envelope = first.dispatch_approved(proposal.action_id)
    assert envelope["args"] == {"url": url}
    first.close()

    resumed = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    resumed.start()
    assert resumed.action_state(proposal.action_id) == "DISPATCHED"
    restored = resumed.consume_dispatched(proposal.action_id)
    assert restored.args == {}
    assert restored.digest == proposal.digest
    assert restored.source_ref == source_ref
    assert resumed.action_state(proposal.action_id) == "RECEIPT_CONSUMED"
    resumed.close()


@pytest.mark.parametrize("url", INVALID_URLS)
def test_broker_rejects_unsafe_url_before_creating_action(tmp_path, url):
    broker = AndroidControlBroker(tmp_path / "reject.sqlite")
    with pytest.raises(ControlDenied):
        broker.propose("open_url", {"url": url})
    assert broker.db.execute("SELECT COUNT(*) FROM control_actions").fetchone()[0] == 0
    broker.close()


def test_open_url_receipt_only_binding_survives_restart_after_receipt_verification(tmp_path):
    db_path = tmp_path / "open-url-receipt.sqlite"
    url = "https://example.com/private?session_token=private"
    source_ref = {
        "source_id": "source-2",
        "sha256": "b" * 64,
        "char_start": 0,
        "char_end": 8,
        "modality": "text",
    }
    broker = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    broker.start()
    proposal = broker.propose(
        "open_url", {"url": url}, ttl=30,
        event_id="event-2", source_ref=source_ref,
    )
    broker.approve(proposal.action_id, confirmed_by_local_ui=True)
    broker.dispatch_approved(proposal.action_id)
    consumed = broker.consume_dispatched(proposal.action_id)
    broker.record_companion_receipt(proposal.action_id, consumed.digest, verified=True)
    broker.close()

    resumed = AndroidControlBroker(db_path, clock=lambda: 1000.0)
    recovered = resumed.receipt_proposal(proposal.action_id)
    assert recovered.capability == "open_url"
    assert recovered.args == {}
    assert recovered.digest == proposal.digest
    assert recovered.source_ref == source_ref
    assert resumed.action_state(proposal.action_id) == "RECEIPT_VERIFIED"
    resumed.close()
