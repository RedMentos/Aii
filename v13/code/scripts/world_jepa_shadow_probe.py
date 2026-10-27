#!/usr/bin/env python3
"""CLI entrypoint for v2 World-JEPA SHADOW inference; never executes actions."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from v13.world_jepa_shadow_probe import main

if __name__ == '__main__':
    raise SystemExit(main())
