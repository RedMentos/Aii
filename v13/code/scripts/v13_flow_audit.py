#!/usr/bin/env python3
"""Termux-friendly entry point for the read-only V13 flow audit."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.flow_audit import main

if __name__ == "__main__":
    raise SystemExit(main())
