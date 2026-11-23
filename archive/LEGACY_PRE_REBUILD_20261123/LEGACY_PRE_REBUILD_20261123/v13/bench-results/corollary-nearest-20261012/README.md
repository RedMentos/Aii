# Kandidat 2: Corollary-Zuordnung mit nächstliegender Vorhersage + Toleranz-Obergrenze (Thread L, 2026-10-12) — **FAIL (nach Vorregistrierung)**

Skript `code/scripts/corollary_nearest_candidate.py`, Vorregistrierung `preregistration.json` (Commit `e7be2d3`, vor dem Lauf gepusht), gleiche Ströme, Saaten und Kriterien wie Kandidat 1 (`../corollary-ceiling-20261012/`). `selfmodel.py` nicht geändert.
Änderung: Bei MIXED wird die Abweichung gegen die **nächstliegende** offene Vorhersage auf dem Kanal gerechnet; nur wenn auch die > K × Toleranz liegt, wird EXTERNAL gemeldet. K = 20 (Kalibrierung: 4 → .783, 6–20 → .983).

| Test-Saaten 13–17 | Balanced Acc. | fremd → MIXED | eigener Fehlschlag verpasst |
|---|---|---|---|
| Standard, unverändert | .767 | .606 | .049 |
| Standard, Kandidat 2 | **.969** | **0** | **.049** (unverändert) |
| Stress (Fehlschläge bis 40×), unverändert | .766 | .606 | .053 |
| Stress, Kandidat 2 | .826 | **0** | .478 |
| nur nächstliegende Abweichung, ohne Obergrenze | = unverändert | | |

Kriterien: (1) 5/5 ✓, (2) 5/5 auf beiden Strömen ✓, Stress-Balanced-Accuracy nie schlechter ✓, aber Anstieg verpasster Fehlschläge im Stress-Strom .42 > .10 ✗ → **FAIL**, nicht integrieren.

Befund:
- Mit nächstliegender Abweichung verschwindet der Verlust aus Kandidat 1 im Standard-Strom ganz: kein einziger eigener Fehlschlag geht mehr verloren, fremde Ereignisse werden nie mehr als eigener Fehlschlag gelernt.
- Die verbleibende Grenze ist grundsätzlich: Ein eigener Fehlschlag, der 20–40× danebenliegt, sieht nach dem Wert allein genauso aus wie ein fremdes Ereignis. Ohne weiteres Signal (z. B. Prozess-/Dateihandle-Herkunft) ist das nicht trennbar.
- Entscheidungsfrage für später (nicht jetzt nötig): Weit danebenliegende Werte als UNCLEAR statt EXTERNAL melden. Dann entsteht weder ein falscher eigener Fehler noch ein falsches „fremd“; der Preis ist, dass solche Fehlschläge nicht gelernt werden. Das wäre ein neuer, getrennt vorregistrierter Kandidat mit einem Kriterium, das UNCLEAR als Enthaltung statt als Fehler zählt.
