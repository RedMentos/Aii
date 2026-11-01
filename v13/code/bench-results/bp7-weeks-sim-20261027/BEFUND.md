# WP-BP7 Wochen-Simulation, Befund 2026-10-27

Urteil: `BP7_WEEKS_SIM_PASS` (alle 7 vorab registrierten Kriterien, Seeds 301–303, Registrierung in `docs/BP7_SLEEP_CONSOLIDATION.md`, vor dem Lauf committet). Rohdaten: `result.json`. Befehl: `PYTHONPATH=. python3 scripts/bp7_weeks_sim.py --out bench-results/bp7-weeks-sim-20261027 --seeds 301,302,303`.

Zahlen (Mittel über 3 Seeds): Treffer@1 auf ähnlichen Paaren Woche 5–6 mit Rekonsolidierung ≈ 1,00 gegen ≈ 0,48 ohne (Gewinn +0,52, Schwelle +0,05). Verlauf mit Rekonsolidierung 0,79 → 0,96 → 1,0; ohne bleibt es bei 0,35–0,66. Eindeutige Einträge 1,0 in beiden Armen. Veraltete Werte nach Korrektur: 0. Speicherinhalt (Schlüssel, Werte, aktiv) nach 6 Wochen in beiden Armen identisch. Batch ohne Checkliste: 826 private und 504 faktenverratende Traum-Einträge gestagt; mit Checkliste 0 und 0. Policy-Traumeinträge: 100 % blieben. Gewichte 0,57–1,43. Prüfliste: 12 Einträge je Seed (die jeweils nicht gemeinten Geschwister).

Erster Probelauf mit Seed 301 zeigte Kriterium 4 als FAIL, weil die Prüfsumme zufällige Eintrags-IDs enthielt (Messfehler im Skript). Korrigiert auf reinen Inhalts-Hash, keine Schwelle verändert; danach der registrierte 3-Seeds-Lauf.

## Was das aussagt und was nicht

- Aussagt: Die Mechanik arbeitet wie entworfen. Menschliche Abruf-Urteile ordnen konkurrierende ähnliche Einträge, ohne einen Wert zu schreiben, und die Checkliste hält private und faktenverratende Einträge aus dem Gewichts-Batch. Ohne Checkliste wären sie drin (Gegenprobe).
- Aussagt nicht: Der Pseudo-Mensch urteilt bei 30 % der Fragen immer richtig; das ist nach oben geschönt. Ähnliche Paare sind absichtlich ein Fall, in dem ein Urteil helfen muss. Kein Modell, kein Gewichts-Training, keine Handy-Messung, nichts über Traum-Nutzen im Modell. Die Rekonsolidierung bleibt im Standard `shadow`.
