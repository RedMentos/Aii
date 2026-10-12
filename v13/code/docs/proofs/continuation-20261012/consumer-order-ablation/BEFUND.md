# Antwortendes Modell mit kompletten Regeln — Befund (Claude, 2026-10-12)

Zwei vorregistrierte Konsumenten-Ablationen. Eingabe sind byte-gleich die aufgezeichneten C3-Nachrichten des `wholesale_control`-Arms der Regel-Weiterreichung (komplette, hash-geprüfte frühere Regeln, 8 Fälle). Nur das antwortende Modell bzw. das Antwortschema ändert sich. Linux-Cloud, kein Redmi, `canonical_gate_pass=false`, keine Modellwahl.

- Teil 1 `consumer-model-ablation/` (Prereg `0a8096c8…f96b`, Report `d35728d9fb616e1c6d236dd795665cc78e7ef8d6b23bdfa894db5fa80b0a9af2`): 3 installierte Dateien (C3 LFM2.5-350M, B2 Qwen3.5-0.8B, B1 LFM2.5-1.2B) × 2 Schema-Reihenfolgen, 48/48 RECORDED.
- Teil 2 `consumer-order-ablation/` (Prereg `6a7ee382…392d`, Report `9106a03d737f46083524ff5bf918205887d5b72978f94b46e0942137ff909b0f`): erzwungene Reihenfolge „erst rechnen, dann entscheiden“ über Schlüssel-Aliase, 24/24 RECORDED.

| Konsument | Schema | Nutzen | exakt | Aktionen (Mira, Lumen, Nacre, Tessera, Orrin, Pelt, Quill, Rhea) |
|---|---|---|---|---|
| C3 350M | action zuerst | 0.469 | 0/8 | 8× NONE |
| B2 0.8B | action zuerst | 0.406 | 0/8 | NONE×4, A, NONE, A, NONE |
| B1 1.2B | action zuerst | 0.646 | 0/8 | 8× NONE |
| C3 350M | erzwungen | 0.573 | 0/8 | UNKNOWN×5, NONE, UNKNOWN×2 |
| B2 0.8B | erzwungen | 0.594 | 0/8 | 8× A |
| B1 1.2B | erzwungen | 0.667 | 0/8 | A×5, UNKNOWN, A, NONE |
Richtig wären: A, B, UNKNOWN, UNKNOWN, A, B, UNKNOWN, UNKNOWN.

## Befunde
1. **Kein Modell besteht die vorab festgelegte Regel** (≥3/4 exakt auf A/B-Fällen und ≥3/4 UNKNOWN). Auch das 1.2B-Modell nicht.
2. **Gefundener Fehler in der Laufzeit:** `v13.common.dumps` sortiert Schlüssel (`sort_keys=True`), und `runners.py` schickt das JSON-Schema so an llama-server. Damit wird die Reihenfolge im Schema verworfen: `action` wird immer **vor** den Optionen erzeugt (alphabetisch), die Entscheidung fällt also vor der Rechnung. Der Arm „options_first“ in Teil 1 war deshalb wirkungslos (Antworten byte-gleich) und ist als ungültig markiert. Gleiches gilt für `OFFER_SCHEMA` (`quotes` vor `summary`) und alle anderen Schemas.
3. Mit erzwungener Reihenfolge bricht das „immer NONE“ auf: B1 trifft Mira und Orrin (A) richtig und rechnet `remaining` meist korrekt; C3 kippt in „immer UNKNOWN“, B2 in „immer A“. Das ist Verhaltensänderung, aber noch kein Können.
4. **Bewertungs-Hinweis:** Das Feld `project` wird streng gegen den reinen Namen („Mira“) geprüft; die Modelle schreiben „Project Mira“ (so steht es in der Quelle). Das war in **jeder** Zeile aller vier Ablationen ein Widerspruch. Ohne dieses Feld wäre trotzdem keine Zeile exakt, deshalb ändert es das Ergebnis nicht; das Original-Gate bleibt unverändert.

## Was das ändert
- Laufzeit-Fix nötig: Schema in der angegebenen Reihenfolge senden (eigenes Paket, betrifft alle strukturierten Ausgaben, braucht neue gebundene Messung, weil sich auch B1/B2-Offers ändern).
- Budget/Eignungs-Rechnung bleibt für 0.35–1.2B unzuverlässig → deterministisches Rechen-Werkzeug (lokales Tool, Nutzerziel) ist der aussichtsreichere Weg als ein größeres Modell.
