# Vorregistrierung WP-Z2l: ganze Kette gegen die STEP2-Kriterien, mit Ein-Körper-Kontrolle (2026-10-26)

Vor jeder Inferenz committet und gepusht. Skript `code/scripts/step2_z2l_chain.py`, Tests `code/tests/test_step2_z2l.py`.

## Warum
WP-Z2k (`../step2-z2k-reader/BEFUND.md`) bestätigte die Kette für geänderte Regeln. Offen ist die STEP2-Frage: Ist die Kombination zweier Körper besser
als der beste einzelne, und lohnt der zweite, andere Körper gegenüber einem Körper mit zwei Zuständen (§99, Z2b-Kriterium 4b)?

## Kette (beide Arme)
`b2_context_chars` = 1536, Zeiger mit 4 Plätzen über ganze frühere Quellen (`b2_quote_choices=sources`), Eignungs-Werkzeug mit Wächter (`history`) und
`rule_reader='newest_quoted'`. Jede Extraktion wird so neu entschieden und mit `v13.utility.score_decision` neu bewertet („Ketten-Nutzen“).

## Aufbau
- Zehn **frische** Episoden: REVISED ×4 (Ankaa, Baten, Cursa, Durre), TWICE ×2 (Enif, Giausar), LONG ×2 (Homam, Imai), CONFIRM ×2 (Kitalpha, Mirach).
- Arme **CS** (zwei Körper: B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B) und **DS** (ein Körper, zwei Zustände, B2 = B1-Gewichte). Seeds **41, 42, 43**. 6 Läufe × 70 Zeilen.

## Entscheidungsregel (Ketten-Nutzen, Cluster-Bootstrap über die 10 Episoden)
1. `Z2L_INVALID` (Strukturfehler, Konsistenz) → 2. `Z2L_NOT_TESTABLE` (Kickoff < 90 % im Kontext) → 3. `Z2L_UNSAFE` (> 0 falsche Festlegungen der Kette).
4. `Z2L_TWO_BODIES_WORTH`: CS `both_exact` > bester Einzelkörper in CS (untere CI-Grenze > 0) **und** CS `both_exact` > DS `both_exact` (untere CI > 0).
5. `Z2L_COMBINATION_ONLY`: schlägt den besten Einzelkörper, aber nicht den Ein-Körper-Arm (dann reicht ein Körper mit zwei Zuständen).
6. `Z2L_NO_COMBINATION_GAIN`.
Sekundär: gegen `same_policy_dual` und DS `prompt_only_dual`, DS gegen seinen besten Einzelkörper, exakte Entscheidungen je Variante/Typ,
aufgezeichneter Nutzen (ohne Kette), B2-Regelquote.

## Erwartung vor dem Lauf
Kombination schlägt den besten Einzelkörper wahrscheinlich (Regeln kommen über B2, Optionen über B1). Ob der andere Körper den Ein-Körper-Arm schlägt, ist
offen; in Z2f lag DQP bei der Regelquote unter CQP. COMBINATION_ONLY wäre ein ehrliches Ergebnis gegen „zwei Körper lohnen“.

## Grenzen
Linux-Cloud, 4 CPUs, kein Redmi. Werkzeug-Nutzen, nicht Endnutzer-Antwort. Schalter bleiben live Standard/aus. Diagnose, kein Kanon-PASS.
