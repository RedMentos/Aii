# Vorregistrierung WP-Z2-Q1 (Skript z2e): allgemeine Körper-Frage statt STEP2-spezifischer (2026-10-22)

Vor jeder Inferenz geschrieben und gepusht. Linux-Cloud, gleiche Modelle/Runner wie Z2b/Z2c, kein Redmi.

## Frage
Z2b/Z2c: Eine gezielte Frage an die Körper hilft (+.22 bis +.23 both_exact), nennt aber Option A/B, Budget, Frist und lokal.
Für den normalen Chat taugt sie deshalb nicht. Behält eine **allgemeine** Frage, die keine Aufgabe nennt, den Gewinn?

- B1: „Which exact details (numbers, names, values) does the current message need? Quote the exact source sentences that state them, or say they are not in the source.“
- B2: „Which earlier statements (rules, constraints, decisions) does the current message depend on? Quote the exact earlier source sentences that state them, or say they are not in the source.“

## Aufbau
`scripts/step2_z2e_general.py`, Z2-Episoden (10) eingefroren, Arm-C-Einstellungen (zwei Körper, Zitat-Kontext 200,
B1-Fenster 600), frische Seeds **23/24/25**, Arme C (keine Frage), CL (spezifische Z2b-Fragen über den Live-Schalter),
CG (allgemeine Fragen über den Live-Schalter). Werkzeug-Replay und Bewertung unverändert (`step2_z2b_seeds.run_one`).
Seit `85468a9` nutzt der Runner `cfg['seed']` selbst (Kettenglied `runner_seed`).

## Entscheidungsregel (fest)
GENERAL_QUESTION_SUPPORTED genau dann, wenn
1. CG − C (both_exact, Cluster-Bootstrap über Episoden, 10000, Saat 20261021): Mittel > 0 und 95-%-KI-Untergrenze > 0,
2. CG − CL Mittel ≥ −0,05,
3. 0 falsch festgelegte Werkzeug-Zeilen in CG.
Nur berichtet: b1_only/b2_only, Zitat-Zählungen, KI von CG − CL.

## Folge
Bei SUPPORTED schlage ich vor, die allgemeine Frage als Standard einzuschalten (nach Nutzerfreigabe). Sonst bleibt der
Schalter aus. Grenze: nur STEP2-Episoden. Ob die Frage normalen Chat stört, ist hier nicht gemessen.

> Paketname geändert (Name geändert: Thread „B2 zitiert Regel selten“ vergab Z2e/Z2f parallel; Code/Skripte heißen weiter z2e/z2f/z2g).
