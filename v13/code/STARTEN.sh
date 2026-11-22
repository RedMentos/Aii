#!/usr/bin/env bash
set -Eeuo pipefail
V13_START_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$V13_START_DIR/setup.sh" "$@"
