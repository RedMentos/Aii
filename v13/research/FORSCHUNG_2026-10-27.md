# V13 Forschungsabgleich Runde 2 (Stand 2026-10-27)

Auftrag (Nutzer, 27.10.): Blueprint und Umsetzung gegen den **tagesaktuellen** Stand der Wissenschaft prüfen,
nicht nur JEPA. Vorgänger: `FORSCHUNG.md` (09.10.), daraus sind WP-S1..S8 entstanden und größtenteils gebaut.
Diese Runde sucht gezielt nach Arbeiten **seit Juni 2026**, vor allem August bis Oktober 2026.

Kennzeichnung: **[geprüft]** = arXiv-/Hugging-Face-Seite heute selbst abgerufen, Zahlen aus der Zusammenfassung
der Autoren (nicht nachgerechnet). **[Suche]** = nur in Suchergebnissen gesehen, nicht selbst geöffnet.
**[Schluss]** = meine Folgerung für V13, nicht gemessen.

Ehrliche Grenze: ~25 Websuchen und 23 abgerufene Quellen sind kein vollständiger Literaturüberblick. Was hier
fehlt, ist nicht automatisch nicht da.

---

## 0. Kurzfassung

1. **JEPA ist nicht falsch, aber nicht die einzige Antwort.** Die neuesten Weltmodell-Arbeiten (Sept./Okt. 2026)
   sagen übereinstimmend: Ein Weltmodell, das nur den nächsten Zustand gut vorhersagt, wählt deshalb noch keine
   guten Handlungen. Besser ist, auf **entscheidungsrelevante** Ziele zu trainieren (D-JEPA, AAWM, AEWM).
   Daneben gibt es echte Alternativen (Dreamer-/TD-MPC-Linie, Sprach-Weltmodelle wie Qwen-AgentWorld).
2. **Vergessen:** Zwei Arbeiten vom Oktober 2026 sind direkt nutzbar: Updates nur im „unwichtigen“ Teil der
   Gewichte (Subspace Tuning, 2–4× weniger Drift) und neues Wissen als wiederverwendbares Verfahren statt als
   auswendig gelernte Beispiele (Skill Schema Transport, Vergessen 42 → 7 Punkte).
3. **Gedächtnis:** Erinnerungen sollten sich beim Abruf verändern dürfen (Rekonsolidierung, REALM, +7 Punkte
   LoCoMo). Und: Welches Gedächtnis „das beste“ ist, kippt nach Wochen (Ground Truth First). V13 misst bisher
   nur kurze Strecken.
4. **Schlaf:** Der Blueprint liegt richtig. Neu: winzige erlernte „Erfahrungs-Notizen“ (Soft Prompts,
   ~0,001 % der Parameter) lernen pro Aufgabe ohne Vergessen; Schlaf als Destillation + selbst erzeugter
   Übungsplan (Behrouz et al.).
5. **Metakognition:** ECE/Brier reichen nicht. Neues Maß „wie gut weiß das Modell, was es weiß“
   (Signal-Detection, meta-I) sagt direkt voraus, wie viel Enthalten nützt. Das passt als Prüfmaß für V13s
   Unsicherheits-Teile.
6. **Selbstwissen:** Echte Introspektion ist bei Sprachmodellen **nicht belegt** (Reality Check, COLM 2026).
   Verhaltens-Selbstvorhersage geht begrenzt. Der Blueprint-Ansatz „Self Model = strukturierter, gemessener
   Zustand“ ist damit richtig; V13 darf nie behaupten, das Modell „fühle“ seinen Zustand.
7. **Routing/MoE:** Die Form des Routers ist fast egal (Equifinality, 62 Läufe); wichtig ist, **wen** man fragt.
   Kleine Kompetenz-Sonden auf Hidden States eines kleinen Modells (ScoutRoute, 16.10.2026) passen zu V13s
   Routen-Kopf.
8. **Sicherheit:** Nur das Antwortverhalten trainieren macht anfällig für Umformulierungen (Representational
   Alignment, 23 Modelle). Ein kleiner Streaming-Wächter (Qwen3Guard-Stream-0.6B, Apache-2.0) existiert.
   Gedächtnis braucht Prüfungen **vor** der Konsolidierung (SSGM).
9. **Handy:** Keine neuen ~1B-Modelle im Sept./Okt. 2026 gefunden; Qwen3.5-0.8B/2B, Gemma 4 E2B, LFM2.5 bleiben
   aktuell. Training am Handy ist gezeigt (3B auf iPhone 17 Pro), aber Dauer-Training halbiert den Durchsatz
   durch Hitze.

---

## 1. Kontinuierliches Lernen ohne Vergessen

**Blueprint sagt:** Lebenslang plastisch, aber nicht überall gleichzeitig (§1.10); Regression Shield,
Retention-Gate, Router/Shared-Path schützen (§16.2.1, W6); 0Q.5 Plasticity vs Retention.
**V13 hat schon:** KL-Drift-Gate (WP-S5), Sparse Memory (WP-S3), KL-Anker im nativen LFM2-Pfad (WP-S6).

| Arbeit | Kern | Was V13 übernehmen sollte |
|---|---|---|
| **Subspace Tuning** (Chavan et al., arXiv 2610.22293, 15.10.2026) [geprüft] | SFT verändert die Hauptrichtungen der Gewichte (Singulärwerte) → Vergessen. SST schränkt jedes Update auf den **unteren** Singulär-Unterraum ein; bis 99 % geschützt, 2–4× weniger KL-Drift; mit SFT oder Self-Distillation kombinierbar. Gewinne wachsen laut Autoren mit Modellgröße. | **Neu, billig:** im nativen C3/LoRA-Training (WP-S6) als Arm gegen den KL-Anker testen. Achtung: Wirkung bei 350M unbelegt → messen, nicht annehmen [Schluss]. |
| **Skill Schema Transport** (Liu et al., arXiv 2610.28892, 20.10.2026, NeurIPS 2026) [geprüft] | Neue Daten werden in ein **Verfahrens-Schema** (Schritte, Abhängigkeiten, Prüfschritte) umgeschrieben, statt Wortlaut zu lernen. Zwei 3B-Modelle: +2,5 bis +5,8 Punkte, Vergessen Qwen-3B MATH 42,4 → 7,1. | Passt auf Proceduralisation (L5.6) und Sleep B: vor Konsolidierung Episoden in Schema-Form bringen. Das ist die erste belegte Methode für „Prinzip statt Einzelfall“ (alte Lücke 7 in FORSCHUNG.md). |
| **Experiential Latent Memories** (Dorovatas et al., arXiv 2606.17803) [geprüft] | Rechnen zur Laufzeit in kleine modulare Soft-Prompt-Speicher destillieren (~0,001 % der Parameter, wenige Gradientenschritte); Belohnung = Mehrheitsabstimmung über eigene Antworten; modular → kein Vergessen. | Kandidat für **Lernen am Handy pro Aufgabe**: winzig, abrufbar, löschbar. Nur Mathe belegt [Schluss]. |
| Algorithmic Stability (arXiv 2610.31551, 22.10.2026) [Suche] | Theorie: Vergessens-Schranken aus Datenmenge, Updates pro Aufgabe, Lernrate, Gradienten-Ausrichtung. | Nur Hintergrund. |

## 2. Weltmodelle (JEPA und Alternativen)

**Blueprint sagt:** World-JEPA = State + Predictor auf A/B/C-Repräsentationen, kein eigener Body (§7.2);
control-grounded Hilfsziele forward/inverse/state-align/outcome (§7.2.1); Coverage + Counterfactual-Confidence (§7.2.2).
**V13 hat schon:** SIGReg (WP-S4), Z12c slot-weises World-JEPA PASS, Z12b FAIL.

| Arbeit | Kern | Was V13 übernehmen sollte |
|---|---|---|
| **D-JEPA** (Liu et al., arXiv 2609.24749, 21.09.2026) [geprüft] | Genaue Vorhersage ≠ gute Wahl: ein „näher am Ziel“ vorhergesagter Zustand kann real schlechter ausgehen. D-JEPA lernt aus **ausgeführten** Ergebnissen, welche von mehreren Kandidaten-Zukünften besser war. PushT 87,9 %, Roboter +17 Punkte. | **Wichtigster Punkt.** Der Blueprint-Term `outcome` (§7.2.1) sollte als **Rangfolge zwischen Kandidaten** trainiert werden, nicht nur als Fehler pro Zustand. |
| **Agent-Authored World Modeling** (Cai et al., arXiv 2606.25421) [geprüft] | Der Agent sagt selbst, was er vor einer Entscheidung wissen muss; daraus werden Trainingsziele gebaut. Schlägt „nächste Beobachtung vorhersagen“ bei gleichem Budget. | Gleiche Richtung: Weltmodell-Ziele aus Entscheidungsbedarf ableiten. |
| **Agent-Editing World Model** (Sun et al., arXiv 2609.28416, 23.09.2026) [geprüft] | Tool-Antworten nachbauen bringt wenig; besser: modellieren, wie Handlungen den **Aufgabenfortschritt** ändern, und veraltete Annahmen/Pläne im Verlauf markieren („task-state contamination“). +3,2 bis +6,7 Punkte. | Für V13s Workspace/JEF: alte Hypothesen aktiv als „überholt“ markieren. Passt zum gefundenen Z5c-Problem (Hypothesen schaden). |
| **Flow-JEPA** (Huo et al., arXiv 2608.29029) [geprüft] | JEPA-Prädiktor erzeugt **mehrere** mögliche Zukünfte (Flow Matching) statt eine. Bei Rauschen 67 → 86 % Erfolg. | Liefert direkt den „prediction spread“, den §7.2.2 verlangt. Später, nicht jetzt. |
| **LeWorldModel** (Maes, …, LeCun, Balestriero, arXiv 2603.19312) [geprüft] | JEPA end-to-end ohne EMA, nur Vorhersage + Gauß-Regularisierer (SIGReg); ~15M Parameter, 1 GPU, Stunden; erkennt physikalisch unmögliche Ereignisse („Überraschung“). | Bestätigt WP-S4 (SIGReg statt EMA). Die Überraschungs-Messung passt zu Salience (F2). |
| **Qwen-AgentWorld** (Zuo et al., arXiv 2606.24597) [geprüft] | **Nicht-JEPA:** Sprachmodell als Weltmodell (35B-A3B und 397B-A17B), sagt nächste Umgebungs-Beobachtung als Text voraus; 10 Mio. Verläufe. | Zu groß fürs Handy. Aber als **Cloud-Lehrer** (AG1) denkbar, um Weltmodell-Spuren zu erzeugen [Schluss]. |
| DreamerV3 (Nature 2025), TD-MPC2, Dreamer 4 [Suche] | **Nicht-JEPA:** latente Dynamik + Belohnung/Wert, Planen in der Vorstellung. | Für V13s Text-Welt nicht direkt nötig; der Gedanke „Wert mitlernen“ deckt sich mit D-JEPA. |

## 3. Gedächtnis, Konsolidierung, Schlaf

**Blueprint sagt:** Active/Warm/Episodic/Exact/Staging/Archive (§9.1), Admission/Forgetting (§9.5),
Sleep A Replay / B Dream / C Homeostasis / D Consolidation (L8.3).

| Arbeit | Kern | Was V13 übernehmen sollte |
|---|---|---|
| **REALM** (Song et al., arXiv 2609.16053, 13.09.2026) [geprüft] | Abruf **verändert** Erinnerungen (Rekonsolidierung): Graph-Gedächtnis wird nach Abruf-Feedback umgebaut. LoCoMo 75,97 % (+7,17), LongMemEval 65,11 % (+1,31). | Blueprint kennt Rekonsolidierung nicht ausdrücklich. Neu: Abruf-Ergebnis (half/half nicht) als Signal an Memory-Admission. |
| **Ground Truth First** (Spencer, arXiv 2607.21962) [geprüft] | Rangfolge von Gedächtnis-Systemen **kippt mit der Zeit**: nach 3 Wochen gewinnt ein anderes als nach 9 Wochen (96 → 72 % vs. 90 %). Schwach geschriebene Fakten scheitern 24 % vs. 2 %. Schutz gegen Einschleusung hängt an erhaltenen Herkunftsgrenzen. | V13 testet Gedächtnis nur über kurze Strecken. **Langzeit-Test mit Wochen-Zeitachse** nötig, bevor ein Gedächtnis-Standard gewählt wird. Bestätigt Provenance (§1.8). |
| **Language Models Need Sleep** (Behrouz et al., arXiv 2606.03979) [geprüft] | Schlaf = Konsolidierung (Destillation zwischen Modellen) + „Träumen“ (RL erzeugt eigenen Übungsplan). Zusammenfassung ohne Zahlen. | Schon im Blueprint zitiert. Konkret neu: Sleep B soll **Übungsaufgaben** erzeugen, nicht nur Szenarien. |
| **SSGM** (Lam et al., arXiv 2603.11768) [geprüft] | Gedächtnis-Entwicklung von Ausführung trennen; vor Konsolidierung Konsistenz, Zeit-Verfall, Zugriffsrechte prüfen; private Inhalte nicht dauerhaft festschreiben; Drift über wiederholtes Zusammenfassen verhindern. Nur Konzept, keine Messung. | Als **Checkliste für Sleep D**: Privat-Filter + Drift-Prüfung vor jedem Gewichts-Update. |

## 4. Metakognition und Unsicherheit

**Blueprint sagt:** Calibration im Self Model (§7.3), Confidence/Abstain/Escalation in JEF, `L_C_CALIBRATION`.

| Arbeit | Kern | Was V13 übernehmen sollte |
|---|---|---|
| **Metakognitive Effizienz mit Signal-Detection** (Cacioli, arXiv 2603.25112, v3 28.07.2026) [geprüft] | ECE/Brier vermischen „wie viel weiß es“ mit „wie gut weiß es, was es weiß“. Maß meta-I₂r; sagt den Nutzen von Enthalten exakt voraus (ρ = +1,00), Genauigkeit nicht. Achtung: v3 korrigiert einen Fehler der früheren Versionen. | **Neues Prüfmaß** für V13s Antwort↔Werkzeug-Gegenprüfung (DS3b) und Effort-Policy: zusätzlich zu ECE melden. |
| **RLMF** (Liu et al., arXiv 2606.32032, v2 12.10.2026) [geprüft] | RL, das Antworten nach Güte der Selbsteinschätzung ordnet; bis 63 % besser als Standard-RL bei treuer Unsicherheits-Angabe. | Cloud-seitig, später. Grundgedanke (Selbsturteil bewerten) passt zu Second-Attempt. |
| Survey Metakognition (Liu et al., arXiv 2607.11881) [geprüft] | Erster Gesamtüberblick, Paperliste auf GitHub. | Nachschlagewerk. |
| EHQ-3000 (arXiv 2609.07879) [Suche] | Test auf erfundene Dinge, Ereignisse nach Wissensstand, Nischenwissen. | Idee für V13-Ehrlichkeitstest. |

## 5. Modul-Routing / MoE

**Blueprint sagt:** JEF ist kein zentraler Router (§3.3, L9.1 Gain statt Modulwahl); Router/Shared Path vor
Plastizität schützen (W6, §16.2.1). **V13 hat:** WP-N11 MoE-Router, Routen-Kopf (KL/Z6i).

| Arbeit | Kern | Was V13 übernehmen sollte |
|---|---|---|
| **Equifinality in MoE** (Ternovtsii & Bilak, arXiv 2604.14419) [geprüft] | 62 Läufe: Router-Varianten liegen innerhalb 1 Perplexity-Punkt; selbst Hash/Zufall nur 1,1–2,2 schlechter. Relative-Norm-Halten spart 25 % Rechnen. | **Keine Zeit in Router-Feinheiten** stecken. Das Halte-Ergebnis ist für Z6i (§24.17) interessant. |
| **ScoutRoute** (Pandhare & Bharucha, arXiv 2610.23443, 16.10.2026) [geprüft] | Ein kleines „Späher“-Modell, einmal durchlaufen; logistische Sonden auf dessen Hidden States schätzen, welches größere Modell kompetent ist. Besser kalibriert als normale Confidence. | Passt genau zu V13: C3/kleines Modell entscheidet per Sonde, ob B1, B2 oder Lehrer gefragt wird. Kandidat für Effort-Policy. |

## 6. Kleine Modelle und Training am Handy

| Quelle | Befund | Folge |
|---|---|---|
| HF „State of Open Models Summer 2026“ (14.08.2026) [geprüft] | Modelle < 1B = 83 % aller Downloads; ggml/llama.cpp gehört seit Feb. 2026 zu Hugging Face; Neuheiten des Sommers sind fast nur Großmodelle. | Keine neue Kleinmodell-Generation, die V13s Wahl überholt. |
| Suche nach Sept./Okt.-Kleinmodellen [Suche] | Kein neues ~1B-Modell von Qwen, Gemma, LFM, SmolLM gefunden; Qwen3.5-0.8B/2B, Gemma 4 E2B (April 2026) aktuell. | Modellwahl aus FORSCHUNG.md bleibt gültig. |
| **3B auf iPhone feintunen** (Geyko et al., arXiv 2610.06325, 05.10.2026) [geprüft] | Nutzer-Adapter in ~einer Akkuladung, so gut wie Server-Adapter; **Dauer-Training halbiert Durchsatz** (Hitze), Pausen helfen nicht. | Für Redmi-Planung: Schlaf-Training mit ~50 % Durchsatz einplanen; iPhone ≠ Redmi, eigene Messung nötig. |

## 7. Sichere / ethische KI

**Blueprint sagt:** F6 Provenance/Rules/Safety, Age-Hülle, Action Gate, IH-H29 Tool-Sicherheit.
**V13 hat:** Regel-Leser v3–v8 (alle UNSAFE), :verbot, :stillstand.

| Arbeit | Kern | Was V13 übernehmen sollte |
|---|---|---|
| **Representational Alignment** (Li et al., arXiv 2609.04022) [geprüft] | 23 Modelle trennen moralische Gegensätze innen schlecht; reines Verhaltens-Training lernt die Antworten, ändert die innere Ordnung kaum und **erhöht** die Anfälligkeit für Umformulierung. | Erklärt, warum V13s Regel-Leser bei neuen Formulierungen scheitern. Folge: Prüfsätze mit gezielten Umformulierungen; Sicherheit nie nur auf gelernte Antworten stützen [Schluss]. |
| **Guard-Benchmark** (Harsh et al., arXiv 2605.28830) [geprüft] | 14 Wächter-Modelle: Qwen Guard 4B höchste Trefferquote (83,97 %); Größe sagt nichts; große Wächter verpassen bis 75 %. | Kleiner Wächter kann reichen. |
| **Qwen3Guard-Stream-0.6B** (HF) [geprüft] | Apache-2.0, 0,6B, prüft **Token für Token** beim Schreiben (Safe/Controversial/Unsafe), 119 Sprachen (Deutsch nicht einzeln genannt). | Kandidat als unabhängiger Zweitwächter neben dem Regel-Leser; RAM und Deutsch erst messen. |
| SSGM (siehe §3) | Gedächtnis-Korruption, Leck privater Inhalte. | Privat-Filter vor Konsolidierung. |

## 8. Selbstwissen

**Blueprint sagt:** Self Model als strukturierter Zustand (§7.3); bewusstseinsnahe Interpretation vorsichtig (§4.6).

| Arbeit | Kern | Was V13 übernehmen sollte |
|---|---|---|
| **Can LLMs Introspect? A Reality Check** (Singh, Linzen, Ravfogel, arXiv 2605.26242, COLM 2026) [geprüft] | Bisherige „Introspektions“-Belege lassen sich aus der Eingabe allein erklären; Erkennung von Eingriffen ist eher allgemeine Anomalie-Erkennung. „Aktuelle Evidenz reicht nicht.“ | Blueprint-Weg (gemessener Zustand statt Modell-Selbstauskunft) ist richtig. Keine Behauptung „V13 spürt sich“. |
| **Evaluating and Improving LLM Self-Modeling** (Zeng et al., arXiv 2608.30980) [geprüft] | Modelle sagen eigenes Verhalten nur begrenzt voraus, Fehler bei einfachen „was wäre wenn“-Fragen; RL verbessert, aber nicht durch privilegierten Zugang. | **Prüfbarer Selbstwissen-Test** für V13: „Würde diese Änderung meine Antwort ändern?“ vorhersagen und nachprüfen. Passt zu Z12a (self/world PASS). |

---

## 9. Änderungsvorschläge (gehen als WP-FS1..FS10 in ROADMAP.md)

Reihenfolge nach Nutzen pro Aufwand [Schluss]:

| Paket | Was | Baustein | Aufwand |
|---|---|---|---|
| WP-FS1 | Weltmodell-Ziel „welcher Kandidat ging besser aus“ (D-JEPA-Rangfolge) neben Vorhersagefehler, auf Z12c-Aufbau | Weltmodell | mittel, Cloud |
| WP-FS2 | Subspace Tuning als Arm im nativen C3-Training gegen KL-Anker, Vergessen + Lernen messen | Lernen | klein, Cloud |
| WP-FS3 | Metakognitive Effizienz (meta-I/Typ-2-SDT) als Pflichtmaß neben ECE für DS3b, Effort-Policy, Abstain | Metakognition | klein |
| WP-FS4 | Selbstwissen-Test „sage eigene Antwortänderung voraus“ (Self-Modeling-Benchmark-Idee) | Selbstwissen | klein |
| WP-FS5 | Regel-Leser-Prüfsätze mit gezielten Umformulierungen; Qwen3Guard-Stream-0.6B als Zweitwächter messen (RAM, Deutsch) | Sicherheit | mittel |
| WP-FS6 | Sleep D Checkliste: Privat-Filter, Konsistenz, Drift über Zusammenfassungen vor jedem Gewichts-Update (SSGM) | Sicherheit/Schlaf | klein |
| WP-FS7 | Skill-Schema vor Konsolidierung: Episoden in Verfahrens-Schema umschreiben (SST-Recasting), gegen Roh-Episoden messen | Lernen/Schlaf | mittel |
| WP-FS8 | Rekonsolidierung: Abruf-Ergebnis verändert Gedächtnis-Eintrag; plus Langzeit-Gedächtnistest über simulierte Wochen | Gedächtnis | mittel |
| WP-FS9 | Späher-Sonden (ScoutRoute): kleines Modell + logistische Sonden entscheiden B1/B2/Lehrer; Router-Feinheiten nicht weiter ausbauen | Routing | mittel |
| WP-FS10 | Veraltete Hypothesen im Workspace aktiv markieren (AEWM „task-state contamination“), Bezug Z5c | Weltmodell/Workspace | klein |

Nicht übernehmen (jetzt): Flow-JEPA (erst wenn FS1 trägt), Qwen-AgentWorld lokal (zu groß), RLMF (Cloud-RL, teuer).
Blueprint-Text bleibt unangetastet (W1 Preservation); die Pakete sind Ergänzungen.

---

## 10. Quellen (alle 2026-10-27 abgerufen)

- Subspace Tuning: https://arxiv.org/abs/2610.22293
- Skill Schema Transport: https://arxiv.org/abs/2610.28892
- Experiential Latent Memories: https://arxiv.org/abs/2606.17803
- Algorithmic Stability: https://arxiv.org/abs/2610.31551
- D-JEPA: https://arxiv.org/abs/2609.24749
- Agent-Authored World Modeling: https://arxiv.org/abs/2606.25421
- Agent-Editing World Model: https://arxiv.org/abs/2609.28416
- Flow-JEPA: https://arxiv.org/abs/2608.29029
- LeWorldModel: https://arxiv.org/abs/2603.19312
- Qwen-AgentWorld: https://arxiv.org/abs/2606.24597
- DreamerV3 (Nature): https://www.nature.com/articles/s41586-025-08744-2
- REALM: https://arxiv.org/abs/2609.16053
- Ground Truth First: https://arxiv.org/abs/2607.21962
- Language Models Need Sleep: https://arxiv.org/abs/2606.03979
- SSGM: https://arxiv.org/abs/2603.11768
- Metakognitive Effizienz: https://arxiv.org/abs/2603.25112
- RLMF: https://arxiv.org/abs/2606.32032
- Metakognition-Survey: https://arxiv.org/abs/2607.11881
- EHQ-3000: https://arxiv.org/abs/2609.07879
- Equifinality in MoE: https://arxiv.org/abs/2604.14419
- ScoutRoute: https://arxiv.org/abs/2610.23443
- State of Open Models Summer 2026: https://huggingface.co/blog/state-of-open-models-summer-2026
- 3B auf iPhone: https://arxiv.org/abs/2610.06325
- Representational Alignment: https://arxiv.org/abs/2609.04022
- Guard-Benchmark: https://arxiv.org/abs/2605.28830
- Qwen3Guard-Stream-0.6B: https://huggingface.co/Qwen/Qwen3Guard-Stream-0.6B
- Introspection Reality Check: https://arxiv.org/abs/2605.26242
- LLM Self-Modeling: https://arxiv.org/abs/2608.30980
