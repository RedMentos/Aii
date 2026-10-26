# Handy-Probe für die Z2l-Kette (ein Körper, zwei Zustände)

Skript `code/scripts/handy_z2_chain.py`: Z2l-Arm DS auf drei Episoden (Baten, Enif, Kitalpha), Seed 1, alle 7 STEP2-Varianten (21 Zeilen), misst Wandzeit,
Zeilenzeiten, Spitzen-RSS (Prozess + Kinder, /proc) und Ketten-Ergebnis. Nichts wird in der Nutzer-Laufzeit eingeschaltet; eigenes Home unter `--work`.

Cloud-Referenz (Linux, 4 CPUs, 2026-10-26): 21 Zeilen in 258 s, längste Zeile 9,4 s, Spitzen-RSS **1988 MB**, `both_exact` 3/3 exakt, 0 falsch,
Kickoff 12/12 im Kontext, B2-Prompt ~550–1020 Tokens.

Aufruf in Termux: `python scripts/handy_z2_chain.py --installed-home <Modell-Home> --work <leerer Ordner>`; Ergebnis `handy_z2_chain_result.json`.
