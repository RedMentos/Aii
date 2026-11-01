# Befund: Eignungs-Werkzeug im Live-Pfad — Extraktions-Prompt (2026-10-21)

Vorregistrierung `PREREG.md` (Commit `298b6d7`, vor Inferenz gepusht). Linux-Cloud, gleiche Modelle/Runner wie 20.10., kein Redmi.

## Ergebnis: LIVE_PROMPT_SUPPORTED (alle vier Kriterien erfüllt)
| Kriterium | Schwelle | Basis (STEP2-Prompt-Replay) | **Live-Prompt** |
|---|---|---|---|
| 1 falsch festgelegt (70) | 0 | 0 | **0** |
| 2 „Regel behalten“, B2-Varianten (30) | ≥ 22 | 24 | **25** |
| 3 gesamt entscheidungs-exakt (70) | ≥ 51 | 54 | **55** |
| 4 alle RECORDED, Artefakte unverändert | ✓ | ✓ | **✓** |

Je Variante (von 10): b2_only, both_none, both_exact, both_control **10**; b1_only, same_policy_dual, prompt_only_dual 5.
Alle 15 Nicht-Treffer sind **UNKNOWN-Verweigerungen** in „Regel behalten“-Episoden, in denen die frühere Regel C3 nicht
erreichte (nur B1 bzw. B2 ohne Kontext, oder B2 zitierte sie nicht): das Werkzeug erfindet keine Regel.

## Was das heißt
Der Live-Pfad (`ToolStep._propose_eligibility` → C3 liest nur typisierte Werte aus Quelle + verifizierten Body-Zitaten →
Rezept entscheidet) ist auf denselben Belegen mindestens so gut wie der gemessene Replay. Zusammen mit
`offer_quote_context_chars=200` kommt eine früher gesagte Regel über B2 zu einer richtigen, begründeten Entscheidung.

## Grenzen
- Gemessen ist Extraktion + Rezept auf aufgezeichneten Belegen, nicht ein ganzer Live-Turn mit C5-Wahl und Antworttext.
- Werkzeug bleibt **aus** (Nutzerfreigabe im Chat `:growth enable eligibility` nötig) und bei Age 0 **SHADOW** (wird berechnet und mit
  der Antwort verglichen, nicht gezeigt). STEP2 bleibt UTILITY_FAIL; kein Redmi-, kein Kanon-Gate.
- BOOT-Wortregel `eligibility.asks` (Option A/B + Budget/Eignung), nicht gelernt.

Daten `code/bench-results/eligibility-live-20261021/`, Skript `code/scripts/step2_eligibility_live.py`, Tests `tests/test_eligibility_live.py`.
