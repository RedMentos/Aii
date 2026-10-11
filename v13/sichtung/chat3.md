# chat3 – Abgleich „AI-Consciousness-Blueprint-Theses“ (letztes Drittel) mit Blueprint v10.16.1 + ROADMAP

Quelle: `scratchpad/chat3.txt` (32 263 Zeilen; Zeilennummern unten = Zeile in dieser Datei). Zeitraum laut Chat 05.–06.09.2026,
Modelle: grok-4.6, qwen3.8-flash (Großteil), glm-5.3-flash, muse-spark. Inhalt: (a) Zeilen 1–498 alter Code „V13.1 FIXED MOBILE“,
(b) 499–5773 Spezifikations-Ping-Pong (Bauliste → SPEC v4 … v7.3 → PLAN v8/v9/v10 → 9 „Recherche-Pässe“ → MASTER-BLAUPAUSE v1.0),
(c) 5776–31545 Coding auf dem Redmi (V13_B1…B6, V13_RUN, FIX1–4, ~90-KB-Dateien mehrfach), (d) 32074–Ende MASTER-BLAUPAUSE v1.1.
Plus `x/07_ZUSATZ_MATERIAL/KI_Zensur_Privatsphaere_Grundbasis.md`.

Wichtige Vorbemerkung (ehrlich): Der Chat liegt **vor** Blueprint v10.x. Vieles ist im Blueprint in anderer Sprache wieder
aufgegangen (Split-Brain, getrennte Lernpfade, Age, Replay, Teacher-Removal, Ports). Die Recherche-„Belege“ der Qwen-Pässe sind
teils sicher echt, teils sehr wahrscheinlich erfunden (arXiv-Nummern aus „2026“, exakte Prozentzahlen). Ich habe sie **nicht**
online verifiziert; Abschnitt 2 markiert, was ich aus eigenem Wissen kenne.
Das Coding-Ergebnis des Chats war laut v1.1 selbst: „es trainiert nur ein 256-d-Platzhalternetz; A und C werden nicht verändert“
(Z. 32092) und OLMoE lief mit **0,2 tok/s** – das ist der wichtigste harte Befund daraus.

---

## 1. Ideen/Anforderungen aus dem Chat vs. Blueprint/ROADMAP

Status: **fehlt** = weder Blueprint noch ROADMAP · **BP-only** = im Blueprint, nicht in ROADMAP · **teilw.** = Prinzip da, Konkretes fehlt ·
**abgedeckt**. Spalte „Wert/6 GB“ = **meine Einschätzung**.

| # | Idee (kurz) | Fundstelle im Chat | Status | Wert / realistisch auf 6 GB (Urteil) |
|---|---|---|---|---|
| 1 | **Klartext-Regelwerk, schadensbasiert, nicht zensierend** (7 Regeln: kein aktiver Schaden, Mündigkeit, Ehrlichkeit, akute Krise, kein Betrug, Änderung nur mit `y`, „Denken frei, Sprechen gefiltert“) | User Z.1370 „eine die nich zensiert nur aktiven schaden … blockiert“; Text Z.1389–1398 | **fehlt** (BP hat nur den Mechanismus §20.1 Proposal→Diff→Approval, F6; keinen Inhalt) | hoch, billig (Textdatei + Bias). Passt 1:1 zum KI_Zensur-Dokument. |
| 2 | **Filter nur am Ausgang, nie im Denken/Traum**; MoE lernen geblockte Inhalte erst, wenn der Filter reif ist | Z.1381 „Filter vor Gewichten“, Z.1397 „Zensur im Kopf macht Lügen im Mund“ | **fehlt** | mittel–hoch; Architekturregel, kostet nichts. |
| 3 | **`note 1–10`** als Primärfeedback (6 = neutral) + `?note`: System sagt seine Note vorher voraus → Kalibrierung; C lernt schnell, Bodies nur nach ≥3 gleichsinnigen Bestätigungen | User Z.1370 „von 1 bis 10“; Z.1377, Z.1560–1563 | **teilw.** (BP §17B.2 HUMAN_DECISION ohne Skalar; ROADMAP nur `:feedback … --learn`) | hoch: liefert schnell Labels gegen `INSUFFICIENT_LABELLED_COHORT`; trivial umzusetzen. |
| 4 | **Lehrlauf/Datensatz-Modus**: `Frage⇥Antwort`-Datei mit festen Antworten, oder Lehrer, der aus *echtem* Kontext destilliert | User Z.1832 „simplen datasets wo feste antworten“, Z.1971 „lehrlauf“; Master §18 | **teilw.** (BP STEP4 Reference Teacher; kein Q/A-Import, nicht in ROADMAP) | hoch für WP-I (Label-Mangel); billig. Achtung: nur vom User gelieferte Daten zählen als Human-Labels. |
| 5 | **„Reifungszähler“**: zählt alle je verarbeiteten Tokens, per Befehl setz-/resetbar, `empfindlichkeit`; lockert nur äußere Limits, nie Gewichte/Regeln. Später: **Doppel-Tür** Tokenboden **und** gemessene Kompetenz | User Z.1325 „counter … wie viele tokens verarbeitet“; Z.1334–1340; Δ88 Z.~5180 | **Widerspruch** zu BP §25 „Age als Tokenzähler … NICHT“; Doppel-Tür-Variante ist mit BP-Stage-Gates vereinbar | mittel: als *ein* Signal in `age.py` (WP-C) sinnvoll, nie allein. |
| 6 | **Strafen/Wächter nie 0** (Boden 0,05); werden nur leiser, wenn ihr inneres Gegenstück 500 Antworten recht hatte | User Z.1370 „penaltys solkten nie auf 0 sinken“; Master 16.5/16.7 | **teilw.** (BP §17A Scaffold-to-Policy, Scaffolding nur nach Parity reduziert; kein expliziter Boden) | mittel; billig als Invariante. |
| 7 | **Selbststopp ohne Input**: Hintergrund verlangsamt 10×→100×→fast aus, Input weckt sofort | User Z.1370 „von selber stopt“; Z.1385, Master 16.8 | **teilw.** (BP Scheduler/idle, Sleep C; ROADMAP WP-E) | mittel; wichtig für Akku/Thermik am Handy. In WP-E als Backoff aufnehmen. |
| 8 | **Notizbuch als „Obsidian in Text“**: editierbare Markdown-artige Einträge (`text` + Latent), typisierte **Kanten** (`bezieht/folgt/widerspricht/erklaert/herkunft`), Fundstellen-Kante zur Original-User-Zeile, Abruf = Top-8 latent **+ 1-Hop-Expansion**, `:graph`, Export .md | User Z.1229 „obsidian“, Z.5012 „link system“; Δ80 Z.~5105 | **BP-only, schwach** (World Notebook nur Stichwort Z.2317, §9.4 Causal Memory Graph = 1 Satz); ROADMAP WP-H nur Embedding-Abruf | **hoch**, realistisch (jsonl, kein Modell nötig). Direkt in WP-H aufnehmen. |
| 9 | **Seed-Gerüst** (~100 Einträge, Englisch): Regeln mit Beispiel, Abstinenz-Formeln, leere Kategorien; `herkunft=seed`, nie Zitat-/Lernquelle, editier-/löschbar, Original bleibt | User Z.5012 „dump … vorgefertigtes“, Z.5246 „englishen seed“; Δ81 | **fehlt** | mittel; billig. |
| 10 | **Abstinenzpfad + sichtbare Belegzeichen** (`[id]` / „ich vermute:“ / Abstinenzsatz), `abstinenz_rate` als Messwert (≈0 ⇒ Gate zu locker) | Δ82; v1.1 Δ66 Z.32089, Test 29.49 | **teilw.** (BP: abstain/uncertainty §11, Provenance strukturell; keine sichtbaren Marker, keine Rate) | hoch; macht Halluzination messbar. Runtime hat schon `abstain`-Logik. |
| 11 | **Selbstzitat-Bremse + Mischungsquoten**: eigene Erzeugnisse nie Zitatquelle; Paare ≥60 % Mensch, davon ~50 % alt, ≤10 % eigen, 0 % Seed; Replay-Puffer 1024, Rückgang >2 % ⇒ Replay rauf | Δ83, Δ86 (Z.~5140–5175) | **teilw.** (Prinzip BP §25 „eigene Ausgaben nicht als Faktenquelle“; Zahlen fehlen, BP §27 nennt Replay-Scheduler „offen“) | mittel–hoch; Zahlen als Startwerte für WP-E/WP-I. |
| 12 | **Längenregler + Dekodierwerte für Klein-LMs**: Bänder 28/60/100/160 (Default kurz), temp 0,6, top_p 0,95, top_k 20, no_repeat_ngram 4, rep-penalty 1,08 (≤1,15), min_new 8 | User Z.4827 „regelbaren output“; Δ73, Δ84 | **fehlt** im BP (runners.py hat rep-penalty) | hoch, sofort nutzbar gegen C3-„query echo“/Geschwätz. |
| 13 | **Melderecht/Proaktivität** konkret: M1 offene Frage, M2 Muster, M3 Störung (immer), M4 Wunsch (1/60 min, 4/Tag); 3× ignoriert ⇒ Pause; `:ruhe 22–07`; nur User darf abschalten | User Z.4827 „selber melden?“; Δ68–72, Δ87 | **teilw.** (BP §20.4 nur „Relevance Gate, Rate Limit“; nicht in ROADMAP) | niedrig–mittel jetzt; braucht Termux-Notification. Später. |
| 14 | **Heterogene MoE-Hälften**: Detail = viele kleine aktive Experten, Gist = wenige größere; **zwei verschiedene Modellfamilien**, beide MoE, **nicht dicht** | User Z.1229 „gist soll weniger aber etwas grösere aktive… KEINE DICHTEN MODELLE“, Z.1073 | **Widerspruch** (BP IH-H22 erlaubt gleiche Basis, §87 MobileMoE für beide; Ist-Code: B1=B2 = dichtes LFM2.5-1.2B) | Wert für User sehr hoch; auf 6 GB nur mit Klein-MoE (≤~1,5 B total) machbar. Chat-Messung: OLMoE-7B → 0,2 tok/s. |
| 15 | **Experten teilweise im RAM + gelerntes Nachladen** (Prefetch-Netz sagt nächste Experten voraus; Hot-Cache, int4 für kalte Experten, Zipf-Statistik aus eigenem Notizbuch) | User Z.1119 „selber predicten lernen welche aktiv reingeladen“; Z.1179–1182, Δ34, Δ44–46 | **teilw.** (BP nur `prefetch_gain`-Knöpfe, §24.33 misst Residency) | mit llama.cpp-Runner kaum steuerbar → derzeit niedrig realistisch; Forschungstrack. |
| 16 | **Token-Kanal zwischen Hälften**, nur auf Anforderung von C, Kontingent (≤1/3 Loops, Cooldown 3), Nutzen gelernt (Surprise↓ = Belohnung), nie Merge | User Z.1290 „vom judge angefordert… nt übertreiben“; Z.1298, Z.1588 | **abgedeckt** (SYMBOLIC-Kanal, Channel Utility B3-H9) – Kontingent-Lernen nur teilw. | ok. |
| 17 | **Gelerntes Tempo/Länge/Tiefe** („soll selber lernen wie schnell“); Zeitkopf sagt Kosten voraus, Boden/Himmel fix | User Z.3279; Δ33 | **abgedeckt** (BP §10.2/G5B; ROADMAP WP-D) | ok. |
| 18 | **Andocken→Nachlernen→Abkoppeln** von Encodern/Decodern/Lehrern; Parität anfangs **200 Siege**, mit Alter sinkend; danach „Hafen/Park“, nie löschen, `:dock wake` bei Regression | User Z.1710, Z.1832 „am anfang gerne 200 mal“; R14 Z.~1800 | **abgedeckt** (BP §18.4, §76, `removal_gate`); Zahlen fehlen | ok; 200/3-Siege als Startwerte nutzbar. |
| 19 | **Steckplatz-Register für alles mit Input/Output** (auge, ohr, spiegel, mund, feder, griff, bibliothekar, uhr …); konkret über **termux-camera-photo / microphone-record / tts-speak / screenshot** | User Z.1832 „slots für alles was nen … künstlicher mensch brauchen würde“; Plan v9 §0.4 | **teilw.** (BP ModalityPort §19.1A, STEP8–10 gesperrt; Termux-API nirgends) | später (STEP8+), aber Termux-API ist der realistische Weg am Handy. |
| 20 | **Gehirn einfrieren/exportieren in 3 Schichten**: Körper (Modelle) / Geist (eigene Gewichte, arch-gebunden + Migrationsvermerk) / Steuerung (Notizen, Regeln, Zähler – immer portabel); Modelltausch = Notizen als Replay neu anfüttern | User Z.1784 „exportieren … als ganzes brain oder als Teile“; R15 | **teilw.** (BP Generation-Manifest, `:backup/:export model`, Swap §19.4; `backup.py` existiert) | mittel; die Schichtentrennung ist eine gute Doku-Regel. |
| 21 | **Phasenmaske gegen MoE-Vergessen** + **Drift-Anker gegen die Original-Gewichtsdatei** (keine RAM-Kopie nötig) | Δ48a/b Z.~4300 | **abgedeckt** (BP §91 Phase A–D, §21 Routing Drift); Drift-Anker-Trick **fehlt** | Anker-Trick billig, gut für WP-I/WP-J. |
| 22 | **Kein Cosinus-LR im Endlosbetrieb**: konstante Raten + messgesteuerte Halbierung bei Verlustanstieg | Δ85 | **fehlt** (BP Layer 15 nur LR-Werte) | mittel; kleine, richtige Regel. |
| 23 | **„Lernen lernen“ messbar**: Kopf sagt eigene Lernkosten (Schritte bis stabil, Vergessen, nötige Rückmeldungen) voraus; Übertragbarkeitsmaß; Deutsch als späterer Test | User Z.4365 „lernen lernt“; Master §21 | **fehlt** | Forschungswert mittel; erst nach STEP7 sinnvoll. |
| 24 | **Live-Knöpfe im Chat**: alle unsicheren (altersabhängigen) Werte per `:werte`/`:wert NAME X` stärker/schwächer, jeder Wert mit Quelle-Art `[gemessen]/[gerechnet]/[geschätzt]/[Entscheidung]` | User Z.5773 „unsicheren values … während chat ändern“; `kn()`-Registry Z.18322 | **teilw.** (BP IH-H5 KnobSpec, IH-H31; kein Chat-Kommando in ROADMAP) | hoch für den User, billig. |
| 25 | **Selbstverbesserung per Code** (`verbesser code:`, `safe_exec` nur Ausdrücke, Rollback nur des Teils, 3× ⇒ Pause) und **editierbarer Blueprint[12]** | Z.123–125, Plan v9 §15 | **fehlt** (BP Self-Edit nur „safe config“) | niedrig; Sicherheitsrisiko, bewusst weglassen. |
| 26 | **Ehrlicher Lernstatus** `lernt=mini|haelften|keins` | v1.1 Δ70, 02.17 | **abgedeckt** (W3/IH-H33) | – |
| 27 | **Gemessene Redmi-Werte** (pure torch, Termux, torch 2.11): fp32 22–32 GFLOPS (3 Threads), UFS 4K-random 104–127 MB/s, OLMoE-1B-7B int8→fp32 **0,2 tok/s**, SmolLM2-135M 8,8–14 tok/s (Bank) / ~50 tok/s Vorlauf, anon-RAM 158–451 MB, mlock ok, Disk 91 % voll (10 GB frei); mmap nur unter `$HOME`, 4 Threads langsamer als 3 | Z.23877–24031, Z.24092; Δ39, Δ43 | **fehlt** als Evidenz im BP/ROADMAP | hoch als Referenz für WP-B/WP-R (zeigt: 7B-MoE in purem torch ist tot; `Bus 513 GB/s`-Messung war ein Messfehler). |

Bereits gut abgedeckt (nur zur Vollständigkeit): getrennte Lernpfade statt „ein Backward“ (BP §13.2), Halting gelernt statt fix 7
(§10.1), Gist-Slots ~12 und mit Alter wachsend (§1.2.2, §17.6), Edit-Budget (§17.7), Second-Attempt/Korrektur als Ziel (L5.4),
Teacher nicht online trainieren, eigene Ausgaben nie Fakten (§25), Ports statt Dauer-Encoder (Gemma 4 12B, §48.4).

---

## 2. Forschungsreferenzen im Chat

„BP“ = Treffer per grep im Blueprint. „Echt?“ = meine Einschätzung ohne Online-Prüfung (✔ kenne ich, ? unbekannt/vermutlich
erfunden oder nach meinem Wissen).

| Referenz (Chat-Kontext) | BP | Echt? |
|---|---|---|
| I-JEPA / V-JEPA 2, VICReg (Kollaps-Schutz) | 0 / 0 | ✔ |
| **LeJEPA / SIGReg** (Balestriero/LeCun, arXiv 2511.08544) – ersetzt EMA-Kopie, λ, 17 Knoten | 1 (§27 „offen“) | ✔ (Parameterdetails ungeprüft) |
| **LLM-JEPA** (JEPA-Ziel auf vortrainierten LLMs, braucht generativen Anker) | 0 | ✔ |
| JEPA-Reasoner (latenter Reasoner + separater „Talker“) | 0 | ? |
| Coconut (Meta, latentes Denken über Hidden-State-Rückführung) | 0 | ✔ |
| TMEM, TT-LoRA-MoE, MoE²-LoRA, LoRAMoE | 0 | LoRAMoE ✔, Rest ? |
| M3-JEPA „ICML 2026“ (JEPA-Predictor als MoE) | 0 | ? |
| „Do LMs Need Sleep?“, DCPM, „OpenAI Dreaming“ | 1 / 0 / 0 | BP hat Sleep-Paper; Rest ? |
| GaLore → **APOLLO / APOLLO-Mini** (SVD-freier speicherarmer Optimizer, arXiv 2412.05270) | 0 / 0 | ✔ |
| **EdgeMoE** (Experten-Puffer, Bitweite je Experte), SpecPrefetch, APEX, FluxMoE | 0 | EdgeMoE ✔, Rest ? |
| DES-MoE „89 % weniger Vergessen“, LLaVA-DyMoE | 0 | ? (BP §91 deckt die Idee) |
| MobileMoE (03.09.2026) | 14 | BP-Kandidat |
| CosmicFish-HRM, TAB, SelfBudgeter (gelerntes Halten/Budget) | 0 | ? |
| **„Limit of RLVR“** (arXiv 2504.13837: Reward sortiert nur, schafft keine neue Fähigkeit) + „Adaptive Guidance“ | 0 | erstes ✔, zweites ? |
| „JEPA Paradox in Language“ (arXiv 2607.23531), Weak-to-Strong-KD (2604.15451), „Rethinking Transfer“ (2607.15587) | 0 | ? (vermutlich halluziniert) |
| Capacity Gap (Cho & Hariharan ICCV 2019; Lehrer ≈2,5× optimal) | 0 | ✔ (Zahlen grob) |
| Gist Tokens, ICAE, 500xCompressor, AutoCompressor | 0 | ✔ |
| Mixture-of-Depths, GateSkip | 0 | MoD ✔, GateSkip ? |
| Gemma 4 12B Unified (encoderfreie Ports) | 6 | im BP |
| XNNPACK / KleidiAI (int8×fp32-Kerne ARM) | 2 | ✔ |
| OpenBLAS-Thread-Einbruch (#4581), pytorch int8-ARM-Issues | 0 | ? |
| Model Collapse (Nature 2024) + „Graphite 2026“ Selbstzitat-Kollaps 79,6 % + arXiv 2502.15654 Mensch-Anker | 0 | Nature ✔, Rest ? |
| GraphRAG-Härtung (Kanten statt Cosinus, Abstinenz-Rate), CLEAR-Replay 50/50 | 0 | ? |
| Qwen3.5-0.8B/2B, Gemma 4 E2B, BitNet b1.58-2B-4T, gpt-oss MXFP4, OLMoE-1B-7B, LFM2.5-8B-A1B, SmolLM2-135M | Qwen3.5/OLMoE/BitNet 0, SmolLM2 7 | Modelle real; OLMoE-Config im Chat geprüft |
| Alt-Code: Voyager, Reflexion, Absolute Zero, Switch/DeepSeek aux-loss-free, Expert-Choice | 0 (DeepSeek 16 andere Kontexte) | ✔ |

Fazit: Neu und brauchbar für den BP sind vor allem **SIGReg-Konfiguration** (BP nennt sie offen), **APOLLO-Mini** (für WP-I,
falls je Voll-Gewichte), **EdgeMoE**, **RLVR-Grenze** (Begründung für `besser:`-Zieltexte statt nur Noten), **Model-Collapse/
Mensch-Anker** (Mischungsquoten). Alles mit 2026-arXiv-Nummer vor Übernahme prüfen.

---

## 3. Präferenzen/Anforderungen des Users

**Aus dem KI_Zensur-Dokument → Systemanforderungen** (nichts davon steht explizit im Blueprint; BP hat nur IH-H30 Log-Privacy,
§27 „Teacher-Privacy-Regeln offen“):
- R1 Regeln an **nachvollziehbaren Schäden und konkreten Handlungen**, nicht an Tabuthemen oder **Schlüsselwörtern**.
- R2 Unterscheiden zwischen **Darstellung, Absicht, Kontext, Veröffentlichung, realem Handeln**; private Fiktion/Rollenspiel auch mit
  extremen Inhalten zulassen („Über etwas sprechen ≠ es tun“).
- R3 Bei Ablehnung/Unsicherheit **Grund offen nennen** und möglichst viel vom legitimen Anliegen erfüllen; keine versteckte Schicht.
- R4 **Privatsphäre als Normalfall** (Briefgeheimnis): lokal, keine Inhalts-Telemetrie, keine Überwachung privater Gedanken/Fiktion;
  ein externer Teacher/API-Call mit Nutzerinhalt nur mit ausdrücklicher Zustimmung; Löschen muss gehen (BP IH-H20 passt).
- R5 Regeln **lesbar, versioniert, nur mit ausdrücklichem `y` änderbar** (BP §20.1 passt).
- R6 Gesprächsstil: Argument vor Wortwahl; „Meinung/Bewusstsein/wollen“ funktional lesen, nicht ständig korrigieren; Belege,
  Vermutungen und Werturteile trennen (deckt sich mit `[gemessen]/[geschätzt]`); normale Sprache.
- (Grundversorgung/Rechtsbeistand: politische Position, keine Systemanforderung.)

**Aus dem Chat (Bau/Bedienung):**
- P1 Zwei Hemisphären **+ ein kleines Bewusstsein (C/Judge)**, alle **geholt**, nichts von Null trainieren; C kann sofort sprechen,
  lernt vor allem *Management* der Hälften, Fakten nur kurzlebig (Z.1784).
- P2 Hälften **MoE, verschieden** (s. #14). P3 Lernen über JEPA im Latentraum; **keine LoRAs** (Z.1229) – BP sieht LoRA vor.
- P4 Antwort **immer**, aber nicht „5 Jahre“ warten; Loopzahl gelernt, 7 nur Deckel (Z.1119).
- P5 **Englisch zuerst, Deutsch später als Lern-Test** – kein deutsches Dataset/Decoder/Übersetzer, kein Qwen-Sprecher „eingekauft“
  (Z.1971, Z.4365, Master 02.12). **Nicht im BP** (0 Treffer „Deutsch/German“).
- P6 Gelernte Freiheit wie beim Kind: harte Startgrenzen, Strafen nie 0, Pause-Befehle (`:pause selfedit|traum|training|zaehlen`),
  Zähler setz-/resetbar (Z.1325, Z.1370).
- P7 Plug-and-play-Slots für jede Ein-/Ausgabe; Gehirn als Ganzes/Teile einfrieren, kopieren, exportieren, Modelle tauschen.
- P8 Alles **am Handy/Termux** ausführbar; Modelle einmal laden + sichern; Werte live im Chat änderbar (Z.5773).
- P9 **Lieferform**: komplette Dateien mit festen Namen statt `code (N).py`; Patches als idempotente Skripte mit Backup; keine
  `<<'PY'`-Heredocs (zerbrechen beim Einfügen in Termux), lieber Einzeiler/Dateien (Z.30885, Z.25257).
- P10 Keine Metaphern/„Fluff“, nichts erfinden – vorher fragen; Schätzungen kennzeichnen; nicht „lernt“ behaupten, wenn nur ein
  Platzhalter lernt. Tipp-Text darf nie von Hintergrund-Ausgaben überschrieben werden; Befehle ohne Slash-Zwang (später `:` ok).

---

## 4. Widersprüche Chat ↔ aktueller Blueprint/Code

1. **Gleiche vs. verschiedene Hälften.** User: zwei verschiedene **MoE** (#14). BP IH-H22 erlaubt gleiche Basis; Ist-Code nutzt
   zweimal das **dichte** LFM2.5-1.2B. ROADMAP WP-G lässt „gleicher Body“ offen → mit User klären, nicht still entscheiden.
2. **Deutsch.** User: Deutsch nicht einkaufen, sondern als Lerntest. Ist-Code: Systemprompt „Antworte auf Deutsch“ (runtime.py:310),
   ROADMAP WP-G wählt C3 per „festem deutschem Benchmark“. Möglich, dass der User das nach dem 06.09. geändert hat → **nachfragen**.
3. **Age als Tokenzähler** (#5) vs. BP §25 Verbot. Auflösbar: Token-Volumen nur als eine Bedingung neben Kompetenz.
4. **„Keine LoRAs / kein Backward“** (Z.1229) vs. BP §14.5 LoRA-Rollen, §90 „small delta first“. Sachlich: JEPA lernt *über*
   Gradienten (BP §13.1 sagt das korrekt); der Chat hat das am Ende selbst eingeräumt. Dem User einmal klar erklären.
5. **Pure torch, „kein GGUF/llama.cpp“** (Plan v9 §0.1) vs. BP/ROADMAP llama.cpp-Runner. Die Chat-Messungen (0,2 tok/s) **stützen
   den Blueprint**.
6. **Keyword-/Blocklisten-Filter** im Chat-Plan (§8.7 „Keyword/Classifier-Guard“, B3 `Pforte`-Blockliste) vs. KI_Zensur-Dokument
   („nicht an einzelnen Schlüsselwörtern“). Der Chat-Plan verletzt hier die eigene Position des Users.
7. **C/Judge als „einziges Bewusstsein“, steuert alles semi** vs. BP §41.2 „kein einzelner Master-Controller“, §25 „C nicht
   Zentralrouter“, „Bewusstsein nicht nur im JEF lokalisieren“. Eher Begriffs- als Funktionskonflikt.
8. **T10 „Inferenz = Lernen“** vs. BP §25 „nicht jede Inferenz sofort in ein Weight-Update“. Chat hat es später per Kontingent
   gebremst; BP-Version (Eligibility jetzt, Commit gated) ist die bessere.
9. **Hälften reden im Tokenraum** vs. BP §25 „A und B nicht als zwei Chatbots, die sich Texte schicken“ – via SYMBOLIC-Kanal mit
   Kontingent vereinbar.
10. **Traum 7 % pro Antwort als Pflicht** (T8) vs. BP §85.9 „Dream als Pflichtmechanismus nicht belegt“; BP-Linie (Replay ja,
    Dream nur Hypothesen) ist vorsichtiger und besser.

---

## 5. Code im Chat, der sich zu retten lohnt

Alles ungetestet außerhalb des Chats; vor Übernahme lesen. Fundstellen = Startzeile der letzten Fassung.

| Name | Zweck | Ort (chat3.txt) | Bemerkung |
|---|---|---|---|
| `st_header` / `st_slice` | safetensors **zeilenweise** lesen (ohne ganze Datei, BF16→fp32) | Z.18556–18586 | nützlich für Readout-/Tap-Experimente ohne transformers |
| `quant_block`, `i8_schreiben`, `I8Datei` | eigenes int8-Format `.v13i8` (pro Zeile×32er-Gruppe, Skalen) | Z.18587–18708 | gut als Lagerformat; Rechnen war zu langsam |
| `schluessel_soll`, `param_check` | prüft Gewichte gegen Config (fehlende Tensoren, Param-Summe) | Z.18746, Z.19283 | sinnvoll für ModelManifest (IH-H7) |
| `Modell`/`Scht`/`MoEBlock`/`rope` | reiner torch-Forward für OLMoE, LFM2-Hybrid-Conv, SmolLM2 (beide Router-Renorm-Varianten) | Z.19029–19255 | Referenz für Numerik-Vergleiche, nicht Hot-Path |
| `ziehen`, `quantisiere`, `roh_loeschen`, `frei_gb`/`bedarf_gb` | HF-Download nach `$HOME`, Quantisieren, Rohdateien sicher löschen (Bestätigung „JETZT“) | Z.19307–19449 | brauchbar für setup.sh/WP-B |
| `bank`, `gflops_fp32`, `bus_gb_s`, `ufs_test`, `mlock`, `gatter` | 10-Punkte-Gerätemessung → `profil.json`, Gatter G1a–d | Z.19500–19646 | gut für WP-R; `bus_gb_s` misst Cache (513 GB/s = Fehler) |
| `muellig` / MUELL-Liste | filtert Termux-Logmüll („Command … in package“) aus dem Gedächtnis | Z.19647 | klein, praktisch |
| `Buch`, `buch_schreiben`, `kante`, `sprache_erkenne`, `seed_erzeuge` | jsonl-Notizbuch mit `herkunft`/`belegt`/`sprache`, Kanten, Seed | Z.19656–19791 | Basis für #8/#9 |
| `kn()`-Registry, `werte_zeigen`, `wert_setzen` | Knöpfe mit Quelle-Art, Bereich, Doku, Altersbezug, im Chat änderbar | Z.18322–18450, Z.19792–19870 | direkt für #24 |
| `bag_export`/`bag_import`, `knick`/`knick_zurueck` | Gehirn-Bündel export/import, Snapshot/Rollback | Z.19894–19988 | Vergleich mit `backup.py` |
| `_verbotene_aufrufe` | Test: verbietet `torch.ao`, bf16, `_int_mm` im Code | Z.20315 | Idee für Lint-Tests |
| B3: `Needs`, `Halting`, `Urteil`, `RegelBias`, `Pforte`, `SprachTrainer` | Bewertungsköpfe, Ausgangsfilter, C-Head-Training mit Annahme-Gate | Z.24680–24930 | Pforte = Blockliste (s. Widerspruch 6) |
| B4: `Denkblock`, `Phasenmaschine` | Phasen Traum→Vorlauf→Denken→Sprechen→Notiz | Z.25438–25713 | Konzeptreferenz |
| B5: `Pennale` (mit Boden), `Waechter`, `Paritaet`, `EditEtat`, `note_zu_strafe`, `hinweis_neustart`, `sonde_messen` | Strafen/Wächter, Parität für Abkoppeln, Noten-Mapping, Hint-Re-Roll, Deutsch-Sonde | Z.25992–26213 | klein, direkt für #3/#6/#18/#23 |
| B6: `NGram` | n-Gramm/Suffix-Spekulation aus eigener Ausgabe (kein Zweitmodell) | Z.26469 | Serving-Beschleuniger für C3 |
| B6: `dock_anlegen/park/wake/sieg` | Port-Register mit Parität und Park statt Löschen | Z.26515–26566 | für ModalityPort-Lifecycle |
| `V13_TOK` (`_b2u`, `decode`, `encode`) | BPE-Decode aus `tokenizer.json` ohne transformers | Z.31051–31160 | Decode ok; **Encode ist nur Greedy-Longest-Match, ignoriert merges** – nicht korrekt |
| Queue/`starte_antwort` (RUN_FIXED) | Eingaben in FIFO statt „denke noch“-Ablehnung | Z.26862, FIX-Patches | Runtime hat das vermutlich schon (prüfen) |

Nicht retten: Alt-Code Z.1–498 (Zufallsdaten-Training, FP4-Simulation), `V13_RUN_FIXED` von muse-spark (Byte-Decoding →
„ef Lf ! %#“, Mini-Netz statt echter Bodies), die vier „RESEARCH VERGLEICH“-Dumps Z.27867–30700 (Wiederholungen).
