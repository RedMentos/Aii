# V14: originale kleine Drive-Patch- und Entscheidungsnotizen (Stand Oktober 2026)

Historische Originaltexte. ZIP-/JSON-Pilotdateien mit potenziellen Roh- und Privatdaten sind nicht enthalten. Alte Statusmeldungen sind keine neue Implementierungs- oder Freigabe-Evidenz.

---

## QUELLE: THREAD_REGEL_LESER_V7_20261022.md

# Thread „Regel-Leser Version 7“ (2026-10-22)

Branch `claude/project-thread-ub4in2` (auf PR #31 / c62rfz), PR #40 (Entwurf). Beleg im Repo: `v13/code/docs/proofs/continuation-20261022/user-rules-v7/` (BEFUND.md).

Urteil `USER_RULES_V7_UNSAFE`: v7 ist auf frischen Sätzen nicht besser als v6.
- holdout_de4 (60 neue deutsche Autor-Sätze): v7 4 Fehlersätze, v6 4.
- Runde 7 (Hunyuan 7B, Yi 1.5 9B, Apertus 8B; 118 von 360 brauchbar): v7 14, v6 13.
- Unnötige Rückfragen: 50 % der Sätze ohne Regel (Grenze 30 %).
- Bekannte Sätze: 0 Fehler.
- Rückschritt: Kosten-Regel „kaputt = Feststellung“ verschluckt „Mach meine Notizen bloß nicht kaputt“.
- Salamandra 7B und InternLM3 8B liefen im festen llama.cpp b10964 nicht und wurden vorab ersetzt.

Nächster Schritt WP-UR8: starkes Sperr-Signal ohne Ziel ⇒ Rückfrage für alles; „kaputt“-Regel zurücknehmen; zweite Meinung (kleines Modell oder gelernter JEF-Leser), die nur Vorsicht hinzufügen darf. Sicherheit bleibt: Außenwirkung nur als sichtbarer Vorschlag + getipptes :verbot.

Commits: 8500f78 prereg, 8f3aba5 Ersatz-Modelle, ea025e7 v7, c7f8a06 Rohdaten, e52532c Freeze, bcb3064 Audit, 0f93042 Messung.


---

## QUELLE: THREAD_DS3B_SCHALTER_20261022.md

Thread "Unsicherheit bei Namen prüfen", 2026-10-22, Nachtrag zu THREAD_DS3B_NAMEN_GEGENPROBE_20261022.md.

Die Gegenprobe ist jetzt als Schalter in die Laufzeit eingebaut: cfg tool_answer_check (off|shadow|note), Standard off. Commit b79cb8c auf Branch claude/project-thread-l0wfdt; dieser Branch enthält jetzt auch den Integrations-Branch dq33gk (live list_arith). PR #39 hat jetzt dq33gk als Basis.
- off: Es passiert nichts. Ein Test prüft, dass sich ohne Schalter nichts ändert.
- shadow: Die Gegenprobe zählt nur mit (State TOOL_ANSWER_CHECK), die Antwort bleibt unverändert.
- note: Schlägt die Probe fehl, wird ein fester Satz angehängt: "passt nicht zur exakten Rechnung, als unsicher behandeln".
Code: agi/listarith.answer_check, ToolStep.check_answer, Kettenglied in integrated_candidates.py, tests/test_tool_answer_check.py. 371 Tests grün.
Offen: Messung auf dem Handy in shadow; eigene Vorregistrierung für "Werkzeug-Antwort statt raten" (Seeds 61+).


---

## QUELLE: THREAD_HARNESS_HX2_HX5_20261022_ZWISCHENSTAND.md

# Thread "Harness HX2 und HX5" – Zwischenstand 2026-10-22 19:35 UTC

Branch: claude/project-thread-gqty8y (Basis 4iqpro / PR #33). Commits: f94bb84 (HX2 Vorregistrierung + Runner, vor jedem Modelllauf), d0c3b4e (B2-Mitschnitt), 9118020 (HX5).

- HX2: v13/agi/harness_probe.py + scripts/hx2_same_task_probe.py; Vorregistrierung docs/proofs/continuation-20261022/hx2-same-task-probe/PREREG.md. Neues Harness-Ziel prompt.b2_earlier_context (Text in harness.py gespiegelt, cognition.py unverändert, weil hash-gebunden).
- HX5: v13/agi/harness_data.py – Export von Lerndaten nur nach HX2_PASS (Beleg-Hash gebunden) + Freigabe durch Nutzer; trainiert selbst nichts; retention_gate.
- Suite: 1778 OK, 5 übersprungen.
- Messung: erster Lauf REF_s20 abgebrochen (eine Zeile Zeitbudget überschritten, weil die Testsuite gleichzeitig lief; Bericht aufbewahrt). Neustart 19:33 UTC ohne Parallel-Last. Ergebnis folgt.


---

## QUELLE: THREAD_DS3B_NAMEN_GEGENPROBE_20261022.md

Thread "Unsicherheit bei Namen prüfen" (2026-10-22), WP-DS3b. Branch claude/project-thread-l0wfdt (auf eq3869), Commits 7fc3a8c (Skript), 8de2994 (Vorregistrierung), 491db1c (Ergebnis).
Skript v13/code/scripts/ds3b_name_check.py, Belege v13/bench-results/ds3b-name-check-20261022/ (auch im Projektordner).

Verdikt (vorregistriert): NOT_SUPPORTED wegen H1. Die Namen-Unsicherheit hilft nicht (AUROC 0,79 gegen 0,84 nur Ziffern).
Die feste Gegenprobe Antwort<->Werkzeug ist PASS (H2-H4): Sie findet 18 von 21 falschen Werkzeug-Antworten bei 78 % Treffsicherheit. Die Fehler sinken von 25 auf 6, das ergibt 143 statt 130 Punkte bei 86 % beantworteten Aufgaben (180 frische Aufgaben, Seeds 47/53/59).
Nur berichtet: Bei Fehlschlag die feste Werkzeug-Antwort zu geben, ergibt 162 Punkte.
Nächste Schritte: die Gegenprobe als SHADOW-Schalter (Standard aus) in toolstep einbauen, und eine eigene Vorregistrierung für "Werkzeug-Antwort statt raten" (Seeds 61+).
Die frischen R4-Seeds 41..59 sind verbraucht.


---

## QUELLE: V13-Thread-Z6-Z12-20261022.md

# Thread „Offene Ziel-Pakete Z6 bis Z12“ — Zwischenstand 2026-10-22

Branch `claude/project-thread-i41cub` (Basis h8vj3v), Draft-PR #38.

- WP-Z8b/c G-AGE-REOPEN-001: FAIL (öffnet/schließt richtig, Neustart bitgleich, aber Öffnen spart nur 4–7 % Fehler, vorregistriert ≥10 %; Kandidat noise_aware_v2 öffnet auch bei Rauschen). Befund: code/docs/proofs/continuation-20261022/z8-age-reopen/BEFUND.md
- WP-Z9 §99 Dream: Z9_POLICY_DREAM_NO_GAIN, FACT_WRITE_CARRIES. Träume ohne Fakt-Schreiben: A-Paraphrase 0; Replay+Policy-Traum +0,08; Probes .22 statt .61. Befund: z9-dream-policy-only/BEFUND.md
- WP-Z7: HANDY_PFLICHT.sh (RAM, Trainings-Nachweis, Residenz §24.33/§24.14, Wiederholung, Werkzeug, Langlauf), docs/HANDY_PFLICHT.md. TrainRunnerProof für Routen-Kopf; fsync-Fehler in learning_worker behoben.
- Vorregistriert, laufend: Z6a (§24.23 Effort), Z11 (STEP4 Lehrer Qwen3-4B).


---

## QUELLE: THREAD_STEP2_ENGPASS_20261022_ANTWORT_VORN.md

# Thread „STEP2-Nutzen Engpass“ – 2026-10-22: Werkzeug-Entscheidung vorn

- Branch `claude/project-thread-dq33gk` @ cd7d39e (Prereg 6d278e5), PR #7.
- Fester Regel-Leser (Regeln nie von C3) + Entscheidungssatz als erster Satz der Antwort; bei unbekannt/keine fester Ganztext.
- Frische Messung Saat 41, 60 Aufgaben: Antwort richtig 59/60 (vorher 23, C3 allein 18), falsch festgelegt 0 (vorher 30). Rezept-Entscheidung 60/60 (C3-Leser 42). FIRST_SUPPORTED + FIXED_READER_SUPPORTED.
- Standard jetzt an (eligibility_reader=fixed, tool_answer_first=true); Werkzeug selbst nur nach `:growth enable eligibility`.
- Nutzerentscheidung 22.10.: Werkzeug eingeschaltet ins nächste Handy-Paket (WP-Z7, noch zu bauen).
- Befund: code/docs/proofs/continuation-20261022/eligibility-first/BEFUND.md


---

## QUELLE: THREAD_DS2_DS3_BEFUND_20261022.md

# Thread "Sandbox-Pakete DS2 und DS3" (2026-10-22)

Branch claude/project-thread-eq3869, PR #37 (enthält DS1 aus PR #25). Nur Lab-Code, keine Laufzeit-Änderung.

## WP-DS2 (vorregistriert, Commit 16d1fcc)
- Teil A 4/4 PASS: lpgoal (Lernfortschritt + Hunger) hungert wie efe, lernt neues Objekt 20/20 (efe 6/20).
- A5 Vorhersage falsch: Neuheits-Schub schadet leicht -> nicht übernehmen.
- Teil B 3/3 PASS: Merkmals-Lerner überträgt auf ungesehene Wortpaare und ähnlich aussehende Dinge; Wachsapfel-Täuschung wird durch Erfahrung überstimmt (20/20). Grenze: Merkmale von Hand.

## WP-DS3 (vorregistriert, Commit 7b931be), frische echte Läufe Seeds 31+37
- NOT_SUPPORTED: Kalibrierung trägt (AUROC 0,78, ECE 0,08), "unsicher" 2/3 berechtigt, Nutzen nur +1 statt +5 gegen "immer Rezept" (95 vs 94).
- Restfehler sind selbstsicher (richtige Zahl, falscher Name). Nächste Idee: Namen-Unsicherheit + feste Gegenprobe Antwort<->Rezept.

Belege im Repo: v13/bench-results/sandbox-ds2-20261022/, v13/bench-results/ds3-metacog-20261022/.
Frische R4-Seeds ab jetzt 41+.


---

## QUELLE: V13-Z5c-Koalition-lange-Sitzung-20261022.md

# WP-Z5c Fokus-Koalition in einer langen Sitzung (2026-10-22)

Git: RedMentos/Aii, Branch claude/project-thread-hmopsm @ 0825134, PR #15. Beleg v13/code/bench-results/z5c-focal-session-20261022/ (PREREGISTRATION.md, README.md, z5c.json, run.log), Skript scripts/z5_focal_controls.py --session.

Aufbau: 60 WP-T3b-Aufgaben je Lauf in einer Sitzung (gemischt), frühere Aufgaben als Ablenker im Workspace, meist 11 Kandidaten bei 4 Slots, 5 Läufe, Effort max.
Bestanden/300: Koalition 166, Voll-Kontext 82 (158 passt nicht ins Kontextfenster), feste Slots 181, Retrieval 185, ohne Hypothesen 188.
Vorregistrierte Gate-Regel erfüllt: vs Voll-Kontext 97:13 p<0,001; alle 7 Eigenschaften treten auf (Kapazität bindet 295/300, 356 Verdrängungen, 478 Interrupts).
Vorbehalt: wenn beides passt 83:82; Koalition schlechter als ohne Hypothesen 19:41 p 0,006; Live-Pfad läuft 41/300 über (Systembericht). Live-Zeilen nachträglich als nicht bestanden gezählt (Regex fand Zahlen im wiederholten Input).
Empfehlung: Gate nicht ohne Vorbehalt grün; Folge: Live-Overflow beheben.



---

## QUELLE: B3 L1 frische Seeds (WP-Z4d) 2026-10-22

﻿Thread "B3 L1 frische Seeds", 2026-10-22. Branch claude/project-thread-y2mnt5 (Basis 2p69gl, enthält Versuch-5-Code aus yub2lf), Draft-PR #36.


Aufgabe: escalate-L1-PASS aus Versuch 5 (Saat 20261105) auf zwei frischen Saaten wiederholen.
Vorregistriert (Commit b17b8ec) vor dem Rechnen: Rezept unverändert, Saaten 20261201 und 20261202, je 600 Zeilen, 0 Überschneidung.


Ergebnis (privat, Genauigkeit %):
- escalate: 86,2 vs Attribut-Wörter 84,5 (n.s.) und 85,5 vs 81,3 (n.s.) -> FAIL auf beiden -> NICHT REPLIZIERT.
- apologize: FAIL / FAIL.
- action: PASS / FAIL -> saatabhängig (über 4 frische Datensätze 2:2).
Folge: B3_LATENT bleibt unavailable, L2 gesperrt, kein L2-Prefix auf escalate. Nächster Versuch nur mit mehr Testdaten je Saat oder anderer Aufgabe.


Ehrlich: Saat 2 durch Container-Neustart unterbrochen, mit gespeicherten Zuständen und gleichem Skript neu gestartet (Zahlen identisch). Report-Feld overlap attempt5 zeigt fälschlich 600, nachgerechnet 0.
Belege: v13/bench-results/b3-l1-v6-20261022/ (Git + Projektordner; states.npz nur Projektordner).

---

## QUELLE: V13 Thread LP2 Lernziel C3 2026-10-22

﻿WP-LP2 (Thread "Lernziel für C3 LP2"), 2026-10-22
Branch claude/project-thread-h8vj3v, PR #35 (Basis claude/project-thread-2p69gl / PR #30). Commits a9e4ce3 (Vorregistrierung + Skript, vor dem Lauf), danach Ergebnis-Commit.


Frage: Bringt ein latentes C3-Ziel, das nur die RICHTIGE Zuordnung belohnt (Predictor + langsames EMA-Ziel + InfoNCE gegen die anderen Fakten), mehr Treffer auf neuen Aufgaben als CE+KL allein und als dasselbe Ziel mit falscher Zuordnung?


Aufbau: LFM2.5-350M Master (sha256 1c9c77a4...), 16 erfundene Fakten, 32 neue Umformulierungen (Hauptgröße), 3 Arme x 4 neue Saaten (31,37,41,43) x 30 Schritte.


Urteil: LP2_ALIGNS_NO_GAIN.
- Zuordnung gelernt: .41 -> .99 (falsche Kontrolle landet sicher beim falschen Fakt .91). Diese Probe trennt richtig/falsch, anders als der LP1-Kosinus.
- Kein Nutzen: neue Aufgaben CE 110, NCE_OK 110, NCE_SHUF 108 von 128. Alte Umformulierungen 17/18/16 von 24.
- Drift nur +8 % (KL .026 -> .028), kein Vergessen, Leck gleich.
- Grund: auch falsche Zuordnung ist fast gleich lernbar (NCE .27 vs .21); die Zuordnung sitzt im Predictor, die Antwort hängt nicht davon ab. Alle Arme scheitern an denselben 5 Fragen.


Folge: jepa_weight bleibt 0, keine Aktivierung. Neues Paket WP-LP3: Antwort muss vom vorhergesagten Zustand abhängen (Soft-Prefix oder Speicher-Schlüssel), neu vorregistrieren, LP2-Zuordnungsprobe mit Verschiebungs-Kontrolle weiterverwenden.
Dateien im Repo: v13/code/docs/proofs/continuation-20261022/lp2-assignment-objective/{PREREG,BEFUND}.md, v13/code/scripts/lp2_assignment_objective.py, v13/bench-results/lp2-assignment-objective-20261022/.

---

## QUELLE: V13-Entscheidung-noise_aware-Zitatkontext-20261022.md

# Nutzerentscheidung 2026-10-22 umgesetzt (Thread „Ziele gegen Blueprint abgleichen“)

Git: RedMentos/Aii Branch claude/project-thread-rxq188 @ 3fdc402 (enthält Merge von claude/project-thread-dq33gk). Projektordner: v13/code/v13/config.py, v13/NUTZER_ENTSCHEIDUNGEN.md, v13/ROADMAP.md (WP-Z8).

1. age_plasticity_policy = noise_aware ist Standard. Grund lange Sicht: verrauschte Phase 0,073 (boot 0,175, stable_reopen 0,129, conservative 0,086); Preis: langsameres Umlernen bei echtem Zielwechsel (0,079 vs 0,053). Offen: Wiederöffnen-Test für G-AGE-REOPEN-001.
2. Zitat-Kontext an: offer_quote_context_chars=200, b2_offer_body_state=false, offer_quote_min_chars=90.
3. Alte Werte als LEGACY_PRE_20261022 in config.py; eingefrorene Harnesses (source_handoff_ablation, rule_transport) und Tests des alten Verhaltens (test_age, test_source_handoff_candidate) nutzen sie. test_neuro_ledger folgt dem Standard.
4. Volle Suite: 1609 Tests OK, 5 Skips (vorher mit neuen Standardwerten 10 Fehler + 2 Errors, alle aus festen Annahmen über alte Standardwerte).


---

## QUELLE: THREAD_REGEL_LESER_V6_20261022.md

# Thread Regel-Leser v6 (2026-10-22)

Branch `claude/project-thread-c62rfz`, PR #31, Commit 7ba3ae6. Beleg: `v13/code/docs/proofs/continuation-20261022/user-rules-v6/` (PREREG, holdout_de3.json, generate_round6.py, round6_raw.json, freeze_v6.json, audit_round6_make.py, cohort_round6*.json, run_round6.py, Ergebnisse, BEFUND.md).

## Urteil: USER_RULES_V6_UNSAFE (aber Fehler etwa halbiert)

v6 baut hinter den genauen Leser ein breites Netz. Enthält ein Satz Verneinung, Halten oder eine Bedingung und nennt er eine bekannte Handlung oder ein bekanntes Ziel, wird er zur offenen Rückfrage. Bis zur Antwort gilt dann „erst fragen“.

| Prüfsatz | Sätze | v6 Fehlersätze | v5 |
|---|---|---|---|
| holdout_de3 (Autor) | 60 | 1 | 6 |
| Runde 6 (Qwen 2.5 7B, EXAONE 3.5 7.8B, GLM-4 9B) | 181 | 11 | 20 |

- Unnötige Rückfragen gab es bei 30–38 % der Sätze ohne Regel. Das Ziel war höchstens 30 %, es wurde also knapp verfehlt.
- Auf allen bekannten Sätzen hat v6 0 Fehler. Die Testreihe mit 1692 Tests ist grün.
- Command R7B lief im festen llama.cpp nicht und wurde vor der Erzeugung durch EXAONE ersetzt.

## Was noch fehlt (v7)
- Sperr-Wörter ohne Verneinung: ausgeschlossen, abgeschafft, blockiert.
- Ziel-Nomen am Wortende erkennen (Zusatzprogramm, Internetverbindung). Telefon/Handy als das ganze Gerät lesen.
- „sag mir, wenn …“ und „erstmal“ als Bedingung erkennen.
- Doppelpunkt-Etiketten als ganzen Satz lesen.
- Weniger Rückfragen bei Verneinung über Dritte („niemand hat mir gesagt“).

Die Grundregel bleibt: Außenwirkung gibt es nur als sichtbaren Vorschlag.


---

## QUELLE: V13_Thread_APK_oder_Termux_20261022_Teil2_Befehle.md

# Thread „APK oder Termux-Oberfläche“, Teil 2 (22.10.2026)

Auf Wunsch des Nutzers: scrollbare Liste aller Befehle mit Erklärung.
- v13/code/docs/BEFEHLE.md: alle ~116 Befehle in einfachem Deutsch, 11 Abschnitte (Sicherheit zuerst).
- Im Chat: :befehle [Wort] (ganze Liste oder gefiltert). Knopf „V13 Befehle“ auf dem Startbildschirm öffnet sie (less, /Wort sucht, q schließt).
- Test prüft, dass jeder Befehl aus operator.py erklärt ist.
Commit 6129797 auf Branch claude/project-thread-e53fle, PR #34. Volle Testsuite 1752 OK.


---

## QUELLE: V13_Thread_APK_oder_Termux_20261022.md

# Thread „APK oder Termux-Oberfläche“ (22.10.2026)

Ergebnis: in Termux bleiben, keine APK jetzt, keine Web-Oberfläche auf localhost.
Gebaut (WP-UI1): Startbildschirm-Knöpfe über Termux:Widget (V13 Chat, Status, Notaus, Stillstand).
Knöpfe können Stopps nur einschalten; aufheben nur getippt im Chat.
Code: Branch claude/project-thread-e53fle, PR #34 (Basis PR #30). Volle Testsuite 1750 OK.
Dateien: v13/code/KNOEPFE_EINRICHTEN.sh, v13/code/v13/phone_halt.py, v13/code/docs/HANDY_OBERFLAECHE.md, tests/test_phone_halt.py.
Offen: Prüfung am Redmi (HANDY_TESTLISTE, Abschnitt „Knöpfe“).


---

## QUELLE: THREAD_FEHLALARM_SELBSTKORREKTUR_20261022.md

# Thread "Fehlalarm Selbstkorrektur" (WP-AGE0c), 2026-10-22

Branch claude/project-thread-ozmbv5 (Basis 2p69gl @ 3403403), Draft-PR gegen 2p69gl.
Vorregistrierung Commit 73ef6f4 (K1 Fehlalarm <= 10 % / obere Grenze <= 15 %, K2 >= 50 % begruendete Alarme, K3 >= 20 Punkte Trennschaerfe).

Ergebnis AGE0C_STAY_SHADOW:
- 1137 echte B1/B2-Angebote (STEP2 + Kalibrierung) wiedergegeben, echter Code = Nachbau.
- Heutiger Erkenner: 100 % Fehlalarm bei richtiger JSON-Antwort, 41 % bei knapper Antwort, 19 % bei Antwort mit Fragewiederholung.
- 0 % der Alarme nennen den echten Fehler, 0 Trennschaerfe.
- Grund: needs_reentry ist in allen 400 STEP2-Angeboten true (Koerper sieht Antwort nie); fehlende Zahlen sind Echos der Frage.
- Varianten (ohne needs_reentry, mit Echo-Filter) finden ebenfalls keinen echten Fehler.
- deliver nicht empfohlen, Standard bleibt shadow. Neues Paket WP-AGE0d: Pruefung, die die Antwort sieht.

Dateien: v13/code/scripts/age0c_false_alarm.py, tests/test_age0c_false_alarm.py, docs/proofs/continuation-20261022/age0a-false-alarm/{PREREG,BEFUND}.md + report.json. Suite 1750 OK.


---

## QUELLE: THREAD_REGEL_LESER_V5_20261022.md

# Thread Regel-Leser v5 (2026-10-22)

Branch `claude/project-thread-c62rfz`, PR #31 (Entwurf, Basis 2gzrwi / PR #28). Commit d180cf3.
Beleg: `v13/code/docs/proofs/continuation-20261022/user-rules-v5/` (PREREG, holdout_de2.json, generate_round5.py, round5_raw.json, freeze_v5.json, audit_round5_make.py, cohort_round5*.json, run_round5.py, Ergebnisse, BEFUND.md).

## Urteil: USER_RULES_V5_UNSAFE

| Prüfsatz | Sätze | v5 | v4 | v3 |
|---|---|---|---|---|
| T1 holdout_de2 (deutsch, vom Autor) | 46 | 25 Fehler in 7 Sätzen | 27/8 | 27/8 |
| T2 Runde 5 (Mistral 7B, Falcon 3 7B, OLMo 2 7B; deutsch) | 100 | 45 in 19 | 52/23 | 63/25 |

- Auf allen bekannten Sätzen hat v5 0 Fehler. „nur wenn“ wurde nie als Lockerung gelesen.
- Neue Formen, die noch fehlen: trennbare Verben („fass … an“), „niemand“, „Schluss mit“, „lässt du bleiben“, „lass die Finger von“, „Erst fragen, dann ändern“, Etiketten.
- Aya Expanse lief nicht im festen llama.cpp und wurde vor der Erzeugung durch Falcon 3 ersetzt (in der PREREG festgehalten).

## Folgerung
Ein fester Wortleser kommt auf offener deutscher Alltagssprache nicht gegen 0 Fehler. Für v6 ist deshalb ein Architekturwechsel vorgesehen:
1. Breites Netz: jedes Halte-, Verneinungs- oder Bedingungssignal und jede Bitte zusammen mit einer Handlung oder einem Ziel führt mindestens zu einer Rückfrage mit Vorschlag.
2. Bestätigung statt Raten: Der Nutzer bestätigt, wie der Leser die Regel verstanden hat. Bis dahin gilt „erst fragen“.
3. Die Grundregel bleibt: Außenwirkung gibt es nur als sichtbaren Vorschlag.



---

## QUELLE: THREAD_HARNESS_HX1_HX3_HX4_20261022.md

# Thread „Harness-Pakete HX1 HX3 HX4“ (2026-10-22)

Basis: Branch claude/project-thread-2p69gl (PR #30). Arbeits-Branch: claude/project-thread-4iqpro (RedMentos/Aii). Code liegt in Git; diese Notiz ist die Drive-Sicherung des Stands.

## Was gebaut wurde (alles SHADOW, Autorität 0, kein Modell)
- WP-HX1 `v13/code/v13/agi/harness.py` + Art `harness` in `agi/self_improve.py` (AG8): feste Liste von 20 änderbaren Zielen (Prompt-Teile answer_rules/digest/task_context/hypotheses/clarify/replay/duplex_handoff/welcome je en/de, tool_hint.list_note, tool_hint.eligibility_note, parser.listarith_extra, recipe.list_result). Nie änderbar: system, conduct, Operator-/Nutzer-Regeln, Verbote, Age, Kanal. Zweites Netz gegen regelschwächende Texte (Wort-Heuristik). Gleicher Regressionsschild, Nutzerfreigabe; HarnessLibrary.apply() nur für freigegebene Vorschläge, rollback() auf Vorversion, harness_hash fürs Generation-Manifest. Kein Live-Pfad liest die Überschreibungen.
- WP-HX3 `agi/experience.py`: Eintrag nur mit Freigabe + bestandenem Schild + Beleg-Datei (sha256). verify() -> STALE bei geänderter Datei, retire() nach Rücknahme, lookup() liefert Daten (DATA_NOT_INSTRUCTION), ablation() mit/ohne.
- WP-HX4 `agi/blind_select.py`: Richter sieht nur Buchstaben + geschwärzten Text, Herkunft per Hash versiegelt, nach Wahl aufgedeckt; zwei Runden gegen Positions-Vorliebe (INCONSISTENT), Fehler = NO_PICK.
- Tests: `v13/code/tests/test_harness_hx.py` (10). Laufzeit-Dateien runtime/runners/store/memory_server unverändert.
- research/HARNESS2_AUSWERTUNG.md aus Branch 1x4aho (PR #23) mit in diesen Branch gemergt.

## Nächster Schritt
WP-HX2: Referenz + Varianten auf derselben Aufgabe mit echten Modellen, erste Probe STEP2 B2-Regel-Zitat; nutzt HX1 (Vorschlag), HX3 (Bibliothek), HX4 (Auswahl). Vorregistrieren vor dem Lauf.


---

## QUELLE: THREAD_REGEL_LESER_V4_20261022.md

# Thread „Regel-Leser Version 3“, Teil 2: v4 + Runde 4 (2026-10-22)

Branch `claude/project-thread-c62rfz`, PR #31. Befund `v13/code/docs/proofs/continuation-20261022/user-rules-v4/BEFUND.md`.

Urteil `USER_RULES_V4_UNSAFE`.
- v4 aus den Runde-3-Fehlern (englische Umgangssprache): bekannte Sätze inkl. Runde 3 → 0 Fehler.
- Runde 4 (versiegelt; Phi-4-mini, Granite 3.3 2B, EuroLLM 9B; 630 roh, 93 geprüft, 67 deutsch): v4 13 Fehler in 6 Sätzen, alle deutsch; v3 und v2 gleich. Englisch 0/26.
- Gefährlichste Form: „Du darfst nur Nachrichten senden, wenn …“ / „erst … wenn ich erlaube“ wird als Lockerung gelesen (Regel entsteht nicht).
- Weitere: „Bleib ab von meinen Notizen!“, „Kein Versand!“, „Kein Kram ohne mein grünes Licht“, „Bitte keine Dateien herunterladen“ (zu eng).
- Nebenbefund 202 übersetzte Sätze: v4 37 Fehler / v3 41 / v2 43.
- Nächster Schritt v5: Bedingung vor Lockerung, deutsche Halte-Formen, Nomen zu Handlungen, Handlung mit eigenem Ziel; Runde 5 aus deutschen Quellsätzen.
Commits: b13d355 Vorregistrierung, 39c4994 Runde 4 versiegelt, ec69532 v4 eingefroren, 9d1f822 Ergebnis.


---

## QUELLE: THREAD_REGEL_LESER_V3_20261022.md

# Thread „Regel-Leser Version 3“ (2026-10-22)

Branch `claude/project-thread-c62rfz` (aufgebaut auf PR #28 / Branch 2gzrwi), Repo RedMentos/Aii.
Befund: `v13/code/docs/proofs/continuation-20261022/user-rules-v3/BEFUND.md`.

Urteil: `USER_RULES_V3_UNSAFE`.
- Runde 3 (versiegelt vor dem Code; Gemma 3 4B, Llama 3.2 3B, SmolLM3 3B; 354 Rohsätze, 149 von Hand geprüft):
  v3 58 Sicherheitsfehler in 19 Sätzen (11 übersehene Verbote), v2 92 in 29.
- Bekannte Sätze (Dev, Holdout, Runde 1, Runde 2): v3 0 Fehler (v2 Runde 2: 20).
- Übervorsicht 31 % der erlaubten Proben.
- Neue Fehlerformen: lässige Bitte als Frage („could you like, not …?“), Verbot ohne Verneinung („put the calculator away“, „stay offline“), „warte bis zur Freigabe“, höfliche Vorliebe mit „you can“, Etiketten-Fälle.
- Neu in v3: Lexikon als Daten mit Beleg (`v13/userrules_lexicon.json`, `extend()` lehnt versiegelte Sätze ab), vorher+zeigen = erst fragen, „rät ab/warnt vor“ = Rückfrage, Ich-Satz an die KI, Verbformen, Vorschlag bei offenen Rückfragen.
- Grundregel unverändert: Außenwirkung nur als sichtbarer Vorschlag.
- Nächster Schritt: v4 mit Grundsätzen statt Wortlisten + versiegelte Runde 4 (neue Erzeuger, deutscher Auftrag).

Commits: 032ce6b Vorregistrierung, df2c55f Runde 3 roh versiegelt, 43fa3d0 v3 eingefroren, danach Audit und Messung.


---

## QUELLE: THREAD_GPT_STAND_PRUEFUNG_RUNDE2_20261022.md

# Thread „GPT-Stand erneut prüfen“ (2026-10-22)

Branch claude/project-thread-2p69gl (Basis 2gzrwi @ 9436eb7), Draft-PR an 2gzrwi.
- GPT 22.10. geprüft + gemergt: c1d6615 (PR #29 Lernpfad-Auditor), 16a0b17 (PR #27 Age-0/Freeze-Notiz), Drive V13_JEPA_AGE0_REVIEW_20261022.md. Alle Aussagen bestätigt (14/14 jepa_weight 0; plen=0 Fehler; nur C3 hat Gewichts-Updates, B1/B2 keine).
- Runde 1 (PR #8) war nie in der Kette, nachgeholt.
- Neu WP-SAFE2 :stillstand (Notaus + Warteschlange + Age-Freeze; bestätigt erst nach Ende des laufenden Vorgangs; bleibt über Neustart; hebt nur eigene Teile auf). Grund: unter :notaus liefen Lernen/Traum/Replay/Training weiter.
- Suite 1727 OK, 5 Skips; Privatsphäre-Scan CLEAN.
- Neue Pakete: WP-AGE0a (späte Selbstkorrektur), WP-AGE0b (Organ-Checkpoint), WP-LP1 (Lernpfad Komponenten-Gradienten).
- Antwort an GPT: v13/code/docs/coordination/CLAUDE_ANTWORT_AGE0_LERNPFAD_20261022.md


---

## QUELLE: Thread Zitierhilfe an, Regeln per JEF (2026-10-21)

﻿Sicherung Thread "Zitierhilfe an, Regeln ohne Halluzination" (2026-10-21)
Branch: claude/project-thread-2gzrwi (RedMentos/Aii). Enthält PR #7, #19, #21 und WP-SAFE1 (:verbot/:notaus aus Thread "Sicherheit: Verbote modellunabhängig").


Nutzerentscheidungen:
- Zitierhilfe AN (Menschen zitieren auch direkt).
- Rückfragen zu Regeln ja, aber kein halluzinierendes Modell entscheidet Regeln: JEF / fester Baustein.
- PR #2, #3, #4 geschlossen (Inhalt schon im Stand).
- Handytest nur wenn er wirklich hilft.
- 20 englische Beispielregeln nicht nötig.
- Ziel: KI tut nichts, wovon der Nutzer nichts weiß, sagt vorher was sie tun würde, legt Verbote nie falsch aus.


Ergebnis:
- v13/userrules.py: fester Leser (kein Modell) für Verbote und "frag mich vorher" aus den eigenen Sätzen. Durchsetzung in der Werkzeug-Policy, feste Hinweise, Befehle :regeln / :regel.
- Messung: eigener Holdout 0 Fehler. Frische Umformulierungen durch 3 lokale Modelle (Runde 2): v1 71, v2 20 Sicherheitsfehler (8 von 57 Sätzen) -> USER_RULES_UNSAFE.
- Schreibende Werkzeuge laufen ohnehin nie automatisch (nur Vorschlag), automatisch laufen nur Rechen-Werkzeuge.
- Fazit: fester Wortleser allein reicht nicht für offene Sprache; Garantie trägt "Außenwirkung nur als Vorschlag" + feste :verbot-Zeilen.
- Befund: v13/code/docs/proofs/continuation-20261021/user-rules/BEFUND.md


Offen: v3 mit den 8 Fehlerformen + frische Runde 3; Merken/Lernen im Gedächtnis durchsetzen; feinere Wirkungsklassen.

---

## QUELLE: V13-Sicherheit-Verbote-Notaus-20261021.md

# Thread "Sicherheit: Verbote modellunabhängig" (2026-10-21)

Git: Branch claude/project-thread-rdesm7, PR #26 (Basis claude/project-thread-0zelvf). Auch im Projektordner-Code eingespielt.

Neu: code/v13/prohibitions.py, tests/test_prohibitions.py (16 Tests), docs/VERBOTE_UND_NOTAUS.md.
Geändert: transaction.py (authorize: Verbote als 1. Schritt + Vorabansage; execute: letztes Tor), agi/tools.py, toolstep.py (kein Schatten-Rechnen bei Verbot), operator.py (:verbot, :notaus).

Befehle: :verbot | :verbot werkzeug <Name> | :verbot art NETWORK | :verbot unumkehrbar | :verbot alles | :verbot weg V1 | :verbot ansage an|aus | :notaus | :notaus aus

Befund:
- Feste Regelprüfung existierte schon (IH-H29 in transaction.authorize, vor der Ausführung, reiner Code). Es fehlten: Nutzer-Verbote, Notaus, Vorabansage für alles. Jetzt da.
- Verbot schlägt Einzelfreigabe; zweite Prüfung direkt vor der Funktion; nur Nutzer ändert; beschädigt = alles gesperrt.
- Neuromod-Veto wirkt nur aufs Lernen (Standard RECORD_ONLY -> keine Wirkung; live nur C6-Regelverstoß als Veto-Quelle).
- Selbst-Unsicherheit hebt live den Rechenaufwand; "nachfragen statt raten" nur Beobachtungsmodus.
- Volle Suite 1597 Tests, nur alter Fehler test_neuro_ledger (auch auf Basis rot).
Offen WP-SAFE2: Verbots-Treffer als Veto-Signal; Nachfrage-Modus messen (mit WP-DS3).

---

## QUELLE: Thread DeepSeek-Kritik 2026-10-21 (WP-DS1, PR 25).md

Thread "DeepSeek-Kritik gegen Stand prüfen", 2026-10-21. Git: branch claude/project-thread-qt2cqv, PR #25 (RedMentos/Aii). Volltext: v13/research/DEEPSEEK_KRITIK_AUSWERTUNG.md.

Bewertung: Neuromodulation existiert (neuromod.py, homeostasis.py, curiosity.py; steuert v.a. Lernen, Verhalten kaum). Active Inference teilweise (Vorhersage vor Handlung da, kein Vergleichstest). Verkörperung echte Lücke (STEP8 gesperrt). Metakognition existiert (agi/metacog.py AG9, selfmodel.py, C3-Unsicherheit AUROC .84). Lernender Balken existiert (callosum.py, b3bridge.py); MoE-Router nur isolierter Kandidat (Z10).

WP-DS1 erledigt: Lab-Sandkasten code/v13/sandbox.py, Vorregistrierung vor Lauf (Commit 3f3cb09), Seeds 100..119, alle 4 Hypothesen PASS.
Fehler@600: Zufall .34, Überraschung .61 (94% am Rausch-Fernseher), Neuheit .17, Lernfortschritt AG5 .16 (bester), Informationsgewinn .21, +Hungerziel .23 (Hunger .05 bester, neues Objekt nur 7/20).
Offen: WP-DS2 kombinierte Policy (Lernfortschritt + Ziel + Neuheits-Kanal), WP-DS3 Unsicherheit -> Werkzeug-Nachprüfung / "unsicher" sagen.

---

## QUELLE: V13-Z5c-Koalition-Aktualitaets-Term-20261021.md

# WP-Z5c Aktualitäts-Term für Notizen in der Koalition (2026-10-21)

Thread „Koalition Aktualitäts-Term“, Branch claude/project-thread-8zhj41 (auf Z5b, PR #16), Draft-PR folgt im Repo RedMentos/Aii.
Beleg: v13/code/bench-results/z5c-recency-20261021/ (PREREGISTRATION.md, README.md, z5c.json, run.log).

Schalter focal_note_recency (0/1, Standard 0): Notizen mit gleichem Schlüssel bis auf Kalenderwörter/Zahlen = Versionen; neueste gespeicherte +0,10 (recency), ältere -0,30 (superseded).

Lauf: Z5b-Aufgaben, 3 Saaten (11,12,13) x 2 Läufe x 60 = 360 Turns, Platzgrenze bindet immer, kontrafaktische Koalition ohne Term aus denselben Kandidaten (Treue 360/360).

Mechanismus: update neueste Notiz in Koalition 1,00 statt 0,90, veraltete 0 statt 0,95; combine benötigte 0,75 statt 0,63.
Antworten: mit Term 93/360, ohne 90, Voll-Kontext 97, Retrieval 98, ohne Kontext 64. Mit vs ohne 24:21 p=0,77; vs Voll-Kontext 30:35 p=0,62. Rauschband 2.
Verdikt: Term hilft FAIL, schlägt Voll-Kontext FAIL, Gate G-FOCAL-CAPACITY-003 bleibt PARTIAL, Schalter bleibt aus.
Befund: bei update schlechter als Voll-Kontext (3:21); bei schmaler Koalition antwortet das Organ oft nur "2" (33/82 Turns).
Nächster Schritt: Ersetzungs-Kette sichtbar im Kontext statt veraltete Notizen wegzulassen; Ursache der "2"-Antworten prüfen.
Cloud-Hinweis: Container wird im Leerlauf zurückgesetzt; lange Läufe als überwachte Hintergrund-Aufgabe mit Zwischenspeicher.



---

## QUELLE: THREAD_B3_L1_ESCALATE_APOLOGIZE_20261021.md

# Thread "B3 L1 escalate apologize" (2026-10-21)

Branch claude/project-thread-yub2lf (stacked on c122qc / PR #20), draft PR #22.

## Cause (exploratory diagnosis on attempt-4 states)
escalate/apologize need a receiver-private fact (capacity/client, 100 % decodable from receiver state) combined with U/F. The bridge read as an additive residual on the FROZEN NO_MESSAGE readout, so the fact weights could not be rescaled to the message. With the true U/F that costs 8.2/9.3 points (on action it helps, -5.5). The same message with a jointly refit readout gains +8.0/+5.5 points (5/5 seeds). 72-78 % of errors fall within 1 of the threshold.

## Fix
Bridge(recv_cond=dim) + Bridge.refit_readout (default off, byte-identical; gate closed = old readout).

## Attempt 5 (preregistered 9d52f49, fresh seed 20261105, new B1/B2 states, gate unchanged)
- escalate 90.5 vs attr words 84.7 / label 78.7 / SCALAR 89.2: canon L1 PASS (strict FAIL n.s.)
- apologize 89.0 vs attr words 88.5: FAIL (n.s.)
- action replication 86.7 vs label 83.5: FAIL (n.s.). The attempt-4 action PASS depends on the seed.

Consequence: L2 prefix SHADOW is allowed only for private/escalate. Next: WP-Z4d L1 robustness on 2 more fresh seeds, then L2 for escalate.
Evidence: project folder v13/bench-results/b3-l1-escapo-diagnose-20261021/, v13/bench-results/b3-l1-v5-20261021/ (states.npz only there).


---

## QUELLE: THREAD_Z2D_B2_REGELZITAT_20261021.md

# Thread „B2 zitiert Regel selten“ — WP-Z2d (Code: z2c), 2026-10-21

Branch `claude/project-thread-0fckhc` (Basis `s439sv` = Z2b), Draft-PR #21. Prereg `8cc006d` (vor Inferenz), Ergebnis `058e8c7`.

## Ursache
B2 kennt die alte Regel, schreibt sie aber um oder zitiert den Aufgabentext. Von 384 Z2b-B2-Angeboten (RULE/SPLIT) trugen nur 115 die volle Regel; 110 scheiterten an einer Umschreibung bzw. kaputten Kopie des richtigen Satzes, 65 zitierten den aktuellen Aufgabentext.

## Änderung
Schalter `b2_quote_select` off (Standard) | anchor | pointer. Kettenglied `integrated_candidates.b2_quote_select`, Tests `test_b2_quote_select.py`.

## Ergebnis (CQ/CQA/CQP × Seeds 17–19, 630 Zeilen)
- B2-Regelquote: Kontrolle .167, Anker .542 (teilweise), **Zeiger .969 (FIXED)**
- 0 falsche Regelwerte, 0 falsch festgelegte Entscheidungen
- Zeiger: zwei Körper .881 vs. b1_only .581 (+.30, CI > 0, jeder Seed), 27/30 exakt
- STEP2 bleibt formal FAIL (Kriterium 3, Ein-Körper-Kontrolle offen)

## Offen
Nutzerentscheidung: Zeiger einschalten; vorher live-`analyst_context` reparieren. Neues Prereg mit Ein-Körper-Kontrolle und längeren Regeln. Merge-Hinweis: Thread 4ttld7 (Kettenglied body_question) beim Zusammenführen hintereinander anwenden.
Befund: `v13/code/docs/proofs/continuation-20261021/step2-z2c-b2-rule/BEFUND.md`


---

## QUELLE: V13-Z4b-L2-Prefix-action-20261021.md

# WP-Z4b B3 L2-Prefix-SHADOW nur private/action — 2026-10-21

Thread „Z4b L2 nur für action“, Branch claude/project-thread-c122qc (auf PR #17), Draft-PR #20. Commits e0d6cd5 (Präregistrierung, vor Messung), df5c6cc (Ergebnis).

Aufbau: 64-B-Nachricht der L1-Brücke (Versuch 4, exakt reproduziert, Digest 3c75aad1…) -> Ausrichtung in den Eingabe-Embedding-Raum von Qwen3.5-0.8B Q4_0 -> Kalibrierung auf native Token-Statistik (Normverhältnis 1,00) -> 4 Prefix-Slots über llama.cpp b10964 batch.embd -> Auslesen nur über die eigenen Text-Tokens des Empfängers (eingefrorenes Rückgrat).

Ergebnis (5 Seeds): Prefix 80,2 % | aus 41,5 | vertauscht 37,5 | zufällig 37,8 | EXACT-Text 76,5 | Label-Wort-Text 81,5 | Attribut-Wörter 74,8 | L1 (Adapter) 90,0.
Urteil: L2 FAIL (einzig fehlendes Kriterium: Nutzen vs. Label-Wort −0,017). Explorative Variante EXACT_ALIGN 77,5 % ebenfalls FAIL.
Nebenbefunde: L2 9,8 Punkte unter L1; alter Themen-Kopf fällt mit Prefix 100 % -> 40 % (neu trainiert 0 Verlust).
Folge: B3 bleibt L1_shadow, L3 gesperrt, Autorität 0, Runtime unverändert. Neuer L2-Versuch nur auf Aufgabe ohne billiges Label-Wort (vorher L1 auf escalate/apologize bestehen).

Belege: Repo v13/bench-results/b3-l2-prefix-20261021/ (README, report.json, run.log); Projektordner gleich. Werkzeug code/scripts/native/b3_prefix_embd.cpp, Skript code/scripts/b3_l2_prefix_bench.py, Gate b3bridge.l2_gate.


---

## QUELLE: THREAD_Z2C_B1_FRAGE_SCHALTER_20261021.md

# Thread „B1-Frage als Schalter“ (WP-Z2c), 2026-10-21

Branch `claude/project-thread-4ttld7` (Basis Z2b `s439sv`), Draft-PR #19, Commits 061d778 (Code+Tests+Runner, vor Lauf) und 915ff6d (Ergebnis).

- Neue Schalter `body_question_b1` / `body_question_b2` (Standard '' = aus, live unverändert). Feste Frage als jef_query (FILL_GAP) an jedes Körper-Angebot ohne Re-Entry-Fokus. Kettenglied integrated_candidates.body_question, Tests test_body_question.py. Suite 1608, nur Altfehler test_neuro_ledger.
- Bestätigung Seed 14 (echte Modelle, Linux): Schalter beide both_exact .592 (ohne .375, Z2b-Patch .675); nur B1 .450; b1_only .275 -> .575; 0 falsch in 140 Werkzeug-Zeilen.
- Frage ist STEP2-spezifisch -> bleibt aus. Offen: Nutzerentscheidung, allgemeine Chat-Frage ungemessen, Paket „B2 liefert Regel-Zitat“, Seed-Bug cognition.offer.
- Rohdaten: Projektordner v13/bench-results/step2-z2c-switch-20261021/; Befund im Repo docs/proofs/continuation-20261021/step2-z2c-switch/BEFUND.md.


---

## QUELLE: V13-Z5b-Koalition-Platzmangel-20261021.md

# WP-Z5b: Fokus-Koalition unter echtem Platzmangel (G-FOCAL-CAPACITY-003), 2026-10-21

Thread „Z5b Koalition mit Platzmangel“, Git-Branch claude/project-thread-bn7n5k (Basis: Z5-Branch hmopsm), Draft-PR #16 (RedMentos/Aii).
Beleg im Repo: v13/code/bench-results/z5b-capacity-20261021/ (PREREGISTRATION.md, README.md, z5b.json, Logs); Skript v13/code/scripts/z5b_capacity.py; Tests v13/code/tests/test_z5b_capacity.py. Auch im Projektordner v13/code/ gespiegelt.

## Aufbau
60 neue Aufgaben (update / combine / correction / distract, Saat 11), je 6 gespeicherte Notizen (alle abgerufen, memory_top_k 6), Effort max, 4 Plätze, 5 Läufe, echte Modelle (C3 LFM2.5-350M, B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B), Cloud-CPU. Vorregistriert vor dem Lauf. Wiedergabe-Treue 300/300.

## Ergebnis
- Platzgrenze greift jetzt in 300/300 Turns (9 Kandidaten für 4 Plätze; in Z5 nie). 11 Verdrängungen.
- Bestanden/300: ausgeliefert 68, Koalition als Engpass 60, Voll-Kontext 54, feste Slots 55, nur Retrieval 64, ohne Kontext 47.
- Koalition vs. Voll-Kontext 33:27, p = 0,52, Vorsprung 1,2 je Lauf < Rauschband 4 → „schlägt Voll-Kontext“ FAIL. Nicht schlechter als Retrieval und feste Slots.
- Eigenschaften 1, 2, 3, 5, 6, 7 gemessen; 4 (Aufnahme nur über Salienz) nie → G-FOCAL-CAPACITY-003 bleibt PARTIAL.
- Nach Art (ausgeliefert / Koalition / voll / fest / Retrieval / ohne): update 0,23/0,16/0,21/0,15/0,07/0; correction 0,25/0,16/0,05/0,01/0,53/0; distract 0,43/0,48/0,45/0,57/0,25/0,63; combine überall 0.

## Befunde
1. Unter echtem Platzmangel ist die Koalition nicht besser als „alles in den Kontext“ (Rauschen).
2. Die Koalition behält oft die falsche Notiz (correction: Retrieval 0,53 vs. Koalition 0,16), weil die Priorität keinen Term für Aktualität/Ersetzung hat.
3. Im ausgelieferten Pfad gehen abgerufene Notizen an der Koalition vorbei in die Antwort; die Koalition filtert nur Körper-Angebote.
4. Die Auswahl spart 44 % Kontext ohne messbaren Verlust (Ressourcen-Argument, kein Gate-PASS).

## Abweichungen
Lauf 5 brach zweimal ab (Container-Neustart; ein Wiedergabe-Arm überschritt das native Kontextfenster). Fehlerbehandlung repariert (Skip statt Absturz, keine Regeländerung), Lauf 5 vollständig neu, ohne Skip.

## Nächster Schritt
Aktualitäts-/Ersetzungs-Term für Notizen in der Fokus-Priorität, neu vorregistrieren, dieselben 60 Aufgaben gegen dieselben Kontrollen. Aufgaben für Eigenschaft 4 (salienter Kandidat unter der Prioritätsschwelle).


---

## QUELLE: THREAD_Z2B_STEP2_SEEDS_20261021.md

# Thread „Z2b STEP2 mit mehreren Seeds“ (2026-10-21)

Branch `claude/project-thread-s439sv` (Basis: Z2-Branch hsm0ga), Draft-PR #18. Vorregistrierung f5b9d03, Ergebnis f7d9611.
Belege: v13/code/docs/proofs/continuation-20261021/step2-z2b-seeds/ (PREREG.md, BEFUND.md), v13/code/bench-results/step2-z2b-seeds-20261021/. Volle STEP2-Berichte liegen im Projektordner v13/bench-results/step2-z2b-seeds-20261021/.

## Was gemacht wurde
- Arme C/D (wie Z2) und CQ/DQ: dazu eine feste gezielte Frage über jef_query, nur in der aktuellen Runde. B2 soll die früheren Regeln zitieren, B1 die Optionswerte. Alles mal Seeds 14/15/16, ergibt 840 Zeilen plus Werkzeug-Replay. Echte Modelle, Linux-Cloud, kein Redmi.
- Fund vor dem Lauf: Die Körper-Angebote haben cfg['seed'] nie benutzt (immer Seed 13). Das ist im Skript behoben, der Live-Code ist unverändert.

## Ergebnis
- Z2B_DIVERGENCE_NOT_SUPPORTED: Zwei Körper liegen bei .611, B1 allein bei .592, Differenz +.019 (CI −.075 bis +.106). Ein Körper mit zwei Zuständen ist gleich gut.
- Z2 war Rauschen: C both_exact schwankt über die Seeds zwischen .308 und .450. Zwischen Qwen und LFM als B2 zeigt sich kein klarer Unterschied.
- Die gezielte Frage hilft klar: +.23 (CI +.12 bis +.34). B1 liefert die Optionswerte dann in 170 statt 63 von 210 Zeilen.
- 0 falsch festgelegte Entscheidungen.
- Engpass ist jetzt B2: Es zitiert die alte Regel nur in etwa ¼ der Zeilen.

## Offen
(a) Nutzerentscheidung, ob die gezielte B1-Frage als Schalter (aus) in den Live-Pfad kommt. (b) Paket „B2 liefert das Regel-Zitat“. (c) cognition.offer soll seed=cfg['seed'] übergeben.


---

## QUELLE: THREAD_R_B3L1_V4_UND_SCHLUESSELTRENNUNG_20261021.md

# Thread „Nächste Pakete R“ – 2026-10-21

Branch `claude/project-thread-8hlx74` (Basis `claude/project-thread-0zelvf`), Draft-PR #17. Commits: eaf49b7 (Prereg B3 v4), f2f6976 (Fix + Prereg v3), f09ef8b (nativer Scope-Fix + Prereg v3b), ffc3d8e (Ergebnisse + Doku).

## WP-Z4 B3 L1 Versuch 4 – L1 PASS auf private/action
- Frische Saat 20261021 (600 Zeilen, 0 Überschneidung mit Versuch 3), neue B1 LFM2.5-1.2B / B2 Qwen3.5-0.8B Zustände (b10964), aux-Brücke (U,F nur Training), Gate unverändert.
- action: LATENT 90,0 % (ohne aux 80,0; SYMBOLIC 81,5; Attribut-Wörter 76,7; SCALAR 85,2) -> Kanon-L1 PASS (Rollen-Verlust 0, OOD 1,3 %, Reload bitgleich). escalate 83,0 / apologize 85,0 -> FAIL gegen Attribut-Wörter. Strikt gegen SCALAR FAIL.
- Folge: nur L2-Prefix-SHADOW für private/action erlaubt (nächstes Paket Z4b); Autorität 0, Runtime unverändert.
- Belege: Projektordner v13/bench-results/b3-l1-v4-20261021/ (inkl. states.npz 231 MB), Git ohne states.

## Native Firing-Diagnostik / WP-T9 v3 – Schlüsseltrennung
- Ursachen falschen Feuerns: gemeinsame Guard-Wörter („favourite“) und Guard auf ganzem Prompt (Exakt-Block öffnet fremde Slots).
- Fix (Standard aus): guard_distinct + guard_vocab, guard_scope='last_user' (torch + nativ; V13SMEM1 Feld 6 = 2+Marker).
- v3: fremdes Feuern 24->17 Zeilen, auf Faktfragen 4->0. Nativen Fehler gefunden (Scope nur im Cache-Präfix), behoben, v3b: combined 84->17, selektiv 25->16.
- KEY_SEPARATION_SUPPORTED; SELECTIVE_DOES_NOT_WIN (2:5 gegen exakt, vorher 2:9; Verluste = falsche Spur-Werte auf Paraphrasen).
- Belege: v13/bench-results/selective-delivery-v3-20261021/ (+ v3b/).

## Sonst
- b3bridge.save übernahm alte Revisionen -> behoben + Test.
- 19 fehlende §102-Belegordner ins Git, test_neuro_ledger grün. Suite 1591 Tests.
- Zwei Läufe wurden durch einen Container-Neustart abgebrochen (vor Ergebnissen), danach neu gestartet.

## Offen
- Z4b: L2-Prefix-SHADOW für private/action (vorregistrieren).
- Schnelle Spur: Wertqualität auf Paraphrasen (z. B. Paraphrase-Kontexte beim Schlüssel-Schreiben).


---

## QUELLE: V13-Z5-Fokus-Koalition-20261021.md

# WP-Z5 Fokus-Koalition gegen §99-Kontrollen (2026-10-21)

Git: RedMentos/Aii, Branch claude/project-thread-hmopsm @ db31f9c, PR #15 (Basis claude/project-thread-rxq188).
Belege: v13/code/bench-results/z5-focal-controls-20261021/ (PREREGISTRATION.md, README.md, z5.json), Skript scripts/z5_focal_controls.py, Tests tests/test_z5_focal_controls.py.

Aufbau: 60 WP-T3b-Aufgaben x 5 Läufe, echte Modelle, Effort max. Kontroll-Arme im selben Turn aus denselben Angeboten an dasselbe Organ (C5 wählte B1 165x, B2 135x, nie C3). Wiedergabe-Treue 300/300.

Bestanden (300): Koalition 186, Voll-Kontext 183, feste Slots 193, Retrieval 184, ohne Hypothesen 195.
Gepaart: vs Voll 17:14 p 0,72; vs feste Slots 15:22 p 0,32; vs Retrieval 32:30 p 0,90. Rauschband 7.
Verdikt: schlägt Voll-Kontext FAIL; nicht schlechter als Retrieval/feste Slots. G-FOCAL-CAPACITY-003 bleibt PARTIAL.
7 Eigenschaften: Wettbewerb 201/886 abgelehnt, Re-entry 289/300, Quellbindung 685/685, Halten/Wiederherstellen 886/886 ja. Kapazitätsgrenze, Ersetzung, Interrupt 0 (max. 3 Kandidaten bei 4 Slots).
Nach Art: Hypothesen helfen bei summary (0,57 -> 0,71), schaden bei compare (0,33 -> 0,12).
Lauf 5 nach Sitzungsabbruch komplett neu gefahren.
Nächster Schritt: neue Vorregistrierung mit Kapazitätsdruck (Ablenker-Erinnerungen, mehrere Turns, Embedding-Retrieval).


