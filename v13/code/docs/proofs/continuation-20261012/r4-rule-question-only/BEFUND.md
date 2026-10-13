# R4 Teil 9: BOOT-Regel für `list_arith` nur auf die Frage (2026-10-13, Thread K)

**Verdikt: NOT_SUPPORTED, nichts übernommen** (Fehlalarm-Grenze verfehlt, alles an einer Vorlage). Vorregistrierung `preregistration.json` (sha256 `348db33f…`, Commit `f01c771`, vor Familie D), Bericht `report.json` (`5da6aa41…`). Kein Modell beteiligt.

**Varianten.** R0 = heutige Regel auf den ganzen Text. R1 = gleiche Muster nur auf den Frageteil (letzte Sätze ohne Ziffern). R2 = R1 + Formulierungen nur aus Trainingsfamilie A von Teil 8 (add … up, altogether, combined, difference between, exceed, gap between, apart). Entschieden auf neuer Familie D (19 Vorlagen, 228 Texte), vorher festgelegt.

| Familie D | Makro-F1 | Fehlalarm | Summe↔Differenz | übersehen |
|---|---|---|---|---|
| R0 | 0,48 | 24 % | 4 % | 58 % |
| R1 | 0,49 | 14 % | 0 % | 67 % |
| R2 | **0,79** | 14 % (Grenze 5 %) | 0 % | 25 % |

Alle R4-Aufgaben (Seeds 7–23, 360) behalten ihre Rechenart unter R1 und R2.

**Lesart.**
1. Nur die Frage prüfen wirkt wie gedacht: Alle Fehlalarme durch Daten („Total:“-Zeile, Zahlen) verschwinden, ebenso die Verwechslungen.
2. Die verbleibenden 14 % Fehlalarme stammen **alle** von einer einzigen Vorlage, „What is the total number of entries?“ (Zählen, nicht Summe). Das Wort „total“ ist mehrdeutig.
3. R2 holt viele neue Formulierungen; übersehen bleiben „make together“, „range from lowest to highest“, „how much bigger … than“.
4. Nach der vorab festgelegten Regel wird nichts übernommen. Eine Ausnahme für „total number of“ jetzt einzubauen, wäre an Familie D angepasst und braucht eine neue Familie zum Prüfen.

**Folge (Vorschlag).** R2 + Ausschluss „total number of / how many“ als neuer Kandidat, geprüft auf einer neuen Familie E; oder Fragen-Regel + Needle-Kopf als zweite Meinung (Teil 8). Runtime unverändert.

**Grenzen.** Alle Familien vom selben Autor, generierte englische Texte.

Reproduktion: `scripts/r4_rule_question_only.py prereg|evaluate`, Tests `tests/test_r4_rule_question_only.py` (3).
