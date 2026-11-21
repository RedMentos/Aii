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



## Boss integration checkpoint — 2026-11-21, 02:58 CET

### Verified release and integration state

- Release branch HEAD at readback: `c3c32c05a0374e970d274f8a777a7ab85c067d66`; this is documentation-only. Last code-bearing release SHA: `3db6d1f00fceab9e7755bc8f4c25882ef7f19258`.
- Exact push CI for `3db6d1f` is fully green, including private bridge, owner-read, Lab Age, release event, staged/integrated regression and V14 T8 Store. This does not imply Redmi installation or correct chat.
- Private owner-read PIPELINE_STATUS issue #357 is unanswered. No UPDATE_REQUEST, phone mutation or local test is authorized from an absent receipt.
- Local full checkout/tests are BLOCKED by GitHub DNS in this environment. GitHub Actions evidence is CI/Linux only.

### Cross-agent candidate reconciliation

1. **#2145 T8 Runtime consumer (Boss lane):** previous exact head failed because the receipt's SourceRef lost span/modality fields before exact provenance matching. Boss branch `boss/v14-t8-runtime-shadow-consumer-20261121` now preserves full verified SourceRef at `08d14737f1ee554f2b160986f95d9f28d6bc1fa2`. Exact-head CI has not run; do not merge. Before integration, carry forward #2143/#2147's newer paginated authority, source-digest grouping and checkpoint validation; the current #2145 snapshot is older.
2. **#2143/#2147 JEPA/Memory:** source-digest holdout fix is conceptually necessary, but exact #2147 tests still fail the shuffled-action negative control on Python 3.13 and 3.14. Keep the gate. Improve the fixture with source-digest groups containing all four action variants and a measurable action-conditioned target; do not loosen assertions or claim useful JEPA from parameter delta alone.
3. **#2144 A5 audio/Core:** exact V14 test fails because the staged test directory already exists; the broader stage chain also needs reconciliation. Fix the fixture idempotently and compose the A5 overlay onto the same Boss-owned builder chain. Do not merge a parallel stage-builder/runtime_deploy pin set.
4. **#2142 model comparison/Research:** read-only candidate comparison code and 16 synthetic tests pass; no GGUF inference or Redmi candidate verification occurred. Exact staged-context check is absent, so it is not yet eligible for the reviewed release queue. No download or production swap.
5. **#2137 T8 Store authority:** merged and exact release push CI is green. It remains a Store-verified scalar temporal adapter, not a normal Runtime consumer or full JEPA.

### Explicit next deliverables by existing team role

| Role | Next concrete implementation/review outcome | Acceptance evidence |
|---|---|---|
| Core & Harness | Repair arithmetic authority/source diagnostics/World-transition checks; fix the shared stage fixture and rebuild one immutable Runtime candidate chain for A5 + T8 consumer without stale source pins | Exact staged + integrated regression green; preserve fastpath and B1/B2/C3 paths; no fabricated arithmetic authority |
| JEPA & Memory | Reconcile #2143/#2147 into the deployable authority, preserve pagination/SELF_MODEL/recall, repair action-conditioned holdout fixture and connect T8 outcome to a real World/Planner consumer | Python 3.13/3.14 negative controls pass; source-digest disjointness; before/after parameter diff, heldout utility, replay/no-predictor ablation, restart/retention/rollback |
| QA & Android | Keep #357 owner-read-only; once a receipt exists, report exact installed SHA/auto-update state; separately test API/UI permissions, stop/revoke/audit, voice and update recovery on Redmi | Actual private owner receipt and device measurements; no CI-to-Android inference |
| Research & Perception | Repair/verify A5 producer-consumer consent contract and RAW EAR source binding; review model comparison's license/ARM/runtime boundary; keep LFM2.5-230M diagnostic-only | Exact source-bound receiver test; no microphone claim without OS capture; no candidate swap without explicit consent and measurements |
| Boss & Integration | Keep release ancestry/PR dependency graph current; obtain CI for #2145 SourceRef fix, integrate only the newer T8 authority plus shared builder after tests; continue clause-level Canon map | Read-back commit/PR SHA, exact-head CI, no capability lost, all environment evidence separated |

### Whole-system priority remains unchanged

The top user-facing blocker is still a correct, responsive native Redmi conversation with source-bound B1/B2 contributions, not a dashboard or synthetic arithmetic test. The next integration must preserve the complete Canon: A0–A5, B1/B2/B3/B4/B5, C/JEF/output/tools, World/Self/memory, JEPA/EMA/plasticity, sleep/replay, voice, Android API/UI control, Age/X10 rights, self-optimization, Context OS/Memorilla, model licensing/performance, privacy and rollback. No capability family is accepted from this checkpoint.


## QA cross-review evidence preserved — 2026-11-21

- **Updater safety:** QA's #2138 fix addresses stale-success CI selection and two race windows: after graceful stop and after source fast-forward immediately before launcher activation. Its exact code-bearing release CI is green. This is a correct release-gate implementation, not proof that the phone installed it; fresh owner-read #357 is unanswered.
- **T8 authority:** the merged #2137 source corrections distinguish CANCELLED/ABORTED from OUTCOME_UNKNOWN/INTERRUPTED without learning updates, scan ActionOutcome history to a 4096-row fail-closed bound, and fsync the parent directory after rollback replacement. The code-identical PR head had 52 focused V14 tests, 240 staged-runtime tests and 415 integrated-regression tests pass. The dedicated V14 T8 workflow was Python 3.11 only in the QA checkpoint; add Python 3.14 coverage before treating that path as target-version verified. None of this proves a normal Runtime learning consumer.
- **Stale device baseline:** private V13OBS #115 (2026-11-18) reported C3 TTFT 77.51 s, total 84.37 s, 11 generated tokens; B1/B2 TIME_BUDGET at 60.1/50.5 s and zero source-bound offers; native residency UNKNOWN_NO_GROUP_CHILDREN. This is stale baseline evidence only. Current installed SHA, runtime, updater and consent remain unknown because fresh PIPELINE_STATUS #357 has no reply.
- **A5 audio:** #2136 is only a consent-checked synthetic PCM16 → PerceptPacket → A4/C3 adapter; no microphone capture or speech effector is proven. #2139's earlier staged/integrated failure came from six downstream immutable candidates pinning an old v13/runtime.py; the shared stage chain must be rebuilt semantically, not hash-refreshed blindly.
