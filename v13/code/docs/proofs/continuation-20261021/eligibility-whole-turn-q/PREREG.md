# Vorregistrierung: Eignungs-Werkzeug im Live-Pfad — Extraktions-Prompt auf STEP2-Belegen (2026-10-21)

Vor jeder Inferenz dieses Laufs geschrieben und gepusht. Linux-Cloud, kein Redmi, kein Gate.

## Änderung
`v13/toolstep.ToolStep._propose_eligibility`: Fragt der Nutzer nach Option A/B unter Projektregeln (BOOT-Wortregel
`eligibility.asks`) und hat er das Werkzeug `eligibility` freigegeben, liest C3 nur typisierte Werte
(`eligibility.EXTRACT_SYSTEM` + `EXTRACT_SCHEMA`) aus aktueller Quelle + verifizierten Zitaten der Body-Offers dieses Turns
(`offer_quotes`, über den Store gelesen), das Rezept `eligibility-v2-anchored` entscheidet. Age 0: Werkzeugwahl bleibt
SHADOW (wird berechnet, verglichen, nicht gezeigt); Age 1 oder Messfreigabe: C5 kann TOOL_CALL wählen, TOOL_RESULT-Schicht
mit lesbarer Entscheidung. Tests `tests/test_eligibility_live.py`.

## Messung
Eingabe: STEP2-Report Arm `context` vom 20.10. (`bench-results/step2-quote-context-20261020/step2_context.json`,
sha256 `8010bbaca2b8efff5258899ab3ca9a6dfcb91c0a0b979c13371ca96e11c69d90`), 70 Zeilen. Je Zeile genau die Belege, die C3 bekam
(aktuelle Quelle + verifizierte Zitate). C3 extrahiert mit dem **Live-Prompt** (nicht dem STEP2-Prompt), Seed 13, gleiche Modelle.
Basis: Replay mit STEP2-Prompt (`tool_context.json`): 54/70 entscheidungs-exakt, „Regel behalten“ B2-Varianten 24/30, 0 falsch.
Skript `scripts/step2_eligibility_live.py`.

## Kriterien (LIVE_PROMPT_SUPPORTED, wenn alle erfüllt)
1. falsch festgelegte A/B/NONE: 0 von 70
2. „Regel behalten“, fünf B2-Varianten: ≥ 22/30 exakt (höchstens 2 unter Basis)
3. gesamt ≥ 51/70 exakt (höchstens 3 unter Basis)
4. alle Zeilen RECORDED, Artefakte unverändert

Sonst NOT_SUPPORTED: Live-Prompt wird an den STEP2-Prompt angeglichen und neu registriert. Erwartung: erfüllt.
