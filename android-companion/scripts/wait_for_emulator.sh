#!/usr/bin/env bash
set -euo pipefail

ready=0
for attempt in $(seq 1 8); do
  probe="$(timeout 12s adb shell 'printf "%s|%s|" "$(getprop ro.build.version.sdk)" "$(getprop sys.boot_completed)"; pm path android' 2>&1 | tr -d '\r' || true)"
  if printf '%s\n' "$probe" | grep -Fq '33|1|package:'; then
    echo "Android emulator shell and PackageManager ready (attempt ${attempt})."
    ready=1
    break
  fi
  echo "Emulator not ready yet (attempt ${attempt}/8): ${probe:0:300}"
  sleep 5
done

if [ "$ready" -ne 1 ]; then
  echo "Emulator booted but ADB shell/PackageManager never became responsive."
  adb devices -l || true
  timeout 10s adb logcat -d -t 100 -v brief | tail -n 80 || true
  exit 1
fi
