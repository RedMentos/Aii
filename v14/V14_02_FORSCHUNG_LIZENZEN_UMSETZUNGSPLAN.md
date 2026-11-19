# V14 — Forschungs-, Lizenz-, Integrations- und Arbeitsplan
**Teil 2 des V14-Masters; Stand 2026-11-19.**  
**Status:** fachliche Erstprüfung auf Basis öffentlicher Primärquellen und der vorhandenen V13-Quellen. Die vorgemerkten Bibliotheken sind **Kandidaten**, noch nicht automatisch in V14 eingebaut. Dieses Dokument erlaubt keine Behauptungen über neue native Redmi-Messergebnisse.

## R0. Zweck und Prinzip

Das Forschungsziel ist nicht, möglichst viele neue Patches zu finden. Es ist, den gesamten V14-Canon mit der **geringstmöglichen Menge neu zu erfindender Technik** vollständig und sinnvoll zu bauen. Alle bestehenden V13-Organe und Arbeitspakete werden gesichtet; jedes neue Konzept erhält entweder (1) Wiederverwendung existierenden V13-Codes, (2) legale Übernahme gut gepflegter Drittbibliothek, (3) konzeptionelle Adaption wissenschaftlicher Arbeit ohne Quelltextkopie oder (4) präzise, selbst zu entwickelnde fehlende Verbindung. Es gibt niemals einen fünften Status „stillschweigend vergessen“.

Forschung ist ein **Baustein des Build-Workflows**, nicht seine Alternative. Ein kleiner externer Prototyp ist nur dann nützlich, wenn er einen echten V14-Consumer erreicht. Gemessene Laufzeit/Qualität und Quellenrecht werden getrennt ausgewiesen.

## R1. Quellumfang und Priorität

**Maßgeblich, integral erhalten:** V13 v10.16.1 Canon (13.773 Zeilen, aus GitHub \`v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md\`); Drive \`ROADMAP_Teil1von3.md\`, \`Teil2von3.md\`, \`Teil3von3.md\` zusammen, \`SICHTUNG.md\`, \`UEBERGABE_FUER_ANDERE_KI.md\`; letzte Entscheidungen und AGENTS.md; V13 GitHub Pull Requests/Issues und Codehistorie. Insbesondere alle W/IH-H, 0P/0R, Layer 1–9, A/B/C, F1–F7, G1–G..., AG..., R..., BP/B3/JEPA und WP-A...U/S/T/KAL/N-Pflichten. Die physischen Experimente und Modell-Quellen sind als historisch/aktuell getrennt zu bewerten.

**Prioritätsregel:** neuere ausdrückliche Nutzerentscheidungen schlagen ältere, *nur wenn sie wirklich widersprechen*. Sonst alte Ziele additiv erhalten. Neue Funktionen wie Mini-Self-Distillation, Weight-Delta-Prognose und mehrschichtige Selbstoptimierung ergänzen JEPA, ersetzen nicht das übrige System. Das Original bleibt als Integral-Appendix für line-by-line Gegenprüfung.

**Privacy:** Die 418-MB-Drive-Gesamtarchiv-ZIP wurde erkannt und als historische Quelle lokal referenziert. Die \`SICHTUNG.md\` dokumentiert deren frühere Auswertung (164 Einträge). Ihre komplette ZIP wurde für diese V14-Fassung **nicht** selbst inhaltlich vollständig neu extrahiert; deshalb keine erfundene Vollarchivprüfung. Der zusätzliche Canon-Appendix plus Drive-Hauptroadmap schützt wichtige Anforderungen, private Rohtraces/Schlüssel dürfen nicht ins öffentliche GitHub kopiert werden. Für mögliche fehlende ältere Einzelideen bleibt ein Historical-Diff-Audit offen.

## R2. Lizenzgrundsatz – rechts- und moralverträgliche Übernahme

**MIT, BSD-2/3, Apache-2.0** eignen sich grundsätzlich für V14-Reuse auch bei späterer Weitergabe, *wenn* Copyright, Lizenzkopie, NOTICE (bei Apache) und Abhängigkeiten beachtet werden. Die Lizenz des GitHub-Repos ist **nicht** die Lizenz seiner heruntergeladenen Modellgewichte oder Datasets. Ein „auf GitHub öffentlich“ ist keine pauschale Code-Lizenz. Dateien ohne nachprüfbare Lizenz oder mit inkompatiblen Bedingungen werden **nur als Konzept gelesen**, nicht in den Repositorycode kopiert. Copyleft-Komponenten benötigen gesonderte Architektur- und Weitergabeprüfung; Lizenzverpflichtungen nicht durch Verschleierung in GitHub umgehen. Im Zweifel neu implementieren statt kopieren.

Für jede externe Integration eine Maschinenlesbare \`THIRD_PARTY_COMPONENTS.json\`-Zeile mit Upstream-URL, exaktem Commit/SHA, SPDX-ID, file-level Exceptions, Modell-/Gewichtsbedingungen, transitive Licenses, Version, Architektur/ABI, RAM, native C++/Python-Bindings, Sicherheitsstatus, Übernahmeart, Notices, Tests, Rollback und Owner. \`COPY\` nur bei Lizenzbefund; \`INSPIRED\` darf keine wörtliche/strukturelle Copyright-Übernahme maskieren. Öffentliche Quellen und eigene Ports getrennt halten.

## R3. Bereits gefundene Upstream-Bausteine

| Komponente, Originalquelle | Lizenz-Befund | V14-Entscheidung | Grenzen / nächste Prüfung |
| --- | --- | --- | --- |
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) und [LICENSE](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE) | MIT, Third-party-Licenses im Repo | **Beibehalten/Native Integration**: GGUF, LFM/C3/B1/B2 serving, streaming, KV, quantisierte Runner | Exakten Stand, LFM2.5-Rekurrenz/Cache, aarch64-Build, QAD/GGUF, API, PSS und Testkorpus prüfen. Kein eigener Inferenzkern. |
| [PyTorch ExecuTorch](https://github.com/pytorch/executorch) [LICENSE](https://github.com/pytorch/executorch/blob/main/LICENSE) | BSD (projektbezogen; transitive prüfen) | **Optional Pilot** für Mini-A3, Distillation/JEPA Predictor oder on-device projizierbaren Head | Exportpfad/Op-Abdeckung, Arm64, Speicher, JNI/Termux vs C++, Vergleich gegen NumPy/C++-Baseline. Kein LLM-Runner-Ersatz. |
| [River](https://github.com/online-ml/river) [LICENSE](https://github.com/online-ml/river/blob/main/LICENSE) | BSD-3-Clause | **Reuse/algorithmische Referenz** für Online-Signal, Drift, Streaming-Auswertung | Native Wheels auf Termux unsicher; reine Minimalalgorithmen zuerst, ggf. eigens portieren, Lizenz beachten. |
| [Avalanche](https://github.com/ContinualAI/avalanche) [LICENSE](https://github.com/ContinualAI/avalanche/blob/master/LICENSE) | MIT (Lizenztext bestätigt), Abhängigkeiten separat | **Offline/Cloud-Baseline** für Continual Learning, Replay, Retention | Schweres PyTorch; nicht blind auf 6 GB Redmi installieren. |
| [facebookresearch/vjepa2](https://github.com/facebookresearch/vjepa2) [LICENSE](https://github.com/facebookresearch/vjepa2/blob/main/LICENSE) | Repo MIT; Modelle/Daten/Einzeldateien separat | **Forschungsreferenz**, nicht native V14-Gewichtkopie | Video-fokussiert, große Backbones, lässt sich nicht direkt als Text-Body-Lerner einhängen. |
| [Hugging Face TRL](https://github.com/huggingface/trl) [LICENSE](https://github.com/huggingface/trl/blob/main/LICENSE) und [DistillationTrainer](https://huggingface.co/docs/trl/main/en/distillation_trainer) | Apache-2.0 | **Favorit für Offline-SDFT/OPD-Referenzexperiment**, verteiltes Training mit kleinen Adaptern, später Head in V14 exportieren | Python/PyTorch/vLLM zu schwer für Standard-Redmi. Lehrsignal und Adapter-Delta müssen auf dem Handy getrennt messbar sein. |
| [TRL SDPO](https://huggingface.co/docs/trl/main/en/sdpo_trainer) | TRL Apache-2.0, experimentelle API | **Probieren als Feedback→Teacher→Student-Referenz** neben JOLT | Unbedingt aktuelle API und Revisionspin; keine eingebauten C3-Weights als Scheintrainingsweg. |
| [idanshen/Self-Distillation](https://github.com/idanshen/Self-Distillation) | Lizenz in dieser Sitzung **nicht zweifelsfrei nachgewiesen** | **Konzept/Referenz prüfen**, noch nicht kopieren | Vor COPY auf Datei- und Root-LICENSE schauen; ggf. den durch TRL lizenzierten Trainer verwenden. |
| [verl OPD](https://verl.readthedocs.io/en/latest/algo/opd.html) / [verl](https://github.com/volcengine/verl) | Lizenz am exakten Commit noch zu prüfen | **Cloud-Vergleich**, keine Mobilabhängigkeit | Distributed Training/Teacher Server; aktuell unnötig für Start-Smartphone. |
| [rllm OPSD](https://github.com/rllm-org/rllm) / [OPD-Codeübersicht](https://github.com/china10s/awesome-opd) | Erst Lizenz prüfen | **Codefinder**, Referenz für student-generated rollouts | Liste ist keine Lizenzfreigabe; nur tatsächlich repo-auditierte Kandidaten übernehmen. |

**Urteil:** V14 muss **nicht** einen eigenen vollständigen LLM-Inferenzkern oder einen separaten großen Training-Framework-Klon bauen. Der einzigartige neue Eigenbau ist der **kleine C++/Python-Port-Adapter** zwischen Organspace, echten LFM/Needle hidden states, trainierbarem Head/LoRA, eigenen Outcome-Kanten, User-Approval und Speicherzustand. Die Forschung kann und soll massiv vorhandenen, gut geprüften Code nutzen.

## R4. Forschung: Self-Distillation und die neue JEPA-Kombination

Der Wortlaut des vom Nutzer erwähnten „tagealten Papers“ war nicht exakt gegeben. Eine Erfindung eines sicheren Treffers wäre falsch. Folgende *echte* verwandte Primärarbeiten wurden identifiziert; beim späteren Einbringen der konkreten Paper-URL kann die Reihenfolge aktualisiert werden, ohne die Architektur wieder umzuschreiben.

**[Self-Distillation Enables Continual Learning / SDFT](https://arxiv.org/abs/2601.19897)**, ICML 2026 ([Proceedings](https://proceedings.mlr.press/v306/shenfeld26a.html)): derselbe Student, mit Demonstration als privilegiertem Kontext, leitet on-policy Lehrsignale ab; Ziel kontinuierliche Fähigkeitsaufnahme mit weniger Forgetting. Passt zum V14-Pfad „selbe Modellfamilie, unterschiedliche Kontextsicht“. **Nicht** erst diese Woche erschienen.

**[Self-Distilled Reasoner: On-Policy Self-Distillation for LLMs](https://proceedings.mlr.press/v306/zhao26be.html)**: Grundlagenthema OPSD, eigene Generierungen unter Teacher-Bewertung. Als Referenz für Token/KL-Signal und Student-Rollout verwenden.

**[A Good Self-Teacher Meets the Student Where They Are / JOLT](https://arxiv.org/abs/2610.10447)**, 2026-10-07: Ein privilegierter Teacher kann *trotz* besserer eigener Taskleistung den Student verschlechtern. JOLT trainiert Lehrer unter Outcome-Rewards und KL-Nähe zum aktuellen Student, Student mit dense On-policy Distillation. **Sehr relevant** für den V14 Learning-Direction-Head und das Verbot, Teacher als unfehlbare Wahrheit zu behandeln. Teacher-/Student-Update-Gradienten sind klar zu trennen.

**[SeOPD](https://arxiv.org/abs/2609.33181)**, 2026-09-27: „deep thinking“ erzeugt Zusatzinformation, „non-thinking“ wird damit distilliert. V14-Analogon: B1/B2 langer Koalitionsprozess liefert *zulässiges, überprüftes Zusatzwissen*, ein kleines C3 oder Router lernt eine schnellere Approximation. Ergebnis nicht als sicher auf andere Modellarchitekturen übertragbar ausgeben.

**[OISD: On-Policy Internal Self-Distillation](https://arxiv.org/abs/2605.29089)**, 2026-05-27: End-Layer als detach Teacher, Intermediate-Layer erhält logit-/attention-alignment. Für die Idee „Prediction Heads beobachten Repräsentation und steuern die Lernrichtung“ näher als ein reines Antwort-Kopieren; aber es ist **nicht automatisch** ein JEPA-Weight-Delta-Optimizer. Prüfe echte hidden states und den Abstand der Tokenizer/Modelle. Paper nennt Code zukünftigen Release; nicht ungeprüft übernehmen.

**[Simplify, Agree, Distill: Label-Free Self-Distillation with Stepping Stones / STONE](https://arxiv.org/abs/2611.18916)**, eingereicht **13. November 2026**, am 17. November 2026 breit indexiert: ein tatsächlich *erst wenige Tage altes* Self-Distillation-Paper und daher ein besonders plausibler Kandidat für die Nutzerbeschreibung. Statt die umstrittene Antwort auf eine schwierige Aufgabe per Mehrheit für wahr zu erklären, lässt die Methode das Modell **einfachere verwandte Zwischenaufgaben** erzeugen, auf denen die eigenen Lösungsversuche konsistent sind. Die Worked Solutions dieser ausgewählten „Stepping Stones“ informieren die privilegierte Teacher-Sicht; die Student-Sicht löst weiterhin die ursprüngliche Aufgabe ohne zusätzliche Inferenzaufrufe. Das Paper berichtet über mathematische Benchmarks beträchtliche Verbesserungen; für V14 sind dies **noch keine** Ergebnisse auf dem Redmi oder für JEPA. **V14-Integration:** Der Shepard/Curiosity-/Active-Learning-Head wählt lösbare lokale Teilaufgaben und misst Agreement; ein eigenes Teacher-Context-Packet mit nachprüfbarer Provenienz kann daraus die kleine On-policy-Distillation speisen. Der JEPA-Latent-/ΔWeight-Head bleibt *zusätzlich*, nicht vom Paper bewiesen. **Code/Lizenz:** Eine offiziell permissiv lizenzierte Referenzimplementierung war zum Prüfzeitpunkt nicht verifiziert, daher Konzeptadaption/selbst entwickelter dünner Adapter statt Codekopie. Gegencheck: mehrere leicht gelöste Teilfragen beweisen nicht die Richtigkeit des schweren Zielproblems, also Kalibrierung, unabhängige Endprüfung und Negative Controls beibehalten.

**[Stabilizing On-Policy Targeted Guidance in Agentic RL](https://arxiv.org/abs/2611.05266)**, 2026-11-03: per-turn Feedback als On-policy-Self-Distillation; Bezug zu V14 Tool/Action/Outcome, aber überwiegend RL-Agent-Setting.

**[ECOS / Environment-Calibrated OPSD](https://arxiv.org/abs/2611.12232)**, 2026-11: Umweltfeedback kalibriert Teacher-Vertrauen, nützlich für V14 World/Outcome. Nur als Paper-Idee, keine ungeprüfte Codefreigabe.

**[Privileged Information Does Not Guarantee Privileged Guidance](https://arxiv.org/abs/2611.16064)**, Mitte November 2026: Untersuchung, wann Teacher-Hinweise die tatsächliche Student-Generierung nicht verbessern. V14 muss damit rechnen, dass Token-Vorhersage-Verbesserung **nicht** in besserer frei generierter Antwort ankommt.

**[Learning Dynamics of On-Policy Distillation](https://amarcu.github.io/ai-paper-digest/archive/2026-11-06.html)**, November 2026: Rückkopplung durch Student-eigene Datenverteilung bei jedem Schritt. Warnsignal für iterative Selbstbestätigung, Drift und Outcome-Abhängigkeit.

**Befund zur Kombination:** Ein qualitativ brauchbarer V14-Mini-Distillationsweg nutzt Teacher–Student-KL/JS oder Representation Matching als **weiteren Verlust**; JEPA predict-target/EMA bleibt eigenständiges objective. Ein kleiner Meta-Head prognostiziert, *wo* ein lokales Update helfen könnte, statt blind alle Gewichte zu verändern. Erfolg wird erst nach echter Shadow-Aktualisierung + Holdout-Abweichung gemessen. Dieser Head kann später über eigene Prediction Error (predicted Δutility vs actual Δutility) online lernen. Die Verbindung ist ein **neuer Forschungsentwurf**, nicht automatisch eine veröffentlichte validierte Methode.

**Formale Minimalstruktur:** Sei student view s, teacher view t*, z = encoder(s), z+ = stopgrad(EMAEncoder(t*)), y = observed outcome und h = extra privileged verified context. Dann z_hat = P(z, action, context) mit L_JEPA = d(z_hat,z+). Für on-policy student tokens a~π_S gilt L_KD = D(π_T(.|s,h),π_S(.|s)) nur auf legitimem gleichen Token-/Actionraum. Update-Proposal m=H(z,error,teacher_diff,eligibility,drift,source_trust). Gradient/Eligibility-Update **auf trainierbaren Parametern**: Δθ = bounded(mask=m, optimizer_grad(L_JEPA + α L_KD + β L_outcome + γ L_retention)). Optionaler V-Head sagt ΔU voraus; Training mit L_meta = (ΔU_pred−ΔU_holdout)^2. Für inkompatible Tokenizer Alignment über explizite Shared Action/Latent/Token-Witness, keine rohe KL zwischen ungleichen Vokabularen. Bei instabiler KL, OOD oder schlechten Retentionsdaten nur Shadow verwerfen.

**Abgrenzung zu Backprop:** Distillation und JEPA sind Ziele/Trainingsanordnungen, kein genereller physikalischer Ersatz für Backprop. Lokale drei-Faktor-Plastizität und Eligibility können **nachgewiesene** lokale Optimierungsregeln realisieren; ohne geeignete Gradienten/Surrogates darf ihre Wirkung nicht als gezielte Deep-Weight-Korrektur behauptet werden.

## R5. Fremdcode-Wiederverwendung je V14-Organ

| V14-Teil | Zuerst im V13-Repo untersuchen | Externer Kandidat | Bauen muss V14 vor allem |
| --- | --- | --- | --- |
| A0–A5 und Audio/Vision | \`v13/aplane.py\`, \`a5_*.py\`, \`raw_ear*.py\`, \`vision.py\` | vorhandene Audio/Whisper- und TTS-Lizenzen nach separater Modellprüfung | gemeinsame Zeitachse, SourceRef-Spannen, native A3-Empfänger |
| B1/B2 Native inference | \`models.py\`, \`runners.py\`, \`bodies.py\`, \`cognition.py\` | llama.cpp, Cactus/Needle-Treiber unter dessen eigenen Bedingungen | getrennte Detail/Gist-Sichten und echte native Erfolgsmessung |
| B3 Latent/Enlightened | \`enlightened_space.py\`, \`b3bridge.py\`, \`latent_bridge.py\` | Forschungsreferenzen JEPA/BYOL/VICReg, ggml Matrixkern | Sender-Hidden-Exporte, Receiver-Projektion, OOD, genaue Token/State-Wirkung |
| C2/C3/JEF | \`executive.py\`, \`fastpolicy.py\`, \`runtime.py\`, \`cognition.py\` | Native LFM llama.cpp / Needle, TRL-Teacher für offline Kompression | native C3 speed/prefill, tatsächliche ausgewählte Offer-Konsumierung |
| F3 Memory | \`memory.py\`, \`semantic_memory.py\`, \`episodes.py\`, \`world*.py\` | SQLite / ggf. lizenzkonforme Vektorindex-Bibliothek | eventbasierter Graph, source-bound „second attempt“, Widerruf |
| F4 Learning | \`body_jepa.py\`, \`body_training.py\`, \`online_world.py\`, \`plasticity.py\` | TRL/SDPO/SDFT, River, Avalanche, ExecuTorch | trainierbarer Master/LoRA + gerçek native delta + retention |
| Sleep/Dream | \`sleep.py\`, \`sleep_offline.py\`, \`consolidation.py\` | River/Avalanche für Referenz-Replay | Outcome- und Curiosity-basiertes Sampling, Stop/Resume |
| Action/Tools | \`toolstep.py\`, \`transaction.py\`, \`actionlearn.py\` | Standard Werkzeugbibliotheken unter Licence/Audits | Consent, Transaction, Corollary, Outcome und Learning |
| UI/Android | \`managed_console.py\`, \`mobile_dashboard.py\`, \`runtime_deploy.py\` | Termux, native Build-Tools, ggml | echte Ein-Befehl-Installation, Button-/Updater-Ehrlichkeit |
| Agentische Selbstoptimierung | aktuell diverse \`agi/\` + Kandidaten | Git/GitHub CI, Code-review-Werkzeuge | isolierter Self-Edit-Planer, reviewed diff, sandbox, Rollback |

Das Wort „noch bauen“ bedeutet **Adapter oder fehlende echte Verbindung**, nicht, dass jedes Modul neu geschrieben werden soll. Bei Systemen mit bereits vorhandenen 200 Kandidatendateien muss zuerst der tatsächliche Consumer im Runtime-Graph gesucht werden.

## R6. Voller V14-Integrations- und Entwicklungsfahrplan

### Phase A — Source Reconstruction & Reality Map
- Roh-Canon/Drive/neuere Entscheidungen mit unveränderlichen Quellkopien; jeweils Datum, Hash, Herkunft, Lizenz.
- V13 Runtime, stager/builders, echte ModelRunner, UI und ALLE Candidate-Dateien inventarisieren. Mapping \`canonical_id → implemented_file → real_caller/consumer → evidence → missing\`.
- Widersprüche schriftlich als alternatives Verhalten ausweisen und neueste Userentscheidung beachten. Nicht unbemerkt alte Rechte auslassen.
- Output: maschinenlesbare Canon-Feature-/Edge-Registry und Trace-Generator; mindestens ein inspectierbarer Dry-Run des gesamten Graphen.

### Phase B — Real connected organism
- V14 Runner/organ ports im vorhandenen Runtime-Spine verbinden. Text-Event A5 → JEF/Episodic/World → echte native B1/B2 Offers → source-bound C3 input → sichtbare Antwort. Kurzer Reflex kann früh antworten, Observer dürfen weiterarbeiten.
- Body→B3→Body und **Enlightened Space system-wide** mit typisierten Nachrichten (keine „latent“-Etiketten ohne Native Receiver).
- Eine lokale Chat-Session mit Reboots, SourceRefs und saturiertem RAM auf Redmi. Wenn eine native Funktion fehlt, sichtbarer OFF/SHADOW-Status plus Antwort; keine 30-Sekunden-Stille.
- Output: reproduzierbarer 20-Turn-Messlauf und native First-Token-Budget, nicht 20 PRs.

### Phase C — Memory/Self/World & real outcome loop
- Existing SQLite Experience/World/Memory/Self Pfade in normalen Run injizieren, Lernen über reale Outcome-IDs, second-attempt und schwierige Analogiefälle messen.
- Human corrected span, explicit approved teacher, source trusted baseline, actual action/result einheitlich typed; Retention und Forgetting ab erster Deltaklasse.
- Output: in einer neuen Session erkennbar **richtige** veränderte zweite Antwort, mit Quellen, Widerruf und Reset.

### Phase D — trainable JEPA/Distillation/LoRA graph
- Bestehende native LoRA/Body-JEPA-Experimente in separaten Worker mit echten trainierbaren Gewichten, EMA/Optimizer/RNG-Persistenz, exact source/teacher/student lineage.
- A3, B1, B2, World, JEF-/C3-Head separat trainieren, cross-organ Lernsignale kontrolliert annehmen, Replay/Sleep als Quelle zugelassener Fälle.
- TRL/SDFT-Referenz am Linux-Host/Cloud; kleinen exportierten Teacher-Pair-/Meta-Head auf Android testen. Kein Muss, große PyTorch-Frameworks aufs Handy zu ziehen.
- Output: gemessenes Δθ + Restart + held-out usefulness/forgetting + Rollback für **mindestens einen** Pfad je Lernklasse, nicht nur ein numerischer Loss.

### Phase E — experimental online mini-distillation direction head
- On-policy eigene Rollouts, privileged Teacher nur mit echter verifizierter Extrainformation. Teacher-KL zur Student-Politik + Outcome-Kalibrierung; Teacher nie automatisch richtig.
- PREDICT_STATE/PREDICT_DELTA/PREDICT_UTILITY getrennt entwickeln. Zunächst nur kleine Matrix-/LoRA-Parameter. Drittgewichte und private model states nicht unbegrenzt kopieren.
- Ablationsmatrix JEPA-only, KD-only, joint, no META, full META, frozen/co-evolving teacher, random teacher, replay/no replay; reale positive Transfer- und Forgetting-Messung. Negative Ergebnisse bleiben dokumentiert.
- Output: belastbarer Mehrwert oder begründete Abschaltung der neuen Zusatzkomponente, während alle anderen Lernpfade weiter funktionieren.

### Phase F — modalities / tools / autonomous skill and self-edit proposals
- Live Audio/Vision/Raw-Path an echten A-Events, asynchronen Aufmerksamkeit-Ports und Text-Ausgabe binden. TTS/Stimme nur mit geklärten Modell-Lizenzen/Consent.
- Handlungsschleifen mit Vorhersage, Tool-Proposal, Approve, Execute, Observe, Compare, Learn.
- Self-edit/Architecture Planner als Vorschlags-/Experimentpfad mit Git diff, separatem Branch, Tests, Angriffsszenarien, Report/Review und Rollback. Keine unautorisierten Selbst-Deployments.
- Output: demonstrierter End-to-End-Sensorimotor/Tool-Outcome und wiederholbar verbesserter Skill.

### Phase G — sparse multi-organ optimization and robust release
- zwei native unterschiedliche Body-Modelle, später sparse MoE+JEF Tiny, echte LFM Hybrid-State-Cache-Grenzen, warm residency, Energy Profiling, quantized trainer/LoRA fallback.
- reale Android-Hardware-Kohorte mit Memory, PSS, Thermik, ggf. 6GB-Floor vs Desktop/Cloud Crossbench, Langzeit-Retention, Build/Update/rollback.
- Abschluss nicht durch Featurezähler, sondern durch beobachtete funktionsfähige Interaktionen und Canon-Ledger.

**Parallelität:** Phase A/B/C sollen sich überlappen und D/E beginnen als isolierte Lab-Probe, sobald Inputs existieren. F/G können unabhängig vorbereitet werden. Keine starre serielle „einen Mini-PR pro Stunde“-Sackgasse.

## R7. Agentenplan mit konfliktfreier Dateieigentümerschaft

Mindestens sieben Fachrollen können gleichzeitig arbeiten:
- Coordinator/Boss: Canon, Integrationsgraph, Release/PR-Review, Cross-Review mit Claude/Codex, Source-Ledger.
- Native/Android: llama.cpp LFM Hybrid/LFM2 QAD, Modell-/Tokenizer-Prefill, TTFT, PSS/RSS, Termux installer.
- A/Perception/Modalities: A0–A5, Audio/Vision/Student Projector.
- Body/B3/Enlightened Space: B1/B2 differenzieren, Native Hidden-Receiver, Message/Latent B3, Shared Space alle Organe.
- C/JEF/UI/Tools: C1–C7, Reflex/Antwort, Action Gate, Autoupdate/Bedienung.
- Memory/Self/World: Experience, SQLite Graph, Outcome, Replay, self-model, causal predictions.
- JEPA/Continual Plasticity: real Master/LoRA, EMA/optimizer state, World/Body, eligibility/three-factor.
- Research/Distillation/Licensing: neue Papers, OPD/SDFT/JOLT/OISD, external licenses, third-party ABI/release notes.
- Independent QA/Security: Retention/replay, Canary privacy, source-bound consent, Gerätedaten-Nachweise.

Eine Fachrolle bearbeitet eigene Dateien/Branchs. Shared Contracts nur nach kurzer Koordination ändern. Alle Arbeitspakete dürfen **vor** langer Geräteabnahme als isolierte Kandidaten gebaut und getestet werden. Keine Expertenrolle darf das Gesamtprojekt durch eine lokale Testpanne monopolisiert bekommen. Selbstständig neue Evidenz und alternative Opensource-Codepfade suchen; keine widersprüchlichen gleichzeitigen Edits. Agenten schreiben nach jedem substantiellen Schritt einen knappen Patch-/Consumer-/Claim-Bericht, nicht nur „alles grün“.

## R8. Reuse-first Entscheidungsbaum

1. Gesuchtes Feature / exakter Consumer und SourceRef-Contract benennen.
2. V13 Repo nach aktueller Implementierung, Staged Candidate, Tests und historischen PRs durchsuchen.
3. Aktuelle öffentliche Quellen suchen (GitHub, primäre Papers/Docs, einschlägige Implementierungen und Lizenz).
4. In Tabelle: Lizenz-Befund, Modell-/Gewichts-Befund, Kompatibilität/ABI, benötigter RAM und Aktivierungsaufwand.
5. Drei Optionen vergleichen: bestehender interner Code, externes Modul, eigener schlanker Adapter. Kleinsten **echten** Integrationstest auswählen.
6. Unter eigener Branch bauen; vollständige Outcome-Kante und Readback statt Standalone-Demo. Smoke, Regression, Retention/negative gate, Review.
7. Nur abgestimmte, geprüfte Integrationen in gemeinsamen V14-Zweig; sichtbarer nicht-funktionierender Testfall ist kein Grund, andere Module nicht weiterzubauen.
8. Wenn zweimal kein substanzieller Fortschritt: Research wechseln, upstream nach Issues/Workarounds prüfen, alternativen trainierbaren Port testen; Ergebnis im Research-Log dokumentieren statt weiteren Minipatch.

## R9. Messplan: Wie V14 Fortschritt tatsächlich definiert

Messungen sind **nicht** ausschließlich CI-Grün. Primäre Metriken:
- Nachweis, dass jeder Organ-Producer mindestens einen echten Consumer hat; EventTrace, Versionsbindung und Drop/Censor erklären.
- Median/p95 TTFT, Tokens/s, Hardware-Warm-/Cold-Last, PSS/RSS, Battery/thermal, Antwortquote über Inputkomplexität; Kurzfragen dürfen keine langen Wartezeiten haben.
- B1/B2 **komplementäre** Verbesserung gegenüber B1-only/B2-only/C3-only und NO_MESSAGE/SOURCE_EXACT/B3 Latent-Ablation.
- Gedächtnis: Quellenbindung, Wiederauffinden, Paraphrase, false memory, Widerruf, pro Session Restart.
- Lernen: trainierbare Deltas, EMA/Optimizer checkpoint, holdout utility, Retention, Forgetting, Generalisation, real zweite Chance; separate Testreife.
- Distillation Head: vorgeschlagene Masken/Schrittgrößen gegen tatsächlich beobachteten Nutzen, Nullhypothesen und Ressourcenverbrauch.
- Bedienung: install, dashboard, update, auto-update, restart, cancel und rollback ohne fehlerhafte Statusanzeigen; Nutzerinteraktionen vollständig privat.

Jeder Claim hat \`Observed / Simulated / Planned\`, SHA der laufenden Quellen, Modellrevision, Gerät, Datenscope, Vorher/Nachher und What-this-does-not-prove. Keine „fertig“-Markierung allein durch JSON/Wire/Mocks.

## R10. Recht, Sicherheit, Responsible Reuse – konkrete Checks

Bei fremdem Code: LICENSE prüfen, alle Dritt-Lizenzen vollständig beilegen, COPYRIGHT behalten, NOTICE pflegen, Änderungshinweise und Quellenrevision in SBOM; keine Umgehung von Lizenz oder Rechte für ein „geheimes Repo“. Bei Gewichten: zusätzlich Modellkarte, Download/Redistribution/Commercial/Usage Restrictions prüfen. Keine Lizenzannahme allein aus „Open Weights“. Private Nutzertexte nur unter tatsächlicher Trainingserlaubnis in den Learner; Cloud Teacher optional und nicht als stiller Abfluss. No external act without per-class consent / approved action. Selbständerungen nur in eigens angelegtem Source/Weight-Lab mit Rollback und Vergleich.

Dokumenten-/Codearbeiten, die eindeutig unter permissiven Lizenzen stehen, dürfen nach Checks adaptiert werden. Bei unklarem Lizenzstatus nur algorithmische Idee beschreiben und eigenständig entwickeln. Dies ist eine technische Due-Diligence-Arbeitsregel, keine individuelle Rechtsberatung.

## R11. Offene Forschungsfragen und explizite Entscheidungen

- **OPSD-Paper-Identität:** Der vom Nutzer erwähnte exakt *tagealte* Beitrag ist anhand des beschreibenden Titels nicht eindeutig identifiziert; SDFT/JOLT/SeOPD/OISD/Nov-OPSD sind belastbare nahe Kandidaten. Keine Behauptung „wir haben das exakte Paper“.
- **JEPA×KD-Kausalität:** Sind latent prediction und token-level self-distillation komplementär oder nur zwei Wege zum selben Proxy? Nur Ablation kann dies zeigen.
- **Gradientenfluss:** Wird „predicted weight delta“ mittels echter differentiabler Meta-Optimierung oder validierter lokaler Eligibility lernt? Propose-only zuerst, keinesfalls blind Base-GGUF schreiben.
- **Privileged Teacher:** Verifiziertes Outcome statt selbst bestätigter Antwort; Teacher besser in Training ≠ Student besser in Generation.
- **Native Hidden State:** LFM2.5/QAD/ggml aktivierbare Layer-Export-Schnittstelle ohne enorme Prefillkosten; Version pinnen und Real-Phone-Probe.
- **Mehrfach-Training:** Interferenzen B1/B2/C3/World, forgetfulness, sample bias, action-source trust, gerade bei 6GB-Klasse.
- **Self-edit:** sichere, überprüfbare Modulversionierung und neue erlaubnisgebundene Tool-Arten; kein autonomer Release-Merge.

## R12. Arbeitspaket-Register und verpflichtender Abschluss

Jede Canon-Pflicht (einschließlich IH-H0–H36, AG-, G-, A/B/C/F-, WP-, R-, B3-H und späterer PR-Ideen) muss als stabile ID im Implementierungsledger erscheinen: \`id, origin, requirement, current_code, producer, consumer, status, effect_measure, license, owner, test, hardware, next_action, rollback, alternatives\`. Das V13-Original und die drei Drive-Roadmaps werden im V14-Master **unverändert als historische Volltexte angehängt**; aus diesen müssen beim nächsten automatisierten Parser-Lauf vollständige ID-Listen erzeugt und mit Registry verglichen werden. Fehlende IDs sind **offen** und dürfen nicht wegdefiniert werden.

Der Coordinator integriert funktionsfähige vertikale Pakete unabhängig von sekundären Spezialforschungen. Ein abgebrochener Update-Test oder JEPA-Ablation darf nicht alle anderen Arbeitspakete stoppen. Der Nutzer bekommt regelmäßig konkrete Nutzbarkeit, nicht bloß Reports. Die stündlichen Agenten müssen die neue V14-Branch/Docs als **Plan** lesen und mit echten Änderungen fortsetzen; bisherige V13 Release-Branches bleiben unverändert, bis eine geprüfte Migration existiert.

## R13. Quellenverzeichnis und Erstprüfung (2026-11-19)

**Eigene Quellen:** [V13 GitHub](https://github.com/RedMentos/Aii), \`v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md\`, \`AGENTS.md\`, \`v13/ROADMAP.md\`, \`v13/code/BUILD_STATE.json\`; Drive ROADMAP 1/2/3, SICHTUNG, Handoff und Originalarchiv. Zuletzt integrierte Build-first-Regeln: [PR #2083](https://github.com/RedMentos/Aii/pull/2083).

**Upstream-/Paper-Originale:** [llama.cpp](https://github.com/ggml-org/llama.cpp), [ExecuTorch](https://github.com/pytorch/executorch), [River](https://github.com/online-ml/river), [Avalanche](https://github.com/ContinualAI/avalanche), [V-JEPA 2](https://github.com/facebookresearch/vjepa2), [TRL Distillation](https://huggingface.co/docs/trl/main/en/distillation_trainer), [TRL SDPO](https://huggingface.co/docs/trl/main/en/sdpo_trainer), [SDFT 2601.19897](https://arxiv.org/abs/2601.19897), [OPSD 2601.18734](https://arxiv.org/abs/2601.18734), [JOLT 2610.10447](https://arxiv.org/abs/2610.10447), [SeOPD 2609.33181](https://arxiv.org/abs/2609.33181), [OISD 2605.29089](https://arxiv.org/abs/2605.29089), [Stabilizing Guidance 2611.05266](https://arxiv.org/abs/2611.05266), [ECOS 2611.12232](https://arxiv.org/abs/2611.12232), [OPSD Guidance Audit 2611.16064](https://arxiv.org/abs/2611.16064), [STONE 2611.18916](https://arxiv.org/abs/2611.18916).

**Scope:** Einige aktuell sichtbare Primärseiten und Lizenztexte wurden überprüft; große Dritt-Repositories wurden **nicht** zeilenweise auditiert und ihre komplette transitive Lizenzliste noch nicht aufgeschrieben. Keine fremden Programmdateien wurden in diesem Dokument kopiert. Diese Vorprüfung erlaubt die **Entscheidung, was als Nächstes zu testen ist**, nicht die automatische Weiterverbreitung von Fremdsoftware.

---

**Ende Teil 2.** Darunter folgen im V14-Master die unverändert erhaltenen Volltexte des bisherigen V13-Canons und der Drive-Roadmaps als verbindliche Preservation-Anhänge. Neue V14-Arbeit muss *an diesen gesamten Umfang* rückgebunden werden.
