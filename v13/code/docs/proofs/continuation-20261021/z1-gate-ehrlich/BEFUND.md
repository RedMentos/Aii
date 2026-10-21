# WP-Z1 Gate-Ehrlichkeit — Befund 2026-10-21

Kein Modelllauf. Nur Auswertung vorhandener Belege mit geänderten Regeln.
Grundlage: Blueprint v10.16.1 §29, §85.1–§85.7, §89, §96 (STEP 2, STEP 5), §99, §100; `ZIELABGLEICH.md` Punkt 5h.

## Problem

`specs/gate-graph.json` meldete auf dem Projektstand **STEP2 = GREEN**. Das einzige Verdikt war
`step2-final-full-audit-20261009.json: all70_rowchecks_pass == true`, also "der Harness lief sauber durch".
Dieselbe Datei sagt `status: UTILITY_FAIL`, `canonical_gate_pass: false`, `b1_b2_each_win_an_episode: false`.
Der §96-Ausgang von STEP2 ist "measurable complementarity, bounded RSS, observer latency known". Der war nie geprüft.
Zweites Problem: ein gemessenes FAIL wurde hinter PARTIAL versteckt, sobald irgendeine andere Belegdatei fehlte.

## Änderung

1. `STEP2` geteilt in `STEP2_HARNESS` (bisherige Prüfung, darf grün sein) und `STEP2_EXIT` (§96-Ausgang mit vier Kriterien).
   STEP6, G-FOCAL-CAPACITY-003 hängen jetzt am Ausgang. G-B-TIMESCALE-DIVERGENCE-001 misst die Komplementarität selbst und hängt am Harness.
   Der Gist-Kopf in `authority.py` zeigt auf `STEP2_HARNESS` (Verhalten unverändert).
2. Neuer `blueprint`-Block je Gate: die Kriterien aus dem Blueprint-Text, jedes an einen gemessenen Wert gebunden.
   Ohne Bindung oder ohne Datei: UNMEASURED. Gelesener Wert falsch: FAIL.
   Gesetzt für STEP2_EXIT, STEP5 und alle zehn §100-Gates. Synthetische Ablationen (ablation99) zählen nicht als Messung.
3. `v13/gates.py`: neuer Status `CRITERIA_UNMEASURED` (Belege vollständig, Blueprint-Kriterium ungemessen).
   Ein gemessenes FAIL ergibt immer `EVIDENCE_NOT_PASSING`, auch bei fehlenden anderen Belegen. Neue Operatoren `exists`, `nonempty`, Listenindex im Pfad.
   `authority.GATE_OK` nimmt `CRITERIA_UNMEASURED` auf (kein gemessenes FAIL). Neu: Köpfe an einem Gate mit gemessenem FAIL
   werden nicht mehr CANDIDATE. Das war laut Docstring schon die Regel, wurde aber durch PARTIAL umgangen.
4. `specs/properties29.json` + `scripts/measure_suite.py`: §29-Tabelle (24 Eigenschaften), Stand **berechnet** aus verknüpften Gates und §24-Benchmarks,
   daneben die Hand-Einschätzung aus ZIELABGLEICH zum Vergleich; dazu Tabelle aller Blueprint-Kriterien je Gate.

## Ergebnis auf dem Projektstand (mit allen Belegen, `SUITE-projektstand.md`)

| | vorher | nachher |
|---|---|---|
| STEP2 | GREEN | STEP2_HARNESS GREEN, **STEP2_EXIT EVIDENCE_NOT_PASSING** (Komplementarität FAIL, B1/B2 gewinnen nicht je eine Episode, RSS-Budget ungemessen, Observer-Latenz Cloud bekannt 3,8 s) |
| STEP5 | GREEN | CRITERIA_UNMEASURED (Lebenszyklus-Beweis PASS; TRAIN_RUNNER_PROOF am Gerät, echte ModulatorPackets, echte Eligibility ungemessen) |
| Gates gesamt | 8 GREEN, 1 EVIDENCE_NOT_PASSING, 10 PARTIAL | 7 GREEN, 5 EVIDENCE_NOT_PASSING, 1 CRITERIA_UNMEASURED, 7 PARTIAL |
| §100-Gates | 0/10 grün | 0/10 grün; 4 davon jetzt mit gemessenem FAIL sichtbar: TIMESCALE, CALLOSUM (B3 L1), FOCAL (Rauschband), REPLAY (CONSOLIDATION_PARTIAL) |
| §29 maschinell | – | 3 erreicht, 15 teilweise, 6 fehlen (Hand-Einschätzung 21.10.: 8 / 14 / 2) |

Die maschinelle §29-Zählung ist strenger als die Hand-Einschätzung, weil "nur Unit-Test" (TESTED) nicht als erreicht zählt
(z. B. Nr. 14 Provenance, 24 endliche Ausgabe) und ein gemessenes Gate-FAIL die Eigenschaft auf "fehlt" setzt (Nr. 2, 8, 9).

## Grenzen

- Die Zuordnung Eigenschaft → Gates/Benchmarks ist kuratiert, nicht aus dem Blueprint ableitbar.
- `bounded_rss` braucht ein vorregistriertes STEP2-RSS-Budget (bisher keins; Cloud-Spitze 1,50 GB).
- Im reinen Git-Baum fehlen die meisten `docs/proofs`-Belege; dort stehen fast alle Gates auf PARTIAL. Maßgeblich ist der Projektstand.
- Keine Gate-Beförderung, kein Original-Gate aufgeweicht.
