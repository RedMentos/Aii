import json
from v13.speech_intent import SpeechIntentQueue
from v13.speech_operator import main

def test_operator_inspect_and_stop(tmp_path, capsys):
    db = tmp_path / "speech.db"
    q = SpeechIntentQueue(db)
    intent = q.submit("hello", source_id="c3:turn-1")
    q.close()
    main(["--db", str(db), "status"])
    status = json.loads(capsys.readouterr().out)
    assert status["counts"]["QUEUED"] == 1
    assert status["android_native"] == "UNVERIFIED"
    main(["--db", str(db), "stop"])
    stopped = json.loads(capsys.readouterr().out)
    assert stopped == {"audio_device_stopped": False, "interrupted": 1}
    q = SpeechIntentQueue(db)
    assert q.status(intent.intent_id) == "INTERRUPTED"
    q.close()
