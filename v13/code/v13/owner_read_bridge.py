"""Owner-authorized READ-ONLY commands over a verified private GitHub relay.

Convenience protocol for ChatGPT GitHub connector: V13READ issues are admitted
only from the exact configured GitHub owner in a PRIVATE repository. The phone
translates the two allowed read-only commands into locally HMAC-authenticated
requests; the secret never leaves Termux. PATCH_* always requires the distinct
stronger signed protocol in remote_maintenance_bridge. Not a general shell.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import sys
import threading

from v13 import remote_maintenance_bridge as bridge

READ_SCHEMA = "v13.private-relay.owner-read/1"
READ_CMDS = frozenset({"HEALTH", "LEARNING_STATUS", "DIAGNOSTICS", "PIPELINE_STATUS", "LOG_PAGE"})
OWNER_AGENT = "agent-owner"
MAX_READ_BODY = 1024


def validate_owner_read(issue, cfg, *, now=None):
    """Validate repository-provided issue author, timestamp, exact payload."""
    clock = int(time.time() if now is None else now)
    if not isinstance(issue, dict) or "pull_request" in issue:
        raise bridge.Denied("not a command issue")
    author = (issue.get("user") or {}).get("login")
    allowed = cfg.get("authors", {}).get(OWNER_AGENT, [])
    if not isinstance(author, str) or author not in allowed:
        raise bridge.Denied("untrusted GitHub author")
    title, raw = issue.get("title"), issue.get("body")
    if not isinstance(title, str) or not title.startswith("V13READ:"):
        raise bridge.Denied("not an owner-read issue")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_READ_BODY:
        raise bridge.Denied("oversized or missing payload")
    obj = bridge.strict_json(raw)
    if not isinstance(obj, dict) or not {"schema","id","command","expires_at"}.issubset(obj):
        raise bridge.Denied("invalid read schema")
    ident, operation, expiry = obj["id"], obj["command"], obj["expires_at"]
    allowed_fields = {"schema", "id", "command", "expires_at"}
    if operation == "LOG_PAGE":
        allowed_fields.add("args")
    if set(obj) != allowed_fields:
        raise bridge.Denied("unexpected read fields")
    args = obj.get("args", {})
    if operation == "LOG_PAGE":
        if (not isinstance(args, dict) or set(args) != {"session","page"} or
            type(args.get("session")) is not int or not 0 <= args["session"] < 32 or
            type(args.get("page")) is not int or not 0 <= args["page"] < 2048):
            raise bridge.Denied("invalid bounded log page")
    elif args:
        raise bridge.Denied("unexpected read args")
    if obj["schema"] != READ_SCHEMA or not isinstance(ident, str) or not bridge.ID.fullmatch(ident):
        raise bridge.Denied("invalid schema/id")
    if title != "V13READ:" + ident or operation not in READ_CMDS:
        raise bridge.Denied("not an allowed read command")
    if type(expiry) is not int or not 0 < expiry - clock <= 600:
        raise bridge.Denied("expired read request")
    created = issue.get("created_at")
    if not isinstance(created, str):
        raise bridge.Denied("unverified issue timestamp")
    try:
        created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if created_at.tzinfo is None:
            raise ValueError("timezone missing")
        created_ts = created_at.astimezone(timezone.utc).timestamp()
    except (ValueError, OverflowError) as exc:
        raise bridge.Denied("invalid issue timestamp") from exc
    if not -90 <= clock - created_ts <= 600:
        raise bridge.Denied("stale/future issue")
    if operation not in cfg.get("permissions", {}).get(OWNER_AGENT, []):
        raise bridge.Denied("disabled owner-read command")
    return ident, operation, args


def process_owner_issue(client, cfg, db, issue, *, now=None):
    try:
        request_id, operation, args = validate_owner_read(issue, cfg, now=now)
        if OWNER_AGENT not in cfg["keys"]:
            return False
        # The resulting local HMAC is never posted or exported.
        signed = bridge.make_command(
            OWNER_AGENT, operation, args, cfg["keys"][OWNER_AGENT],
            now=now, request_id=request_id
        )
        local = dict(issue)
        local["title"] = "V13CMD:" + request_id
        local["body"] = bridge.canonical(signed).decode("ascii")
        return bridge.process_issue(client, cfg, db, local, now=now)
    except (bridge.Denied, TypeError, KeyError, ValueError):
        return False


def poll_once(client, cfg, *, now=None):
    client.check_private()
    state_dir = Path(cfg["state_dir"])
    if (state_dir / "STOP").exists():
        return {"status": "STOPPED_LOCALLY", "processed": 0}
    with bridge.local_lock(state_dir) as state:
        if (state / "STOP").exists():
            return {"status": "STOPPED_LOCALLY", "processed": 0}
        with bridge.database(state) as db:
            processed = 0
            for issue in client.issues():
                if processed >= 20:
                    break
                title = str(issue.get("title", ""))
                if title.startswith("V13READ:"):
                    worked = process_owner_issue(client, cfg, db, issue, now=now)
                else:
                    worked = bridge.process_issue(client, cfg, db, issue, now=now)
                if worked:
                    processed += 1
            return {"status": "POLL_OK", "processed": processed}


def github_token():
    """Use gh device-login credentials; never print or persist the token here."""
    env = os.environ.get("V13_RELAY_TOKEN", "")
    if env:
        return env
    try:
        result = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True,
            check=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise bridge.Denied("GitHub CLI login missing; run gh auth login") from exc
    token = result.stdout.strip()
    if not token:
        raise bridge.Denied("GitHub CLI returned no credential")
    return token


def create_read_request(command, *, now=None, session=0, page=0):
    """Build a non-secret READ request for a trusted GitHub connector."""
    if command not in READ_CMDS:
        raise bridge.Denied("read-only commands only")
    out = {"schema": READ_SCHEMA, "id": secrets.token_hex(16),
           "command": command, "expires_at": int(time.time() if now is None else now) + 600}
    if command == "LOG_PAGE":
        if type(session) is not int or not 0 <= session < 32 or type(page) is not int or not 0 <= page < 2048:
            raise bridge.Denied("bounded log page values only")
        out["args"] = {"session":session, "page":page}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="V13 PRIVATE owner-read Termux bridge")
    parser.add_argument("action", choices=("once", "serve", "stop", "resume", "make-read"))
    parser.add_argument("--config", required=False)
    parser.add_argument("--command", choices=sorted(READ_CMDS))
    args = parser.parse_args(argv)
    if args.action == "make-read":
        if not args.command:
            parser.error("--command is required")
        obj = create_read_request(args.command)
        print(json.dumps({"title": "V13READ:" + obj["id"], "body": obj}, sort_keys=True))
        return
    if not args.config:
        parser.error("--config is required")
    if args.action in ("stop", "resume"):
        bridge.cli([args.action, "--config", args.config])
        return
    cfg = bridge.private_config(args.config)
    if cfg.get("remote_apply_enabled"):
        raise bridge.Denied("one-command owner bridge must remain read-only")
    if cfg["relay_repo"].lower() != "redmentos/aiiii":
        raise bridge.Denied("unexpected private relay destination")
    client = bridge.GitHub(github_token(), cfg["relay_repo"])
    if args.action == "once":
        print(json.dumps(poll_once(client, cfg), sort_keys=True))
        return
    seconds = cfg.get("poll_seconds", bridge.DEFAULT_INTERVAL)
    if type(seconds) is not int or not 15 <= seconds <= 3600:
        raise bridge.Denied("bad polling interval")
    # Independent from the browser: automatic CI-gated checks keep running
    # while no browser tab is open, as long as Termux keeps this process alive.
    from . import pipeline_agent
    def update_worker():
        while True:
            try:
                pipeline_agent.run_cycle()
            except (OSError, ValueError, RuntimeError) as exc:
                print(json.dumps({"status":"PIPELINE_ERROR",
                                  "error_code":type(exc).__name__}), flush=True)
            time.sleep(30)
    threading.Thread(target=update_worker, name="v13-phone-updater", daemon=True).start()
    while True:
        try:
            print(json.dumps(poll_once(client, cfg)), flush=True)
        except (OSError, ValueError) as exc:
            print(json.dumps({"status": "POLL_ERROR", "error_code": type(exc).__name__}), flush=True)
        # An updated relay must reload its own Python modules before it can
        # serve newly added commands. Never do so inside an issue transaction.
        if pipeline_agent.refresh_requested("bridge"):
            pipeline_agent.acknowledge_refresh("bridge")
            os.execv(sys.executable, [sys.executable, "-m", "v13.owner_read_bridge",
                                      "serve", "--config", args.config])
        time.sleep(seconds)


if __name__ == "__main__":
    main()
