# 2026-11-12 — no-input scheduler and actual runtime recovery

Source parent: `0d6bd47b116f89c44c94c4d5ac6308afd604bac7`. User supplied
phone measurements and reiterated that ongoing work without input is required.
No raw phone transcript, device process identifier or private chat was committed.

Confirmed gaps and repairs in the isolated, composed runtime copy:

- Original scheduler stops after 12 background dispatches until a new accepted
  user turn. New explicit `:idle on` renews at most 12 existing jobs per rolling
  hour (or a smaller configured budget), without fabricated input. Default
  remains unchanged. Retries count; quota persists; clock rollback, corrupt
  state, pauses, resources, quiet hours, input priority and Age remain binding.
  `:idle status` is read-only and reports the worker, quota, cycles, block reason
  and actual small world-model fit/sample state. This is not large-body training.
- The B1 smoke probe used a separate 35s structured-offer deadline after its
  90s smoke call, then erased successful smoke evidence if the offer failed.
  Phase results, budgets, durations and metrics now survive failure. Overall
  failure still fails. Increasing observer_seconds is a diagnostic, not a claim
  that B1 now passes on the phone.
- Plain chat reprinted persisted assistant messages at every process start.
  It now identifies saved history without presenting it as fresh output, while
  new messages and ongoing streams still render. Bare `:learning` is a read-only
  mode query before the idle mutation guard; explicit mode changes retain it.
- The bridge installer did not switch the actual model-runtime launcher.
  `scripts/termux_runtime_recovery.sh` stages the entire pinned composed build
  and uses explicit `--activate`. The helper verifies all staged source hashes
  and syntax, requires the model runtime stopped, backs up the launcher/settings
  and SQLite privately, then atomically switches the launcher. Rollback changes
  only the launcher and preserves later messages/settings. No model download or
  learning permission is granted. Android platform path aliases are supported.

Frozen original Runtime, Store, operator, scheduler, UI and verification files
remain byte-identical. New behavior is staged by the updated existing stager;
all earlier World/Body/context/resume changes and imported scripts/native helpers are retained. The user must execute
activation and start the chat, then send `:idle on`, before this runs on the phone.
Existing false completion flags and all negative evidence remain unchanged.

Validation:

- Real coordinator/SQLite, accelerated clocks: six hourly sleep cycles and more
  than 12 completed existing jobs, zero accepted user turns/messages/native PIDs;
  enablement, sleep state and honest TOO_FEW_TRANSITIONS persisted on restart.
- Combined recovery and six existing real-stage suites: 34 passed, 9 intentional
  child-only skips, 5 subtests passed; nested idle suite separately 9 passed.
- Activation helper: 16 passed under umask 022, including SQLite snapshot,
  restart lease, Android ancestor alias, PREPARED crash recovery and rollback
  preserving new data. Node/Android/native inference was not used by these tests.
- Runtime recovery shell syntax passes. The staged context CI now includes all
  recovery suites. One external anyio/pytest deprecation warning remains local.

Phone instructions and reversible commands:
`code/docs/TERMUX_RUNTIME_RECOVERY_20261112.md`.
Android background process survival and B1 success are still unmeasured by this
repair. Large GGUF body training remains unavailable. Drive storage was already
full at the prior backup attempt; GitHub and local ZIP are the available saves.

# 2026-11-12 — Termux bootstrap / browser-button recovery review

CI follow-up: the first published owner-read run `43165385938` exposed a
test-fixture permission assumption under the runner's umask 022. The fixture
now explicitly creates its private directory with mode 0700; mobile-dashboard
and bootstrap tests pass locally under umask 022. Original bridge-security CI
`43165385950` passed. The Drive ZIP backup attempt was rejected with HTTP 403
`storageQuotaExceeded`; no Drive backup is claimed. The public-source ZIP is
retained locally and the code is saved on the GitHub work branch.

Reviewed source: PR #1794 head `26f6247f63632d7e16bb41ac17e9d9de83458dad`.
Both supplied Actions runs (`43164147674`, `43164147641`) were successful;
these are offline software checks, not proof of phone connectivity.

The existing head already fixes the mobile button URL bug: an input named
`action` shadows `HTMLFormElement.action`; the script uses
`form.getAttribute('action')` and urlencoded POST bodies. The Node regression
rejects the old expression. Real mobile Chromium clicked start, send and
shutdown against the actual local HTTP UI with a disposable echo process;
the transcript was recorded and there were no browser errors. No real model
or Redmi run was performed.

This follow-up fixes the installer: preserve explicit local STOP; refuse a
running V13 before updating; stop only matching same-home idle dashboards
before changing their source/template; briefly pause old UIs while checking
for live children, and resume them unchanged on refusal. Reject unexpected
origins/branches and dirty source; replace branch reset with fast-forward
merge. Keep ancestry when fetching updates to a shallow clone. Run freshly
loaded modules from their own source directory. Treat terminated zombie
bridge processes as stopped. No model/runtime source under `code/v13/` changed.

Validation from `v13/code`:

- `python -m pytest -q tests/test_remote_maintenance_bridge.py tests/test_termux_patch_staging.py tests/test_owner_read_bridge.py tests/test_source_updater.py tests/test_managed_console_dashboard.py tests/test_mobile_dashboard.py tests/test_termux_bootstrap.py`: **81 passed, 7 subtests passed**. One external anyio pytest deprecation warning.
- `node tests/test_mobile_dashboard_browser.js`: PASS; old `form.action` counterexample fails as intended.
- `bash -n scripts/termux_one_command.sh scripts/v13-update`: PASS.
- Ten real-bash bootstrap tests use only local Git fixtures and inert package/auth stubs. They cover STOP, active V13, wrong origin/branch, local edits/history, normal and shallow fast-forward, idle UI shutdown before fetch, and resuming a UI with a live child.
- The broader check initially exposed three stale mobile-dashboard tests omitted by the old CI. They now exercise the current managed-chat path and bounded error categories; the workflow runs both mobile-dashboard and bootstrap suites.

Other agents: the read-only bootstrap reviewer independently found the STOP
and orphaned-child defects, then owned only `test_termux_bootstrap.py`; the
coordinator integrated, ran the combined suite and actual Chromium smoke.

Next phone action: stop any running V13 via **V13 beenden**, then rerun the
one-command installer documented in `code/docs/ONE_COMMAND_TERMUX_20261111.md`
and use the newly opened browser tab. If the bridge was explicitly stopped,
the installer reports a separate local resume command instead of bypassing it.
`v13-update` targets `~/V13-Phone`; the dashboard has a separate update button.
B1/B2 native probe failures still require device evidence; no claim that this
bootstrap repair fixes model loading. Existing negative gates and overall
completion flags remain unchanged. No live relay request or private log was
published by this review.

# 2026-11-11 — tatsächliche World-JEPA-Trainingsfortsetzung

Der aktuelle Stager nutzt `integrated_world_training_resume_candidate_20261111.py` (SHA `82e2fd27712d17a489ce5fd2f75d749f3f0e08dcc9d7fcc8852bbe6f738e8e18`) auf derselben Kontext-/Archiv-/Feedback-/Body-/C3-/World-Kette. Bestätigte Ursache behoben: bisher wurden bei jedem Warm-start Adam-Momente, inverses Modell und Zufallsfolgen neu erzeugt. Die Testkopie erhält sie nun zusammen mit Encoder, Ensemble und EMA und persistiert alles in demselben quellgebundenen privaten NPZ. Tatsächlicher Runtime-Neustart und derselbe nächste Lernaufruf ergeben exakt denselben vollständigen numerischen Stand wie ohne Neustart. Keine eingefrorene produktive Datei editiert.

Neues Resume-Paket vorher **10 FAIL / 1 PASS**, danach **11 PASS**; sechs gezielte Staging-/Runtime-Dateien **13 äußere Tests PASS** einschließlich 15 Kontext- und 11 Resume-Fällen. Gemeinsame Stage inklusive vorhandener World-Kerntests **415 PASS / 3 CUDA SKIP / 58 Untertests PASS**. Neuer Remote-CI-Stand wird nach tatsächlichem Abschluss ergänzt. Details `INTEGRATED_WORLD_TRAINING_RESUME_20261111.md`; lokale erzeugte Kopie `/workspace/shared/v13-world-training-resume-review-20261111`.

Noch kein unabhängiger Nutzen-/Retention- oder Redmi-Beweis. Die Fortsetzung vergleicht dieselbe Folge von Lernaufrufen mit/ohne Neustart, keinen anders aufgeteilten Fit. Alte Inference-Revisionen werden nicht automatisch zu vollständigem Resume; Originaldateien bleiben erhalten. Nächste offene Kanten: feste Holdout-/Retention-Ziele, reguläre Body-JEPA-Auswahl/Consumer, Replay/Sleep/Idle und effiziente Gesamtkonsolidierung. Selbstoptimierungs-/Cross-Organ-Anforderung bleibt verbindlich offen. Freeze, negative Gates und beide false-Gesamtflags bleiben; alte rote Vollsuiten nicht umetikettieren.

# 2026-11-11 — ausführbare Gesamt-Testkopie und normaler Kontextabruf

`scripts/stage_integrated_candidate.py` erzeugt jetzt die gemeinsame hashgebundene Reviewkopie einschließlich begrenztem ContextOS-Quellenabruf. Tatsächliche ältere, komprimierte Quellen aus demselben Chat erreichen nach ausdrücklichem `:ctxos active` + `:ctxos recall on` die normalen C3-Nachrichten und deren Quellenlineage; aktives Kontextfenster bleibt begrenzt. Kalte Textreferenzen verwenden ein vorhandenes vollständig verifiziertes Archiv weiter, statt den Klartextblob erneut anzulegen. `messages.text` bleibt zusätzlich in SQLite; kein fertiger unendlicher Kontext, Idle-Lernen oder unmittelbares Entlernen.

**374 PASS / 3 CUDA SKIP / 35 Untertests PASS** in einer gemeinsamen Stage, auf dem aktuellen Quellstand; zusätzlich **12 äußere gezielte Tests PASS**, darin **15 Kontextfälle PASS**, echte SQLite-Runtime-Smokes und JEPA-Holdout-/Restart-Readback. Python-3.11-CI auf Code-HEAD `7aa8f08ba4102dc1e98804b7592bf48c01aab4f6` grün: Push-Run `42973853469` auf genau diesem Checkout und PR-Run `42973858006` auf Merge-Checkout `03c1497` jeweils mit beiden Jobs SUCCESS. Builder `168d6003db2c871599e70922619cfc416882b137ce05704b5c7b4d35037f6c0f`, Reviewkopie `/workspace/shared/v13-integrated-context-review-20261111-v2`. Details und Limits: `INTEGRATED_CONTEXT_SOURCE_RECALL_20261111.md`.

Andere Chats geprüft: Stage #1738, QA #1740, Runtime #1742, Workflow #1744, QA-Reparatur #1745, JEPA #1737. Doppeltes `tests.mkdir()` und falsche QA-Root-Erwartung in eigener Kopie repariert. Exakte Original-Vollsuiten bleiben **#1742: 109 FAIL / 5485 PASS / 51 SKIP / 94 ERROR; #1737: 108 FAIL / 5483 PASS / 51 SKIP / 94 ERROR**, jeweils 3027 Untertests. Vollständige Rohlogs verlustfrei gebunden; `INTEGRATED_STAGE_CROSS_REVIEW_20261111.md`.

Der #1741-Nachtrag `../../USER_ADDENDUM_2026-11-11_SELF_OPTIMIZATION.md` und `CROSS_ORGAN_WEIGHT_EDIT_CONTRACT_20261111.md` sind übernommen: echte organübergreifende Parameteränderungen, Selbstoptimierung und später kontrolliertes strukturelles Self-Edit bleiben verbindlicher **offener** Langzeitumfang. Zuerst World-Modell/EMA **und Optimizer** konsistent fortsetzen und feste Holdout-/Retention-Nachweise, dann reguläre Body-Anbindung, Replay/Sleep/Idle. Bisher lädt World-JEPA beim Restart Gewichte/EMA, aber einen frischen Optimizer. SourceHandoff-Freeze und sämtliche negativen Gates/false-Gesamtflags bleiben. Drive-Sicherung weiterhin durch Quota-403 blockiert; nur bestätigten Git-Remote als gesichert bezeichnen.

# 2026-11-11 — Feedback, Fehlerpreview und Datensatzkatalog auf gemeinsamer Basis

#1644-Notizen und Katalog (47 Ansichten/35 Repositories; 18 PROBE, 29 HOLD), Paper-/Fehlerlernnotiz und #1640-Feedbackbausteine sind in die gemeinsame Kette übernommen und gegen ihren Git-HEAD bytegeprüft. `scripts/integrated_feedback_bootstrap_candidate_20261111.py` verbindet in der hashgebundenen Testkopie die geprüfte Rating-Fanout-/C5-SHADOW-Version mit dem späteren Source-Lifecycle. Ein tatsächlicher synthetischer Turn bindet explizite Korrektur und World-Quittung an dieselbe T8-Aktion; Fehlergradient nur Vorschau, keine Gewichtsänderung. **2 äußere Tests PASS; 358 PASS / 3 CUDA SKIP / 35 Untertests PASS**. `INTEGRATED_FEEDBACK_BOOTSTRAP_20261111.md`.

Nächste Kante: tatsächlichen, unterbrechbaren ContextOS-/Source-Retrieval-Pfad für komprimierte ältere Quellen entwickeln, ohne ein verschachteltes SQLite-`BEGIN` oder unbeschränkte Ausgabe; `messages.text`-Duplikate und Speicherquoten separat bewerten. Anschließend Idle-Importer/-Scheduler und Body-Operator anhand der Nutzerentscheidungen fertig integrieren. Kein automatischer Download, keine Bildschirmfreigabe und keine nachgewiesene Learning-Utility.

# 2026-11-11 — Quellen-/Archiv-Lifecycle auf gemeinsamer Basis

`scripts/integrated_memory_world_candidate_20261111.py` verbindet die bytegeprüfte #1653-Quellen-/Archiv-Kopie mit C3, Body-JEPA und World. **2 äußere Tests PASS; 252 PASS / 3 CUDA SKIP / 16 Untertests PASS** in derselben Testkopie. Neuer echter SQLite-Turn: lernen → Quelle komprimieren → Unicode-Span prüfen → Neustart → Quelle widerrufen/bereinigen → World-Nutzung und Quellenlesen verweigert. Details `INTEGRATED_MEMORY_WORLD_LIFECYCLE_20261111.md`.

Das ist noch kein quasi unbegrenzter, effizienter Kontext: reguläres `native_history` bleibt auf `history_turns` und das aktive Modellbudget begrenzt, `messages.text` liegt zusätzlich in SQLite, und der bounded Streaming-Leser ist noch kein normaler ContextOS-/Chat-Abruf. Nächste Naht: die Nutzer-/Blueprint-Entscheidungen und den #1644-Datensatzkatalog in diese gemeinsame Kette holen; dann explizit begrenzten Source-Retrieval-/Context-Pfad, Cold-Scan-Abbruch/Quoten und tatsächliche Idle-Steuerung prüfen. Keine automatische Netz-/Trainings- oder Bildschirmaktivierung behaupten.

# 2026-11-11 — C3-LoRA-Restart in gemeinsamer Testkopie

`scripts/integrated_c3_resume_candidate_20261110.py` ergänzt zur Body-/World-Testkopie einen quellgebundenen C3-Resume-Preflight, validierte AdamW-Parameter/Slots und atomare Rückrolle bei Ladefehlern. Neben dem Shuffle- wird der CPU-Torch-RNG gespeichert: Der erste Tiny-Restarttest war **11 PASS / 1 FAIL**, danach stimmt der unterbrochene Zwei-Schritte-Torch-/PEFT-Lauf einschließlich Gewichten und Loss mit dem ununterbrochenen überein. **2 äußere Tests, 162 PASS / 3 CUDA SKIP** in der gemeinsamen Kopie; echter SQLite-AG6-Stage-/Train-Pfad ruft den synthetischen C3-Trainer auf, ohne Aktivierung. `INTEGRATED_C3_RESUME_CANDIDATE_20261111.md`.

Keine Vollbindung aller Tokenizer-/Config-Dateien oder lebender Source-Rechte, keine während jedes Schrittes geprüfte Numerik, keine Crash-/Dateiquota-Garantie, kein B1/B2-/C3-Native-/Redmi-Nutzen. Neue Quellbindung lehnt alte ungebundene Checkpoints ab; sie löscht diese nicht. Nächster Schritt: Archive-/Text-/Bild-Quellen-Lifecycle #1651/#1653 mit demselben gekoppelten System vereinigen und den langen Kontext/komprimierte Abrufe unter den dokumentierten Grenzen prüfen; danach Body-Operator, C3-Step-Integrität und Idle-Datenpfad weiterführen.

# 2026-11-10 — Body-JEPA und World auf gemeinsamer Testbasis

Die unterbrochene Arbeit aus `/workspace/v13-body-anchor-guard-reconcile` wurde nicht überschrieben; ihre 14 Asset-Dateien sind gegen angegebene Git-Commits bytegeprüft und über `scripts/integrated_body_world_candidate_20261110.py` mit der World-/JEPA-Testkopie verbunden. **2 äußere Tests PASS; 139 Tests PASS / 3 CUDA SKIP** in derselben Kopie, einschließlich echtem Tiny-Torch-/PEFT-Update, EMA-Fehlerrückrolle und Checkpoint-Fit-Neustart. #1663-Ankertest wird ausdrücklich auf die neue Listenfunktion angepasst; alte skalare API bleibt. Details `INTEGRATED_BODY_WORLD_RECONCILIATION_20261110.md`.

Wichtige Grenze: `agi/trainers.py` wählt aktuell `LoraTrainer`, nicht `BodyJepaTrainer`; die Body-Testläufe sind daher keine belegte reguläre Runtime-Anbindung oder B1/B2-/Redmi-/Native-/Nutzenaussage. Nächste Naht: autorisierter quellengebundener Organ-Trainingspfad und getrennte gepaarte Holdouts (#1695 rot, Workflow-Kind #1698 grün; nicht vermischen), dann C3-Resume und Memory-/Idle-Reconciliation.

# 2026-11-10 — Predictor-Historie vor Update und Vorhersage prüfen

Die weitere hashgebundene Komposition `scripts/integrated_predictor_history_guard_20261110.py` prüft sämtliche bereits gelernten Quellquittungen in SQL-Chunks vor `OnlineWorld.update` und `predict`, einschließlich eines alten Widerrufs außerhalb des aktuellen Fensters und nach Neustart. SQLite-Write-Fence gegen parallelen kooperierenden Widerruf für Vorhersage und tatsächliches NumPy-Update geprüft. **3 äußere Tests PASS; 1 altes Gegenbeispiel und 53 Tests auf der neuen Kopie PASS**; alte Mock-Daten nutzen nur in deren Tests eine ausgewiesene Schnittstelle. Details/Einschränkungen `INTEGRATED_PREDICTOR_HISTORY_GUARD_20261110.md`. Die synchrone Vollprüfung kostet mit wachsender Historie Zeit und hält eine Schreibsperre; keine Handy- oder Entlern-Aussage. Freeze und Gesamtsuite-RED unverändert.

Nächste konkrete Arbeit: unvollendete B1/B2-Body-JEPA-Reconciliation unter `/workspace/v13-body-anchor-guard-reconcile` prüfen, mit der gemeinsamen Kopie verbinden und echte Tiny-Fits + Gegenbeispiele testen; danach C3-Resume und Context-/Idle-Pfade. Quellmaterial der anderen Threads nicht überschreiben.

# 2026-11-10 — Predictor-Stream an Quellpfad gebunden

In der #1716-Komposition wurde reproduziert, dass `learn_stream()` bei einem bereits quellgebundenen Predictor vor dem abgelehnten Checkpoint Gewichte/Zähler mutiert. `scripts/integrated_predictor_stream_guard_20261110.py` verhindert dies in einer weiteren hashgebundenen Testkopie schon vor Iteratorzugriff und erhält den normalen `OnlineWorld.update`-Pfad. **3 äußere Tests PASS**, darin 1 bestätigtes Gegenbeispiel auf der Vorgängerkopie und **50 Tests PASS** auf der neuen Kopie einschließlich JEPA/Restart. Kein Schutz gegen beliebige private Objektmutation, keine vollständige historische Widerrufsbehandlung; Details `INTEGRATED_PREDICTOR_STREAM_GUARD_20261110.md`. Fortsetzen: Predictor-Quellhistorie/Revocation und Body-/C3-/Memory-/Idle-Nähte.

Neu gesichteter Parallel-HEAD #1717 `b3ac133148411330c5b1d5d1cb7c43547c469e78`: Spezial-CI `finite-loss` rot, weil dessen Fixture vor dem erwarteten Loss-Fehler bereits den Gradienten-Fehler auslöst. Das vorhandene gestufte Staging lehnt dieses Fixture unverändert ab. Anderen HEAD nicht als vollständig geprüft oder grün ausgeben.

# 2026-11-10 — World-JEPA-Lineage und Neustart im gemeinsamen Testpfad

Aufbauend auf #1716 materialisiert `scripts/integrated_jepa_guard_candidate_20261110.py` einen zusätzlichen quellgebundenen JEPA-Pfad mit Modus-/Pause-/Age-/Idle-Prüfung, tatsächlichen kleinen NumPy-Updates, vollständiger begrenzter Historie der im Modell verwendeten T8-Zeilen und privaten, nachvollziehbar gebundenen Save-/Restore-Generationen. **3 äußere Tests und 47 Tests in der isolierten Kopie PASS**, darunter Neustart, Änderungen und Widerruf alter Quellen, Manipulation und Fehler beim Veröffentlichen. Optimizer wird nicht gespeichert; vorherige Generation wird nur in den Speicher geladen. Freeze, Original-Runtime und Gates bleiben. Details und Grenzen `INTEGRATED_JEPA_LINEAGE_CANDIDATE_20261110.md`.

Nächster konkreter Schritt: `learn_stream()` im komponierten Predictor gegen unbeabsichtigte Teilmutation vor fehlgeschlagenem Checkpoint testen und reparieren; dazu die neuere andere Prädiktor-Kette #1711/#1715 und ihr abweichendes Format respektieren. Altwiderruf beim Predictor, echte Body-JEPA-/C3-Reconciliation und Memory-/Idle-Pfade bleiben offen. Siehe Roadmap und Ledger; keine abgeschlossene Architektur behaupten.

# 2026-11-10 — neue Integrationsanweisung und World-Predictor-Komposition

Nutzer verlangt Fortsetzung unter den neueren Anweisungen. Root-AGENTS und `coordination/V13_FAST_INTEGRATION_AGENT_PLAYBOOK_20261110.md` aus #1655 wurden gelesen: vorhandene Pfade auf gemeinsamer Basis integrieren, SourceHandoff-Freeze beachten. Auf #1663 HEAD `95aea15a046e73acf82c67ccf934cebda651ef87` materialisiert `integrated_online_world_candidate_20261110.py` #1631-Quellen-/Modus-/Quittungsschutz sowie #1648-Gradienten-Staging in einer Runtime-Testkopie; **50 Tests PASS**, einschließlich echter SQLite-Turns, Update und Neustart. Direktaufruf kann RECORD_ONLY nicht über Callback umgehen. Ein Test dokumentiert ausdrücklich die noch fehlende Widerrufsprüfung älterer Aktionen außerhalb des Fensters. Original-Runtime unverändert.

Wichtig: Der getrennte World-JEPA-Operator auf #1663 lernt nachweislich in RECORD_ONLY und Trainingspause sowie aus einem widerrufenen T8-Trainings-Ref; alter Private-Restore akzeptiert widerrufene Lineage. Checkpoint-Previous kann bei Schreibfehler die frühere Generation verlieren, Cleanup ein fremdes passend benanntes File löschen. `INTEGRATED_ONLINE_WORLD_GUARD_20261110.md` und die vier `review_*20261110.py`-Skripte erhalten die Gegenbelege. #1661-Vollsuite **73 FAIL / 5.394 PASS / 50 SKIP / 94 ERROR / 3.012 Untertests**, nicht auf #1663 übertragen. Nächste Arbeit: JEPA-Operator-/Source-/Restart-Lineage im tatsächlichen Pfad integrieren; Body-JEPA- und C3-Resume-Reviews weiterführen. Keine Gate-Beförderung.

Exakte #1663-Vollsuite in `git archive`-Kopie: **75 FAIL / 5.395 PASS / 50 SKIP / 94 ERROR / 3.012 Untertests**; ursprüngliches Rohlog verlustfrei `proofs/integrated-world-review-20261110/1663-exact-full-suite.log.gz`, entpackter SHA-256 `f8fc6afa952fa662c8d1063e866ce105dd0fb9e22b77b2d298bba009e0b8aba6`. Nicht als PASS oder als Ergebnis des geänderten Testkopie-Kandidaten ausgeben.

Die vorherigen Nutzerziele für langen geschichteten Kontext, begrenztes Idle-Lernen und erlaubte spätere Wahrnehmung sind nach `v13/NUTZER_ENTSCHEIDUNGEN.md` auf diesen gemeinsamen Integrationsstand übertragen. Speicher-/Archivkandidaten #1644/#1651/#1653 und Replay-Vorschau #1714 bleiben zu reconciliierende parallele Arbeiten, nicht gelöscht oder bereits als aktiviert behauptet.

---

# 2026-11-01 — Run117CF→CK source-safe Sleep, C3 no-native negative controls, Linux F7 (review-only)

**Newest verified local integration chain for this handoff:** Run117CK PR [#1563](https://github.com/RedMentos/Aii/pull/1563), branch `assistant/v13-run117ck-sleep-f7-post-fairness-20261101-hourly11`, head `0fe11ac7b94e07566342c18e7956f8f83a7b5ba2`. Its review-only ancestors: CF [#1559](https://github.com/RedMentos/Aii/pull/1559) (eight blocked DRAFT sessions no longer starve ninth ready; real RED→51/51 GREEN), CG [#1560](https://github.com/RedMentos/Aii/pull/1560) (`:sleep digest` shows pending workload before first cycle; real RED→54/54 GREEN), CH [#1561](https://github.com/RedMentos/Aii/pull/1561) (synthetic-only Run83 C3 driver no-cache test repaired without native/model/runner change; real RED→6/6 GREEN), CJ [#1562](https://github.com/RedMentos/Aii/pull/1562) (real Runtime without weights remains `STRUCTURAL_RED/Unavailable`, zero native calls; 8/8 GREEN), CK [#1563](https://github.com/RedMentos/Aii/pull/1563) (byte-identical preregistered F7 benchmark rerun, 7/7 GREEN, Linux-only). All remain draft/review branches, **not production-integrated**.

Original raw for CF/CG/CH/CJ RED+GREEN, original CC full-suite RED, CE Linux benchmark and CK Linux benchmark independently CRC/SHA-verified and byte-identically re-materialized from private Library `/V13-Checkpoints/2026-11-01/Run117-Hourly11/`. Exact ZIP SHA256 and source blobs in `BUILD_STATE_RUN117CF_SLEEP_BLOCKED_FAIRNESS_20261101.md`, `BUILD_STATE_RUN117CG_SLEEP_PREDIGEST_OPERATOR_20261101.md`, `BUILD_STATE_RUN117CH_C3_FAKE_DRIVER_20261101.md`, `BUILD_STATE_RUN117CJ_C3_NATIVE_ABSENCE_20261101.md`, `BUILD_STATE_RUN117CK_SLEEP_F7_POST_FAIRNESS_20261101.md`. No Drive retry.

**Parallel independent full-suite branch, not an ancestor:** `assistant/v13-run117ci-currentchain-fullsuite-retest-20261101-hourly11`, pinned source head `44840c9991bd72aadc9d659934e9d54f39b5b44e`, [Actions 41257747643](https://github.com/RedMentos/Aii/actions/runs/41257747643) **terminal RED**, 5,331 tests, 4 failures, 75 errors, 28 skips; original ZIP artifact `13064530049` SHA256 `10610fb68aa6b801dab1d571153bc4a287ee120a835996f21dea92f1c2ae57f3`, independently CRC/25 inner hashes checked and private Library byte-identical backup. Original Run117CC was RED (5,326 tests, 5 failures, 75 errors, 28 skips). The repaired synthetic C3 test removed one failure, but frozen-source guards and missing historical native artifacts remain. See sibling [PR #1565](https://github.com/RedMentos/Aii/pull/1565) and `BUILD_STATE_RUN117CI_FULLSUITE_RED_20261101.md` for exact failures and next commands; do not waive them. Reconcile sibling only after independent review, without force-push.

**Canonical scope still entire** `V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` (blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`): JEF/C2, C3, B1/B2, JEPA, Context OS, Callosum, Dream/Sleep, age and all original gates. Age0 RECORD_ONLY, STEP2 UTILITY_FAIL, B3 NO_PROMOTION, Body-JEPA UNAVAILABLE, World-JEPA SHADOW, `jepa_weight=0`; no native/Redmi/learning/whole-system promotion. Next useful work after raw audit: source-registered independent C3/JEF utility beyond typed copying, Body-JEPA attribution and Redmi-specific resource/native proof; do not mistake software/synthetic/Linux observations for phone evidence. Remaining platform budget UNKNOWN.

---

# 2026-10-30 — C2 native route provenance preflight GREEN, native deferred

Review-only PR #1205, branch `assistant/v13-c2-native-route-provenance-20261030-0425`, child of v3 PR #1204. Preregistered 3 fixed source prompts seed43, `route_override=auto`, stored ExecutiveControlContext + Needle/C2 operation C metrics; no C3/Body inference or live answer. Software Actions `40997339478` GREEN **7/7** tests, 7/7 stages, privacy CLEAN, raw SHA256 `d0e78551a3186b234363fb4b15ae2701818ebc2119fd7928fc2dde3ee9a08479`, private byte-identical backup. The real Store route test uses an explicit **synthetic Needle stub**, so `native_c2_proven=false`. Native v3 Actions `40996792157` still owns heavy execution; only after terminal launch the pinned C2-only native workflow in same concurrency group. Source/seed/model pins and all negative gates remain. See `docs/C2_NATIVE_ROUTE_PROVENANCE_PREFLIGHT_GREEN_20261030.md` and scoped BUILD_STATE.

# 2026-10-30 — STEP2 v3 nine-task counterbalanced native pilot launched (unverified)

Review-only child PR #1204, branch `assistant/v13-step2-v3-counterbalanced-20261030-0419`, parent PR #1202. New seed41 nine fixed disjoint source tasks, fixture SHA256 `fe9b86fdf561778ad540dd4767111f04c10a147a8a44cf783fa16f0d2c8a45ca`, 27 fresh native turns with balanced A/B/C arm order. Source prereg commit dc2fcc9 before implementation. Software preflight Actions 40996622134 GREEN 12/12 tests, 7/7 stages, privacy CLEAN, raw SHA256 `1ff7d0b3e59bb4cd9e971aacae5b071c15d20151765d5a5aa77dfc45cd746d70`, private byte-identical backup. Native Actions `40996792157`, exact source HEAD `5e802d235c9501879a3aff07e5134c1455e1769b`, currently unverified. Next: download original native raw ZIP at terminal, verify SHA/CRC/manifest/27 raw/36 body releases, score and backup; do not infer result from job status. Source/seed/model pins, negative gates, historical full-suite RED unchanged. See `docs/STEP2_PAIRED_NATIVE_V3_LAUNCH_CHECKPOINT_20261030.md` and scoped BUILD_STATE.

# 2026-10-30 — STEP2 fresh disjoint native paired v2 launched (result pending)

Review-only child of PR #1198 on `codex/v13-step2-paired-native-v2-20261030-hourly11`. New preregistered unseen Solace/Tundra/Harbor/Atlas fixtures, seed29, SHA256 `b8dba3465d80aa90142065550a6d1b6770b562fd852e25f598ec8260d2bf6cf4`, contradiction-vetoing scorer and corrected route-override evidence; original native pilot RED `40989187037` untouched. Software preflight Actions `40992003721` **12/12 PASS**, 7/7 stages, raw private byte-verified. New heavy native 4×3 run `40992102064` launched under original native concurrency group; **no native result yet** at this checkpoint. Source/owner/next command in `STEP2_PAIRED_NATIVE_V2_LAUNCH_CHECKPOINT_20261030.md` and BUILD_STATE `run11_20261030_step2_paired_native_v2`. Must inspect terminal raw before any native claim. No Needle/C2 native proof or STEP2 promotion, all Age0/B3/JEPA gates unchanged.

# 2026-10-30 — STEP2 original paired native pilot independent raw audit (review-only)

Owner's original pilot `40989187037` remains `PILOT_PARTIAL_RED` (0/8 all three arms after fail-closed validator). Separate audit on `codex/v13-step2-pilot-raw-validator-audit-20261030-hourly11` verified original ZIP SHA256 `fcc66cf5d0d2c59bfe3bbd7a8b5b3c140169ee5a05020d9e4df12e566c30d9ce`, 38/38 inner hashes, 156/156 structural checks, 12/12 native-generated raw turns and 16/16 two-body process-reaped receipts. Found 12/12 validator schema mismatches: `route.native_control` expected dict but `route` only holds `source=OPERATOR_ROUTE_OVERRIDE`; C2 native control not proven. Posthoc contradictory-aware remainder diagnostic: A 0/8, B 3/8, C 5/8, NOT a preregistered STEP2 utility gate. Audit CI `40991083424` 6/6 PASS; raw, code and result byte-backed in private Library. Details `STEP2_PAIRED_PILOT_RAW_VALIDATOR_AUDIT_VERIFIED_RESULT_20261030.md`, BUILD_STATE key `run11_20261030_step2_paired_native_readonly_audit`. Original RED, Age0/STEP2/B3/JEPA negative gates intact. Next: owner to preregister a fresh native paired pilot with schema-correct C2 proof and contradiction-aware scoring; no overwrite of original branch.

# Aktuell 2026-10-22 (Thread „GPT-Stand erneut prüfen“): Gegenprüfung Runde 2 + `:stillstand`

GPT/Codex-Stand vom 22.10. (PR #29 `c1d6615`, PR #27 `16a0b17`, Drive-Notiz) geprüft und gemergt, Aussagen nachgerechnet und bestätigt; Runde 1 (PR #8) nachgeholt. Neu WP-SAFE2 `:stillstand`: hält Werkzeuge, Aufgaben/Lernen/Hintergrund und Alterung zusammen an, bestätigt erst nach Ende des laufenden Vorgangs, bleibt über Neustart, hebt nur eigene Teile auf. WP-AGE0a gebaut: späte Selbstkorrektur über Age-0-Recht `late_correction`, `:self correction off|shadow|deliver`, Standard shadow (Live unverändert), Messung offen. WP-AGE0b gebaut: `:organ snapshot|check|restore` sichert/stellt ein einzelnes Modell-Organ (Köpfe, Adapter, Brücken) zurück, ohne andere Organe anzufassen. Neue Pakete WP-AGE0b (Organ-Checkpoint), WP-LP1 gemessen: latenter Term erreicht die Parameter, kein Nutzen, doppelte Drift, falsches Ziel hebt den Kosinus fast gleich → `LP1_NO_ATTRIBUTABLE_GAIN`. Details `docs/coordination/CLAUDE_ANTWORT_AGE0_LERNPFAD_20261022.md`, Branch `claude/project-thread-2p69gl`. ROADMAP/Handoff/Zielabgleich hier mit dem Projektordner zusammengeführt (beide Seiten hatten Abschnitte, die der anderen fehlten).

WP-LP2 (22.10., Branch `claude/project-thread-h8vj3v`): latentes C3-Ziel mit Predictor + EMA-Ziel + InfoNCE lernt die richtige Zuordnung (.41 → .99, falsche Kontrolle sicher beim falschen Fakt), bringt aber keinen Nutzen auf 32 neuen Umformulierungen (110 = CE 110, falsch 108 von 128) → `LP2_ALIGNS_NO_GAIN`, `jepa_weight` bleibt 0. Nächstes: WP-LP3, Antwort muss vom vorhergesagten Zustand abhängen. Befund `docs/proofs/continuation-20261022/lp2-assignment-objective/BEFUND.md`.

# Aktuell 2026-10-22 (Codex, isoliertes Review-Paket): Lernpfad-Auditor und Promptgrenze

Basis `9436eb7` (Claudes zusammengeführte Nutzerregeln + SAFE1), eigener Branch `codex/learning-path-audit-20261022`. Zwei neue, standardmäßig nicht integrierte Skripte: read-only `learning_path_claim_audit.py` und quellgebundener `lora_prompt_boundary_candidate.py`. Audit der 14 archivierten AG6-Manifeste: alle JEPA-Gewicht 0, alle Kosinusgewinn; kein Nachweis eines Beitrags des JEPA-Terms. Tatsächlichen `_encode`-Fehler bei vollständig abgeschnittenem Prompt reproduziert; Kandidat lehnt solche Paare ab und trennt Checkpointordner per Revision/Quellhash. 34 fokussierte Tests bestanden; Software-/Artefaktprüfung, kein neuer Native-/Redmi-Lauf. Runtime, aktive Kohorten und Gates unverändert. Details/Belege: `LEARNING_PATH_AUDIT_20261022.md`, `proofs/continuation-20261022/learning-path-audit/`. Nächster Schritt: registrierter Komponenten-Gradienten-/Nutzenvergleich am vorgesehenen Body-Pfad, innerhalb der vollständigen verbundenen Architektur. Übergabe ist kein Nachweis, dass Claude sie bereits gelesen hat.

# Aktuell 2026-10-21 (Thread „Zitierhilfe an, Regeln per JEF“): Zitierhilfe an + Nutzer-Regeln mit festem Leser

Nutzerentscheidung: Zitierhilfe an (Standard jetzt `b2_quote_select='pointer'`, `offer_quote_context_chars=200`, `b1_recent_source_chars=600`, alte Werte für eingefrorene Harnesses in `config.LEGACY_QUOTE_PATH`); `analyst_context`-Fix aus PR #7 übernommen; Körper-Frage an, aber nur bei Regel-Entscheidungsfragen (`body_question_scope='rule_decision'`); Regelwerte liest kein Modell mehr (`eligibility_reader='fixed'`, `eligibility.fixed_read`). Neu `v13/userrules.py`: fester Leser (kein Modell) für Verbote / „frag mich vorher“ aus den eigenen Zeilen des Nutzers, durchgesetzt in IH-H29 `_policy`, feste Hinweise im Broker, Befehle `:regeln` / `:regel`. Gemessen: Autor-Holdout 0 Sicherheitsfehler; frische Modell-Umformulierungen Runde 2: v2 20 Fehler in 8/57 Sätzen (v1: 71) → `USER_RULES_UNSAFE`. Schreibende Werkzeuge bleiben ohnehin Vorschläge. Befund `docs/proofs/continuation-20261021/user-rules/BEFUND.md`, Branch `claude/project-thread-2gzrwi` (enthält PR #7, #19, #21). PR #2, #3, #4 geschlossen.

# Aktuell 2026-10-21 (Thread „B2 zitiert Regel selten“): WP-Z2d B2 liefert das Regel-Zitat — Zeiger behebt den Engpass

Ursache: B2 schreibt die alte Regel um statt sie wörtlich zu zitieren (110/384 Z2b-Angebote), die Zitatprüfung verwirft das. Neuer Schalter `b2_quote_select` (`off` Standard | `anchor` | `pointer`, Kettenglied `integrated_candidates.b2_quote_select`). Vorregistrierter Lauf CQ/CQA/CQP × Seeds 17–19 (630 Zeilen): B2-Regelquote .167 → Anker .542 (teilweise) → **Zeiger .969** (`Z2C_B2_RULE_QUOTE_FIXED`, CI > 0, 0 falsch). STEP2 zwei Körper `both_exact` .881 vs. b1_only .581 (+.30, CI > 0, alle Seeds), 27/30 exakte Entscheidungen. STEP2 bleibt formal FAIL (Kriterium 3, Ein-Körper-Kontrolle offen). Schalter aus bis Nutzerentscheidung; live-`analyst_context` nimmt erweiterte Zitate noch nicht an. Befund `docs/proofs/continuation-20261021/step2-z2c-b2-rule/BEFUND.md`, Branch `claude/project-thread-0fckhc`. Merge-Hinweis: Thread „B1-Frage als Schalter“ (Branch `4ttld7`, auch „WP-Z2c“ genannt) hängt ein eigenes Kettenglied `body_question` an `cognition.py`; beim Zusammenführen beide Glieder in `integrated_candidates.rebase` hintereinander anwenden.

# Aktuell 2026-10-21 (Thread „B1-Frage als Schalter“): gezielte Körper-Frage als Live-Schalter — Standard aus

Neue Schalter `body_question_b1` / `body_question_b2` (Standard `''` = aus = live unverändert): feste Frage als `jef_query` an jedes Körper-Angebot ohne Rückfrage-Fokus. Bestätigungslauf Seed 14 mit echten Modellen: Schalter (beide) both_exact .592 vs ohne .375 (Z2b-Patch .675), nur B1 .450; b1_only .275 → .575; 0 falsch festgelegt. Frage ist STEP2-spezifisch, deshalb bleibt sie aus. Befund `docs/proofs/continuation-20261021/step2-z2c-switch/BEFUND.md`, Branch `claude/project-thread-4ttld7`.

# Aktuell 2026-10-21 (Thread „Z2b STEP2 mit mehreren Seeds“): Rauschband + gezielte Fragen — Gate FAIL, Frage hilft

Vorregistrierter Lauf (C/D/CQ/DQ × Seeds 14–16, 840 Zeilen, echte Modelle, Linux-Cloud): `Z2B_DIVERGENCE_NOT_SUPPORTED`. Z2-Abstände lagen im Rauschband. Eine feste gezielte Frage an die Körper hebt den Werkzeug-Nutzen um +.23 (CI > 0), vor allem weil B1 dann die Optionswerte zitiert; B2 zitiert die alte Regel weiter selten (Engpass). 0 falsch festgelegt. Befund `docs/proofs/continuation-20261021/step2-z2b-seeds/BEFUND.md`, Branch `claude/project-thread-s439sv`.

# Aktuell 2026-10-21 (Thread „Z2 STEP2 mit B1-Detailinfo“): STEP2 mit B1-eigener Information — Gate FAIL

Neuer Schalter `b1_recent_source_chars` (Standard 0 = aus): B1 behält die exakte Quelle seiner letzten Runde. Vorregistrierter Lauf (10 Episoden, 5 Arme × 70 Zeilen, echte Modelle, Linux-Cloud): `Z2_DIVERGENCE_NOT_SUPPORTED` — Zwei-Körper .325 < b1_only .333, ein Körper + zwei Zustände nicht schlechter. B1 liefert jetzt Optionswerte (27/70 statt 0), exakte SPLIT-Entscheidungen nur im Ein-Körper-Arm (3/6). 0 falsch festgelegt. Befund `docs/proofs/continuation-20261021/step2-z2-timescale/BEFUND.md`, Code nur im Git-Branch `claude/project-thread-hsm0ga` (Schalter in `v13/cognition.py`, hier im Projektordner noch nicht). STEP2 UTILITY_FAIL bleibt.
# Aktuell 2026-10-22 (Thread „STEP2-Nutzen Engpass“): Werkzeug-Entscheidung vorn
Eignungs-Werkzeug: Regeln liest ein fester Leser, die Entscheidung ist der erste Satz der Antwort (bei unbekannt/keine die ganze Antwort). Vorregistriert gemessen, 60 frische Aufgaben: Antwort richtig 59/60, 0 falsch (vorher 23/60). Standard an, Werkzeug selbst nur nach Freigabe. Befund `docs/proofs/continuation-20261022/eligibility-first/BEFUND.md`.

# Aktuell 2026-10-21 (Thread „STEP2-Nutzen Engpass“): Eignungs-Werkzeug im Live-Pfad

`ToolStep._propose_eligibility`: Option-A/B-Fragen unter Projektregeln → C3 liest typisierte Werte aus Quelle + Body-Zitaten → Rezept entscheidet. Nur nach `:growth enable eligibility`, Age 0 SHADOW. Vorregistriert gemessen: 55/70 exakt, 0 falsch (LIVE_PROMPT_SUPPORTED). Handy-Testliste `../HANDY_TESTLISTE.md`. Befund `docs/proofs/continuation-20261021/eligibility-live/BEFUND.md`.

Zusammengeführt in `claude/project-thread-dq33gk` (PR #7): Qs Fassung gilt (TOOL_LIVE_SUPPORTED), dazu Zitat-als-Zeiger-Schalter + `analyst_context`-Fix (Chat brach mit Schalter an ab). Ganzer Turn der dq33gk-Variante war NOT_SUPPORTED, entfällt.

# Aktuell 2026-10-21 (Thread „Nächste Pakete Q“): Eignungs-Werkzeug im ganzen Live-Turn

`eligibility` läuft im normalen Turn (nur nach Freigabe, Alter 0 = SHADOW). Vorregistrierte Messung, 60 frische Aufgaben auf C3: Antworttext richtig 22 → 32 (p .006), falsch festgelegt 33 → 23, Rezept nie falsch, mit Broker-Korrektur sichtbar richtig 53/60. Befund `docs/proofs/continuation-20261021/eligibility-whole-turn-q/BEFUND.md`, Branch `claude/project-thread-hzzqh4`. Parallele Fassung im Thread „STEP2-Nutzen Engpass“ (dq33gk) beim Zusammenführen abgleichen.

Zusammengeführt in `claude/project-thread-dq33gk` (PR #7): Qs Fassung gilt, dazu Zitat-als-Zeiger-Schalter + `analyst_context`-Fix (Chat brach mit Schalter an ab). Ganzer Turn der dq33gk-Variante war NOT_SUPPORTED, daher entfallen.

# Aktuell 2026-10-21 (Thread „B3 L1 escalate apologize“): L1 PASS auf escalate, apologize knapp FAIL

Ursache der escalate/apologize-FAILs gefunden: eingefrorener NO_MESSAGE-Kopf kann die Empfänger-private Tatsache (Kapazität/Kunde) nicht zur Nachricht passend gewichten (kostet selbst mit echtem U/F 8–9 Punkte). Fix `Bridge(recv_cond)` + `refit_readout` (Standard aus). Vorregistrierter Versuch 5 auf frischer Saat 20261105: **escalate Kanon-L1 PASS** (90,5 vs Attribut-Wörter 84,7), apologize FAIL (89,0 vs 88,5, n.s.), action-PASS aus Versuch 4 **nicht repliziert** (86,7 vs Label 83,5, n.s.). L2-SHADOW nur für private/escalate erlaubt. Belege `bench-results/b3-l1-escapo-diagnose-20261021/`, `bench-results/b3-l1-v5-20261021/`, Branch `claude/project-thread-yub2lf` (auf c122qc / PR #20).

# Aktuell 2026-10-21 (Thread „Nächste Pakete R“): B3 L1 Versuch 4 PASS auf action + Schlüsseltrennung der schnellen Spur

- **WP-Z4 B3 L1 Versuch 4** (vorregistriert `eaf49b7`, frische Saat 20261021, neue B1/B2-Zustände, `aux`-Brücke): **Kanon-L1 PASS auf `private/action`** (LATENT 90,0 % vs SYMBOLIC 81,5 / Attribut-Wörter 76,7 / SCALAR 85,2; Rollen-Verlust 0, OOD 1,3 %). escalate/apologize FAIL. Folge: nur L2-Prefix-SHADOW für `private/action` erlaubt (nächstes Paket Z4b), Autorität 0, Runtime unverändert. `bench-results/b3-l1-v4-20261021/`.
- **Native Firing-Diagnostik / WP-T9 v3**: zwei Ursachen falschen Feuerns gefunden und behoben (`sparse_memory` `guard_distinct`/`guard_vocab`/`guard_scope='last_user'`, Hook `v13_memory_hook.h`, Standard aus). Nativ: 0 fremde Feuerungen auf Faktfragen, combined 84 → 17 Zeilen; selektive Zustellung 2:5 gegen exakt (vorher 2:9) → weiter kein Gewinn, Verluste = falsche Spur-Werte auf Paraphrasen. `bench-results/selective-delivery-v3-20261021/`.
- Branch `claude/project-thread-8hlx74` (Basis `claude/project-thread-0zelvf`). Suite 1591, einziger Fehler `test_neuro_ledger` durch 19 nachgezogene Belegordner behoben.

# Aktuell 2026-10-21 (Thread „Z3b Parser statt C3-Leser“): Parser reicht, C3 bringt als Leser nichts Sicheres

Vorregistriert, 39 kanonische + 39 umformulierte Aufgaben × 3 Seeds, nur C3. Urteil `PARSER_SUFFICIENT_NO_C3_GAIN`, sekundär `BOOL_PARSER_FIX_CONFIRMED`: C3-Zahlen + Parser für `local_only` kanonisch 117/117 exakt, 0 falsch. C3 gibt `local_only` immer `true` zurück (auch bei verneinten Umformulierungen); auf Umformulierungen kein C3-Arm ≥ 0.80, einziger Gewinn (+26 Punkte) mit 7.7 % falscher Wahl. Regel: Ja/Nein-Regeln nie vom C3 lesen lassen. Beleg `docs/proofs/continuation-20261021/z3b-parser-paraphrase/BEFUND.md`. Keine Gate-Beförderung.

# Aktuell 2026-10-21 (Thread „Z1 STEP2-Gate ehrlich“): Gate-Graph ehrlich

STEP2 geteilt: `STEP2_HARNESS` GREEN, `STEP2_EXIT` (§96 Komplementarität) EVIDENCE_NOT_PASSING. STEP2_EXIT, STEP5 und alle zehn §100-Gates prüfen jetzt Blueprint-Kriterien an gemessenen Werten (`blueprint`-Block, Status CRITERIA_UNMEASURED); gemessenes FAIL nie mehr hinter PARTIAL. `measure_suite.py` gibt die §29-Tabelle berechnet aus: 3 erreicht, 15 teilweise, 6 fehlen. Befund `docs/proofs/continuation-20261021/z1-gate-ehrlich/BEFUND.md`. Branch `claude/project-thread-61we5j`.

# Aktuell 2026-10-20 (Abend): Handy-Paket Werkzeug-Vorhersage fertig

Ein Befehl am Redmi: `bash WERKZEUG_TESTEN.sh` (Stufen `paritaet|kurz|voll`, Anleitung `WERKZEUG_ANLEITUNG.txt`). Vorprüfung, Einrichtung bei Bedarf, GPTs begrenzter Treiber mit Frist, RAM-/Temperaturverlauf, Ergebnis-ZIP in Downloads. Nebenbei behoben: Handy-ZIP brach im Setup-Selbsttest ab (zwei fehlende Belegdateien in `package_source.py`). Cloud-Probelauf aus dem entpackten ZIP: `voll` bestätigt, gleiche Zahlen wie 12./13.10., Spitzen-RSS 1,2 GB. Redmi-Messung offen (Nutzer). Belege `docs/proofs/continuation-20261020/werkzeug-handy-cloud/`.

# Aktuell 2026-10-20 (Thread „STEP2-Nutzen Engpass“): B2→C3-Zitat als Zeiger

Neuer Schalter `offer_quote_context_chars` (Standard 0 = aus). Mit 200: frühere Regel erreicht C3 23/30 statt 7/30, mit Eignungs-Werkzeug 24/30 statt 11/30 exakt, 0 falsch. STEP2 bleibt UTILITY_FAIL (B1 ohne eigene Info; C3 rechnet ohne Werkzeug nicht). Einschalten = Nutzerentscheidung. Befund `docs/proofs/continuation-20261020/step2-quote-context/BEFUND.md`, ROADMAP-Abschnitt gleichen Namens.

# Aktuell 2026-10-20 (Abend): WP-G2 nativer Gist-Readout-Konsument

`v13/gist_readout.py` konsumiert den B2-Tap (Qwen3.5-0.8B) bytegenau gebunden und gruppiert ihn in Gist-Slots (`:gist readout`, SHADOW). Vorregistrierte native Messung, 2 Runden: gegen feste Gruppierung mit gleicher Gruppenzahl helfen Text-Grenzen (+.08 Recall@1, CI [.045,.114]), das native Zustands-Sprungsignal nicht (hybrid FAIL). Standard `text`. Details `docs/GIST_READOUT.md`. Keine Gate-Beförderung.

# Aktuell 2026-10-20 (Abend): privater STEP2-Pilot nativ gelaufen

18/18 Zeilen, 0 exakt, Aktion nie richtig — auch die exakte Quellen-Kontrolle scheitert, also liegt der Flaschenhals beim C3-Konsumenten (LFM2.5-350M), nicht beim Zitat-Transport. Kohorte `NOT_CONFIRMED` wegen 1 ERROR-Zeile (B2 zitierte öffentlichen Text unter privater Ref, korrekt abgelehnt). Lief unter einer zweiten, vor dem Lauf veröffentlichten Registrierung (Modelle/Runner/Quellen byte-identisch zur GPT-Registrierung, nur Gerät/Pfade neu). GPTs read-only Auditor vom 19.10. ist eingebaut (`step2-private-fixtures/audit_private_pilot.py`). Details: `docs/proofs/continuation-20261016/step2-private-fixtures/pilot-run-20261020/ERGEBNIS.md`. Keine Gate-Beförderung.

# Aktuell 2026-10-20: GPT-Stand bis 19.10. von Claude übernommen

GPT/Codex `codex/continuation-20261016` @ `a1973d4` (PR #4) ist mit allen Claude-Threads K–P im Projektordner zusammengeführt; Git-Branch `claude/project-thread-0zelvf`. Volle Suite 1571 Tests OK (6 Skips). Projektstand behielt in tools/broker/toolstep/transaction die W2c-Eligibility-Registrierung; GPTs Vorzeichen-Guard (listarith), Outcome-Tap-Fix (toolforecast) und Lernintegritäts-Skripte sind übernommen. Native ToolForecast-v2 610/610 Linux-SHADOW-Lerngates PASS im engen Scope. Nicht übernommen: GPTs Drive-Kandidat vom 19.10. (`V13_PRIVATE_PILOT_AUDIT_RUN7_DELTA_20261019.zip`, read-only Pilot-Auditor) — nächstes Paket. Offen: privater 18-Zeilen-STEP2-Pilot (registriert, nicht gelaufen), STEP2 UTILITY_FAIL, B3 L1 FAIL, Redmi, Canon. Nächste Pakete: ROADMAP.md Abschnitt „GPT/Codex-Stand 13.–19.10. übernommen“.

# Aktuell: Abendliche native Kohorte610/610 abgeschlossen und unabhängig reproduziert

NativeToolForecast-v2-Lerngates bestanden:4/4Rechen- und3/3Notizaktionen verbessert; eingehaltene feste Retentionsgrenzen.610 SCORED+EXECUTED,942.39s,Linux,SHADOW.30+20Retentionszustände waren wiederholte feste Kontrollen;70verschobene Zahlen/50freie Notizen neu. Kein Redmi-/Canon-/allgemeiner-Lern-PASS. Sourcecheckpoint50af1c9455693a0a2cf708a0c42bbbe7f860399a. Unabhängige Rechnung reproduziert gesamte Lernreports und Adaptions-NPZ/Arrays exakt. Belege recovery-evening/native-final/ und replay-verification/. Vollständiges Roharchiv Drive1-m_Oj_j9AkTxAiML-6eGh12dRQPPq0_v SHA0260f5396145f1eae0db5f6db71a4869c4803c5ef42e36e01e33cf7701c30371; tatsächlicher Remote-Download geprüft, sieben verifizierte Zwischenarchive.

Nach Abschluss enger Source-Zahlen-Guard-Fix im Listenrechner: falsches +5 aus -5/Unicode-Minus wird abgewehrt, Schema erlaubte negativeIntegerbereits; alte positiveK-Fälle bleiben.11fokussierte Tests bestanden, neue Gesamtsuite folgt. Neue private STEP2-Quelle ist als isolierter Runtime/Store-Adapter tatsächlich gebaut,28Softwaretests. Dreifall-Pilot(A/B/NONE)×6Arme18Zeilen/max42Aufrufe separat registriert, noch keine native Aussage daraus. Original70/70UTILITY_FAIL/B3L1FAIL bleiben.

## Historische Übergaben (erhalten)

# Abend-Fortsetzung 2026-10-16: Unterbrechung korrekt erfasst, Testpfad wird integriert

Nach späterer Nutzernachricht war Scratch leer; vorheriger nativer610-Call-Lauf hat **keinen dauerhaft bestätigten Abschlussbeleg**. Gesichert sind Runtime/Plan/Parität und50 Rohzeilen auf GitHub `3af7ea8fe8f124459041133a34ce457f179d1f99`; die letzte lokale Sichtung238/610 ist nur Toolausgabe. Keine Hochrechnung auf Erfolg oder Vollständigkeit. Alte Preregistrierung a2d152c0… ist verbraucht, kein Resume/Repeat desselben Registers. `proofs/continuation-20261016/recovery-evening/interrupted-native-attempt.json`.

GitHub K–P/M sind unverändert. Zusätzlich sichtbarer hiczvw ist alter11.Oktober-Import und Vorfahr unserer Integration; keine Übernahme. Agenten integrieren aktuell vollständige Lernprüfung/nonzero-Exit in die normalen Phone-Skripte, fsynced Einzelzeilen und bytegleiche Prelearn-Rohdaten. Separater echter Store/SourceRef-Adapter für neue private STEP2-Fixtures in Arbeit, keine native Nutzenaussage daraus.

Neue610-Aufruf-Prüfung wird separat registriert:70 neue verschobene Zahlen und50 neue freie Notizen;30+20 feste in-world Retentionszustände werden ausdrücklich wiederholt, da nur24 völlig unbenutzte in-world Zahlen übrig sind. Größen/Gates/Region-Lernregel unverändert. Nicht als komplett frische Retentionskohorte ausgeben. Neuer GGUF/Runner gepinnt wiederhergestellt; Inferenz noch nicht gestartet. Frühere vollständig grüne1421-Test-/ZIP-Belege gelten für3af7, neue Quelländerungen werden neu getestet und gesichert.

## Bisherige Übergaben (historisch erhalten)

# Fortsetzung 2026-10-16: K+M integriert, neue native v2-Prüfung vorbereitet

Arbeitsbranch `codex/continuation-20261016`, Basis M `1941d07afeb57299d7d5a466fd1eb44ec2569dfe`. K `4ed1539fb9fd6ea961fc6145bd98745e5f63adac` list_arith ist mit M calc/note/ToolForecast zusammengeführt; minimale H-Text- und G-Approval-Voraussetzungen sind übernommen. Default-Berechtigungen, Age-Hülle und SHADOW bleiben erhalten. Die Claude-Owner-Branches werden nicht überschrieben.

M hat die fünf früheren Codex-Befunde selbst korrigiert; diese Änderungen wurden als Basis übernommen. Neu reproduziert und eng behoben: Quellentausch während Outcome-Tap durfte sonst unter altem Encoder gebucht werden. Neue Integritätsprüfung verhindert einen Lern-PASS bei unvollständigen Zeilen/Aktionen. Belege unter `proofs/continuation-20261016/`. Vollständiger kombinierter Regressionstest läuft; native Qualität noch nicht behauptet.

**Neuere Zustände gelten:** SourceHandoff16/16 vollständig, Freeze laut ROADMAP am12.Oktober aufgehoben. Dream2v3 ist15/15 abgeschlossen mit Nutzen/Retention-Tradeoff, kein allgemeiner Nutzen-PASS. Alte Hinweise unten auf Freeze/2von15 sind historische Übergaben. Aktuelles Competence-v2 hat420/420 Messungen; der alte bestätigte Lernlauf nutzte v1. Deshalb neue disjunkte610-Call-v2-Prüfung mit festen unveränderten Gates und vor Inferenz veröffentlichter Preregistrierung. `native-v2-learning/preregistration.json` bindet Quellen, Modell, native Bibliotheken, Tap-Reader und neuen Plan.

Linux-8GiB-Ressourcen sind jetzt wieder gepinnt installiert; das ist kein Redmi-Nachweis. STEP2 UTILITY_FAIL, B3L1 FAIL sowie Canon/Fullscope-offen bleiben erhalten. Nächste Schritte: vollständige Regression abschließen, Preregistrierung auf GitHub verifizieren, native Parity+Lernkohorte seriell ausführen, Rohbelege regelmäßig sichern und Paket aus dem finalen Stand prüfen.

## Historische Übergaben (unverändert erhalten)

# Fortsetzung 2026-10-12: Arbeitsregeln und vollständige native Rohdaten

`AGENTS.md` enthält die wiedergefundenen Arbeitsregeln samt Quellen, Research-Verfahren, offenen Fragen, Endziel, Agenteneinsatz und geprüften Sicherungen. Ein vollständiger Chatexport ist keine Voraussetzung der autorisierten Fortsetzung. Die exakten letzten drei Nachrichten wurden nicht vollständig wiedergefunden.

Der erhaltene alte Workspace wurde mit GitHub verglichen; sein neuerer lokaler Checkpoint `dac5a5f` ist wieder aufgenommen. Tatsächlich überprüft: 1875 native Zeilen/118 Rohbatches. Die 736er Basis plus 72-Batch-Delta rekonstruieren das gesamte originale NPZ bytegleich (`09fde379793ea8c4a63268df729a33b4b98a3f4f90f3eeee2dec4a83a10b5843`). Geschlossene Rohbytes liegen verlustfrei in `docs/proofs/continuation-20261011/action-native1875-recovered-20261012/parts/`; der Report erklärt den unverändert erhaltenen veralteten letzten Einzelworker-Status. Kein Nutzen-/Redmi-PASS daraus.

Der vorhandene isolierte Approval-Reader-/Firing-Fix ist wiedergefunden. Ein zusätzlicher Lock-/SQLite-Reproducer zeigt: Cancellation/Deadline blockierten bis zum Ende eines Schreibers. Der Kandidat prüft beim Warten nun spätestens alle 50 ms; beide Regressionen scheiterten vorher und bestehen danach; 31 gezielte Tests PASS. Belege `approval-reader-cancellation-20261012/`. Nicht in die eingefrorene Runtime integriert. Native Diagnose-Registrierung muss nach dieser Kandidatenänderung separat neu gebunden werden.

Nächste Arbeit gestartet: unveränderte 16-Fall-SourceHandoff-Ablation im erhaltenen Workspace, gleiche Preregistrierung `4cfaddad1d9fadd23b5810c7cd4ddc0637e0e9b59d6d6fcd007fc22b5870b1d0`, alle 121 Runtimequellen unverändert. Danach originale NumPy-Trainings-Seeds13/21/34 und Dream2 (2/15 abgeschlossen), danach isolierte Fixes integrieren, Gesamttests/Paketprüfung und weitere ursprüngliche Gates. Fehlendes PyTorch im neuen Workspace ist eine technische Voraussetzung, kein abgeschlossener Dream-Lauf.

STEP2 UTILITY_FAIL/B3 L1 FAIL bleiben erhalten; Canon/Fullscope noch offen. GitHub-Veröffentlichung gilt erst nach geprüftem Remote-Tree.

## Ergänzung 2026-10-12 Thread „Nächste offene Pakete I“ (Claude): WP-N7-Rest native Cache

Isolierter Kandidat, keine eingefrorene Runtime-Quelle geändert: `scripts/native_cache_primitives.py`, `scripts/native_cache_bench.py`, 8 Tests, Linux-nativer Beleg `bench-results/native-cache-20261012/`, Doku `docs/NATIVE_CACHE.md`, Branch `claude/project-thread-uu86x1`. Wichtig für die spätere Integration: `runners.py` begrenzt weder `--cache-ram` (b10964-Standard 8192 MiB) noch `--ctx-checkpoints` (32; B2 je 19,3 MiB) → vor längeren Handy-Tests begrenzen (Vorschlag in der Doku), dann am Redmi messen. Kein Cache-Pfad ist bitgleich; Exact-Restore bleibt volles Re-Prefill.

## Ergänzung 2026-10-12 13:40Z Thread „Nächste offene Pakete I“ (Claude): WP-S6-Rest nativer LFM2-Trainingspfad

Isolierter Kandidat, keine eingefrorene Runtime-Quelle geändert; `build_native_finetune.sh` und `native_select_finetune.cpp` behalten ihre Manifest-Hashes. Neu: `scripts/patches/ggml-lfm2-backward-b10964.patch` (SSM_CONV/CONCAT-Backward, TRANSPOSE-Gradient, Trainings-Graphbudget, maskierte Labels, exakter Cross-Entropy-Backward für Nullzeilen; `test-backend-ops grad` OK), `scripts/build_native_lfm2_finetune.sh`, `scripts/native_answer_finetune.cpp`, `scripts/native_lfm2_finetune_bench.py`, 5 Tests, Doku `docs/NATIVE_LFM2_TRAIN.md`, Belege `bench-results/native-lfm2-finetune-20261012/` (Linux-nativ, kein Redmi). Ergebnis: C3 LFM2.5-350M lernt nativ bis 7/8 Fakten (streng, Q4-Pfad), vergisst aber 2–5 von 10 Proben, Leck 0,4–0,8 → AG6-Gate nicht bestanden, nichts aktiviert. Harte Anker-Replays helfen nicht; der danach gebaute KL-Anker mit weichen Basis-Labels (`llama_opt_set_soft_labels`, Nachtrag 17:30Z) tauscht nur Lernen gegen Behalten (ffn_late 1–2/8 bei −1/−2 Proben). Nächster Schritt: weniger/andere Parameter (Low-Rank, Sparse-Memory) und Early-Stop. Achtung für alle nativen Trainingsbenches: Trainingstext in der History-Form des Templates bauen (nicht Prefill: LFM2 fügt `<think></think>` ein und lässt `<|im_end|>` weg).

## Vorheriger datierter Handoff (historisch erhalten)

# Aktueller Fortsetzungsstand — Codex, 2026-10-11, 23:21 Berlin

Der vorhandene Drive-Plan bleibt verbindlich; neue Zukunftsideen werden getrennt gesammelt. Ziel sind belastbare längere Menschentests und belegter fortgesetzter Lernnutzen, kein vorzeitig behauptetes AGI-/RSI-Ergebnis.

- Autoritative Code-/Test-/Proof-Quelle: GitHub `RedMentos/Aii`, Branch `codex/authority-live-comparisons`, https://github.com/RedMentos/Aii/tree/codex/authority-live-comparisons . Zuletzt verifizierte Basis: `ef46ddbbe2cc2b694ccb0c74275a86a78f0ae2aa`, Tree `0bd3babb9d8f0777f8b772f377829d5e7b3e4c36`. Vor jedem Wechsel tatsächlichen Remote-HEAD neu lesen; diese Notiz ist ein datierter Checkpoint.
- Code liegt im Repo unter `v13/code`; Roadmap `v13/ROADMAP.md`; aktueller Status `v13/code/BUILD_STATE.json`, `docs/completion-ledger.json`, `docs/CONTINUE_20261011_PROGRESS.md`, Proofs `docs/proofs/continuation-20261011/`. Drive-Roadmap-Originale, Canon und frühere Fehlschläge erhalten.
- Aktuell gesicherter Source-ZIP Version4, Phone-ZIP Version2. Phone-ZIP SHA `477593e79a6069210258d91500ca9a42b0dfeaadf696d9788b09c3a63679a88a`: tatsächlich entpackt1125 Tests PASS,0Skips,495 Datei-Hashes unverändert. Ausschließlich Linux-Softwaretest; Redmi-RAM/Thermals/Laufzeit nicht gemessen. Eine fehlerhafte RSS-Probe wurde verworfen und separat korrigiert.
- Workspace-Bereinigung entfernte zweimal lokale Caches/ungesicherte Resultate. Original736 native Tap-Zeilen/46Rohbatches sind als geschlossenes ZIP dauerhaft gesichert. Die erste vollständige1875-Erfassung hat dauerhaft erhaltene terminale11Worker-Belege, ihre großen Rohbytes wurden vor erfolgreichem Upload entfernt. Metadaten-Dataset wurde aus bereits angelegten Git-Blobs gerettet; dadurch fehlen weiterhin die nativen Zustände. Nicht aus Metadaten als vollständig rekonstruierte Rohdaten ausgeben.
- Native3Modelle+Launcher+19Bibliothekseinträge jetzt wieder bytegleich;121Source-Handoff-Quellen eingefroren. Neue Night-Capture-Preregistrierung `f348d9ca38c728c8b7a5074b25ce1a74aac7fd924e15da9406c3912146590c80` ändert nur Wiederherstellungsordner, keine numerischen Einstellungen oder Gates. Erst nach Git-VerifikationInference starten. Neue geschlossene Belege in<=1MiB Teile mit Teil-/Gesamt-SHA sichern; `scripts/sealed_storage_parts.py` rekonstruiert exakte Originalbytes.
- Nächste Reihenfolge: begrenzte tatsächliche Capture mit zwei frischen Invarianzkontrollen und kontrollierten8BatchWorker-Grenzen, vollständige1875Rohdaten plus originale3NumPySeeds13/21/34; danach unveränderte16FallSource-Handoff-Ablation; danach Dream2 exakt40BSteps×3Seeds×5Arme (2/15dauerhaft abgeschlossen; unvollständigerB10Arm vonBase neu). Alle schweren Modelljobs seriell unter8GiBLinux-Cgroup. Danach isolierteAG6Reader/FiringFixes integrieren und Paket erneut testen, dann weitereOriginal-Gates.
- Original STEP2:70/70UTILITY_FAIL, kein neuer Nutzen-PASS. B3L1:alle8TasksFAIL, L2–L4gesperrt. Gist nativeReadoutConsumer fehlt, aktuelletextbasierte Gruppierung ist kein gelerntesGist-Ziel. NativeFiringdiagnostik bleibtSHADOW,keineSelective-Auslassung. `canonical_architecture_complete=false`, `user_full_scope_complete=false`, aktuellerHandyqualitätsnachweisoffen.
- Bei parallelem Codex/Claude-Wechsel: erst Remote-HEAD und diese Drive-Datei neu lesen; geschlossene Belege/Gates weiterführen; eigene Branches oder Hash-CAS für Schreibzugriffe. Keine Force-Pushes und keine Änderungen an aktiven gefrorenen Quellen. Kein direkter Claude-Kanal ist hier verfügbar; GitHub/Drive sind die gemeinsame Übergabe.

## Historische ursprüngliche Drive-Übergabe (unverändert erhalten)

# V13 / Inquisition-JEPA – Übergabe für eine andere KI (Stand 2026-10-11)

Projekt: brain-inspirierte, kontinuierlich lernende KI-Runtime für ein Redmi-Handy (Android/Termux, 6 GB RAM). Nutzer schreibt Deutsch, arbeitet nur am Handy. Leitfrage des Projekts: braucht AGI mindestens 8 GB RAM; Zwischenergebnisse für Tests und exakte Werte sind erlaubt.

## Wo was liegt (Drive-Ordner https://drive.google.com/drive/folders/1dEAaqlWvdsU8hciVBNfVVPV1f5CjucZv)
- ROADMAP_Teil1von3.md, Teil2von3.md, Teil3von3.md: alle Arbeitspakete mit Status (zusammen die komplette ROADMAP.md)
- SICHTUNG.md: Sichtung der ganzen Übergabe, Widersprüche, verlorener Code
- NUTZER_ENTSCHEIDUNGEN.md: verbindliche Nutzerentscheidungen
- Code, Tests und Bench-Ergebnisse liegen NICHT als Text auf Drive. Sie stecken in ZIPs im Claude-Projekt (V13_2_Code.zip ca. 1,7 MB, V13_1_Doku.zip, V13_3_Bench.zip, V13_4_Archiv_ohne_Chat.zip, V13_5_Proofs.zip). Wer sie braucht, bittet den Nutzer, die ZIPs hierher in den Ordner hochzuladen.

## Kernpunkte
- Code in `code/v13/` (ca. 104 Module), Tests `code/tests/` (zuletzt ca. 940 grün, `test_bodies.TightBudget` sporadisch flaky), Befehl: `cd code && PYTHONPATH=.:tests python -m unittest`.
- Nutzerentscheidungen: viele verschiedene Modelle (B1 und B2 echt verschieden), Englisch zuerst, konstantes Lernen als Endziel, Ziel ist eine heruntergebrochene Gehirn-Simulation. Age-Hülle startet bei 0.
- Fertig laut ROADMAP: WP-A bis E, WP-V1 bis V9, WP-N1 bis N14, WP-T1 bis T16, WP-U1 bis U10, WP-AG (AG0 bis AG13), Abdeckung ca. 56 %.
- Offen: B3 LATENT unavailable (L1-Gate FAIL), STEP2 two-body FAIL, viele SHADOW-Flags brauchen Redmi-Messung (WP-R, nur der Nutzer), WP-T17 Dream-Lauf 2 (`--b-steps 40 --seeds 13,21,34`).
- Arbeitsregel: jedes Paket aktualisiert ROADMAP.md und schreibt eine Übergabenotiz; Status-Zeile „in Arbeit“ vor Beginn setzen.
- Nutzer-Pause bis Montag 2026-10-12 04:00 Berlin war angesetzt; der Nutzer lässt jetzt eine andere KI bis Montag weiterarbeiten.

## Ergänzung 2026-10-12 Thread „Nächste offene Pakete K“ (Claude): WP-S4-Rest SIGReg auf echten Taps

Vorregistrierte Ablation ema|sigreg|both (120 Läufe, unveränderter `predictor_worker.train`, echte B1-Token-Zustände aus `b3-l1-v3-20261012/states.npz`): **Default bleibt `ema`**. Wichtig für spätere Arbeit: Beim Laufzeitbudget (lr .002, Norm .02, 240 Schritte) repariert kein Modus einen kollabierten Checkpoint; wer das Predictor-Budget erhöht, sollte `sigreg` nehmen (EMA überanpasst dort). Keine Runtime-Änderung. Befund `docs/proofs/continuation-20261012/sigreg-real-taps/BEFUND.md`, Branch `claude/project-thread-s0290g`. Offen: B2-Qwen-Token-Zustände, Redmi.

## Ergänzung 2026-10-12 Thread K: R4 Teil 3, C3-Token-Unsicherheit

C3 LFM2.5-350M erkennt eigene Rechenfehler gut über die kleinste Logprob eines Ziffern-Tokens (frisch AUROC 0,84, vorregistriert), aber Körper zu wecken rettet diese Fehler nicht (Politik = C3 allein). Nächster sinnvoller Schritt: Signal mit Werkzeug-Nachrechnen (W2c) oder ehrlicher Unsicherheitsangabe koppeln, neu vorregistrieren. Befund `docs/proofs/continuation-20261012/r4-c3-uncertainty-wake/BEFUND.md`. Keine Runtime-Änderung.

## Ergänzung 2026-10-13 Thread K: R4 Teil 4, Nachrechnen mit `calc`

Vorregistriert: bei Ziffern-Unsicherheit schreibt C3 einen Ausdruck, `calc` rechnet, C3 antwortet erneut. Frisch 45/60 vs. C3 allein 42 (nicht signifikant, NOT_SUPPORTED). Summen-Ausdrücke gelingen 15/15, Differenzen (max − min) 1/15. Nächster Schritt: typisierte Werte + festes Rezept wie WP-W2. Befund `docs/proofs/continuation-20261012/r4-calc-recheck/BEFUND.md`.

## Ergänzung 2026-10-13 Thread K: R4 Teil 5, typisierte Werte + Rezept — CALC_SUPPORTED

Vorregistriert, frischer Seed 17: C3 liest nur Zahlen, feste Regel wählt Summe/Differenz, Rezept rechnet → 50–51/60 statt 40 (netto +10, p 0,006). Nächster Schritt: als SHADOW-Werkzeug in `toolstep.py` anschließen und mit anders formulierten/deutschen Fragen messen. Befund `docs/proofs/continuation-20261012/r4-typed-recipe/BEFUND.md`.

## Ergänzung 2026-10-13 Thread K: R4 Teil 6, `list_arith` im Live-Werkzeug-Pfad — TOOL_PATH_SUPPORTED

Werte-Rezept aus Teil 5 als READ_LOCAL-Werkzeug `list_arith` (aus bis Nutzer-Freigabe, dann SHADOW bis Alter 1). Vorregistriert, frischer Seed 19, echter Pfad ToolStep → C5 → TOOL_RESULT: 54/60 statt 40 (p 0,0013). Lesbare Ergebnis-Schicht war nötig (roh ignoriert C3 den Wert). Offen: Posten „Total“ verwerfen (1 Fehler je Seed), Broker-Korrekturtext kürzen, Werkzeugwahl für andere Formulierungen/Deutsch. Befund `docs/proofs/continuation-20261012/r4-listarith-live/BEFUND.md`. Branch `claude/project-thread-s0290g`.

## Ergänzung 2026-10-13 Thread K: R4 Teil 7, Summen-Zeile nicht als Posten — FIX_SUPPORTED

`listarith` verwirft gelesene Posten namens total/sum/gesamt. Frischer Seed 23: 55/60 statt 42 (p 0,001), Werkzeug-Werte 30/30. Befund `docs/proofs/continuation-20261012/r4-listarith-total/BEFUND.md`.

## Ergänzung 2026-10-13 Thread K: R4 Teil 8, gelernte Werkzeugwahl (Needle-Kopf) — NOT_SUPPORTED

Kopf erkennt neue englische Formulierungen viel besser als die Regel (F1 0,78 vs. 0,38), aber 21 % Fehlalarme; Deutsch blind. Nächster sinnvoller Schritt: BOOT-Regel nur auf die Frage anwenden (kein Modell), dann Kopf + Bestätigung. Befund `docs/proofs/continuation-20261012/r4-tool-choice-head/BEFUND.md`.

## Ergänzung 2026-10-13 Thread K: R4 Teil 9, Regel nur auf die Frage — NOT_SUPPORTED

Frage-only-Regel beseitigt Daten-Fehlalarme; mit Formulierungen aus Familie A F1 0,79 vs. 0,48, aber 14 % Fehlalarm durch „total number of entries“. Nichts übernommen. Befund `docs/proofs/continuation-20261012/r4-rule-question-only/BEFUND.md`.

## Ergänzung 2026-10-13 Thread K: R4 Teil 10, Fragen-Regel R3 übernommen

`agi/listarith.operation` liest jetzt nur den Frageteil, kennt mehr Formulierungen und schließt Zählfragen aus. Neue Familie E: F1 0,73 vs. 0,50, 0 Fehlalarme; R4-Aufgaben unverändert. Befund `docs/proofs/continuation-20261012/r4-rule-r3/BEFUND.md`.

## Ergänzung 2026-10-13 Thread K: R4 Teil 11, R3-Formulierungen live — R3_LIVE_SUPPORTED

Frischer Seed 29: 25/30 statt 13 (p 0,0018), Werte 30/30. R4-Werkzeugkette (Teile 3–11) vorerst abgeschlossen; offen: Deutsch, übersehene Formulierungen, Redmi. Befund `docs/proofs/continuation-20261012/r4-r3-live/BEFUND.md`.

## Merge-Hinweis 2026-10-13 13:05Z Thread K (GPT/Codex arbeitet parallel)

Nutzerhinweis: GPT arbeitet am selben Code weiter. Stand: Branch `claude/project-thread-s0290g` (HEAD `42a28dd`) hat keine fremden Commits. `origin/codex/continuation-review-20261013` (GPT/Codex, letzter Commit `5a69538`) baut auf Thread M auf und enthält Thread Ks R4-Werkzeug **nicht**. Beim Zusammenführen betroffen: `v13/toolstep.py` (Thread K: `_propose_list`, `shadow`, `layer`, `LIST_*`; Thread M: `propose_note_edit`, `_forecast`), `v13/agi/tools.py` (eine `list_arith`-Registrierung), `v13/transaction.py` (WP-W2c-`text`-Typ, identisch zu W2c), `v13/broker.py` (`correction_text` für `list_arith`), neu `v13/agi/listarith.py`. Der geteilte Ordner `/mnt/project-files/v13/code` enthält beide Seiten schon zusammengeführt und getestet (Referenz). Nichts überschreiben, kein Force-Push; Konflikte beidseitig erhalten.

## Ergänzung 2026-10-21 Thread „Z5b Koalition mit Platzmangel“: WP-Z5b gemessen — G-FOCAL-CAPACITY-003 bleibt PARTIAL

Vorregistriert (`bench-results/z5b-capacity-20261021/PREREGISTRATION.md`), `scripts/z5b_capacity.py`, 5 Tests. 60 neue Aufgaben mit je 6 gespeicherten Notizen, Effort max, 4 Plätze, 5 Läufe: Platzgrenze greift in 300/300 Turns (9 Kandidaten), 11 Verdrängungen. Bestanden/300: ausgeliefert 68, Koalition als Engpass 60, Voll-Kontext 54, feste Slots 55, Retrieval 64, ohne Kontext 47; Koalition vs. Voll-Kontext 33:27 p = 0,52, Rauschband 4 → FAIL. Eigenschaft 4 (Aufnahme nur über Salienz) tritt nie auf. Ursache: Notiz-Priorität kennt keine Aktualität/Ersetzung. Wichtig für Folgearbeit: im ausgelieferten Pfad gehen abgerufene Notizen an der Koalition vorbei in die Antwort (ACTIVE_VIEW); die Koalition filtert nur Körper-Angebote. Cloud-Home: `python3 -m v13.bootstrap --home DIR` (ca. 3 min).
