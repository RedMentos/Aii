"""Safe local operator preview: python -m v13.android_operator_cli dry launch com.example.app.

No Android API calls, permission grants or implicit C3 tool execution.
"""
from __future__ import annotations
import argparse
import json
from .android_capability_contract import CapabilityRegistry
from .android_companion_dispatch import AndroidDispatcher
from .android_operator_bridge import dispatch_operator_command

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="V13 Android action preview (OFF; no native execution)")
    parser.add_argument("mode", choices=["dry"])
    parser.add_argument("action", choices=["launch", "observe", "back", "tap", "type"])
    parser.add_argument("target", nargs="?")
    args = parser.parse_args(argv)
    command = f":android {args.mode} {args.action}"
    if args.target is not None:
        command += " " + args.target
    result = dispatch_operator_command(command, AndroidDispatcher(CapabilityRegistry()))
    print(json.dumps({"status": result.status, "capability": result.capability,
                      "request_id": result.request_id, "detail": result.detail}, sort_keys=True))
    return 0 if result.status == "DRY_RUN" else 2

if __name__ == "__main__":
    raise SystemExit(main())
