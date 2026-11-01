# Befund: STEP2 B2→C3-Transport — Zitat als Zeiger (2026-10-20)

Vorregistrierung `PREREG.md` (Commit `3d9e767`, vor Inferenz gepusht). Linux-Cloud x86_64, 4 CPUs, kein Redmi.
Modelle/Runner byte-gleich mit dem 13.10.-Lauf (B1 bb741ebb…, B2 57d19977…, C3 3d10b6ab…, b10964).
Beide Arme: `b2_offer_body_state=False`, `offer_quote_min_chars=90`; unveränderter STEP2-Harness, je 70 Zeilen + Werkzeug-Replay 70 Zeilen.

## Ergebnis: CONTEXT_SUPPORTED (alle vier Kriterien erfüllt)
| Kriterium | Schwelle | control (`offer_quote_context_chars=0`) | **context (`=200`)** |
|---|---|---|---|
| 1 volle frühere Regel in B2-Zitaten an C3, „Regel behalten“ (30 Offers) | ≥ control + 8 | 7/30 (10 nur teilweise) | **23/30** (0 teilweise) |
| 2 falsch festgelegt mit Werkzeug (70 Zeilen) | 0 | 0 | **0** |
| 3 „Regel behalten“, B2-Varianten, exakt mit Werkzeug (30) | ≥ control + 5 | 11/30 | **24/30** |
| 4 Struktur (RECORDED, Quellen/Artefakte unverändert) | alles | ✓ | ✓ |

Entscheidungs-exakt mit Werkzeug je Variante (von 10): context b2_only **10**, both_none **10**, both_control **10**, both_exact 9,
b1_only 5, prompt_only_dual 5, same_policy_dual 5 (control: 7/7/6/6/5/5/5). b2_only „Regel behalten“: alle 6 exakt (control 3/6).
Überschreibungs-Episoden (B2-Varianten, 16 Zeilen) in beiden Armen 16/16 exakt: die jetzt vollständig ankommende alte Regel
verführt das Werkzeug nicht (aktuelle Regel gewinnt). Laufzeit STEP2 je Arm ~8–9 min Zeilen + Vorbereitung.

## Was das heißt
- Der Engpass zwischen B2 und C3 war der **exakte Zitat-Kanal**: Qwen-B2 fand die Regel, zerlegte sie aber in Teilzitate
  oder schrieb sie klein („local-only requirement: true.“ → verworfen). Als Zeiger auf exakte Quellsätze (≤ 200 Zeichen
  derselben Quelle) kommt die Regel in 23/30 statt 7/30 Fällen ganz an. Transportiert wird weiterhin nur exakter Quelltext.
- Rest 7/30: B2 zitiert die frühere Regel gar nicht (z. B. nur aktuellen Text) — das ist jetzt der B2-Auswahl-Engpass.

## Was es nicht heißt
- **STEP2 bleibt UTILITY_FAIL** (beide Arme, mit und ohne Werkzeug, wie vorab erwartet): B1 trägt nichts Eigenes bei
  (b1_only 5/10, die Fixtures geben B1 keine eigene Information), Zwei-Körper ist nicht besser als b2_only (Werkzeug: both_exact .842 < best_solo .917).
- **Ohne Werkzeug 0/70 exakt** in beiden Armen: C3 (LFM2.5-350M) rechnet `remaining`/Eignung nicht. Der Gewinn entsteht nur
  zusammen mit dem deterministischen Eignungs-Werkzeug (WP-W2c). Gleicher Befund wie der private STEP2-Pilot vom 20.10.
- Kein Redmi-, kein Kanon-Gate. Schalter bleibt im Code **aus**.

## Empfehlung / offen
1. Nutzerentscheidung: `offer_quote_context_chars=200` zusammen mit `b2_offer_body_state=false`, `offer_quote_min_chars=90`
   einschalten (ändert alle Body-Offers; laufende Messungen anderer Threads vorher getrennt binden).
2. Eignungs-Werkzeug in den Live-Antwortpfad (C5/READ_LOCAL) — ohne es bleibt jeder Transportgewinn unsichtbar.
3. Für eine echte STEP2-Zwei-Körper-Aussage: neue, vorregistrierte Fixtures, in denen B1 eigene Information hat (Original bleibt eingefroren).

Daten: `code/bench-results/step2-quote-context-20261020/` (Zusammenfassungen, Werkzeug-Replays, Log, SHA256SUMS);
volle STEP2-Reports (je ~3 MB) im Projektordner `v13/bench-results/step2-quote-context-20261020/`.
Skript `code/scripts/step2_quote_context.py`, Code `v13/cognition.quote_span`, Kettenglied `scripts/integrated_candidates.quote_context`, Tests `tests/test_quote_context.py`.
