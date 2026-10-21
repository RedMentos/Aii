# V13 Zielabgleich: Blueprint v10.16.1 gegen ROADMAP/ABDECKUNG (2026-10-21)

Anlass: Nutzer am 21.10.: Ziele scheinen zu fehlen und nicht zum Blueprint zu passen, und die Arbeit scheint aufgehört zu haben.
Grundlage: `blueprint/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` (§29, §96, §99, §100, §105, §23, §24, §31/§79, B3-Addendum),
`ROADMAP.md`, `ABDECKUNG.md`, `NUTZER_ENTSCHEIDUNGEN.md`, `code/specs/gate-graph.json`, `code/specs/benchmarks.json`.
Frisch nachgemessen am 21.10.: `python3 scripts/measure_suite.py` auf dem Projektstand (nur Auswertung vorhandener Belege, kein Modelllauf).

## 0. Kurzfassung

1. **Der Nutzer hat recht.** Die Roadmap ist seit dem 12.10. ein Arbeitsprotokoll und keine Zielliste mehr. Ihr Kopf (Zielbild, Stand, Reihenfolge) ist vom 09.10. und wurde nie nachgezogen.
2. **Die eigentlichen Blueprint-Ziele fehlen als Liste.** Der Blueprint sagt selbst, wann V13 „funktioniert“ (§29, 24 Eigenschaften) und welche zehn Gates grün sein müssen (§100). Keine der beiden Listen stand in der Roadmap. Sechs der zehn §100-Gates kamen in ROADMAP und ABDECKUNG nie vor.
3. **Stand nach den Blueprint-Regeln:** 0 von 10 §100-Gates grün (alle PARTIAL), von den 24 §29-Eigenschaften 8 erreicht, 14 teilweise, 2 fehlen. Nach Blueprint-Wortlaut ist V13 damit noch ein **Harness-Prototyp**.
4. **Die „56 % ✅“ in ABDECKUNG.md heißen „Code existiert“, nicht „Ziel erreicht“.** Von 35 §24-Kern-Benchmarks sind nur 6 mit echten Zahlen gemessen (davon 1 durchgefallen), 25 haben nur einen Existenz-Test.
5. **Die Arbeit ist vom Blueprint-Pfad abgedriftet.** Viel Aufwand ging in Seitenzweige (R4 Teile 1–11 Rechen-Werkzeug-Regeln, Action-JEPA Runden 1–9, Werkzeug-Vorhersage). Die sind sauber gemacht, schließen aber kein §100-Gate. Der Blueprint-Engpass, STEP2 (B1/B2 ergänzen sich messbar), ist seit dem 09.10. offen.
6. **Neue Pakete WP-Z1 bis WP-Z12** (Abschnitt 6) bringen die Arbeit zurück auf die Blueprint-Reihenfolge §96/§105.

## 1. §29 „V13 funktioniert“: die 24 Pflicht-Eigenschaften

Legende: ✅ erreicht (Code + echte Messung), 🟡 teilweise (Code da, Messung/Nutzen fehlt), ❌ fehlt.

| # | Eigenschaft (§29) | Stand | Beleg / was fehlt | Paket |
|---|---|---|---|---|
| 1 | echte vortrainierte A + B + C | ✅ | G1; B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C2 Needle, C3 LFM2.5-350M | – |
| 2 | B1 fein + B2 adaptiv grob mit Cross-scale SourceLinks | 🟡 | G1B: B2-Readout misst Text-Grenzen besser, gelernte adaptive Gruppierung und Antwort-Nutzen fehlen | WP-G2-Rest, Z2 |
| 3 | BodyPort-Profile + trainierter Callosum-Bootstrap | 🟡 | G2; Bootstrap nur EXACT/CONTROL/SYMBOLIC | Z4 |
| 4 | adaptive Kanal-Policy mit nachgewiesenem Latent-vs-Fallback-Nutzen + Empfänger-Kalibrierung | ❌ | B3 L1 FAIL (Diagnose 20.10.), §24.11 MEASURED_FAILING | Z4 |
| 5 | echter Message-Subspace-Austausch ohne Private-State-Kollaps | ❌ | B3 L2–L4 gesperrt bis L1 PASS | Z4 |
| 6 | kleiner echter JEF-Sprach-/Executive-Body mit privatem Native-KV | 🟡 | C3 läuft, entscheidet nie (Z3 21.10.: 0/117 direkt, auch mit fertigem Werkzeug-Satz); liest Zahlen fehlerfrei, Bool `local_only` falsch; Entscheidung nur über Werkzeug (strict 0 falsch); B1/B2 als Konsument schlechter; kein natives JEF-KV; Z3b 21.10.: Parser + C3-Zahlen kanonisch 117/117, C3 liest Ja/Nein-Regeln nie (immer `true`), auf Umformulierungen kein sicherer Gewinn | Z3 ✓, Z3b ✓ |
| 7 | versionierter JEF_BROADCAST_CACHE + trainierte JEF↔A/B-Brücken | 🟡 | Broadcast-Cache da, Brücken nur gelernte Feld-Gates | Z6 |
| 8 | A/B-Observer-Pass → OFFER_PACKETs | 🟡 | live im Turn; Nutzen (§24.25) nur Existenz-Test | Z6 |
| 9 | FOCAL_COALITION_STATE | 🟡 | Code live; Utility-Bench: kein Arm außerhalb des Rauschens; G-FOCAL-CAPACITY-003 PARTIAL | Z5 |
| 10 | selektiver `none/A/B/A+B`-Wake mit gemessener Eskalations-Qualität | 🟡 | R4-Teile 1–3 (gelerntes Wecken, C3-Unsicherheit); §24.22 nur Existenz-Test | Z6 |
| 11 | automatischer Direct/Skill-Pfad | 🟡 | Code live; G-PROCEDURALIZATION-004 nur synthetisch (−52 % Kosten), echte Latenz/Energie fehlen | Z7 |
| 12 | gezielte Deliberation mit Re-entry + Halting-vs-Trajectory-Test | 🟡 | Python fertig; §24.17 nur Existenz-Test | Z6 |
| 13 | handlungsgeerdetes World-JEPA mit Coverage/Counterfactual-Konfidenz | 🟡 | kontrollgeerdetes Weltmodell + Action-JEPA (extern), kein latentes World-JEPA im Körper | Z12 |
| 14 | Context/Provenance ohne History-Korruption | ✅ | `store.py`, SourceRef, §24.7 | – |
| 15 | Fast-Episodic-Vorteil beim zweiten Versuch | ✅ | §24.1 MEASURED (Linux), STEP3 | – |
| 16 | lokale Eligibility + echtes JEPA/EMA-Update + Pre-Router-Regressions-Monitor | 🟡 | Eligibility ✅; JEPA nur externer Prädiktor; §24.19 NOT_IMPLEMENTED (braucht MoE) | Z10, Z12 |
| 17 | Replay + Restart-Persistenz | ✅ | WP-E, Neustart-Tests, 7-Tage-Soak Cloud | – |
| 18 | Regression-Schutz | ✅ | Stability Envelope, Generationen, Rollback | – |
| 19 | messbarer Übergang Scaffold→Imitation→Exploration→Shadow→gelernte Route je Fähigkeit | 🟡 | Scaffold→Shadow da; ganze Kette je Fähigkeit nie gemessen | Z6 |
| 20 | echte Age-Rechtehülle + bindender user_stage_cap + Reife je Fähigkeit | ✅ | G9; aber §99 „Age hilft Stabilität“ nicht belegt → G-AGE-REOPEN-001 offen | Z8 |
| 21 | adaptive Reasoning-Effort-Policy mit User-Override und Fixed-Effort-Baselines | 🟡 | Code ✅, Utility-Bench im Rauschen; R5/§24.23 nicht gemessen | Z6 |
| 22 | native Cache/Sparse-Attention nur nach Ablation | 🟡 | G6B: Manifest + Auswahl gemessen, Runtime-Anschluss/Redmi offen | WP-N7-Rest |
| 23 | Event/Wake-Scheduler + unabhängiger Response Governor | ✅ | `scheduler.py`, Governor; Redmi-Langlauf offen | Z7 |
| 24 | endliche Output-Garantie | ✅ | §24.6 | – |

Summe: **8 ✅, 14 🟡, 2 ❌.**

## 2. §96 Bauordnung: Ausgangs-Kriterien je STEP

| STEP | Ausgang laut Blueprint | Stand | Anmerkung |
|---|---|---|---|
| 0 Substrat | Liste §96 STEP 0 | ✅ | |
| 1 JEF-Slice | echte Ausgaben, Persistenz, Telemetrie, ohne B | ✅ | C3-Qualität bleibt schwach |
| 2 Split-Brain-Observer | **messbare Komplementarität**, begrenztes RSS, bekannte Observer-Latenz | ❌ | STEP2 UTILITY_FAIL seit 09.10. Achtung: `gate-graph.json` meldet STEP2 GREEN, weil dort nur Harness-Kriterien geprüft werden → Widerspruch, siehe Z1 |
| 3 Fast Memory | zweiter Versuch besser ohne Gewichts-Update | ✅ | Linux |
| 4 Reference Teacher | SELF zuerst, REFERENCE getrennt, HUMAN entscheidet | 🟡 | Lanes da, kein stärkerer Referenz-Lehrer angeschlossen (Z11) |
| 5 Shadow Learning | TRAIN_RUNNER_PROOF, ModulatorPacket, Eligibility, Shadow-Generation, atomarer Commit | 🟡 | alles da außer TRAIN_RUNNER_PROOF auf dem Redmi (Z7) |
| 6A Callosum-Kanäle | NONE/EXACT/CONTROL/SYMBOLIC | ✅ | |
| 6B Latent-Brücke | einfachste Prefix-Ausrichtung zuerst | ❌ | L1 FAIL, Versuch 4 offen (Z4) |
| 6C B-Lernen | Prädiktoren, Projektoren, aktive Expert-Deltas, Router eingefroren | 🟡 | Prädiktoren ja; Expert-Deltas fehlen (MoE nicht verdrahtet, Z10) |
| 7 Stabilitäts-Epoche | Wochen, Retention, Thermik, Neustarts | ❌ | nur 7 simulierte Tage in der Cloud; Redmi fehlt (Z7) |
| 8–11 Modalitäten, Age > 0 | „erst danach“ | ⏸ | Vision-Lab existiert trotzdem schon (siehe 5d) |

## 3. §100 Arbeits-Gates (grün nur mit Code, echtem Zustandspfad, Persistenz, Test, Telemetrie, Ablations-Baseline, bekannten Grenzen)

`measure_suite.py` am 21.10.: **alle zehn PARTIAL, keins grün.** Vorher standen sechs davon weder in ROADMAP noch in ABDECKUNG.

| Gate | Was es verlangt | Stand / Lücke | Paket |
|---|---|---|---|
| G-B-TIMESCALE-DIVERGENCE-001 | B1/B2 mit verschiedenen, komplementären Fehlerprofilen; Kombination schlägt zwei gleiche Instanzen; 4 Kontrollen | STEP2 FAIL; in bisherigen Fixtures hat B1 keine eigene Information | **Z2** |
| G-CALLOSUM-UTILITY-002 | LATENT schlägt NONE/EXACT/CONTROL/SYMBOLIC auf 8 Achsen | L1 FAIL, Ursache diagnostiziert, Versuch 4 offen | **Z4** |
| G-FOCAL-CAPACITY-003 | Kapazitätsgrenze, Wettbewerb, Ersetzung, Interrupt, Re-entry, Quellbindung, Erholung; schlägt „alles in den Kontext“ | Tests für Eigenschaften da; Vergleich gegen Voll-Kontext/Retrieval/feste Slots fehlt (§99-Kontrollen fehlen) | **Z5** |
| G-PROCEDURALIZATION-004 | Latenz↓, Energie↓, Genauigkeit nicht schlechter, Wiederöffnen bei Fehler | synthetisch belegt; echte Latenz/Energie fehlt | Z6, Z7 |
| G-SELF-WORLD-005 | 6 Fälle Selbst- vs. Welt-Ursache | Tests da (synthetisch), Corollary-Kandidat 3 übernommen; keine echte Handlungsfolge | Z12 |
| G-TRAIN-RUNNER-PROOF-001 | kein APPROVED_COMMIT ohne grünen Proof für genau diesen Parameterpfad | Cloud-Proof da; Redmi-Proof fehlt | **Z7** |
| G-REPLAY-CONSOLIDATION-001 | Replay/Konsolidierung mit Retention-Nutzen | Dream2v3 15/15 mit Nutzen/Retention-Abwägung; §99-Kontrolle „dream policy-only“ fehlt | Z9 |
| G-MODULATOR-SPECIFICITY-001 | typisierte Modulatoren schlagen Skalar/Human/Outcome-only | synthetisch 5/5 bzw. 4/5; nicht mit echten Modellen | Z6 |
| G-AGE-REOPEN-001 | Age-Wiederöffnen stabilisiert | §99: Age **nicht** belegt; Kandidat `noise_aware` wartet seit 10.10. auf Nutzerwahl | **Z8** |
| G-MOBILE-LONGRUN-001 | Redmi-Langlauf | nur Cloud-Soak | **Z7** |

## 4. §24 Kern-Benchmarks und §99 Pflicht-Ablationen

- §24 (35 Stück): **6 MEASURED** (24.1, 24.15, 24.18, 24.20, 24.24 und 24.11 **durchgefallen**), **25 nur TESTED** (es gibt einen Test, aber keine Messung mit echten Modellen), 2 NEEDS_REDMI (24.14, 24.33), 2 NOT_IMPLEMENTED (24.19 Pre-Router-Vergessen, 24.31 Cross-modal). ABDECKUNG zählte alle 35 als eine Zeile 🟡.
- Utility-Bench mit echten Modellen (WP-T3/T3b, 10.10.): Koalition, Inquisition, Adaptive Effort, Gist aktiv, Attention aktiv liegen **alle im Rauschband**. Die „Gehirn-Mitte“ hat also Code, aber noch keinen gemessenen Nutzen.
- §99 (11 Hypothesen): Kontrollen fehlen noch bei „Callosum hilft“ (latent), „Focal coalition hilft“ (full context only, retrieval only, fixed slots) und „Dream hilft“ (dream policy-only). „Age hilft Stabilität“ wurde gemessen und ist **nicht belegt**. „Zwei Bodies lohnen die Handy-Kosten“ hängt an Z2.

## 5. Was nicht zum Blueprint passt

a. **Roadmap-Kopf veraltet.** §1–§4 der ROADMAP sind vom 09.10. (z. B. „B1 und B2 sind dasselbe LFM2.5-1.2B“, alte STEP2-Zahlen). Jetzt als historisch markiert, neuer Abschnitt 0 oben.
b. **„R4 Teile 1–11“ heißt im Blueprint etwas anderes.** §31 R4 = „kann der kleine Executive Kosten sparen, ohne Qualität zu verstecken“ (C-native vs. Body-Wake, §24.22). Ab Teil 4 wurde daraus Feinarbeit an Rechen-Werkzeug-Regeln (`calc`, `list_arith`, Fragen-Regeln R2/R3, Familie E). Das gehört zu IH-H29/§6 Werkzeuge und schließt kein Gate. Nicht weiter ausbauen; Ergebnis in die §24.22-Messung (Z6) einbringen.
c. **Zwei R-Nummerierungen im Blueprint.** §31 hat R0–R9, §79 hat R0–R6 mit anderen Inhalten (dort ist R4 „lokales Lernen“). Ab jetzt gilt in der Roadmap §31 und wird so benannt.
d. **Vision-Lab vor STEP7.** §96: „Only then modalities/Age > 0“. WP-N15/WP-T16 bleiben als Lab-Gerüst stehen, bekommen aber keine weitere Arbeit, bis STEP7 erreicht ist.
e. **Action-JEPA (9 Runden) und Werkzeug-Vorhersage** liegen fachlich bei §7.2/L4.6, ersetzen aber nicht das World-JEPA im Körper (§29 Nr. 13) und belegen „konstantes Lernen“ nur im engen Werkzeug-Rahmen.
f. **WP-AG „12 AGI-Lücken“** stammt aus FORSCHUNG.md, nicht aus dem Blueprint. Bleibt als Nutzerziel, wird aber getrennt geführt und zählt nicht als Blueprint-Abdeckung.
g. **ABDECKUNG widerspricht sich selbst.** Zeilen sagen ✅, das zugehörige Gate 🟡: Adaptive Reasoning Effort ✅ vs. G5B 🟡, Inquisition ✅ vs. G5 🟡, Koalitions-Binder ✅ vs. G3D 🟡. Legende ist jetzt klargestellt (✅ = Baustein im Code), die Gate-Ebene steht getrennt.
h. **`gate-graph.json` STEP2 = GREEN** obwohl der Blueprint-Ausgang (Komplementarität) FAIL ist. Muss getrennt werden (Z1).

## 6. Neue Pakete WP-Z (Reihenfolge nach §96/§105)

| Paket | Inhalt | schließt | wo |
|---|---|---|---|
| **Z1** | `gate-graph.json`: STEP2 in `STEP2_HARNESS` (grün) und `STEP2_EXIT` (Komplementarität, rot) trennen; §100-Gates mit Blueprint-Kriterien je Gate prüfen statt nur Belegdateien; `measure_suite` gibt §29-Tabelle aus | Ehrlichkeit, IH-H33 | Cloud, klein |
| **Z2** | STEP2 neu: vorregistrierte Fixtures, in denen **B1 eigene Detail-Information** hat und B2 den Überblick; alle 4 Kontrollen (gleiches Modell gleiche Policy, nur anderer Prompt, ein Körper + zwei Zustände, zwei Körper) | G-B-TIMESCALE-DIVERGENCE-001, §99 „zwei Bodies lohnen“, STEP2-Ausgang | Cloud, Modelle |
| **Z3** | C3-Konsument isolieren: gleiche exakte Quellen an C3 (350M), an B1 als Antwort-Körper und an deterministisches Werkzeug vor C3; entscheidet, ob C3 ersetzt/ergänzt werden muss (§29 Nr. 6, §31 R9/§24.34) | STEP2-Engpass aus Pilot 20.10. | Cloud, Modelle |
| **Z4** | B3 L1 Versuch 4 (läuft seit 21.10. in einem anderen Thread): frische Zustände, `aux`-Brücke, Gate unverändert, vorregistriert | G-CALLOSUM-UTILITY-002, STEP6B | Cloud, Modelle |
| **Z5** | Fokus-Koalition gegen die drei fehlenden §99-Kontrollen (Voll-Kontext, nur Retrieval, feste Slots) auf den 60 Widerspruchs-Aufgaben aus WP-T3b mit festem Rauschband | G-FOCAL-CAPACITY-003 | Cloud, Modelle |
| **Z6** | §24 von TESTED zu MEASURED, zuerst die Gehirn-Mitte: 24.22 Wake, 24.23 Effort (R5), 24.17 Deliberation, 24.25 Observer-Nutzen, 24.26 Broadcast-Brücke, 24.32 Lebenszyklus je Fähigkeit; R4-Werkzeug-Ergebnisse hier einbringen | §29 Nr. 7, 8, 10, 12, 19, 21; G-MODULATOR-SPECIFICITY-001 | Cloud, Modelle |
| **Z7** | Ein Redmi-Paket für den Nutzer mit allen Handy-Pflichtmessungen in einem Lauf: TRAIN_RUNNER_PROOF, Langlauf, 24.14, 24.33, Proceduralisierung Latenz/Energie, Werkzeug-Vorhersage | G-TRAIN-RUNNER-PROOF-001, G-MOBILE-LONGRUN-001, STEP5, STEP7 | Nutzer (WP-R) |
| **Z8** | Nutzerentscheidung Age-Plastizität (`boot` / `stable_reopen` / `noise_aware`), danach Wiederöffnen-Test | G-AGE-REOPEN-001 | Nutzer, dann Cloud |
| **Z9** | Dream-Ablation mit fehlender Kontrolle „dream policy-only“ | G-REPLAY-CONSOLIDATION-001 | Cloud |
| **Z10** | MoE-Hälften verdrahten (WP-N11 Teil 3) und §24.19 Pre-Router-Vergessen messen; Expert-Deltas mit eingefrorenem Router | STEP6C, §29 Nr. 16 | Cloud, groß |
| **Z11** | STEP4: stärkeren Referenz-Lehrer in der Cloud als REFERENCE-Lane anschließen (nie als Wahrheit), Teacher-on/off messen | STEP4, §24.28B | Cloud |
| **Z12** | JEPA im Körper: Body-JEPA-Term und handlungsgeerdetes World-JEPA auf echten Handlungsfolgen; G-SELF-WORLD-005 mit echten statt synthetischen Fällen | §29 Nr. 13, 16 | Cloud, nach Z2 |

Empfohlene Startreihenfolge für parallele Threads: **Z1, Z2, Z3, Z5** sofort (alles Cloud; Z4 läuft schon, ebenso ein Thread zum Eignungs-Werkzeug im Live-Pfad), Z6 danach, Z7 sobald der Nutzer ein Handy-Fenster hat, Z8 braucht nur eine Antwort.

## 7. Offene Nutzerentscheidungen, die Ziele blockieren

1. Age-Plastizität `boot | stable_reopen | noise_aware` (offen seit 10.10., blockiert G-AGE-REOPEN-001).
2. Zitat-Kontext-Schalter `offer_quote_context_chars=200` (offen seit 20.10., STEP2-Transport).
3. Redmi-Läufe (Z7): ohne sie können STEP5, STEP7 und drei §100-Gates nie grün werden.

## 8. Nutzer-Ziel über dem Blueprint (neu formuliert 21.10.)

Laut Projekt-Gedächtnis hat der Nutzer am 21.10. das Endziel neu gefasst: eine wissenschaftlich, psychologisch und moralisch fundierte KI, die Menschen nie schadet; das Gehirn als grobes Grundmodell echter selbstbewusster Intelligenz; neue Module darf sie am Ende nur mit bewusster, unmanipulierter Erlaubnis selbst holen und daraus lernen. Handy-Tests laufen parallel nach einer Testliste, die Claude schreibt.
Folge für die Ziele: Der Blueprint deckt den Schaden-Schutz über F6/§6.4/IH-H29 (Action Gate, Werkzeug-Sicherheit) und die Erlaubnis über Age/Human-Control (§17, IH-H15) ab; „Module selbst holen“ ist im Blueprint nur als Body-Swap/ModalityPort (§19, G11) mit Nutzer-Freigabe angelegt. Ein eigenes Paket dafür kommt erst nach STEP7. Die Testliste für das Handy ist WP-Z7.
