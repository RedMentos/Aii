# WP-Z3 C3-Konsument isolieren — Befund (2026-10-21)

**Status `RECORDED`, 819/819 Zeilen (39 Fixtures × 3 Seeds × 7 Arme), 0 Fehler, Bindungen unverändert.
Vorregistriertes Urteil: `NO_CONSUMER_PATH`.** Kein Gate, keine Autorität; STEP2 `UTILITY_FAIL` unverändert.
Registrierung `e33d9583…` (Commit vor dem Lauf), Report `run/report.json`, Zeilen `run/rows.json.gz`
(entpackt sha256 `9da61fca…` = `rows_sha256` im Report). Linux-Cloud-CPU, 4 Kerne, kein Redmi; Modelle byte-gleich zum Pilot.

## Ergebnis (gepoolt, n = 117 je Arm)

| Arm | Entsch. exakt | streng exakt | Aktion richtig | falsche Festlegung | UNKNOWN-Kontrollen richtig | Δ zu c3_direct (95-%-KI) |
|---|---:|---:|---:|---:|---:|---|
| c3_direct (C3 350M) | 0.000 | 0.000 | 0.154 | 0.000 | 18/18 | — |
| b2_direct (Qwen 0.8B) | 0.265 | 0.000 | 0.368 | **0.632** | 0/18 | +0.26 [0.14, 0.40] |
| b1_direct (LFM 1.2B) | 0.128 | 0.017 | 0.282 | **0.718** | 0/18 | +0.13 [0.04, 0.22] |
| c3_extract_tool (v2) | 0.513 | 0.145 | 0.513 | 0.026 | 15/18 | +0.51 [0.36, 0.67] |
| **c3_extract_tool_strict** | **0.538** | 0.145 | 0.538 | **0.000** | 18/18 | +0.54 [0.38, 0.69] |
| tool_label_c3 | 0.000 | 0.000 | 0.154 | 0.000 | 18/18 | 0.00 |
| tool_only (kein Modell) | 1.000 | 1.000 | 1.000 | 0.000 | 18/18 | +1.00 |

Seeds 13/14/15 fast gleich (Temperatur 0.1): Werkzeug-Arme identisch je Seed, b1 0.10/0.10/0.18, b2 0.26/0.26/0.28.
Kein Arm erreicht die Schwelle (≥ 0.80 exakt und ≤ 0.05 falsch). Das Urteil gilt so, wie registriert.

## Was das heißt
1. **C3 wählt nie eine Option.** 117/117 Antworten `action: UNKNOWN`, auch wenn das Werkzeug ihm die fertige Entscheidung
   als Satz vorlegt (`tool_label_c3`, z. B. „choose option A; …“). C3 ist damit als Entscheider auch nicht als „Abschreiber“
   brauchbar. Es ist allerdings vorsichtig: 0 falsche Festlegungen.
2. **Größere Körper sind schlechter, nicht besser:** B1 antwortet in 117/117 Zeilen `A`, B2 fast immer `A` oder `NONE`.
   Das ist Positions-Bias, kein Rechnen; auf allen 18 Kontrollen (fehlende/widersprüchliche Regel) legen beide sich fest.
   „B1 ersetzt C3“ ist widerlegt.
3. **C3 liest Zahlen fehlerfrei.** Im Extraktions-Arm stimmen Budget, Frist und alle Optionswerte in 117/117 Zeilen.
   **Einziger Fehler: C3 gibt `local_only` immer `true` zurück** (117/117, richtig wäre in 69 Zeilen `false`).
   Der verankerte Wächter verwirft den falschen Wert (`local_only:not_stated`) → UNKNOWN statt falscher Wahl.
4. **Die vorab vorhergesagte v2-Lücke ist real:** v2 prüft Widersprüche zwischen Zitaten nicht und legt sich auf 3 der
   18 Kontrollzeilen fest (falsch). Die vorab entworfene Gleich-Revisions-Prüfung (`strict`) schließt sie: 0 falsche Festlegungen.
5. Nachträgliche Analyse (**nicht registriert**, nur Hinweis): ersetzt man im selben Extraktionslauf nur `local_only` durch
   den deterministisch gelesenen Wert, wären 117/117 exakt, 0 falsch.

## Entscheidung für §29 Nr. 6 (kleiner Sprachkörper) und §31 R9 / §24.34
- C3 bleibt **Leser** (typisierte Zahlen), nicht Entscheider. Entscheiden muss das deterministische Rezept (Canon §6.5
  erlaubt dauerhafte Tool-Rezepte). Ein größerer Körper als Konsument bringt hier nichts.
- STEP2-Nutzen hängt damit am Konsumenten-Pfad *Werkzeug*, nicht am Zitat-Transport (der ist mit Exakt-Quellen sauber).
- Der Live-ToolStep-Pfad (Branch dq33gk, eligibility-v2) braucht vor dem Einschalten **die strict-Prüfung**, sonst
  legt er sich bei widersprüchlichen Quellen fest.

## Nächster Schritt (neue Registrierung nötig, Z3b)
Bool-Regeln nicht vom Modell lesen lassen: Rezept liest `local_only` (und optional alle Regeln) direkt hinter dem Regelwort,
C3 nur Optionswerte — vorregistriert auf dieser Kohorte **und** auf umformulierten Regeln (Paraphrasen), denn auf der
festen Wortform hier gewinnt ein reiner Parser trivial (`tool_only` 100 %). Erst die Paraphrasen zeigen, ob C3 als
Leser überhaupt etwas beiträgt.

## Grenzen
Eine synthetische Aufgabenform mit fester Wortwahl; 39 Fixtures; Cloud-CPU statt Handy; Seeds bei Temperatur 0.1
sind kaum unabhängig (Werkzeug-Arme seed-identisch). Kein Nachlauf unter dieser Registrierung.
