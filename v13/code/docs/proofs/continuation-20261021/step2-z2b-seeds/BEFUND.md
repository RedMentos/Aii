# Befund WP-Z2b: STEP2 Rauschband (Seeds 14–16) + gezielte Fragen an die Körper (2026-10-21)

Vorregistrierung `PREREG.md` (Commit `f5b9d03`, vor Inferenz gepusht). Linux-Cloud x86_64, 4 CPUs, **kein Redmi**.
Modelle/Runner frisch installiert und byte-gleich mit Z2: B1 LFM2.5-1.2B `bb741ebb…`, B2 Qwen3.5-0.8B `57d19977…`, C3 LFM2.5-350M `3d10b6ab…`,
llama.cpp b10964 `79e31218…`. 12 Läufe × 70 Zeilen = 840 Zeilen, alle RECORDED, 0 Fehlerzeilen; dazu Werkzeug-Replay je Lauf (840 Zeilen).
CI = 95 %, Cluster-Bootstrap über die 10 Episoden (Seeds einer Episode bleiben zusammen).

## Ergebnis: `Z2B_DIVERGENCE_NOT_SUPPORTED` (Gate FAIL, ehrlich)
| Kriterium (primär CQ = zwei Körper + gezielte Frage, Mittel Seeds 14–16) | Wert | erfüllt |
|---|---|---|
| 1 `both_exact` > bester Einzelkörper (b1_only), CI > 0, jeder Seed | .611 vs .592, Differenz +.019 [−.075, +.106]; Seeds 15/16 nicht größer | ✗ |
| 2 B1 und B2 gewinnen je eine Episode in ≥ 2 Seeds | nur 1 Seed | ✗ |
| 3 komplementäre Fehlerprofile | Optionsfelder b1 .99 / b2 .37 (✓ .62), Regelfelder b2 .03 / b1 .20 (✗) | ✗ |
| 4a > gleiches Modell gleiche Policy | +.042 [−.056, +.125] | ✗ |
| 4b > gleiches Modell nur anderer Prompt (DQ) | +.042 [−.058, +.131] | ✗ |
| 5 Struktur; Arme taten, was sie sagen | alles RECORDED; CQ/DQ 120/120 Angebote mit Frage, C/D 0/120 | ✓ |
§99 „zwei Körper lohnen die Handy-Kosten“: **nein** (CQ − DQ `both_exact` −.014 [−.111, +.083]) → die billigere Form (ein Körper + zwei Zustände) reicht.

## Die zwei Fragen aus Z2, beantwortet
**1. War Z2 Rauschen?** Ja. Mit drei neuen Seeds schwankt Arm C `both_exact` zwischen .308 und .450 (Spanne .142); Z2-Wert .325 liegt im Band.
Der Z2-Abstand „zwei Körper − b1_only“ (−.008) liegt im Seed-Band [−.017, +.108], „ein Körper − zwei Körper“ (+.042) im Band [−.058, +.100].
Weder „zwei Körper schlechter als B1“ noch „LFM als B2 besser als Qwen“ ist belegt (D − C `both_exact` +.019 [−.072, +.108]; `b2_only` −.047 [−.117, +.017]: **NO_CLEAR_DIFFERENCE**).

**2. Hilft eine gezielte Frage an die Körper?** Ja, deutlich, und das CI schließt 0 aus:
- zwei Körper: C .378 → CQ .611, **+.233 [+.122, +.344]** (QUERY_HELPS); ein Körper: D .397 → DQ .625, **+.228 [+.100, +.378]**.
- Exakte Entscheidungen `both_exact` (von 30): C 4 → CQ 8; D 2 → DQ 10. `both_none` CQ 13/30.
- **0 falsch festgelegte Entscheidungen** in allen 840 Werkzeug-Zeilen (Werkzeug sagt UNKNOWN statt zu raten).

## Warum trotzdem kein Zwei-Körper-Gewinn: B2 ist der Engpass
Verifizierte Zitate bei C3 (Summe über 3 Seeds, je Arm 210 Zeilen; B2 ist in 150 davon beteiligt):
| | B1 Optionen | B1 Regeln | B2 Regeln | B2 Optionen | Regeln **und** Optionen in derselben `both_exact`-Zeile |
|---|---|---|---|---|---|
| C | 63 | 17 | 43 | 3 | 5 |
| CQ | **170** | 2 | 37 | 12 | 6 |
| D | 77 | 24 | 57 | 12 | 0 |
| DQ | **114** | 2 | 33 | 19 | 12 |
Die Frage macht B1 zum verlässlichen Lieferanten der Optionswerte (b1_only .31 → .59, Spanne über Seeds nur .017). B2 zitiert die alte
Regel mit oder ohne Frage nur in ~¼ der Zeilen (Qwen wie LFM). Deshalb liegt `both_exact` kaum über b1_only, und exakte SPLIT-Entscheidungen
(Regeln nur bei B2, Optionen nur bei B1) bleiben selten: CQ 1/18, DQ 5/18, C 1/18, D 0/18.
Hinweis zur Fehlerprofil-Zahl: „Regelfelder“ (remaining/eligible/action) brauchen auch die Optionswerte; b2_only kann sie bei SPLIT nie
richtig haben. Kriterium 3 ist damit für diese Fixtures streng; es wird nicht nachträglich geändert.

## Pannen, offen genannt
- Fund vorab (vor Inferenz, in PREREG): Körper-Angebote ignorierten `cfg['seed']` (immer 13). Im Skript behoben, Live-Code unverändert.
- DQ Seed 16 Versuch 1 brach nach 53/70 Zeilen ab, weil die Container-Arbeitsumgebung neu startete. Verworfen und komplett neu gelaufen;
  Zeilenwerte von Versuch 1 als `DQ_s16-attempt1-aborted.json` aufbewahrt.

## Empfehlung
- Gate bleibt FAIL: STEP2 UTILITY_FAIL und G-B-TIMESCALE-DIVERGENCE-001 offen, `canonical_gate_pass=false`. Schalter `b1_recent_source_chars` bleibt aus.
- **Kandidat für den Live-Pfad:** gezielte Frage an B1 in der aktuellen Runde („welche Optionswerte gelten, zitiere sie“). Größter gemessener
  Gewinn bisher (+.23, CI > 0), 0 falsche Entscheidungen. Einbau nur als Schalter (aus) und nach Nutzerentscheidung; die Fragen sind hier
  fest vorgegeben, im Live-Pfad müsste JEF sie selbst stellen (`fastpolicy.focus_for`), das ist ungemessen.
- Nächstes Paket: B2 dazu bringen, die alte Regel zu zitieren (z. B. B2-Fragetext mit `earlier_context`-Bezug, B2 nur Regel-Zitat statt
  Zusammenfassung, oder deterministischer Regel-Abruf aus B2s exaktem Kontext). Erst wenn B2 Regeln verlässlich liefert, kann Kriterium 1 fallen.
- Kleiner Code-Fix (eigene Entscheidung): `cognition.offer` sollte `seed=cfg['seed']` übergeben (Seed 13 = byte-gleich). Hier nicht eingebaut.

Daten: `code/bench-results/step2-z2b-seeds-20261021/` (z2b_result.json, Zusammenfassungen, Werkzeug-Replays, Logs, SHA256SUMS);
volle STEP2-Berichte (je ~3,4 MB) im Projektordner `v13/bench-results/step2-z2b-seeds-20261021/`.
