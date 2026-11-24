# R4 Teil 10: Fragen-Regel R3 für `list_arith` — übernommen (2026-10-13, Thread K)

**Verdikt: R3_ADOPTED.** Vorregistrierung `preregistration.json` (sha256 `c701ad29…`, Commit `6c2f52c`, vor Familie E), Bericht `report.json` (`843d8a54…`). Kein Modell beteiligt.

**R3** = Regel nur auf den Frageteil (Teil 9) + Formulierungen nur aus Trainingsfamilie A (Teil 8) + Ausschluss „total/overall number/count of“ (Zählen, keine Summe; einziger Fehlalarm-Grund in Teil 9).

| Neue Familie E (228 Texte) | Makro-F1 | Fehlalarm | Summe↔Differenz | übersehen |
|---|---|---|---|---|
| R0 (bisherige Regel) | 0,50 | 18 % | 4 % | 58 % |
| **R3** | **0,73** | **0 %** | **0 %** | 42 % |

Alle 360 R4-Aufgaben (Seeds 7, 11, 13, 17, 19, 23) behalten ihre Rechenart, also gelten die Live-Ergebnisse aus Teil 6/7 für diese Aufgaben weiter. Ehrlich: Der Zähl-Ausschluss griff auf E nicht (R2 = R3 auf E); E zeigt vor allem, dass R2/R3 ohne Fehlalarm verallgemeinern.

**Übernommen.** `agi/listarith.operation` ist jetzt R3 (`question_part`, `EXTRA`, `COUNT`). Die alte Regel R0 ist im Skript `r4_rule_question_only.py` eingefroren (Auswertungen von Teil 8–10 laufen wegen Hash-Bindung nur im jeweiligen Vorregistrierungs-Commit).

**Übersehen bleiben** z. B. „add these numbers together“, „combine all the values“, „by how much is the maximum above the minimum“, „gap from … to …“. Deutsch weiterhin nicht erkannt.

**Grenzen.** Alle Familien vom selben Autor, generierte englische Texte; die umformulierten Live-Fragen, die R3 neu erkennt, sind nicht live nachgemessen.

Reproduktion: `scripts/r4_rule_r3.py prereg|evaluate` (im Commit `6c2f52c`), Tests `tests/test_r4_rule_r3.py`, `tests/test_listarith.py`.
