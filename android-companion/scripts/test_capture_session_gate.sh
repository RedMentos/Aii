#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

javac -d "$TMP" \
  "$ROOT/app/src/main/java/com/redmentos/v14/companion/CaptureSessionGate.java" \
  "$ROOT/scripts/CaptureSessionGateSmoke.java"
java -ea -cp "$TMP" com.redmentos.v14.companion.CaptureSessionGateSmoke
