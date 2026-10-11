# V13 / Inquisition-JEPA – Übergabe für eine andere KI (Stand 2026-10-11)

Projekt: brain-inspirierte, kontinuierlich lernende KI-Runtime für ein Redmi-Handy (Android/Termux, 6 GB RAM). Nutzer schreibt Deutsch, arbeitet nur am Handy.
Zuerst lesen: `ROADMAP.md` (Pakete + Status), `NUTZER_ENTSCHEIDUNGEN.md`, `SICHTUNG.md`, `ABDECKUNG.md`, `code/README.md`, `code/docs/CONTINUE.md`.
Code: `code/v13/` (Runtime), `code/tests/`, `code/scripts/`, `code/specs/`. Tests: `PYTHONPATH=.:tests python -m unittest` in `code/` (zuletzt ~940 grün; `test_bodies.TightBudget` sporadisch flaky).
Nutzerentscheidungen: viele verschiedene Modelle, Englisch zuerst, konstantes Lernen als Endziel, Gehirn-Simulation, Age-Hülle bleibt Start bei 0.
Offene Punkte: L1-Gate FAIL (B3 LATENT unavailable); STEP2 two-body FAIL; viele SHADOW-Flags brauchen Redmi-Messung; WP-T17 Dream-Lauf 2 offen.
Nicht im Repo (zu groß): `code/docs/proofs/` (199 MB) und `archiv/chat/` (5 MB), bench-results/*/acceptance.
