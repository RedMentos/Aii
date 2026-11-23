#!/usr/bin/env bash
# V13 Cloud-Prüfstand (WP-B): echter llama.cpp-b10964-Runner + 3 gepinnte Modelle auf Linux.
# Nutzung (aus jedem Thread, 1 Befehl):
#   bash /mnt/project-files/v13/code/scripts/cloud_bench.sh            # Units + Setup/Probe + Acceptance --quick
#   bash .../cloud_bench.sh --units     # nur Unit-Tests (kein Modell)
#   bash .../cloud_bench.sh --smoke     # Units + Setup + selftest + probe
#   bash .../cloud_bench.sh --full      # wie Standard, aber volle Acceptance (lange)
#   bash .../cloud_bench.sh --candidates  # Units + Setup + Modellkandidaten-Vergleich (specs/cloud-candidates.json, EN+DE)
#   bash .../cloud_bench.sh --semantic    # Units + Setup + WP-H Abruf-Benchmark EmbeddingGemma vs. lexikalisch
#   bash .../cloud_bench.sh --suite       # Units + WP-N12 Messsuite (§24/§99, Register, Gates; ohne Modell)
# Weitere Argumente nach den Modus-Flags gehen an scripts/acceptance.py (z.B. --stage-limit 3).
# Die Quelle wird nach $V13_BENCH_DIR/app kopiert; der freigegebene Ordner bleibt unverändert.
# Modelle/Runner liegen in $V13_BENCH_DIR/home und werden bei Wiederholung per Hash wiederverwendet.
set -Euo pipefail
{ # ganzer Lauf in einem Block: Bash liest das Skript vorab, Änderungen während eines Laufs brechen ihn nicht
SRC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
MODE=default
ARGS=()
for a in "$@"; do
  case "$a" in
    --units) MODE=units;; --smoke) MODE=smoke;; --full) MODE=full;; --candidates) MODE=candidates;; --semantic) MODE=semantic;; --suite) MODE=suite;;
    *) ARGS+=("$a");;
  esac
done
BENCH="${V13_BENCH_DIR:-${TMPDIR:-/tmp}/v13-bench}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${V13_BENCH_OUT:-$(dirname "$SRC")/bench-results}/$STAMP"
APP="$BENCH/app"; export V13_HOME="$BENCH/home"
mkdir -p "$BENCH" "$OUT" "$V13_HOME"
PY="$(command -v python3)"
log(){ printf '[bench %s] %s\n' "$(date -u +%H:%M:%S)" "$*" | tee -a "$OUT/bench.log"; }

log "Quelle $SRC -> $APP"
rm -rf "$APP"; mkdir -p "$APP"
(cd "$SRC" && tar --exclude='__pycache__' --exclude='*.pyc' -cf - .) | (cd "$APP" && tar -xf -)
# Canon fehlt in reinen Code-Kopien: aus blueprint/ ergänzen, Hash wird von verification.py geprüft.
CANON="docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md"
if [[ ! -f "$APP/$CANON" && -f "$(dirname "$SRC")/blueprint/$(basename "$CANON")" ]]; then
  mkdir -p "$APP/docs/canon"; cp "$(dirname "$SRC")/blueprint/$(basename "$CANON")" "$APP/$CANON"
fi

declare -A RC
run(){ local name="$1"; shift; log "START $name"; local t0=$SECONDS
  ( cd "$APP" && "$@" ) >"$OUT/$name.log" 2>&1; RC[$name]=$?
  log "ENDE  $name rc=${RC[$name]} ($((SECONDS-t0))s)"; }

export PYTHONPATH="$APP" NEEDLE_TELEMETRY=0 DO_NOT_TRACK=1 V13_NO_AUTOSTART=1
run units "$PY" -m unittest discover -s tests -p 'test_*.py'
if [[ "$MODE" == suite ]]; then
  ln -sfn "$(dirname "$SRC")/bench-results" "$BENCH/bench-results"  # Gate-Belege ../bench-results/ gelten auch in der Kopie
  run suite "$PY" "$APP/scripts/measure_suite.py" --out "$OUT/suite"
elif [[ "$MODE" != units ]]; then
  run setup bash "$APP/setup.sh"          # Download+Hash-Check, Build, selftest, probe
  [[ -f "$V13_HOME/exports/native-probe.json" ]] && cp "$V13_HOME/exports/native-probe.json" "$OUT/"
  if [[ "$MODE" == candidates ]]; then
    run candidates "$PY" "$APP/scripts/cloud_candidates.py" --home "$V13_HOME" --cache "$BENCH/candidates" --out "$OUT/candidates" "${ARGS[@]}"
  elif [[ "$MODE" == semantic ]]; then
    run semantic "$PY" "$APP/scripts/semantic_recall_bench.py" --home "$V13_HOME" --cache "$BENCH/candidates" --out "$OUT/semantic_recall.json"
  elif [[ "$MODE" != smoke ]]; then
    ACC=(--installed-home "$V13_HOME" --archive-dir "$OUT/acceptance")
    [[ "$MODE" == full ]] || ACC+=(--quick)
    run acceptance "$PY" "$APP/scripts/acceptance.py" "${ACC[@]}" "${ARGS[@]}"
  fi
fi

"$PY" - "$OUT" "$MODE" "$SRC" <<'PY'
import json,sys,re,pathlib,platform,hashlib
out,mode,src=pathlib.Path(sys.argv[1]),sys.argv[2],sys.argv[3]
def tail(n):
    p=out/f'{n}.log'; return p.read_text(errors='replace').splitlines()[-15:] if p.exists() else None
units=(out/'units.log').read_text(errors='replace') if (out/'units.log').exists() else ''
m=re.search(r'Ran (\d+) tests',units); f=re.search(r'FAILED \((.*)\)',units)
res={'stamp':out.name,'mode':mode,'source':src,'platform':platform.platform(),'python':platform.python_version(),
     'units':{'ran':int(m.group(1)) if m else None,'ok':bool(re.search(r'^OK',units,re.M)),'failed':f.group(1) if f else None},
     'logs':{n:tail(n) for n in ('setup','acceptance','candidates','semantic','suite')}}
probe=out/'native-probe.json'
if probe.exists():
    try:
        d=json.loads(probe.read_text()); res['probe']={k:d.get(k) for k in ('status','ok','passed','smoke_valid') if k in d}
    except Exception as e: res['probe']={'error':str(e)}
(out/'result.json').write_text(json.dumps(res,indent=1,ensure_ascii=False))
print(json.dumps({'result':str(out/'result.json'),'units':res['units']},ensure_ascii=False))
PY
log "Ergebnis: $OUT/result.json"
FAIL=0; for k in "${!RC[@]}"; do [[ "${RC[$k]}" == 0 ]] || FAIL=1; done
exit $FAIL
}
