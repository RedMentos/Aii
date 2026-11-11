import hashlib
import pytest

from v13.speech_intent import SpeechIntentQueue, SpeechIntentError
from v13.speech_runtime_bridge import C3ResponseReceipt, SpeechRuntimeBridge


def receipt(text="Hello"):
    return C3ResponseReceipt(
        event_id="evt_" + "a" * 28,
        output_sha256=hashlib.sha256(text.encode()).hexdigest(),
        text=text, completed=True,
    )


def test_completed_c3_receipt_to_durable_queue_and_stop(tmp_path):
    path = tmp_path / "speech.sqlite"
    q = SpeechIntentQueue(path)
    bridge = SpeechRuntimeBridge(q)
    with pytest.raises(SpeechIntentError, match="OFF"):
        bridge.submit(receipt())
    bridge.enabled = True
    intent = bridge.submit(receipt())
    assert intent.source_id == "c3:" + receipt().event_id
    assert q.claim().intent_id == intent.intent_id
    assert bridge.stop() == 1
    assert q.status(intent.intent_id) == "INTERRUPTED"
    q.close()
    q = SpeechIntentQueue(path)
    assert q.status(intent.intent_id) == "INTERRUPTED"
    q.close()


def test_untrusted_or_incomplete_receipts_never_enqueue(tmp_path):
    q = SpeechIntentQueue(tmp_path / "speech.sqlite")
    bridge = SpeechRuntimeBridge(q, enabled=True)
    good = receipt()
    bad = [
        C3ResponseReceipt(good.event_id, good.output_sha256, "Tampered", True),
        C3ResponseReceipt(good.event_id, good.output_sha256, good.text, False),
        C3ResponseReceipt("../invalid", good.output_sha256, good.text, True),
        C3ResponseReceipt(good.event_id, good.output_sha256, good.text, True, "B1_DETAIL"),
        C3ResponseReceipt(good.event_id, "z"*64, good.text, True),
    ]
    for item in bad:
        with pytest.raises(SpeechIntentError):
            bridge.submit(item)
    assert q.db.execute("SELECT count(*) FROM speech_intents").fetchone()[0] == 0
    q.close()

def test_replayed_c3_response_is_not_spoken_twice_after_restart(tmp_path):
    path = tmp_path / "speech.sqlite"
    q = SpeechIntentQueue(path)
    bridge = SpeechRuntimeBridge(q, enabled=True)
    bridge.submit(receipt())
    with pytest.raises(SpeechIntentError, match="already queued"):
        bridge.submit(receipt())
    q.close()
    q = SpeechIntentQueue(path)
    bridge = SpeechRuntimeBridge(q, enabled=True)
    with pytest.raises(SpeechIntentError, match="already queued"):
        bridge.submit(receipt())
    assert q.db.execute("SELECT count(*) FROM speech_intents").fetchone()[0] == 1
    q.close()
