# Vorregistrierung: STEP2 B2→C3-Transport — Zitat als Zeiger auf exakte Quellsätze (2026-10-20)

Geschrieben und gepusht **vor** jeder Inferenz dieses Laufs. Linux-Cloud, kein Redmi. STEP2-Kanon-Gate wird nicht befördert.

## Befund vorher (nur aus bereits aufgezeichneten Daten, keine neue Inferenz)
Thread O (2026-10-13, `bench-results/b2-offer-candidate-20261013/step2_cand.json`, Schalter `b2_offer_body_state=False`,
`offer_quote_min_chars=90`): Die frühere Projektregel ist ein Ereignis aus vier kurzen Sätzen
(„Project X. Budget N euros. Deadline D days. Local-only requirement: true.“). Qwen-B2 zitiert sie meist
**zerstückelt** („Project Borealis. Budget 90 euros.“ + „Deadline 4 days.“) oder **umgeschrieben** („local-only requirement: true.“,
klein geschrieben → Zitatprüfung verwirft es). Vollständige Regel in den verifizierten B2-Zitaten, die C3 erreichen:
**7/30** „Regel behalten“-Offers (`scripts/step2_quote_context.transport`). Das ist der Engpass zwischen B2 und C3:
B2 *findet* die Regel, aber der exakte Zitat-Kanal transportiert nur Bruchstücke.

Offline-Simulation auf denselben aufgezeichneten Zitaten (explorativ, vor dieser Vorregistrierung):
nur Groß/Klein-/Leerzeichen-tolerant 7/30, + Satzgrenzen 7/30, + Nachbarsätze bis 200 Zeichen **21/30**.

## Änderung (live, Schalter, Standard aus)
`v13/cognition.quote_span` + cfg `offer_quote_context_chars` (0 = aus = bisherige exakte Prüfung byte-gleich).
Bei N>0: ein Zitat, das sich von der Quelle nur in Groß/Klein-Schreibung oder Leerraum unterscheidet, gilt als belegt;
ein Zitat ab 12 Zeichen wird auf seine ganzen Sätze derselben Quelle erweitert, dann auf Nachbarsätze, solange die
Spanne ≤ N Zeichen bleibt. **Transportiert wird immer der exakte Quelltext** (SourceRef-Spanne), das Zitat ist nur Zeiger.
Kettenglied `integrated_candidates.quote_context` (bindet `source_handoff_candidate` weiter exakt). Tests `tests/test_quote_context.py`.

## Arme (gleiche Modelle/Runner wie 13.10.: B1 bb741ebb…, B2 57d19977…, C3 3d10b6ab…, Runner b10964)
Beide mit `b2_offer_body_state=False`, `offer_quote_min_chars=90`; unveränderter STEP2-Harness (70 Zeilen), danach
Werkzeug-Replay (`scripts/step2_tool_replay.py`, eligibility-v2-anchored, Seed 13).
- **control**: `offer_quote_context_chars=0`
- **context**: `offer_quote_context_chars=200`

Skript `scripts/step2_quote_context.py --arm control --arm context`. Reihenfolge: control, dann context, nacheinander.

## Kriterien (context gegen control desselben Tages)
1. **Transport:** volle frühere Regel in verifizierten B2-Zitaten der „Regel behalten“-Zeilen (30 B2-Offers):
   context ≥ control + 8.
2. **Keine falschen Festlegungen:** Werkzeug-Replay context, alle 70 Zeilen: 0 falsch festgelegte A/B/NONE.
3. **Entscheidung:** Werkzeug-Replay, „Regel behalten“-Zeilen der fünf B2-Varianten (30): decision-exakt context ≥ control + 5.
4. **Struktur:** alle Zeilen RECORDED, Quellen/Artefakte unverändert, in beiden Armen.

Alle vier erfüllt → `CONTEXT_SUPPORTED`: Empfehlung, den Schalter zusammen mit den B2-Offer-Schaltern einzuschalten
(Nutzerentscheidung, ändert alle Offers). Sonst `NOT_SUPPORTED`, Schalter bleibt aus.

## Erwartung (vorab notiert)
Kriterien 1–4 erfüllt. STEP2-Harness-Gate (Zwei-Körper-Nutzen) bleibt **UTILITY_FAIL** in beiden Armen, mit und ohne
Werkzeug: die Fixtures geben B1 keine eigene Information, b2_only bleibt bestenfalls gleichauf. Ohne Werkzeug rechnet
C3 weiterhin nicht (`remaining`), daher kaum Gewinn im Harness selbst. Risiko: in Überschreibungs-Episoden erreicht die
alte Regel C3 jetzt vollständig; das Werkzeug muss die aktuelle Regel vorziehen (Kriterium 2).
