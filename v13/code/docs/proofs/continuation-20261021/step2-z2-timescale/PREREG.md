# Vorregistrierung WP-Z2: STEP2 mit Information, die nur B1 hat (2026-10-21)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2_timescale.py`, Tests `code/tests/test_step2_z2.py`.
Gate aus Kanon §85.1 `G-B-TIMESCALE-DIVERGENCE-001` (komplementäre Fehlerprofile, Kombination schlägt zwei gleiche Instanzen, 4 Kontrollen).

## Warum neu
Alle bisherigen STEP2-Fixtures gaben B1 nichts Eigenes: Im Code hält B1 aus der Vorrunde nur seine eigene 240-Zeichen-**Hypothese**,
nie exakten Quelltext (`cognition.body_context` liefert für B1 `[]`). Das Eignungs-Werkzeug zählt nur exakte Zitate, also konnte B1
nie etwas beitragen (b1_only 5/10, 20.10.). Ein Zwei-Körper-Gewinn war damit ausgeschlossen, bevor gemessen wurde.

## Neuer Baustein (Schalter, aus = live, byte-gleicher Pfad)
`b1_recent_source_chars` (0..960, Standard 0). An: B1 behält den **exakten Quelltext seiner letzten Runde** zum selben Thema bis N Zeichen
(`recent_source`), darf daraus zitieren; gleiche Sitzungs-/Generations-/Modell-/Themenprüfung wie B2. Das ist die Zeitskalen-Trennung aus §85.1
(integration_horizon, segment_span, exactness_bias): B1 = eine Runde, fein (600 Zeichen), B2 = bis 4 Runden, grob (je 240 Zeichen Auszug).

## Fixtures (10 Episoden, eingefroren im Skript)
Jede Episode: Regel-Runde (alt) → Ablenker „Project Zenith“ → letzte Runde → Frage. C3 sieht nur die Frage und die Body-Offers, nie den Verlauf.
- **SPLIT** (6: Kestrel, Lumen, Meridian, Nimbus, Orion, Perseus): Regeln nur in der alten Runde, Optionswerte nur im Datenblatt der letzten Runde
  **ab Zeichen ~305** (außerhalb von B2s 240-Zeichen-Auszug, innerhalb von B1s 600er-Fenster). Braucht beide Körper.
- **RULE** (2: Quasar, Rigel): Optionen in der Frage, Regeln nur alt → B2 reicht.
- **DETAIL** (2: Sirius, Tycho): Regeln in der Frage, Optionen nur im Datenblatt → B1 reicht.
Orakel per `eligibility.recipe`; Aktionen A/B/NONE, nie UNKNOWN (sonst gewinnt ein Körper ohne Information „gratis“).
Die Lage der Optionen hinter Zeichen 240 ist Absicht und wird offen genannt: getestet wird, ob das System die Horizont-Trennung nutzt.

## Ablauf
Unveränderter STEP2-Harness (`tests/integration_step2_utility.py`, 7 Varianten, echte B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M, llama.cpp b10964),
nur `FIXTURES` und die drei Vorbereitungs-Runden in einer privaten Modulkopie ersetzt. Danach Werkzeug-Replay jeder Zeile (`scripts/step2_tool_replay.py`).
Alle Arme mit `b2_offer_body_state=false`, `offer_quote_min_chars=90` (wie 20.10.).

| Arm | Körper | Zitat-Kontext | B1-Fenster |
|---|---|---|---|
| A | zwei Körper | 0 | 0 (live) |
| B | zwei Körper | 200 | 0 |
| **C (primär)** | zwei Körper | 200 | 600 |
| D | ein Körper + zwei Zustände (`shared_body_dual_state`) | 200 | 600 |
| E | zwei Körper | 0 | 600 |

Kontrollen: gleiches Modell gleiche Policy = C `same_policy_dual`; gleiches Modell nur anderer Prompt = D `prompt_only_dual`;
ein Körper + zwei Zustände = D `both_exact`; zwei Körper = C `both_exact`.

## Primäre Entscheidung (Werkzeug-Nutzen, alle 10 Episoden, Arm C/D) — `Z2_DIVERGENCE_SUPPORTED` nur wenn alles gilt
1. C `both_exact` > max(C `b1_only`, C `b2_only`)
2. B1 und B2 gewinnen je mindestens eine Episode gegeneinander (unveränderte `paired_utility`-Regel)
3. Komplementäre Fehlerprofile: b1_only − b2_only bei Optionsfeldern ≥ 0,25 **und** b2_only − b1_only bei Regelfeldern (remaining, eligible, action) ≥ 0,25
4. C `both_exact` > C `same_policy_dual` und > D `prompt_only_dual`
5. Struktur: keine STRUCTURAL_FAIL/INCOMPLETE
§99 „zwei Körper lohnen die Handy-Kosten“ nur, wenn 1–5 gelten **und** C `both_exact` > D `both_exact`.
Ist D `both_exact` ≥ C `both_exact`, darf das Redmi die billigere Form nutzen (Kanon erlaubt das ausdrücklich).

Sekundär: dasselbe ohne Werkzeug (C3 frei), Arme A/B/E (Wirkung von Schalter und Zitat-Kontext einzeln), Nutzen je Typ, wer welche Information
tatsächlich als verifiziertes Zitat an C3 lieferte (`information_access`).

## Erwartung vor dem Lauf
- A/B: B1 liefert nie Optionswerte als Zitat → SPLIT/DETAIL UNKNOWN, Gate FAIL (wie alle bisherigen Läufe).
- C: Gewinn nur, wenn LFM-B1 die Options-Sätze aus `recent_source` wirklich zitiert und Qwen-B2 die alten Regeln; Unsicherheit hoch,
  weil B1 bisher selten exakt zitierte und `offer_quote_min_chars=90` lange Zitate verlangt. Kein Ergebnis wird vorweg angenommen.
- Ohne Werkzeug erwartet 0 exakt (C3 rechnet nicht).

## Grenzen
Linux x86 Cloud, kein Redmi; 10 Episoden, ein Seed → diagnostisch, kein Kanon-PASS (`canonical_gate_pass` bleibt false).
Schalter bleibt im Code aus; Einschalten nur nach Nutzerentscheidung. Altes STEP2 UTILITY_FAIL bleibt bestehen.
