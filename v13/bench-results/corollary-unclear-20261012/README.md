# Corollary-Kandidat 3: weit danebenliegende Werte → UNCLEAR — **PASS**, übernommen (Thread L, 2026-10-12)

Skript `code/scripts/corollary_unclear_candidate.py`, Vorregistrierung `preregistration.json` (Commit `7cc677d`, vor dem Lauf gepusht), Rohdaten `report.json`. Gleiche Ströme und Saaten wie Kandidat 1/2, K = 20 fest aus Kandidat 2.
Änderung: Bei MIXED wird die Abweichung gegen die **nächstliegende** offene Vorhersage gerechnet. Liegt auch die über 20 × Toleranz, heißt das Ergebnis UNCLEAR (Enthaltung) statt EXTERNAL.
„Schädlich“ zählt: fremdes Ereignis als SELF/MIXED, eigener Fehlschlag als SELF/EXTERNAL, eigener Erfolg als MIXED/EXTERNAL.

| Strom | heute schädlich | Kandidat 2 (EXTERNAL) | Kandidat 3 (UNCLEAR) | Enthaltung K3: eigene Fehlschläge / fremd |
|---|---|---|---|---|
| Standard (Fehlschläge 3–6 × Toleranz) | .389 | .003 | **.003** | 0 / .61 |
| Stress (Fehlschläge bis 40 ×) | .389 | .031 | **.003** | .42 / .61 |

- Kriterien: weniger schädlich als heute 5/5 auf beiden Strömen, nie schlechter als Kandidat 2, Standard-Enthaltung bei eigenen Fehlschlägen 0 ≤ .05 → **PASS**.
- Übernommen in `v13/selfmodel.attribute` (`FAR_K = 20`) mit Test in `tests/test_selfmodel.py`; der Live-Code liefert auf den Test-Strömen exakt dieselben Zahlen wie der Kandidat.
- Preis: Fremde Ereignisse auf einem Kanal mit offener eigener Aktion werden UNCLEAR statt EXTERNAL (61 %). Heute wurden sie fälschlich als eigener Fehler gelernt, jetzt wird nichts gelernt. Im Stress-Strom enthalten sich 42 % der sehr weit danebenliegenden eigenen Fehlschläge.
- Die Berichte `corollary-*-20261012/report.json` der früheren Läufe stammen vom alten `attribute`.
- Grenze: synthetische digitale Beobachtungen, BOOT-Toleranzen/Fenster.
