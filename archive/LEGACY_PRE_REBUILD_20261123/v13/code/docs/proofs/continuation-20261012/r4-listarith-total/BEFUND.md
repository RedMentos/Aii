# R4 Teil 7: `list_arith` verwirft gelesene Summen-Zeilen (2026-10-13, Thread K)

**Verdikt: FIX_SUPPORTED.** Vorregistrierung `preregistration.json` (sha256 `4e7beff8…`, Commit `8a9dbe9`, vor Seed 23), Bericht `report.json` (sha256 `51878d74…`), Rohdaten `live-fresh23.json` (sha256 `02bf5d1e…`).

**Fehler aus Teil 6.** C3 las die Zeile „Total: 173 euros" als weiteren Posten (Seed 7 und 19 je 1 von 30 Werten falsch); der Zahlen-Wächter ließ es durch, weil die Zahl im Text steht.

**Änderung.** `agi/listarith.py`: Posten mit Namen total/sum/summe/gesamt…/summary (Regex `AGGREGATE`) sind die zu prüfende Behauptung, nie Eingabe, und werden vor dem Rezept verworfen (für Summe und Differenz). Sonst unverändert.

**Nachrechnung (ohne Modell, auf schon gelesenen Werten).** Seed 7 und 19: je 58 → 60 von 60 Werten richtig.

**Frisch, Seed 23 (Teil-6-Messung unverändert).**

| Satz | n | C3 allein | mit Werkzeug | gewonnen/verloren | p |
|---|---|---|---|---|---|
| **orig** | 60 | 42 | **55** | 14 / 1 | **0,001** |
| match | 30 | 6 | 24 | 18 / 0 | < 0,001 |
| nomatch | 15 | 2 | 2 | 0 / 0 | 1 |

Werkzeug-Werte 30/30 richtig (Regel: alle richtig), summary 9 → 14, compare 5 → 13, long/notes unverändert. Die Regel griff hier in 1 von 30 Vorschlägen.

**Grenzen.** Wie Teil 6: generierte englische Aufgaben, Regex-Prüfung, Cloud-CPU, Alters-Urteil für die Messung ersetzt, kein Redmi. Die Namensliste ist englisch/deutsch und fest; andere Namen für Summenzeilen fallen weiter durch.

Reproduktion: `scripts/r4_listarith_total.py prereg|evaluate`, Erfassung `scripts/r4_listarith_live.py capture <home> 23 <out>`.
