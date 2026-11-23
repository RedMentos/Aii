# chat1 – Auswertung (erstes Drittel „AI-Consciousness-Blueprint-Theses“)

Quelle: `chat1.txt` (33.571 Zeilen; Zeilenangaben unten beziehen sich darauf). Abgeglichen mit
`ROADMAP.md` (Stand 09.10., inkl. neuem Abschnitt WP-S1…S8) und Blueprint v10.16.1 (per grep).

**Kurz zum Inhalt:** Der Chat enthält zwei Phasen.
(a) Z. 1–16020: GLM-5.3 baut eine *selbst geschriebene* PyTorch-Single-File-Version
(`V13_CHAT_DIRECT.py` v2.1→v2.9.1, ~36M Parameter, Byte-Decoder). Sie lief auf dem Redmi
(Tests grün, Z. 13707ff.), gab aber nur Byte-Müll aus (Z. 13946).
(b) Z. 16020–29443: Der Nutzer verlangt fertige, aktuelle Modelle. Muse-Spark baut eine
llama.cpp-„Harness“ (`v13.py` v3.1–v3.4) mit zwei GGUF-Backends plus kleinem Torch-Kern.
Am Ende (Z. 29443–30408) steht der **Thesen-Prompt T1–T10 / Ziele 2A–2G** des Nutzers. Das ist
die wichtigste Quelle für Nutzerwünsche.
Viele Code-Dumps wiederholen sich (5 hochgeladene Fremd-Versionen Z. 16036–24488, zweimal
wiederholt Z. 30409–33572).

Der heutige Blueprint ist ein **anderes, weiterentwickeltes System** (A/B/C-Planes, JEF statt
Judge, native vortrainierte Bodies). Viele Chat-Ideen sind dort sinngemäß aufgegangen, aber
unter anderen Namen. Status-Legende: **fehlt** / **BP, nicht ROADMAP** = im Blueprint, aber
ohne Arbeitspaket / **abgedeckt** / **schwach**.

---

## 1. Ideen/Anforderungen aus dem Chat vs. Blueprint/ROADMAP

| # | Idee (Kurz) | Chat-Stelle (Zitat) | Status | Wert / realistisch auf 6 GB (meine Einschätzung) |
|---|---|---|---|---|
| 1 | **„Ausbrennen“/Autonomie-Budget:** läuft dauerhaft, solange Input kommt; ohne Input klingt die Aktivität ab, und der Judge lernt, wann Pause ist. Das Budget soll manuell erhöht werden können, damit das System später selbst Input holt (Tools) oder mit sich selbst redet. | Z. 29691 „Nur langsam Ausbrennen (noch) kinda hard-coded … der judge seober lernen wann er in pause gehen soll“ | **schwach**: BP hat Event-Scheduler/Idle (§22.2.1), Initiative/Self-Messaging altersabhängig (§20.3/20.4); ROADMAP WP-E (Scheduler). Ein *Abklingbudget ohne Input*, eine gelernte Pause-Policy und Self-Talk gibt es nicht. | Hoch für den Nutzer (Kern seines Ziels), billig: ein Zähler/Budget im Scheduler + gelernter Pause-Head (Shadow). Realistisch. |
| 2 | **Implizites Feedback/Konditionierung:** Der Judge lernt Lob-Muster im normalen Chattext und passt sie langsam an. | Z. 10827 „wenn du geiles arschloch immer bei gutem output kommt es au irgendwann check yk ah is gut“ | **fehlt** und widerspricht dem BP: Feedback ist typisiert und „nicht als normaler Chattext versteckt“ (BP Z. 4780). | Mittel. Machbar als *Vorschlags*-Klassifikator („war das Lob? → als :feedback buchen?“), der nur in den Shadow geht. Würde auch WP-I-Labelmangel (`INSUFFICIENT_LABELLED_COHORT`) lindern. |
| 3 | **Gelernte Penalty beim Editieren eigener Ausgaben/Kontexte**; Promotion „frei→real“ mit lernbarer Penalty | Z. 10827 „seine ausgaben editieren kann … mit yk leichter penalty, die evtl auch vom judge … gelernt werden“ | **schwach**: BP hat Provenance-Trennung, „Context-Edit-Budget“ als Age-Recht (BP Z. 4567) und Output-Commit (IH-H12). Eine gelernte Edit-Kostenfunktion fehlt. | Niedrig–mittel. Nach WP-K (Output-Commit) als Parameter `edit_cost [LEARNED]` sinnvoll. |
| 4 | **Selbst-editierender Kontext** (konsolidieren/löschen/revidieren, autonom, über einen Quorum-Gate) | Z. 2617 „mit welt modell, und selbst editier bar“, umgesetzt Z. 2626 | **BP, nicht ROADMAP**: BP §20.2 Self-Edit, §8.3 Context OS, §9.5 Forgetting. Kein WP dafür (WP-H = nur Retrieval). | Mittel–hoch. Reine Python-Logik, gut machbar. Gehört als eigenes WP neben WP-E/H. |
| 5 | **Kontext dreigeteilt: real / Weltbild / frei** (Dream-Zeilen), mit Promotion | Z. 10836 (GAP-Tabelle v2.8) | **abgedeckt** (BP §1.8 Provenance: Evidenz/Hypothesen/Dream getrennt; „World Notebook“). Die Namen des Nutzers fehlen. | Nur Mapping dokumentieren (real=Exact/Episodic, Weltbild=World Notebook/Semantic, frei=Hypotheses/Dream). |
| 6 | **Hot-Commands:** Python-Änderungen ohne Neustart (`py …`, `reload`), Modellwechsel ohne Neustart, Stop während Inferenz | Z. 15556 „inference auch stopen … pyton änderungen ohne immer neu starten“ | Stop/Cancel **abgedeckt** (IH-H15 `:cancel/:pause`, ROADMAP STEP0 PASS). `:unload/:import model` vorhanden. **`py`-Live-Code fehlt**, bewusst nicht im BP (LLM-freier Operator-Parser). | Live-Code nur als User-Befehl mit Bestätigung + Audit. Ein Debug-REPL wäre am Handy praktisch. Sicherheitsrisiko gering, weil nur der Nutzer es tippt. |
| 7 | **Mehrzeiliges Einfügen** als ein Block (Input-Drain), nicht als N Einzelnachrichten | Z. 14601ff. | **fehlt** im BP (UI-Detail). Ob der Operator das heute kann, ist unklar. | Klein, aber relevant: der Nutzer tippt nur am Handy. Prüfen. |
| 8 | **Zwei verschiedene schwere Modelle**, beide MoE, Detail mit mehr aktiven Experten als Gist | Z. 16020 „die 2 großen modelle sollen unterschiedlich sein“; Z. 25652 „beides moe … detail mehr als gist“ | **schwach**: BP verlangt „zwei komplementäre sparse bodies“, erlaubt aber denselben Base (IH-H22). Ist-Stand: B1 = B2 = LFM2.5-1.2B. ROADMAP WP-S1 schlägt Qwen3.5-0.8B als *anderen* B2 vor (dense). | Hoch (STEP2 `UTILITY_FAIL`). Die im Chat genannten MoEs (OLMoE-1B-7B Q4 ~4,2 GB, LFM2.5-8B-A1B Q4 ~5 GB) passen **nicht beide** auf 6 GB. Selbst einzeln ist das per mmap riskant (Kaltstart-Thrash, im Chat selbst eingeräumt). Eher ein Research-Kandidat mit RUNNER_PROOF. |
| 9 | **Judge-JEPA / Weltmodell-Übergangskopf** `s_t→s_{t+1}`. Seine Surprise steuert Stop, Nachfragen (must_ask) und Dream-Abbruch. | Z. 2624, Z. 10834 | **BP, nicht ROADMAP**: World-JEPA §7.2 und t+2-Predictor (STEP6) existieren, Surprise→Halting-Kopplung steht in §10.1. ROADMAP nennt World-JEPA nur im Zielbild, ohne WP. | Mittel. Ein kleiner Head, billig. Gut als Signal für WP-D (Effort/Halting). |
| 10 | **Taktung 1..7 mit „Zwang“** (Kohärenz < 0.8 → weiter) und Freeze-Stop nach 3 konsekutiven Δ<1e-3 / KL<0.01 | Z. 29691 Thesen T7, Pipeline [06]/[13] | **abgedeckt** als Konzept (Focal Loop, §10.1 Trajectory/Halting, G5B). Konkreter Konvergenz-Stopp fehlt. | WP-D könnte den Freeze-Streak als einen Halting-Kandidaten testen. Billig. |
| 11 | **Modulations-Ring:** Gewichte = Wissen; alles drumherum moduliert (Judge gewichtet Hälften, Lerntempo, Novelty→Dream-Rate, Habituation) | Z. 9145 „das wissen … halten … die gewichte … alles drum rumm … puffer der sinnvoll moduliert“ | **BP, nicht ROADMAP**: Layer 6/13 Modulator-Bus (M_truth…M_retention), Gain F1. ROADMAP hat kein WP für den Modulator-Bus (nur Salience/Homeostasis). | Hoch als Prinzip, Python-only machbar. Gehört zu WP-D/F/I. |
| 12 | **Neuromodulator/„Bock/Angst“-Wertsystem** statt fixer Gewichte w1..w5 | Z. 30285 Abschnitt „Emotion / Value System fehlt komplett“ | **abgedeckt** (BP Layer 6, typisierte Modulatoren), im Code nicht umgesetzt (siehe 11). | wie 11 |
| 13 | **Aktives Vergessen**, Hippocampus-Replay/Konsolidierung | ebd., Punkte 2 und 6 | **abgedeckt** BP §9.5, §15, L8.3. ROADMAP: WP-E/WP-S7 (Replay); Vergessen nicht explizit. | Mittel. In WP-E aufnehmen (Decay/Archiv-Regeln). |
| 14 | **Digitale Interozeption** als Grund zu „broadcasten“ | ebd., Punkt 3 | **abgedeckt** BP §7.4 (RAM, Akku, Temperatur modulieren Compute/Dream). Resource-Monitor existiert (STEP0). Kopplung an Lernen/Dream fehlt. | Billig, sinnvoll. In WP-E (Ressourcenmodus) teils schon drin. |
| 15 | **6–7 verschachtelte Zeitskalen** (H-JEPA) statt nur 1/8 Token | ebd., Punkt 4 | **BP, nicht ROADMAP** (§41.3, §41.11) | Niedrig für jetzt. |
| 16 | **„Nichts komplett frozen“**: alles lernt dauerhaft, außer den Safety-Regeln (nur per Feedback); Inference = Learning (T10) | Z. 1221 „basically nix is komplett frozen“; Z. 30285 „bisauf die savety rules … sollen lernen“ | **Widerspruch** (siehe §4). BP: Age-0 = Shadow, Lernen nur human-gated; Teacher frozen. | Der Nutzer erwartet sichtbares Dauerlernen. Ein ehrlicher Zwischenschritt: Shadow-Updates sichtbar machen (Telemetrie „was hat es heute gelernt“). |
| 17 | **Progressiver Merge à la Gemma-4-12B-Unified:** Encoder/Decoder langsam integrieren; fällt die Qualität, wird der Merge zurückgenommen | Z. 7440, Z. 10827 „encider werden gemerged wie bei gemma 12b langsam“ | **abgedeckt** (BP §18.12, §76 Teacher-Retirement, §48.4 Gemma 4 12B, §3.4.11). Liegt in STEP11 (gesperrt). | Langfristig. Die Idee „Quality-Gate setzt Merge zurück“ (Z. 9136) passt gut zu Teacher-Removal als Experiment. |
| 18 | **Bild-/Video-Output**, einheitlicher multimodaler Decoder; „Videoclips als Traumsequenzen“ | Z. 5639 „output sachen wie yk bilder videos“ | Bild: **abgedeckt** (C7-Renderer, STEP8/10 gesperrt). Video-Output: **fehlt**. | Auf 6 GB unrealistisch für Video. Bild erst nach STEP7. |
| 19 | **Free Dream 7 % vor jedem Output**, 50 % „grounded edit budget“ | Thesen T8 (Z. 29691) | **Widerspruch** (siehe §4); BP: Dream offline, keine Faktenquelle. | Konzept passt besser in Idle-Sleep (WP-E). |
| 20 | **Thesen-Messgrößen:** winziger bewusster Zustand (2 KB), Aktiv-Anteil (Sparsity 1–2 %), Filterkette 10M→10k→1600→11, Latent vs. Token-Geschwindigkeit | Z. 29691 T1–T6 | **fehlt** (BP vermeidet Bewusstseinsclaims, Z. 155) | Als Telemetrie billig: aktive Parameter pro Turn, Größe des Fokus-Workspace, Latent-ms vs. Token-ms. Würde dem Nutzer zeigen, dass seine Thesen gemessen werden. Kein Architektur-Muss. |
| 21 | **Fakt / Schätzung / Vermutung** strikt markieren | Z. 29691 „Markiere klar: Fakt (gemessen), Schätzung …, Vermutung“ | **abgedeckt** (Claim-Limit W3, IH-H31, Tags [RESEARCH]/[BOOT]) | – |
| 22 | **Hardwareabhängige Größen** (Auto-Preset nach RAM), System lernt, effizient zu bleiben (Zeitbudget drosselt Dream/Batch) | Z. 10837–10838 | **abgedeckt** (Resource State Machine IH-H23, M_cost, Response Governor) | – |
| 23 | **Token-Prediction-Head im Judge / MTP / sparse prediction** | Z. 30285 „token prediction layer evtl in judge“; Z. 16027 | **schwach**: BP sieht MTP nur als Serving (Z. 7586) | Niedrig. |
| 24 | **Selbstverbesserung über Code** („improve code: <py>“, STaR, Voyager-Skill-Lib, Reflexion get_best) | Z. 29691 Audit-Prompt; Code `safe_exec` | **schwach**: Skills/Proceduralization (WP-F) und Tool-Security IH-H29 abgedeckt; Selbst-Code-Änderung nicht vorgesehen | Nicht vor WP-K. Riskant. |
| 25 | **Externer Kontext**: `file <pfad>` importieren, `fetch <url>` (standardmäßig aus) | Z. 1300 | **schwach**: Tools erst P3/WP-K; Datei-Import nicht explizit | Datei-Import in Memory ist billig und für den Nutzer nützlich (Trainings-/Wissenstexte vom Handy). |
| 26 | **Judge segnet allen Output ab**: Output geht immer raus, aber nur genehmigter Output fließt ins Weltbild | Z. 10835 | **abgedeckt** (eigene Outputs sind keine Faktenquelle, BP §1.8; Output-Commit) | – |
| 27 | **Hard-Rule-Änderung nur per Rückfrage** „soll ich Rule ändern? {old}->{new}“ | T9, Z. 29691 | **abgedeckt** BP §20.1 (proposal→diff→approval), STEP0 Rules | – |
| 28 | **B1/B2 reden direkt**, nicht nur über den Judge (Callosum) | Z. 5639 „die 2 reden auch Miteinander“ | **abgedeckt** BP §1.4, B3, WP-J | – |

---

## 2. Forschungsreferenzen im Chat und ob der Blueprint sie nennt

| Referenz (im Chat) | Wofür im Chat | im BP? |
|---|---|---|
| I-JEPA, V-JEPA 2 (arXiv 2506.09985, Assran 2025): L1-Loss, EMA + Stop-Grad gegen Kollaps, kein VICReg | JEPA-Loss-Wahl (Z. 24502, 28054) | Name/arXiv-ID: **nein**. EMA/JEPA allgemein: ja (§13). ROADMAP WP-S4 nennt LeJEPA/SIGReg |
| H-JEPA (LeCun, hierarchisch) | mehrere Zeitskalen | **nein** (Konzept §41.3 ja) |
| VICReg, InfoNCE (τ 0.07), BYOL, RND (Novelty mit EMA-Target) | Loss/Novelty | **nein** (Begriffe kommen nicht vor) |
| DeepSeek-V3 (arXiv 2412.19437): aux-loss-freier Bias nur in Top-k-Selektion, Sigmoid-Gates, `swiglu_limit` | Router | V3 **nein**; DeepSeek-V4/V4.1-Flash **ja** (§48.6) |
| DeepSeek-V4, Qwen3.8 (Server-MoEs, „nur Mechanik übernehmen“) | Konzepte (MTP, Sparse Attention) | V4 ja; Qwen3.8 **nein** |
| Switch/Mixtral/DeepSeekMoE, z-loss, Expert- vs. Token-Choice, Capacity | MoE-Training | **nein** (BP: native Router nicht patchen) |
| Gemma 4 (12B Unified, E2B/E4B MatFormer) | Merge-Konzept | **ja** (§48.4, Ref 26/27; MatFormer nur bei Gemma 3n) |
| Qwen3-0.6B, Qwen3.5-0.8B (unsloth GGUF) | Detail-Body | BP **nein**; ROADMAP WP-S1 **ja** (Qwen3.5-0.8B) |
| LFM2.5-1.2B-Instruct, LFM2-8B-A1B, LFM2.5-8B-A1B (LiquidAI) | Gist-Body | LFM2.5-1.2B nur ROADMAP (Ist-Body); 8B-A1B **nein** |
| OLMoE-1B-7B-0924 (AllenAI, 64 Exp/top-8) | Detail-MoE | **nein** |
| MobileMoE | als ungeeignet verworfen (kein GGUF, NC-Lizenz) | **ja** (§IH-H6; ROADMAP S1 stuft ebenfalls ab) |
| EdgeMoE; llama.cpp mmap-Demand-Paging, Issue #19163 (Prefetch beim Laden) | MoE > RAM | mmap ja (9×), llama.cpp ja; EdgeMoE und Issue **nein** |
| MXFP4 (OCP E2M1, E8M0) / NVFP4 nur Blackwell; Q4_K_M als echter 4-bit-Pfad; QAT/STE-Fake-Quant | „alles FP4“ | MXFP4/NVFP4 **nein**; INT4/QAT/GGUF ja |
| TinyLlama, GPT-2 (dbmdz/german-gpt2), DistilGPT2, fastText | vortrainierter Decoder (verworfen) | **nein** (veraltet, egal) |
| STaR, Voyager (Skill Library), Reflexion, „Absolute Zero“-Executor | Selbstverbesserung | **nein** (Skill Store §6.2 als Konzept ja) |
| Global Workspace Theory, Interpreter-Theorie (Gazzaniga), Split-Brain | Bio-Begründung | GWT als Name **nein**; Split-Brain ja; „Interpreter“ nur in anderem Sinn |
| Bio-Zahlen: 69 Mrd. Kleinhirn-Neuronen, Neocortex 16 Mrd., 1–2 % Feuerrate, Auge 10M bit/s | „Body-less 10x“-These | **nein** (BP: Analogien, keine Bewusstseinsclaims) |

Vorsicht: Mehrere Modellangaben im Chat (Qwen3.8, LFM2.5-8B-A1B, Dateigrößen) behauptet
Muse-Spark „verifiziert“. Ich habe sie nicht geprüft. ROADMAP WP-S1 enthält nur einen Teil davon.

---

## 3. Nutzerpräferenzen / Anforderungen (aus den User-Nachrichten)

Im Blueprint erfasst oder kompatibel:
- Läuft auf dem Redmi Note 10 Pro, Termux, Python bevorzugt (Z. 29691 „termux mit phyton … am besten“).
- Mindestens 4-bit-quantisiert, „möglichst klein“ (Z. 16027).
- Hard Rules ändern sich nur per Rückfrage. Output kommt immer. Kein externer LLM-as-Judge.
- Zahlen sind Schätzungen, Prinzipien zählen („Thesen > Zahlen“, Z. 29691).

**Nicht oder kaum im Blueprint festgehalten:**
1. **„Thesen > Blueprint“**: Bei Konflikt gelten T1–T10/2A–2G (Z. 29691 „Wenn Blueprint vs T1-T10 kollidiert, nimm T1-T10“). Der heutige BP hat eigene LOCKED-Regeln. Die Priorität der Nutzerthesen steht nirgends. Das sollte geklärt werden (Entscheidung beim Nutzer).
2. **Nicht ständig das Ziel verdrehen, alte Konzepte bewahren**: „dreht man immer zum unsinnigen es nerft“ (Z. 10827), „schau die alten sachen nochmal durch“ (Z. 7440). Der BP hat dazu W1/IH-H0 (Preservation), das passt.
3. **„Mischung aus Harness und Architektur“**: Bestehende Komponenten wiederverwenden statt alles neu bauen (Z. 29691 „eig sollte da garnich so mega vuel code neu gemacht werden“). Passt zur ROADMAP-Beobachtung §7.
4. **Wirklich aktuelle Modelle/Forschung**, auf den HF-Seiten nach „neueste“ sortiert, nicht nach Bestenlisten, und alle Versionen einzeln geprüft (Z. 25649). Für die Modellwahl (WP-G/S1) wichtig.
5. **Zwei unterschiedliche schwere Modelle**, beide MoE, Detail mit mehr aktiven Experten (Z. 16020, 25652, 26835). Der Ist-Stand (B1 = B2) verletzt das.
6. **Ohne Input irgendwann stoppen**, nicht endlos selbst generieren (Z. 30285). Das Ausbrennen soll später manuell hochstellbar sein (Z. 29691).
7. **Alles lernt permanent**, außer den Safety-Regeln (Z. 30285, Z. 1221).
8. **Befehle während des Laufs**, Inferenz stoppbar, keine Neustarts für kleine Änderungen (Z. 14543, 15556).
9. **„Kein Metapher-BS“**: Jedes Konzept soll tatsächlich funktional existieren (Z. 28051). Das passt zu W3/IH-H33.
10. **Komplette Dateien liefern, nicht nur ankündigen** (Z. 13391 „Dude du schreibst sie nie“). Der Nutzer arbeitet nur am Handy: copy-paste-fertig, ein Befehl.
11. Bild- und später Video-Output gewünscht (Z. 5639).
12. Sprache: Deutsch. Der Nutzer will Ehrlichkeit statt Marketing („kein Gaslighting“).

---

## 4. Widersprüche Chat ↔ aktueller Blueprint

1. **Judge = einziges „Bewusstsein“/zentraler Richter** (T1) ↔ BP: „JEF != one Judge LLM“ (Z. 11713), „kein einzelner Master-Controller“ (§41.2), „C5 = candidate competition, not single judge scalar“ (Z. 12967). Funktional ist der Judge im JEF + Focal Coalition aufgegangen. Dem Nutzer sollte man das Mapping erklären.
2. **Gemeinsamer Residual-Stream, in den beide Hälften schreiben** (T3) ↔ BP: private Body-States, ein Latent-Kanal muss seinen Nutzen erst beweisen, `NO_MESSAGE` ist erlaubt, ein Alignment-Zwang z_A≈z_B ist verboten (Z. 7316).
3. **Dream 7 % vor jedem Output und Rückschreiben in den Zustand** (T8) ↔ BP §1.6 „Dream … blockieren niemals die sichtbare Antwort“, `DREAM.fact_write_gain [LOCKED=0]`.
4. **Inference = Learning, alles permanent plastisch** (T10, „nix frozen“) ↔ BP Age 0: `ACTUAL OPTIMIZER LR [BOOT, SHADOW ONLY]`, Lernen nur über Freigabe, „Lifetime plastic, aber nicht überall gleichzeitig“ (§1.10). Der A2-Teacher ist frozen, native Top-k wird nicht gepatcht.
5. **Zwei verschiedene Modelle** ↔ IH-H22 erlaubt denselben Base-Checkpoint. Der Ist-Code nutzt genau das.
6. **Detail hat mehr aktive Experten** (Z. 25652) ↔ eigene Altquellen des Nutzers: Detail kd=1 (top-1), Gist kg=2 (Z. 12722). BP: „Detail schärfer/selektiver“ (§1.2.1). Die Nutzerangaben widersprechen sich selbst, das sollte man klären.
7. **Implizites Feedback aus Chattext** ↔ BP Z. 4780: Feedback wird typisiert und „nicht als normaler Chattext versteckt“.
8. **Output IMMER, nie nichts sagen** (2F) ↔ BP §1.6 erlaubt „Unsicherheit/Abstinenz markiert“. Das ist nur ein kleiner Konflikt: auch eine markierte Abstinenz ist ein Output.
9. **Kappa-Modulation der Experten durch den Judge, eigene MoE-Router, Aux-Loss** ↔ BP §1.3/1.2.5: Native Router bleiben autoritativ. Eingriffe sind nur über Gain/Adapter erlaubt.
10. **Frozen Stem 100M** (Blueprint v1.2 des Nutzers, Z. 29691 [02]) ↔ seine eigene spätere Aussage „nix frozen“. Der heutige BP kennt einen frozen A2-Teacher als Scaffold, das ist ein Kompromiss.
11. **Byte-Level-Eigenbau-Decoder** (Phase a) ↔ BP/ROADMAP: native vortrainierte Bodies. Die Phase-a-Idee ist faktisch überholt. Der Nutzer hat das selbst eingeleitet (Z. 16020 „modelle nutzen dies schon gibt“).

---

## 5. Code im Chat, der sich zu retten lohnt (nur Referenzen)

Alles ist Python/PyTorch, ungetestet außer v2.9.1 (lief auf dem Redmi). Behandle es als
Ideensteinbruch, nicht als Drop-in.

| Snippet | Zweck | Ort (chat1.txt) | Nutzen für V13 heute |
|---|---|---|---|
| `Backend` (llama-server-Start, Streaming-`generate` mit `stop_event`, Slot-Cancel) + `FakeBackend` + Offline-Tests | Stop während Inferenz, Tests ohne Modelle | v3.1 `v13.py` ab Z. 24552 (Backend ~Z. 24898, FakeBackend ~Z. 25218); v3.4 ab Z. 28093 | Vergleich mit dem heutigen Runner/Cancel. FakeBackend-Muster für Cloud-Tests (WP-B) |
| `do_doctor` mit Warnung Datei- vs. RAM-Größe, mmap/MAP_POPULATE-Kaltstart, Q3-Fallback | Modellgröße auf 6 GB prüfen | v3.3 ab Z. 26887, v3.4 `do_doctor` | Ergänzung für `:doctor` und MoE-Kandidaten (WP-G/S1) |
| `safe_py` / `safe_exec` (AST-Allowlist, blockt Attribute/Import/Schleifen) | Live-`py`-Befehl, Sandbox | `safe_exec` Z. 718 (v2.1) … Z. 16997; `safe_py` in v3.1/v3.4 | Basis für einen optionalen Operator-REPL (Idee 6) |
| Input-Drain/Paste-Erkennung + `stop`-Check im Generate | Mehrzeiliges Einfügen, Abbruch | Z. 14601–14710 (Design), Patch ~Z. 15389ff. | Idee 7 |
| `self_edit` (consolidate/delete/revise, `skey()`-Fix, Promote frei→real mit Penalty) | Selbst-editierender Kontext | Z. 3506 (v2.3) … Z. 11971 (v2.8); Fix-Beschreibung Z. 28054 Tabelle #5 | Idee 4/3 |
| `trigger`-Head + `fb_buf` (lernt Lob-Muster aus gut/schlecht-Marks) | Implizites Feedback | v2.8 ab Z. 10846 (Tabelle Z. 10841); v3.4 Judge | Idee 2 (als Shadow-Vorschlag) |
| WM-Übergangskopf + Surprise → Stop/must_ask/Dream-Abbruch, mit Warmup | Weltmodell-Signal | v2.3 ab Z. 2627 (Beschreibung Z. 2624) | Idee 9/WP-D |
| `RND` mit EMA-Target (Habituation) | Novelty-Signal M_novelty | Z. 1237 | Modulator-Bus |
| `quality_gate` (Merge-Level fällt bei Score-Einbruch zurück + Rollback) | „Merge fällt eh wieder raus“ | Z. 8456 (v2.6) … | Muster für Teacher-Retirement/Adapter-Freigabe |
| `Router.update_bias` (aux-free, nur bei `torch.is_grad_enabled()`), EMA per Namens-Matching statt `zip` | korrektes EMA/Router-Update | Z. 219/229; Fehlertabelle Z. 18–39 | Für eigene Heads/Predictor (STEP6, WP-S4). Die Fehlertabelle Z. 14–39 ist eine gute Checkliste typischer JEPA/MoE-Bugs |
| `param_groups` (kein Weight Decay auf Norm/Bias/Pos) | Optimizer-Hygiene | Z. 950 | für den Train-Runner (WP-I) |
| `GroundRules` mit „soll ich Rule ändern?“-Dialog | Human-Gate | Z. 701 | Vergleich mit den heutigen Rules (STEP0) |
| Taktung mit Freeze-Streak (3× Δ<1e-3 oder KL<0.01) | Halting-Kandidat | v2.9-Plan Z. 13014; Code in den Fremd-Versionen ab Z. 16036 | WP-D-Ablation |
| `training_data.txt`-Seed (deutscher Mini-Korpus) | Decoder-Warmup | Z. 14201 | wertlos für heutige vortrainierte Bodies |
| Fremd-Versionen `code (4).py`/`(3)`/`(2)`/`(1)`/`code.py` | v2.9.2–v3.0 anderer KIs | Z. 16036–24488 (Duplikate Z. 30409ff.) | nur bei Bedarf. `code (3).py` laut Muse-Spark kaputt (Z. 24502 #5) |

---

## Fazit (ehrlich)

Inhaltlich ist der Blueprint v10.16.1 dem Chat weit voraus. Fast alle Mechanismen (Callosum,
Dream/Sleep, Rules-Gate, Modulatoren, Vergessen, Interozeption, Output-Garantie) sind
abgedeckt. Die echten Lücken sind eher **produktnahe Wünsche des Nutzers**:
- Ausbrenn-/Autonomie-Budget mit gelernter Pause,
- implizites Feedback,
- Live-Befehle/Paste-Handling,
- zwei wirklich verschiedene Bodies,
- sichtbares Dauerlernen.

Dazu kommen BP-Teile ohne Roadmap-Paket: Self-Edit/Context-OS, Modulator-Bus, World-JEPA.

Der größte offene Konflikt ist grundsätzlich: Der Nutzer sagt „Thesen > Blueprint“ und
„alles lernt immer“. Der Blueprint sagt „Age 0 = Shadow, human-gated“. Das sollte man dem
Nutzer einmal klar vorlegen und nicht still auflösen.
