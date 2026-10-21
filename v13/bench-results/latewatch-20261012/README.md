# §99-Ablation: spätes Body-Offer unterbricht die Ausgabe (WP-U3 F2, §5.2) — **SUPPORTED_SYNTHETIC** mit drei Schwächen (Thread L, 2026-10-12)

Skript `code/scripts/ablation_latewatch.py`, Vorregistrierung `preregistration.json` (Commit `0d93f18`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echtes `latewatch.Watcher.check` (Modus active, unveränderte `disagreement`-Regel und „später nochmal schauen“-Schleife), nur die Laufzeit drumherum ist ein Stub. 400 Rechen-Runden je Saat, 5 Saaten: Antwort falsch mit p .30; Body richtig .80 / andere falsche Zahl .10 / unklar mit `needs_reentry` .10; Offer kommt an zufälliger Zeichenposition (teils nach dem Ende).
Wertung je Runde: +1 Schnitt einer falschen Antwort (Body nicht selbst falsch), −1 Schnitt einer richtigen Antwort, sonst 0.

| Strom | Regel | nie schneiden | immer schneiden | zufällig (gleiche Zahl) | Regel gewinnt (nie / immer / zufällig) |
|---|---|---|---|---|---|
| standard (Zahlen < 1000) | **+.064** (64 nützlich, 39 unnötig) | 0 | −.295 | −.094 | 5 / 5 / 5 |
| format (halb ≥ 1000 mit Tausender-Komma) | −.081 (61 / 93) | **0** | −.329 | −.165 | 0 / 5 / 5 |

- Auf dem Standardstrom hilft die Regel klar gegenüber allen Kontrollen → SUPPORTED_SYNTHETIC. Shadow bleibt trotzdem Standard (Grenzen unten).
- Schwäche 1, `BODY_REENTRY`: ≈ 19 von 39 unnötigen Schnitten je Saat. Ein unklarer Body mit Zitat schneidet auch richtige Antworten, weil die Regel die Antwort dabei gar nicht prüft. In diesem Strom ist das Flag unabhängig davon, ob die Antwort stimmt; die Kosten sind also eine Obergrenze (echte Bodies flaggen vermutlich öfter bei falschen Antworten).
- Schwäche 2, abgeschnittene Zahl: ≈ 4 je Saat. Kommt das Offer mitten in einer Zahl („The result is 5026…“ statt 502670), gilt die halbe Zahl als anderes Ergebnis → RESULT_CONFLICT.
- Schwäche 3, Tausender-Komma: `nums` macht aus „1,234“ „1.234“. Schreibt der Body 1234, zählen Quellzahlen als „neu“, und richtige Antworten werden geschnitten (≈ 57 je Saat). Mit solchen Zahlen ist die Regel schlechter als nie schneiden.
- Nächster Kandidat (getrennt vorregistrieren): Ziffernfolge am Ende des Teiltexts ignorieren, Tausender-Komma vor dem Vergleich entfernen; `BODY_REENTRY` erst nach eigenem Ergebnis der Antwort.
- Grenze: synthetische Rechenrunden, nur zahlbasierter Konflikt, BOOT-Schwellen 24/48 Zeichen; keine Modellausgabe.
