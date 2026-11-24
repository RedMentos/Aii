# Werkzeug-Folgen-Prädiktor im Live-Pfad — Live-Prüfung (Thread „Nächste offene Pakete M“, 2026-10-12)

Vorregistriert in `preregistration.json` (GitHub `ee57c61`, vor dem Lauf). Skript `scripts/tool_forecast_live_check.py`,
Laufzeit `v13/toolforecast.py`, Encoder: neu gebautes `native_layer_taps` + Qwen3.5-0.8B-Q4_0 (`57d19977…`), Parität PASS.
Jeder Aufruf lief durch die Laufzeit-Bausteine in einem frischen Store: Vorhersage vor der Wirkung (`predicted` in der
Transaktion), echter `calc`- bzw. `sandbox_note`-Aufruf, Messung nach der Wirkung. Notizen über
`ToolStep.plan → propose_call → :tx approve` (Skript gibt als Nutzer frei).

## Ergebnis: **LIVE_PATH_CONFIRMED** (245/245 gemessen)

Verhältnis mittlere Vorhersage-MSE / beste Kontrolle (Kopie, Mittelwert-Delta) je Handlung:

| Arm | n je Handlung | Verhältnisse | Gate |
|---|---|---|---|
| calc, nie benutzte Startwerte 1–999 | 25 | double .22, add_15 .17, quarter .24, subtract_7 .18 | PASS |
| Notiz, nie benutzte Runde-8-Notizen | 25 | append_done .05, prefix_urgent .09, uppercase .10 | PASS |
| calc außerhalb 1–999 (nur Bericht) | 10 | double .39, add_15 .59, **quarter 1.13**, subtract_7 .33 | – |
| freie Notizsätze (nur Bericht) | 10 | append_done .63, prefix_urgent .88, uppercase .89 | – |

- In der gemessenen Welt hält der Kandidat im Live-Pfad, was Runden 7/8 zeigten (Test dort .09–.18 / .06–.11).
- Außerhalb verliert er deutlich: bei großen Zahlen ist `quarter` schlechter als die Kontrolle, freie Sätze liegen nur
  knapp unter ihr. Das ist der erwartete Grenzbefund, kein Gate.
- Median 2,55 s je Aufruf (zwei native Tap-Prozesse mit Modellladen) auf 4 Cloud-CPUs; auf dem Redmi ungemessen.

## Grenzen

Skript als Nutzer, geschlossene Welten, Linux-x86-Cloud. SHADOW: nichts liest die Vorhersage. Kein Redmi-Nachweis,
keine Lern- oder Empfängerautorität, `canonical_architecture_complete=false`.

Dateien: `report.json` (Plan, Encoder mit Parität, Arme, Laufzeitbericht), `rows.json` (jeder Aufruf mit MSE und Ergebnistext).
