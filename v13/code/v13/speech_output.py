"""Explicit, serialized Termux system-TTS fallback for FINAL C3 text.

No automatic playback, microphone access, network, model swap or trainable vocoder.
A timeout degrades this Runtime instance; the Termux:API service is never killed.
"""
from __future__ import annotations

import fcntl
import os
import shutil
import signal
import stat
import subprocess
import threading
import time
from pathlib import Path

from .common import dumps, uid
from .config import save_config
from .contracts import packet
from .speech_intent import final_text_intent, verify_intent

MAX_PLAYBACK_CHARS = 3000
DEFAULT_TIMEOUT_SECONDS = 60.0


class TermuxTtsAdapter:
    def __init__(self, executable="termux-tts-speak", timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
        if type(timeout_seconds) not in (int, float) or not 0.1 <= timeout_seconds <= 120:
            raise ValueError("TTS timeout must be 0.1..120 seconds")
        self.executable = executable
        self.timeout_seconds = float(timeout_seconds)
        self._thread_lock = threading.Lock()
        self._degraded = False

    @staticmethod
    def _marker_path(home):
        return Path(home) / "tmp" / "termux-tts.degraded"

    @classmethod
    def _marker_state(cls, home):
        path = cls._marker_path(home)
        try:
            marker_stat = os.lstat(path)
        except FileNotFoundError:
            return False, False
        unsafe = (not stat.S_ISREG(marker_stat.st_mode) or marker_stat.st_nlink != 1
                  or marker_stat.st_uid != os.getuid() or marker_stat.st_mode & 0o077)
        return True, unsafe

    def status(self, enabled, home):
        marked, unsafe = self._marker_state(home)
        return {
            "enabled": enabled is True,
            "available": shutil.which(self.executable) is not None,
            "engine": "TERMUX_SYSTEM_TTS_FALLBACK",
            "automatic_playback": False,
            "microphone_access": False,
            "trainable_voice_model": False,
            "degraded": self._degraded or marked,
            "degraded_marker_unsafe": unsafe,
        }

    def reset(self, home, *, confirmed=False, enabled=False):
        if confirmed is not True:
            return {"status": "CONFIRMATION_REQUIRED"}
        if enabled is True:
            return {"status": "DISABLE_FIRST"}
        path = self._marker_path(home)
        try:
            marker_stat = os.lstat(path)
        except FileNotFoundError:
            self._degraded = False
            return {"status": "NO_MARKER"}
        if (not stat.S_ISREG(marker_stat.st_mode) or marker_stat.st_nlink != 1
                or marker_stat.st_uid != os.getuid() or marker_stat.st_mode & 0o077):
            return {"status": "LOCK_UNSAFE"}
        os.unlink(path)
        self._degraded = False
        return {"status": "RESET", "manual_service_restart_required": True}

    def _write_degraded_marker(self, home):
        path = self._marker_path(home)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = None
        try:
            fd = os.open(str(path), flags, 0o600)
            os.write(fd, str(int(time.time())).encode("ascii"))
            os.fsync(fd)
        except FileExistsError:
            pass
        except OSError:
            pass
        finally:
            if fd is not None:
                os.close(fd)

    @staticmethod
    def _terminate_group(proc):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.communicate(timeout=1.0)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            proc.communicate(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass

    def speak(self, runtime, intent, row):
        marked, marker_unsafe = self._marker_state(runtime.home)
        if self._degraded or marked:
            return {"status": "DEGRADED", "degraded_marker_unsafe": marker_unsafe, "audibility_verified": False}
        if not verify_intent(intent, row["id"], row["event_id"], row["text"]):
            return {"status": "INVALID_INTENT", "audibility_verified": False}
        text = row["text"]
        if len(text) > MAX_PLAYBACK_CHARS:
            return {"status": "TOO_LONG", "audibility_verified": False}
        executable = shutil.which(self.executable)
        if not executable:
            return {"status": "UNAVAILABLE", "audibility_verified": False}
        if not self._thread_lock.acquire(blocking=False):
            return {"status": "BUSY", "audibility_verified": False}

        lock_fd = None
        started = time.monotonic()
        try:
            tmp_dir = Path(runtime.home) / "tmp"
            tmp_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            dir_stat = os.lstat(tmp_dir)
            if (not stat.S_ISDIR(dir_stat.st_mode) or dir_stat.st_uid != os.getuid()
                    or dir_stat.st_mode & 0o077):
                return {"status": "LOCK_UNSAFE", "audibility_verified": False}
            nofollow = getattr(os, "O_NOFOLLOW", None)
            if nofollow is None:
                return {"status": "LOCK_UNAVAILABLE", "audibility_verified": False}
            flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_CLOEXEC", 0) | nofollow
            lock_path = tmp_dir / "termux-tts.lock"
            lock_fd = os.open(str(lock_path), flags, 0o600)
            lock_stat = os.fstat(lock_fd)
            if (not stat.S_ISREG(lock_stat.st_mode) or lock_stat.st_nlink != 1
                    or lock_stat.st_uid != os.getuid()):
                return {"status": "LOCK_UNSAFE", "audibility_verified": False}
            os.fchmod(lock_fd, 0o600)
            try:
                fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return {"status": "BUSY", "audibility_verified": False}

            proc = subprocess.Popen(
                [executable], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True,
            )
            try:
                proc.communicate(text.encode("utf-8"), timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                self._terminate_group(proc)
                self._degraded = True
                self._write_degraded_marker(runtime.home)
                return {
                    "status": "TIMEOUT",
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "text_sha256": intent["text_sha256"],
                    "text_chars": intent["text_chars"],
                    "audibility_verified": False,
                }
            except KeyboardInterrupt:
                self._terminate_group(proc)
                self._degraded = True
                self._write_degraded_marker(runtime.home)
                return {"status": "INTERRUPTED", "audibility_verified": False}
            return {
                "status": "CLI_COMPLETED" if proc.returncode == 0 else "CLI_FAILED",
                "cli_exit_code": proc.returncode,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "text_sha256": intent["text_sha256"],
                "text_chars": intent["text_chars"],
                "engine": "TERMUX_SYSTEM_TTS_FALLBACK",
                "audibility_verified": False,
            }
        except OSError as exc:
            return {"status": "UNAVAILABLE", "error_type": type(exc).__name__, "audibility_verified": False}
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
                os.close(lock_fd)
            self._thread_lock.release()


def _adapter(runtime):
    adapter = getattr(runtime, "_termux_tts_adapter", None)
    if adapter is None:
        adapter = TermuxTtsAdapter()
        runtime._termux_tts_adapter = adapter
    return adapter


def _speak_last(runtime, adapter):
    row = runtime.last_answer()
    if not row or row["status"] != "FINAL":
        return {"status": "NO_FINAL", "audibility_verified": False}
    enabled = runtime.cfg.get("speech_output_enabled", False) is True
    intent = final_text_intent(
        row["id"], row["event_id"], row["text"], row["status"],
        enabled=enabled, user_command=True,
    )
    if intent is None:
        return {"status": "OFF", "audibility_verified": False}
    generation = runtime.store.generation_id
    if not isinstance(generation, str) or not generation:
        return {"status": "LEDGER_BLOCKED", "audibility_verified": False}
    action_id = uid("act")
    try:
        runtime.store.add_packet(
            "ActionIntent",
            packet("ActionIntent", "C5_ANDROID_OUTPUT", row["event_id"], generation,
                   action_id=action_id, action_type="SPEAK_TEXT", permission="LOCAL_OPERATOR_COMMAND"),
        )
    except Exception as exc:
        return {"status": "LEDGER_BLOCKED", "error_type": type(exc).__name__, "audibility_verified": False}

    result = adapter.speak(runtime, intent, row)
    actual = {
        "engine": "TERMUX_SYSTEM_TTS_FALLBACK",
        "text_sha256": intent["text_sha256"],
        "text_chars": intent["text_chars"],
        "duration_ms": result.get("duration_ms", 0),
        "cli_exit_code": result.get("cli_exit_code"),
        "audibility_verified": False,
    }
    try:
        runtime.store.add_packet(
            "ActionOutcome",
            packet("ActionOutcome", "C5_ANDROID_OUTPUT", row["event_id"], generation,
                   action_id=action_id, status=result["status"], actual=actual),
        )
    except Exception as exc:
        try:
            runtime.store.log("speech_output_outcome_persist_failed", row["event_id"],
                               {"action_id": action_id, "error_type": type(exc).__name__})
        except Exception:
            pass
        result = dict(result) | {"ledger_status": "OUTCOME_PERSIST_FAILED"}
    return {"intent": intent, "outcome": result, "automatic_playback": False, "audibility_verified": False}


def operator_command(runtime, args):
    args = list(args or [])
    action = args[0] if args else "status"
    adapter = _adapter(runtime)
    if action == "status" and len(args) <= 1:
        return dumps(adapter.status(runtime.cfg.get("speech_output_enabled", False), runtime.home))
    if action == "on" and len(args) == 1:
        cfg = runtime.cfg | {"speech_output_enabled": True}
        save_config(runtime.home, cfg)
        runtime.cfg.update(cfg)
        return "Platform TTS fallback enabled; playback still requires explicit :speak. No microphone or OS permission is granted."
    if action == "off" and len(args) == 1:
        cfg = runtime.cfg | {"speech_output_enabled": False}
        save_config(runtime.home, cfg)
        runtime.cfg.update(cfg)
        return "Platform TTS fallback disabled for future requests; an already-started Android utterance may continue."
    if action == "speak" and len(args) == 1:
        return dumps(_speak_last(runtime, adapter))
    if action == "reset" and args == ["reset", "--confirm"]:
        return dumps(adapter.reset(runtime.home, confirmed=True,
                                   enabled=runtime.cfg.get("speech_output_enabled", False) is True))
    raise ValueError(":voice [status|on|off|speak|reset --confirm]")
