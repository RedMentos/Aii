# V13 — Cross-Organ Weight Editing & Self-Optimization: Implementierungsvertrag (2026-11-11)

**Status:** BACKLOG / DESIGN ONLY. Kein neues Laufzeitrecht, kein Modellupdate, keine Gate-Promotion. Quelle: Nutzer-Nachtrag `v13/USER_ADDENDUM_2026-11-11_SELF_OPTIMIZATION.md`. Grundlage: integrierter Kandidat PR #1716 und JEPA-Holdout PR #1737 (beide separat review-only). Diese Datei überschreibt weder Canon noch fremde Ownership.

## 1. Ziel / Begriff

**Gewichte direkt editieren** bedeutet: Ein von Organ X erzeugtes Lern-/Fehlersignal darf durch einen *explizit autorisierten, vom Zielorgan überprüften* Updatepfad die trainierbaren Tensoren von Organ Y ändern, sodass vor/nach-Gewichte verschieden sind, das trainierte Ziel besser bewertet wird und der Zustand persistiert. Nicht ausreichend: Prompt-Umformung, Rollenrouting, reine Erkenntnisprotokolle, ein isolierter Toy-Fit ohne Runtime-Consumer oder behauptetes In-place-Edit von GGUF.

Beispiel: T8 trusted `(state, action, next_state, source_id)` -> WorldJEPA EMA/PredictionError -> B1/B2 trainierbares Adapter-Objective (inklusive Fehler × Eligibility × Modulation) -> vom jeweiligen Organ kontrollierter Optimizer -> Delta/Provenance -> neuer Reader-Stand/Checkpoint -> disjunkte Holdout-/Retention- und Restart-Prüfung. WorldJEPA **schlägt** Update-Signale vor; es erhält keine pauschale Schreibbefugnis auf B1/B2/C3-Basistensoren. Später kann autorisierte Gegenseitigkeit und adaptive Selbstoptimierung zugelassen werden.

## 2. Minimaler Organ-übergreifender Vertrag

Eingabe `LearningIntent` (typisiert und persistent):
- `producer_organ`, `target_organ`, `target_model_revision`, `target_parameter_scope`, `objective_revision`, `optimizer_revision`
- trusted `source_ids` / `T8_transition_ids`, Consent-/Revocation-Snapshot, zeitliche Provenance und Quellenbindungs-Hash
- separate train/validation/old-retention cohorts; keine Testdaten im Update
- `eligibility_trace`, Fehler-/Surprise-Signal, `neuromodulation`, Gradienten-/Norm-Budget, `age_capability`, Freigabe-ID, `expires_at`

Vor Anwendung `TargetOrganOptimizer`:
- Zielorgan prüft Modell-/Source-/Objective-Revision, eigene Rollenrechte, aktive Quelle, Parameter-Allowlist, RAM-Zeitbudget und monotonen Event-/Checkpoint-Cursor.
- Rechnet einen begrenzten trainierbaren Schritt (`float32/float16 master`, LoRA/PEFT/kleiner Head oder gesondert autorisierte Master-Tensoren), dokumentiert Gradientennorm, wirklichen Hash/Diff, Optimizer-State und Nicht-Endlichkeit.
- Atomarer Publish: Source-/Learning-Receipts, Modell-/Optimizer-Artefakte, Manifest/Generationszeiger und Cursor müssen konsistent sein. Bei Crash, Widerruf, fehlendem Einverständnis oder Regression: keine Teilpromotion, eindeutiger Rollback/Quarantänepfad.
- `WeightDeltaReceipt`: Source-Lineage, betroffene Tensoren/Hash alt-neu, Loss vorher/nachher, disjunkte Holdouts, alte Retention, CPU/RAM/Walltime, Freigabe/Gate und Consumer-Revision.
- Beim Lauf auf quantisiertem GGUF: native Basistensoren bleiben unverändert, außer ein separat spezifizierter, geprüfter Master->Quantisierung->Deployed-Runner-Export mit Qualitätsvergleich ist freigegeben.

## 3. Stufen / DoD (nicht als abgeschlossen markieren, bevor die jeweilige Evidenz vorliegt)

| Stufe | Realer Fähigkeiten-Zuwachs | Mindestbeweis |
|---|---|---|
| S0: Ausführbarer World-Pfad | Trusted T8 -> Update -> persisted JEPA/EMA -> Restart/Readback | CI auf genauem HEAD; Quellen-Revoke, Cursor, echte Gradienten/EMA und datendisjunkter Holdout |
| S1: Cross-Organ Adapter | World/JEF/Body signalisiert B1 oder B2 einen zulässigen Parameter-Update; Target besitzt Optimizer | Vor/nach-Parametertensoren, korrekte Source-Lineage, tatsächlich neuer Runtime-Consumer, isolierter Restart/Rollback |
| S2: Bidirektionales Lernen | Organ A und B lernen mit explizitem Arbitration/Gating voneinander, ohne zirkuläre Selbstbestätigung | No-signal/Random-signal/Frozen-target/EMA-off Ablationen; A->B->A Retention; N>1 Seeds; OOD/Interferenz |
| S3: Selbstoptimierung | AG8/F7/JEF erzeugen und vergleichen eigene Lern-/Routing-/Konsolidierungsvorschläge | Gleiche festgehaltene Kohorten, Regression Shield, Nutzen und Ressourcen; dauerhaftes Revert; keine Test-Leakage |
| S4: Strukturelles Self-Edit | Genehmigte neue Trainer/Adapter/Architektur/Code-Komponenten in Sandbox + kontrollierter Austausch | Signierte/reproduzierbare Artefakte, unabhängiger Review, isoliertes Experiment, reversible Promotion; erhöhte Rechte |

**Zu messen:** Disjunkte Train/Calibration/Test-IDs und Inhalte; Per-Organ-Loss und Task-Utility vor/nach; alte Retention/Forgetting; Replay on/off; Gradient-shuffle; Quelle nach Widerruf; doppelte/gleichzeitige T8-Events; Restart vor/nach Commit-Crash; gemessene CPU/PSS/RSS/Temperatur auf Redmi; echte Token-Ausgaben auf unveränderter Basis. Negative Ergebnisse erhalten.

## 4. Bestehender Code und konkrete nächste Schnittstelle

Bekannt: `v13/code/v13/agi/self_improve.py` (AG8 Vorschlag/Sandbox), `v13/code/v13/agi/trainers.py` (u. a. C3 LoRA), `v13/code/v13/plasticity.py`, `v13/code/v13/body_jepa.py`, `v13/code/v13/online_world.py`, `v13/code/v13/continuous_predictor.py`, `v13/code/v13/agi/eligibility.py`, `v13/code/v13/neuromod.py`.

**Nächster Code-Schnitt statt Guard-Mikro-PRs:** Auf eigenem JEPA-Integrationsbranch einen minimalen typisierten `LearningIntent` + B1/B2 Float-Adapter-Consumer im *bestehenden* PR-#1716/#1737 T8/World-Pfad anbinden. Dazu einen synthetischen Runtime-Test für (A) erlaubte Actual-Weight-Update-Route, (B) verbotenes Cross-Write, (C) Restart/Cursor/Restore, (D) vorher/nachher Holdout samt Replay-off-Ablation. Keine doppelte Fork-Implementierung des Train-Runners; Cross-Organ-Contract mit Core/B1B2/Boss abgleichen.

**Ownership:** JEPA/Memory: World/T8/LearningIntent und Messung. Core/B1B2: Eigentümer der trainierbaren Body-Tensoren/Optimizer und nativer Reader. Boss: Verträge, Canon, Integrationszweig. QA: adversariale Regression/Redmi-Hardware. Forschung: Objectives/empirische Papers/Lizenzen. Alle Änderungen in getrennten PRs mit geprüfter Abhängigkeit; keine globalen Age-0-Gates, die lokale erlaubte Lernupdates pauschal unterbinden.

**Bekannte Risiken:** Goodhart/Metrik-Hacking, zirkuläre Labels, Rückkopplungs-Instabilität, Retention-Kollaps, Quellenwiderruf nach Gewichtseinfluss, quantisierte Master/Deployed-Divergenz, Handy-RAM und irreversible Fehlupdates. Unlernen nach Widerruf nicht behaupten, solange Retrain/Rollback/Isolation nicht nachgewiesen.

**Status / Nachweis:** Diese Datei spezifiziert zukünftige Arbeit. Es wurden durch ihre Erstellung **keine** Modellgewichte verändert, kein Code ausgeführt und keine Tests als bestanden behauptet. `canonical_architecture_complete=false`, `user_full_scope_complete=false`.
