# Übergabe 2026-10-12 — §102-Ledger-Felder + §8.2/§93 Workspace-Slot-Schema (Thread „Nächste offene Pakete L“)

Branch `claude/project-thread-n3gv74`, Basis Thread G `bbd710e`. Linux-Cloud, kein Redmi-Nachweis, kein Modell nötig.

## 1. §102 Updated Completion Ledger Fields

- Neu `v13/neuro_ledger.py` + `specs/neuro-ledger.json`. `verification.completion_ledger` hängt an **jede** Zeile die zehn §102-Felder
  `neuro_inspiration_class, neuro_claim_limit, ablation_baseline, train_runner_proof_id, modulator_schema, eligibility_owner,
  corollary_required, replay_authority, age_window_policy, redmi_longrun_proof` plus `neuro_claim_status`. Ledger-Version 3 → 4,
  neuer Block `neuro_ledger` (Zählung je Klasse/Status, `untested_labels`, `missing_evidence`, `lowered_pass`).
- 38 Zeilen kuratiert aus den vorhandenen §99-Belegen (`docs/CORE_EXPERIMENTS.md`, `bench-results/ablation99-20261010`,
  `delayed-reward-20261010`, `age-noise-20261010`, `dream-ablation-20261010` + Dream2 v3, `episodic-ablation-20261010`,
  `jepa-*`, `step2-two-body-20261009`, `b3-l1-20261009`, `utility-20261010`, `r2-scope-20261010`). Alle anderen Zeilen: `NONE`.
- Stand der Behauptungen (leerer Home, Linux): Neuromod TESTED_PARTIAL; Age TESTED_NOT_SUPPORTED (BOOT); Proceduralisierung
  TESTED_SUPPORTED_SYNTHETIC; Dream/Replay, Focal-Koalition, JEPA-Prädiktoren, Gist TESTED_NOT_SUPPORTED; STEP2/Callosum/B3 TESTED_FAIL;
  ohne Ablation (UNTESTED_LABEL): Selbstmodell/Corollary, Homöostase, Metaplastizität, Attention-Gain, Workspace-Lernen, Episoden, Reflex, Latewatch u. a.
- Regeln: Klasse mit Hirn-Behauptung braucht `neuro_claim_limit`; ohne Ablation → `UNTESTED_LABEL`, und ein PASS-Gate wird auf PARTIAL gesenkt
  (heute trifft das keine Zeile: alle PASS-Zeilen sind STEP0-Infrastruktur ohne Hirn-Behauptung). Verdikt nur aus fester Liste,
  `modulator_schema` muss registriertes Schema sein, `eligibility_owner` muss existieren.
- Live statt kuratiert: `train_runner_proof_id` = neuester `TrainRunnerProof` mit passender `runner_revision` (sonst null);
  `age_window_policy` = `AGE_CONTROL:<age_plasticity_policy>`; `redmi_longrun_proof` = ABSENT, außer ein auf Android gemessener
  Sustained-Beweis liegt vor — und auch dann nur `BOUNDED_PHONE_ONLY`, nie „Langlauf“.
- Belegpfade werden geprüft; fehlende Datei markiert die Zeile nur (das Handy-Paket enthält keine `bench-results`). Im Repo prüft
  `test_evidence_files_exist_in_repository`, dass jeder zitierte Beleg existiert.
- Grenze: Action-JEPA Runden 6–8 (Werkzeug-Welt bestätigt) und G1B GIST_NO_GAIN liegen auf anderen Branches und sind nur im Text der
  Zeilen erwähnt, nicht als Belegpfad.

## 2. §8.2 / §8.2A / §93 Workspace-Slot-Minimum

- `contracts.SLOT_FIELDS` (Pflicht für `FocalItem` und für `WorkspaceSlot.content`): `self_generated`, `created_wall` (Zeitstempel),
  `origin_event_id`, `age_ms`, `expiry` (BOOT-Turn-Zerfall: verbleibende Turns bis zur Drop-Grenze), `confidence_type`,
  `exact_fallback` + `exact_fallback_refs` (Zeiger auf die exakte Quelle), `scale` (fine/phrase/sentence/event/topic/gist),
  `covered_range` (vereinigte Quellspannen je Quelle), `compression_ratio` (abgedeckte Zeichen / Slot-Text), `boundary_confidence` +
  `boundary_source`, `children`/`parents` (Cross-Scale-Links). `validate_slot` prüft Typen und Konsistenz (z. B. SOURCE_REF ⇔ Refs vorhanden,
  Grenz-Quelle NONE ⇔ Konfidenz null, Körper-Offers sind immer `self_generated`).
- `focal.item` füllt alles; `focal.boundary` = **gekennzeichneter lexikalischer Proxy** (`LEXICAL_ALIGNMENT_PROXY`): Anteil der Spannen-Enden auf
  Satz-/Teilsatzgrenzen in der exakten Quelle; nicht gelernt, keine semantische Grenze. Gedächtnis-Einträge sind menschliche Entscheidungen → `self_generated=False`.
- Zurückgehaltene Slots behalten ihren ursprünglichen Zeitstempel, altern und verlieren Restlaufzeit (Test in `test_focal.py`).
  Ausnahme: der Legacy-Einzeldurchlauf `cognition.focal` (`admission='LEGACY_FIRST_N'`, nur Proofs/Ablationen) bleibt beim alten
  Feldsatz, weil `cognition.py` von der SourceHandoff-Kandidatenkette byte-gebunden ist; der Live-Turn (`FocalLoop`) schreibt immer das volle Minimum.
- Alte, bereits gespeicherte Pakete werden nicht neu validiert (Validierung nur beim Schreiben); alte Workspace-Zustände laden weiter
  (`created_wall` fällt auf `admitted_wall` zurück).

## Tests
- Neu `tests/test_neuro_ledger.py` (6), `tests/test_workspace_slot.py` (3), Erweiterung `tests/test_focal.py`. Volle Suite 1249 OK, 4 Skips (kein PyTorch), Linux-Cloud.

## Offen
- Ablationen für die UNTESTED_LABEL-Zeilen (Selbstmodell/Corollary, Homöostase, Attention-Gain, Workspace-Lernen) vorregistrieren.
- `boundary_confidence` aus echter Event-Segmentierung (`episodes.text_segments`) statt lexikalischem Proxy, sobald B2-Slots echte Segmente tragen.
- `docs/completion-ledger.json` ist ein alter Export (Version 2); neuer Export über `:doctor`.

## 3. Folge: §99-Ablationen für ungetestete Hirn-Etiketten (vorregistriert, synthetisch)
- Metaplastizität (META-Regel in `neuromod`): **PARTIAL** — schlägt nur P = 1; festes konservatives/budgetgleiches P ist besser, Neuheits- und Wiederholungsterm helfen nicht (Rauschen öffnet Plastizität wieder). `bench-results/homeo-meta-20261012/`.
- Homöostase (`homeostasis.regulate`): **SUPPORTED_SYNTHETIC**, kleine Abstände; Nutzen aus Update-Budget-Dämpfung + Wiederöffnen toter Pfade, Dominanz-Dämpfung ≈ 0. Gleiche Ordner.
- Corollary/Selbstmodell: Zuordnung schlägt alle Kontrollen, aber fremde Ereignisse auf offenem eigenem Kanal werden zu MIXED (54–66 %); Dämpfung schlägt keine/zufällige, volle Abziehung besser → **PARTIAL**. `bench-results/corollary-20261012/`.
- `specs/neuro-ledger.json` aktualisiert: UNTESTED_LABEL 15 → 13. Volle Suite 1253 OK / 4 Skips.
- Nächste Kandidaten (je eigene Vorregistrierung): rauschbewusster META-Wiederöffnungsterm; `attribute` mit Toleranz-Obergrenze (weit daneben → EXTERNAL/UNCLEAR).
