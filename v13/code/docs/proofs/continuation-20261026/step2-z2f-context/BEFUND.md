# Befund WP-Z2f: B2-Zeiger auf schweren Aufgaben mit größerem Kontext-Budget (2026-10-26)

Vorregistrierung `PREREG.md` (Commit `e0e9bcf`, vor Inferenz gepusht). Linux-Cloud, 4 CPUs, kein Redmi. 9 Läufe × 70 Zeilen (CQ/CQP/DQP × Seeds 23–25),
alle RECORDED, ohne Abbruch. `b2_context_chars` = 1536 in allen Armen.

## Gültigkeit: erfüllt
Die Kickoff-Notiz mit den Regeln stand jetzt in **100 %** der B2-Angebote auf schweren Episoden im Kontext (alle drei Arme). Der Test ist aussagefähig.

## Ergebnis laut Vorregistrierung: `Z2F_UNSAFE_OR_INVALID`
| | CQ (aus) | CQP (Zeiger) | DQP (ein Körper, Zeiger) |
|---|---|---|---|
| B2-Regelquote schwere Episoden | .094 | .260 (Seeds .19/.19/.41) | .031 |
| davon LONG / REVISED | .17 / .02 | .46 / .06 | — |
| Differenz CQP − CQ [CI] | — | +.167 [−.021, +.396] | — |
| **falsch festgelegte Entscheidungen** | **7** | **18** | **2** |
| `both_exact` / b1_only Werkzeug-Nutzen | .553 / .572 | .619 / .586 | .525 / .589 |
| B2-Prompt-Tokens (Mittel) | ~608 | ~833 | ~862 |
Der Zeiger hebt die Regelquote, aber nicht sicher über die Kontrolle (CI schließt 0 ein) und weit unter .60. Bei LONG wählte B2 oft nur die lange
Kopfzeile (Erweiterung trägt dann nur das Budget). STEP2-Kriterien: alle ✗ außer Struktur.

## Der eigentliche Befund: veraltete Regeln führen zu falschen Entscheidungen
**Alle 27 falsch festgelegten Entscheidungen** liegen in REVISED-Episoden und sind genau die Aktion, die nach der **alten** Regel richtig wäre.
Mechanismus (nachgeprüft an den Zeilen): B2 zitiert die alte Kickoff-Notiz exakt, aber nicht die spätere Änderung; C3 liest den alten Wert; das
Eignungs-Werkzeug prüft nur, ob der Wert in einem exakten Zitat steht und ob der *aktuelle* Text widerspricht — beides ist erfüllt, also legt es sich fest.
Mit dem alten Budget (768) trat das nicht auf, weil die alte Notiz gar nicht ankam. **Mehr Gedächtnis ohne Aktualitätsprüfung ist unsicher.**
Das betrifft auch die Kontrolle ohne Zeiger (7) — es ist kein Zeiger-Fehler, der Zeiger macht nur mehr alte Regeln sichtbar.

## Explorativ (nicht vorregistriert, auf schon gesehenen Daten): Aktualitäts-Wächter
Regel: ein Regelwert zählt nur, wenn **keine jüngere** im Sitzungsgedächtnis behaltene exakte Quelle (240-Zeichen-Auszüge der früheren Züge) einen
anderen Wert für dieselbe Regel nennt; sonst UNKNOWN (`scripts/step2_recency_guard_explore.py`, deterministisch auf den aufgezeichneten Extraktionen).
| Daten | falsch vorher → nachher | exakte Aktion vorher → nachher |
|---|---|---|
| Z2f (CQ/CQP/DQP) | 7/18/2 → **0/0/0** | 32/37/25 → 32/37/25 |
| Z2d (CQ/CQA/CQP) | 0 → 0 | 42/65/94 → unverändert |
| Z2b (C/CQ/D/DQ) | 0 → 0 | unverändert |
Kein Verlust an richtigen Entscheidungen, alle veralteten Festlegungen weg. Weil die Regel nach Sicht dieser Fehler entworfen wurde, ist das nur ein Kandidat.

## Empfehlung
- Schalter `b2_quote_select` bleibt **aus**; `b2_context_chars` live bleibt 768, solange es keine Aktualitätsprüfung gibt.
- Nächstes Paket **WP-Z2g**: Aktualitäts-Wächter ins Eignungs-Werkzeug (Live-Pfad, Schalter, Standard aus), vorregistriert auf **frischen** Episoden mit
  geänderten Regeln und neuen Seeds bestätigen; Kriterium 0 falsch bei gleicher Trefferzahl. Danach erneut Zeiger + größeres Budget.
- Für LONG: B2 braucht mehr als zwei Zeiger-Plätze oder eine Erweiterung bis zur ganzen Notiz; eigenes Paket.

Daten: `code/bench-results/step2-z2f-context-20261026/` (z2f_result.json, Zusammenfassungen, Werkzeug-Replays, Log, recency_guard_explore.txt, SHA256SUMS);
volle Berichte im Projektordner `v13/bench-results/step2-z2f-context-20261026/`.
