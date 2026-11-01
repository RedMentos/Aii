# Vorregistrierung: ganze Live-Turns mit Eignungs-Werkzeug (2026-10-21)

Vor dem frischen Lauf gepusht. Regel, Seed und Code-Hashes stehen bindend in `prereg.json` (Skript `scripts/eligibility_live_turn.py`).
- Je Episode neue Sitzung, drei echte Runtime-Turns: frühere Regel → Ablenker → Frage Option A/B. Arme: `c3_alone` (Werkzeug aus) vs `tool_active` (Werkzeug an, Age-Urteil nur für dieses Werkzeug durch Messfreigabe ersetzt). Beide Arme mit Zitat-Schaltern an.
- Bewertet wird die Entscheidung im Antworttext (`decision_of`, feste Regel) gegen das Orakel.
- **TOOL_TURN_SUPPORTED** genau dann, wenn auf frischem Seed 31 (24 Episoden): Netto-Gewinne ≥ +5 UND Vorzeichentest p < .05 UND falsch festgelegte Entscheidungen mit Werkzeug ≤ ohne Werkzeug UND nicht mehr Turn-Fehler als ohne.
- Dev-Seed 7 (4 Episoden, nur zum Finden von Verdrahtungsfehlern): Werkzeug 4/4 richtig, C3 allein 2/4. Vor dem Dev-Lauf gefunden und behoben: mit Zitat-Schalter AN brach jeder echte Turn mit „Consumer quote differs from offered quote“ ab (`analyst_context`), und frühere Nutzer-Nachrichten fehlten als Beleg.
