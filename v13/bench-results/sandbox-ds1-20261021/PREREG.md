# WP-DS1 Vorregistrierung (vor dem Messlauf, 2026-10-21)

Anlass: DeepSeek-Kritik (Active Inference fehlt, Embodiment fehlt). Lab-Sandkasten `code/v13/sandbox.py`, Bench `code/scripts/sandbox_ds1_bench.py`, Tests `code/tests/test_sandbox.py`. Kein Laufzeit-Code, kein Modell, Age-0-Kern unberührt.

**Ehrlichkeitshinweis:** Vor dieser Registrierung liefen Pilot-Seeds 1..5 (zum Prüfen, ob die Welt überhaupt lernbar ist). Dabei war `LP` vor `EIG`. Die Messung nutzt nur die frischen Seeds **100..119**; Welt, Tabellen, Prior und Schwellen werden danach nicht mehr geändert.

Messgröße: mittlere KL(Wahrheit || Vorhersage) über alle (Wort, Handlung)-Paare der vorhandenen Objektarten.

| Hypothese | Kriterium (20 Seeds, gepaart) |
|---|---|
| H1 Neugier schlägt Zufall | `novelty`, `lp`, `eig`, `efe` haben jeweils in ≥ 15/20 Seeds kleinere KL bei Schritt 600 als `random` |
| H2 Rausch-Fernseher-Falle | `surprise` verbringt ≥ 50 % der Handlungen am Fernseher, `eig` und `lp` je ≤ 25 % |
| H3 Lernfortschritt (V13 AG5) gegen Informationsgewinn (Active Inference) | Sieger = ≥ 14/20 Seeds kleinere KL bei Schritt 600, sonst TIE. Vorhersage aus Pilot: LP_BETTER |
| H4 Hunger-Ziel (pragmatischer Wert) | `efe` hat in ≥ 15/20 Seeds weniger mittleren Hunger als `eig` und KL@1500 ≤ 1,25 × `eig` |
| H5 neues Objekt `pilz` ab Schritt 600 | nur berichtet: wie viele Seeds lernen es (KL ≤ 0,1) und Median-Schritte |
| Grounding | nur berichtet: Anteil richtiger Vorhersage-Modi je Policy, Erwartung ≥ 0,95 außer `surprise` |

Ein FAIL wird so stehen gelassen; Folgeideen nur als neue, eigene Vorregistrierung.
