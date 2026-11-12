import pytest
from v13.speech_intent import SpeechIntentQueue, SpeechIntentError

def test_restart_does_not_claim_audio_was_played(tmp_path):
    db = tmp_path / "speech.db"
    q = SpeechIntentQueue(db)
    a = q.submit("Hello", source_id="c3:turn-1")
    assert q.status(a.intent_id) == "QUEUED"
    assert q.claim().digest == a.digest
    assert q.claim() is None
    with pytest.raises(SpeechIntentError):
        q.acknowledge(a.intent_id, digest="0"*64, rendered=True)
    q.close()
    q = SpeechIntentQueue(db)
    assert q.status(a.intent_id) == "RENDERING"
    # Operator has verified that the old renderer is no longer running.
    assert q.recover_uncertain() == 1
    assert q.status(a.intent_id) == "INTERRUPTED"
    with pytest.raises(SpeechIntentError):
        q.acknowledge(a.intent_id, digest=a.digest, rendered=True)
    q.close()

def test_acknowledgement_queue_capacity_and_barge_in(tmp_path):
    q = SpeechIntentQueue(tmp_path / "speech.db", max_pending=2)
    a = q.submit("One", source_id="c3:1")
    b = q.submit("Two", source_id="c3:2")
    with pytest.raises(SpeechIntentError):
        q.submit("Three", source_id="c3:3")
    assert q.claim().intent_id == a.intent_id
    q.acknowledge(a.intent_id, digest=a.digest, rendered=True)
    assert q.status(a.intent_id) == "RENDERED"
    assert q.interrupt() == 1
    assert q.status(b.intent_id) == "INTERRUPTED"
    q.close()

def test_untrusted_inputs_and_unclaimed_ack(tmp_path):
    q = SpeechIntentQueue(tmp_path / "speech.db")
    for text, source in [("", "c3:1"), ("Hi", "../secret"), ("x"*2049, "c3:1"), ("\x00", "c3:1")]:
        with pytest.raises(SpeechIntentError):
            q.submit(text, source_id=source)
    a = q.submit("ok", source_id="c3:1")
    with pytest.raises(SpeechIntentError):
        q.acknowledge(a.intent_id, digest=a.digest, rendered=True)
    assert q.interrupt() == 1
    q.close()
