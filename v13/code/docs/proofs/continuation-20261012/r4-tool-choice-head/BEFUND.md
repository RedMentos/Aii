# R4 Teil 8: Gelernte Werkzeugwahl für `list_arith` auf dem C2-Needle-Embedding (2026-10-13, Thread K)

**Verdikt: NOT_SUPPORTED** (eine von drei vorab festgelegten Bedingungen verfehlt). Vorregistrierung `preregistration.json` (sha256 `1f25ee13…`, Commit `6f0dd64`, vor Auswertung der Testfamilie), Bericht `report.json` (`7426a1a8…`), Vektoren `vectors.npz` (`92e978e5…`, Needle needle3 Revision `b274efcb`).

**Frage.** Erkennt ein kleiner Kopf (multinomiale logistische Regression) auf dem eingefrorenen C2-Needle-Embedding die Rechenart keine/Summe/Differenz bei umformulierten Fragen besser als die feste BOOT-Regel aus Teil 6?

**Aufbau.** Generierte Listen-Kontexte (Ausgaben, Niederschlag, Punkte, Lager; die Hälfte der Ausgaben mit „Total:“-Zeile). Drei getrennte Fragen-Familien, vor dem Einbetten festgelegt (Commit `5268354`): Training A (20 englische Vorlagen, 240 Texte), Test B (19 neue englische Vorlagen, 228), Deutsch C (12 Vorlagen, 120, nur berichtet). Sicht und L2 nur auf A gewählt (Kreuzvalidierung ohne Vorlage): ganzer Text, L2 0,1.

**Test B (englisch, neue Formulierungen).**

| | Makro-F1 | Fehlalarm bei „keine“ | Summe↔Differenz verwechselt | Rechenfrage übersehen |
|---|---|---|---|---|
| Regel | 0,38 | 11 % | 6 % | 70 % |
| **Kopf** | **0,78** | **21 %** (Grenze 5 %) | 1,4 % | 21 % |
| Regel, sonst Kopf | 0,79 | 32 % | 8 % | 7 % |

Bedingungen: F1 ≥ Regel + 0,15 ✓, Verwechslung ≤ 2 % ✓, Fehlalarm ≤ 5 % ✗.

**Deutsch C.** Kopf F1 0,20, Regel 0,17: fast alle Rechenfragen übersehen. Needle trägt deutsche Formulierungen nicht.

**Lesart.**
1. Der Kopf verallgemeinert auf neue englische Formulierungen deutlich besser als die Regel (die Regel übersieht 70 %).
2. Zum Einschalten reicht es nicht: jede fünfte Nicht-Rechenfrage würde einen Werkzeugaufruf auslösen (häufig „Sort the entries from high to low“ → Differenz). Ein Fehlalarm kostet einen C3-Aufruf und legt einen passenden, aber nicht gefragten Wert in den Kontext.
3. Die Regel ist auch auf englischen Testfragen schwach: Fehlalarme und Verwechslungen kommen fast nur von „Total:“ in den Daten (Teil 6).
4. Häufigste Fehler des Kopfes: „grand total“, „sum these up“, „tally up“ als keine erkannt; Kontext dominiert das Embedding des ganzen Texts.

**Folge (Vorschlag, nicht umgesetzt).** (a) Regel nur auf die Frage anwenden, nicht auf die Daten (behebt „Total:“-Fehlalarme ohne Modell). (b) Kopf mit Bestätigung kombinieren, z. B. nur vorschlagen, wenn Kopf und eine C3-Ja/Nein-Prüfung übereinstimmen, oder Kopf als SHADOW-Lerner mit echten Nutzerfragen trainieren. (c) Deutsch braucht ein mehrsprachiges Embedding. Keine Runtime-Änderung.

**Grenzen.** Generierte Texte, ein Encoder, Cloud-CPU, Vorlagen selbst geschrieben (Familien getrennt, aber gleicher Autor). Kein Redmi.

Reproduktion: `scripts/r4_tool_choice_head.py embed|prereg|evaluate`, Tests `tests/test_r4_tool_choice_head.py` (3).
