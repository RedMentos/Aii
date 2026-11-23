# V13: Altcode-Review (Stand 09.10.2026)

Grundlage: Quellen nur gelesen, nichts davon ausgeführt. `$S` = Scratch-Verzeichnis, `CUR` = `/mnt/project-files/v13/code`.
Mit „fehlt im aktuellen Code“ ist gemeint: per grep über `CUR/v13/*.py` geprüft (Begriffe wie moe/expert, hemisph,
cautious, kappa/inquisition, stream_a, lora, vicreg, kl/opd, merge, ternary). Treffer, die nur aus Doku-Strings oder
Teilwörtern stammen, wurden einzeln angesehen und verworfen.

## 0. Kurzfazit

- Die Standalone-Prototypen (v1.1, Hemisphere, TRUE_v2, Combined v3, inquisition_rsi, code (23–30)) sind **PyTorch/HF-Skizzen**.
  Ihre Audits melden oft „PASS“ für Mechanismen, die im Code nicht greifen. Ein ganzes Modul davon lohnt sich nicht zu übernehmen.
  Brauchbar sind nur einzelne Funktionen als Referenz.
- Der aktuelle Code (numpy + gepinntes llama.cpp, 10 externe Lernpfade, Proof-Lifecycle) ist ein anderes Programm.
  Er ist deutlich ehrlicher und solider, setzt aber MoE, Hemisphären-Module, P1/P2-Inquisition, Stream A, LoRA und Teacher-KL **nicht** um.
- **Wichtigster Befund:** Arbeit aus burst3, burst4 und burst5 (06.10.) ist **still verloren gegangen**: `body_training.py`,
  `native_capability_profile`, der Fix für die Executive-Task-Aktualisierung und der STEP2-`task_score`. Nirgends steht dazu ein Vermerk.
  Der Executive-Fix ist dadurch wieder ein **Regressionsfehler** im aktuellen Code (siehe §4).

## 1. Alte Codelinien

### 1.1 V13_v10 (`$S/pv/V13_v10/V13_v10/starter/`, ca. 830 Zeilen, Stand 14.09.)
- Inhalt: Datenverträge (`contracts.py`) und ein SQLite-Snapshot-Repository mit CAS-Commit (`expected_snapshot_id`),
  Validierung, Rollback und Cache-Invalidierung (`storage.py`). Dazu kommen kurzlebige **Eligibility-Traces** mit TTL und Bindung an
  experience_id/model_version/snapshot_id, linear zerfallend und beim Neustart nicht persistiert (`eligibility.py`).
  Weiter ein kooperativer **Inference-vor-Training-Coordinator** an Slice-Grenzen (`scheduler.py`), eine feste Age-0-Policy (`policy.py`)
  und eine Admissions-Checkliste für Body-Modelle (`backends.py`: Gist≠Detail-Familie, echtes MoE, Hooks, Evidenz-Refs).
  Getestet wird mit `tests/test_invariants.py` (20 Tests). `STATUS.md` sagt ehrlich: „kein JEPA, kein neuronales Lernen“.
- Urteil: **gut**: klein, sauber, ehrlich, und die Invarianten sind getestet. Es ist ein konzeptioneller Vorläufer der aktuellen Linie.
- Im aktuellen Code fehlt davon: die TTL- und versionsgebundene Trace-Semantik. Aktuell ist `eligibility` nur ein konstanter
  `eligibility_decay`-Wert in `LearningTrace`-Paketen plus ein Aktivitäts-EMA in `learning_worker.py`.
  Ebenfalls fehlen die Admissions-Prüfung für Modellpaare und der explizite Coordinator.
  Für Letzteres gibt es einen Teilersatz: `runtime.py:60` setzt `cancel_event` für Hintergrundjobs.

### 1.2 V13_Termux_v11 (`$S/pv/V13_Termux_v11/V13_Termux_v11/v13term/`, ca. 1.600 Zeilen, 15.09.)
- Inhalt: Ein-Modell-Chat (`qwen35` = Qwen3.5-0.8B-GGUF) über `llama-server`, dazu eine prompt_toolkit-TUI, ein HTTP-Dienst mit
  Owner-Token, Modell-Download mit Hash-Prüfung, Backup/Restore und **Regelvorschläge des Modells mit Digest, Stale-Check und
  Owner-Freigabe** (`store.py: propose_rule/decide_request`). Die README sagt ehrlich: keine Hemisphären, kein JEPA.
- Urteil: **solide App-Schale**, ohne Architekturanteil. Ein Linux-Live-Lauf ist belegt (`LIVE_MODEL_RESULT.json`).
- Im aktuellen Code fehlen: die Vorschlags- und Freigabe-Pipeline für Modell-Regeländerungen (`age.py` kennt die Fähigkeit
  `propose_config_changes` erst ab Stufe 4, aber nicht ihren Mechanismus), die TUI und der HTTP-Dienst. Die beiden Letzteren sind unkritisch.

### 1.3 V13_Brain_complete_v1.1 (`v13_brain.py`, 1.331 Zeilen)
- Inhalt: ein eigenes Byte-LM mit zwei Hemisphären pro Layer (je eigenes **SparseMoE**, 8 Experten, Top-2, Capacity,
  Balance-Loss, z-Loss), `SemiPermeableBridge` und `CautiousnessGate` (0,05–0,25). Weiter `SharedP12` (P1/P2 über gemeinsame
  Gewichte, N Runden, κ = cos), Stream A (latente Slots), Stream B (SQLite) und Replay. Dazu kommen `TernaryLinear` (BitNet-artig, STE)
  und `LoRALinear.merge_slow(β)`, das β·Delta in die Basis schiebt und A/B mit √(1−β) skaliert. Die Gesamtwirkung bleibt dabei erhalten, das ist korrekt.
- Fehler: (a) **Zukunftsleck**: `world` wird über alle Sequenzpositionen gemittelt und auf jede Position addiert
  (`V13Model.forward`, `h=z+inq.unsqueeze(1)`). Das kausale LM sieht damit beim Training die Zukunft.
  (b) Das „JEPA“ besteht nur aus `smooth_l1(mean(z[:-1]), mean(z[1:]))`, ohne Predictor und ohne EMA-Target.
  (c) Bei schlechtem Feedback wird trotzdem auf die schlechte Antwort trainiert (Gewicht 0,05).
  (d) Ein untrainiertes Byte-LM liefert keine Sprache. Das Audit gibt das selbst zu.
- Urteil: **didaktisch, nicht verwendbar**.
- Im aktuellen Code fehlt alles davon: MoE, Hemisphären, Bridge, Cautiousness, P1/P2, Stream A, LoRA, Ternary und Merge.

### 1.4 V13_Hemisphere_Brain_Prototype (`v13_hemisphere.py`, 1.246 Zeilen)
- Inhalt: Qwen2.5-0.5B als „Sprachanker“, darauf zwei MoE-Hemisphären, Bridge, Cautiousness und `InquisitionCore`.
- Fehler: (a) Das Inquisition-Ergebnis `condition` geht **nie** in die Generierung ein, die Antwort kommt aus einem reinen Prompt.
  (b) Hemisphären, Bridge, Anchor und Fusion stehen **in keinem Optimizer** und bleiben für immer zufällig.
  (c) `consolidate()` rechnet `p ← (1−β)p + βp`, also gar nichts (das „p←p“-Problem, das v3 selbst benennt).
  (d) Es gibt kein LoRA: jedes Feedback löst ein **Voll-Finetuning** des 0,5B-LMs aus, was auf dem Handy nicht machbar ist und vergisst.
- Urteil: **Fassade**. Nichts übernehmen.

### 1.5 V13_TRUE_ARCHITECTURE_v2 (`v13_true.py`, 805 Zeilen)
- Inhalt: A = OLMoE-1B-7B (natives 64/Top-8), B = SmolLM2-135M, ein `SparseModelScheduler`, Bridge, `Cautiousness`
  (mit memory_conf/recent_error/novelty), adaptive Rundenzahl über die Schwellwerte caution/disagreement, eine
  `ContextPolicy` (native/protected/mixed), Stream A/B und Replay.
- Fehler: `z2` (das Inquisition-Ergebnis) wird verworfen. Der Scheduler-Index wird nie benutzt, beide Bodies laufen immer.
  Der Controller bekommt **keinen Gradienten**, weil `_world` unter no_grad läuft und der LM-Loss den Controller nicht berührt.
  `best_snapshot` wird nirgends verwendet. OLMoE-7B-total ist auf 6 GB RAM mit transformers/Termux unrealistisch.
- Urteil: **Fassade**. Die einzige Idee mit Wert ist die heuristische Rundenwahl nach Unsicherheit. Die ist in
  `effort.py` inzwischen besser gelöst.

### 1.6 V13_Combined_v3_FINAL (`v13_combined.py`, 2.184 Zeilen)
- Inhalt: Default-Body Qwen3.5-35B-A3B (für 6 GB **nicht ladbar**), `MetaRouter` (A/B/both, Runden, Kontext-Tier; die
  Rundenwahl wird bewusst überschrieben), `SharedP12`, `JEPAPredictor` (4 Transformer-Blöcke), `vicreg_loss`, Urteil-, Zeit- und
  Fähigkeits-Heads, PhaseMask/Pennale/Guardian/Parity/EditBudget (Ideen aus B4/B5), KV-Codecs (FP8/Int8-Stubs), Residency, Docks und NGram.
- Fehler: (a) `learn_from_experience` verwendet die **undefinierte Variable `target`** (Z. ~1864). Der `NameError` wird vom
  `try/except` geschluckt, das LoRA-SFT läuft also **nie**. (b) `JEPAPredictor` und `vicreg_loss` werden in keinem Loss benutzt.
  Zeit- und Fähigkeits-Head sind ungenutzt. (c) `_local_loss` trainiert den Urteil-Head auf `hash(user)%10000` als konstantem
  Vektor, also auf Rauschen. (d) P2 = −P1(shared) ist degeneriert. (e) `condition` geht nicht in die Generierung ein.
  Das `IMPLEMENTATION_AUDIT_v3.md` meldet trotzdem „continuous local learning PASS“.
- Urteil: **Fassade mit schönen Namen**. Brauchbar sind nur `vicreg_loss` als Referenz und die Lernregel „Selbstantwort ≠ Wahrheit“
  (gewichtet nach Herkunft). Letztere ist im aktuellen Code längst strenger umgesetzt.

### 1.7 inquisition_rsi_prototype (`inquisition_rsi.py`, 1.025 Zeilen)
- Inhalt: Qwen2.5-0.5B + PEFT-LoRA, Stream A/B, `InquisitionSpace` und eine C0–C3-Route **nach Wortanzahl**.
  Online-LoRA-SFT bei Feedback und `opd_step`: Reverse-KL Student‖Teacher über die Top-k-Tokens des Studenten plus einen Overflow-Bin.
- Fehler: P1/P2 sind **zwei getrennte Linear-Schichten**, obwohl die README „derselbe LoRA-Adapter“ sagt. Das Latent beeinflusst die
  Antwort nur über `kappa<0` → ein Satz im Prompt. `opd_step` läuft unter `@torch.no_grad`, misst also nur und **trainiert nicht**.
  Der Default-Teacher ist dasselbe Modell wie der Student. In die Trainingsdaten wird der Text „QualityScore: x“ geschrieben.
  Schlechte Antworten werden mit Gewicht 0,25 eintrainiert.
- Urteil: **schwach**. Die KL-Funktion mit Top-k und Overflow-Bin ist als Messbaustein brauchbar, siehe §2.

### 1.8 `$S/x/03_WORK_STATUS/code (23)…(30).py`
- (23) B5 Zeithead/Pennale, (24) B6 Bremse/NGram/Docks/Merge, (25) Verdrahtung B1+B4-REPL. Diese hängen von `V13_B1..B4` ab,
  die **nicht vorliegen** und daher nicht lauffähig sind.
- (26) = (26)(1), byte-identisch: `V13_RUN_FIXED.py`. Das ist der **einzige echte JEPA-Ansatz** unter den Prototypen: maskierte Blöcke
  (`make_masks`), Kontext-Encoder mit **EMA-Target-Encoder** (`ema_update`, 0,996), Predictor, VICReg, MoE mit Load-Balance, ein
  Rollback auf den besten Checkpoint und eine Dead-Expert-Erkennung.
  Fehler: `inv,var,cov = vicreg_loss(...)` erwartet 3 Rückgabewerte, die Funktion liefert aber 4. Das wird durch den Patch (27)
  behoben. `decode_ids` liefert bei leerer Ausgabe den Füllsatz „verstanden, erzaehl mehr dazu“, also eine **Fake-Antwort**.
  Der Byte-Decoder hat keine Sprachqualität.
- (27), (29) und (30) sind Text-Patches auf (26). (28) ist ein reiner Python-BPE-Codec für SmolLM2/OLMoE.
- Urteil: (26) taugt als Referenz für eine maskierte JEPA mit EMA. Der Rest ist Bastelstand ohne eigenen Wert.

### 1.9 Frühe aktuelle Linie (V13-Phone-Source…auto5, Redmi-Start run3/burst2, Redmi-Install*)
- Jede Funktion (`def`), die es dort gab, existiert auch im aktuellen Code (Abgleich der Funktionsnamen). Hier ist also nichts verloren gegangen.
- Ausnahme ist der Zweig **burst3 → burst5** (06.10.), siehe §2 und §4. Das neueste `V13-Redmi-Start` hat zusätzlich nur
  Proof-Skripte unter `docs/` (`check_resume_acceptance.py`, `docs/proofs/*.py`). Gegenüber CUR fehlen ihm `age.py`, `effort.py`,
  `cloud_bench.sh` und `test_sqlite_close_audit.py`. CUR ist damit neuer.

## 2. Was sich als Referenz zu übernehmen lohnt (Ziel: `/mnt/project-files/v13/salvage/<name>/`)

Priorität A heißt: wiederherstellen, also zurück in den Runtime-Code. Priorität B heißt: nur als Referenz ablegen.

| Prio | Quelle (exakt) | Ziel | Grund |
|---|---|---|---|
| A | `$S/pv/V13-Redmi-Start-20261006-burst5/V13-Phone/v13/body_training.py`, `.../tests/test_body_training_port.py`, `.../docs/proofs/native-body-train-port-contract-20261006.md` | `salvage/body_train_port/` | Fail-closed-Vertrag für einen nativen B1/B2-Train-Port: Hashes, getrennter FP-Master, Requantizer, Parameter-IDs, update_authority = 0. Das ist genau das Tor, das WP-I/WP-S6 (TRAIN_RUNNER_PROOF) braucht. 49 + 42 Zeilen, ohne Abhängigkeiten außer `common.file_hash`. |
| A | `.../burst5/V13-Phone/v13/verification.py` Z. 33–50 (`native_capability_profile`) und die Aufrufe in `.../v13/operator.py` Z. 176–177 und `.../v13/world.py` Z. 136 | `salvage/native_capability_profile/` | Ein konservatives, gemeinsames Fähigkeitsprofil für `:self`, `:doctor` und `:world`. Aktuell steht in `world.py` `'body_training':False` hart verdrahtet. |
| A | `.../burst5/V13-Phone/v13/executive.py` Z. 78–83 und der Test `test_implicit_task_tracks_current_turn_but_explicit_task_persists` in `.../tests/test_executive.py`, Beleg `$S/x/03_WORK_STATUS/executive-implicit-task-refresh-20261006.json` | `salvage/executive_implicit_task/` | Behebt das Problem, dass alter Nutzertext dauerhaft in den nativen Kontext gelangt. Im aktuellen Code ist dieser Fix verloren (§4). |
| A | `.../burst5/V13-Phone/scripts/analyze_step2_proof.py` (`task_score`, plus der Test `test_task_bound_score_is_reported_without_gate_promotion` in `.../tests/test_step2_analysis.py`) | `salvage/step2_task_score/` | Eine an die Aufgabe gebundene STEP2-Bewertung statt der bloßen Zahlenpräsenz. Wichtig für WP-G (STEP2-Nutzen neu messen). |
| B | `$S/pv/V13_v10/V13_v10/starter/v13/{eligibility.py,scheduler.py,storage.py,backends.py,policy.py,contracts.py}` + `starter/tests/test_invariants.py` + `starter/STATUS.md` | `salvage/v10_starter/` | Referenz für die F6-Eligibility mit TTL und Versionsbindung, für den Vorrang von Inferenz vor Training und für die Admissions-Checkliste von Modellpaaren (wichtig für WP-G/S1: Gist und Detail sollen verschiedene Familien sein). |
| B | `$S/x/03_WORK_STATUS/code (26).py` (nur `ema_update`, `vicreg_loss`, `make_masks`, `TinyEncoder/TinyPredictor`, `Brain.forward_once/train_step`) + `code (27).py` | `salvage/ijepa_torch_ref/` | Referenz für WP-S4: maskiertes JEPA, EMA-Target und VICReg mit **Kovarianzterm**. Der aktuelle `predictor_worker.py` hat nur Varianzboden und Anker, keinen Kovarianzterm. Achtung: Das ist torch, die aktuelle Runtime ist numpy. Es dient nur als Vorlage. |
| B | `$S/pv/inquisition_rsi_prototype/inquisition_rsi/inquisition_rsi.py` Z. 685–760 (`opd_step`) | `salvage/kl_topk_overflow/` | Passt direkt zu WP-S5 (Drift-Gate KL(neu‖Basis) auf einer festen Probe-Menge). Weil `llama-server` nur Top-n-Logprobs liefert, ist „Top-k + Overflow-Bin“ genau die passende Näherung. Neu umsetzen ohne torch. |
| B | `$S/pv/V13_Brain_complete_v1.1/v13_brain.py` Z. 176–235 (`TernaryLinear`, `LoRALinear.merge_slow`) und Z. 252–330 (`SparseMoE` mit Capacity/Balance/z-Loss) | `salvage/lora_slow_merge_moe_ref/` | Für WP-I/S6: eine korrekte langsame Adapter→Basis-Konsolidierung (die Gesamtwirkung bleibt erhalten). MoE-Losses nur, falls später doch ein MoE-Body kommt. Das Zukunftsleck der Datei gehört **nicht** dazu. |
| B | `$S/pv/V13_Termux_v11/V13_Termux_v11/v13term/store.py` Z. 41–100, 251–300 (`_validate`, `_digest`, `propose_rule`, `decide_request`) | `salvage/rule_proposals/` | Vorlage für die Age-Fähigkeit `propose_config_changes`: Digest, Stale-Erkennung über `rule_version`, nur der Owner entscheidet. |

**Nicht übernehmen:** Hemisphere, TRUE_v2 und v3 als Ganzes; code (23)–(25), (28)–(30); alle KV-Codec-, Docks- und Residency-Stubs.
Sie fügen nichts Belastbares hinzu, und mehrere ihrer Audits sind irreführend.

### body_training.py: warum es verschwand und ob es zurück soll
- Burst5 (`BUILD_STATE-20261006-burst5.json`, `completed_this_run`): „Added fail-closed native B1/B2 body train-port binding
  contract … 248/248 unit tests PASS“, Proof `docs/proofs/native-body-train-port-contract-20261006.md`. Der Vertrag war in
  `verification.native_capability_profile` eingebunden.
- Im neuesten Stand (`V13-Redmi-Start`, `Redmi-Install-20261009-0819`, CUR) fehlen die Datei, der Test, der Proof und die Funktion.
  `BUILD_STATE.json` und `completion-ledger.json` erwähnen `train_port_contract`, `capability_profile` und `implicit` **null Mal**.
  `RECOVERY_20261007.md` und die `recovery_*`-Blöcke nennen nur andere verlorene Arbeit.
- Ursache, aus den Daten erschlossen: Alle Stände gehen von `base_checkpoint = V13-Redmi-Start-auto-burst2.zip` aus. Der burst3–5-Zweig
  vom 06.10. wurde bei den Wiederherstellungen am 07.–09.10. (ZIP33/38/40/47/60) offenbar nicht übernommen. Es war also eine **unbemerkte
  Verlust-Regression, keine bewusste Entfernung**. `docs/NATIVE_TRAIN_PORT_NEXT_20261008.md` plant den TrainRunnerProof neu, ohne
  auf das vorhandene Modul zu verweisen.
- Empfehlung: **wiederherstellen**, zuerst nach `salvage/`, dann zurück nach `v13/` mit Test. Es ist klein, gibt keine Rechte frei
  und passt zur Roadmap (WP-I/S6). Ein Konflikt ist zu beachten: `:capability` belegt jetzt `age.py` (Stufen absenken). Das Profil
  sollte deshalb unter `:doctor`/`:self` oder einem neuen Befehl `:native` erscheinen. Die Schemas `native-body-train-port.json`
  und `TrainRunnerProof` (Ledger) sollten mit dem Konzept in `NATIVE_TRAIN_PORT_NEXT` abgeglichen werden. Dort ist der Slice
  `token_embd_norm` FP32, ein Requantizer ist also „NOT_APPLICABLE“. Der Vertrag verlangt aber zwingend einen Requantizer und muss dafür eine Ausnahme bekommen.

## 3. Architektur-Paket-Codeaudit (`V13-Architektur-Codeaudit-20261009.md`, Quelle: ZIP-Stand vom 09.10., 00:28)

Kernaussagen und ob sie für CUR noch gelten:

| Aussage | Gilt für CUR? |
|---|---|
| Routen simple/detail/gist/both, PRESSURE → C3-Fallback, C5-Quellenkopie; Bodies seriell, höchstens 1 B1-Re-entry | ja (`runtime.py` Z. 211–293) |
| B1 und B2 sind **dieselbe** LFM2.5-1.2B-Q4_0-Datei, also kein MoE-Paar | ja (`specs/models.json`) |
| Callosum: `latent_authority=0`, `receiver_effect_proven=False` | ja (`cognition.py:163`) |
| 10 externe Lernpfade (route, wake, halt, control_calibration, output_adapter, a3_student, b1/b2_predictor, world_predictor, memory_retrieval) mit Shadow → Prüfung → Freigabe | ja (`operator.py` `:learn`-Liste) |
| Body- und World-Predictor mit Stop-Gradient/EMA-Target; kein „vollständiges JEPA“ | ja (`predictor_worker.py`) |
| Native Experimente (Observer, Pause/Resume, Final-Norm-Receiver, RMSNorm-Parameter, Mid-Layer) nur LAB, Qualitäts-Gates verwerfen die Kandidaten | unverändert, kein neuer Code |
| STEP2 hat 42/70 gültige Zeilen; C3 nutzt den abgerufenen Quellwert nicht korrekt (27/28) | unverändert |
| F8 „nur Age0“, F2 „gelernte Salienz fehlt“ | **teilweise überholt**: `age.py` (Stufenhülle mit Hysterese, `BUILD_CEILING=0`) und `effort.py` (Salienz per Regex-Heuristik, **nicht gelernt**) sind neu |
| 314 Softwaretests (Log vom 08.10.) | überholt: laut ROADMAP 382/398 bzw. 401 |
| Volle JEPA-Architektur, Sparse Experts, Train-Master, Inquisition-Rekursion, gelernte Admission: PLAN | gilt weiter |

Das Audit ist sorgfältig und deckt sich mit dem Code. Es **erwähnt die verlorenen burst3–5-Features nicht**, weil es nur den gesicherten ZIP-Stand kannte.

## 4. Widersprüche zwischen Versionen auf Codeebene

1. **Executive-Regression (Bug):** burst5 `executive.py` übernimmt nur `EXPLICIT_OPERATOR_TASK` dauerhaft. Gewöhnliche Turns
   ersetzen den Task, so belegt in `executive-implicit-task-refresh-20261006.json`, 242/242 PASS. CUR `executive.py:96` hat
   `task=previous.get('active_task') or {...}`. Damit bleibt **die erste Nutzerfrage einer Session für immer `active_task`** und wird
   jedes Mal in die Ref-Liste und den nativen Kontext aufgenommen. Das ist genau der Fehler, den der Fix behoben hatte. Der Test dazu ist ebenfalls weg.
   (Das ist eine statische Analyse, in CUR nicht ausgeführt.)
2. **Stille Löschungen ohne Vermerk:** `body_training.py` + Test + Proof, `native_capability_profile` (burst4/5), `task_score` in
   `analyze_step2_proof.py` (burst3–5) und 8 Testfunktionen. Keiner dieser Punkte steht in BUILD_STATE, im Ledger oder in den RECOVERY-Dokumenten.
3. **`:capability` wurde umgewidmet:** In burst5 gab es das native Fähigkeitsprofil aus, in CUR senkt es Age-Stufen (`operator.py:209`).
   Alte Doku und Proofs, die `:capability` nennen, beschreiben jetzt etwas anderes.
4. **Fähigkeitsbericht:** In burst5 wurde er aus geprüften Port-Deskriptoren abgeleitet, in CUR ist er in `world.py:136` hart
   verdrahtet (`body_training:False`). Das Ergebnis ist gleich, der Prüfpfad aber verloren.
5. **Admissions-Regel gegen den Ist-Stand:** v10 `backends.py` lehnt Gist=Detail (gleiche Familie) und dichte Bodies ab. CUR fährt
   B1=B2=dasselbe dichte LFM2.5-1.2B. Die ROADMAP nennt das offen „Harness-Body“, der Canon-Bruch selbst ist aber nirgends als Ausnahme registriert.
6. **Prototyp-Audits und README gegen den Code:** v3 meldet „continuous local learning PASS“, obwohl das LoRA-SFT wegen
   `NameError` nie läuft und JEPA ungenutzt ist. Die RSI-README sagt „P1/P2 = derselbe LoRA-Adapter“, der Code hat zwei getrennte
   Linear-Schichten. RSI enthält einen OPD-„Teacher-Student-Loop“, der nie trainiert. v1.1 meldet „Fake decoder vermeiden PASS“, und code (26) hat einen Füllsatz-Fallback.
   Die Hemisphere-README nennt eine „langsame EMA-Integration“, die als No-op implementiert ist.
7. **Modellwahl widerspricht der Hardware:** v3 (Qwen3.5-35B-A3B ×2) und TRUE_v2 (OLMoE-1B-7B + SmolLM2 per transformers) passen
   nicht in 6 GB RAM, Termux nicht eingerechnet. Seit v11 und der aktuellen Linie wurde das korrigiert (GGUF Q4, ≤1,2B).
8. **Ungeprüfte Zitate in den Prototyp-Audits:** „NeoHorse-1 arXiv 2609.08183“, „DeepSeek-V4.1-Flash 10.09.2026“ und „Edge0-35B-A3B“
   wurden hier nicht verifiziert. Sie sollten im Blueprint nicht als Beleg dienen, ohne dass das in WP-S8 geprüft wird.
9. **Architekturbegriffe ohne Gegenstück im aktuellen Code:** Hemisphären-MoE, Semi-Bridge, Cautiousness-Gate, P1/P2-Inquisition mit κ,
   Stream A (latente Slots), LoRA/Slow-Merge und Teacher-KL fehlen in CUR vollständig (grep). Sie leben nur im Blueprint und
   in den Prototypen weiter. Wer „V13 = Inquisition-Architektur“ sagt, muss wissen: Die laufende Runtime hat davon heute **keinen**
   dieser Kernmechanismen implementiert, nur die quellengebundene B1/B2/C-Pipeline mit externen Heads.

## 5. Empfohlene nächste Schritte (klein)
1. Die vier A-Punkte aus §2 nach `salvage/` kopieren. Danach Executive-Fix und Test wieder einspielen (betrifft den Besitzer von `executive.py`, WP-D).
2. `body_training.py` und das Fähigkeitsprofil zurückholen, `:native` als Befehl und eine Ledger-Zeile `TRAIN_PORT_CONTRACT` anlegen.
3. In `BUILD_STATE` die Verluste vom 06.10. einmalig nachtragen.
4. Für WP-S4: VICReg-Kovarianz plus Rang-Telemetrie in numpy nach dem Vorbild von code (26). Für WP-S5: KL mit Top-k und Overflow aus RSI.
