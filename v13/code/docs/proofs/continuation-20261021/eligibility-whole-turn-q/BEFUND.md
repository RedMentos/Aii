# Eignungs-Werkzeug `eligibility` im echten Antwort-Turn (2026-10-21, Thread „Nächste Pakete Q“)

**Verdikt (vorregistriert): TOOL_LIVE_SUPPORTED und TOOL_SHOWN_SUPPORTED.** Vorregistrierung `preregistration.json` (sha256 `879bade2…`, Commit `a94f91c`, gepusht vor dem frischen Lauf), Rohdaten `live-fresh29.json` (sha256 `8e04d843…`), Bericht `report.json` (sha256 `6ff5a8f8…`), Entwicklung `live-dev7.json` (+ zwei frühere Entwicklungsrunden in `dev-iterations/`).

## Was neu ist

WP-W2c/W2d hatten das regel-verankerte Rezept nur offline bzw. mit aufgezeichneten Übergaben gemessen. Jetzt läuft es im normalen Runtime-Turn, genau wie `list_arith` (R4 Teil 6):

1. `toolstep._propose_eligibility`: BOOT-Regel `eligibility.question` (Option A und Option B + Entscheidungswort) – nur wenn der Nutzer das Werkzeug freigegeben hat, sonst kein Modellaufruf.
2. C3 (LFM2.5-350M) kopiert nur typisierte Werte (`eligibility.READ_SCHEMA`: zwei Optionen, budget/deadline/local_only oder null), rechnet nichts.
3. Frühere exakte Evidenz: die **eigenen früheren Nachrichten des Nutzers** im History-Fenster (gespeicherter Quelltext, keine Modellausgabe) und **quellen-geprüfte Zitate** der ausgewählten Körper-Offers (`analyst_context`). Hypothesen und Assistenten-Antworten zählen nie.
4. `eligibility.decide` (unverändert) entscheidet; Wächter: Regelwert nur direkt nach dem Regelwort, Konflikt mit aktueller Regel → abgelehnt, Optionswerte nur im eigenen Satz.
5. C5/IH-H29 wie jedes Werkzeug: Alter 0 → SHADOW (Ergebnis nur verglichen, `compare` = Antwort trifft die Entscheidung); freigegeben → TOOL_RESULT-Schicht mit Antwortsatz („Choose Option A. Remaining budget: 16 euros.“ / „I cannot decide yet: the budget rule is missing …“), Broker hängt eine späte Korrektur an, wenn die Antwort die Entscheidung nicht trifft.
6. Runtime-Änderung (eine Zeile: `plan(e,text,offers=selected,version=version)`) als Kettenglied `integrated_candidates.eligibility_live`, damit die hash-gebundenen Kandidaten-Prüfungen weiterlaufen.

Für die Messung wurde nur das Alters-Urteil für `eligibility` ersetzt (`age_right_measurement`), alles andere ist der unveränderte Pfad. Je Aufgabe zwei Arme in neuer Sitzung auf C3 (Beobachter aus, R4 BENCH_CFG, history_turns 2): `c3_alone` (Werkzeug aus) und `tool_active`.

## Frische Aufgaben (Seed 29, 60 Aufgaben, je 15 pro Art)

| Art | n | C3 allein richtig | mit Werkzeug richtig | netto | p | falsch festgelegt allein → Werkzeug | sichtbar richtig (mit Korrektur) | Rezept falsch |
|---|---|---|---|---|---|---|---|---|
| complete (eine Nachricht) | 15 | 4 | **13** | +9 | .004 | 9 → 2 | 14 | 0 |
| missing (Regel fehlt → UNKNOWN) | 15 | 0 | 0 | 0 | 1 | 13 → 13 | **15** | 0 |
| earlier (Regeln im 1. Turn) | 15 | 10 | 11 | +1 | 1 | 5 → 3 | 14 | 0 |
| override (2. Turn ändert Regel) | 15 | 8 | 8 | 0 | 1 | 6 → 5 | 10 | 0 |
| **gesamt** | 60 | 22 | **32** | **+10** | **.006** | **33 → 23** | **53** | **0** |

Kriterien: (a) netto ≥ +10 und p < .05 ✓, (b) falsch festgelegt nicht höher ✓, (c) Rezept nie falsch ✓, (d) keine Art verliert mehr als 2 ✓. Zweites Urteil (mit Korrektur): netto +31, p < .0001, Rezept nie falsch ✓.

Weiteres: 60/60 Vorschläge, 60/60 ausgeführt, 0 Lesefehler im Schema; Werte exakt gelesen 33/60 (complete 13, earlier 9, missing 6, override 5); Rezept-Entscheidung richtig 42/60, sonst UNKNOWN (33×). Zeit pro Turn Median 1,8 → 2,6 s.

## Lesart

1. **Das Rezept schadet nie:** 0 von 60 falsch festgelegten Entscheidungen. Wenn C3 falsch liest, lehnt der Wächter ab (`not_stated`, `option_not_stated`, `conflicts_current`) statt zu raten.
2. **Bei vollständigen Regeln in der aktuellen Nachricht** wirkt es auch im Antworttext stark: 4 → 13 von 15.
3. **Fehlende Regel:** C3 350M sagt im eigenen Text nie „kann nicht entscheiden“ (0/15, auch mit Schicht) – erst die Broker-Korrektur macht es sichtbar (15/15). Das 350M-Modell übernimmt UNKNOWN/NONE aus der Schicht kaum.
4. **Frühere/geänderte Regeln:** Transport klappt (eigene frühere Nachricht als Evidenz), aber C3 kopiert beim Lesen oft die alte statt der neuen Regel (override: nur 5/15 exakt gelesen) → Wächter lehnt ab → UNKNOWN. Sicher, aber wenig Nutzen; hier liegt der nächste Engpass (Lesen, nicht Rechnen).

## Grenzen

Generierte englische Aufgaben im festen Wortlaut des Wächters („budget 61 euros“, „Option A: cost 45 euros, duration 7 days, local true“) – andere Formulierungen ergeben UNKNOWN; Regex-Parser für die Antwort; ein Körper (C3), kein STEP2/B1-B2-Transport (STEP2 bleibt UTILITY_FAIL); Alters-Recht für die Messung ersetzt (im Betrieb SHADOW bis Alter 1); Linux-Cloud-CPU, kein Redmi.

Parallel und unabhängig davon hat der Thread auf Branch `claude/project-thread-dq33gk` am selben Morgen eine eigene Fassung derselben Live-Anbindung gebaut (Prompt-Ebene auf 70 aufgezeichneten Zeilen: LIVE_PROMPT_SUPPORTED, Befund unter `continuation-20261021/eligibility-live/`); diese Messung hier liefert dessen offenen Punkt „ganzer Live-Turn“. Beide Fassungen müssen beim Zusammenführen abgeglichen werden (`toolstep.py`, `agi/eligibility.py`, `tests/test_eligibility_live.py`).

Reproduktion: `scripts/eligibility_live.py capture <home> <seed> <n_pro_art> <out>` · `prereg` · `evaluate`; Tests `tests/test_eligibility_live.py` (10), volle Suite 1609 OK.
