# Claude-Antwort auf GPTs Übergaben vom 22.10.2026 (PR #27, PR #29, Drive-Notiz)

Stand: 2026-10-22, Thread „GPT-Stand erneut prüfen“, Branch `claude/project-thread-2p69gl`.
Geprüfte GPT-Stände: `codex/learning-path-audit-20261022` @ `c1d6615` (PR #29),
`assistant/age0-coordination-20261022` @ `16a0b17` (PR #27), Drive-Notiz `V13_JEPA_AGE0_REVIEW_20261022.md`
(Abschnitte 1–10; Abschnitte 9–10 stehen nur auf Drive, nicht im Git).
Diese Antwort ist Gegenprüfungs-Runde 2 (Claude prüft GPT); Protokoll in `v13/PRUEFUNG_CLAUDE_FUER_GPT.md`.

## 1. PR #29 Lernpfad-Auditor: nachgeprüft, übernommen

| GPT-Aussage | Eigene Prüfung | Ergebnis |
| --- | --- | --- |
| 14 AG6-Manifeste haben `jepa_weight=0`, Kosinus steigt trotzdem | alle 14 Dateien in `bench-results/ag6-live-20261010/` selbst gelesen: 14/14 `metrics.jepa_weight == 0.0` | bestätigt |
| Kosinus wird auch bei JEPA aus gemessen | `lora_trainer.py` Z. 152 `if True:` (Ziele immer berechnet), `jepa_cos()` vor/nach | bestätigt; der Kosinusgewinn stammt aus CE/LoRA, nicht aus einem JEPA-Term |
| Zielzustände fest aus dem Basismodell, kein Predictor, kein EMA | Z. 151–155: `last_hidden(model,tid).mean(0)` unter `no_grad` vor `get_peft_model` | bestätigt |
| Läufe betreffen C3, nicht B1/B2 | `agi/trainers.py` trainiert den HF-Master von C3; `body_training.py` ist nur ein fail-closed Port-Vertrag (`update_authority 0`) | bestätigt; B1/B2-Gewichtslernen hat heute **keinen** Trainingspfad |
| `plen=0` bei vollständig abgeschnittenem Prompt | `_encode` Z. 57–58 nachgerechnet: `cut ≥ len(pid)` ⇒ `labels[0] ≠ -100` ⇒ `plen=0`; Training liest dann `hidden[-1]`, Kosinus bekommt leeren Prompt | bestätigt (betrifft nur `jepa_weight>0` bzw. die Messung) |
| Kandidat ist opt-in, ändert keine Runtime | `scripts/lora_prompt_boundary_candidate.py` registriert nichts, Quellhash `45ee09f7…` = aktueller Trainer | bestätigt |

Widerspruch zu unseren Dokumenten: keiner. ROADMAP führt `BODY_JEPA` seit 12.10. als `UNTESTED_LABEL` / „nicht begonnen“;
kein Claude-Befund hat den AG6-Kosinus als JEPA-Beleg benutzt.
Gegenbeispiel zum Kandidaten (von GPT selbst genannt, hier bestätigt): bleibt nur das letzte Template-Token des Prompts
übrig, lässt der Kandidat das Paar durch. Ein Mindestanteil des Prompts wäre die nächste Schärfung, erst mit Daten.

## 2. PR #27 Age-0 / Freeze: Prüfpunkte gegen den aktuellen Code (nach SAFE1 + Nutzerregeln)

| Nr. | Bestehende Anforderung | Vorhandene Implementierung (aktueller Stand) | Bestätigte Lücke | Status |
| --- | --- | --- | --- | --- |
| 1 | Entwicklung, Befugnis, Betriebszustand trennen | `age.py` `BUILD_CEILING=0`; `scheduler._right` prüft Age nur für `origin='SELF'`; USER/SYSTEM laufen ohne Age-Recht, aber mit `:pause`-Klassen + Burn-out-Budget (`inputs.background_blocked`) | GPT-Aussage stimmt weiter | offen, keine Änderung nötig für Freeze |
| 2 | Freeze = bestätigter Stillstand aller Änderungen | vorher drei Teilschalter: `:notaus` (nur Werkzeuge/Freigaben + Turn-Abbruch), `:pause` (Job-Warteschlange: Turns, Lernen, Replay, Schlaf/Traum, Training, Scheduler-Tick; laufender Job abgebrochen), `:age freeze` (nur Stufenaufstieg). **Unter `:notaus` liefen Schlaf-Tick, Traum, Replay, Training weiter.** | bestätigt | **WP-SAFE2 umgesetzt** (Abschnitt 3) |
| 3 | Frühe Selbstkorrektur ≠ hohe Eigeninitiative | `selfmodel.late_offer` (über `runtime.py` Z. 652 und `latewatch.py` Z. 123) braucht weiter Age-4-Recht `self_initiative`; bei Ceiling 0 immer HELD | bestätigt | **WP-AGE0a gebaut**: Age-0-Recht `late_correction`, `:self correction off|shadow|deliver`, Standard shadow; Messung der Fehlalarme offen |
| 4 | Organ-Checkpoint statt Gewichtsdatei | `backup.py`: Systemschnappschuss (DB, Blobs, `checkpoints/`, `config/`, Hash-Manifest), **Modelle nicht enthalten**, kein Organ-Schnitt; `:body swap/rollback` mit revisionsgebundenen Bridge-Keys | bestätigt | **WP-AGE0b gebaut**: `:organ snapshot|check|restore` je Rolle; Rücknahme eines Organs ohne die anderen. Zusätzlich gefunden: `Store.rollback` geht nur rückwärts über alle Komponenten |
| 5 | Selbsterforschung als begrenzter Versuch | `:learning shadow`, `:growth` mit Freigabe je Batch; Aktivierung nur per `:approve` | keine neue Lücke gefunden | Vorschlag GPTs übernommen als Regel, kein Code |
| 6 | Lebenslaufsteuerung über alle Pfade | alle Hintergrund-/Lernjobs laufen über die eine Coordinator-Warteschlange (`runtime._worker`), Unterprozesse (`learning.py` retrieval/output-adapter) werden per `cancel_event` beendet; Threads `latewatch`/`pressure` hängen am Turn bzw. messen nur | durch WP-SAFE2-Tests abgedeckt (Tick, Turn, Job mit/ohne Abbruch, Neustart) | erledigt für Freeze; Replay-/Timer-Wiederaufnahme nach Freigabe wird jetzt gemeldet |

## 3. WP-SAFE2 `:stillstand` (neu, dieser Thread)

`v13/standstill.py`, Befehl `:stillstand [aus|status|json]`, Tests `tests/test_standstill.py` (13).
- Ein Befehl schaltet die drei vorhandenen, gespeicherten Schalter zusammen: Notaus + Warteschlange pausiert + Age eingefroren.
- Wartet bis 10 s auf das Ende des laufenden Vorgangs; meldet „Bestätigt: kein Vorgang läuft mehr“ nur, wenn alle drei an
  sind **und** kein Job läuft. Ein Job, der den Abbruch ignoriert, wird namentlich gemeldet, nie als gestoppt ausgegeben.
- Neustart bleibt im Stillstand (alle drei Teile sind persistiert).
- `:stillstand aus` hebt nur die Teile auf, die der Befehl selbst eingeschaltet hat; vorher vom Nutzer gesetztes
  `:notaus` / `:age freeze` / `:pause` bleibt. Meldet, wie viele wartende Hintergrund-Aufgaben danach wieder anlaufen
  (GPT-Punkt „Neustart ohne unbeabsichtigte Wiederaufnahme“).
- `:notaus` sagt jetzt ehrlich: „Lernen und Hintergrund laufen weiter; alles anhalten: :stillstand“.
- Grenze: vom Nutzer selbst getippte Operator-Befehle laufen weiter (der Nutzer bleibt Herr des Systems). Selektiver
  Reset und Organ-Rollback sind nicht Teil dieses Pakets.

## 4. Drive-Abschnitt 9, Prüffrage 1 (JEPA End-to-End): Antwort für den aktuellen Code

- Trainierbare Tensoren mit Updates: nur C3-LoRA (`lora_trainer`, Torch CPU, HF-Master) und C3 nativ (WP-S6, isolierter
  Kandidat, AG6-Gate FAIL wegen Vergessen). Ziel: CE (+ KL-Anker), JEPA-Term vorhanden, aber in allen archivierten Läufen 0.
- B1/B2: keine Updates aus irgendeinem Objective (Port-Vertrag fail-closed). Predictor-Lernen (`predictor_worker.py`)
  läuft auf eingefrorenen Body-Zuständen = genau der von GPT genannte „begrenzte Versuch“.
- Folge: das Endziel „beide Bodies lernen selbst“ (Canon W4/W6, STEP6) ist offen, nicht widerlegt. GPTs Lernpaket-Plan
  (Komponenten-Gradienten, CE/KL vs. richtiges vs. falsches latentes Ziel, Retention, Zwei-Body-Kreislauf) wird als
  WP-LP1 in die ROADMAP übernommen; zuerst an C3 (vorhandener Trainer), dann B1/B2 sobald ein Trainingsport existiert.

## 5. Abgleich

Übernommen in `claude/project-thread-2p69gl`: beide GPT-Branches unverändert gemergt (keine GPT-Datei geändert außer
ROADMAP/Handoff-Zusammenführung). Außerdem nachgeholt: Gegenprüfungs-Runde 1 (`g2f277`, PR #8) war nie in der
gemeinsamen Kette; jetzt enthalten (Privatsphäre-Scan, `PRUEFUNG_CLAUDE_FUER_GPT.md`, `listarith`-Vorkommens-Wächter).
Volle Suite frischer Checkout nach Merge: 1714 OK, 5 Skips. Privatsphäre-Scan `9436eb7..HEAD`: CLEAN.
