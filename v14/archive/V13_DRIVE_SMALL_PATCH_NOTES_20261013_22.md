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


