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


