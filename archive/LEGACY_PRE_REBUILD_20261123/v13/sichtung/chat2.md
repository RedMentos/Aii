# chat2 – Auswertung (mittleres Drittel „AI-Consciousness-Blueprint-Theses“)

Quelle: `scratchpad/chat2.txt` (34 013 Zeilen). Zeilenangaben = Zeilen in dieser Datei.
Abgleich mit `v13/ROADMAP.md` (Stand 09.10., inkl. neuem Abschnitt WP-S1…S8) und
Blueprint v10.16.1 (`…B3_HARDENED.md`, per grep).

**Was im Chat steht (Überblick):**
- Zeitraum 2.–4.9.2026. Assistenten waren *meta/muse-spark-1.3* und einmal *deepseek-v4-pro*, kein GLM.
- Ungefähr 70 % sind Code-Dumps: V13_REDMI v3.0, v2.9.1/2.9.2, „FINAL FIXED v3“, FLUID_ANSWERING, V13.5/V13.1, dazu die Assistenten-Dateien code (5)…(12).py. Viele Nachrichten sind Duplikate:
  - Die Blueprint-Datei kommt 5× vor.
  - Die User-Thesen kommen 2× vor.
  - v3.0 und v2.9.1 kommen jeweils 2× vor.
- Der inhaltliche Kern:
  - die 10 Thesen und die Ziele 2A–2G des Users (Z. 10481–11447),
  - seine „Was fehlt zum Hirn“-Liste (Z. 11026 ff.),
  - die Harness-Vision (Z. 11323),
  - die Termux-Bedien-Wünsche (Z. 12994–28185).
- Das Gesamtsystem in diesem Chat war ein **von Null trainiertes** PyTorch-Netz mit 1,6 M bis 36 M Parametern und Byte-Vokabular. Es gab nie sinnvollen Text aus („rere:U:hi“, „Ĵ“).
- Am Ende sagt der User selbst (Z. 28185): „so viel quatsch drin … Idee wird immer verdreht“.

---

## 1. Ideen und Anforderungen, die im Blueprint und/oder in der ROADMAP fehlen oder schwach sind

Legende für den Status:
- **fehlt**: weder im Blueprint noch in der ROADMAP.
- **BP≠RM**: im Blueprint, aber nicht in der ROADMAP.
- **abgedeckt**: in beiden vorhanden.

Die Bewertungen sind mein Urteil (6-GB-Redmi, Termux, llama.cpp-Stack).

### 1.1 Termux-Bedienung (größte echte Lücke, billig)

**a) Live-Logs dürfen getippten Text nicht löschen**
- Fundstelle: „wenn termux nen neuen tackt angibt … es den text löscht“ (Z. 14297).
- Lösung im Chat: `readline.get_line_buffer()`, dann `\r\x1b[K`, Log ausgeben, Prompt und Puffer neu zeichnen. Dazu eine LOG_Q-Queue mit Lock (Z. 18689, 26656).
- Status: **fehlt**. Blueprint W8 nennt Cancel/Pause/Resume/Partial Output, aber keine tippsichere Live-Anzeige.
- Urteil: hoch, ca. 50 Zeilen, sofort machbar.

**b) Arbeit im Hintergrund statt Blockieren, plus `stop`/`wait` jederzeit**
- Fundstelle: „Stoppable inference … send stop while it runs“ (Zusammenfassung Z. 12421).
- Status: **abgedeckt**, Blueprint W8 hat `:cancel :pause :resume`.
- Prüfen sollte man nur, ob der aktuelle Operator wirklich nicht blockiert.

**c) Befehle mit Präfix, freier Text = Chat**
- Fundstelle: Der User lehnte erst Sonderzeichen ab (Z. 23005). Die `/`-Lösung lief dann.
- Ursache: Befehle wie `stat` wurden als Chat-Text gespeichert.
- Status: **abgedeckt**. Der Blueprint nutzt `:`-Kommandos, und Modell-Output wird nie geparst.

**d) Hot-Change ohne Neustart (`/py CODE`, „editierbare Werte“)**
- Fundstelle: „Hot python commands without restart“ (Z. 12421).
- Status: **fehlt**. Ein freies `exec` widerspricht der Operator-Sicherheit, siehe §4.
- Urteil: Als sicheres `:set <key> <wert>` für Whitelist-Configs ist es mittelwichtig und billig.

**e) Kontext-Vorschau: genau das zeigen, was ins Modell geht**
- Fundstelle: `ctx` zeigt den „echten Prompt B=1“ (Z. 18332), `ctx_preview` (Z. 17797).
- Status: **fehlt** als Operator-Kommando.
- Urteil: hoch für Debugging, billig.

### 1.2 Drei Takte: Draft / Publish / Idle

**a) Draft und Publish**
- Fundstelle: „2 tacktungen eins wo es … erstmal drafted bis es relativ zufrieden is und dann alles outputet“ (Z. 18526).
- Gemeint: Draft T1…7 intern mit sichtbarer Animation, dann genau ein Publish. Code: `think_once` (Z. 27577).
- Status: **BP≠RM**, sinngemäß abgedeckt. Der Blueprint hat Focal-Loop, Halt und Output-Governor. ROADMAP WP-D steuert die Tiefe, aber nicht die sichtbare Live-Anzeige.
- Urteil: mittel.

**b) Idle: antwortet und lernt von selbst, „mega langsam“**
- Fundstelle: „seobst wenn antwort raus solls ja weiter denken … idle einf mit seinem eig kontext“ (Z. 18526). Code: `idle_loop` (Z. 27702).
- Status: **BP≠RM**, teilweise. Der Blueprint hat Idle-Events im Scheduler und Self-Messaging „später“ (§20.4, Age-gated). In der ROADMAP deckt WP-E nur Scheduler und Replay ab, keine spontane Ausgabe.
- Urteil: Idle-Replay ist realistisch. Spontane Nachrichten sind laut Blueprint Age>0.

### 1.3 „Ausbrennen“ als gelernte Selbstregulation

- Fundstelle: „Nur langsam Ausbrennen (noch) kinda hard-coded aber eig soll der judge selber lernen wann er in pause gehen soll … langsamer lernen ohne neuen imput … ausbrennen im ideal fall immer weiter hoch stellen manuell“ (Z. 11323).
- Vorläufer im Code: `sleep_after_eff = sleep_after*(0.5+uni_g)` (Z. 3171 ff.) und `learn_gain` (Z. 725).
- Was gemeint ist:
  - Die Lern- und Denkaktivität klingt ohne neuen Input ab.
  - Wann pausiert wird, wird gelernt.
  - Der User kann das Limit stufenweise anheben.
  - Später holt das System selbst Input (Tools) oder führt Selbstgespräche.
- Status: **fehlt als eigener Mechanismus**. Bruchstücke im Blueprint: Homeostasis §16.2, Age `autonomy_curve`, Self-Messaging. In der ROADMAP nur Homeostasis.
- Urteil: hoch, weil es ein Kernwunsch ist und gut als „Activity/Plasticity-Budget mit User-Regler“ in WP-C (Age) und WP-E (Scheduler) passt.

### 1.4 Editierbarer Kontext und Denk-Trace, mit gelernter Edit-Bremse

**a) Kontext dreigeteilt, dazu Dream-Zeilen und Offline-Langzeit**
- Aufteilung: real / weltbild / frei, plus D:-Dream-Zeilen, plus Offline-Langzeitspeicher.
- Alles ist vom User **und** vom System editierbar: add/edit/del/consolidate/revise sowie `think`/`thinkdel` für den Takt-Trace.
- Fundstellen: Z. 12421 und Z. 14343 („kontext/+thinking bearbeitbar“). Code: `MemoryStore` (Z. 13596) und `self_edit` mit Konsolidierung real→welt (Z. 790).
- Status: **BP≠RM**, nur teilweise. Der Blueprint hat Self-Edit-Rechte (§20.2), Context-Edit-Budget (§17.5) und World Notebook. Es fehlen Operator-Kommandos für die Speicher-Sichtung und -Bearbeitung sowie ein sichtbarer Denk-Trace. In der ROADMAP steht nichts davon.

**b) „lernt nt zu viel nur editieren“**
- Fundstelle: Z. 14297.
- Umsetzung im Chat:
  - Edit-Budget 3/20,
  - gelernte `edit_penalty`: steigt bei „schlecht“ nach einem Edit, sinkt bei „gut“ (Z. 863 ff.).
- Status: **fehlt**. Es gibt nur ein Budget, keine gelernte Strafe.
- Urteil: mittel, billig.

### 1.5 Schutz vor vergiftetem Gedächtnis

- Fundstellen:
  - Bash-Fehlermeldungen, Status-Logs und eigene „V:“-Ausgaben landeten in `real` und im Pretrain-Pool („pool=689 vergiftet“, Z. 24599).
  - Persönliche Testtexte des Users wurden sogar in den Boot-Korpus übernommen (Z. 26681 ff.).
- Code: `is_garbage` und `is_usable` (Z. 26777).
- Status: **teilweise**. Der Blueprint trennt Self-, Reference- und Human-Lanes (Provenance/Admission). Einen Filter für „vom User eingefügte Terminal-Logs bzw. Nicht-Dialog“ gibt es nicht.
- Urteil: mittel. Wichtig, bevor WP-I echte Nutzer-Labels sammelt.

### 1.6 Decoding-Hygiene gegen Echo und Wiederholung

- Fundstelle: „Repetition-Penalty 1.15, Trigram-Block, PAD/BOS gesperrt, min 8 / max 48“ (Z. 18901).
- Status: **fehlt**. Der Blueprint enthält null Treffer zu repetition/no-repeat.
- Relevanz: Die ROADMAP meldet, dass C3 nur „query echo“ liefert. Anti-Echo- und Wiederholungs-Penalty sowie eine Mindestlänge sind billige erste Gegenmittel, bevor man das Modell wechselt.
- Urteil: hoch, in WP-G aufnehmen.

### 1.7 Werte- und Affektsystem („Bock/Angst“)

- Fundstelle: „Emotion / Value System fehlt komplett … Mensch bewertet … ‚will ich das überhaupt denken?‘ … Neuromodulator für Judge statt feste Gewichte“ (Z. 11026).
- Status: **BP≠RM**. Der Blueprint hat Layer 6 „Valuation/Neuromodulation“ und typisierte Neuromodulatoren. In der ROADMAP stehen nur Homeostasis und Salience (WP-F).
- Urteil: mittel. Als kleine gelernte Heads über vorhandenen Signalen ist das realistisch, ein „echtes“ Affektsystem nicht.

### 1.8 Neugier: RND und Intrinsic Novelty als „Need“

- Fundstelle: „Needs als Layer: Coherence, Diversity, Confidence, JEPA_sim, RND“ (T10, Z. 10481). Code: `class RND` (Z. 488).
- Status: **fehlt**. „Neuheit“ kommt im Blueprint nur als Salience-Trigger vor, nicht als Lernsignal oder Explorationsantrieb.
- Urteil: mittel, kostet ein kleines MLP auf Embeddings. Sinnvoll für Replay-Priorität und Controlled Exploration (§6.6).

### 1.9 Grounding über Code-Ausführung

- Fundstelle: `safe_exec` in einer AST-Sandbox als „grounded bonus“ für Selbstverbesserung (Z. 642, 2141), `absolute_zero_executor` (Z. 33518 ff.).
- Status: **fehlt** als Lern- und Belohnungssignal. Tools kommen im Blueprint erst ab C6/C7.
- Urteil: mittel. Für Rechen- und Codeaussagen ist das billige, ehrliche Verifikation. Es braucht WP-K (Action-Transaction).

### 1.10 Aktives Vergessen als Feature, Konsolidierung real→weltbild

- Fundstelle: „Vergessen als Feature … Teil1+Teil3 wird irgendwann Müll, Mensch räumt auf“ (Z. 11026).
- Status: **BP≠RM**. Der Blueprint hat „Memory Admission und Forgetting“ (§9.5) und Konsolidierung. In der ROADMAP deckt WP-E nur Replay und Konsolidierung ab, Vergessen nicht ausdrücklich.
- Urteil: mittel, billig (Score-basiertes Prunen).

### 1.11 Mehr Zeitskalen (H-JEPA, 6–7 Ebenen)

- Fundstelle: „Mensch hat 6-7 verschachtelte JEPA Level wie in H-JEPA“ (Z. 11026).
- Status: **schwach**. Der Blueprint hat einen Multi-Timescale-Workspace mit 2 Bodies, H-JEPA wird nicht zitiert.
- Urteil: auf dem Handy geringer Wert. Höchstens als Slot-Zeitskalen, keine weiteren Modelle.

### 1.12 „Decoder merged langsam in sich“ / Gemma-4-Unified-Internalisierung

- Fundstelle: „Es soll decoder langsam selber in sich mergen, jepa latent space, token prediction wos geht (bzw token prediction layer evtl in judge)“ (Z. 11026). Im Code: `dec_share`, `merge_u`, `self_trust`.
- Status: **BP≠RM**. Der Blueprint sagt dazu „Zielrichtung, nicht Startvoraussetzung“ (Z. 400 BP).
- Urteil: auf dem Handy gering, solange C3 schon an der Sprache scheitert.

### 1.13 Bereits abgedeckt (zur Beruhigung)

- Human-gated Hard-Rule-Änderung „soll ich Rule ändern? old→new“: BP §20.1, „proposal → diff → explicit user approval“.
- Output immer (T8 „Output IMMER“): Output-Garantie per Governor.
- Quorum gated nur das Lernen: STEP5 Shadow, Approve.
- Rollback nach Score-Abfall: Regression Shield.
- Arch-Hash-Prüfung beim Checkpoint: Generation-Manifest.
- Callosum und Cross-Prediction Detail↔Gist: L4.2 Cross-JEPA.
- MoE lernt mit JEPA: Expert-Deltas.
- Self-Model-Notizen (blueprint.json mit 12 Slots): Self Model §7.3. Der Blueprint ist hier sogar tiefer als der Chat.
- Hippocampus-Replay: Sleep A/B/C.
- Interozeption: §7.4.
- Kleiner vortrainierter Sprach-„Judge“, der aus 2 Streams Sätze baut (Z. 24677: „wirklich mini und ohne viel Wissen, gerade Sprache selbst“): entspricht C3 (LFM2.5-230M) und WP-G.

### 1.14 ROADMAP-Lücken bei Themen, die der Blueprint hat

Diese Themen hat der User im Chat ausdrücklich gewollt:
- Neuromodulation/Valuation (Layer 6),
- Self Model und World Notebook,
- Rules-Versionierung und `:rules`-Flow,
- Self-Edit-Rechte und Context-Edit,
- Self-Messaging/Initiative.

Vorschlag: ein Paket „WP-L Operator & Gedächtnis-Bedienung“ (1.1, 1.4, 1.5, :set) und ein Paket „WP-M Ausbrennen/Aktivitätsbudget“ (1.3, 1.2b) anlegen.

---

## 2. Forschungsreferenzen im Chat

Die Spalte „im BP?“ zeigt grep-Treffer im Blueprint v10.16.1.

| Referenz (im Chat) | Wofür im Chat | im BP? |
|---|---|---|
| I-JEPA (2301.08243) | EMA-Target, schmaler Predictor, Block-Mask, L2 | nein (nur „JEPA“/„EMA“ allgemein, §13) |
| V-JEPA / V-JEPA 2 (2506.09985), „V-JEPA 2.1 α=0.99925“ | action-conditioned Predictor, Deep-Sup | nein (World-JEPA ohne Zitat) |
| C-JEPA (2410.19560) | VICReg + InfoNCE im JEPA | nein |
| LeJEPA / SIGReg | EMA-freie Stabilisierung | ja (1×), ROADMAP WP-S4 |
| H-JEPA | Zeitskalen-Hierarchie | nein |
| VICReg, InfoNCE (τ=0.07) | Kollapsschutz | nein |
| Switch Transformer, GLaM, ST-MoE (z-loss), Mixtral | Routing, Aux-Loss, z-loss, SwiGLU | nein |
| Expert Choice (Zhou 2022) | Gist-Routing | nein |
| DeepSeekMoE / V3 aux-loss-free Bias-Update | Router-Bias statt Aux-Loss | DeepSeek ja (V4.1-Flash), aux-loss-free nein |
| „SIMBAL, 36 % schnellere Konvergenz“ | Router-Balancing | nein, **nicht verifiziert** (Assistent-Behauptung) |
| EdgeMoE, OLMoE-1B-7B, LFM2-8B-A1B | „riesiges Unterbewusstsein“-Rechnung | nein. ROADMAP: MobileMoE als Ersatz, zurückgestuft |
| Qwen3-0.6B (+NVFP4), Qwen3.6, Gemma-3n-E2B (MatFormer/PLE), Gemma 4 E2B/12B Unified | Kandidaten für echte kleine Modelle | Gemma 3n/4 ja, Qwen3-Omni ja. ROADMAP WP-S1: Qwen3.5-0.8B/2B, Gemma-4-E2B |
| TinyLlama-1.1B (Output-Head), GPT-2 | Sprach-Ausgabe | nein. User lehnte GPT-2 als veraltet ab |
| Voyager, Self-Refine, STaR, Reflexion, MemGPT | Self-Dev-Schleife, Skill-Lib, 3-Split-Memory | nein (BP nutzt eigene Begriffe: Skills, Replay, Self-Edit) |
| Absolute Zero (Executor) | Code-Grounding | nein |
| RND (Burda 2018) | Neugier-Need | nein |
| Global Workspace, Interpreter-Theorie | T3/T4-Analogie | Workspace/JEF ja, Wortlaut „Global Workspace“ nein |
| Azevedo 2009 (69 Mrd. Kleinhirn-Neuronen) | Body-Less-10×-These | Cerebellum ja (als Fast-Forward), These selbst nein |
| MXFP4/NVFP4, FP4-QAT | „echte FP4-Modelle“ | FP4 nur 1× (DeepSeek-KV) |
| Termux-Issues (pytorch#186521, termux-packages#29198 Leak) | PyTorch auf Termux | nein, irrelevant seit llama.cpp |

Fazit: Neue, verwertbare Forschung kommt aus dem Chat kaum. Alles außer SIGReg ist Standard aus 2022–2025 und betrifft Eigenbau-Training, das V13 nicht mehr macht. Echte Lücke für V13: RND bzw. Neugier.

---

## 3. Präferenzen und Anforderungen des Users

### 3.1 Ziel- und Architektur-Wünsche

- **Thesen schlagen Zahlen** (Z. 10481): „Thesen > Zahlen … Prinzip ‚riesig gespeichert, winzig aktiv, winzig bewusst‘ zählt.“
  - Alle Leistungszahlen sind Schätzungen.
  - Kennzeichnung Fakt / Schätzung / Vermutung ist Pflicht.
  - Status: Der Blueprint hat ein Evidenzprinzip, die Prioritätsregel „Thesen > Zahlen“ ist nicht festgehalten.
- **Kein Chatbot, sondern ein „Mix aus Harness und KI-Architektur“** (Z. 11323).
  - „das meiste existiert ja schon … mehr ‚harness‘ nur das die modelle halt schon mit jepa lernen“.
  - Diese Linie verfolgt V13 heute bereits.
- **Dauerlauf** solange Input kommt. Ohne Input langsam auslaufen, nicht ewig selbst generieren. Siehe 1.3.
- **Alles lernt permanent außer den Safety-Regeln** (Z. 11026). „basically nothing is completely frozen“ (Z. 12421). Siehe Widerspruch 4.2.
- **Denken und Output trennen.** Der „Judge“ soll Gedanken in natürliche Sprache bringen. Das Denken bleibt latent (Ziel C).
- **Die beiden Hälften reden direkt miteinander**, nicht nur über den Judge (Z. 14399: „cross sachen … von gegenseitig als imput genutzt um zu lernen“).
- **Mindest-Output pro User-Input.** Zwang am Anfang, der „gleitend verliert und anpasst“ (Z. 14297).
- **Kleiner vortrainierter Sprachteil**, „die midelle sollten eig alle text schon können“ (Z. 24677). Damit lehnt der User das Training von Null selbst ab.
- **Später**: Tools und Selbstgespräch als Input-Quelle (Z. 11323).

### 3.2 Bedienung und Lieferform

- **Muss auf dem Handy laufen**: Termux + Python. „Mach halt so das man nt alles einzeln machen muss“.
- **Immer den fertigen Termux-Befehl mit exaktem Pfad mitliefern.**
  - Der Pfad sieht so aus: `/storage/emulated/0/Download/code (N).py`.
  - **Nicht umbenennen lassen** (Z. 15599, 18286: „Gib immer den termux befehl mit“).
  - Befehle einzeln geben, damit nichts zusammen gepastet wird.
- **Vollständige Lieferung**: Nichts weglassen oder umgehen. „lösch nt einf dinge raus … du sollst fixen“ (Z. 16986). „ich will net alles immer einzeln explizit wieder sagen“ (Z. 14399).
- **Ehrlichkeit, kein Fake.**
  - „sieht für mich aus als fakest du viel“ (Z. 23005).
  - Fake-FP4 und Fallback-Floskeln als „neural“ auszugeben, war genau der Kritikpunkt.
- **Erst organisieren und recherchieren, Code erst auf Freigabe** („jo mach“, Z. 12421).
- **Recherche nach aktuellen Modellen**: HF neueste Sortierung, artificialanalysis.ai, Modelle < 1 Monat alt.
- **Deutsch, locker.** Wünscht ASCII-Architekturskizzen bzw. ein Bild der Architektur (Z. 28182).

### 3.3 Im Blueprint nicht festgehalten

Diese Punkte sind gute Kandidaten für `USER_DECISIONS_AND_OPEN_QUESTIONS.md` (dort steht „None“):
- Pfad- und Termux-Befehlsmuster,
- „nichts weglassen“,
- „Thesen > Zahlen“,
- tippsichere Live-Logs,
- Ausbrennen mit User-Regler,
- Mindest-Output.

---

## 4. Widersprüche zwischen Chat-Ideen und aktuellem Blueprint

1. **„Bewusstsein = nur Judge, 2 KB FP4-Vektor“ (T1/These 1).**
   - Blueprint: „V13 behauptet … kein bewiesenes Bewusstsein“, „JEF != Bewusstsein allein“, JEF ist ein System und kein einzelnes LLM.
   - Der Blueprint ist hier zurückhaltender und, wie ich finde, richtiger.
   - Der 2-KB-Gedanke lebt nur als kleiner Focal/Workspace-State weiter.

2. **„Inference = Learning, alles lernt immer, nichts frozen“ (T10, Ziel D).**
   - Blueprint (Age 0): `RECORD_ONLY|SHADOW_UPDATE|APPROVED_COMMIT`, human-gated, Bodies zuerst eingefroren, Lernen über Adapter und Predictor hinter Retention-Gates.
   - Das ist der größte Konflikt mit dem User-Wunsch.
   - Die Blueprint-Linie ist technisch begründet (Vergessen, Drift). Das sollte man dem User aber ausdrücklich als bewusste Abweichung erklären.

3. **„Gleicher Residual Stream / beide schreiben in denselben 4096d-Raum“ (T3/T4).**
   - Blueprint: „Blindes Addieren eines fremden Vektors in einen beliebigen Residual Stream ist kein kanonischer Default“.
   - Weiter: „keine gemeinsame Latent-Sprache“ zwischen fremden Bodies; Callosum-Alignment `z_A≈z_B` als Zwang ist ausdrücklich verboten.

4. **Fester Takt 1…7 mit Kohärenz-Zwang 0.8 (T7).**
   - Blueprint: „Trajectory first, Halting second“, adaptiver Reasoning Effort, selektiver B1/B2-Wake, „kein C_fast-Seriellzwang“.
   - Das Prinzip „Mindestdenken mit abklingendem Zwang“ ist vereinbar. Die festen Zahlen sind es nicht.

5. **Dream 7 % vor *jedem* Output (T8).**
   - Blueprint: Dream bzw. Counterfactual läuft in Sleep B, schreibt nur Hypothesen und blockiert nie den Live-Pfad.

6. **„Riesiges Unterbewusstsein“ 15,3 Mrd. Parameter (LFM2-8B-A1B + OLMoE, 8,6 GB Q4).**
   - Auf 6 GB nicht machbar.
   - Der Blueprint bzw. Code nutzt 1,2B-Bodies. MobileMoE ist laut ROADMAP gated und ohne GGUF.
   - Die Thesen T4–T6 (Latent 18× schneller, Filterkette 10M→10k→1600→11, Body-Less 10×) sind unbelegte Rechnungen. Kein Blueprint-Gate hängt daran, und das sollte so bleiben.

7. **Training von Null mit Byte-Vokabular** (gesamter Chat-Code) gegen vortrainierte Modelle via llama.cpp im Blueprint.
   - Der User hat diesen Wechsel selbst gefordert (Z. 24677). Also nur ein historischer Widerspruch.

8. **Hot `/py`-exec** gegen den privilegierten Operator-Kanal des Blueprints.
   - Freies exec ist ein Sicherheitsloch. Nur als Whitelist-`:set` übernehmen.

9. **Lesbarer „Fallback“-Text bei schwachem Decoder** („Ich lerne noch conf … Was meinst du mit …“, Z. 27620).
   - Das ist eine verdeckte Floskel und widerspricht der Ehrlichkeit von Blueprint und User.
   - Nur mit sichtbarer Kennzeichnung `[FALLBACK]` zulassen, nie als Modellantwort zählen und nie lernen.

10. **Vereinigter Byte+Bild-Decoder und ASCII-Render jetzt** gegen STEP8 (Vision gesperrt bis nach dem Age-0-Core).

---

## 5. Retten lohnt sich bei diesen Code-Stellen

Retten heißt: die Idee übernehmen, nicht den Code 1:1, denn alles ist PyTorch-Eigenbau.

| Name | Zweck | Ort in chat2.txt | Wert für V13 |
|---|---|---|---|
| `flush_logs` / `live_flush` + `LOG_LOCK`/`LOG_Q` | readline-sicheres Live-Logging, Prompt und getippten Puffer neu zeichnen | Z. 26656–26690 (auch 18963, 20670) | **hoch**, direkt in `operator.py` |
| `launch` + `STOP_EVENT` + `TRAIN_THREAD` | ein Hintergrundjob, `stop`/`wait`, „busy“-Antwort | Z. ~27690 | mittel (W8 hat Cancel, prüfen) |
| `idle_loop` | nach X s ohne Input grounded Replay, langsames Lernen, sichtbare Idle-Zeile | Z. 27702–27740 | mittel, für WP-E |
| `think_once` | Draft-Schleife mit abklingendem Zwang `zw=1-(t-1)/6`, Mindest-Takten, Früh-Stopp, Publish, Quorum-Gate fürs Lernen | Z. 27577–27690 | mittel, als Muster für WP-D |
| `is_garbage` / `is_usable` | Terminal-Logs und Nicht-Text aus Gedächtnis und Training filtern | Z. 26777–26800 | **hoch**, vor WP-I-Labels |
| `MemoryStore` (online real/weltbild/frei/dream, offline long, rules.json, blueprint.json, `edits_used`-Budget) | editierbarer Kontext mit Budget | Z. 13596–13700 | mittel, Bedienkonzept |
| `System.self_edit` + `feedback_apply` | Konsolidierung real→weltbild, Prunen nach Score, Dream-Promotion mit gelernter `edit_penalty`, Takt/Länge/Dream-Rate aus gut/schlecht | Z. 790–880 | mittel, Idee der gelernten Edit-Bremse |
| `System.learn_gain` | Lernrate = f(Neuheit, Fehler, 1-Score), begrenzt | Z. 725–728 | mittel (Neuromodulator-Proxy) |
| `class RND` | Neugier-Signal (Predictor gegen eingefrorenes Zufallsnetz) | Z. 488–500 | mittel (1.8) |
| `System.think` | Freeze-Streak aus Δ/KL, Weltmodell-Surprise-„Schock“ erzwingt Nachfragen | Z. 741–768 | niedrig bis mittel (Halt-Features) |
| `System.improve` | Checkpoint, Änderung, Re-Score, Rollback; nach 3 Rollbacks Schlaf | Z. 846–862 | niedrig (Regression Shield existiert) |
| `safe_exec` | AST-Whitelist-Sandbox für Rechen-Grounding | Z. 642–672 (v2.9.2: 2141, blockt auch while/for) | mittel, erst mit WP-K |
| `GroundRules.propose` | Hard-Rule-Änderung nur mit y/N | Z. 633–641 | niedrig (BP §20.1 vorhanden) |
| `Router.update_bias` + `peer_bias` | aux-loss-free Balancing, Bias-Sync zwischen den Hälften | Z. 235–248, 711–717 | niedrig, nur bei eigenem MoE |
| `Callosum` (bidirektionale Cross-Attention mit lernbarem `peer_scale`, Start klein) | Hälften reden direkt, Gate startet nahe 0 | Z. 27060–27075 | niedrig bis mittel für B3-Receiver (WP-J) |
| Generate mit Repetition-Penalty 1.15, Trigram-Block, Token-Sperren, min/max | Anti-Echo | Beschreibung Z. 18901 (Tabelle #5), Code in UDec.generate Z. ~27160 | **hoch** als Sampling-Option für C3 |
| `run_tests` in `tempfile.mkdtemp` | Tests dürfen den echten Checkpoint nie überschreiben | Z. ~27745 | niedrig (Hygiene, prüfen) |

Nicht retten:
- Die Eigenbau-Modelle (JEPA/MoE/Decoder von Null, `fake_q4`, `t2l`-Hash-Latents).
- `/py`-exec.
- Die Fallback-Floskel.
- `BOOT_CORPUS`: Er enthält persönlichen User-Text.
