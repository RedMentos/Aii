# WP-Z9 Vorregistrierung: §99-Kontrollen „dream no writes“ und „dream policy-only“

Geschrieben und committet **vor** dem ersten Lauf (2026-10-22, Thread „Offene Ziel-Pakete Z6 bis Z12“).

## Frage
Blueprint §99 verlangt für „Dream helps“ vier Kontrollen: no dream, replay only, dream no writes, dream policy-only.
Dream2v3 (15/15, `docs/proofs/continuation-20261012/dream2-b40-v3/`) hat no dream (`none`) und replay only
(`replay_exact`). Es fehlen „no writes“ und „policy-only“. Blueprint §15.6/§94.3/L8.2: Sleep B hat
`fact_write_authority = 0`, `DREAM.fact_write_gain = 0`, Dream lernt nur Policies/World („policy/world only, no facts“).
Der Dream2v3-Arm `dream_validated` trainiert dagegen die Quell-**Faktantwort** auf Traumfragen, schreibt also Fakten.
Offen ist deshalb: kommt der Paraphrase-Vorteil der Träume (.75 statt .42) aus Fakt-Schreiben (vom Blueprint verboten)
oder aus einem Policy-Anteil (Frage-Form → richtiger Antwortrahmen), den auch eine blueprint-konforme Sleep B hätte?

## Aufbau (unverändert von Dream2v3 übernommen)
230M-Master `LiquidAI/LFM2.5-230M@40cb2ad3…` (sha256 `f630da86…cfd`), Torch FP32, LoRA r8 auf DEFAULT_TARGETS,
Phase A Fakten A (4), Phase B genau 40 Schritte auf Fakten B + Mix je Arm, Seeds 13/21/34, `--per-fact 3`,
Traumdatei `bench-results/dream-ablation-20261010/dreams.json`, gleiche Anker-Prüfung (`split_dreams`), gleiche Auswertung
(`split_eval`). Kein Skript aus Dream2v3 wird verändert; neues Skript `scripts/z9_dream_policy_only.py` importiert es.

## Neue Arme
- `dream_no_writes`: geprüfte Träume werden erzeugt und gezählt, schreiben aber nichts (Mix = nur B).
  Erwartung: bytegleich zu `none` desselben Seeds. Nur Seed 13 (Identitätsprüfung, keine Nutzenaussage).
- `dream_policy_only`: B + dieselben geprüften Traumfragen wie `dream_validated`, Antwort = gespeicherte Quellantwort,
  **aber Loss-Maske auf allen Token, die den Faktwert tragen** (Token, deren Zeichen den Schlüssel überdecken, z. B. „Mitzi“).
  Gradient nur auf den Antwortrahmen („Your cat is called … .“), kein Gradient zum Faktwert = `fact_write_gain = 0`.
- `replay_dream_policy`: B + exaktes A-Replay (Sleep A, echte Episoden dürfen schreiben) + `dream_policy_only`-Mix.
  Das ist die blueprint-konforme Sleep A + B.
- `replay_dream_validated`: B + exaktes A-Replay + `dream_validated`-Mix (schreibend). Gegenstück, um den Preis des Schreibens zu sehen.
Alle drei Seeds für die drei letzten Arme. Vergleichswerte `none`, `replay_exact`, `dream_validated` aus Dream2v3 (gleiche Seeds,
Basisauswertung muss gleich reproduzieren; sonst Ergebnis `NOT_COMPARABLE`).

## Größen und Entscheidungsregeln (je Arm Mittel über 3 Seeds; Raster je Seed: A 1/4, Probes 1/12)
Hauptvergleich (§99 „Dream helps“ gegen „replay only“, blueprint-konform):
`replay_dream_policy` gegen `replay_exact`.
- **Z9_POLICY_DREAM_HELPS**: A-Paraphrase im Mittel ≥ +0,17 und in keinem Seed niedriger, **und** Probe-Retention im Mittel
  höchstens −0,09 und A-Recall im Mittel höchstens −0,09.
- **Z9_POLICY_DREAM_COSTS**: A-Paraphrase ≥ +0,17, aber Probe-Retention oder A-Recall schlechter als −0,09.
- **Z9_POLICY_DREAM_NO_GAIN**: sonst.

Zuordnung (woher kommt der Traum-Vorteil?): `dream_policy_only` gegen `dream_validated` und `none`.
- **POLICY_CARRIES**: A-Paraphrase von `dream_policy_only` höchstens 0,09 unter `dream_validated`.
- **FACT_WRITE_CARRIES**: A-Paraphrase von `dream_policy_only` höchstens 0,09 über `none`.
- **MIXED**: dazwischen.
Preis des Schreibens (beschreibend): `replay_dream_validated` gegen `replay_dream_policy` in Probe-Retention und Near-miss-Leak.

Sanity: `dream_no_writes` Seed 13 muss in allen `after_b`-Werten gleich `none` Seed 13 aus Dream2v3 sein, sonst `NOT_COMPARABLE`.
Maskenprüfung: jedes Policy-Item hat ≥ 1 maskiertes Token, und kein ungemaskiertes Label-Token-Stück enthält einen Schlüssel.

## Grenzen (vorab)
4+4 erfundene Fakten, 230M-Master statt 350M-C3, Cloud-CPU, kleine Stichprobe (3 Seeds). Ergebnis schließt höchstens die
§99-Kontrollzeile in diesem Spielzeug-Aufbau, nicht den ganzen Sleep-Pfad; `phone_measured=false`, `canonical_gate_pass=false`.
Ein FAIL bleibt FAIL; keine nachträgliche Schwelle.
