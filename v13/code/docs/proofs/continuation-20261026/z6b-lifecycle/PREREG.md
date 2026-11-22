# WP-Z6b Vorregistrierung: §24.32 Fluid Experience Lifecycle (vor dem Lauf committet)

Frage: Durchläuft der echte STEP5-Lerner (Routen-Kopf auf Needle-Embeddings, NumPy-Worker, `learner.shadow()`,
`:approve`, `store.rollback`) die Lebenszyklus-Wege L0→L11 sinnvoll, und spart eine adaptive Regel unnötige Updates,
ohne schlechter zu werden?

Aufbau `code/scripts/z6b_lifecycle_bench.py`, Seed 71, je Arm eine frische Runtime, gleicher Strom:
- 40 record-only Ereignisse (ohne Rückmeldung) → dürfen kein Update auslösen.
- Phase 1: 6 Pakete × 8 menschliche Routen-Korrekturen (je 2 pro Route).
- Phase 2 (neue Evidenz): der Nutzer will „Hälfte von X“-Fragen jetzt als `simple`; 4 Pakete × 8, davon je 4 neu
  beschriftet → Rückkehr L11/Wiederöffnen.
- Arme: `fixed` (Shadow nach jedem Paket), `adaptive` (Shadow nur, wenn der aktive Kopf ≥ 25 % des Pakets falsch
  routet, oder noch kein Kopf da ist), `none` (kein Lernen). Die Harness spielt den Menschen und gibt jeden
  PENDING_APPROVAL-Kandidaten frei. Bewertung durch die Bench auf festem Held-out-Satz (je 8 neue Umschreibungen pro
  Route + 8 Hälfte-Fragen, deren Label nach der Verschiebung `simple` ist); die Regeln sehen den Held-out-Satz nie.
- Am Ende Rücknahme der letzten Freigabe; sie muss die vorher gemessene Eltern-Genauigkeit (gleiches Label-Set) exakt
  wiederherstellen. Danach Neustart.

Messgrößen (§24.32): unnötige Updates (Kandidat < +1 Punkt gegen den aktiven Kopf), Zeit bis nutzbare Verbesserung
(Korrekturen bis Held-out ≥ 90 % in Phase 1; bis Hälfte-Fragen ≥ 80 % in Phase 2), falsche Freigaben (Genauigkeit
−1 Punkt oder unveränderte Fragen −5 Punkte), Rücknahme-Erfolg, Behalten (unveränderte Fragen Ende/Ende Phase 1),
Freigabe-Last, Lernrate je Route.

Kriterien (`Z6B_LIFECYCLE_ADAPTIVE_PASS` nur wenn alle gelten):
C1 adaptive ≤ 70 % der unnötigen Updates von fixed (und fixed hat welche); C2 Endgenauigkeit adaptive ≥ fixed − 3 Punkte;
C3 falsche Freigaben adaptive ≤ fixed; C4 Rücknahme stellt in beiden Armen exakt wieder her; C5 Behalten adaptive ≥ 90 %;
C6 record-only löst in keinem Arm ein Update aus.
Beschreibend (kein Kriterium): ob Phase 2 überhaupt gelernt wird (Hälfte-Fragen ≥ 80 %).

Vorlauf (Smoke, Seed 5, nur fixed, vor dieser Vorregistrierung, nicht gewertet): in Phase 2 scheiterten alle Kandidaten an
der Prüfung (EVALUATED_FAIL), Hälfte-Fragen 0 %; dazu ein Fehler der Bench beim Rücknahme-Vergleich (falsches Label-Set),
behoben vor diesem Lauf.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, ein Seed, Mensch durch Regel ersetzt, Cloud.
