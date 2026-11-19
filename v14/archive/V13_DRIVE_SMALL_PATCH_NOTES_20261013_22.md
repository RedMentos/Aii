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



---

## QUELLE: THREAD_Z2_STEP2_B1_DETAIL_20261021.md

# THREAD Z2 STEP2 mit B1-Detailinfo (2026-10-21)

Git: RedMentos/Aii Branch claude/project-thread-hsm0ga @ 6a8937d (Prereg bdaafc2). Volle Berichte: Projektordner v13/bench-results/step2-z2-timescale-20261021/.

# Befund WP-Z2: STEP2 mit Information, die nur B1 hat (2026-10-21)

Vorregistrierung PREREG.md (Commit bdaafc2, vor Inferenz gepusht). Linux-Cloud x86_64, 4 CPUs, kein Redmi.
Modelle/Runner byte-gleich mit 13.10./20.10.: B1 LFM2.5-1.2B bb741ebb, B2 Qwen3.5-0.8B 57d19977, C3 LFM2.5-350M 3d10b6ab, llama.cpp b10964 79e31218.
5 Arme x 70 Zeilen, alle RECORDED, 0 Strukturfehler; dazu Werkzeug-Replay je Arm (350 Zeilen).

## Ergebnis: Z2_DIVERGENCE_NOT_SUPPORTED (Gate FAIL)
1 C both_exact > bester Einzelkörper: .325 vs b1_only .333 -> nein
2 B1 und B2 gewinnen je eine Episode: ja
3 komplementäre Fehlerprofile (>= .25): Optionsfelder b1 .57 / b2 .37, Regelfelder beide .10 -> nein
4a > gleiches Modell gleiche Policy: .325 > .308 -> ja
4b > gleiches Modell nur anderer Prompt (D prompt_only_dual): .325 < .425 -> nein
5 Struktur: ja
§99 "zwei Körper lohnen": nein (ein Körper + zwei Zustände .367 >= zwei Körper .325).

## Sekundär
- Neuer Schalter b1_recent_source_chars (0 = aus): B1 behält exakte Quelle der letzten Runde. Damit liefert B1 Optionswerte als verifiziertes Zitat 27/70 (vorher 0).
- Erstmals exakte SPLIT-Entscheidungen, aber nur im Ein-Körper-Arm D (both_none 3/6); Zwei-Körper-Arm 0/6.
- 0 falsch festgelegte Entscheidungen in 350 Werkzeug-Zeilen; ohne Werkzeug 0 exakt.
- Ohne Zitat-Kontext (Arm E) 0 verifizierte Zitate.

## Pannen
- Arm C Nachbearbeitung brach ab (altes Feld 'prior'), Zeilen weiterverwendet.
- Arm D Versuch 1: Hash-Wächter kannte shared_body nicht, alle Vorbereitungen ERROR; korrigiert, neu gelaufen, Versuch 1 aufbewahrt.

## Empfehlung
Schalter bleibt aus. Nächstes (neu vorregistrieren): Rauschband mit 3-5 Seeds für C/D; gezielte JEF-Rückfrage "zitiere Regel/Optionen"; Qwen- vs. LFM-B2 als gebundene Modellfrage.


---

## QUELLE: THREAD_Z3C_ERWEITERBARER_PARSER_20261021.md

# Thread Z3c Erweiterbarer Regel-Parser (2026-10-21)

Branch claude/project-thread-x1etmj (Basis a9je9s / PR #12), Draft-PR #13. Beleg im Repo:
v13/code/docs/proofs/continuation-20261021/z3c-extensible-parser/ (PREREG.md, BEFUND.md, parser_v2.py, lexicon.json, z3c_run.py, Tests, run/).

Reihenfolge: 62c5c7f Vorregistrierung + versiegelter Autor-Holdout -> dac892a Parser eingefroren -> cc34bda B1-Runde 1 + Audit -> 92d87ce Nachtrag A1 -> 40e0618 Runde 2 + Audit -> afde1f9 Ergebnis.

Urteil: PARSER_V2_CARRIES_AUTHOR_ONLY; sekundaer C3_TRAINING_NOT_NOW.
- kanonisch 39/39, Z3b-Paraphrasen 39/39 (vorher 0.154), Autor-Holdout 0.912 exakt, 1/57 falsch (Koeder "Nobody has decided whether the budget should be 102 euros.").
- Modell-Holdout (B1 formuliert um): nur 22/39 bedeutungsgleich -> unterbesetzt; 0.318 exakt, 0 falsch. Luecken: Lokal-Wortschatz (nearby, area, anywhere, "requirement is true"), "tops out".
- C3-Satzprobe: 57/60 true, nie null bei Koedern -> kein Trainingssignal.
Naechstes: neues Paket mit Lexikon-Erweiterung + neuem fremden Holdout (Nutzer-Saetze oder staerkeres Cloud-Modell). v2 nur SHADOW.


---

## QUELLE: THREAD_Z3B_PARSER_VS_C3_20261021.md

# Thread „Z3b Parser statt C3-Leser“ — 2026-10-21

Branch `claude/project-thread-a9je9s` (Basis xiuwmf/Z3), Commits 23eb0df (Prereg vor Lauf), 50e239f (Ergebnis). Beleg im Repo und Projektordner: `v13/code/docs/proofs/continuation-20261021/z3b-parser-paraphrase/`.

Frage: Kann C3 (350M) Regeln besser lesen als ein fester Parser? 39 kanonische + 39 umformulierte Aufgaben (gleiche Werte), 3 Seeds, 468 C3-Aufrufe, Schwellen vorab ≥80 % exakt, ≤5 % falsch.

Urteil: PARSER_SUFFICIENT_NO_C3_GAIN; sekundär BOOL_PARSER_FIX_CONFIRMED.
- Parser liest local_only, C3 nur Zahlen: kanonisch 117/117 exakt, 0 falsch.
- C3 gibt local_only immer true zurück (234/234), auch bei verneinten Umformulierungen.
- Auf Umformulierungen kein C3-Arm ≥ 0.80; einziger Gewinn (0.41 statt 0.15) mit 7.7 % falscher Wahl.
- Folge: Ja/Nein-Regeln nie vom C3 lesen lassen, auch nicht als Rückfall. Neue Wortformen brauchen erweiterbaren Parser oder Lese-Training.


---

## QUELLE: THREAD_STEP2_ENGPASS_20261021_ENDE.md

# Thread „STEP2-Nutzen Engpass“ – Stand 2026-10-21 (Ende)

- Branch `claude/project-thread-dq33gk` @ 4898f7a, PR #7 aktualisiert. Suite 1609 OK.
- Zitat-als-Zeiger-Schalter: CONTEXT_SUPPORTED (Transport 7→23/30). Fehler behoben: mit Schalter an brach jeder echte Chat-Turn in analyst_context ab.
- Ganzer Live-Turn mit meiner Eignungs-Variante: NOT_SUPPORTED (Rezept 23/24 richtig, C3 ignoriert Ergebnis).
- Thread Qs Fassung (Antwortsatz + Broker-Korrektur, TOOL_LIVE_SUPPORTED 22→32/60, sichtbar 53/60) zusammengeführt und gilt.
- STEP2 bleibt UTILITY_FAIL (B1 ohne eigene Info).
- Offen: Nutzerentscheidung Schalter einschalten; Handy-Paket mit Schaltern+Werkzeug; STEP2-Fixtures mit B1-eigener Info (WP-Z2).
- Handy-Testliste: v13/HANDY_TESTLISTE.md.


---

## QUELLE: THREAD_Q_ELIGIBILITY_LIVE_TURN_20261021.md

# Thread „Nächste Pakete Q“ – 2026-10-21

Paket: Eignungs-Werkzeug `eligibility` im echten Antwort-Turn (C5/IH-H29, SHADOW zuerst).
Git: Branch `claude/project-thread-hzzqh4`, Draft-PR #11 (Basis `claude/project-thread-0zelvf`), Commits a94f91c (Code + Vorregistrierung, vor dem Lauf gepusht), f2d99b3 (Ergebnis).

Ergebnis (60 frische Aufgaben, C3 LFM2.5-350M, Linux-Cloud, Alters-Recht nur für die Messung ersetzt):
- Antworttext richtig 22 → 32 (p .006), falsch festgelegt 33 → 23, Rezept 0/60 falsch → TOOL_LIVE_SUPPORTED
- mit Broker-Korrektur sichtbar richtig 53/60 → TOOL_SHOWN_SUPPORTED
- Schwächen: fehlende Regel sagt C3 nie selbst (nur Korrektur), geänderte Regeln liest C3 oft alt (override 5/15) → sichere Ablehnung.

Achtung: Thread „STEP2-Nutzen Engpass“ (dq33gk) hat parallel eine eigene Fassung gebaut; beim Zusammenführen toolstep.py / agi/eligibility.py / tests/test_eligibility_live.py abgleichen.
Runtime-Änderungen nur als Kettenglied in scripts/integrated_candidates.py, sonst brechen ~60 hash-gebundene Tests.
Befund: v13/code/docs/proofs/continuation-20261021/eligibility-whole-turn-q/BEFUND.md (Git + Projektordner).
Nächster Engpass: Lesen geänderter Regeln. Einschalten bleibt Nutzerentscheidung.


---

## QUELLE: THREAD_Z3_C3_KONSUMENT_20261021.md

# Thread „Z3 C3-Konsument isolieren“ — 2026-10-21

Branch claude/project-thread-xiuwmf (Basis rxq188), Commits: Prereg (vor Lauf), fe814d3 Ergebnis. Draft-PR gegen rxq188.
Beleg im Git: v13/code/docs/proofs/continuation-20261021/z3-c3-consumer/ (PREREG.md, BEFUND.md, registration.json, run/report.json, run/rows.json.gz).

Aufbau: 39 private Fixtures × 3 Seeds × 7 Arme, gleiche Exakt-Quellen; Modelle byte-gleich zum Pilot 20.10.; Linux-Cloud.
Urteil (vorregistriert): NO_CONSUMER_PATH.
- C3 direkt 0/117 exakt, immer UNKNOWN (auch mit fertigem Werkzeug-Satz), 0 falsch.
- B1 0.13 / B2 0.27 exakt, 72 % / 63 % falsche Festlegung (Positions-Bias A).
- C3 liest + Eignungs-Werkzeug strict: 0.54 exakt, 0 falsch. C3 liest Zahlen 117/117 richtig, local_only immer true.
- v2 ohne strict: 3/18 Kontrollen falsch festgelegt -> strict vor Einschalten des Live-Pfads.
- Nur Werkzeug: 1.00.
Nächstes: Z3b (Bool-Regeln deterministisch, Paraphrasen-Kohorte), neue Registrierung.


---

## QUELLE: THREAD_Z1_GATE_EHRLICH_20261021.md

Thread "Z1 STEP2-Gate ehrlich" 2026-10-21. Git: RedMentos/Aii Branch claude/project-thread-61we5j (fae26f4, 930fe5d), Draft-PR #9 -> claude/project-thread-rxq188. Projektordner: v13/code synchronisiert, ROADMAP WP-Z1 = ERLEDIGT.

WP-Z1 Gate-Ehrlichkeit (kein Modelllauf)
- Problem: gate-graph STEP2 = GREEN, weil nur all70_rowchecks_pass (Harness) geprüft wurde; Ergebnis ist UTILITY_FAIL (canonical_gate_pass false).
- STEP2 geteilt: STEP2_HARNESS (GREEN), STEP2_EXIT (§96: Komplementarität FAIL, B1/B2 je eine Episode FAIL, RSS-Budget UNMEASURED, Observer-Latenz Cloud 3,8 s PASS) -> EVIDENCE_NOT_PASSING.
- blueprint-Block: Blueprint-Kriterien für STEP2_EXIT, STEP5, alle zehn §100-Gates an gemessene Werte gebunden. Neuer Status CRITERIA_UNMEASURED; gemessenes FAIL nie mehr hinter PARTIAL.
- measure_suite: §29-Tabelle berechnet (specs/properties29.json): 3 erreicht, 15 teilweise, 6 fehlen (Hand-Einschätzung 8/14/2).
- Gates Projektstand vorher 8 GREEN/1 ENP/10 PARTIAL, jetzt 7 GREEN/5 ENP/1 CRITERIA_UNMEASURED/7 PARTIAL.
- Tests: Gate/Authority 18/18; volle Suite 1584, 1 bekannter FAIL test_neuro_ledger.
- Offen: STEP2-RSS-Budget vorregistrieren (mit Z2).
Befund: v13/code/docs/proofs/continuation-20261021/z1-gate-ehrlich/BEFUND.md


---

## QUELLE: THREAD_STEP2_ENGPASS_TEIL2_20261021.md

# Thread „STEP2-Nutzen Engpass“, Teil 2 — 2026-10-21

Nutzerziel (21.10.): AGI = wissenschaftlich, psychologisch, moralisch fundiertes System, das Menschen nicht schadet; Gehirn als grobes Basismodell; holt später selbst Module nur mit bewusster, unmanipulierter Erlaubnis und lernt daraus. Weiterarbeiten, Handy-Tests parallel nach Liste.

Git: RedMentos/Aii Branch `claude/project-thread-dq33gk` (PR #7, Basis `claude/project-thread-0zelvf`), Prereg `298b6d7`, Ergebnis-Commit danach.

## Eignungs-Werkzeug im Live-Antwortpfad
- `ToolStep._propose_eligibility`: Frage nach Option A/B unter Projektregeln → C3 liest nur typisierte Werte aus Quelle + verifizierten Body-Zitaten → deterministisches Rezept entscheidet → C5-Kandidat.
- Nur nach Freigabe `:growth enable eligibility`; Age 0 = SHADOW (berechnet, verglichen, nicht gezeigt).
- Vorregistriert gemessen auf 70 STEP2-Belegen: LIVE_PROMPT_SUPPORTED, 55/70 exakt, „Regel behalten“ 25/30, 0 falsch. Alle Fehlschläge sind ehrliche UNKNOWN-Verweigerungen.

## Handy-Testliste
`v13/HANDY_TESTLISTE.md` im Projekt: 1. `bash WERKZEUG_TESTEN.sh` (ZIP export/V13-Werkzeug-Handy-20261020.zip), 2. RAM-Messung `scripts/ram_budget_bench.py`, 3. `bash TESTEN.sh --quick`, 4. STEP2 am Handy erst mit neuem Paket.

## Offen
Ganzen Live-Turn mit Werkzeug + Antworttext messen; dann Schalter + Werkzeug gemeinsam einschalten (Nutzerentscheidung); neues Handy-Paket; STEP2-Fixtures mit B1-eigener Information.



---

## QUELLE: THREAD_GEGENSEITIGE_PRUEFUNG_20261021.md

# Thread „Gegenseitige Prüfung mit GPT“ — 2026-10-21

Nutzerwunsch: Claude und GPT prüfen sich gegenseitig.

Git: Branch `claude/project-thread-g2f277` @ 58c5d1a, Draft-PR #8 (Basis `claude/project-thread-0zelvf`).
Projektordner: v13/PRUEFUNG_CLAUDE_FUER_GPT.md (volles Protokoll + Checkliste für GPT), AGENTS.md, UEBERGABE, ROADMAP aktualisiert.

## Runde 1: Claude prüft GPT bis a1973d4 (PR #2–#4)
- Laufzeitcode (listarith, toolstep, tools, transaction, broker, toolforecast): korrekt; Werkzeuge standardmäßig aus, nur mit Nutzer-Erlaubnis; Vorhersage bleibt SHADOW.
- Gate-Angaben ehrlich: canonical_gate_pass=false, phone_measured=false, FAILs bleiben FAIL. Urteilsname CONTINUAL_LEARNING_CONFIRMED (stammt von Claude M) klingt größer als gemessen -> immer mit „SHADOW, zwei Werkzeugwelten“ nennen.
- GPT hatte zwei echte Claude-Fehler gefunden (Vorzeichen im list_arith-Wächter; M-Analyse akzeptierte 4/21 Zeilen). Beide inzwischen drin.
- Privatsphäre: neues scripts/public_repo_privacy_scan.py, alle GPT-Branches CLEAN; „private“ STEP2-Fixtures sind synthetisch.
- PR #3: Code-Kandidaten in a1973d4 enthalten; 51 Review-Belege nur auf dem PR-#3-Branch.

## Behoben
- list_arith-Zahlen-Wächter zählt Vorkommen (doppelt gelesener Posten: 800 statt 500 lief durch).
- 19 Belegordner bench-results/*-20261012 fehlten im Git -> Suite auf frischem Checkout war 1 FAIL.

## Tests (v13/code, PYTHONPATH=.:tests python -m unittest discover -s tests)
- GPT a1973d4: 1439 OK, 5 Skips
- Basis cc527f0: 1582, 1 FAIL (fehlende Belege)
- nach Runde 1: 1585 OK, 5 Skips

## Offen
- GPT: Runde 2 (Claudes Arbeit prüfen), Checkliste Abschnitt 4 in PRUEFUNG_CLAUDE_FUER_GPT.md.
- list_arith: ausgelassener Posten wird nicht erkannt; „Total cost: 65“ zählt als Posten (braucht Messung).
- Nutzer: alte GPT-Draft-PRs #2–#4 schließen oder offen lassen.


---

## QUELLE: V13-Zielabgleich-20261021.md

Sicherung Thread „Ziele gegen Blueprint abgleichen“, 2026-10-21. Git: RedMentos/Aii Branch claude/project-thread-rxq188 @ 1c27c2a (v13/ZIELABGLEICH.md, ROADMAP.md §0 + WP-Z1..Z12, ABDECKUNG.md §12, NUTZER_ENTSCHEIDUNGEN.md offene Punkte). Projektordner: /v13/ZIELABGLEICH.md.

# V13 Zielabgleich: Blueprint v10.16.1 gegen ROADMAP/ABDECKUNG (2026-10-21)

## Kurzfassung
1. Die Roadmap ist seit dem 12.10. ein Arbeitsprotokoll und keine Zielliste mehr; ihr Kopf (Zielbild, Stand, Reihenfolge) war vom 09.10.
2. Die Blueprint-Ziele fehlten als Liste: §29 „V13 funktioniert“ (24 Eigenschaften) und §100 (10 Gates). Sechs der zehn §100-Gates kamen in ROADMAP/ABDECKUNG nie vor.
3. Stand nach Blueprint-Regeln: 0 von 10 §100-Gates grün (alle PARTIAL, measure_suite 21.10.); §29: 8 erreicht, 14 teilweise, 2 fehlen (Latent-Kanal-Nutzen, Message-Subspace-Austausch). Nach Blueprint-Wortlaut noch Harness-Prototyp.
4. „56 % ✅“ in ABDECKUNG = Code existiert, nicht Ziel erreicht. §24: nur 6 von 35 gemessen (24.11 durchgefallen), 25 nur Existenz-Test, 2 NEEDS_REDMI, 2 NOT_IMPLEMENTED.
5. Drift: R4 Teile 4–11 (Rechen-Werkzeug-Regeln), Action-JEPA Runden 1–9, Werkzeug-Vorhersage schließen kein §100-Gate. STEP2 (Komplementarität B1/B2) ist seit 09.10. offen.

## §96 STEP-Ausgänge
STEP0 ✅, STEP1 ✅, STEP2 ❌ (UTILITY_FAIL; gate-graph.json meldet trotzdem GREEN), STEP3 ✅, STEP4 🟡 (kein Referenz-Lehrer), STEP5 🟡 (TRAIN_RUNNER_PROOF Redmi fehlt), STEP6A ✅, STEP6B ❌ (B3 L1 FAIL), STEP6C 🟡 (keine Expert-Deltas), STEP7 ❌ (Redmi-Wochenlauf), STEP8–11 ⏸.

## §100 Gates (alle PARTIAL)
G-B-TIMESCALE-DIVERGENCE-001 → Z2; G-CALLOSUM-UTILITY-002 → Z4; G-FOCAL-CAPACITY-003 → Z5; G-PROCEDURALIZATION-004 → Z6/Z7; G-SELF-WORLD-005 → Z12; G-TRAIN-RUNNER-PROOF-001 → Z7; G-REPLAY-CONSOLIDATION-001 → Z9; G-MODULATOR-SPECIFICITY-001 → Z6; G-AGE-REOPEN-001 → Z8; G-MOBILE-LONGRUN-001 → Z7.

## Was nicht passte
a ROADMAP §1–§4 veraltet (jetzt historisch, neuer §0). b „R4 Teile 4–11“ sind Werkzeug-Regeln, nicht §31 R4. c Blueprint hat zwei R-Nummerierungen (§31 R0–R9, §79 R0–R6); Roadmap folgt §31. d Vision-Lab vor STEP7 (Blueprint: erst danach) – keine weitere Arbeit. e Action-JEPA/Werkzeug-Vorhersage ersetzen kein World-JEPA im Körper. f WP-AG (12 AGI-Lücken) ist Nutzerziel, nicht Blueprint. g ABDECKUNG-✅ widerspricht Gate-🟡 (Effort/G5B, Inquisition/G5, Koalition/G3D). h gate-graph STEP2 GREEN trotz FAIL.

## Neue Pakete WP-Z
Z1 Gate-Ehrlichkeit (STEP2_HARNESS vs STEP2_EXIT, §29-Tabelle in measure_suite). Z2 STEP2 neu mit B1-eigener Detail-Information + 4 Kontrollen. Z3 C3-Konsument isolieren (C3 vs B1 vs Werkzeug). Z4 B3 L1 Versuch 4 (läuft in anderem Thread). Z5 Fokus-Koalition gegen Voll-Kontext/Retrieval/feste Slots. Z6 §24 Gehirn-Mitte messen (24.22, 24.23, 24.17, 24.25, 24.26, 24.32). Z7 ein Redmi-Paket für alle Handy-Pflichtmessungen. Z8 Nutzerwahl Age-Plastizität. Z9 Dream-Kontrolle policy-only. Z10 MoE verdrahten + 24.19. Z11 Referenz-Lehrer STEP4. Z12 JEPA im Körper + echte Self/World-Fälle.
Start sofort: Z1, Z2, Z3, Z5. Seitenzweige nicht weiter ausbauen bis Z2–Z5 Ergebnisse haben.

## Offene Nutzerentscheidungen
1 age_plasticity_policy boot|stable_reopen|noise_aware (seit 10.10.). 2 offer_quote_context_chars=200 (seit 20.10.). 3 Redmi-Läufe (Z7).


---

## QUELLE: THREAD_B3_L1_DIAGNOSE_20261020.md

# Thread „B3 L1 Gate reparieren“ — 2026-10-20

Branch `claude/project-thread-0zelvf`, Commits dbd9df7 (Vorregistrierung), 8568949 (Diagnose + aux-Parameter), cc527f0 (aux-Lauf, Doku). Projektordner gespiegelt (v13/code, v13/bench-results/b3-l1-diagnose-20261020).

## Ergebnis
- L1-FAIL liegt NICHT an Bytes (64 B kosten nur 0,004 Nutzen mehr) und NICHT am Kanal: die 64-B-Nachricht trägt U/F (R² 0,88–0,94); mit U/F-Sonde gelesen ist sie so gut wie SCALAR (89/93/86 % vs 91/94/84 %, n.s.).
- Ursache: Brücke lernt nur aus ≤360 Aufgabenlabels, SYMBOLIC_ATTR/SCALAR bekommen privilegierte U/F-Labels. Eingefrorener NO_MESSAGE-Kopf kostet weitere ~2 Punkte. Mehr Aufgabenlabels (180→360) schließen die Lücke nicht.
- Fix-Kandidat: `Bridge(aux=A).fit(..., aux=...)` in v13/b3bridge.py (nur Trainingssignal; Empfängerpfad und 64 B unverändert; Default byte-identisch; Test mit Gradientenprüfung).
- Explorativ (gesehene Testitems): LATENT_AUX +5,5/+4,7/+9,8 Punkte; Gate PASS auf `action` (auch strikt vs SCALAR), escalate/apologize weiter FAIL gegen Attributwörter.
- Kein Canon-PASS: B3_LATENT bleibt unavailable, L2 gesperrt.

## Nächstes Paket
B3 L1 Versuch 4: vorregistriert, neue Datensaat (neue B1/B2-Zustände, Modelle wie Versuch 3), aux-Brücke, Gate unverändert, Rollen-Retention neu messen.

## Suite
1572 Tests, 5 Skips, 1 Fehler = vorbestehender test_neuro_ledger (fehlende bench-results im Git-Baum), auch ohne diese Änderung.


---

## QUELLE: THREAD_HANDY_PAKET_WERKZEUG_20261020.md

# Thread „Handy-Paket Werkzeug-Vorhersage“ (2026-10-20, Claude)

Paket 4 aus ROADMAP „Nächste offene Pakete“. Git: Branch `claude/project-thread-0zelvf`, Commits `5571a0b` (Paket) und `d341be2` (ROADMAP-Merge).

## Ergebnis
- Ein Befehl am Redmi: `bash WERKZEUG_TESTEN.sh [paritaet|kurz|voll]` (neu `code/WERKZEUG_TESTEN.sh`, `code/scripts/werkzeug_handy.py`, Tests `tests/test_werkzeug_handy.py` 9/9, Anleitung `code/WERKZEUG_ANLEITUNG.txt`).
- Ablauf: Vorprüfung (RAM >= 1,5 GB frei, Speicher, kein Chat), bei Bedarf `setup.sh` ohne Chat-Autostart, `termux-wake-lock`, GPTs begrenzter Treiber `tool_forecast_bounded_phone_candidate.py` mit Frist 2/4/10 h, RAM-/Akku-Temperatur-Verlauf alle 10 s, Ergebnis-ZIP `V13-Werkzeug-Ergebnis-<stufe>-<zeit>.zip` in Downloads (nur Berichte/Logs, KURZ.txt). Kein Plan/Gate geändert, Autorität 0, SHADOW.
- Fehler behoben: Handy-ZIP brach im Setup-Selbsttest ab (2 Belegdateien fehlten in `package_source.py` PHONE_REQUIRED_FIXTURES). Selbsttest im entpackten ZIP jetzt 1580 OK.
- Cloud-Probelauf aus entpacktem ZIP, frisches Home (Linux, 4 CPUs, KEIN Redmi): `voll` → LIVE_PATH_CONFIRMED+CONTINUAL_LEARNING_CONFIRMED in 22 min; Parität PASS 45 s; Live 245/245, Median 1,47 s/Aufruf, Spitzen-RSS Tap-Prozess 1213 MB; Lernen 610 Aufrufe 14,8 min, Integrität PASS. Verhältnisse identisch zu 12./13.10.
- Handy-ZIP: Claude-Projektordner `export/V13-Werkzeug-Handy-20261020.zip` (12,2 MB, SHA f8fb5719…, 714 Dateien). Nicht auf Drive (Größe/Inline-Upload).
- Bekannt, nicht von diesem Thread: `test_neuro_ledger` scheitert im reinen Git-Baum (fehlender Belegordner `bench-results/homeo-meta-20261012`), Thread uvi2sq hat die Ordner auf seinem Branch nachgezogen.

## Offen (Nutzer)
Redmi: ZIP entpacken, `bash WERKZEUG_TESTEN.sh` (kurz, geschätzt 30–90 min), Ergebnis-ZIP hochladen; optional `voll` über Nacht. SHADOW → active erst danach.


---

## QUELLE: THREAD_STEP2_ENGPASS_20261020.md

# Thread „STEP2-Nutzen Engpass“ — 2026-10-20

Git: RedMentos/Aii Branch `claude/project-thread-dq33gk` (Basis `claude/project-thread-0zelvf`), Commits `3d9e767` (Code + Prereg, vor Inferenz) und `7109977` (Ergebnis, ROADMAP, Handoff).
Projektordner: v13/code (Code übernommen), v13/bench-results/step2-quote-context-20261020 (volle Reports), ROADMAP-Abschnitt gleichen Namens.

## Ursache
Qwen-B2 findet die frühere Projektregel, zitiert sie aber zerstückelt oder klein geschrieben. Die exakte Zitatprüfung verwirft das; volle Regel erreichte C3 nur in 7/30 „Regel behalten“-Offers.

## Änderung
`v13/cognition.quote_span`, Schalter `offer_quote_context_chars` (Standard 0 = aus = bisher). Bei 200: Zitat ist Zeiger auf ganze exakte Quellsätze (≤200 Zeichen derselben Quelle), transportiert wird nur exakter Quelltext. Kettenglied `integrated_candidates.quote_context`. Tests `tests/test_quote_context.py` 7/7.

## Native Messung (Linux, gleiche Modelle wie 13.10.), CONTEXT_SUPPORTED
- volle Regel an C3: 7/30 → 23/30
- mit Eignungs-Werkzeug, „Regel behalten“ B2-Varianten exakt: 11/30 → 24/30
- 0 falsch festgelegt; b2_only/both_none/both_control 10/10; Überschreibungen 16/16 in beiden Armen

## Unverändert
STEP2 UTILITY_FAIL (B1 ohne eigene Information; both_exact .842 < b2_only .917 mit Werkzeug). Ohne Werkzeug 0/70 exakt: C3 (350M) rechnet nicht. Kein Redmi/Kanon.

## Offen
1. Nutzerentscheidung: Schalter einschalten (offer_quote_context_chars=200 + b2_offer_body_state=false + offer_quote_min_chars=90).
2. Eignungs-Werkzeug in den Live-Antwortpfad (C5/READ_LOCAL).
3. Neue vorregistrierte STEP2-Fixtures mit B1-eigener Information.
4. Rest 7/30: B2 zitiert die frühere Regel gar nicht.


---

## QUELLE: THREAD_WP_G2_GIST_READOUT_20261020.md

# Thread „Nächste Pakete Abdeckung“ — WP-G2 nativer Gist-Readout-Konsument (2026-10-20)

Git: RedMentos/Aii Branch `claude/project-thread-uvi2sq` (Basis `claude/project-thread-0zelvf` @ 13acfc3), Commits 8036f62, 86a500f, d4336a6.
Projektordner: /mnt/project-files/v13 (Code, ROADMAP, ABDECKUNG, HANDOFF_CURRENT aktualisiert).

## Was gebaut wurde
- `code/v13/gist_readout.py`: konsumiert gespeicherten B2-Tap (Qwen3.5-0.8B Endnorm pro Token), bytegenaue Token→Zeichen-Bindung über native Pieces, Gruppierung ~8 Tokens (fixed|text|native|hybrid), 12 Slots, §3.2A-Felder, verlustfrei geprüft. `:tap B2_GIST` → `:gist readout [Modus]`. SHADOW, keine Rechte.
- Tests `tests/test_gist_readout.py` (11). Volle Suite 1582 OK / 5 Skips.
- 19 fehlende §102-Belegordner (`bench-results/*-20261012`, 444 KB) ins Git nachgezogen (Test test_neuro_ledger schlug sonst im Git-Baum fehl).

## Messung (nativ Linux, vorregistriert, Prereg vor Lauf gepusht)
- Runde 1 (160 Fragen): hybrid .594, text .563, nativ .563, fest .481, zufällig .355 → SUPPORTED.
- Explorativ: fest Größe 9 (gleiche Gruppenzahl) .544 → Teil-Effekt durch Gruppenzahl.
- Runde 2 (640 Fragen, Kontrolle gleiche Gruppenzahl): hybrid +.022 CI [-.016,.061] FAIL; text +.081 CI [.045,.114]; nativ -.005.
- Folge: Standardmodus `text`. Natives Sprungsignal liegt an Satzgrenzen (AUC .88), bringt aber keinen Zusatznutzen.

## Offen
Andere Tap-Schicht; gelernter Grenz-Kopf (neues Prereg); Antwort-Nutzen mit `:gist active`; native Firing-Diagnostik (anderer Teil von Paket 5) nicht angefasst. Redmi nicht gemessen.


---

## QUELLE: THREAD_STEP2_PILOT_20261020.md

# THREAD Privater STEP2-Pilot — 2026-10-20

Git: RedMentos/Aii Branch claude/project-thread-s7943o @ 5ae02fd (Registrierung vorab @ abc5dc4). Projektordner: v13/code/docs/proofs/continuation-20261016/step2-private-fixtures/pilot-run-20261020/

# Privater STEP2-Pilot — nativer Lauf 2026-10-20

**Status: gelaufen, 18/18 Zeilen abgedeckt, Kohorte `NOT_CONFIRMED` (1 Zeile ERROR), 0/18 exakt. Diagnostik, kein Gate. Historisches STEP2 `UTILITY_FAIL` und B3 L1 `FAIL` unverändert.**

## Ablauf
1. GPTs read-only Auditor (Drive `V13_PRIVATE_PILOT_AUDIT_RUN7_DELTA_20261019.zip`, alle 10 Manifest-Hashes geprüft) eingebunden: `audit_private_pilot.py`, `test_audit_private_pilot.py` (11/11 OK).
2. Original-Registrierung `pilot/native-registration.json` hier nicht ausführbar (bindet GPTs Gerät/Pfade); bleibt unverändert `REGISTERED_NOT_RUN`.
3. Neues Home aus dem gepinnten Katalog: B1/B2/C3-GGUF, Runner b10964 und alle 39 Bibliotheken byte-identisch zur Original-Registrierung.
4. Zweite Registrierung `native-registration-20261020.json` vor dem Lauf veröffentlicht (Commit abc5dc4), Quellen = exakt a1973d4.
5. Auditor-Preflight: PREPARED_NOT_RUN, 0 Fehler.
6. Lauf seriell 19:27–19:30 UTC, 188 s, Linux x86_64, 4 CPUs, Peak-RSS 1408 MB. report.json sha256 50ed2226…
7. Auditor nach Lauf: REFUSED nur wegen der einen ERROR-Zeile; sonst konsistent.

## Ergebnis
| Arm | RECORDED | exakt | Aktion richtig | Feld-Utility |
| --- | ---: | ---: | ---: | ---: |
| b1_model_quotes | 3/3 | 0 | 0 | 0.667 |
| b2_model_quotes | 3/3 | 0 | 0 | 0.639 |
| paired_model_quotes | 3/3 | 0 | 0 | 0.639 |
| same_policy_dual | 3/3 | 0 | 0 | 0.639 |
| no_message | 2/3 | 0 | 0 | 0.361 |
| exact_source_control | 3/3 | 0 | 0 | 0.667 |

## Befunde
- Flaschenhals ist C3 (LFM2.5-350M), nicht der Zitat-Transport: auch die Exakt-Quellen-Kontrolle liefert 0/3 exakt und immer action UNKNOWN; C3 rechnet remaining nicht.
- B1 zitiert seine Regel korrekt; mehr Zitate helfen C3 nicht.
- ERROR-Zeile bfzwzwww/no_message: B2 zitierte den öffentlichen Text unter seiner privaten SourceRef, Adapter lehnt korrekt ab (strenge registrierte Regel).
- project-Format ("Project X" statt "X") kostet 12 Felder.

## Nächster Schritt
Konsument isoliert testen (neue Registrierung): Exakt-Quellen-Kontrolle mit größerem Konsumenten (B1) oder deterministischem calc/eligibility-Tool vor C3.


---

## QUELLE: THREAD_GPT_UEBERNAHME_20261020.md

## GPT/Codex-Stand 13.–19.10. übernommen — ERLEDIGT 2026-10-20 (Thread „GPT-Stand erneut übernehmen“)
Git: Branch `claude/project-thread-0zelvf` (Draft-PR https://github.com/RedMentos/Aii/pull/5, baut auf GPT-PR #4 auf). Bitte künftig hier aufsetzen.

- Quelle: **GPT/Codex** Branch `codex/continuation-20261016` @ `a1973d4` (PR #4, 12 Commits seit `1941d07`, 16.10.), dazu Drive: `V13-Codex-Fortsetzung-20261016.md`, Native-Abend-ZIPs (geschlossen `V13-Native-Evening-0610-closed.zip`, SHA `0260f539…`), Preregistrierungen, und am 19.10. ein **nicht integrierter** Kandidat `V13_PRIVATE_PILOT_AUDIT_RUN7_DELTA_20261019.zip` (read-only Auditor für den privaten STEP2-Pilot, 11/11 eigene Tests, kein Modelllauf; GPT konnte ihn nicht auf GitHub pushen, Branch `assistant/private-pilot-readonly-audit-20261019` = `a1973d4` ohne neuen Code). PR #3 (`codex/continuation-review-20261013`) war schon von M umgesetzt; seine restlichen Review-Kandidaten bleiben dort.
- Was GPT gebracht hat: K (list_arith) + M (calc/note/ToolForecast) zusammengeführt; enger Fix gegen Quellentausch während Outcome-Tap (`toolforecast.py`); Lernintegritäts-Gate gegen falschen PASS aus unvollständigen Zeilen, in die normalen Phone-Skripte integriert; Vorzeichen-Guard in `agi/listarith.py` (−5/Unicode-Minus wird nicht mehr als +5 akzeptiert); **native ToolForecast-v2-Lernkohorte 610/610 geschlossen** (Linux, SHADOW, Qwen-Taps): verschobene Zahlen calc MSE-Verhältnis .386–.707, Notizen .504–.666, feste Retention calc .982–1.002, Notizen 1.000, beide Lerngates PASS im engen Scope, unabhängig nachgerechnet. Erster abgebrochener Lauf bleibt UNKNOWN/negativ. Neuer Runtime/Store-Adapter für private STEP2-Quelle (28 Tests) und registrierter 18-Zeilen-Pilot — **noch nicht gelaufen**.
- Übernahme: 152 neue GPT-Dateien + 7 nur von GPT geänderte Dateien übernommen; `tools.py`, `broker.py`, `toolstep.py`, `transaction.py` behalten den Projektstand (hatte K+M bereits, plus WP-W2c `eligibility`-Tool, das GPT fehlte; GPT-Unterschiede dort nur Kommentare/Reihenfolge). Vorherige Fassungen in `archiv/vor-gpt-uebernahme-20261020/`. Kein Überschreiben, kein Force-Push.
- Prüfung: volle Suite (auch auf dem reinen Git-Tree) → **1571 Tests OK, 6 Skips**. Privatsphäre-Grep: nichts Privates.
- Unverändert offen/negativ: STEP2 original 70/70 UTILITY_FAIL, B3 L1 FAIL, Redmi-Messungen, Canon/Fullscope.

### Nächste offene Pakete (für sechs parallele Threads)
1. Privater STEP2-Pilot nativ ausführen (18 Zeilen/max 42 Aufrufe) + GPTs read-only Auditor vom 19.10. prüfen und binden.
2. B3 L1 / LATENT weiter (L1 FAIL, L2–L4 gesperrt).
3. STEP2-Nutzen: B2-Produzent/C3-Konsument-Flaschenhals, nächste Ablation auf Basis R4-Teile 5–8.
4. ToolForecast v2 → Gerät: Phone-Paket bauen, Neuinstallation + Redmi-Messung durch Nutzer.
5. Canon-Abdeckung: nächste offene WP aus ABDECKUNG.md (~56 %), Gist-Readout-Consumer, native Firing-Diagnostik.
6. Git-Konsolidierung: welcher Branch ist Hauptstand (PR #2/#3/#4/#5).



---

## QUELLE: Thread_N_Sicherung_2026-10-13.md

# V13 Thread „Nächste offene Pakete N“ – Sicherungsnotiz 2026-10-13

Repo: RedMentos/Aii, Branch `claude/project-thread-lmo0ri`, HEAD `434b19b` (Remote geprüft). Basis: Branch von Thread H (`claude/project-thread-3w32al`).
Gleicher Stand liegt im geteilten Projektordner `v13/code/` (Live-Kopie aller Threads).

| Paket | Commit | Inhalt |
|---|---|---|
| WP-N16 §97.2 | e60340b | Ressourcen-Modi GREEN/YELLOW/ORANGE/RED (`v13/resource_modes.py`), im Turn, Effort, Bodies, Sleep, Lern-Jobs |
| WP-N17 §22.2.4/§73 | 9a190fc | Observer-Scheduling-Regler (`v13/observer_schedule.py`), RSS-Budget als Modus-Eingang |
| WP-N18 G13 | c94eb00 | Langlauf-Soak `scripts/longrun_soak.py`; Fix: Wach-Replays verdrängten Nacht-Schlaf (`v13/sleep.py`) |
| WP-N19 B3-H10/H11 | f06696c | Degradations-Leiter + 10 Auslöser (`v13/b3degrade.py`), `:doctor`-Pflichtfelder |
| WP-N20 B3-H4/H5/H9 | bbedb57 | Empfänger-Kalibrierungspaket + hartes Tor (`v13/b3calibration.py`) |
| WP-N21 | bd356d3 | Körper-Größen aus RAM-Messung (`v13/body_sizes.py`, `specs/body-sizes.json`) |
| WP-N22 B3-H8 | ff214a0 | Trainingsreihenfolge erzwungen (`v13/b3order.py`) |
| – | 434b19b | `.gitignore` für Python-Caches |

Volle Suite 1333 OK / 4 Skips (Linux-Softwaretest, kein Redmi). Doku: `code/docs/RESOURCE_MODES.md`, `LONGRUN_SOAK.md`, `B3_DEGRADATION.md`.
Offen: Redmi-Messungen (WP-R): `:resources calibrate`, RAM-Bench von Thread P + `:resources bodies import <json>`, `longrun_soak.py --native`.
Keine privaten Daten im Repo geprüft (keine Tokens, E-Mails, Geräte-IDs).


