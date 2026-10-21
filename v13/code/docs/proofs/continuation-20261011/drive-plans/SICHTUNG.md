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
