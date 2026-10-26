# Befund WP-Z2k: jüngster zitierter Regelwert — bestätigt (2026-10-26)

Vorregistrierung `PREREG.md` (Commit `7087f616`, vor Inferenz gepusht). Linux-Cloud, 4 CPUs, kein Redmi. 6 Läufe × 70 Zeilen (A4/S4 × Seeds 38–40),
alle RECORDED, kein Abbruch.

## Ergebnis laut Vorregistrierung: `Z2K_READER_CONFIRMED`
| | A4 nur Wächter | A4 + Leser | S4 nur Wächter | **S4 + Leser** |
|---|---|---|---|---|
| exakt (210 Zeilen) | 7 | 7 | 8 | **36** |
| davon REVISED / TWICE / CONFIRM | 3 / 0 / 4 | 3 / 0 / 4 | 0 / 0 / 8 | **22 / 6 / 8** |
| `both_exact` exakt (30 Zeilen) | 1 | 1 | 2 | **14** |
| falsch festgelegt | 0 | 0 | 0 | **0** |
| ohne Wächter falsch | 15 | | 65 | |
- S4, Leser − nur Wächter je Episode: +.93 [+.43, +1.50] (untere CI-Grenze > 0); **keine** Zeile verloren. Gültigkeit 100 %, Konsistenz und Struktur erfüllt.
- Werkzeug-Nutzen `both_exact` (ohne Leser gemessen): A4 .519, S4 .675; b1_only .52 / .51. B2-Regelquote A4 .17, S4 .52.
- A4 profitiert nicht: dort steht die Änderungsnotiz fast nie in den Zitaten, und der Leser nimmt nur Werte, die zitiert sind.

## Was das heißt
Erstmals werden **geänderte Regeln** in nennenswertem Umfang richtig entschieden (S4: 28 von 168 REVISED/TWICE-Zeilen statt 0), ohne eine einzige falsche
Festlegung. Die Kette, die das trägt: B2-Gedächtnis groß genug (1536 Zeichen) → B2 wählt ganze frühere Notizen (`b2_quote_choices=sources`) →
Werkzeug liest den jüngsten zitierten Regelwert (`rule_reader='newest_quoted'`) → Wächter verwirft alles Überholte.

## Grenzen (ehrlich)
- Der Leser ist ein festes Regelwort-Muster (Budget/Deadline/Local-only) im Eignungs-Werkzeug, kein allgemeines Verstehen; C3 liefert weiter die
  Optionen. Das Ergebnis zeigt, dass das 350M-Modell die Aktualität nicht selbst erkennt.
- Die Mehrheit bleibt UNKNOWN (174/210 bei S4), meist weil B2 nicht alle Notizen wählt oder C3 die Optionen nicht vollständig liest.
- Linux-Cloud, kein Redmi. Schalter bleiben live Standard/aus, bis der Nutzer entscheidet.

## Empfehlung
Nächstes Paket **WP-Z2l**: die ganze Kette (1536 + `sources` + Wächter + Leser) gegen die STEP2-Kriterien messen, mit Ein-Körper-Kontrolle
(gleiches Modell, zwei Zustände) — beantwortet die ursprüngliche Frage, ob zwei Körper ihren Preis wert sind.

Daten: `code/bench-results/step2-z2k-reader-20261026/`; volle STEP2-Berichte im Projektordner `v13/bench-results/step2-z2k-reader-20261026/`.
