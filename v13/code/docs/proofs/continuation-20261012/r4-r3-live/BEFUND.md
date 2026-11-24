# R4 Teil 11: Von R3 neu erkannte Formulierungen im Live-Werkzeug-Pfad (2026-10-13, Thread K)

**Verdikt: R3_LIVE_SUPPORTED.** Vorregistrierung `preregistration.json` (sha256 `247b495d…`, Commit `c6d9637`, vor Seed 29), Bericht `report.json` (`2b1c151a…`), Rohdaten `live-fresh29.json` (`9b97f88c…`).

**Aufbau.** Wie Teil 6 (echter Pfad ToolStep → C5 → TOOL_RESULT → Broker, C3 LFM2.5-350M, Alters-Urteil nur für die Messung ersetzt). Frischer Seed 29, 30 Aufgaben mit neuen Formulierungen:
- compare: „…by how many millimetres did it exceed the driest one?“ (die alte Regel erkannte das nicht, R3 über „exceed“)
- summary: „…Add the items up and give the right figure.“ (R3 erkennt „add … up“ in der Frage; die alte Regel griff hier nur über „Total:“ in den Daten)

| | n | C3 allein | mit Werkzeug | gewonnen/verloren | p |
|---|---|---|---|---|---|
| gesamt | 30 | 13 | **25** | 13 / 1 | **0,0018** |
| summary | 15 | 7 | 15 | | |
| compare | 15 | 6 | 10 | | |

Werkzeug in 30/30 ausgeführt, Werte 30/30 richtig, mit Broker-Korrekturzeile 30/30.

**Lesart.** Die von R3 neu erkannten Formulierungen bringen live denselben Nutzen wie die alten. Bei compare bleiben 5 Fehler, obwohl der Wert stimmt (Stadt oder Zahl in der Antwort falsch); die Korrekturzeile fängt sie auf.

**Grenzen.** Zwei Formulierungen, generierte englische Aufgaben, Regex-Prüfung, Cloud-CPU, Alters-Recht für die Messung ersetzt. Kein Redmi.

Reproduktion: `scripts/r4_r3_live.py capture|prereg|evaluate` (im Commit `c6d9637`).
