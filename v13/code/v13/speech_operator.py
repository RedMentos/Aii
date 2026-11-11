"""Local read-only C3 speech queue inspection and manual stop; no audio execution."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .speech_intent import SpeechIntentQueue

def main(argv=None):
    parser = argparse.ArgumentParser(description="V13 C3 speech-intent inspection (no audio)")
    parser.add_argument("--db", required=True, help="local speech-intent SQLite path")
    parser.add_argument("command", choices=("status", "stop"))
    args = parser.parse_args(argv)
    db = Path(args.db)
    if not db.is_file():
        parser.error("existing speech database required")
    queue = SpeechIntentQueue(db)
    try:
        if args.command == "stop":
            print(json.dumps({"interrupted": queue.interrupt(), "audio_device_stopped": False}, sort_keys=True))
        else:
            counts = dict(queue.db.execute("SELECT status,count(*) FROM speech_intents GROUP BY status"))
            print(json.dumps({"counts": counts, "renderer": "NOT_CONNECTED", "android_native": "UNVERIFIED"}, sort_keys=True))
    finally:
        queue.close()

if __name__ == "__main__":
    main()


class LocalSpeechHandoff:
    """Opt-in committed-C3 queue writer for local Termux operator interaction.

    No Android audio renderer is invoked. The opt-in flag is an operator API
    contract, not proof of Android-side identity or permission.
    """
    def __init__(self, store, db_path, *, max_pending=16):
        from .speech_runtime_bridge import SpeechRuntimeBridge
        self.store = store
        self.queue = SpeechIntentQueue(db_path, max_pending=max_pending)
        self.bridge = SpeechRuntimeBridge(self.queue, enabled=False)
        self.closed = False

    def enqueue(self, event_id, *, local_user_opt_in=False):
        from .speech_intent import SpeechIntentError
        from .speech_store_binding import enqueue_committed_c3
        if self.closed:
            raise SpeechIntentError("speech handoff closed")
        if local_user_opt_in is not True:
            raise SpeechIntentError("local user opt-in required")
        self.bridge.enabled = True
        try:
            return enqueue_committed_c3(self.store, event_id, self.bridge)
        finally:
            self.bridge.enabled = False

    def stop(self):
        if self.closed:
            return 0
        return self.bridge.stop()

    def close(self):
        if not self.closed:
            self.stop()
            self.queue.close()
            self.closed = True
