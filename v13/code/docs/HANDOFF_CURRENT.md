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

Neuer Schalter `b1_recent_source_chars` (Standard 0 = aus): B1 behält die exakte Quelle seiner letzten Runde. Vorregistrierter Lauf (10 Episoden, 5 Arme × 70 Zeilen, echte Modelle, Linux-Cloud): `Z2_DIVERGENCE_NOT_SUPPORTED` — Zwei-Körper .325 < b1_only .333, ein Körper + zwei Zustände nicht schlechter. B1 liefert jetzt Optionswerte (27/70 statt 0), exakte SPLIT-Entscheidungen nur im Ein-Körper-Arm (3/6). 0 falsch festgelegt. Befund `docs/proofs/continuation-20261021/step2-z2-timescale/BEFUND.md`, Branch `claude/project-thread-hsm0ga`. STEP2 UTILITY_FAIL bleibt.
# Aktuell 2026-10-21 (Thread „STEP2-Nutzen Engpass“): Eignungs-Werkzeug im Live-Pfad

`ToolStep._propose_eligibility`: Option-A/B-Fragen unter Projektregeln → C3 liest typisierte Werte aus Quelle + Body-Zitaten → Rezept entscheidet. Nur nach `:growth enable eligibility`, Age 0 SHADOW. Vorregistriert gemessen: 55/70 exakt, 0 falsch (LIVE_PROMPT_SUPPORTED). Handy-Testliste `../HANDY_TESTLISTE.md`. Befund `docs/proofs/continuation-20261021/eligibility-live/BEFUND.md`.

# Aktuell 2026-10-21 (Thread „Nächste Pakete Q“): Eignungs-Werkzeug im ganzen Live-Turn

`eligibility` läuft im normalen Turn (nur nach Freigabe, Alter 0 = SHADOW). Vorregistrierte Messung, 60 frische Aufgaben auf C3: Antworttext richtig 22 → 32 (p .006), falsch festgelegt 33 → 23, Rezept nie falsch, mit Broker-Korrektur sichtbar richtig 53/60. Befund `docs/proofs/continuation-20261021/eligibility-whole-turn-q/BEFUND.md`, Branch `claude/project-thread-hzzqh4`. Parallele Fassung im Thread „STEP2-Nutzen Engpass“ (dq33gk) beim Zusammenführen abgleichen.

Zusammengeführt in `claude/project-thread-dq33gk` (PR #7): Qs Fassung gilt, dazu Zitat-als-Zeiger-Schalter + `analyst_context`-Fix (Chat brach mit Schalter an ab). Ganzer Turn der dq33gk-Variante war NOT_SUPPORTED, daher entfallen.

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
