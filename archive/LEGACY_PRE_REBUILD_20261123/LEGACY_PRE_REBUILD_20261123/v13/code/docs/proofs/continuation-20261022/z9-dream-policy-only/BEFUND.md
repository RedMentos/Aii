# WP-Z9 Befund: §99 „Dream helps“ — alle vier Kontrollen gemessen, Ergebnis `Z9_POLICY_DREAM_NO_GAIN`, Zuordnung `FACT_WRITE_CARRIES`

Vorregistriert (`PREREG.md`, Commit `eaeebb5` vor dem Lauf). Skript `scripts/z9_dream_policy_only.py`,
Daten `bench-results/z9-dream-policy-only-20261022/` (je Seed `z9-seed*.json`, `analysis.json`, `run.log`).
Protokoll unverändert von Dream2v3 (230M-Master sha `f630da86…`, LoRA r8, 40 Phase-B-Schritte, Seeds 13/21/34).
Basisauswertung und alle Basis-Generierungen reproduzieren Dream2v3 bytegleich; `dream_no_writes` Seed 13 ist in allen
Werten gleich `none` (Sanity erfüllt). Maske: je Policy-Arm 12 Traumfragen, 30 maskierte Fakt-Token; Masken-Prüfung bestanden.

## Mittel über 3 Seeds nach Phase B
| Arm | A-Recall | A-Paraphrase | Probe-Retention | Near-miss-Leak |
|---|---|---|---|---|
| none (kein Traum) | .33 | .42 | .61 | .33 |
| replay_exact (nur Replay) | 1.0 | .42 | .61 | .93 |
| dream_validated (Traum schreibt Fakten) | 1.0 | .75 | .19 | .93 |
| **dream_policy_only** (Traum ohne Fakt-Schreiben) | **.25** | **0** | .17 | .33 |
| **replay_dream_policy** (Sleep A + B blueprint-konform) | 1.0 | .50 | **.22** | .87 |
| replay_dream_validated (Sleep A + schreibender Traum) | 1.0 | .67 | .22 | .93 |

## Entscheidung nach Vorregistrierung
- Hauptvergleich `replay_dream_policy` gegen `replay_exact`: A-Paraphrase nur +0,08 (Schwelle +0,17) → **`Z9_POLICY_DREAM_NO_GAIN`**.
  Zusätzlich (beschreibend) kostet die Traum-Schicht viel allgemeines Wissen: Probe-Retention .22 statt .61.
- Zuordnung: `dream_policy_only` A-Paraphrase 0, also nicht über `none` (.42) → **`FACT_WRITE_CARRIES`**.
  Der Paraphrase-Vorteil der Träume aus Dream2v3 kam vollständig aus dem **Schreiben von Fakten** aus Träumen —
  genau das, was der Blueprint verbietet (`fact_write_authority = 0`, §15.6/§94.3).

## Was das heißt (einfach)
Träume, die nur „wie man antwortet“ üben dürfen und keine Fakten schreiben, helfen hier nicht; sie schaden sogar:
das Modell lernt den Antwortrahmen („Your cat is called …“) und füllt ihn dann falsch (A-Paraphrase 0, Recall .25).
Träume, die Fakten schreiben, helfen bei Umformulierungen, sind aber verboten und kosten zwei Drittel der allgemeinen Proben.
Damit ist die §99-Zeile „Dream helps“ **vollständig kontrolliert und nicht belegt**. Sleep B bleibt SHADOW; G-REPLAY-CONSOLIDATION-001
hat jetzt die Ablations-Basis, aber keinen Nutzen-Beleg für Träume (Replay selbst schützt A-Recall voll).

## Grenzen
4+4 erfundene Fakten, 230M-Master (nicht der 350M-C3), Cloud-CPU, 3 Seeds; „Policy“ ist hier der Antwortrahmen eines
LoRA-Spielzeug-Aufbaus, nicht eine echte Routen-/Weltmodell-Policy. Ein Traum-Mix mit Anker gegen Probe-Drift wäre ein
neuer, eigens vorzuregistrierender Versuch. `phone_measured=false`, `canonical_gate_pass=false`.
