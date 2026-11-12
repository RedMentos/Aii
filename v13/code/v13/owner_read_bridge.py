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
READ_CMDS = frozenset({"HEALTH", "LEARNING_STATUS", "DIAGNOSTICS", "PIPELINE_STATUS", "LOG_PAGE", "CHAT_SEND", "CHAT_RESULT", "CHAT_OPERATOR", "UPDATE_REQUEST", "LOG_SHARING_ON", "LOG_SHARING_OFF"})
OWNER_AGENT = "agent-owner"
MAX_READ_BODY = 2048


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
    if operation in ("LOG_PAGE","CHAT_SEND","CHAT_RESULT","CHAT_OPERATOR"):
        allowed_fields.add("args")
    if set(obj) != allowed_fields:
        raise bridge.Denied("unexpected read fields")
    args = obj.get("args", {})
    if operation == "LOG_PAGE":
        if (not isinstance(args, dict) or set(args) != {"session","page"} or
            type(args.get("session")) is not int or not 0 <= args["session"] < 34 or
            type(args.get("page")) is not int or not 0 <= args["page"] < 2048):
            raise bridge.Denied("invalid bounded log page")
    elif operation == "CHAT_SEND":
        if (not isinstance(args, dict) or set(args) != {"text"} or
                not isinstance(args.get("text"), str) or
                not args["text"].strip() or len(args["text"].encode("utf-8")) > 1400 or
                any(ch in args["text"] for ch in ("\x00", "\n", "\r")) or
                args["text"].strip().startswith(":")):
            raise bridge.Denied("invalid remote chat message")
    elif operation == "CHAT_OPERATOR":
        from .remote_chat import SAFE_OPERATOR_COMMANDS
        if (not isinstance(args, dict) or set(args) != {"command"} or
                type(args.get("command")) is not str or
                args["command"] not in SAFE_OPERATOR_COMMANDS):
            raise bridge.Denied("invalid diagnostic operator")
    elif operation == "CHAT_RESULT":
        if (not isinstance(args, dict) or set(args) != {"request_id"} or
                not isinstance(args.get("request_id"), str) or
                not bridge.ID.fullmatch(args["request_id"])):
            raise bridge.Denied("invalid remote chat lookup")
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


def monitor_and_alert(client, *, now=None):
    """Send one private GitHub incident when real V13 chat health changes.

    A GitHub update being successful is NOT proof the AI can answer.
    Only approved enums are written. No user texts, traceback, paths or
    SHA/blob names ever leave the phone through this channel.
    """
    from . import phone_monitor
    from .common import atomic_write
    clock=int(time.time() if now is None else now)
    report=phone_monitor.check()
    phone_monitor.persist_status(report)
    incident=phone_monitor.safe_incident(report)
    private=phone_monitor.PRIVATE
    flag=private/"phone-monitor-last-alert.json"
    if flag.is_symlink():
        raise bridge.Denied("unsafe phone monitor alert state")
    previous={}
    try:
        if flag.is_file() and flag.stat().st_size <= 1024:
            previous=json.loads(flag.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        previous={}
    previous_code=previous.get("fingerprint")
    code=(incident["component"]+":"+incident["code"] if incident else "HEALTHY")
    # Publish transitions, and remind about an unresolved incident no more
    # than once per 24 hours. Healthy with no prior alert publishes nothing.
    if previous_code==code and (not incident or clock-int(previous.get("reported_at",0)) < 86400):
        return {"status":"UNCHANGED","code":code}
    if not incident and not previous_code:
        return {"status":"HEALTHY","code":"HEALTHY"}
    body=incident or {"schema":"v13.phone-incident/1","severity":"RECOVERED",
                       "component":"CHAT","code":"HEALTHY",
                       "ai":report["ai"]}
    body={**body,"reported_at":clock}
    title=("V13ALERT:"+body["component"]+":"+body["code"] if incident else
           "V13RECOVERED:CHAT:HEALTHY")
    # GitHub client is restricted to the exact configured PRIVATE repository.
    client.request("POST","/repos/"+client.repository+"/issues",
                   {"title":title,"body":bridge.canonical(body).decode("ascii")},limit=4096)
    atomic_write(flag,json.dumps({"fingerprint":code,"reported_at":clock}))
    flag.chmod(0o600)
    return {"status":"PUBLISHED","code":code}


OWNER_GRANTS = (
    "HEALTH", "LEARNING_STATUS", "DIAGNOSTICS", "PIPELINE_STATUS",
    "LOG_PAGE", "CHAT_SEND", "CHAT_RESULT", "CHAT_OPERATOR",
    "UPDATE_REQUEST", "LOG_SHARING_ON", "LOG_SHARING_OFF"
)


def activate_owner_capabilities(config_path):
    """Safely migrate exactly the known older RedMentos owner scope once.

    The user explicitly requested these phone-to-ChatGPT capabilities.
    A one-time local marker means a later explicit permission revocation is
    respected on restarts; never auto-regrant a second time.
    """
    from pathlib import Path
    import stat
    import tempfile
    path=Path(config_path)
    private=path.parent
    marker=private/"owner-capabilities-v2.done"
    if path.is_symlink() or not path.is_file() or marker.is_symlink():
        raise bridge.Denied("owner capability config path is unsafe")
    if marker.exists():
        return False
    st=path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_mode & 0o077:
        raise bridge.Denied("owner capability config not private")
    obj=bridge.strict_json(path.read_bytes())
    if (not isinstance(obj,dict) or
            obj.get("relay_repo")!="RedMentos/Aiiii" or
            obj.get("remote_apply_enabled") is not False or
            obj.get("authors",{}).get(OWNER_AGENT)!=["RedMentos"]):
        raise bridge.Denied("owner capability policy is untrusted")
    p=obj.get("permissions",{}).get(OWNER_AGENT)
    if (not isinstance(p,list) or not p or not set(p).issubset(OWNER_GRANTS)):
        raise bridge.Denied("owner permissions include unknown authority")
    if p != list(OWNER_GRANTS):
        obj["permissions"][OWNER_AGENT]=list(OWNER_GRANTS)
        fd,tmp=tempfile.mkstemp(prefix=".v13-owner-scope-",dir=str(private))
        try:
            os.fchmod(fd,0o600)
            with os.fdopen(fd,"wb") as stream:
                stream.write(bridge.canonical(obj))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    fd=os.open(marker,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_NOFOLLOW",0),0o600)
    with os.fdopen(fd,"w") as stream:
        stream.write("complete\n")
        stream.flush()
        os.fsync(stream.fileno())
    return True


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


def create_read_request(command, *, now=None, session=0, page=0, text=None, request_id=None, operator_command=None):
    """Build a non-secret READ request for a trusted GitHub connector."""
    if command not in READ_CMDS:
        raise bridge.Denied("read-only commands only")
    out = {"schema": READ_SCHEMA, "id": secrets.token_hex(16),
           "command": command, "expires_at": int(time.time() if now is None else now) + 600}
    if command == "LOG_PAGE":
        if type(session) is not int or not 0 <= session < 34 or type(page) is not int or not 0 <= page < 2048:
            raise bridge.Denied("bounded log page values only")
        out["args"] = {"session":session, "page":page}
    if command == "CHAT_SEND":
        if not isinstance(text,str) or not text.strip() or len(text.encode("utf-8")) > 1400 or text.startswith(":") or any(c in text for c in ("\n","\r","\x00")):
            raise bridge.Denied("one bounded non-operator text required")
        out["args"]={"text":text}
    if command == "CHAT_OPERATOR":
        from .remote_chat import SAFE_OPERATOR_COMMANDS
        if operator_command not in SAFE_OPERATOR_COMMANDS:
            raise bridge.Denied("approved diagnostic command required")
        out["args"]={"command":operator_command}
    if command == "CHAT_RESULT":
        if not isinstance(request_id,str) or not bridge.ID.fullmatch(request_id):
            raise bridge.Denied("valid previous chat request ID required")
        out["args"]={"request_id":request_id}
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
    # Restore newly committed files from older sparse checkouts before
    # importing remote chat/monitor modules. Then extend the approved owner
    # scope once; this avoids another manual Termux command after a CI update.
    from .source_updater import ensure_sparse_phone_modules
    ensure_sparse_phone_modules()
    activate_owner_capabilities(args.config)
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
                if pipeline_agent.claim_scheduled_update():
                    pipeline_agent.run_cycle(force=True, manual=True)
                else:
                    pipeline_agent.run_cycle()
                # V13 itself must be kept alive independently of the browser
                # and updater; do not restart if the owner explicitly turned
                # off the AI or while a verified update is in progress.
                from .chat_service import _read_desired, ensure_service
                if (_read_desired() and
                        pipeline_agent.snapshot()["last_result"] != "CHECKING"):
                    ensure_service(timeout=8)
            except (OSError, ValueError, RuntimeError) as exc:
                print(json.dumps({"status":"PIPELINE_ERROR",
                                  "error_code":type(exc).__name__}), flush=True)
            time.sleep(30)
    threading.Thread(target=update_worker, name="v13-phone-updater", daemon=True).start()
    while True:
        try:
            print(json.dumps(poll_once(client, cfg)), flush=True)
            print(json.dumps(monitor_and_alert(client)), flush=True)
        except (OSError, ValueError, RuntimeError) as exc:
            print(json.dumps({"status": "POLL_ERROR", "error_code": type(exc).__name__}), flush=True)
        # An updated relay must reload its own Python modules before it can
        # serve newly added commands. Never do so inside an issue transaction.
        if (pipeline_agent.refresh_requested("bridge") and
                pipeline_agent.snapshot()["last_result"] != "CHECKING"):
            pipeline_agent.acknowledge_refresh("bridge")
            os.execv(sys.executable, [sys.executable, "-m", "v13.owner_read_bridge",
                                      "serve", "--config", args.config])
        time.sleep(seconds)


if __name__ == "__main__":
    main()
