# WP-W2 Deterministisches Eignungs-Werkzeug — Befund (Thread H, 2026-10-12)

Status **RECORDED_DIAGNOSIS** 72/72, 0 Strukturfehler, Artefakte unverändert. Preregistrierung `189828d3…0c72` (vor der ersten Inferenz gepusht, `897a025`), Report SHA256 `ff3efa687860439f559824ce932c8ad35e4f4fe9e948c1617068989b9f9d7bf5`. Skript `scripts/calc_tool_ablation.py`, Tests `tests/test_calc_tool_ablation.py` (8). Eingaben: byte-gleich die aufgezeichneten wholesale-Nachrichten der Regel-Weiterreichung (wie Konsumenten-Ablation). Modelle bytegleich (gleiche SHA256 wie dort); Runner b10964 in diesem Container neu gebaut (Hashes im Prereg), **neuer Draht WP-W1** (Schema-Reihenfolge erhalten). Linux-Cloud, kein Redmi, `canonical_gate_pass=false`, keine Modellwahl, STEP2 UTILITY_FAIL bleibt.

Primärmetrik (vorab festgelegt): Entscheidung exakt = alle Felder außer `project` (Modelle schreiben „Project Mira“); strenge Exaktheit zusätzlich berichtet.

| Konsument | Arm | Entsch. exakt | streng exakt | Nutzen | A/B ok | UNKNOWN ok | Regel |
|---|---|---|---|---|---|---|---|
| C3 350M | action_first | 0/8 | 0 | 0.573 | 0/4 | 4/4 | FAIL |
| C3 350M | options_first | 0/8 | 0 | 0.583 | 0/4 | 4/4 | FAIL |
| C3 350M | **extract_tool** | **7/8** | 0 | 0.885 | 3/4 | 4/4 | **PASS** |
| B2 0.8B | action_first | 0/8 | 0 | 0.562 | 0/4 | 0/4 | FAIL |
| B2 0.8B | options_first | 0/8 | 0 | 0.615 | 0/4 | 0/4 | FAIL |
| B2 0.8B | **extract_tool** | **8/8** | 0 | 0.917 | 4/4 | 4/4 | **PASS** |
| B1 1.2B | action_first | 1/8 | 0 | 0.677 | 1/4 | 0/4 | FAIL |
| B1 1.2B | options_first | 0/8 | 0 | 0.677 | 0/4 | 0/4 | FAIL |
| B1 1.2B | **extract_tool** | **7/8** | 5 | 0.938 | 3/4 | 4/4 | **PASS** |

## Befund
1. **Mit dem Werkzeug bestehen alle drei Modelle die Regel**, ohne Werkzeug keines, auch nicht mit der jetzt wirksamen Reihenfolge „erst Optionen, dann Entscheidung“ (W1). Optionswerte (Kosten, Tage, lokal) werden in 24/24 Zeilen richtig gelesen; das Rechnen war der Engpass.
2. **Wichtige Grenze: Die UNKNOWN-Fälle löst der Zahlen-Wächter, nicht das Modell.** Kein Modell gibt bei fehlender Regel `null` zurück; alle erfinden ein Budget (100, 10000, 50) und teils eine Frist (2024, 30). 24/24 erfundene Werte wurden vom Wächter verworfen (Wert kommt nicht als exaktes Token in aktueller Quelle oder verifiziertem Zitat vor). Der Wächter ist damit tragend; er versagt, wenn ein erfundener Wert zufällig als anderes Token im Text steht (z. B. gleich einer Kosten-Zahl). Nächster Härtungsschritt: Wert an seine Fundstelle binden (Zitat-Span je Regel statt Token-Suche).
3. **Regel-Auswahl bei Überschreibung bleibt fragil:** Pelt (current_override) liest C3 die alte Frist 8 statt 5 (falsche Aktion A), B1 das alte Budget 69 und Frist 8 (Aktion zufällig richtig, `remaining` falsch). Lumen haben alle richtig. B2 hat beide richtig.
4. Ohne Werkzeug auf dem neuen Draht: C3 sagt fast immer UNKNOWN, B2 action_first immer NONE, options_first meist A; B1 meist A. Das ist Verhaltensänderung gegenüber dem alten Draht, kein Können (die alten Messungen der Konsumenten-Ablation sind für den alten Draht gebunden).

## Was das ändert
- Ein deterministisches Eignungs-Rezept (§6.5: deterministische externe Tool-Rezepte dürfen dauerhaft bestehen) plus Zahlen-Wächter macht die Entscheidung mit kleinen Modellen möglich; die kognitive Aufgabe reduziert sich auf „typisierte Werte lesen und aktuelle Regel wählen“.
- Noch nicht integriert: Rezept + Wächter sind Skript-Kandidaten. Integration als Werkzeug im ToolRegistry/C5-Pfad (READ_LOCAL, IH-H29) und eine STEP2-ähnliche, gebundene Messung mit echtem Produzenten (nicht wholesale) sind eigene Schritte. Wächter vorher an Fundstellen binden (Punkt 2).
