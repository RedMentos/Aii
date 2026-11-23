#!/usr/bin/env bash
# Optional existing-chat entry with the real same-causal C3 decoder.
set -Eeuo pipefail
umask 077
V13_CAUSAL_START_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
V13_CAUSAL_DATA_DIR="${V13_HOME:-$HOME/v13}"
export V13_HOME="$V13_CAUSAL_DATA_DIR"
printf 'V13 · Einrichtung und Vorbereitung des kausalen C3-Decoders\n'
V13_NO_AUTOSTART=1 bash "$V13_CAUSAL_START_DIR/setup.sh"
bash "$V13_CAUSAL_START_DIR/VORBEREITEN_CAUSAL.sh" --enable
printf 'Kausaler C3-Decoder vorbereitet. Chat: %s/bin/v13 chat\n' "$V13_CAUSAL_DATA_DIR"
if [[ -t 0 && "${V13_NO_AUTOSTART:-0}" != 1 ]]; then
  exec "$V13_CAUSAL_DATA_DIR/bin/v13" chat --welcome "$@"
fi
