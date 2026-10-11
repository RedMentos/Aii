# C2-Benchmark Needle 3 vs. FunctionGemma-270M (§57, G12C, WP-V7) — 2026-10-10, Cloud x86

Korpus `code/specs/c2-benchmark.json`: 96 englische Prompts, 24 je Route (simple/detail/gist/both), Labels von Claude aus der
Tool-Definition `select_processing` geschrieben (keine Nutzer-Labels). Skript `code/scripts/c2_benchmark.py`.

| Kandidat | Genauigkeit | Macro-F1 | gültige Calls | Latenz p50 | Peak-RSS | Datei |
|---|---|---|---|---|---|---|
| Regex-Gerüst (heute Fallback) | 48 % | .47 | 100 % | 0 ms | – | – |
| Needle 3, nativer Tool-Call | 17 % | .16 | 100 % | 115 ms | 102 MB | 35 MB |
| **Needle-Einbettung + Softmax-Kopf (4-fach CV)** | **85 %** | **.85** | 100 % | 38 ms | (wie Needle) | 35 MB |
| FunctionGemma-270M Q8, freie Tool-Wahl | 4 % | .07 | 10 % | 366 ms | 736 MB | 292 MB |
| FunctionGemma-270M Q8, per JSON-Schema erzwungen | 25 % (immer „simple“) | .10 | 100 % | 693 ms | 800 MB | 292 MB |

Befund:
- Zero-shot taugt keiner der beiden als Router. Needles native Konfidenz sagt Richtigkeit nicht voraus (AUROC .52).
- Needles Einbettungen tragen die Route aber gut: ein kleiner Kopf erreicht 85 %. Das ist genau der Blueprint-Weg „separate
  JEF-fast-Heads bleiben Baseline“ (G12C) und existiert schon als `C2_EXTERNAL_ROUTE_HEAD` (lernt aus `:feedback … --learn`).
- FunctionGemma ist 8× größer im RAM, 3–6× langsamer und ohne Fine-Tuning unbrauchbar; llama.cpp b10964 parst sein natives
  Call-Format nicht (Skript liest es selbst). Kein C2-Ersatz.
- Empfehlung: Needle bleibt C2-Encoder; Routing über den gelernten Kopf, sobald echte Nutzer-Labels da sind. Kein Modelltausch.

Grenzen: Cloud-CPU statt Redmi (Latenz/RSS nur relativ), Autor-Labels, n=96, Probe-Kopf ist kein freigegebener Kopf (der echte
läuft über control_calibration mit Retention-Gate).
