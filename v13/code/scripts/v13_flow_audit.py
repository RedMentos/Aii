#!/usr/bin/env python3
"""Termux-friendly entry point for the read-only V13 flow audit."""
from v13.flow_audit import main

if __name__ == "__main__":
    raise SystemExit(main())
