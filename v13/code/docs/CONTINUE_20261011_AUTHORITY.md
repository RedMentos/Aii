# Wiederaufnahme: WP-T10 Live-Vergleiche, 2026-10-11

Ausgangspunkt ist `RedMentos/Aii`, Branch `claude/project-thread-hiczvw`, Commit `a895487f1b8edda600dcd8098cb7f6a92bfbecfa`. Arbeitsbranch: `codex/authority-live-comparisons`. Kein Neuaufbau und kein Austausch von Claudes funktionierenden Teilen.

Die Single Source of Truth bleibt `docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`, SHA256 `3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`.

## Fertiger Teil dieses Checkpoints

Die vorhandenen Controller `attention.py`, `deliberation.py` und `callosum.py` speisen trainierte Scaffold-/Learned-Vergleiche in die vorhandene Lernfreigabe ein. `tests/test_authority_live.py` prüft untrainierte Rückfälle, gültige Anfrage-Auswahl, genau einen Provider-Pfad, Age-Gates, Empfängerwechsel und SQLite-Restart. Zusammen mit den betroffenen bestehenden Tests: 46 PASS. Maschinenlesbarer Bericht und Original-Testlog: `docs/proofs/authority-live-20261011/`.

Installationsprüfung aus der entpackten ZIP: 946 Tests in 59,081 s, 942 PASS, vier explizite PyTorch-Skips. Der erste Versuch mit dem unvervollständigten Import (ein FAIL, zwölf ERROR) bleibt als Log erhalten. Die drei fehlenden Dateien `native_norm_shadow_port.cpp`, `native_norm_poll_policy.hpp` und `causal-output-lifecycle-20261009/native-fixture-proposal.json` sind aus dem früher gesicherten Installationspaket Version 19 gegen dessen Manifest-Hashes bytegleich wiederhergestellt. Es wurden keine vorhandenen Runtime-Dateien durch alte Versionen ersetzt.

Die Beobachtungen betreffen Rangfolge/Modusliste/Kanalwahl. Sie liefern keine erfundenen Outcome-Labels und keinen Nutzen-Nachweis. PARTIAL-Lernziele, Gate-Verdikte und explizite menschliche ACTIVE-Freigabe bleiben bestehen. LATENT bleibt gesperrt. Das generische Authority-Ledger ist aggregiert und nicht pro Empfängerrevision isoliert.

## Exakt weiterarbeiten

1. Dieses Dokument, `BUILD_STATE.json` → `current_checkpoint` und die WP-T10/WP-T9-Einträge in der äußeren `ROADMAP.md` lesen. Der bisherige `CONTINUE.md`-Inhalt ab dem historischen Oktober-9-Checkpoint bleibt als Verlauf erhalten.
2. WP-T10: Die drei jetzt angebundenen Köpfe haben weiter PARTIAL-Lernziele. Lernziel-/Gate-Nachweise müssen gemessen werden; ein gut übereinstimmender Vorschlag genügt nicht. Gist und Neuromod-META haben weiterhin keine Live-Vergleichs-Hooks.
3. WP-T9: Vorhandenen Exact+Sparse-Doppelkontext im bestehenden Runtime-/Trainer-Pfad auflösen und mit realen Gewichten gegen die eingefrorenen Baselines messen. Das bisherige schwächere kombinierte Ergebnis erhalten. Nicht ohne Messung die Auto-Trainerwahl ändern.
4. Danach die offenen Aufgaben der Roadmap fortsetzen: B1/B2-Verschiedenheit und STEP2-Nutzen, native Body-/B3-Gates, Dream/F4 und aktueller Redmi-Dauerlauf. Der historische Redmi-SMOKE_PASS bleibt ein historischer Nachweis, kein Test dieser Revision.

## Vorhanden / fehlend

Claudes GitHub-Stand enthält Quellen, Tests, Pläne und viele Bench-Ergebnisse. Die großen ursprünglichen `docs/proofs/`-Rohsammlungen, native Modell-Caches und `archiv/chat/` waren dort nicht enthalten. Historische Dateipfade in BUILD_STATE sind keine Garantie für lokal vorhandene Rohartefakte. Keine nativen Aufrufe in diesem Checkpoint; keine gelöschten fehlgeschlagenen Messwerte.

Der erste Push wurde historisch durch die automatische Freigabeprüfung blockiert. **Am 2026-10-11 um 04:35:02 Europe/Berlin erteilte der Nutzer die dauerhafte Freigabe für Projekt-Pushes auf Arbeitsbranches in `RedMentos/Aii`: „Man so das du immer kannst“.** Diese Freigabe ist in der äußeren `NUTZER_ENTSCHEIDUNGEN.md` festgehalten und gilt für weitere Routine-Zwischensicherungen. Nicht erneut nach derselben Erlaubnis fragen. Die Shell besitzt keine GitHub-Anmeldung; der verbundene GitHub-Zugang kann den identischen Quellbaum über die Git-Objekt-API veröffentlichen. Erst ein verifizierter Remote-Head/Quellbaum bestätigt die Sicherung.

Die bereits gespeicherten Download-ZIPs sichern den zum Erstellzeitpunkt noch unveröffentlichten Stand als Wiederherstellungsartefakte. Der Quell-ZIP enthält den vollständigen GitHub-Import plus Änderungen, Berichte und die ursprüngliche Roadmap; ein Git-Bundle und ein Patch erlauben auch die Wiederaufnahme des lokalen Branches auf der bekannten Claude-Basis.

**Aktueller Veröffentlichungsblocker nach erteilter Freigabe:** Der erneute CLI-Push scheiterte an fehlenden Zugangsdaten (`could not read Username`). `github_create_tree` über den verbundenen GitHub-Zugang antwortete mit HTTP 403 `Resource not accessible by integration`. Es wurde kein neuer Branch/Commit auf GitHub veröffentlicht. Das installierte Plugin ist vorhanden, doch seine verfügbaren Einstellungsfunktionen können keine GitHub-OAuth-/Repository-Schreibrechte aktivieren. Die GitHub-Verbindung benötigt technisch Schreibzugriff auf `RedMentos/Aii`; dies ist keine fehlende Nutzerfreigabe. Nach Beheben der Verbindung ohne erneute Routine-Zustimmungsfrage veröffentlichen und den Remote-Quellbaum verifizieren.

Archiv-Metadaten nennen den Quell-Commit und die Prüfsummen; sie enthalten keine Modellgewichte oder Nutzerdaten. Installations-ZIP starten: entpacken, in `V13-Phone` `bash STARTEN.sh`. Einrichtung lädt die gepinnten Modelle, baut die vorhandenen Runner, führt Selbsttest/Probe aus und startet im Terminal den Chat. Der Android-Start dieser Revision muss noch auf dem Gerät geprüft werden. Nach Dokumentationsaktualisierungen werden die finale ZIP und ihre ausführbaren Dateien gegen die tatsächlich geprüfte ZIP verglichen; keine erneute Modellinferenz wird dadurch behauptet.

`canonical_architecture_complete=false`, `user_full_scope_complete=false`: Der Gesamtplan ist weiterhin offen; dieser Checkpoint schließt die konkret oben beschriebene Hook-Lücke.

## Veröffentlichung nach Installation des Connectors

Am 2026-10-11 wurde der technische 403-Blocker behoben. Der Arbeitsbranch `codex/authority-live-comparisons` ist auf GitHub veröffentlicht: Commit `5f5d22de540d1b48129a6e213c4bec1ed009f348`, Quellbaum `ca9e183507323025093f4656c2aeb781a85b988e`. Ein read-only Git-Fetch bestätigte denselben Quellbaum wie der zuvor unveröffentlichte lokale Checkpoint. Die vier lokalen historischen Commits bleiben auf `codex/authority-local-archive`. Der frühere Blockerabsatz ist Verlauf, kein aktueller Zugriffsfehler. Routine-Pushes sind weiterhin autorisiert.
