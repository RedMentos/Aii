# B2-Offer-Kandidat gegen STEP2 + Werkzeug — Befund (Thread O, 2026-10-13)

Vorregistrierung `PREREG.md` (Commit `a73a8fe`, vor Inferenz gepusht). Daten `v13/bench-results/b2-offer-candidate-20261013/step2_cand.json`,
Werkzeug-Replay `tool_report.json`. 70 + 70 Zeilen RECORDED, Artefakte unverändert. Linux-Cloud, kein Redmi.
Kandidat: `cognition.patch` (B2 ohne body_state, Zitatkappe 90 statt 57 Zeichen, gleiches Budget), nur im Messprozess geladen.

## Kandidaten-Kriterien: alle vier erfüllt
| Kriterium | Schwelle | live (w1) | nur ohne body_state | **Kandidat** |
|---|---|---|---|---|
| 1 falsch festgelegt mit Werkzeug | 0 | 0 | 0 | **0** |
| 2 „Regel behalten“, B2-Varianten, exakt mit Werkzeug | ≥ 8/24 | 0/24 | 0/24 | **10/24** |
| 3 B2-Offers über eigenen Zustand | ≤ 5/50 | 41/50 | 0/50 | **0/50** |
| 4 Struktur/Artefakte | alles RECORDED | ✓ | ✓ | **✓** |

Entscheidungs-exakt mit Werkzeug je Variante: b2_only 7/10, both_none 7/10, both_control 6/10, both_exact 5/10, b1_only/prompt_only/same_policy 5/10 (live überall 5/10).
Rest-Ablehnungen in den 24 Zeilen: local_only nicht belegt 17, deadline 14, budget 9 (Qwen zitiert oft nur einen Teil des Regelsatzes oder gar nicht).

## Primär: STEP2 bleibt FAIL (wie vorab erwartet)
Mit Werkzeug both_exact .708 < b2_only .792; B1 gewinnt keine Episode allein. Ohne Werkzeug UTILITY_FAIL (both_exact .608 < b2_only .650).
Der Kandidat verbessert den Regel-Transport von B2, nicht die Zwei-Körper-Komplementarität; die STEP2-Fixtures geben B1 keine eigene Information.

## Folgen
- **Übergabe:** Patch `cognition.patch` + Tests `tests/test_b2_offer_candidate.py` an den Besitzer der Live-Kette (cognition.py ist über `source_handoff_candidate` exakt gebunden; Integration braucht ein Kettenglied). Schalter-Vorschlag nach Integration: `b2_offer_body_state=False`, `offer_quote_min_chars=90`.
- Offene Restgrenze: Qwen zitiert auch mit 90 Zeichen nur in ~40 % der nötigen Zeilen den ganzen Regelsatz.
- Für eine echte STEP2-Zwei-Körper-Aussage fehlen Fixtures mit B1-eigener Information.
