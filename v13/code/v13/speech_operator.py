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
