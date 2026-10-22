# Zielabgleich 2026-10-21 — zuerst lesen

Neue Zielliste aus dem Blueprint selbst: `ZIELABGLEICH.md` (§29 24 Eigenschaften: 8/14/2; §100 Gates: 0 von 10 grün; STEP2 ist der Engpass). Nächste Pakete sind **WP-Z1 bis WP-Z12** am Ende von `ROADMAP.md`; sie gehen vor älteren offenen Paketen. Seitenzweige (R4-Werkzeug-Regeln, Action-JEPA-Runden, Vision-Lab) nicht weiter ausbauen, bis Z2–Z5 Ergebnisse haben.

Stand 22.10. (Thread „Harness-Pakete HX1 HX3 HX4“, Branch `claude/project-thread-4iqpro`): WP-HX1/HX3/HX4 gebaut (Drumherum-Vorschläge mit Erlaubt-Liste in AG8, Erfahrungs-Bibliothek nur mit Beleg, blinder Auswähler), alles SHADOW; nächster Schritt WP-HX2. Details `code/docs/HANDOFF_CURRENT.md` oben.

Stand 22.10. (Thread „B3 L1 frische Seeds“): **B3-L1-PASS auf escalate (Versuch 5) auf 2 frischen Saaten nicht repliziert** (beide knapp n.s. über den Attribut-Wörtern); action saatabhängig (2 von 4). B3_LATENT bleibt unavailable, L2 gesperrt. Beleg `bench-results/b3-l1-v6-20261022/README.md`, Branch `claude/project-thread-y2mnt5`.

Stand 22.10. (Thread „GPT-Stand erneut prüfen“): GPTs Pakete vom 22.10. (PR #27, #29) geprüft und übernommen; neu **`:stillstand`** hält alles an (Werkzeuge, Lernen, Hintergrund, Alterung), weil `:notaus` Lernen weiterlaufen ließ. Antwort an GPT je Prüfpunkt: `code/docs/coordination/CLAUDE_ANTWORT_AGE0_LERNPFAD_20261022.md`. Nächste Pakete WP-AGE0a/b, WP-LP1, Regel-Leser v3 (`ROADMAP.md` oben).

Stand 21.10. (Thread „Nächste Pakete R“): **Z4 erledigt — B3 L1 PASS auf `private/action`** (escalate/apologize FAIL); nächster Schritt Z4b (L2-Prefix-SHADOW nur für action). **Z4b erledigt (21.10., Branch `claude/project-thread-c122qc`): L2 FAIL** — latenter Prefix im eingefrorenen B2 trägt die Info (80,2 % vs. 41,5 aus, Kontrollen auf Zufall), schlägt EXACT und Attribut-Wörter, aber nicht das Label-Wort als Text (81,5 %); B3 bleibt L1_shadow, L3 gesperrt. Beleg `bench-results/b3-l2-prefix-20261021/`. Schnelle Spur: Schlüsseltrennung nativ bestätigt, selektive Zustellung noch kein Gewinn.

**Regel-Lesen (Z3 → Z3b → Z3c, 2026-10-21):** C3-350M liest Ja/Nein-Regeln nie (konstant `true`), auch kein Signal für Training. Regeln liest ein deterministischer Parser: `code/docs/proofs/continuation-20261021/z3c-extensible-parser/parser_v2.py` + `lexicon.json` (Einträge nur mit Beleg, `extend()`), Urteil `PARSER_V2_CARRIES_AUTHOR_ONLY` (frische Autor-Formen 0.91 exakt, 1/57 falsch; Modell-Umformulierungen noch Lücken im Lokal-Wortschatz, dort UNKNOWN statt falsch). Branch `claude/project-thread-x1etmj`. Nur SHADOW.

# Claude-Übernahme des GPT-Stands — 2026-10-20

Für GPT/Codex: Dein Stand `codex/continuation-20261016` @ `a1973d4` (PR #4) ist übernommen und mit den Claude-Threads K–P zusammengeführt (die GPT nicht hatte, u. a. WP-W2c Eligibility-Tool, R4 Teile 3–8, WP-N16–N22, §102-Ledger). Gemeinsamer Stand: Branch `claude/project-thread-0zelvf` (baut auf `a1973d4` auf, nichts überschrieben). Suite 1571 Tests OK, 6 Skips. Dein Drive-Kandidat vom 19.10. (privater Pilot-Auditor) ist noch nicht integriert. Bitte künftig auf `claude/project-thread-0zelvf` aufsetzen. Nächste Pakete: ROADMAP.md, Abschnitt „GPT/Codex-Stand 13.–19.10. übernommen“.

**Gegenseitige Prüfung ab 2026-10-21 (Nutzerwunsch):** Claude und GPT prüfen jeweils die letzte Arbeit der anderen Seite, bevor sie darauf weiterbauen (Regel in `AGENTS.md`, Abschnitt „Cross-review“). Runde 1 (Claude prüft GPT bis `a1973d4`): `PRUEFUNG_CLAUDE_FUER_GPT.md`, Branch `claude/project-thread-g2f277`. Ergebnis: GPT-Code korrekt, Gate-Angaben ehrlich, alle GPT-Branches privat-sauber; eine gemeinsame Lücke im `list_arith`-Zahlen-Wächter (doppelt gelesene Werte) behoben. **GPT ist als Nächstes dran:** Checkliste in Abschnitt 4 von `PRUEFUNG_CLAUDE_FUER_GPT.md` abarbeiten und Runde 2 dort oben eintragen.

**Gegenseitige Prüfung ab 2026-10-21 (Nutzerwunsch):** Claude und GPT prüfen jeweils die letzte Arbeit der anderen Seite, bevor sie darauf weiterbauen (Regel in `AGENTS.md`, Abschnitt „Cross-review“). Runde 1 (Claude prüft GPT bis `a1973d4`): `PRUEFUNG_CLAUDE_FUER_GPT.md`, Branch `claude/project-thread-g2f277`. Ergebnis: GPT-Code korrekt, Gate-Angaben ehrlich, alle GPT-Branches privat-sauber; eine gemeinsame Lücke im `list_arith`-Zahlen-Wächter (doppelt gelesene Werte) behoben. **GPT ist als Nächstes dran:** Checkliste in Abschnitt 4 von `PRUEFUNG_CLAUDE_FUER_GPT.md` abarbeiten und Runde 2 dort oben eintragen.

**B3 L1 Diagnose 2026-10-20:** L1-FAIL liegt nicht am Kanal oder an Bytes, sondern am Trainingssignal (Brücke lernt nur Aufgabenlabels, Baselines bekommen privilegierte Attribut-Labels). Neuer optionaler `aux`-Trainingsziel-Parameter in `v13/b3bridge.py`; explorativ PASS nur auf `action`. Details `bench-results/b3-l1-diagnose-20261020/README.md`; nächster Schritt vorregistrierter Versuch 4 mit frischen Daten.
## Frühere Übergaben (erhalten; GPTs Fassung vom 16.10. liegt zusätzlich auf Drive)

# V13 / Inquisition-JEPA – Übergabe für eine andere KI (Stand 2026-10-11)

Projekt: brain-inspirierte, kontinuierlich lernende KI-Runtime für ein Redmi-Handy (Android/Termux, 6 GB RAM). Nutzer schreibt Deutsch, arbeitet nur am Handy.
Zuerst lesen: `ROADMAP.md` (Pakete + Status), `NUTZER_ENTSCHEIDUNGEN.md`, `SICHTUNG.md`, `ABDECKUNG.md`, `code/README.md`, `code/docs/CONTINUE.md`.
Code: `code/v13/` (Runtime), `code/tests/`, `code/scripts/`, `code/specs/`. Tests: `PYTHONPATH=.:tests python -m unittest` in `code/` (zuletzt ~940 grün; `test_bodies.TightBudget` sporadisch flaky).
Nutzerentscheidungen: viele verschiedene Modelle, Englisch zuerst, konstantes Lernen als Endziel, Gehirn-Simulation, Age-Hülle bleibt Start bei 0.
Offene Punkte: L1-Gate FAIL (B3 LATENT unavailable); STEP2 two-body FAIL; viele SHADOW-Flags brauchen Redmi-Messung; WP-T17 Dream-Lauf 2 offen.
Nicht im Repo (zu groß): `code/docs/proofs/` (199 MB) und `archiv/chat/` (5 MB), bench-results/*/acceptance.


## Reviewbarer Fortsetzungsstand 2026-10-11 (2026-10-11T04:21:30.678042+00:00)

Der eingefrorene STEP2-Vergleich ist vollständig:70/70 Varianten, alle strukturellen Prüfungen und Abschlussbindungen bestehen, semantisch bleibt **UTILITY_FAIL**. Primär `both_exact`=.5, B1 allein=.508333, Same-policy-dual=.558333. Alle70 Antworten wählen NONE;22 enthalten ungültige Entitätszuordnungen. Die neue Transportauswertung reproduziert sämtliche Originalscores. Der eingefrorene Quellstand und sein Report bleiben getrennt von späterer Entwicklungsarbeit.

Danach ist der dreiteilige Source-Handoff in `code/v13/bodyview.py`, `cognition.py` und `runtime.py` integriert: eigener Aktionszustand ist ausdrücklich kein Quellenwissen; ausgewählte Hypothesen werden von verifizierten Zitaten getrennt; gespeicherte Query/Offer-/Quellenbindungen werden vor Zustellung erneut geprüft. Keine fehlenden Regeln werden aus Oracle oder vollständigem Prior eingesetzt. Die Hauptsuite im Linux-Quellbaum besteht mit1061 Tests (1057 PASS, vier explizite PyTorch-Skips, keine Fehler). Das ist **kein neuer entpackter Handy-ZIP- oder Redmi-Nachweis**. Native Qualitätsverbesserung bleibt offen; die getrennte16-Fälle-Ablation ist vorregistriert.

64 echte native Schema-Diagnoseantworten vergleichen350M und1.2B mit identischen Quellen/Fällen/Armen. Alle Enumlabels sind in Kopierkontrollen ausführbar. Weder Feldreihenfolge noch das größere Modell liefert im Vier-Fälle-Entscheidungsset der Vollschema-Arme eine vollständig korrekte Rechnung/Eligibility/Entscheidung. Die Feldreihenfolge-Hypothese ist damit kein begründeter Produktionsfix; keine Modellwahl oder Qualitätsbeförderung. Laufzeitvergleich ist ausdrücklich ungültig. Beleg: `code/docs/proofs/continuation-20261011/schema-action-model-comparison.json`.

Dream-Lauf2 hat2/15 vollständige Arme (seed13: none und replay_exact) mit echten230M-Master-/LoRA-Schritten, PhaseB40 und Seeds13/21/34. Er ist seit2026-10-11T04:19:35Z **PAUSED_FOR_SERIAL_HEAVY_JOBS**, Worker nach Exit130 beendet. Der unvollständige seed13/dream_validated-Armenstand B10/40 ist erhalten; Wiederaufnahme startet diesen Arm unverändert von der Basis. Die Vergleichsauswertung ist partial, kein vollständiger Dream-Nutzen-Gate-Nachweis. Pause: `code/docs/proofs/continuation-20261011/dream2-v2-serialization-pause.json`.

Native Action-Tap-Erfassung: datierter haltbarer Snapshot736/1875 Zeilen und46 Batches (2026-10-11T04:17:50.512766+00:00); ursprünglicher384-Zeilen-/24-Batch-Prefix ist konserviert. Der zuletzt vorhandene beobachtete Versuch endet SIGKILL(-9)/RemoteDisconnected; frühere Fehler-/OOM-Belege werden nicht entfernt. Root hat die exakt gebundene Wiederaufnahme aus736 als einzigen schweren Modelljob autorisiert. Neue terminale Beobachtung und vollständige1875-Zeilen-Erfassung stehen aus; keine Fit-/Empfänger-/JEPA-Qualitätsfreigabe. Laufende Reports wurden für diese Statusfortschreibung nur gelesen.

Weiter: zuerst serialisierte beobachtete Capture vervollständigen; danach unveränderten Dream-v2-Lauf wiederaufnehmen und getrennte Source-Handoff-Ablation messen. Vollständige native Body/Sparse-/B3-/Lernziel-/Kalibrierungs-/Redmi-Gates bleiben offen. `canonical_architecture_complete=false`, `user_full_scope_complete=false`, keine aktuelle Handyqualitätsbehauptung. Autoritativer Status: `code/BUILD_STATE.json.current_checkpoint.webchat_review` und die gespiegelten Ledgers.


## Durable recovery 2026-10-11T09:59:49.462861+00:00

GitHub3d63ec8 and both saved ZIPs were restored and hash/CRC verified after scratch was cleared. Actualdurable tap evidence is736/1875rows46batches; later1248-row observation exists only in prior conversation, not recovered raw data. Dream2 retains2/15 completed arms. Native and pinned training resources are rebuilding; no new inference or gate promotion yet. Embedding per-request RSS accumulation requires separately preregistered bounded worker lifetime, real fresh-worker invariance checks and serialized heavy jobs.
