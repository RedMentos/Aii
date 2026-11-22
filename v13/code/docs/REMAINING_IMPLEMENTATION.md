> **Hinweis 2026-10-10 (WP-T15):** Diese Tabelle ist der Stand vom 2026-09-29 und führt inzwischen Erledigtes noch als fehlend. Maßgeblich sind `ROADMAP.md` und `ABDECKUNG.md` im Projektordner sowie `docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md`. Bekannter Blocker, der hier fehlte: der 46-Zeilen-Nativlauf scheiterte vor dem Fit am SQLite-Export (`checkpoint_kind CAUSAL_NATIVE46_NINTH_EXPORTED_SQLITE_FAILED_BEFORE_FIT`); er ist nach dem SQLite-Close-Guard am Handy zu wiederholen.

# Verbindlicher Restumfang — 2026-09-29

Die SSOT bleibt unverändert. Diese Liste streicht keine Anforderungen und
erklärt bestandene Teiltests nicht zur fertigen Gesamtarchitektur.

| Bereich | Ausführbar und nachgewiesen | Tatsächlich noch fehlend |
|---|---|---|
| STEP0 | Persistenz mit transaktionalen Schema-Migrationen, Provenance, Operator, persistente Queue/Cancel, Generation/Rollback, Schemas, Setup, kontinuierliche Ressourcen-Telemetrie | Breitere Langzeit-/Migrationsnachweise; zeitbasierte Diagnose-Retention jetzt implementiert und auf Quellen-/Chat-/Proof-Erhalt geprüft |
| STEP1 | C2-only, C3-only, C2+C3 ohne B; C1-Aufgaben-/Quellen-/Action-Kontinuität und Quellen-Governor mit Neustart; gepinnter C3-Vergleich; externe native First-Route-Agreement-Kalibrierung | Native Confidence-Head-Training und allgemeine Confidence; breitere Sprachqualität und stabiler Redmi-Resident-Pfad |
| STEP2 | Echte B1/B2-Ausgaben; Fine/Gist-Views; begrenzter B2-Kontext; Angebote und Kanäle | Validierte semantische Komplementarität; native Sparse-Bodies; gemessene Dauer-RAM-Grenze auf Redmi |
| STEP3 | Human-Korrektur, quellengebundener Second-Attempt, Neustart, negative Transfers | Allgemeine Übertragung auf unbekannte Frageformen; gelernter Needle-Paar-Relevanz-Head mit Quellenbindung, Ablationen, Retention und nativer Report-Nutzung ist jetzt implementiert |
| STEP4 | Getrennte Self-/Reference-/Human-Lanes; ganze Antwort/Spans wählen; persistenter JSONL-Export | Breitere Teacher-on/off-Qualitätsmessung; stärkerer Teacher nur bei tatsächlichem Import |
| STEP5 | Externe Route/Wake/Halt-Heads; lokale Held-out-Kalibrierung, tatsächliche Runtime-Nutzung, komponentenbezogene Freigabe/Neustart/Rollback | Allgemeine/native semantische Confidence, native Mehrpositions-Output-Adaptation und trainierter Executive-Latent-State; externer nativer First-Token-Delta jetzt implementiert |
| STEP6A | NONE/EXACT/CONTROL/SYMBOLIC und Ablationen | Generalisierte Nutzennachweise |
| STEP6B/C | A3-Text-Projector mit getrenntem Alignment/Reconstruction und realem JEF-Shadow-Consumer; read-only Dense-Taps; externer lokaler t+2-Predictor mit Target-EMA, Nicht-Kollaps-/Ablations-Gates und explizitem Tap-Consumer | A3 multimodale Ports/Teacher-Parity, native Receiver-Injection, B3-Projectors/Empfänger-Kalibrierung; vollständige A/B-/Cross-JEPA-Ziele, aktive Expert-Deltas und quantisierter Body-Train-Runner |
| Self/World/Fabrics | Eigene digitale Zustände, beobachtete Aktion/Outcome-Paare, empirische Timing-Prognose, externer action-conditioned digitaler Latent-Predictor mit Target-EMA, festem Retention-Referenztest und wirklichem _turn-Consumer, Fehler und Crash-Recovery | Semantischer World-/Self-JEPA, kausale Dynamik, gelernte Multi-Mode-Prognosen, neural trainierte Metaplastizität und native Shared-Layer-Homeostasis; gemessener langsamer F7-Shadow-Budget-Regler ist jetzt ausführbar |
| Memory/Sleep | Exact/Fast-Episodic, echtes Episodic Replay, hypothetischer Dream-Entwurf | Native parametrische Semantic-/Skill-Konsolidierung, unbekannte Cue-Generalisierung und autonome Schlafphasen; bestätigte Human-Quellenindizes, Verdichtung, exakte Verfahren und native Replay-Nutzung jetzt implementiert |
| STEP7 | Ausführbarer wiederholter Test mit Ressourcenmessung, Neustarts und Teilberichten | Umfangreiche Sessions/Wochen, Retention/Drift, tatsächliche Redmi-Thermal-/Energie-/RSS-Werte |
| STEP8–11 | Als Fähigkeiten ausdrücklich gesperrt | Vision/Audio/weitere Effectors, Full-Duplex, Teacher-Removal, höhere Ages; laut SSOT erst nach stabilem Age0-Core |

`specs/component-contracts.json` enthält alle 30 aktuellen A/B/C/F-Komponenten
mit Code-/Schema-Zuordnung. `specs/learning-objectives.json` enthält das reale
Routing-Lernziel und die noch nicht implementierten Ziele mit Lernfreigabe null.
Ein Contract ist kein Implementierungs- oder Trainingsnachweis.

## Konkrete nächste Implementierung

1. Den aktuellen Build auf dem Redmi mit `bash TESTEN.sh --compare-c3` messen.
   Fehlende Sensorwerte bleiben unbekannt. Das alte `SMOKE_PASS` ist historisch.
2. Native Body-/Train-Port-Fähigkeiten tatsächlich herstellen und separat
   beweisen: read-only Basis, konkrete Tap-IDs, trainierbare aktive Parameter,
   persistente Train-Master-/Quantisierungsartefakte und exakt gebundene Revisionen.
   Der im Canon genannte MobileMoE-Kandidat verlangt Zugang; der beobachtete
   öffentliche Zugriff ist separat unter `docs/research/` dokumentiert. Ein
   fehlender Zugang rechtfertigt keinen behaupteten Ersatz-Train-Runner.
3. ObjectiveAdapter gemäß IH-H25: wirkliche Inputs/Targets, stop-gradient und
   EMA, analytisch geprüfte Gradienten, Nicht-Kollaps-/Retention-Gates und
   tatsächlicher Consumer. Beliebige Zufallsvektoren oder MSE allein sind kein
   JEPA-Nachweis. A/B-/World-/Executive-Ziele einzeln ablieren.
4. Bridge zuerst als kleinste tatsächlich unterstützte kontinuierliche
   Schnittstelle; danach Receiver-Norm, OOD, Utility, No-Message/Exact-Ablation
   und Router-Stabilität messen. Bis dahin bleiben native Latent-Rechte null.
5. Zusätzliche trainierbare Komponenten benötigen komponentenbezogene
   Generation-Manifeste. Route, Wake, Halt sowie B1/B2-Predictors besitzen getrennte
   Artefakt-Einträge. Bestehende Deltas dürfen bei Erweiterungen nicht verschwinden.

Diese Lücken sind noch nicht erledigte Entwicklungsarbeit. Die neue ZIP ist
ein ausführbarer, geprüfter Arbeitsstand und enthält alle vorhandenen Teile.

Neue Software-Nachweise (2026-10-04): Migration/Queue14 Tests, Runtime-Queue5 Tests, C1/Governor11 Unit- und11 native Prüfungen sowie native Ressourcen-/Abbruchprüfung15 Checks. Einzelne native Reports sind historisch, sobald die Quellen anschließend geändert wurden. Der aktuelle Gesamtcollector bindet alle21 Pfade an denselben Quellstand.

## Native progress and remaining gates — 2026-10-08

- STEP2 now has a preregistered70-row structured scorer and complete first native run (230actualFINALcalls).54rows fail restored body-state identity; all failed raw rows/Stores remain available. Restart isolation and a separate corrected attempt are required before any utility conclusion.
- C3 output head lifecycle23/23 passes for known human-labelled greeting/thanks first tokens. The complete retrieval test remains27/28 because the tiny C3 receiver does not use the required source value; B1 does. No gate is removed and no fixed source copy is counted as model output.
- The existing BodyPort live-prefill observer has a compiled isolated native prototype. Actual feature/logit/continuation parity, old head compatibility and phone measurements remain necessary before replacing separate prefills in the runtime.
- Cheap C5/F6 exact approved replies and transitive revoked-rule history guards are implemented. General learned semantic safety, native recursive multimodal learning and C6/C7 external effectors remain separate unfinished capabilities.
- The SSOT remains unchanged; runnable source ZIP, BUILD_STATE and raw proofs are checkpointed during continuing work. Compilation, Linux smoke and historical individual proofs do not mark the whole architecture complete.

## Aktueller Code- und Proofstand — 2026-10-09

Der korrigierte STEP2v3-Vergleich ist vollständig:70/70 strukturell gültige Varianten, echte C3-Ausgaben und vollständige Prozessbereinigung. Das vorregistrierte semantische Nutzen-Gate bleibt `UTILITY_FAIL`; B1 allein ist stärker als die primäre Kombination. Der frühere fehlgeschlagene Lauf bleibt erhalten.

Der native Observer und die native Pause/Fortsetzung besitzen getrennte tatsächliche numerische Nachweise. Ein neuer Python-Port verbindet einen gebundenen C3-Kontext mit derselben Fortsetzung;10Software-Protokollprüfungen bestehen, sein neuer Client-Nachweis ist noch offen. Der vorhandene Worker erzeugt vier Tokens; ein vollständiger Produktions-Streamingpfad ist damit noch nicht hergestellt. Native Lern-/Receiver-/Freigaberechte bleiben getrennt.

Der Gesamtcollector besitzt `--resume` und `--stage-limit` mit unverändert vollständiger Stufenliste. Code, echte Modelle, Runner, Einstellungen und abgeschlossene Rohdateien müssen identisch bleiben; abgeschlossene Fehler werden nicht entfernt.


2026-10-09: Fresh recovered native midlayer numeric cohort passes baseline/zero/nonzero checks, with full-vocabulary effect. Actual live Python client passes10 collector/15 session checks and emits four real tokens. Original alias-check failure remains byte-identical. No learned head, production streaming, speed improvement or current Redmi proof is inferred. Adjacent full streaming implementation is in progress; complete70 STEP2 remains UTILITY_FAIL.


2026-10-09: Adjacent full causal C3 streaming is executable via TESTEN_NATIVE_STREAM.sh --prompt with64/128 output caps or actual EOS. One unchanged-greeting Linux baseline/zero pair passed all8 exact invariance checks, emitting13 tokens inclEOS, with12 unbiased decodes/no extra-prefill and both workers reaped. This is not semanticquality/training/production/phone promotion. Raw proof and old4token source are preserved.


2026-10-09 final checkpoint: Causal fullstream source compiled/guarded; native baseline-zero byteparity13tokenEOS and separate long97tokenEOS runPASS (128cap configured, not reached). New causal-live train entry reuses original optimizer/gates,6softwarechecksPASS, genuine labelledcohort absent. Strict collector retained realJEF proof unchanged and resumed onlynext Experience stage: bothPASS, overall2/20 remainsDIAGNOSTIC_INCOMPLETE. Actual sharedNeedleworker pin fixed, firstpreflight failure preserved. Finalsource liveclient SOFTWARE:10complete rawcases plusoneisolated lastcasePASS; full11run rawterminalsummary missing andnotclaimedcomplete. Full70STEP2 remainsUTILITY_FAIL. Production/nativeweights/SSOT unchanged; no fullarchitecture or phonepromotion.

2026-10-09 continuation: original acceptance source frozen byte-for-byte before adjacent development;3/20native stagesPASS. Newworking-source export and phasecheckpoint helpers are separate and not promoted by oldcohort results.


## Causal-live labelled export — 2026-10-09

The adjacent `scripts/export_live_output_dataset.py` now lists valid original output labels, captures actual pause/features/tokens/context/completion plus native label tokenization, and assembles exact hashed portable trainer input. The installed operator command is `:feedback output <reference text> --learn`; export separately requires explicit original decision/source IDs and `--learn`. A new persisted typed export decision transparently links byte-preserved original human authority to the later observed native ABI; it never claims the human saw future features and never uses the model preview as a label. See `docs/LIVE_OUTPUT_DATA_EXPORT.md`.

Six focused software checks pass. The FIRST isolated Linux TEST_OPERATOR lifecycle passes: two actual Runtime FINAL turns, two actual same-context zero-bias native captures (11/23 decoded tokens), native first-label rows55382/5732, zero extra-prefills and all template/worker processes reaped. Original decisions and production/model/source hashes remain unchanged. The unchanged trainer validates input then reports `INSUFFICIENT_LABELLED_COHORT` with zero optimizer steps. This is authored TEST_OPERATOR protocol evidence, not a genuine end-user training cohort, a learned live candidate, quality gain, current Redmi evidence, approval or production activation.

Resume using `labels`, explicit `capture --decision ... --label-source ... --learn`, then `assemble --fragment ...` and the unchanged trainer's `--validate-only`. Collect genuinely intended operator labels on distinct exact source queries before any fit; source-disjoint minimums/calibration/gradient/retention gates stay strict. The frozen original acceptance cohort remains3/20 and must resume separately from its exact archived source. Full70 STEP2 remains `UTILITY_FAIL`; native sparse-body/B3 utility, current Redmi sustained evidence and full-plan completion remain open. Proof: `docs/proofs/live-output-export-native-20261009/report.json`; source-bound audit: `docs/proofs/live-output-export-prepared-20261009/final-audit.json`.

2026-10-09 production integration: STARTEN_CAUSAL.sh installs/prepares/selects the actual same-causal C3 decoder in existing persistent Chat.15actual lifecycle checks and362software regressionsPASS; fixed rules, feedback lineage andrestart preserved. Independent originalserver matches exacttokens/output, queryecho retained as poor-quality observation. Learnedcausal candidate consumer, nativebody/quantgradient/B3 utility and targetphone sustained gates remainopen. Fullscope/SSOT completion isfalse.
