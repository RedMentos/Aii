# WP-W2b Zitat-gebundener Werkzeug-Wächter — Befund (Thread H, 2026-10-12)

Status **RECORDED_DIAGNOSIS** 144/144, 0 Strukturfehler, Artefakte unverändert. Preregistrierung `a6800726…98c0` (vor der ersten Inferenz gepusht, `f8f28c3`), Report SHA256 `9511e5b8a23146c741b657fdc62d02951af5abcecb550973eaa96a63c2ba9f5a`. Skript `scripts/calc_tool_span_ablation.py`, Tests `tests/test_calc_tool_span_ablation.py` (8). C3 350M, B2 0.8B, B1 1.2B (gleiche Modell-Hashes wie WP-W2), W1-Draht, Linux-Cloud, kein Redmi, `canonical_gate_pass=false`, STEP2 UTILITY_FAIL bleibt. Entscheidungsregel auf den **8 neuen Fällen** (konstruierte Nachrichten im aufgezeichneten Format); die 8 alten Fälle sind exponiert und nur berichtet.

| Konsument | Arm | neu: Entsch. exakt | A/B ok | UNKNOWN ok | Regel (neu) | alt (exponiert) |
|---|---|---|---|---|---|---|
| C3 350M | action_first | 0/8 | 0/4 | 4/4 | FAIL | 0/8 |
| C3 350M | extract_tool (Token-Wächter) | 6/8 | 2/4 | 4/4 | **FAIL** | 7/8 |
| C3 350M | extract_span (Zitat-Wächter) | 4/8 | 0/4 | 4/4 | **FAIL** | 4/8 |
| B2 0.8B | action_first | 0/8 | 0/4 | 0/4 | FAIL | 0/8 |
| B2 0.8B | extract_tool | **8/8** | 4/4 | 4/4 | **PASS** | 8/8 |
| B2 0.8B | extract_span | 4/8 | 0/4 | 4/4 | FAIL | 4/8 |
| B1 1.2B | action_first | 0/8 | 0/4 | 0/4 | FAIL | 1/8 |
| B1 1.2B | extract_tool | **8/8** | 4/4 | 4/4 | **PASS** | 7/8 |
| B1 1.2B | extract_span | 4/8 | 0/4 | 4/4 | FAIL | 4/8 |

## Befund
1. **Zitat-Wächter fällt durch:** Mit ihm antworten alle Modelle in allen 48 Zeilen UNKNOWN (4/8 sind nur die richtigen UNKNOWN-Fälle). Die kleinen Modelle liefern keine brauchbaren exakten Zitate: C3 meist „Budget 74 euros“ (passt), aber für local-only nur „false“/„true“ ohne Regelwort; B2 schreibt „>=74“, „}“; B1 „74 euros“ ohne Regelwort oder Regel-Formeln aus dem Systemtext. Die Bindung an Fundstellen ist so mit 0.35–1.2B nicht nutzbar; das ist ein negatives Ergebnis, kein Wächter-Fehler.
2. **Token-Wächter bestätigt sich auf neuen Fällen für B2 und B1 (8/8)**, C3 nur 6/8: in Umber liest C3 die überholte Regel (local-only true statt false → NONE), in Tarn/Sable ok. Regel-Überschreibung bleibt die Schwachstelle von C3.
3. **Kein Modell gibt bei fehlender Regel null zurück** (0/48 auf neuen UNKNOWN-Fällen über beide Werkzeug-Arme): es erfindet 100 oder übernimmt die 80 aus der Analysten-Hypothese. Beides hat der Token-Wächter verworfen. Die vorab gebaute Kollisionsfalle (Kosten 50/100 bei fehlendem Budget) wurde **nicht ausgelöst**, weil kein Modell genau diesen Wert erfand (Yarrow: Kosten 100, Modelle sagten 80). Die Lücke des Token-Wächters ist damit nicht widerlegt, nur nicht getroffen.
4. Ohne Werkzeug auf neuen Fällen: B1/B2 fast immer NONE, C3 immer UNKNOWN.

## Was das ändert
- Für die Integration bleibt der **Token-Wächter** (WP-W2) die gemessene Variante; Zitat-Bindung durch das Modell nicht weiterverfolgen. Bessere Härtung ohne Modell-Zitate: Wächter verlangt Regelwort **im Evidenztext unmittelbar vor dem Wert** (deterministisch, z. B. „Budget <n> euros“), statt das Modell zitieren zu lassen. Das wäre ein reiner Code-Kandidat und kann an diesen aufgezeichneten Antworten offline nachgerechnet werden (keine neue Inferenz nötig).
- Konsument mit Werkzeug: B2/B1 bestehen auf frischen Fällen, C3 nicht (Regel-Überschreibung). Modellwahl bleibt separat gebunden.
