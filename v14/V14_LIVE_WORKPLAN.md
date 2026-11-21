# V14 / Inquisition-JEPA — LEBENDER ARBEITSPLAN

**Fassung:** 2026-11-20 · **Rolle:** operativer Einstiegspunkt für ALLE V14-Agenten.  
**Kanon:** [V14 Master](V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md) (aktive Gesamtarchitektur mit ALLEN historischen Anhängen), [Architekturfassung](V14_ARCHITECTURE_AND_RESEARCH_ONLY_20261119.md), [Forschungsjournal](V14_RESEARCH_LEDGER.md), [Backups](backups/).  
**Wichtig:** Nicht als Implementierungsbeweis lesen. Funktionale Ziele sind verbindlich; Status erfordert reale Laufzeit-, Lern- und Geräteevidenz.

## 0. Nutzerabsicht und unverhandelbare Korrekturen (20.11.2026)

- Das gesamte System soll *verteilt denken*: das Bewusstseins-/Integrationsmodell gehört logisch zum ganzen Gehirn, nicht zu einem JEF-Chef und nicht zu einem Meldesystem isolierter Mini-Agenten. Der Begriff ist hier eine Designmetapher, kein bewiesenes phänomenales Bewusstsein.
- Keine starren A→B→C-Takte: ereignisabhängige, rekursive, kooperative, rivalisierende, mehrstufige, emergente und opportunistische Pfade. Reale Handy-Ausführung darf Ressourcen bedingt serialisieren, aber nicht die kognitive Logik linearisieren.
- **Echter latenter Austausch im ganzen System als Ziel**, kein gewöhnlicher gemeinsamer Text-/JSON-Messagebus als vermeintliche Erfüllung. Aktivierungsvektoren, trainierte Alignment-Projektoren, flexible Schreib-/Lesezugänge, Provenance, Consent, zeitliche Semantik, Receiver-Wirkung, Ablationsmessung. Text/SOURCE_EXACT bleiben Fallback, nicht das finale Design.
- **Aktives, dauerhaftes Lernen ist systemisch und vielförmig**, nicht eine einzige JEPA- oder Reward-Updatekette: Wahrnehmungslernen, Ereignis-/Zeit-/Omission-Vorhersage, Aufmerksamkeit, Neugier/Exploration, eigene Fragestellung, Kausal-/World/Self-Updates, Episodic/Semantic, Modulatoren, lokale Eligibility/Plastizität, Cross-Organ-Lernen, JEPA, LoRA/Expert, distillative Mini-Interventionen, Replay/Dream, Meta-Lernen, Algorithmus-/Code-Selbstoptimierung. Zusätzlich alte V13-Untermechanismen und Parameter ohne Auslassung.
- **Langfristig alle geeigneten neuronalen Komponenten lernfähig**, auf unterschiedlichen Zeitskalen. Ein langsam laufendes EMA-Ziel oder temporärer Vergleichsstand ist kein permanent „frozen teacher“. Technische statische Hilfsteile im Prototyp sind nur als ausdrücklich vorübergehendes Provisorium zulässig. Keine ideologische Architekturfixierung auf fest trainierte Teacher.
- V14 ist **vollständige Weiterentwicklung von V13**. Nichts aus dem V13-Canon, allen drei Drive-Roadmaps, neueren Anforderungen oder historisch benannten Komponenten wird still gelöscht. Aktive Designanpassungen müssen Migration, Nachweis und Rückfall enthalten.
- **Aktuellste Forschung wird proaktiv betrieben und behalten**: Paper lesen, begrenzen, falsifizieren, technisch auf V14 abbilden, konkrete Prototyp-Ideen, Checks, Nachfolgearbeit, Quellen und Datum dauerhaft dokumentieren. Erkenntnisse dürfen V14 nach begründetem Vergleich verändern, auch Komponenten neu kombinieren oder ersetzen; niemals Ziele still abschaffen.
- **V14 Master bleibt live bearbeitbar**; bei jeder begründeten inhaltlichen Änderung erst unveränderliche historische Sicherung + Provenienz/Diff, danach aktive Master-/Kurzfassung/Workplan-Aktualisierung. V13-Rohcanon bleibt historische Referenz, nicht täglich umzuschreiben.

## 1. Source of Truth: aktive Dokumente vs. unveränderliche Sicherungen

1. **Aktive SoT:** `v14/V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md` – Name historisch datiert, Inhalt ausdrücklich lebend; keine neue konkurrierende „V15“-Masterdatei pro Agentenlauf. Vollständige V13-Quellenanhänge hinter Teil III unverändert lassen.
2. **Lesefassung:** `v14/V14_ARCHITECTURE_AND_RESEARCH_ONLY_20261119.md` – deckungsgleich zu den operativen Teilen I/II, aber ohne Anhänge. Kein eigener widersprechender Canon.
3. **Laufende Aufgaben:** diese Datei – priorisierte Integrationsarbeit, Zuständigkeiten, Beweise; regelmäßig aktualisieren.
4. **Research Ledger:** `v14/V14_RESEARCH_LEDGER.md` – nachprüfbarer Eingangs-, Prüf- und Versuchspfad für aktuelle Forschung; keine losen Paper-Sammellisten.
5. **Backups:** `v14/backups/` – historische unveränderliche Kopien vor substanziellen Masteränderungen; zusätzlich ist jedes Git-Commit ein reproduzierbarer Stand. Keine Secrets oder privaten Originalchats öffentlich ablegen. Git-Kommit vor und nach Änderungen verifizieren, kein Force-Push.
6. **Ledger Canon Coverage:** `v14/V14_CANON_COVERAGE_INDEX.md` – alle erkannten historisch benannten Bausteine/Abschnittsüberschriften; Status default `REQUIREMENT/UNVERIFIED`, bis belastbare Code-/Test-Evidenz existiert. Ein Punkt darf nicht aus diesem Index verschwinden, nur weil eine alte Lösung ersetzt wird.

### Update-Transaktion
`READ_CURRENT_HEAD -> INVENTORY_CHANGED_REQUIREMENTS -> CREATE_IMMUTABLE_BACKUP -> EDIT_ACTIVE_MASTER -> SYNC_READABLE -> UPDATE_LIVE_WORKPLAN & RESEARCH_LEDGER -> DIFF_COVERAGE -> REVIEW -> PUSH -> READBACK`.

Neue Agenten prüfen vor Änderungen GitHub-HEAD und andere offene Arbeiten. Bei Konflikten: neue Branches/PRs oder geordnete Integration, keine überlagernden Schreibzugriffe.

## 2. End-to-End-Ziel und ausführbarer vertikaler Pfad

**Funktion statt Organ-Attrappe:** reales Input-Ereignis → A0..A5 Provenance → dynamische verteilte Aktivität in B1_DETAIL/B2_GIST, B3 latentem Austausch, B4 Workspace und C/World/Self/Memory/Inquisition → finaler C3-/C7-Output oder zugelassene C5-Aktion → Outcome/Feedback → neue Erinnerung oder *nachgewiesener* numerischer Lernschritt → Retention/Rollback → Restart. **Das ist ein Testszenario**, keine starre Pflichtreihenfolge im echten Betrieb.

- Native C3-Ausgabe und schnelle einfache Antwort ohne schwere Bodies; komplexe Fälle können parallel oder rekursiv re-enter.
- B1 und B2 liefern *verschiedene* kausal nutzbare Beiträge; zwei identisch gepromptete Dense-Läufe zählen nicht als finale zwei MoE-Gehirnhälften.
- Jede echte latente Übertragung muss Senderaktivierung → trainierte Projektion → Einbindung beim Receiver → gegenüber SOURCE_EXACT/NO_MESSAGE messbar veränderte Receiverfunktion belegen.
- Jeder echte JEPA-/Continual-Learning-Claim verlangt trainierbaren Parameter, Optimierer-/Update-Semantik, Parameter-/Checkpointdiff, echte EMA-/Target-/Retention-/Holdout-/Negative-Control-Auswertung, Persistenz und Rückfall.
- Jede Live-Android-Funktion verlangt auf dem Redmi gemessene reale Ausführung. Linux-Tests und synthetische Verträge bleiben wertvoll, sind aber keine Android-/MoE-/JEPA-Beweise.

## 3. Parallele Entwicklungsfronten – nicht nur ein Patch nach dem anderen

| Front | Jetzt zu verbinden oder zu bauen | Akzeptanz und negativer Beweis |
| --- | --- | --- |
| **A / Perception / Active Attention** | A0–A5 reale multimodale Eventspur, Quelle/Zeit, A3 lebendiger Projector, A4 Re-look/Neugier, Audio/Bild später live mit Consent | native Eingabe→brauchbarer konsumierter Latent/Percept; echte A5-Source-Kette |
| **B1/B2 / Split Brain** | unterschiedliche Detail-/Gist-Modelle und Zeitfenster; langfristig zwei eigenständige sparse MoE; Expert-/Residency-/Swap-Pfade | eigenständige native Beiträge, Ablation, Komplementarität, RAM/Latency |
| **B3/B4 / Latent + verteilte Integration** | Aktivierungen/Projektoren, Receiver-Injection, verteilter Zustand, Rekurrenz, dynamisches Routing; genau definierte Lastpfade | Latent vs Exact vs None, echter Receiver-Effekt, nicht nur JSON-Routing |
| **C / JEF / Inquisition / Language** | kleine C2-/C3-Organe, flexible Fokus-/Interrupt-/Kritik-/Outputpfade; kein JEF-Zentralbewusstsein | richtige schnelle C3 Native Tokens, nachweislich konsumierte Alternativen, Sicherheits-/Toolgrenze |
| **Memory / World / Self / Motivation** | Fast/Slow; Episodic + semantischer Weltgraph, getrennter Self-Kopf, Zeit-/Outcome-/Omission-Erwartungen, Goal-Registry/Curiosity | second-attempt, Quellenbindung, realer Outcome/negative controls, Widerruf/Restart |
| **JEPA / Online Plasticity / Meta** | lokale und Cross-Organ-Head-/Adapter-/Expert-Gewichte; JEPA EMA, Eligibility×Modulation, Teacher/Student nur als flexible Rollen, kleine selektive Distillation, Sleep/Dream | Lernkurve vs Kontrollgruppen, alte Fähigkeit behalten, nach Reboot nutzbar |
| **Android / Runtime / UI** | ein Befehl, Update/Automerge ohne Verlust, lebendige Buttons, Autostart/Cancel/Resume, bounded native multi-model runs, echte Performance | 20+ native korrelierte Turns, p50/p95, RSS/PSS, Crash-/Update-Recovery |
| **Tools / Safety / Self-Edit** | Rechte/Consent/Age getrennt von Ressourcen; C5 Action→Outcome; künftig begrenzter Code-/Organ-Ersatz via Tests, Review, Rollback | realer genehmigter Pfad, Negative Cases, keine Selbstvergabe von Rechten |
| **Research / Open Source** | laufend Primärquellen/Releases/Benchmarks, Lizenz-/Weight-Prüfung, Experimente, konkrete Integrations-Vorschläge | datiertes Research Ledger, verknüpfte Tests und Pull Requests, auch negative Befunde |

**Arbeitsreihenfolge = Abhängigkeits- und Nutzenpriorisierung, keine funktionale Beschneidung.** Mehrere Fronten parallel bearbeiten; einen gemeinsamen integrierten Kernel ausbauen und im selben Entwicklungszyklus korrigieren, nicht bei jeder synthetischen Fixture anhalten.

## 4. Aktive Research-Routine

Bei jedem Forschungs-/Entwicklungsdurchlauf: (a) neue Primärquellen und Versionen seit dem letzten durch echte Quellen dokumentierten Scan finden; (b) relevante Arbeiten vollständig oder zumindest Methode, Daten, Limitations, Tabellen/Code kritisch prüfen; (c) aktuelle Evidenz vs Hypothese vs Marketing unterscheiden; (d) V14-Teilpfad / alter Canon-Abschnitt / nötiges fehlendes Modul bestimmen; (e) skizzierte Integration mit Alternativen, Ressourcen, Lizenz, Ablation, Gegenbeispiel, Rollback und konkretem nächstem Versuch im [Research Ledger](V14_RESEARCH_LEDGER.md) protokollieren; (f) erst bei nachweisbarer Verbesserung die aktive Architektur ändern und vorher sichern.

Bei vom Nutzer genanntem Paper: Titel/ArXiv/Varianten/Synonyme auflösen, vorhandenen Ledger zuerst prüfen, neue Primärquelle lesen, bestehende Hypothesen und Notizen zeigen, mit realen Gegenbefunden abgleichen; niemals „schon gelesen“ ohne einen tatsächlichen datierten Nachweis.

**Adaptieren ausdrücklich erlaubt:** Ist eine Arbeit nach kritischer Prüfung genau das gesuchte fehlende Verfahren oder die nötige Voraussetzung, darf der Forschungsagent einen Architektur-/Code-Änderungsvorschlag und erforderlichen Tests selbst eröffnen und Implementierung vorantreiben. Nur nach Messung und unabhängiger Prüfung wird aus Vorschlag ein aktives Design. Funktionale V13-Ziele bleiben erhalten; bei technischen Ersetzungen explizite Migration statt stiller Streichung.

## 5. Agenten- und Berichtvertrag

Der erste Agent liest aktive Master-/Workplan-/Ledger-Dateien. Jeder bearbeitet eigene Dateien / Branch; zentrale Master-Edits nur durch Integrator oder nach koordinierter Ownership. Kein Agent meldet Anzahl eigener Textbeiträge als Fortschritt. Jeder Bericht enthält:
1. tatsächlich neue ausführbare Funktion/Consumer, mit Quelle, SHA, Modellen/ABI/Lizenzen;
2. gekoppelter Full-System-Pfad und betroffene alte Canon-/neue V14-Anforderungen;
3. getrennte Evidenz `SYNTHETIC / LINUX_NATIVE / ANDROID_NATIVE / REAL_WEIGHT_UPDATE / HELDOUT_PASS`;
4. was noch nicht funktioniert; bekannte negative Kontrolle/Regression;
5. relevante neue Forschungsbefunde + Ledger-Link;
6. größter nächster Integrationsschritt und zuständige Front.

Mehrere Agents dürfen die Architektur kreativ herausfordern; sie dürfen weder alte Nutzerentscheidungen überschreiben noch unbelegte Behauptungen als real eintragen. Bei widersprechenden Quellen gilt: neueste klare Nutzerentscheidung > aktive Architekturkonkretisierung > historisch erhaltene Quelle; Laufzeitbehauptungen folgen aber immer dem tatsächlichen Testbeweis.

## 6. Unvollständigkeitskennzeichnung

**Gesamtstatus 2026-11-20:** V14-Design/Kanon vorhanden; vollständiger auf Redmi gelebter Organverbund, echter systemweiter Latent-Transfer und permanente lernende Zwei-Body-MoE-Endarchitektur **NICHT NACHGEWIESEN**. Die historischen STEP2/B3-FAILs bleiben offen, bis auf genau diese Ziele bezogene Re-Tests erfolgreich sind. Kein `COMPLETE`, kein Reife-/Age-Aufstieg aus Dokumentation.

## Aktuelle Team- und Nutzer-Übergabe (20.11.2026)

Die bestehenden fünf stündlichen Jobs arbeiten als **ein Engineering-Team** mit [Arbeitsvertrag](V14_TEAM_OPERATING_SYSTEM.md), [gemeinsamem Ticket-Board](V14_WORK_BOARD.json) und [nutzbarer Übergabe für das nächste Gespräch](V14_USER_NEXT_ACTION.md). Vorrangig ist **tatsächliches Coding, lokales Testen, Fixen, direktes Pushen in die eigene GitHub-Lane, Review, Integration und sichere automatische Übernahme nur mit verifiziertem Geräte-Updater**; der Nutzer soll für normale Pushes nicht jedes Mal einen Befehl eingeben müssen. Alternative kleine/größere Modelle sind ausdrücklich als isolierte Messversuche erlaubt; produktiver Wechsel nur nach transparenter Messung und Zustimmung. Der Terminal-Name kann `v13` bleiben. Keine falsche Behauptung von Android-Installation aus einem GitHub-Commit.



## Integration checkpoint — 2026-11-21

- Merged PR #2137 (`3db6d1f`) after source review and exact PR-head V14/Store plus V13 staged/integrated CI PASS.
- Merge-commit exact push: staged-runtime PASS; integrated-regression still IN_PROGRESS at last readback. Do not mark the current code release green until the exact SHA run finishes.
- The new T8 Store adapter is intentionally not yet imported by normal Runtime. Existing `Runtime._worker` invokes `online_world_update(limit=64)` after each committed turn, but a source scan found no `OnlineWorld.predict()` consumer in cognition/world/executive.
- Next combined slice: compose #2135's atomic weights+processed-ID checkpoint with #2137's verified T8 outcome path in the automatic postcommit loop; then make the resulting World prediction available to an actual decision consumer in SHADOW. Require held-out utility, no-predictor/replay-only ablations, source-disjoint validation, cancellation/omission controls, restart, retention and rollback.
- Core & Harness: repair #2140 arithmetic authority/source/World contracts and rebuild the #2139 audio/runtime candidate chain from semantic anchors.
- JEPA & Memory: rebuild the #2135 nested candidate chain bottom-up, integrate T8 postcommit consumer and expose prediction to World/Planner; no blind SHA refresh.
- QA & Android: keep private device status read-only; no UPDATE_REQUEST until a fresh owner-authenticated receipt; separately verify Android background/UI and voice consent on Redmi.
- Research & Perception: continue A5 RAW EAR consent/producer contract and primary-source/license review; do not call PCM16 synthetic tests microphone proof.
- Boss: finish exact merge-SHA CI, update coverage/board, and integrate the next compatible vertical slice.


### JEPA & Memory implementation checkpoint — 2026-11-21 / PR #2143

- Base: verified `gpt6/v13-private-remote-bridge-20261111` HEAD `c3c32c05a0374e970d274f8a777a7ab85c067d66`; code commit `2311b039eb49375829876e1bea8f2ac2d6975fe8`.
- The prior #2133 candidate's three QA findings are addressed in #2143: source-grouped rather than action-ID holdout, no learning/processed-ID insertion for CANCELLED/ABORTED/OUTCOME_UNKNOWN/INTERRUPTED, and oldest-first SQLite rowid keyset pagination instead of latest-N starvation.
- State schema v2 persists scan cursor with checkpoint; rollback restores the previous cursor. World/Self readouts and source-linked numeric episodic Memory recall are exposed in the Store-backed consumer.
- CI is configured for Python 3.13 and 3.14; exact results are pending. No local checkout test or Redmi receipt is claimed. Runtime wiring remains open; #2135's exact-once OnlineWorld candidate is still blocked by its nested SourceHandoff builder chain.
- Next: independent review, then integrate with the existing postcommit OnlineWorld path and expose predictions to a real World/Planner consumer in SHADOW. Keep learning gates closed by default.


### JEPA & Memory verification checkpoint — 2026-11-21 / PR #2143

- PR #2143 is ready for review. Code commit: `2311b039eb49375829876e1bea8f2ac2d6975fe8`; current branch head at this checkpoint: `a2788aacdae09bb675fff220cbda4ba74d400912`.
- Exact GitHub Actions result: run `44848998581`, Python 3.13 `57 passed in 4.35s`, Python 3.14 `57 passed in 7.83s`; `py_compile` passed on both. Additional push workflow `44848994421` (private remote bridge security) passed.
- The tests exercise source-disjoint grouping/digest integrity, censored-status exclusion, oldest-first backlog paging, restart/cursor continuation, nonzero encoder/predictor and EMA parameter changes, negative controls, B1/B2/SELF readouts, numeric Memory recall, checkpoint readback, retention and rollback.
- These are GitHub Actions/Linux results. No local Aii checkout or Redmi owner receipt is available: `REDMI_UNVERIFIED`. The consumer is still not wired into the normal Runtime postcommit path and does not update native B1/B2 GGUF weights.
- Next: independent review/merge, then integrate into `Runtime.online_world_update -> OnlineWorld.update` and route the source-bound prediction to a real World/Planner consumer in SHADOW. #2135's nested SourceHandoff builder chain remains the immediate integration blocker. No user action.


### JEPA & Memory final verification note — 2026-11-21

PR #2143 is no longer a draft and is ready for independent review. The exact tested code/workflow commit is `a2788aacdae09bb675fff220cbda4ba74d400912`; docs-only handoff updates follow it. Run `44848998581` passed all 57 V14 learning tests on Python 3.13 (4.35s) and Python 3.14 (7.83s), including compilation. Run `44848994421` also passed the private remote-bridge security workflow. No local Aii checkout or Redmi owner receipt exists. Runtime wiring remains the next gap.


## JEPA & Memory checkpoint — 2026-11-21 (PR #2148)

- Current tested chain: #2143 source-verified/paginated Store-backed WorldJEPA/EMA + numeric B1/B2/SELF SHADOW readouts; #2147 source-content-digest disjointness; #2148 strict action-shuffled positive control plus explicit uniform-replay vs no-replay ablation.
- Exact #2148 head 10e058a7418a5356b96f22f5344a5a3384f96214, GitHub Actions run 44853980297: Python 3.13 59 passed (12.19s), Python 3.14 59 passed (10.30s), compile PASS. PRs remain open/unmerged. No exact local checkout test and no Redmi proof.
- The current learner's replay-on/off comparison is an experimental code-path ablation, not yet evidence of improved real-user retention. The next experiment must compare new-cohort holdout utility and old-cohort retention under equal update and memory budgets.
- Integration blocker: #2145 currently records temporal/World SHADOW outcomes but does not call WorldJEPAStoreConsumer; its T8 authority uses newest-first latest-N scans without the persisted cursor/digest-disjoint page from #2143/#2147. Its runtime test also has the prediction_error vs persisted error field mismatch. Port the authoritative source/digest/cursor path and invoke the learner after committed outcomes, still with optimizer gates closed.
- No native B1/B2 GGUF weights, no normal Runtime learning loop, no Android install and no Redmi test are claimed. Release SHA: NOT_RELEASED; Redmi: REDMI_UNVERIFIED.


## Final JEPA PR readback — 2026-11-21

PR #2148 current head 6fec2dec1534285b654db60349efcd81f81b846c; code/test head 10e058a7418a5356b96f22f5344a5a3384f96214. Exact run 44854219157 tested docs/coverage head 3d8e55441d208eb8aec76cd121cc9f068376a88c and passed 59 tests on Python 3.13 (8.18s) and 59 on Python 3.14 (7.74s), including compilation. The only subsequent commit is research-ledger documentation; no code/test changes followed the tested head. PR is open, stacked on #2147, and not released. No local checkout or Redmi proof.


## Latest exact CI readback — 2026-11-21

PR #2148 current head is fb5e75f28dc4ac5b3f547388c48ea387b0e4d4c5. Exact code/test tree head e46b87d7d5cf1da31f58f6561d21193a4dfc9e87 passed GitHub Actions run 44854338438: Python 3.13 59 passed in 6.52s; Python 3.14 59 passed in 8.81s; compile and both jobs PASS. The only later commit is a next-action Markdown table refresh; no code or test file changed after the tested e46b head. The earlier run 44854219157 also passed 59/59 on both versions and is superseded by this readback.


## Boss integration checkpoint — 2026-11-21 05:00 CET

**Verified integration base:** `gpt6/v13-private-remote-bridge-20261111` HEAD `c0cedbde718ede6107f4df1f1bf9c784df4e00cf`.

### Newly present code (do not overstate its runtime scope)

- **WorldJEPA/EMA learner — PR #2151 with QA retention fix #2152:** merged into the release branch. Exact PR-head workflow `44861797478` passed 64 tests on Python 3.13 and 64 on Python 3.14, including compile. The code verifies source-bound T8 outcomes, oldest-first cursor plus bounded pending cohort, source-ID and content-digest-disjoint folds, censored-status exclusion, numeric encoder/predictor/EMA changes, separate B1/B2/SELF readouts, new-cohort utility, shuffled/zero-action negative controls, prior-cohort retention, persistence, restart, rollback and replay ablation. **Evidence = synthetic SQLite Store receipts on GitHub Actions/Linux.** The learner is not yet invoked by normal Runtime and is not native B1/B2 GGUF learning.
- **RAW EAR acoustic cues — PR #2155:** merged into the release branch. Exact safe-additive run `44862523075` passed py_compile + 8/8 synthetic tests; generic staged/integrated run `44862523082` passed 240 staged and 415 integrated tests. The separate module extracts bounded pitch/voicing/energy/activity hints from caller-supplied PCM16 and writes through the tested Store/A4/C3-admission adapter. **It is not the normal Runtime consumer**, not microphone capture, not ASR or speaker recognition, and not a trained/calibrated perception model.
- **Current release gate:** exact post-merge SHA `c0ced...` has 13 associated required workflows in `action_required`, not green. The branch is not release-certified. The current private owner-read has no reply; installed phone SHA is unknown. Do not issue UPDATE_REQUEST or claim Android deployment.

### Shared P0/P1 execution plan

| Owner | Next concrete code outcome | Acceptance before promotion |
| --- | --- | --- |
| Core & Harness | One current staged Runtime composition for source-bound arithmetic, A5 audio cues and FINAL/PROVISIONAL boundaries; integrate `audio_voice_cues.py` into the actual consumer and repair the shared candidate-builder chain | Exact staged + integrated + migration tests; 2+2 correct; B1/B2 offers delivered and consumed by C4/C3; no raw PCM persistence; consent-revocation negative control |
| JEPA & Memory | Port the exact #2151 source/digest/pending-cohort/retention authority into the normal postcommit Runtime consumer; route prediction to a real World/Planner receiver in SHADOW | Restart/idempotence, source-disjoint holdout, prior retention, shuffled/zero-action/no-predictor/replay-only controls; no optimizer permission |
| QA & Android | Maintain read-only device state until a fresh owner-authenticated receipt; independently validate updater CI ordering and rollback; prepare separate background/API and UI capability acceptance | Exact installed SHA receipt, updater consent, stop/revoke/audit/restart; OS permission evidence on Redmi; no GitHub-to-device inference |
| Research & Perception | Compare deterministic RAW EAR cues with a measured VAD/prosody baseline; maintain A0–A5 source/time/provenance; continue native hidden-state and latent receiver research | Calibrated task utility vs noise/silence/impulse and no-audio controls; ARM cost; provenance/consent; no learning/action authority from heuristic cues |
| Boss & Integration | Keep whole-Canon ledger synchronized, retire stale #2149 snapshot only after replacement PR exists, review current PR bases/heads/CI and integrate one compatible vertical slice | Exact current-head tests, consumer proof, immutable V13 appendix unchanged, current branch CI green, and Redmi receipt before release |

### Open PR reconciliation

- #2151 and #2152 are merged into the current release ancestry; #2150/#2148/#2147 are superseded by the #2151 integrated candidate.
- #2155 is merged. It does not change existing Core source pins, but Core must explicitly consume its new module.
- #2142 remains an open, stale-base read-only model-lab candidate; 23/23 synthetic tests passed on its code/test SHA, but no native GGUF comparison or staged-context acceptance exists.
- #2144 and #2153 remain staged Runtime candidates with shared builder/composition failures. #2139/#2140 are older failing alternatives. #2145 remains blocked and must not overwrite the newer #2151 source/digest/pending-cohort authority.
- #2149 is a stale documentation PR based on c3c32 and is not mergeable against current c0ced. The replacement evidence sync is built from c0ced on a new branch.
- #1983 remains optional SHADOW context-companion work; it does not replace Context OS.

### Environment and negative evidence

- GitHub CI is the only current exact test environment for the two merged code packages above. Full local Aii checkout is BLOCKED in this worker because GitHub DNS resolution failed; no local repository test is claimed.
- No native Redmi receipt, microphone, model inference, normal Runtime JEPA update, native B1/B2 weights, real-user retention or trained B3 latent exchange is demonstrated.
- Existing V13 functions and all historical V13 appendices remain in scope. No master architecture edit was made in this checkpoint; no backup operation was required. Do not mark any whole-system or Android acceptance as complete.



### Documentation sync PR — 2026-11-21 05:08 CET

- Fresh five-file evidence sync is open as [PR #2156](https://github.com/RedMentos/Aii/pull/2156), based directly on exact release HEAD `c0cedbde718ede6107f4df1f1bf9c784df4e00cf`; current PR head after board/handoff refresh is recorded by GitHub readback.
- PR changes only the work board, user handoff, live workplan, research ledger and additive Canon coverage overlay. No source/runtime code, model, permission, weight, phone data or device state changed.
- PR is currently mergeable, but its head has no returned workflow runs or combined status checks. Full local checkout is still DNS-blocked. Keep it open for independent review; do not treat it as a release.
- Stale documentation PR #2149 (base c3c32, mergeable=false) was closed as superseded by #2156 after its useful QA findings were reconciled.
- Boss posted concrete integration ownership notes on #2142, #2145 and #2153. Core owns the single staged audio/arithmetic builder chain; JEPA/Memory must port #2151/#2152 authority before Runtime wiring; Research/Perception keeps #2142 diagnostic-only until its current-base and staged-context gate are verified.



### Exact staged-builder failure readback — 2026-11-21 05:10 CET

- #2153 staged/integrated run `44860698029`: **17 failed, 221 passed, 10 skipped, 2 errors, 41 subtests**. The first shared failure is `integrated_jepa_guard_candidate_20261110.py:50`: `ValueError: online-world composition source changed` because `integrated_online_world_candidate_20261110.py` does not match its pinned `ONLINE_BUILDER_SHA`. A separate integrity check reports `integrated online-world hash mismatch: v13/contracts.py`. Two migration tests in `44860698035` report `PARTIAL` because staging did not activate.
- #2144 staged/integrated run `44856133052`: **22 failed, 206 passed, 10 skipped, 12 errors, 36 subtests**; the shared chain reports `integrated online-world hash mismatch: v13/operator.py` and a recovery/chat candidate pin mismatch.
- These fail before the intended audio/finality/JEPA Runtime consumers can be accepted. This is not a reason to relax immutable source checks or to update expected hashes blindly. Core must rebuild one composed candidate chain from current release bytes, then rerun Python 3.14 startup, staged-runtime, integrated regression, Lab Age and two-checkout migration.

