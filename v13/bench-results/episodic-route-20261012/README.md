# §99-Ablation: „Zweites Mal besser“ für Routen (WP-U10 §9.1) — **SUPPORTED_SYNTHETIC** (Thread L, 2026-10-12)

Skript `code/scripts/ablation_episodic_route.py`, Vorregistrierung `preregistration.json` (Commit `0cc3afc`, vor dem Lauf gepusht), Rohdaten `report.json`.
Echtes `episodic_route.for_turn` (aktiv) auf frischem SQLite-Store; Korrekturen über das echte `Memory.feedback(…, 'route', …)`. 12 Projekte × 4 Aufgaben × 3 deutsche Umformulierungen, 300 Anfragen je Saat, 5 Saaten. Je Projekt/Aufgabe weicht die wahre Route mit p .40 vom Aufgaben-Standard ab; falsche Routen korrigiert der Mensch mit p .50.
Primärmaß: Routen-Trefferquote in der zweiten Hälfte.

| Arm | Trefferquote | episodic gewinnt |
|---|---|---|
| episodic (Entitäts-Schutz, Relevanz ≥ .6) | **.963** ± .014 | — |
| nur Standard-Route (Gerüst) | .600 ± .064 | 5/5 |
| ohne Entitäts-Schutz (reine Wort-Überlappung) | .889 ± .051 | 5/5 |
| neueste Korrektur egal wofür | .239 ± .030 | 5/5 |

- Eine einzige Korrektur reicht, damit sehr ähnliche Folgeanfragen richtig geroutet werden → SUPPORTED_SYNTHETIC.
- Der Entitäts-Schutz zählt: Ohne ihn springt die Korrektur für „Projekt Aurora“ auf „Projekt Borealis“ über (−7 Punkte).
- Grenze: synthetische Vorlagen-Anfragen, eine Sitzung, BOOT-Schwelle .6, ohne Konsolidierungspfad. Modus bleibt shadow, bis echte Korrekturen gemessen sind.
