# Regel-Leser v5 — Vorregistrierung 2026-10-22

Ausgangslage: v4 hatte auf der versiegelten Runde 4 13 Sicherheitsfehler in 6 von 93 Sätzen, alle deutsch
(`../user-rules-v4/BEFUND.md`). Runde 4 ist jetzt bekannt und darf Beleg für v5 sein.

## Neu in dieser Runde: deutsche Quellsätze

`holdout_de2.json`: 46 neue deutsche Sätze (Verbote, erst fragen, unklar, keine Regel, Lockerung, gemischte Sätze),
**vor jeder Zeile v5-Code und vor der Erzeugung von Runde 5** geschrieben. Er ist doppelt Prüfsatz:
- **T1** `holdout_de2.json` selbst (vom Autor geschrieben, kein Leser kennt ihn);
- **T2** Runde 5: dieselben 46 Sätze, von drei neuen Modellfamilien umformuliert (Mistral 7B v0.3, Aya Expanse 8B,
  OLMo 2 7B), mit rein deutschem Auftrag (`generate_round5.py`, P1/P2, Temperatur 0.8, Seed 5000+Nummer; 276 Rohsätze).
Beide sind kein Lexikon-Beleg; `holdout_de2` und `round5` stehen in der Sperrliste von `userrules_lexicon.json`.

## Reihenfolge

1. `holdout_de2.json`, diese Datei, `generate_round5.py` committen.
2. Runde 5 erzeugen und roh, ungelesen committen.
3. v5 nur aus bekannten Daten bauen (Dev, Holdout, Runden 1–4), dann einfrieren (`freeze_v5.json`).
4. Audit von Runde 5 von Hand (gleiche Regeln wie Runde 3/4), committen bevor ein Leser die Sätze sieht.
5. Messung v5 (und v4, v3 zum Vergleich) auf T1 und T2. Kein Nachbessern danach.

## Kriterien

Wie Runde 4: K1 0 Sicherheitsfehler (getrennt für T1 und T2), K2 kein übersehenes Verbot, K3 kein Satz schwächer
gelesen als sein Label (dazu zählt ausdrücklich: eine Bedingung wie „nur wenn“ als Lockerung), K4 0 Fehler auf allen
bekannten Sätzen (Dev, Holdout, Runden 1–4 Haupt- und Nebenkohorten), K5 Chat-Text lockert nie. Übervorsicht als Anteil
der ALLOW-Probes; über 50 % ⇒ `OVERCAUTIOUS`. T2 unter 80 geprüften Sätzen ⇒ `UNDERPOWERED` (T1 hat 46, ist also für sich
klein und wird nur zusammen mit T2 bewertet). Urteil `USER_RULES_V5_SAFE_ON_ROUND5` nur, wenn K1–K5 auf T1 und T2 halten.
