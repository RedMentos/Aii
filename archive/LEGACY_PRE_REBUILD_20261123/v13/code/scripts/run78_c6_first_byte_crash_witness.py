#!/usr/bin/env python3
"""Run78 independent zero-byte output commit crash-window SQLite witness.

Synthetic local Store only. Demonstrates that commit_output alone does not
prove visible first-byte delivery; not a claim that the API is wrong when a
real stream owner calls it at the correct boundary.
"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from v13.config import initialize
from v13.store import Store, audit_closed
from v13.transaction import commit_output


def witness():
    with tempfile.TemporaryDirectory(prefix="v13-c6-first-byte-") as tmp:
        home = Path(tmp)
        initialize(home)
        store = Store(home)
        try:
            session = store.new_session()
            event = store.event(session, "Synthetic C6 output boundary witness.")
            mid = store.message(session, event["event_id"], "assistant",
                                "synthetic answer", "DRAFT",
                                {"shadow": True, "candidate_sha256": "synthetic"})
            moved = commit_output(store, mid, event["event_id"])
            before = store.one("SELECT status FROM messages WHERE id=?", (mid,))["status"]
            # Deliberately no append_message, no write to a TTY, no bytes emitted.
            # Model a crash/restart immediately after the database commit.
        finally:
            store.close()
        reopened = Store(home)
        try:
            after = reopened.one("SELECT status,text FROM messages WHERE id=?", (mid,))
            output = {
                "schema": "v13.run78.c6_first_byte_crash_window_witness.v1",
                "status": "ZERO_BYTE_COMMIT_WINDOW_REPRODUCED"
                          if moved and before == "OUTPUT_COMMITTED"
                          and after["status"] == "INTERRUPTED"
                          else "WITNESS_UNEXPECTED",
                "commit_output_returned": moved,
                "status_before_restart": before,
                "status_after_restart": after["status"],
                "synthetic_stream_bytes_sent": 0,
                "stored_candidate_retained": after["text"] == "synthetic answer",
                "native_model_called": False,
                "real_tty_approved": False,
                "production_authority": 0,
                "step2_promoted": False,
                "claim_limit": "Synthetic Store lifecycle only; does not test real stream owner",
            }
        finally:
            reopened.close()
        output["closed_store_ok"] = bool(audit_closed(home)["ok"])
        return output


def main():
    print(json.dumps(witness(), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
