# STEP2 neu binden nach WP-W1 — Vorregistrierung (Thread O, 2026-10-12 vor jeder Inferenz)

## Frage
WP-W1 (Thread H, `3316a10`) sendet JSON-Schemas mit Original-Schlüsselreihenfolge an llama-server.
Damit schreiben B1/B2-Offers jetzt `summary, quotes, uncertainty, needs_reentry` statt alphabetisch.
ROADMAP verlangt danach, STEP2 neu zu binden. Ändert der Draht den STEP2-Zwei-Körper-Nutzen?

## Aufbau (fest)
- Harness unverändert: `tests/integration_step2_utility.py` sha256 `a5a00d1f89eadda5e44ef68d2b2c1f33acf7d4dd354522f899cef6ea4525acf7`,
  10 Episoden × 7 Varianten, Fixtures `69e7ab3b…83cf`, Konsumenten-Schema `397cdd68…b162`, Seed 13, Gate `paired_utility` (unverändert).
- Wrapper `scripts/step2_wire_rebind.py`, zwei Arme, sonst alles gleich:
  - `w1`: Live-`runners.wire_json` (Reihenfolge erhalten).
  - `sorted`: `runners.wire_json` zur Laufzeit durch `common.dumps` ersetzt = exakt die Request-Bytes vor `3316a10`.
- Installiert (`/home/user/v13home`, frische `ModelManager.install` + offizielles Release-Binary):
  B1 LFM2.5-1.2B `bb741ebb…e1`, B2 Qwen3.5-0.8B `57d19977…f8cf`, C3 LFM2.5-350M `3d10b6ab…5b1d`, llama-server b10964 `79e31218…5d39` (gleich wie 2026-10-09).
- Reihenfolge: zuerst `w1`, dann `sorted`, seriell (nie zwei native Läufe gleichzeitig). Linux-Cloud, 4 CPU, kein Redmi.

## Primär (unverändert aus Harness)
`scoped_utility_gate_pass` = vollständig ∧ B1 und B2 gewinnen je eine Episode ∧ both_exact > best_solo ∧ > same_policy_dual ∧ > prompt_only_dual.
Bewertet je Arm. Ein FAIL bleibt FAIL; der Vergleich mit 2026-10-09 ist wegen anderem C3 (damals `e75f8326…`) nur beschreibend.

## Sekundär (vorab festgelegt, `diagnose()`)
- D1 mittlere Nutzen je Variante, beide Arme; Differenz `w1 − sorted` je Variante (n=10, keine Signifikanzbehauptung).
- D2 Regel-Transport: Zeilen, in denen ein verifiziertes Zitat an C3 `Budget <früheres Budget> euros` enthält; Zeilen, in denen eine Analysten-Hypothese die frühere Budgetzahl als Token enthält.
- D3 Aktions-Mix von C3 (A/B/NONE/UNKNOWN/INVALID) und exakte Treffer.

## Erwartung (vorab, ehrlich)
Primär FAIL in beiden Armen: die Konsumenten-Ablation zeigte, dass C3 350M die Rechnung auch mit vollständigen Regeln nicht schafft (0/8), und das STEP2-Schema lässt `action` in beiden Armen vor `options` stehen. W1 kann höchstens D2 (Offers mit Zusammenfassung vor Zitaten) verbessern.
Was die Implementierung ändern würde: steigt D2 unter `w1` deutlich, ist der Engpass allein der Konsument → STEP2-Werkzeug-Arm (WP-W2/READ_LOCAL, Thread H) als nächste vorregistrierte Variante. Bleibt D2 ≈ 0, ist der Produzent weiter der Engpass.
