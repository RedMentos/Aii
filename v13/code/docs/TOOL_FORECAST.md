# Werkzeug-Folgen-Prädiktor im Live-Pfad (SHADOW) — Thread „Nächste offene Pakete M“, 2026-10-12

## Was es ist

Der in Action-JEPA Runde 7 (`calc`) und Runde 8 (`sandbox_note`) vorregistriert bestätigte Kandidat
(feste Mittelwert-Delta-Basis + Ridge-Rest, `scripts/action_jepa_round6_ridge.py`, Taps `l_out-11` letzter Token,
Arm `full`, Seed 13 — Auswahl vor jeder Live-Nutzung fest) läuft jetzt im echten Werkzeugpfad mit:

- **Vor der Wirkung:** `v13/toolforecast.py` ordnet einen Aufruf einer bestätigten Welt zu
  (`calc`: `N*2`, `N+15`, `N/4`, `N-7`; Notiz-Bearbeitung: `" Done."` anhängen, `"Urgent: "` voranstellen, Großschreibung),
  tappt den Vorzustand nativ und sagt den Folge-Latent voraus. Die Vorhersage (mit beiden Kontrollen Kopie und
  Mittelwert-Delta) wird gespeichert, ihre ID steht im IH-H29-Feld `predicted` des Aufrufs und damit in der
  `CorollaryCopy` der Aktions-Transaktion — vor dem Effekt festgeschrieben.
- **Nach der Wirkung:** Ergebnistext aus dem Werkzeug selbst (Rechenergebnis bzw. zurückgelesene Notiz), Tap mit
  demselben Encoder, quadratischer Fehler gegen Vorhersage und Kontrollen; Statistik je Welt/Handlung,
  Telemetrie `tool_forecast`. Idempotent je Vorhersage, übersteht Neustart (Zustand `TOOL_FORECAST`).
- **Nichts liest die Vorhersage** (kein Gate, keine Antwort, kein Wecken, kein Lernschritt). Aufrufe außerhalb der
  Welten bekommen keine Vorhersage, nur einen Grund (`CALC_EXPRESSION_NOT_IN_WORLD`, `NOTE_EDIT_NOT_IN_WORLD`, …).
  `undo` ist live nicht zugeordnet (der Vorzustand einer Rücknahme ist ein anderer als in Runde 8).
- AG2-Grounding bekommt den Aufruf wie bisher, aber ohne die Latent-Vorhersage (sein Häufigkeits-Modell erwartet
  `{'outcome':…}`), damit seine Fehlerrate unverändert bleibt.

Neu im Live-Pfad: `ToolStep.plan` erkennt „Mark note X as done“, „Make note X urgent“, „Uppercase note X“ als
Bearbeitung einer bestehenden Sandbox-Notiz (WRITE_LOCAL → immer PROPOSED mit Vorschau, nur per `:tx approve`).

## Bedienung

```
python3 scripts/install_tool_forecast.py install --home <HOME> --tool <native_layer_taps> --model <Qwen3.5-0.8B-Q4_0.gguf>
:toolforecast shadow      # an (Standard OFF: jede Vorhersage kostet einen nativen Prefill-Prozess)
:toolforecast status      # Zähler, Statistik je Handlung, letzte Messungen
:toolforecast score       # offene Vorhersagen nachmessen (z. B. nach Encoder-Installation)
```

Bau des Tap-Werkzeugs wie Thread F (`docs/continuation-20261012-action-jepa-native-seeds.md`): vendorte llama.cpp
aus dem sdist `llama-cpp-python==0.3.36`, cmake-Target `llama`, dann
`g++ -O2 -std=c++17 scripts/native_layer_taps.cpp -I…/include -I…/ggml/include -L…/build/bin -lllama -lggml -lggml-base`.

## Bindung und Parität

- `specs/tool-forecast.json`: Checkpoint-/Metrik-/Paritäts-Hashes, Herkunft (Ergebnis-ZIP `4e66fa56…` bzw. `330db432…`),
  Erfassungs-Encoder (GGUF `57d19977…`, Tool `c00d6829…`, Schicht 11, letzter Token, RMS-Normierung).
- `build-assets` prüft, dass die Laufzeitformel die gemessene Test-MSE aus den gespeicherten Taps reproduziert
  (max. relative Abweichung 1,2e-7, float32-Summationsreihenfolge).
- Das neu gebaute Tap-Werkzeug ist **nicht bitgleich** zum Erfassungs-Build (anderes Binary, Thread-Zahl ohne Einfluss;
  cos ≥ 0,9998, relative RMS-Abweichung ≤ 1,8 %). `install` verlangt deshalb das eigene Gate des Kandidaten auf seiner
  Test-Partition mit dem neuen Encoder (Vorhersage < 0,98 × beste Kontrolle je Handlung) und schreibt `encoder.json`
  nur bei PASS. Cloud-Ergebnis: **PASS**, Verhältnisse zur besten Kontrolle calc .09–.19, Notiz .06–.11 (gespeicherte
  Taps: .09–.18 / .06–.11). Auf dem Redmi muss `install` dort neu laufen (eigener Build, eigene Parität).

## Am Handy messen: `bash TESTEN_TOOLFORECAST.sh` (2026-10-12, Thread M)

Ein Befehl nach `setup.sh`, ohne laufenden Chat: (1) baut `native_layer_taps` gegen die installierte, gepinnte
b10964-Laufzeit (gleiche Quell-Archiv-/Header-Prüfung und exakte Bibliotheken wie `test_native_prefill_port`, clang
`-Wall -Wextra -Werror`), (2) `install` mit Paritäts-Gate gegen das installierte B2-GGUF, (3) dieselbe Live-Prüfung
mit festem Plan `specs/tool_forecast/live-plan.json` (= vorregistrierter Plan). Bericht
`~/v13/exports/tool-forecast-<Zeit>/report.json` zum Hochladen. Danach kann `:toolforecast shadow` im Chat vorhersagen.

- `native_layer_taps.cpp`: lädt bei Builds mit dynamischen ggml-Backends (b10964-Release) die CPU-Backends
  (`V13_GGML_BACKEND_DIR`), Kontext 512 statt 2048 Tokens. Für den statischen Erfassungs-Build bitgleiche Ausgabe geprüft.
- Cloud-Probelauf genau dieses Wegs mit dem b10964-Linux-Release (`docs/proofs/continuation-20261012/tool-forecast-device-cloud/`):
  Parität PASS (104 s), Live **LIVE_PATH_CONFIRMED** 245/245, Verhältnisse wie oben (calc .17–.24, Notiz .06–.10),
  Median 2,7 s je Aufruf, **Spitzen-RSS des Tap-Prozesses ≈ 1 GB** (Modell + CPU-Repack). Auf dem 6-GB-Redmi deshalb
  nie neben einem Chat; ob Modi/RSS-Budget (Thread N) das Werkzeug dort zulassen, zeigt erst der Handy-Lauf.

## Live-Prüfung (vorregistriert, `docs/proofs/continuation-20261012/tool-forecast-live/`)

**LIVE_PATH_CONFIRMED**, 245/245 Aufrufe gemessen. Nie benutzte Werte/Notizen der Welten: Vorhersage bei
.17–.24 (calc) bzw. .05–.10 (Notiz) der besten Kontrolle. Außerhalb der Welten (nur Bericht): calc mit Werten
1000–9999 .33–1.13 (`quarter` schlechter als Kontrolle), freie Notizsätze .63–.89. Median 2,55 s je Aufruf in der Cloud.

## Befund nebenbei (nicht behoben, Besitz Thread G / `agi/tools.py`)

Ein per `:tx approve` freigegebener Aufruf trägt die `event_id` des ursprünglichen Turns; `_execute` legt sein Ergebnis
deshalb in den Provisional-Puffer dieses längst abgeschlossenen Turns, der nie mehr abgerechnet wird → AG2-Grounding
erhält freigegebene Sandbox-Schreibvorgänge nie (TTL-Tombstone). Die Vorhersage-Messung umgeht das, indem
`transaction.operator_command` nach `approve` direkt misst.

## Grenzen

Geschlossene Welten der Runden 7/8; freie Notizen und Werte außerhalb 1–999 liegen außerhalb der Messung.
Nur Linux-x86-Cloud, kein Redmi (Latenz pro Tap-Prozess, RSS). SHADOW, keine Autorität,
`canonical_architecture_complete=false`.
