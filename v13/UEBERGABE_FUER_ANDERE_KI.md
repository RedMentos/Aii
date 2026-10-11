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
