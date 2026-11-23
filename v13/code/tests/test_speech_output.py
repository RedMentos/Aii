import json
import os
import stat
import threading
import time
from pathlib import Path

import pytest

from v13.config import initialize
from v13.contracts import validate
from v13.operator import Operator
from v13.speech_intent import final_text_intent, verify_intent
from v13.speech_output import TermuxTtsAdapter, operator_command


class Store:
    generation_id = "generation-1"

    def __init__(self):
        self.packets = []
        self.logs = []

    def add_packet(self, kind, packet):
        validate(kind, packet)
        self.packets.append((kind, packet))
        return packet

    def log(self, *args):
        self.logs.append(args)


class Runtime:
    def __init__(self, home, status="FINAL", text="A local answer."):
        self.home = Path(home)
        self.cfg = initialize(self.home)
        self.store = Store()
        self.row = {"id": 7, "event_id": "event-7", "status": status, "text": text}

    def last_answer(self):
        return self.row


def fake_tts(path, body):
    path.write_text("#!/usr/bin/env python3\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_intent_is_final_source_bound_and_explicit_only():
    assert final_text_intent(7, "e", "text", "FINAL", enabled=True, user_command=False) is None
    assert final_text_intent(7, "e", "text", "DEADLINE", enabled=True, user_command=True) is None
    intent = final_text_intent(7, "e", "text", "FINAL", enabled=True, user_command=True)
    assert intent and "text" not in intent and intent["automatic_playback"] is False
    assert verify_intent(intent, 7, "e", "text")
    assert not verify_intent(intent, 7, "e", "changed")
    with pytest.raises(ValueError):
        final_text_intent(7, "e", "bad\x00text", "FINAL", enabled=True, user_command=True)


def test_voice_is_off_by_default_and_only_explicit_speak_runs(tmp_path, monkeypatch):
    runtime = Runtime(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    capture = tmp_path / "captured.txt"
    script = bin_dir / "termux-tts-speak"
    fake_tts(script, "import os,sys\nopen(os.environ['CAPTURE_FILE'],'w').write(sys.stdin.read())\n")
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("CAPTURE_FILE", str(capture))
    disabled = json.loads(operator_command(runtime, ["status"]))
    assert disabled["enabled"] is False and disabled["available"] is True
    assert json.loads(operator_command(runtime, ["speak"]))["status"] == "OFF"
    assert not runtime.store.packets
    operator_command(runtime, ["on"])
    result = json.loads(operator_command(runtime, ["speak"]))
    assert result["outcome"]["status"] == "CLI_COMPLETED"
    assert result["audibility_verified"] is False
    assert capture.read_text() == "A local answer."
    kinds = [kind for kind, _ in runtime.store.packets]
    assert kinds == ["ActionIntent", "ActionOutcome"]
    intent_packet = runtime.store.packets[0][1]
    outcome_packet = runtime.store.packets[1][1]
    assert intent_packet["action_id"] == outcome_packet["action_id"]
    assert "A local answer." not in json.dumps(outcome_packet)
    operator_command(runtime, ["off"])
    assert runtime.cfg["speech_output_enabled"] is False


def test_non_final_never_speaks_or_records_action(tmp_path, monkeypatch):
    runtime = Runtime(tmp_path, status="DEADLINE")
    operator_command(runtime, ["on"])
    result = json.loads(operator_command(runtime, ["speak"]))
    assert result["status"] == "NO_FINAL"
    assert not runtime.store.packets


def test_calls_are_serialized_and_second_is_busy(tmp_path, monkeypatch):
    runtime = Runtime(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    started = tmp_path / "started"
    script = bin_dir / "termux-tts-speak"
    fake_tts(script, "import pathlib,sys,time\npathlib.Path(%r).write_text('1')\ntime.sleep(0.6)\nsys.stdin.read()\n" % str(started))
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    intent = final_text_intent(7, "event-7", "A local answer.", "FINAL", enabled=True, user_command=True)
    adapter = TermuxTtsAdapter(timeout_seconds=3)
    first = []
    thread = threading.Thread(target=lambda: first.append(adapter.speak(runtime, intent, runtime.row)))
    thread.start()
    deadline = time.time() + 2
    while not started.exists() and time.time() < deadline:
        time.sleep(0.01)
    assert started.exists()
    second = adapter.speak(runtime, intent, runtime.row)
    thread.join(timeout=3)
    assert second["status"] == "BUSY"
    assert first and first[0]["status"] == "CLI_COMPLETED"


def test_timeout_degrades_adapter_without_killing_api_service(tmp_path, monkeypatch):
    runtime = Runtime(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    script = bin_dir / "termux-tts-speak"
    fake_tts(script, "import time\ntime.sleep(3)\n")
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ.get("PATH", ""))
    intent = final_text_intent(7, "event-7", "A local answer.", "FINAL", enabled=True, user_command=True)
    adapter = TermuxTtsAdapter(timeout_seconds=0.1)
    first = adapter.speak(runtime, intent, runtime.row)
    second = adapter.speak(runtime, intent, runtime.row)
    assert first["status"] == "TIMEOUT"
    assert second["status"] == "DEGRADED"
    restarted_adapter = TermuxTtsAdapter(timeout_seconds=0.1)
    assert restarted_adapter.speak(runtime, intent, runtime.row)["status"] == "DEGRADED"
    assert json.loads(operator_command(runtime, ["status"]))["degraded"] is True
    assert json.loads(operator_command(runtime, ["reset", "--confirm"]))["status"] == "RESET"
    assert json.loads(operator_command(runtime, ["status"]))["degraded"] is False


def test_operator_command_is_tty_only(tmp_path):
    runtime = Runtime(tmp_path)
    with pytest.raises(ValueError):
        Operator(runtime).run(":voice on", origin="WEBVIEW")
