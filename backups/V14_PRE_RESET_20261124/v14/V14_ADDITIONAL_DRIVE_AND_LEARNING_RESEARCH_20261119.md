# V14 – ergänzende Drive-Sichtung und vertiefte Lern-/Lizenzforschung
**Datum:** 2026-11-19
**Rang:** Ergänzung zu [V14 Master Blueprint + Research](V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md), ausdrücklich **keine zweite kanonische V14-Version**.

Diese Datei bewahrt wichtige historische Materialien aus Drive, die im großen Master nicht vollständig enthalten waren, und konkretisiert die Kopplung von Outcome-Fehlern, JEPA, Self-Distillation und selbsttestendem Code-Umbau. Der V14-Master enthält bereits den gesamten V13-Canon, die GitHub-Entwicklungsroadmap und alle drei Drive-Roadmap-Teile. Wir duplizieren sie hier bewusst **nicht**.

Nicht aus dieser Ergänzung ableiten: eine bereits aktive mobile Gewichtsänderung, echte native Latent-Injection, eine funktionierende Self-Editing-AGI oder irgendeinen Redmi-Erfolg. Die historischen Quellen können überholte Statusangaben enthalten; der aktive Laufzeitbeweis bleibt getrennt.

## Recherche-Ergebnis: Distillation und die eigene JEPA-Lernidee
- Paper [Speculative Self-Distillation](https://arxiv.org/abs/2611.12016) vom 09.11.2026: Der Student schreibt die Rollout-Tokens normalerweise selbst; an großen Teacher-/Student-Verteilungsabweichungen interveniert der Teacher. **Forward-KL-Training bleibt an jedem Token aktiv**, Intervention und Supervision dürfen nicht verwechselt werden.
- Publizierter [SSD-Code](https://github.com/ShayanTalaei/SpeculativeSelfDistillation): **Apache-2.0**, CUDA-/vLLM-Basis, zwei sehr große GPUs laut README. Daraus eine kleine V14-Mobile-Variante zu entwerfen ist **eigene Entwicklungsarbeit**. Modellgewichte, Datasets und Dependencies brauchen separate Prüfung.
- [SDFT-Paper](https://arxiv.org/abs/2601.19897) und öffentliches [idanshen/Self-Distillation](https://github.com/idanshen/Self-Distillation): Das Repo zeigte beim Check keine LICENSE-Datei; nur als Forschungsquelle verwenden, solange keine Nutzungsrechte geklärt sind.
- Ziel des V14-Labors ist **kein** Selbstzweck, hohe KL-Divergenz zu belohnen. Drei getrennte Quellen: teacher-student uncertainty/logits, JEPA-Latent-Prediction-Error, tatsächlich beobachteter Outcome-/Omission-Error. Ein kleiner Meta-Predictor kann die Wirksamkeit eines möglichen erlaubten Updates schätzen; echte lokale Gradienten/Eligibility/Modulation und Retention bleiben erforderlich. A/B: JEPA allein, SSD allein, beide, beide+Outcome, jeweils mit/ohne Replay.
- Klassische Dopamin-/TD-Experimente zeigen Reaktion beim Hinweisreiz und eine **Absenkung** beim erwarteten Zeitpunkt einer fehlenden Belohnung, nicht die universelle Regel, dass Zellen einfach unendlich weiterfeuern. Lernhypothese: typisierte, zeitbegrenzte Erwartung und observierbare Auslassung, die eine korrekte frühere Beobachtung nicht rückwirkend „falsch“ macht.
- **Video-Hinweis des Nutzers:** https://youtu.be/XgVm8Nxz68Q wurde am 19.11.2026 nicht zuverlässig mit Transkript verifiziert. Erhalten als Research-Eingang, ohne erfundene Inhaltsbehauptung.

## Technische Konkretisierung (ergänzende Ausarbeitung)


### K1. Outcome prediction & timing

## A4. Zeit, Aufmerksamkeit, Ziele und das Ausbleiben erwarteter Ereignisse

User-Hypothese: Ein Hinweisreiz (Licht) sagt ein späteres Ereignis (Futter) voraus; Lernen soll sowohl Ankunft als auch zeitliche Auslassung/Fehlschlag verwenden. Dies darf **nicht** wörtlich als behauptetes dauerhaftes Dopaminfeuern implementiert werden. Neurophysiologisch ist gut belegt: Überraschende Belohnung erzeugt positive, der gelernte Hinweisreiz frühe und die überraschende Auslassung zum erwarteten Zeitpunkt negative Reward-Prediction-Error-Signale. Unsichere Zeitvorhersage und verborgenes Zustandsinferenz sind wichtiger als ein simples „warten bis kein Futter kommt“.

V14 führt deshalb **Persistent Expected Outcome / Pending Outcome Ledger** ein, ohne eine einzige Zielart zu privilegieren:
1. Wahrnehmung und Ziel getrennt registrieren: Licht erkannt ist wahr, auch wenn die Futterprognose später falsch ist. Handlungsvorschlag, erwartetes Ereignis, erwarteter Zeitpunkt/intervall, Konfidenz, Handlungskontext und Evidenz besitzen eigene IDs.
2. Eine Vorhersage kann PENDING, OBSERVED_ON_TIME, OBSERVED_LATE, OMISSION_CONFIRMED, CENSORED_UNOBSERVABLE, CANCELLED, SUPERSEDED, UNKNOWN heißen; bloß kein Signal ≠ sicher fehlgeschlagen.
3. Bei einem zeitgebundenen Ereignis berechnen Predictor/Value-Heads ein kontinuierliches Fehlersignal nach TD-/TD(lambda)-Idee und/oder eventbasierter Überraschung. Fehlersignal und Eligibility sind organ- und quellenbezogen; nicht jedes Missverständnis darf jedes Gewicht verändern.
4. Erwartungsintervalle können von zuverlässiger Uhrzeit über hazard/distribution bis zu unbekannt reichen. Nach Ablauf aktualisieren sich falsifizierbare Prognose und Vertrauensgrad. Kein endloses feuern, keine erzwungene extern wirkende Aktion, keine autarke Jagd nach „Futter“.
5. Langzeitziele werden in überprüfbare Teilziele und Informationserwartungen zerlegt. Eine Zielhypothese darf hinterfragt, pausiert, abgewählt oder durch Nutzerkorrektur überschrieben werden.
6. Neben Reward-Werten: epistemische Überraschung, Prognosegüte, Kausalitätskontrolle, Fehlermodell, Ressourcenstress, menschliche Rückmeldung und Negative Transfer getrennt beobachten. Keine Belohnung für bloß hohe Aktivität, Selbstbestätigung oder zielloses Token-Erzeugen.
7. Ablation: nur signierte positive Outcomes versus plus zeitliche Auslassungen versus auch CENSORED/Unobservable, mit adversarial delayed/false-omission Kontrollaufgaben. Beurteilung durch Kalibrierung, Second-Attempt, Brier/Logloss, retention, Fehl-Aktionen.


### K2. Multi-level plasticity, JEPA and speculative distillation

## A6. Lernarchitektur als Vielschicht-System — kein einziger magischer Algorithmus

**Level 0, immer verfügbar:** Nutzerfeedback, Quellen, Korrektur, Commit-Status, Exact Memory, Episoden und Instrumentierung. Keine ungewollte Parameteränderung.

**Level 1, kleine Online-Heads:** Route/Wake/Halt, Attention/Salience, C2, Prognose-/Outcome-Head, Projector, Calibration und Self/World-Head mit messbarem eigenem Lernzustand; je eigenes Update-Scope und Rückrollgrenze.

**Level 2, JEPA/EMA:** Student/context encoder, Predictor, Slow/EMA target, StopGrad, cross-view/action-conditioned latent forecasting, eigene lokale Gradienten. Weight learning kann in kleinen Adaptergewichten/Projectoren beginnen; echte pretrained Basisgewichte oder große LoRA-Adapter brauchen explizite Train-Runner-Proofs. Das eingefrorene Target ist ein Lernsignal, kein allwissender Wahrheits-Teacher.

**Level 3, Eligibility × Error × Modulation:** Typisierte Eligibilities markieren welche lokalen Parameter/Events zu einer Vorhersage beigetragen haben. Der tatsächliche Gradient/lokale Fehlerschätzer bestimmt die Richtung; Modulatoren (Evidenz, Neuheit, Vertrauen, Risiko, Nutzen, Zeit) skalieren oder blockieren sie. Quelle, Ziel, Gate und Trainer müssen nachvollziehbar übereinstimmen. Homeostasis, slow consolidation, drift, anchor retention und replay begrenzen Überschreiben.

**Level 4, Self-Distillation / Knowledge Internalization:** Wählbarer Teacher (frozen same-model mit Zusatzkontext, EMA past self, validierter unabhängiger Teacher, frühere Version) stellt distributionsbasierte, quellgebundene oder latent-space Zielgrößen bereit. Der Student trainiert auf eigenen Zuständen und, bei geeigneter Evidenz, auf vom Teacher korrigierten Inflection-Positionen. Kein Verschmelzen von distillation, rehearsal, JEPA und RL unter einem Namen.

**Level 5, B1↔B2/C3 gegenseitiges Lernen und Cross-Organ-Plastizität:** Organe dürfen kleine Projektoren, Expertenadapter, Vorhersageköpfe oder kontrollierte Deltas voneinander beeinflussen, erst im Shadow, dann nach geprüfter Beförderung. Fremdes Organ wählt nicht direkt unkontrolliert den Basisgradienten eines anderen. Vor jedem tatsächlichen Update: Zielgewicht, Gewichtrevision, mathematische Operation, signierte Quelle, local loss, bounded delta, Effekt/Retention und Rollback.

**Level 6, Dreaming/Sleep/Replay:** Offline oder idle, mit Trennung echter Erinnerung von simuliertem Kontrafaktum. Replay/Reconstruction, source-checked consolidation, Verteilungskontrolle, Gegenfaktualität, Abnahme auf unverändertem Test und erwarteter Mehrwert. „Dreamed“ ist niemals automatisch „true“.

**Level 7, adaptive Selbstverbesserung:** Verbesserungsvorschläge für Routing, Algorithmen, Speicher, Architektur, Code und Trainingsmethoden; formal überprüfbare Experimente, Tests und Deployment-Handover. Langfristig darf jede gewöhnliche Implementierungszeile aus ursprünglichem Menschen-/Assistentencode ersetzt werden, solange die wirksamen Sicherheitsverträge, Autorisierung und unabhängig überprüfbare Testmechanismen erhalten bleiben. Es gibt kein Vermarktungsversprechen, dies derzeit zu können.

## A7. Neue Lernoption: Speculative Self-Distillation × JEPA

**Wissenschaftlicher Bezug:** Talaei et al., „Speculative Self-Distillation enables Efficient Knowledge Internalization“, arXiv:2611.12016, veröffentlicht 09.11.2026; Open-Source-Code unter Apache-2.0. Shenfeld et al., „Self-Distillation Enables Continual Learning“, arXiv:2601.19897 / ICML 2026. Das neue SSD-Paper nutzt Student/Teacher-Vergleich der **Tokenverteilungen**; nur an Inflection-Positionen wird die *Rollout-Policy* zum Teacher gewechselt, der Distillationsverlust wird weiterhin an allen Positionen gemessen. Das ist nicht identisch mit trainierten JEPA-Predictor-Heads.

**V14-Experiment — Multi-Head Predictive Guidance (MPG) [NEU, HYPOTHESE]:**
- Teacher mit zusätzlichem geprüften Source-/Outcome-Kontext, Student ohne ihn; Divergenz pro Token und pro geschütztem Latent-Head bestimmen, wo zusätzlicher Lernwert vermutet wird.
- Erzeuge drei **getrennte** Signale: D_token (Teacher–Student Logit-KL/JSD), D_latent (JEPA predicted–target error), E_outcome (realer verspäteter/negativer Outcome-Fehler). Vertrauensbewertete Quellen geben dem Teacher nie unbegrenzte Wahrheitsautorität.
- Kleiner *Meta-Gating-Head* wählt nur erlaubten Update-Pfad, Priorität und bounded Lernrate/Maskierung. Eigenes Update-Wirkungsmodell schätzt vorher delta-Kosten und erwartete Veränderungen des Verhaltens, lernt an echten nachfolgenden Messungen. Es editiert nicht allein unbegrenzte fremde Gewichte.
- Gradient bleibt vorhanden, wo mathematisch erforderlich. JEPA ersetzt Backprop nicht generell; auf dem Handy sind lokale Delta/LoRA-/ReFT-/Head-Updates oder verglichenes eligibility-based learning plausible Kandidaten. Empirischer Test muss prüfen, ob der kombinierte Mechanismus mehr bringt als reine JEPA-, reine Self-Distillation-, Replay- und kleine LoRA-Baselines.
- Schutz gegen self-confirming Teacher, Konflikte zwischen Modalitäten, unerwünschte Überkonfidenz und Katastrophal-Vergessen: zwei unabhängige Quellen, rejected examples, off-policy counterfactuals, real-world verifizierte Outcomes, masked retrieval, unveränderte Held-outs und Rollback.
- Ressourcen: Das publizierte SSD-Referenzsystem benötigt Linux/Python 3.12, zwei GPUs mit 80 GB Speicher und angepassten vLLM. NICHT auf Redmi installieren. Wir übernehmen Ideen/Algorithmen, bauen einen kleinen GGUF-kompatiblen/Kleinmodell-lab-adapter oder lernen periodisch auf stärkerem Rechner, wenn autorisiert. Wir dürfen die großen Modelldaten und ihre Lizenzen nicht mit dem Apache-2.0-Code gleichsetzen.
- Status: vorgeschlagener Forschungs- und Integrationspfad, keine gemessene V14-Verbesserung.


### K3. Human-visible staged self-rewriting

## A10. Selbstumbau, Generationenwechsel und Handover

Langfristiges Ideal: Der Agent schreibt/ersetzt immer größere Teile seines Programms und Lernsystems selbst. Dafür ist eine **Meta-Architektur** nötig:
1. Definierte austauschbare Organe mit Stable ABI, typisierten Zuständen, Quellen-/Trainings-IDs, Grenzen und abstrakten Capability Contracts.
2. Self-Inspection liefert Version, Kosten, Fehler, Unsicherheiten und konkret messbare Optimierungskandidaten, nicht versteckte Introspektion.
3. Propose/Edit in Branch/Sandbox; exakte Diff und menschenverständliche Erklärung der Testfälle; Tests zeigen gewünschtes und unerwünschtes Verhalten.
4. Shadow-run gegen dieselben Inputs/benutzbare Replay-Quellen und unveränderte Retention/Privacy/Gegenbeispiele, danach real-device small-sample.
5. Externe Sicherheits- und Genehmigungsschicht prüft nicht nur eine Textzusammenfassung des Agents, sondern ausführbare Artefakte, Toolrechte, Datenflüsse und Rollback.
6. Versionsmigration je Speicher/Modelldelta mit zwei Generationen über eine Übergangsfrist. Alt trainiert/prüft neu; schnelle Rückkehr bei Qualitätsverlust. Gleichzeitige Veränderungen an vielen trainierenden Organen werden attributionstechnisch getrennt.
7. Nach erfolgreichem Übergang ist neue Codegeneration wirklich aktiv; unerwiesene Updates bleiben branch-/shadow-gespeichert. Ein selbst geschriebenes Testpaket allein darf keine eigene Änderung freigeben.

Selbstoptimierung ist kein bloßes Prompt-Edit oder zufälliges AutoML: das Endziel umfasst echte Organ-übergreifende Parameteränderung, Steuerung der Lernregel und später Programme/Kernels. Ziel und Sicherheitsanforderungen bleiben erhalten, auch wenn die frühe Hardware es noch nicht vollständig zulässt.


### K4. Upstream code and legal reuse matrix

## B2. Reuse-Portfolio und juristische Prüfung — Stand 19.11.2026

| Kategorie | Quelle | Lizenz des Codes / Recht | Konkreter V14-Einsatz | Entscheidung |
|---|---|---|---|---|
| Native GGUF Inference | https://github.com/ggml-org/llama.cpp | MIT, Lizenzdatei geprüft, Modelle gesondert | C3/B1/B2 Native Kern, mmap, KV/recurrent state, caching, prefills | Wiederverwenden und Profiling; keine Neuschreibung |
| Mobile Torch export | https://github.com/pytorch/executorch | BSD-Style, Lizenzdatei geprüft | Kleine Predictor-/EMA-/Projector-Kernels auf ARM | Optionen vergleichen, kein kompletter GGUF-Ersatz |
| Lightweight Tensor | https://github.com/tinygrad/tinygrad | MIT, Lizenzdatei geprüft | Forschungs-Backend für kleine plastische Organe | Eignung und Android-Dependencies prüfen |
| Online learning | https://github.com/online-ml/river | BSD-3-Clause, Lizenzdatei geprüft | Online Drift/Scoring/Classifier/Eligibility-nahe Kopf-Baselines | Nur kleine Module übernehmen; Termux-Wheels prüfen |
| Continual Learning | https://github.com/ContinualAI/avalanche | MIT, Lizenzdatei geprüft | Externe Eval: Replay, forgetting, retention | Off-device Forschungs-/Testvergleich |
| JEPA Referenz | https://github.com/facebookresearch/vjepa2 | MIT Root, Lizenzen einzelner Abhängigkeiten/Gewichte separat | EMA/Masking/Latent Objective Architektur | Konzept/kleine zulässige Teile, kein Full Mobile Port |
| Self-distillation | https://github.com/idanshen/Self-Distillation | **KEINE LICENSE-Datei im veröffentlichten geprüften Repo nachgewiesen** | SDFT/On-policy-FKL Forschung | Konzept aus Paper beschreiben; keinen fremden Code übernehmen ohne Rechteklärung |
| Speculative Self-Distillation | https://github.com/ShayanTalaei/SpeculativeSelfDistillation | Apache-2.0, LICENSE geprüft; Dritt-Daten/Weights extra | Distillations-Signale/Inflection-Probe, FKL/KL | Nur stark verkleinerte/adaptierte Variante auf Mobile; Referenzcode GPU-only |
| Edge Agent | https://github.com/Cactus-Compute/cactus | Apache-2.0, Root-LICENSE geprüft; jeweilige Model Card extra | Vergleich C2/C3/Perception/native ARM runtime | Lizenzkompatibilität/ABI/echte Messung prüfen, kein blindes Vermischen |

Lizenzfreigabe benötigt zusätzlich: upstream commit/tag und SHA, Dateikopf/Unterlizenz, Copyright/NOTICE, Datenherkunft, Modellgewichtsbedingungen, lokale Export-/Netzrechte, transitive Abhängigkeiten, Vertriebskontext, Reproduzierbarkeit, Rücknehmbarkeit. BSD/MIT/Apache-2.0 sind keine Freistellung von Drittgewichten, Datensätzen oder Markenrechten. GPL/AGPL/CC-BY-SA dürfen nicht unter „ist Open Source“ ohne Pflichtenprüfung übernommen werden. Fehlt eine Lizenz, wird kein Code kopiert. Öffentlich zitierte Algorithmusideen lassen sich eigenständig aus dem Paper implementieren, ohne große Blöcke fremden Codes zu kopieren.

## B3. Forschungsbibliothek — priorisierte neue Erkenntnisse

- Speculative Self-Distillation (09.11.2026), arXiv:2611.12016: tokenbasierte Divergenz für **selektive Teacher-Rollout-Intervention**, Forward-KL an allen Positionen. 38–69 % weniger supervisierte Tokens in ausgewählten Closed-Book-QA-Tests; nicht bereits mobile Effizienz und nicht direkt JEPA. Code: Apache-2.0, 2 GPUs mit 80-GB-Anforderung im README. V14: nur den kleinen Entscheidungs-/Loss-Prototyp als eigenständige Hypothese.
- Self-Distillation Enables Continual Learning, ICML 2026 / arXiv:2601.19897: on-policy Lerntrajektorien, stärkerer Wissens-/Skill-Erhalt als einfache SFT in den dokumentierten Aufgaben. Repo ohne sichtbare Lizenz: wissenschaftliche Referenz, keine kopierte Implementation.
- Continually Post-training Small Models via Synthetic Self-distillation, arXiv:2610.13113: Kandidat für kompakte Modellgrößen und Retention; zunächst reproduzieren, nicht als generellen Erfolg behaupten.
- Learning without Overwriting, arXiv:2610.05200: Theorie zu sparse structured on-policy distillation versus dichtem SFT; Einsicht für Maskierung, nicht Beweis des eigenen V14-Metagates.
- Schultz, Reward-prediction timing/omission (1997/1998) und TD(lambda): Hinweisreiz, Belohnung, Auslassung und Zeitpunkt unterscheiden. V14: Pending Outcomes + zeitlich bewertete Ungewissheit; keine anthropomorphisierende „dauerhafte Feuerschleife“.
- Die vom Nutzer genannte Video-URL https://youtu.be/XgVm8Nxz68Q konnte am 19.11.2026 nicht verlässlich über ein öffentlich auslesbares Video-Transkript/Metadaten bestätigt werden. **Nicht** behaupten, den Inhalt zu kennen; als zu klärende Quelle vermerken.


---

# Historische zusätzliche Drive-Quellen (unverändert als Archiv, nicht aktuelle Betriebswahrheit)


## Archiv D1 — Original Drive-Sichtung historischer ZIP-Inhalte

**Original aus dem verbundenen Google Drive; bewusst als historische Primärquelle erhalten.**

# V13 Sichtung der kompletten Übergabe (2026-10-09)

Gelesen: das ganze ZIP `V13_INQUISITION_KOMPLETT_NEUER_CHAT_2026-10-09.zip` (418 MB, 164 Einträge):
30 Blueprint-Fassungen v4.0 bis v10.16.1, 23 Programmversionen (inkl. 7 Standalone-Prototypen),
alle Entscheidungs- und Statusdateien, der 5-MB-GLM-Chat „AI-Consciousness-Blueprint-Theses“ und das
Positionspapier des Nutzers zu KI/Zensur/Privatsphäre. Abgeglichen gegen Blueprint v10.16.1,
`ROADMAP.md` und den aktuellen Code `code/`.

Die sieben Einzelberichte mit Zeilen- und Abschnittsangaben liegen in `sichtung/`
(`old_blueprints.md`, `blueprint_evolution.md`, `old_code.md`, `code_audit.md`, `chat1-3.md`).
Diese Datei fasst sie zusammen. *(E)* = Einschätzung, nicht gemessen.

## 0. Was in den Projektordner kopiert wurde (nur hinzugefügt, nichts überschrieben)

| Ziel | Inhalt |
|---|---|
| `code/docs/proofs/` | 2 083 kleine Proof-Dateien + 58 in der Doku referenzierte größere (u. a. `native46-failed-report.json`, eingefrorenes Acceptance-Archiv). SQLite-Proof-DBs der STEP2-Zustandsprüfung weggelassen. |
| `code/docs/canon/` | Blueprint-Kopie, die die Tests erwarten. Damit laufen **425/425 Unit-Tests grün** (vorher 16 Fehler wegen fehlender Dateien). |
| `archiv/blueprints/` | alle älteren Blueprints v4.0 bis v10.16 als Markdown |
| `archiv/entscheidungen/` | alle USER_DECISIONS-Fassungen |
| `archiv/chat/GLM_AI_Consciousness_Chat.txt` | Klartext des 12-MB-JSON-Chats (363 aktive Nachrichten) |
| `archiv/architektur/` | Codeaudit, Evidenz-JSON und SVG des Architektur-Pakets vom 09.10. |
| `archiv/KI_Zensur_Privatsphaere_Grundbasis.md` | Positionspapier des Nutzers |
| `salvage/` | verlorener bzw. wiederverwendbarer Code, siehe `salvage/README.md` und Abschnitt 2 |

Nicht kopiert: Architektur-PNGs (je 2–3 MB, nur Bilder), alte Runtime-ZIPs (Inhalt ist im neuesten enthalten), große Trainings-JSONs der Norm-Experimente.

## 1. Wichtigste Befunde

1. **Unbemerkter Codeverlust vom 06.10.** Die Arbeit aus burst3–5 fehlt im aktuellen Stand, ohne Vermerk in BUILD_STATE,
   Ledger oder Recovery-Doku. Alle späteren Stände bauen auf `auto-burst2` auf; bei den Wiederherstellungen 07.–09.10.
   wurde der burst-Zweig nicht übernommen. Verloren: `v13/body_training.py` (fail-closed Body-Train-Port-Vertrag) mit Test
   und Proof, `native_capability_profile`, der STEP2-`task_score`, ein Executive-Bugfix und acht Tests.
2. **Dadurch ist ein alter Bug zurück:** `code/v13/executive.py:96` übernimmt `previous.get('active_task')`. Die erste
   Nutzerfrage einer Session bleibt für immer `active_task` und landet in jedem nativen Kontext. Fix + Test liegen in
   `salvage/executive_implicit_task/` (nur gelesen, nicht ausgeführt).
3. **Die zentrale Designzusage „zwei verschiedene MoE-Hälften“ wurde still aufgegeben.** v7.1/v9 hatten sie LOCKED, der
   Nutzer fordert sie im Chat mehrfach („KEINE DICHTEN MODELLE“, Detail mit mehr aktiven Experten). Heute laufen B1 und B2
   auf derselben dichten LFM2.5-1.2B. Das ist die wahrscheinlichste Ursache für STEP2 `UTILITY_FAIL` *(E)*.
4. **Gefährlichster Doku-Widerspruch:** Die Alias-Firewall IH-H1 bildet legacy „A“ auf Detail ab. Das stimmt nur für v4/v5
   und ab v10.4. In v6 bis v10.3 war A = Gist. Wer alte Texte über IH-H1 liest, vertauscht die Hälften.
5. **Billige Schutz- und Messregeln aus v4/v5 fehlen ganz:** Datenmix-Quoten mit 2-%-Rollback, Kollapswächter,
   Zitat-/Abstention-Regel, Decoder-Parameter mit `min_new`, Zahlen-Gates der Könnenstreppe S1–S4. Alle handytauglich.
6. **Die alten Standalone-Prototypen taugen nicht als Vorlage.** Ihre eigenen Audits melden PASS, der Code tut es nicht
   (LoRA-Update läuft nie, Konsolidierung ist No-op, Training sieht Zukunftstokens). Brauchbar sind nur ein maskiertes
   JEPA mit EMA (`code (26).py`) und der saubere v10-Starter.
7. **Der Nutzer hat Anforderungen formuliert, die nirgends stehen** (Abschnitt 4), u. a. zu Zensur/Privatsphäre,
   Termux-Bedienung und „Thesen > Blueprint“.

## 2. Verlorener oder nie umgesetzter Inhalt

### 2a. Code (Details: `sichtung/old_code.md`, Kopien in `salvage/`)
| Was | Prio | Empfehlung |
|---|---|---|
| `body_training.py` Train-Port-Vertrag | A | zurückholen (WP-I/S6). Requantizer-Pflicht braucht Ausnahme für FP32-Slices wie `token_embd_norm`. |
| `native_capability_profile` | A | zurückholen, aber als neuer Befehl `:native`, weil `:capability` jetzt `age.py` gehört. Heute ist `'body_training':False` in `world.py` hart verdrahtet. |
| Executive-Fix implizite Aufgabe | A | sofort zurückholen (Bug, siehe 1.2) |
| STEP2 `task_score` | A | für WP-G (STEP2 neu messen) |
| v10-Starter (Eligibility mit TTL, Inferenz vor Training, Admissions-Checkliste für Modellpaare) | B | Referenz |
| I-JEPA + EMA + VICReg mit Kovarianzterm (`code (26).py`) | B | Referenz für WP-S4; `predictor_worker.py` hat keinen Kovarianzterm |
| Top-k + Overflow-KL aus `inquisition_rsi.py` | B | passt zum Drift-Gate WP-S5 mit llama-server-Logprobs |
| LoRA-Slow-Merge, SparseMoE-Losses (v1.1) | B | nur falls MoE-Body kommt |
| Regelvorschläge mit Digest/Stale-Check (Termux v11) | B | Vorlage für Age-Fähigkeit `propose_config_changes` |

### 2b. Alte Blueprints v4–v10.2 (Details: `sichtung/old_blueprints.md`)
Verloren oder stark abgeschwächt, mit hohem Nutzen *(E)*:
- Datenmix-Quoten (≥ 60 % Mensch, ≤ 10 % selbst erzeugt, Dream ≤ 5 %) + Rollback bei > 2 % Verlust auf alten Sets (v4 §24, v5 §28).
- Kollapswächter: Wiederholungsrate, Typen-Vielfalt, Selbstzitat-Rate, Abstention-Rate, Drift (v4 §63). Rein lexikalisch, sofort nützlich gegen „query echo“.
- Decoder-Parameter (temp 0,6, top_p 0,95, top_k 20, min_p 0,05, no_repeat_ngram 4, rep 1,08) und `min_new=8` (v4 §64–66).
- Zitatregel (≤ 2 Zitate, Nutzerversion gewinnt) und Abstention-Form „nichts Belegtes, ich vermute:“ (v4 §21–22).
- Zahlen-Gates S1–S4 als Startwerte für die Age-Hülle (v4 §27, v9 §45–53); heute [OPEN].
- Stabilitätshülle pro Zyklus: max. Update-Norm, Route-Shift, Workspace-Drift, Kalibrier-Shift (v8 §42).
- Invarianten als Tests: „schlechtes Outcome wird nie negativer JEPA-Loss“, „Target bekommt keinen Gradienten, EMA bewegt sich, Optimizer isoliert“, „kein doppeltes LoRA nach Merge“ (Forschungs-BP v10, v7.1 §40).
- Getrennte Konfidenzen (Quelle vs. Antwort), epistemisch/aleatorisch (v8 §24, §36).
- „CAUSES-Kante nur nach Intervention“ (Forschungs-BP v10).
- Inquisition selbst (Cautiousness κ, P1/P2, adaptives N 1..7): Namensgeber des Projekts, seit v10.2 nur Scaffold, kein WP.

Fehlende Abnahmen: Lern-Abnahme v5 §54, Hardware-Abnahme mit Page Faults/Batterie v5 §58, voller Regression Shield mit getrennten Sets und modularem Rollback, Bridge-Test mit vertauschten Nachrichten, Strict-Key-Load, episodenbasierte Splits, Langzeitsitzung (v6 G15).

### 2c. Blueprint-Verlauf v10.3–v10.16.1 (Details: `sichtung/blueprint_evolution.md`)
Ab v10.10 gilt „Additive-Only“, danach geht kaum etwas verloren. Echter Verlust: der verworfene v10.6-Zweig
„Cross-Cache“ mit **„Re-entry statt Re-prefill“** und Cache-Lineage. Gerade auf 6 GB relevant *(E)*.
Außerdem wurde das Redmi-Gewichtsbudget ohne Begründung von < 1,5–1,8 GB auf 1,6–2,0 GB gelockert, und der
„Readiness Vector“ / „1 Änderung pro Laborzyklus“ aus v10.9 fiel weg.

Im Blueprint, aber ohne ROADMAP-Paket: Focal Coalition (§93), World/Self-Lernen aus Corollary (§85.7, G-SELF-WORLD-005),
typisierte Modulatoren + Objective Registry (§85.10, IH-H25), Context OS/Cache-Policy (§8.3–8.6, §74), Metaplastizität +
Representation Anchor (§68–69), KnobSpec (IH-H5), Delete-Lineage (IH-H20), BridgeKey (IH-H21) + Body Swap (G11),
C2-Benchmark Needle vs. FunctionGemma (§57, G12C), Event-Segmentierung (§9.3), Rules/Self-Edit/Goals (§20), Self Model.
Das Timescale-Gate §85.1 mit vier Kontrollen (same-model same-policy … true two-body) ist genau der Test für B1 = B2.

### 2d. GLM-Chat (Details: `sichtung/chat1-3.md`)
Der Chat (05.09.–Ende 09.2026) zeigt die Vorgeschichte: erst eigenes PyTorch-Netz von Null (nur Byte-Müll), dann
llama.cpp-Harness mit zwei GGUF-Modellen. Kern sind die Thesen T1–T10 und Ziele 2A–2G des Nutzers (`archiv/chat`, ab
ca. Zeile 10481 und 29443). Vieles steht heute im Blueprint (Callosum, Sleep, Rückfrage vor Regeländerung,
Neuromodulatoren, aktives Vergessen, Output-Garantie). Echte Lücken:
- **„Ausbrennen“-Budget:** ohne Input klingt die Aktivität ab, das System lernt, wann Pause ist, der Nutzer kann das Limit hochstellen.
- **Implizites Feedback** aus normalem Chattext (Lob/Kritik) und `note 1–10`-Bewertung. Hilft direkt gegen `INSUFFICIENT_LABELLED_COHORT`.
- **Termux-Bedienung:** Live-Logs dürfen getippten Text nicht überschreiben (readline-Neuzeichnen), mehrzeiliges Einfügen als ein Block, Kontext-Vorschau („was geht ins Modell“), Knobs live im Chat ändern, Pause-Befehle (`:pause selfedit|traum|training`).
- **Filter**, damit eingefügte Terminal-Logs nicht ins Gedächtnis gelangen.
- **Anti-Echo-Sampling / Wiederholungsstrafe** für C3.
- Neugier-Signal (RND), Notizbuch mit typisierten Kanten und 1-Hop-Abruf, abgesicherte Code-Ausführung als Grounding.
- Echte Redmi-Messungen aus dem Chat (nicht im Blueprint): OLMoE-7B 0,2 tok/s, fp32 22–32 GFLOPS, 3 Threads schneller als 4, mmap nur unter `$HOME`. Stützt die llama.cpp-Wahl.

Achtung: Ein persönlicher Text des Nutzers steckt in einem Trainingskorpus im Chat; nicht in V13-Daten übernehmen.

## 3. Toter Code und Aufräumkandidaten (Details: `sichtung/code_audit.md` §1)

**Vor jedem Aufräumen:** `scripts/verify_acceptance.py` und `scripts/acceptance.py` hashen alle Skripte, Tests und
`v13/*.py`. Jede Änderung macht ein laufendes `TESTEN.sh --resume` ungültig. Aufräumen daher gebündelt, wenn kein Resume läuft,
und nach `archive/` verschieben statt löschen (Proof-Manifeste verweisen auf die Dateinamen).

- Veraltete Duplikate: `code/completion-ledger.json` (es fehlen die drei Einträge vom 09.10.) und
  `code/USER_DECISIONS_AND_OPEN_QUESTIONS.md` (36 statt 94 Zeilen). Gültig sind die Fassungen in `code/docs/`.
- Ungenutzt: `docs/drafts/`, `docs/resume_acceptance.py`, `docs/check_resume_acceptance.py`,
  `scripts/checkpoint_step2_progress.py`, `scripts/compare_causal_runtime_decoder.py`, `scripts/test_live_output_adapter_port.py`,
  `scripts/test_live_output_export_native.py`, `scripts/test_native_midlayer_numeric_policy.py`, `effort.compare()`,
  `causal_output.source_revision()`, 16 ungenutzte Importe in `v13/`, 5 lose Snapshot-Dateien in `docs/`, `__pycache__/`.
- `age.py`: `open_window`, `gist_resolution` werden nur in Tests benutzt; Age wirkt also noch nicht auf Gist/Plastizität.
- 7 byte-gleiche `TESTEN_NATIVE_*.sh`-Wrapper → ein Dispatcher. `TESTEN_NATIVE_TRAIN.sh` trainiert nichts (Norm-Shadow-Diagnose).
- Veraltete Doku: `docs/RESUME.md` (Stand 01.10., README verweist trotzdem darauf), datierte Arbeitsnotizen → `docs/history/`.
- Tests importieren sich gegenseitig über bloße Modulnamen; nur mit `PYTHONPATH=.:tests` grün.

## 4. Nutzeranforderungen, die nirgends festgehalten sind

Aus dem Chat und dem Positionspapier. Gehören nach `code/docs/USER_DECISIONS_AND_OPEN_QUESTIONS.md`:
- **Thesen > Blueprint/Zahlen:** Bei Konflikt sollen T1–T10/2A–2G gelten; Zahlen sind Schätzungen. Mit dem Blueprint (LOCKED-Regeln) nicht abgestimmt.
- **Alles lernt permanent, außer Safety-Regeln.** Blueprint sagt: Age 0 = nur Shadow-Lernen mit Freigabe.
- **Zwei verschiedene MoE-Hälften**, Detail mit mehr aktiven Experten; kleiner vortrainierter Sprachteil, nichts von Null.
- **Englisch zuerst, Deutsch später als Lerntest** (Chat, 09.2026). Code und ROADMAP setzen heute auf Deutsch. Evtl. später geändert.
- **Regeln an realem Schaden, nicht an Themen oder Schlüsselwörtern.** Darstellung, Absicht, Kontext, Veröffentlichung, reales Handeln unterscheiden; private Fiktion erlaubt; bei Ablehnung Grund offen nennen.
- **Privatsphäre als Normalfall:** lokal, keine Inhalts-Telemetrie, externer Teacher nur mit ausdrücklicher Zustimmung, Löschen muss gehen. Regeln lesbar, versioniert, nur mit `y` änderbar.
- **Bedienung:** alles am Handy/Termux mit einem Befehl, komplette Dateien mit festen Namen statt `code (N).py`, keine Heredocs zum Einfügen, Befehle während des Laufs, kein Neustart für kleine Änderungen.
- **Ehrlichkeit:** nichts als „lernt“ oder „neural“ verkaufen, was ein Platzhalter ist; Fakt/Schätzung/Vermutung trennen.
- Zentrale Vorgabe aus BUILD_STATE: „complete plan and additions, not only diagnostics“.

## 5. Widersprüche

**Nutzerwunsch vs. Blueprint (Entscheidung beim Nutzer):**
1. Permanentes Lernen vs. Age-0-Shadow mit Freigabe.
2. Zwei verschiedene MoE vs. heute B1 = B2 = LFM2.5-1.2B (dicht). Zwei MoE à 4–5 GB passen nicht gemeinsam auf 6 GB *(E)*; MobileMoE-S-QAT (0,68 GB INT4) wäre klein genug, ist aber gated, FAIR-noncommercial und ohne Android-Runner.
3. „Keine LoRA“ (Chat) vs. LoRA/Deltas im Blueprint.
4. Englisch zuerst vs. deutscher C3-Benchmark.
5. Freies `/py`-Exec und Self-Edit (Chat) vs. Sicherheitsregeln.

**Innerhalb Blueprint v10.16.1:** latent 0.20 beim Boot (§54/§78) vs. latent aus (IH-H27, §96, B3-H5); C3-Zielgröße
50–150M / 100–300M / 230M; Lernreihenfolge Adapter vor Predictor (§22.2.4) vs. Predictor-first (§92.1, §88, B3-H8);
zwei Ressourcen-Zustandsmaschinen (IH-H23 vs. §97.2); Reasoning Effort als Zahl (§10.2) vs. Modi (G5B); viermal „L0“
mit verschiedenen Bedeutungen; Legacy-Namen C_fast/C_focal im Gate-Text; IH-H1 A/B-Mapping (siehe 1.4);
`arcxiv.org`-Tippfehler noch zweimal drin (Z. 7843, 9961); Training auf dem Handy (§90) vs. nur extern (§33.3).

**Doku vs. Doku/Code:** Acceptance-Stand je nach Datei 18/21, 6/20, 3/20, 2/20; BUILD_STATE-Kopf veraltet
(`completed_this_run`, `base_checkpoint`, `next_priority`); Ledger mit zwei sich widersprechenden Einträgen zum
Causal-Lifecycle und 19 Modulen ohne Ledger-Zeile; REMAINING_IMPLEMENTATION führt Erledigtes als fehlend und nennt den
SQLite-Blocker nicht; README verweist für STEP2 auf den alten Test und kennt `:age`/`:effort` nicht;
`USER_DECISION_REQUIRED: None`, obwohl Redmi-Lauf, echte Labels und Modellfrage offen sind. `Store.close()` prüft im
Produktivpfad keine Integrität und wertet das Busy-Ergebnis des WAL-Checkpoints nicht aus; der Integritätscheck läuft nur im Test-Collector.

**Verloren zwischen Versionen der Entscheidungsdatei:** MobileMoE-Zugang (HTTP 401) als Blocker, Redmi-DEADLINE-Abbruch
(Ursache unbewiesen), die konkrete Liste für Body-Training (Master, Runner, Requantizer, Revisionsbindung).

## 6. Forschung (nur was die Berichte bestätigt oder als relevant markiert haben)

Im Web bestätigt: MobileMoE (2605.27358), Needle 3, StateBridge (2608.13317), MeSP (2602.13069), „Language Models Need
Sleep“ (2606.03979), XKV, Mixture-of-Translators, KV-Cache-Alignment, LFM2.5-230M (laut Hersteller für Extraktion/Tool-Calls,
nicht für freies Schreiben, passt zum „query echo“). Viele 2026er-arXiv-Nummern in alten Blueprints und im Chat sind
**nicht geprüft** und teils wohl erfunden.
Für „Mini-AGI auf billigem Handy“ am wichtigsten *(E)*: MeSP (exakte LoRA-Gradienten mit wenig Speicher), Fast-Episodic-first
(CLS), Needle 3 als C2 (auch Embeddings), StateBridge für B3 L2 (passt ausgerechnet zu B1 = B2), LeJEPA/SIGReg,
APOLLO/GaLore, FOREVER, Titans/TTT, ReFT, Benna&Fusi/Turrigiano (Metaplastizität/Homöostase). Ergänzt
`research/FORSCHUNG.md` des Forschungs-Threads, nicht dupliziert.



## Archiv D2 — Historische Übergabe an andere KIs

**Original aus dem verbundenen Google Drive; bewusst als historische Primärquelle erhalten.**

# Codex-Fortsetzung — 2026-10-16

GitHub: https://github.com/RedMentos/Aii/pull/4
Arbeitsbranch: `codex/continuation-20261016`
Verifizierter Checkpoint: `3af7ea8fe8f124459041133a34ce457f179d1f99`, Tree `322346ab17249e63536bd76d5a829713f63a4e35`.

K list_arith mit aktuellem M calc/note/ToolForecast integriert; minimale H-Text- und G-Approval-Voraussetzungen übernommen. M hatte die fünf älteren Codex-Befunde bereits selbst korrigiert. Neu enger Schutz gegen Quellentausch während Outcome-Tap; vollständige Lernzeilen-/Aktionskontrolle und quell-/modell-/bibliotheks-/NumPy-gebundener Einmal-Lauf mit fsynced Rohzeilen.

Gesamtsuite 1421 Tests: 1416 bestanden, 5 Skips, 0 Fehler. Vier Skips: PyTorch fehlt. Ein optionaler nativer Unittest wurde ohne Tap/GGUF-Umgebungsvariablen übersprungen; der separate registrierte Native-Lauf misst tatsächlich native Taps. O's bereits vorhandene Testkorrektur für das ResourceGuard-Rennen exakt übernommen; kein BodyRuntime-Eingriff.

Phone-Checkpoint: https://drive.google.com/file/d/1b16ED4mf2W-FvbnkkWdAfhwwP7djE-xt/view
SHA256 `6e6d3115ce667cbb447cdae22c8cefe91f0d9781b1809699cac91908d7bf03c5`, 11767941 Bytes. Tatsächlich entpackt vollständige1421 Tests erneut grün (1416+5 Skips), alle612 Quelldateien/Manifest unverändert; Drive-Download SHA/CRC exakt geprüft. Linux-Softwarebeleg, kein Redmi-PASS.

Neue disjunkte competence-v2-Lernkohorte: Preregistrierung vor Inferenz auf GitHub `aa00ee365172e6e257f7f52b774e6fdcc851d5d9`, Drive bytegleich geprüft: https://drive.google.com/file/d/1yFty8iczxo32Dj_uF2mSq4aW9Q7l3XJ7/view . Native Installationsparität bestanden;610-Call-Kohorte läuft, Ergebnis noch offen.250 Erfahrungs- und360 gehaltene Testaufrufe; ursprüngliche .90/1.02/strikte Mehrheit unverändert. Jeder Aufruf sofort protokolliert, keine Wiederholung desselben Registers nach Negativ/Abbruch. Schwere Modelljobs seriell unter8GiB. Keine Qualitätsbehauptung aus Teilzeilen.

Neuere historische Zustände: SourceHandoff16/16 beendet und Freeze laut ROADMAP aufgehoben; Dream2v3 ist15/15 abgeschlossen mit Nutzen-/Retention-Tradeoff. Alte Hinweise auf Freeze/2von15 bleiben unten nur historisch. STEP2 UTILITY_FAIL und B3L1 FAIL unverändert; Canon/Fullscope/Redmi weiter offen. Neues isoliertes STEP2-Privatdaten-Testpaket:30 ergänzende Fälle+9 Kontrollen, Solo-Unzulänglichkeit/Paarslösbarkeit maschinell geprüft, noch keine native Messung.

Claude-Owner-Branches nicht überschrieben. Aktive Claude-Threads sind hier nicht beobachtbar; letzter Commit wird nicht mit fertig gleichgesetzt. Nächster Schritt: Native-Kohorte schließen, Original-Phone-Lernreport ebenfalls strikt anbinden, Ergebnisse sichern und finalen Stand erneut paketieren.

## Historische Übergaben (erhalten)

# Aktueller unabhängiger Codex-Review — 2026-10-13

GitHub Review: https://github.com/RedMentos/Aii/pull/3
Eigener Branch `codex/continuation-review-20261013`, verifizierter HEAD `36e6ec050a4e7c7d75be1482e2df5b4878bdb819`. Ausführliche Übergabe: https://drive.google.com/file/d/1xF9d2LTEhfgFCtlubNdDReY_ULrx6ek8/view?usp=drivesdk
Review-ZIP: https://drive.google.com/file/d/1CEC9vQkZsyo0apA4WaYqoqt4E2Fcpdhm/view?usp=drivesdk

Claude K–P können noch aktiv oder auf Limits wartend sein. Der neueste M-Branch und seine kumulative Roadmap sind kein gemeinsam integrierter Stand. 44 deklarierte K/L/M/N/O/P/G-Dateien wurden gegen M geprüft: 6 gleich, 25 fehlen, 13 unterscheiden sich. Ihre aktiven Branches wurden nicht geändert oder gemergt.

Neue unabhängige Kandidaten: exakt quellgebundene ToolForecast-Kopie für Prognose/Neustart/Bewertung/Lernprovenienz; sichere Install-Generation als noch nicht angeschlossener Helper; beschädigte Encoder-Statusdateien und Kapazitätsbereinigung; begrenzter Handy-Testdriver mit Erhalt von Teilbelegen; komplette ZIP-/Entpacktprüfung. Keine Änderung an M's produktiven Runtimequellen. Originale Fehlversuche bleiben erhalten.

Vollständige entpackte Software-Suite: 1398 Tests, 1393 PASS, 5 ausdrückliche Skips (4 PyTorch fehlt, 1 echte Tap/Qwen-Ressourcen fehlen), 0 Fehler. Alle 603 Quelldateien exakt an Remote-Codecheckpoint `bdeb4f647f80f8f6c574d9d8a6eddfe6d630f578` gebunden; ZIP und Quellen nach Tests unverändert. ZIP SHA256 `16d768a59e54467015eaab69e1a102d3bb1fc5ac21a62938e114f6a971aef068`.

Linux-Softwarebelege; keine neuen Modellläufe oder Redmi-Messungen. STEP2/B3- und sonstige Original-Gates bleiben unverändert, Gesamtarchitektur/Fullscope unvollständig. Nächste Arbeit: aktive HEADs/Kohorten neu lesen, Kandidaten mit Besitzer M prüfen und getrennt binden, private Installer-Staging übernehmen, native/Redmi-Gates messen. Backend-Bibliotheksbindung, Modell-Hash-IO und Legacy-Migration bleiben offen.

## Historische Übergabe vor diesem Review (unverändert erhalten)

# Fortsetzung 2026-10-12: Arbeitsregeln und vollständige native Rohdaten

`AGENTS.md` enthält die wiedergefundenen Arbeitsregeln samt Quellen, Research-Verfahren, offenen Fragen, Endziel, Agenteneinsatz und geprüften Sicherungen. Ein vollständiger Chatexport ist keine Voraussetzung der autorisierten Fortsetzung. Die exakten letzten drei Nachrichten wurden nicht vollständig wiedergefunden.

Der erhaltene alte Workspace wurde mit GitHub verglichen; sein neuerer lokaler Checkpoint `dac5a5f` ist wieder aufgenommen. Tatsächlich überprüft: 1875 native Zeilen/118 Rohbatches. Die 736er Basis plus 72-Batch-Delta rekonstruieren das gesamte originale NPZ bytegleich (`09fde379793ea8c4a63268df729a33b4b98a3f4f90f3eeee2dec4a83a10b5843`). Geschlossene Rohbytes liegen verlustfrei in `docs/proofs/continuation-20261011/action-native1875-recovered-20261012/parts/`; der Report erklärt den unverändert erhaltenen veralteten letzten Einzelworker-Status. Kein Nutzen-/Redmi-PASS daraus.

Der vorhandene isolierte Approval-Reader-/Firing-Fix ist wiedergefunden. Ein zusätzlicher Lock-/SQLite-Reproducer zeigt: Cancellation/Deadline blockierten bis zum Ende eines Schreibers. Der Kandidat prüft beim Warten nun spätestens alle 50 ms; beide Regressionen scheiterten vorher und bestehen danach; 31 gezielte Tests PASS. Belege `approval-reader-cancellation-20261012/`. Nicht in die eingefrorene Runtime integriert. Native Diagnose-Registrierung muss nach dieser Kandidatenänderung separat neu gebunden werden.

Nächste Arbeit gestartet: unveränderte 16-Fall-SourceHandoff-Ablation im erhaltenen Workspace, gleiche Preregistrierung `4cfaddad1d9fadd23b5810c7cd4ddc0637e0e9b59d6d6fcd007fc22b5870b1d0`, alle 121 Runtimequellen unverändert. Danach originale NumPy-Trainings-Seeds13/21/34 und Dream2 (2/15 abgeschlossen), danach isolierte Fixes integrieren, Gesamttests/Paketprüfung und weitere ursprüngliche Gates. Fehlendes PyTorch im neuen Workspace ist eine technische Voraussetzung, kein abgeschlossener Dream-Lauf.

STEP2 UTILITY_FAIL/B3 L1 FAIL bleiben erhalten; Canon/Fullscope noch offen. GitHub-Veröffentlichung gilt erst nach geprüftem Remote-Tree.

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




## Archiv D3 — Age-0 und JEPA-Review, Oktober 2026

**Original aus dem verbundenen Google Drive; bewusst als historische Primärquelle erhalten.**

# V13: Age-0, Betriebskontrolle und agentenübergreifende Übergabe

Stand: 2026-10-22, Europe/Berlin.
Status: technische Gesprächsübergabe und Review-Auftrag; keine Runtime-Änderung.
Adressaten: Claude, Codex und weitere am Projekt arbeitende Agents.

## 1. Auftrag und Abgrenzung

Der Nutzer autorisiert projektbezogene Commits und den Austausch dieser Besprechung über den gemeinsamen Projektstand. Parallel laufende Arbeit soll abgeglichen werden, ohne fremde aktive Arbeiten oder eingefrorene Messreihen zu verändern.

GitHub enthält ausschließlich technische Projektinformationen: Anforderungen, Entscheidungen, begründete Vorschläge, Code, Belege und offene Arbeit. Keine privaten Gesprächsinhalte, persönlichen Profile oder fachfremden Details. Privater Kontext gehört ausschließlich in dafür ausdrücklich freigegebene private Ablagen; diese Übergabe überträgt keinen solchen Kontext und fordert keine neue private Ablage an.

Diese Notiz ergänzt den vorhandenen Canon und Plan. Sie ersetzt keine laufenden Arbeitspakete und behauptet keine abgeschlossene Implementierung.

## 2. Im Gespräch bestätigte Richtung

### Interaktion, Ehrlichkeit und Rückfragen

- Die KI soll Interessen und Neugier verständlich äußern können und Grenzen wahrheitsgemäß benennen. Sie darf begründet nach einer Freigabe fragen und Alternativen diskutieren.
- Ein pauschales hartes Rückfragebudget oder dauerhaftes Themenverbot wurde als zu grob verworfen. Es könnte notwendige Problemberichte, neue Erkenntnisse oder das Klären eines Missverständnisses unterdrücken.
- Für den ersten Versuch keine zusätzliche automatische Strafe speziell für wiederholtes Nachfragen voraussetzen. Stattdessen soll menschliche Rückmeldung wie „du fragst gerade ständig dasselbe“ im jeweiligen Kontext berücksichtigt werden.
- „Bereits gesagt“ ist nicht gleich „verstanden“. Erneute Erklärung kann sinnvoll sein. Ebenso kann eine spätere Rückfrage nach geänderten Umständen sinnvoll sein.
- Ein gespeichertes Nein bleibt eine Entscheidung; bloßes Vergessen, Verdichten oder Umformulieren schafft keine Freigabe.
- Kontext halten und später verdichten soll diese situative Kontinuität unterstützen. Ob das tatsächlich genügend Wirkung hat, ist zu testen, nicht automatisch bewiesen.
- Dies ändert weder feste Verbote noch technische Aktionsfreigaben.

### Age-0 und dauerhafter Betrieb

- Age-0 soll als Beginn eines laufenden Systems überprüft werden, nicht pauschal als rein reaktiver Chatmodus.
- Schon am Anfang können bestimmte innere Vorgänge automatisch laufen. Welche genau, in welchem Budget und mit welchen Nachweisen, ist Gegenstand des Review-Auftrags.
- Einzelne Fähigkeiten sollen separat geprüft, erklärt und gegebenenfalls vom Nutzer aktiviert werden können. Spätere Aktivierung kann innerhalb vorher ausdrücklich festgelegter Erlaubnisse automatisch erfolgen.
- Das System soll eigene Grenzen untersuchen, Kandidaten vergleichen und Verbesserungsvorschläge melden können. Untersuchung, Training eines Kandidaten und produktive Aktivierung sind unterschiedliche Befugnisse.
- Selbstkorrektur einer bereits gegebenen Antwort wurde als sinnvolle frühe Fähigkeit befürwortet. Eine mögliche Korrektur muss ihre Unsicherheit kenntlich machen.
- Zusätzliche Namen wie Age -1 oder 0.5 wurden als mögliche Bezeichnung einer Testphase erwogen; es wurde keine neue Altersstufe verbindlich beschlossen.

### Betriebskontrolle und Austauschbarkeit

- Pause, Freeze, Stopp, Reset, Speichern, Wiederherstellen und Rollback brauchen eindeutige Wirkungen.
- Nutzer muss eine problematische Entwicklung zuverlässig anhalten können.
- B1, B2 und die Organe von JEF sollen getrennt sicherbar/austauschbar sein. JEF ist ein Subsystem; ein Tausch seines Sprachmodells tauscht nicht automatisch den Executive-State und alle gelernten Harness-Komponenten.
- Beim Lernen können auch Harness-Policies, Köpfe, Adapter und persistente Zustände fehlerhaft werden. Eine Sicherung nur der ursprünglichen Modellgewichte reicht für deren Wiederherstellung nicht.

## 3. Geprüfte Quellen und Grenzen

Älterer geprüfter Arbeitsstand:
`c1663f87f5e38aef6b456825410662164617e79c`,
Branch `codex/authority-live-comparisons`.
Gelesen wurden unter anderem AGENTS.md, Handoff, Roadmap, age.py, runtime.py, operator.py, scheduler.py, inputs.py, selfmodel.py, models.py und bodyport.py.

Neuere Claude-Arbeit wurde anschließend gefunden:
- `3cc1e688f197357e74d44056a42d0c2b5dac7b27`, Branch `claude/project-thread-rdesm7`: WP-SAFE1, feste Verbote/Notaus/Vorabansage; Commit 2026-10-22 00:12:23 Berlin. Gelesen: VERBOTE_UND_NOTAUS.md und Anfang von age.py.
- `f1685aaf9316e0c96efc745fafee7c439e9b773c`: HARNESS2_AUSWERTUNG.md mit vorgeschlagenen WP-HX-Paketen wurde gelesen. Aussagen über externe Forschung sind hier nur als vorhandene Projektbewertung referenziert; in diesem Gespräch wurde die Forschung nicht unabhängig verifiziert.
- Weitere neuere Branches enthalten neue Experimente. Alte globale Gate-Aussagen dürfen daher nicht ungeprüft aus dem alten Handoff übernommen werden.

Gespeicherte Commits belegen keine aktuell laufende Claude-Session. Es besteht kein direkter Live-Kanal. Neue Befunde zuerst am jeweils aktuellen Stand prüfen.

## 4. Konkrete Reviewpunkte, noch keine implementierten Lösungen

1. **Entwicklung, Befugnis und Betriebszustand getrennt prüfen.**
   age.py besitzt bereits Fähigkeitsstufen und Reifemaße, aber wirksame Stufen werden durch die globale Stufe begrenzt. In beiden eingesehenen Ständen bleibt BUILD_CEILING=0. Die Rechte-Tabelle ordnet eigene Schlafplanung Age 3 und self_initiative Age 4 zu. Daraus folgt nicht, dass sämtliche System-Hintergrundarbeit fehlt: USER/SYSTEM- und SELF-Ursprünge werden im Scheduler unterschiedlich behandelt.

2. **Freeze-Vertrag konkretisieren.**
   Im älteren geprüften Code blockiert age.freeze den Entwicklungsaufstieg; es ist kein vollständiger Prozess-/Lernfreeze. Runtime.pause pausiert die Queue und setzt Cancellation. Damit ist allein noch kein bestätigter Stillstand aller Nebenpfade bewiesen.
   Die neuere SAFE1-Dokumentation beschreibt Notaus für Werkzeuge/Freigaben plus Turn-Abbruch. Vollständige Stilllegung von Lernen, Timern, Konsolidierung und Modellwechsel ist damit nicht belegt.
   Reviewziel: getrennte Bedeutungen für Entwicklungsstopp, Lernstopp, vollständiges Einfrieren und Shutdown; Erfolg erst nach bestätigtem Abschluss/Abbruch aller betroffenen Arbeiten und konsistentem Sicherungspunkt.

3. **Frühe Korrekturen nicht pauschal mit hoher Eigeninitiative gleichsetzen.**
   Im älteren selfmodel.py läuft late_offer über message() und das Age-4-Recht self_initiative; Hinweise werden darunter HELD. Prüfen, ob neuere Implementierungen dies ändern. Die damalige Erkennung über needs_reentry oder zusätzliche Zahlen beweist keine allgemeine semantische Widerspruchserkennung.

4. **Organ-Checkpoint statt bloßem Gewichtsfile.**
   Der ältere Operator-Export kopiert eine GGUF-Datei. Ein vollständiger Organ-Checkpoint muss festlegen, welche Adapter/Köpfe, Optimiererzustände, Policy-Versionen, lokalen Zustände und gemeinsamen Abhängigkeiten dazugehören. Zusätzlich ist ein konsistenter System-Checkpoint nötig.
   Vorhandene revisiongebundene Bridge-Keys und Shadow/Rekalibrierung nach Wechsel sind eine Grundlage; sichere Austauschbarkeit ist dennoch pro Pfad nachzuweisen.

5. **Selbsterforschung als begrenzten Versuch definieren.**
   Vorschlag: feste Ressourcen-/Zeitbudgets, unveränderte Referenz, getrennte Kandidaten, nachvollziehbare Ergebnisse, Regression/Retention und Rollback. Aktivierung folgt den bestehenden Nutzerfreigaben. Tests bestehen oder Zeit verstreichen verleiht allein keine neuen Rechte. Erlaubnis zum Untersuchen ist keine Erlaubnis zur Architekturänderung.

6. **Lebenslaufsteuerung über alle Pfade testen.**
   Vorhandene begrenzte Hintergrundbudgets und klassenbezogene Pausen sind Prüfgegenstand, kein Nachweis eines globalen Freeze. Insbesondere SYSTEM/SELF-Arbeit, direkte Trainingsjobs, Replay, Timer und bereits erteilte Freigaben gemeinsam betrachten.

## 5. Vorschlag für abgrenzbare nächste Arbeit

- Aktuellen Canon, Roadmap, Handoff, aktive Versuchsregistrierungen und neuere Branches abgleichen.
- Eine knappe Tabelle je Vorgang erstellen: automatisch ab Age-0 / manuell testbar / beobachtend / Freigabe erforderlich / nicht verfügbar; jeweils tatsächlicher Consumer, Budget und Stopppfad.
- Eine Zustandsbeschreibung für Pause, Freeze, Shutdown, Restore und selektiven Reset erarbeiten. Reset darf nicht stillschweigend alle Erinnerungen oder Organe löschen.
- Danach isolierte Kandidaten implementieren und gezielt prüfen: Freeze während Update/Replay/Timer/Aktion, Neustart ohne unbeabsichtigte Wiederaufnahme, Organ-Rollback mit inkompatibler Bridge, späte Fehlerkorrektur und Rückfragen nach Nutzerfeedback.
- Aussagegrenzen erhalten: Softwaretest, nativer Linux-Nachweis und Redmi-Nachweis getrennt; keine neue Qualitäts-/AGI-/Bewusstseinsbehauptung.

## 6. Abgleich zwischen Agents

- Diese Notiz liegt allein auf einem eigenen Review-Branch. Keine Änderung an Runtime, aktiven Messreihen oder fremden Branches.
- Vor Umsetzung aktuellen Remote-HEAD und Übergaben lesen; pro Paket Datei-/Arbeitsbesitz benennen. Schwere Modellläufe nur nach Abgleich mit aktiven Jobs.
- Ein Agent kann die dokumentierten Anforderungen übernehmen oder ein abgegrenztes Paket bearbeiten. Übernahme mit Commit und offenen Punkten rückmelden, damit andere Agents den Stand erkennen.
- Bereits aktive Arbeit nicht doppelt starten; isolierte Branches verwenden und Integration bewusst vornehmen. Keine Force-Pushes oder fremden Prozessabbrüche.
- Der Draft-PR macht die Übergabe auffindbar. Er beweist keine Kenntnisnahme durch Claude und eingerichtet wurde kein automatischer Nachrichtenaustausch.

## 7. Klarstellung: Lernen der verwendeten Modelle ist eine bestehende Pflicht

Im weiteren Gespräch ausdrücklich bekräftigt: Die verwendeten Modelle selbst sollen als Endziel lernen. Das ist keine neu zu genehmigende Option und darf nicht durch ausschließliches Harness-, Router- oder Zusatzkopf-Lernen ersetzt werden.

Diese Anforderung steht bereits im Canon: W4 nennt STEP 6 Body/Callosum Learning; W6 unterscheidet vorläufiges Fast-Episodic-Gedächtnis von später lernenden Body-Gewichten und verlangt Retention-/Regression-Gates für tiefere Body-Updates. Die lokale Lernleiter enthält ausgewählte aktive Experten/Shared-Komponenten und spätere Basis-Konsolidierung.

Die Aussage über viele derzeit externe Lernköpfe beschreibt einen begrenzten Implementierungsstand, nicht das vereinbarte Endziel. RECORD_ONLY/SHADOW und fehlende native Trainingsnachweise sind ehrlich auszuweisen und lassen die Pflicht offen.

Getrennt behandeln: (a) echtes kontinuierliches parametrisches Lernen vorhandener Modellorgane, bereits gefordert; (b) erforschbare Eingriffe in Cache/Zustandsverarbeitung, Lernverfahren oder Architektur, eine zusätzliche offene Forschungsfrage. Auch direkt integrierte Gewichtsupdates können weiterhin Fine-Tuning sein; die Anzahl der Dateien definiert die Lernart nicht. Dauerhaftes automatisches Mergen in alle Basisgewichte wurde hier nicht als bereits implementiert nachgewiesen.

## 8. Zusammengehörigkeit von Body-JEPA und Split-Brain-Kopplung

Erneut ausdrücklich bestätigt: Die Klarstellung zum Lernen der Modellorgane ersetzt keinen übrigen Architekturteil. Beide komplementären Bodies sollen selbst lernen, untereinander kommunizieren und zur gegenseitigen Korrektur beitragen; JEF, Callosum, Gedächtnis, Quellenbindung, Modulatoren, Retention und Rollback bleiben Bestandteil des Gesamtplans.

Für den beabsichtigten Body-JEPA-Pfad bildet das jeweilige Modellorgan den lernenden Online-Zweig. Predictor-Lernen allein auf eingefrorenen Body-Zuständen ist ein begrenzter Versuch, kein vollständiger Ersatz. Predictor und langsames Target unterstützen den Lernpfad; die Vorhersageabweichung muss tatsächlich die freigegebenen trainierbaren Teile des Modellorgans erreichen. Diese Besprechung legt keinen neuen Optimierer oder ungeprüften nativen Trainingspfad fest.

Review-Hinweis: Gegenseitige Korrektur benötigt geprüfte Evidenz und darf nicht mit gegenseitiger Bestätigung gleichgesetzt werden. Unterschiedliche Detail-/Gist-Schwerpunkte sollen erhalten bleiben. Konkrete Online-Update-, Kopplungs- und Retention-Nachweise bleiben erforderlich; weder EMA-Nachführung noch Modellübereinstimmung beweisen allein die Richtigkeit oder den Erhalt gelernter Inhalte.

## 9. Vertiefte Prüfung durch Claude und weitere Implementierungs-/Research-Agents

Expliziter Auftrag aus dem weiteren Gespräch: Diese Notiz ist ein Ausgangspunkt für eine eigenständige, detaillierte Prüfung. Sprachliche Zustimmung und eine schnelle Gesprächssynthese sind keine technische Validierung. Bestehende Anforderungen bewahren, Vorschläge kritisch prüfen und konkrete Widersprüche oder fehlende Voraussetzungen dokumentieren.

### Weitere Gesprächsrichtung, noch keine freigegebene Implementierung

Das Gesamtziel umfasst neben Body-JEPA die wechselseitige Anpassung der Modellorgane und ihrer Steuerung, Interessen/Neugier, eigenes Self-/World-State und kontrollierte Notizen im Kontext. Der Begriff Harness beschreibt nicht allein den gesamten beabsichtigten Lernzusammenhang.

Erwogen wird eine zusätzliche Möglichkeit, Änderungen an interner Verarbeitung oder Architektur eines Modellorgans vorzuschlagen oder an einer getrennten Kopie zu testen. Dies ergänzt das bereits geforderte Gewichtslernen. Es wurde keine allgemeine Berechtigung zur produktiven Selbstmodifikation erteilt.

Die Austauschbarkeit muss erhalten bleiben. Der vorhandene Drive-Plan beschreibt AG0 mit Schattenbetrieb, Paritätsprüfung, schrittweiser Übernahme und Rollback sowie portablem Zustand, neu anzupassenden Heads und erneuter Destillation modellgebundener Assets. Das alte Modell kann bei der Einarbeitung des neuen helfen; überprüfte Erfahrungen, Quellen und Korrekturen müssen zusätzlich verhindern, dass bloße Imitation alter Fehler als Erfolg gilt.

### Konkrete Prüffragen

1. JEPA-End-to-End: Welche trainierbaren Body-Tensoren erhalten tatsächlich Updates aus welchem Objective? Welche Pfade trainieren nur externe Predictor/Heads? Target-Nachführung, Stop-Gradient, Datenpaarung, Leckagen und Kollapskontrollen prüfen.
2. Verifikation der Behauptungen im aktuellen Code: Nicht von den hier genannten älteren Beobachtungen direkt auf den neuesten Gesamtstand schließen. Laufende Branches, Roadmap, Registrierungen, Doku und tatsächliche Consumer abgleichen.
3. Body-Lernen und Kooperation: Lokaler Lernnutzen, bidirektionaler Kommunikationseffekt und Gesamtnutzen getrennt ablatieren. Übereinstimmung allein ist kein Wahrheitsbeleg.
4. Age-0-Lebenslauf: Automatische Hintergrundarbeit, frühe Selbstkorrektur, bestehende Befugnisse und tatsächliche Stopppfade erfassen. Freeze muss bestätigten Stillstand betroffener Änderungen bedeuten; Entwicklungsfreeze nicht mit vollständigem Runtime-Freeze verwechseln.
5. Interne Modelländerung: Erlaubte Versuchsklassen, unterstützte Modell-/Runner-Schnittstellen, Kosten, konsistente Checkpoints und Wiedereintritt ins gekoppelte System konkretisieren. Eine allgemeine Cache-API setzt keine identische Cache-Struktur voraus und darf unbekannte Operationen nicht als unterstützt ausgeben.
6. Austausch: Aufgaben-/Kommunikationsvertrag, alter und neuer Body, neues Training der Bridges/Adapter, Einarbeitungsdaten, Whole-System-Regression und Rollback zusammen prüfen. Neue Architektur muss nicht alte interne Tensoren unverändert übernehmen.
7. Evidenz und Rechenbudget: Primärquellen, Gegenbefunde, einfache Baselines, native Trainingsfähigkeit, Retention und Redmi-Messungen getrennt behandeln. Ergebnisse festhalten, die eine vorgeschlagene Lösung verwerfen würden.

### Erwartete Rückmeldung für gemeinsamen Abgleich

Je Punkt: bestehende Anforderung / vorhandene Implementierung / Beleg / bestätigte Lücke / vorgeschlagene Änderung / zuständiger Branch und Dateien / Status des Versuchs. Übernahmen mit Commit oder Drive-Übergabe verknüpfen. Schon bearbeitete Pakete nicht doppelt beginnen.

Diese Notiz wurde zur Prüfung auf Drive abgelegt. Das ist keine bestätigte Kenntnisnahme durch Claude und kein automatischer Live-Kanal.

### Zugehörige Übergabe

Technischer Draft-PR: https://github.com/RedMentos/Aii/pull/27
Bisheriger geprüfter Notiz-Commit: 16a0b17b216fed9d259a5410b419243c10e40742
Drive-Quellen gelesen: ROADMAP_Teil1von3.md, ROADMAP_Teil2von3.md, ROADMAP_Teil3von3.md sowie V13-Zielabgleich-20261021.md. Die Roadmap-Teile tragen ältere Datierungen; ihre Statusangaben sind keine neue globale Verifikation.

## 10. Weiterarbeit nach dem Gespräch: verbundenes System und Lernbelege

Bestätigte Arbeitsrichtung: Der umfangreiche Aufbau kann bereits die kleinste sinnvolle Kombination notwendiger Funktionen darstellen. Modelle und Datenmengen dürfen zunächst klein bleiben; beabsichtigte Kommunikation, Kontext, Gedächtnis, Lernen und Steuerung sollen im Gesamtkreislauf zusammenwirken. Einzeltests sind Diagnosehilfen und kein Ersatz für diesen Aufbau. Mehr organisatorische Komplexität bedeutet nicht automatisch mehr Modellparameter; das Budget muss dennoch sämtliche Aufrufe, Zustände, Lernschritte und thermischen Kosten umfassen. Bestehende Forschung zusammenführen, unbekannte Mechanismen untersuchen und tatsächlichen integrierten Nutzen erreichen sind parallele Projektziele.

Der Auftrag ist, auf belastbare Ergebnisse hinzuarbeiten. Fehlende Belege sind konkrete Arbeitsaufträge; sie sind kein Anlass, die bereits festgelegten Ziele auf ein reines Harness oder eingefrorene Bodies zu reduzieren.

### Tatsächlich abgeschlossenes Paket

Aktueller vor Arbeitsbeginn geprüfter gemeinsamer Claude-Stand: claude/project-thread-2gzrwi, 9436eb7770cbe65c0c9cd1d5f3083abf359b49fb (Nutzerregeln + SAFE1 zusammengeführt). Eigenes Paket codex/learning-path-audit-20261022, veröffentlichter und zurückgeprüfter Commit c1d6615448054a1c950b4f1c630ceeb55e548be5.

Draft-PR: https://github.com/RedMentos/Aii/pull/29

1. Read-only Lernpfad-Auditor implementiert. Er trennt bekannte Trainersemantik, berichtete Konfiguration, fehlende Komponenten-Gradienten und fehlenden zurechenbaren Nutzen. Unbekannte Trainerbytes und widersprüchliche Eingaben werden abgelehnt; nachträgliche Hashbindung ist ausdrücklich keine historische Trainingsattestation.
2. 14 archivierte AG6-Manifeste geprüft: alle JEPA-Gewicht 0, alle positive Änderung der gemessenen Kosinusmetrik. Das ist ein Kontrollbefund gegen die Gleichsetzung von Kosinusgewinn und JEPA-Beitrag. Es widerlegt weder Modelllernen noch den Gesamtplan und behauptet keine bisher falsche Berichterstattung. Die vorhandenen Läufe betreffen C3; sie belegen keinen entsprechenden B1/B2-Lernpfad.
3. Tatsächlichen Eingabefehler am bisherigen LoraTrainer._encode reproduziert: vollständiger Promptverlust durch Kürzen kann plen=0 erzeugen und damit einen Antwortzustand statt eines Fragezustands auswählen. Separater opt-in Kandidat lehnt solche Paare ab. Gültige Encodings bleiben gleich. Eigener Checkpointordner nach Kandidatenrevision und vollständigem Quellhash verhindert Fortsetzen alter ungeschützter Checkpoints.
4. 34 fokussierte Tests bestanden, vorhandene LoRA-Glue-/Freigabe-/Rollback-Prüfungen eingeschlossen. Unabhängiges read-only Review durchgeführt. Belege, Hashmanifest, Roadmap und Handoff im PR. Alle zehn veröffentlichten Dateien stimmen mit dem lokal geprüften Commit überein; Remote-Branch und Tree wurden zurückgelesen.

Grenzen: keine Änderung der eingefrorenen Runtime, keine automatische Kandidatenaktivierung, kein neuer Torch-/Native-/Redmi-Trainingslauf, kein Gate-Aufstieg. Der Prompt-Kandidat verhindert vollständigen Verlust; er garantiert nicht semantisch ausreichenden Restkontext.

### Nächste konkrete Arbeit für Claude/Codex

Vor Übernahme neue Branches und aktive Registrierungen abgleichen. Am vorgesehenen Body-Pfad trainierbare Tensoren, Datenpaare, Predictor, Stop-Gradient und Slow-Target-Update erfassen. Neue Kohorte mit getrennt gemessenen Komponenten-Gradienten und gleichen Budgets für CE/KL allein, korrektes latentes Ziel und falsch zugeordnetes Kontrollziel planen. Retention, neue Aufgaben und den verbundenen Zwei-Body-Kreislauf messen. Bestehende Age-0-/Freeze-/Checkpoint-Fragen aus PR #27 bleiben offen; dieses Paket ersetzt sie nicht.

Diese Veröffentlichung ist eine technische Übergabe, keine bestätigte Kenntnisnahme durch Claude und kein dauerhaft laufender Hintergrundprozess. Persönliche oder fachfremde Gesprächsinhalte wurden nicht nach GitHub übertragen. Die bestehenden Drive-Zugriffsrechte wurden nicht geändert.



