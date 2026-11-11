"""Local Termux operator preview for Android action proposals.

Usage: python -m v13.android_control_cli --db /path/audit.sqlite
This deliberately cannot execute device actions. It does not request Android
permissions and never accepts remote/model-origin approvals.
"""
import argparse
import json
import sys
from .android_control import AndroidControlBroker, ControlDenied


def main(argv=None, *, stdin=None, stdout=None):
    parser = argparse.ArgumentParser(description="V13 Android control dry-run operator")
    parser.add_argument("--db", required=True, help="private local audit SQLite path")
    args = parser.parse_args(argv)
    inp = stdin or sys.stdin
    out = stdout or sys.stdout
    if not inp.isatty():
        print("Refusing non-interactive approvals", file=out)
        return 2
    broker = AndroidControlBroker(args.db)
    try:
        broker.start()
        print("DRY RUN ONLY. Commands: propose <capability> <JSON object>, stop, quit", file=out)
        while True:
            out.write("android> ")
            out.flush()
            line = inp.readline()
            if not line or line.strip() in ("quit", "stop"):
                break
            try:
                command, capability, payload = line.strip().split(" ", 2)
                if command != "propose":
                    raise ControlDenied("unknown command")
                p = broker.propose(capability, json.loads(payload))
                print("Action:", p.capability, json.dumps(p.args, ensure_ascii=False), file=out)
                out.write("Approve this single dry-run action? Type YES: ")
                out.flush()
                confirmation = inp.readline().strip()
                if confirmation != "YES":
                    print("Rejected", file=out)
                    continue
                broker.approve(p.action_id, confirmed_by_local_ui=True)
                print(json.dumps(broker.execute(p.action_id), ensure_ascii=False), file=out)
            except (ControlDenied, ValueError, json.JSONDecodeError) as exc:
                print("Denied:", str(exc), file=out)
        return 0
    finally:
        broker.close()


if __name__ == "__main__":
    raise SystemExit(main())
