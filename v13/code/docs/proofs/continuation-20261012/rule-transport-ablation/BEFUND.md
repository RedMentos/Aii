# Regel-Weiterreichung als Zitat (Source-Handoff-Kandidat 2) — Befund (Claude, 2026-10-12)

Status **RECORDED_DIAGNOSIS**: 24/24 Zeilen, 0 Strukturfehler, echte B2 (Qwen3.5-0.8B) + C3 (LFM2.5-350M), Runner wie in der 16-Fall-Ablation, Artefakte unverändert. Preregistrierung `d34576bc…9d30` (vor der ersten Inferenz gepusht, Commit `dc7fb3d`). Report SHA256 `25f2fb97a8b0e9788145685f086b091b429198aa25ac4da9f57d9f0b964c9413`. Linux-Cloud, kein Redmi, `canonical_gate_pass=false`. Skript `scripts/rule_transport_ablation.py`, Tests `tests/test_rule_transport_ablation.py` (8).

| Arm | Nutzen | exakt | Zeilen mit früherem Zitat (alle / prior+override) | korrupt zugestellt |
|---|---|---|---|---|
| current | 0.469 | 0/8 | 1/8 · 0/4 | 0 |
| earlier_quotes | 0.469 | 0/8 | 4/8 · 2/4 | 0 |
| wholesale_control | 0.469 | 0/8 | 6/8 · 4/4 | 0 |

## Befund
1. **earlier_quotes besteht die vorab festgelegte Regel nicht** (2/4 statt ≥3/4). B2 versucht zu zitieren, paraphrasiert aber („Deadline 8.“ statt „Deadline 8 days.“, kleingeschriebenes „local-only“) → Zitat als nicht exakt verworfen. In Lumen (current_override) reichte es das **überholte** frühere Budget weiter; die Prüfung „aktuelle Regel ersetzt frühere“ fehlt im Feld.
2. **Auch wenn die Regeln vollständig ankommen (wholesale, 4/4), antwortet C3 in allen 24 Zeilen `action: NONE`**; der Nutzen ist in allen drei Armen gleich (0.469). Beispiel Mira: Budget 61, Frist 8, A kostet 45 bei 7 Tagen → richtig wäre A.
3. Damit verschiebt sich der Engpass: Nach dem Transport ist jetzt **der Konsument C3 (350M) der begrenzende Teil**. Er rechnet die Optionen nicht gegen die Regeln, sondern wählt immer NONE (wie schon in STEP2 70/70).
4. Korrupt-Kontrollen: in keinem Arm zugestellt.

## Was das ändert
- earlier_quotes nicht integrieren. Kein weiterer Transport-Kandidat, bevor der Konsument die Entscheidung mit vollständigen Regeln schafft.
- Nächster sinnvoller Test (separat preregistrieren): Konsumenten-Ablation mit wholesale-Regeln, also C3-Prompt/Schema (z. B. Feld `eligible` je Option vor `action`) und größerer Konsument (1.2B Body als C3-Referenz, gebundener Modellvergleich). Oder deterministischer Rechen-Kern (Tool) für Budget/Eligibility als Werkzeug-Aktion, passend zu Nutzerziel „lokale Tools“.
- STEP2 UTILITY_FAIL bleibt.
