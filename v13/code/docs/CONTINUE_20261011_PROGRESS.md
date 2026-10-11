# Continue: WP-T9 / WP-T10, 2026-10-11

Die Canon bleibt unverändert: `docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` (`3423906b01b24443fcef733fb5c7ef47296963df63e603d8f843c99d544877ee`). Kein Neuaufbau. Repository `RedMentos/Aii`, Arbeitsbranch `codex/authority-live-comparisons`; stehende Nutzerfreigabe gilt. Connector-Schreibzugriff funktioniert; vorheriger Checkpoint `5f5d22de540d1b48129a6e213c4bec1ed009f348` ist remote-baumsynchron verifiziert.

## Implementiert

- WP-T10 Neuromod-META: Vergleich der Scaffold-Plastizität mit dem tatsächlichen logistisch angepassten Vorschlag bei mindestens acht trainierten Retention-Snapshots. Unveränderte Zustände werden über Neustarts dedupliziert, Diagnosereports/Veto/Konflikt zählen nicht. Keine erfundenen Outcomes; Anwendung und explizite menschliche Freigabe bleiben bestehen. Das vorhandene Neuromod-Lernziel ist IMPLEMENTED, die drei früher angeschlossenen Köpfe bleiben PARTIAL. Gist ist weiterhin regelbasiert/UNAVAILABLE und darf keine angeblich gelernte Beobachtung erzeugen.
- WP-T9 native Fact-Slots führen unveränderliche ID/Key/Value/Source-Bindungen über Training, Akkumulation und Export mit. Die Registry bindet den Metadaten-Hash; Forget/Previous-Rollback aktualisieren die Bindung. Der bestehende Fehler mit Integer-Schlüsseln bei Akkumulation ist behoben.
- Der tatsächliche gesunde native Runner führt eine Ladebindung. Warmstarts prüfen billige Dateimetadaten; geänderte Registry/Modell/Binärdatei/Slots/Metadaten führen zum Entladen und Neuprüfen. Fehlgeschlagene/tote/ungebundene Runner liefern keine Bindung. Geerbte unfreigegebene V13_MEMORY_FILE-Variablen gelangen nicht in native Kinder.
- Der bestehende Runtime-Pfad schreibt nach Auswahl und Ausgabe des letzten Runners ein SHADOW-Inventar möglicher Exact/Trace-Doppelzustellung. Exact-Prompt, Memory-IDs und ursprüngliche Quell-Lineage bleiben vollständig erhalten. Hash-/Quell-/Inhaltskonflikte und alte Metadaten können keine Kandidaten liefern. `firing=UNMEASURED`, keine aktive Auslassung von Exact. Diagnose-Telemetrie erhält nur erlaubte IDs/Hashes/Flags, keine Faktenwerte oder Dateipfade.
- `scripts/fast_trace_compare.py` sichert jede native Antwort atomar, einschließlich voller Ausgabe, Tokens und Latenz. `--resume` verlangt identische Modell/Runner/Memory/Korpus/Quell-Bindung; `--repeats N` erhält einzelne gepaarte Wiederholungen. Gleichzeitige Wiederaufnahme ist gesperrt; Fehler und unvollständige Versuche bleiben erhalten. Vorhandene Ergebnisdateien werden ohne explizite Wiederaufnahme nicht überschrieben.

## Nachweise und Grenzen

107 gezielte Tests: 103 PASS, vier vorhandene PyTorch-Skips. 35 neue Tests. Der erste Aufruf enthielt einen falsch geschriebenen Modulnamen und ist als Fehlerlog erhalten; der korrigierte Aufruf bestand. Alle neuen native-memory-Tests nutzen ausdrücklich synthetische Bytes bzw. echte HTTP-Testkinder, keine erfundenen Modellqualitätsbelege. Bericht und Logs in `docs/proofs/continuation-20261011/`.

Echte C3-Linux-Baselines: englische/deutsche Antworten und Quellwert exakt 120, vier von vier pro eingefrorenem Quellstand; alle Prozesse beendet. Vollausgaben/Ressourcen/Hashes/Frozen Sources liegen in den beiden native-baseline-Unterordnern. Die zweite Baseline wurde vor der letzten einzeiligen Environment-Bereinigung aufgenommen; ihren Quellen-Hash nicht als finale Gesamtrevision ausgeben. Der laufende STEP012-Pfad verwendet den finalen Runner. Kein neuer Redmi-/Body-Trainings-/Sparse-Firing-Nachweis durch diese Baselines.

## Beim nächsten Continue

1. `BUILD_STATE.json.current_checkpoint` und `docs/proofs/continuation-20261011/report.json` lesen; laufende Arbeit nicht neu entwerfen.
2. Package-Selbsttest und native Vertikalmessung vervollständigen, deren echte Logs/Fehler samt Quellbindung hier sichern. Keine Diagnosesystem-Ausgabe als Modellantwort zählen.
3. WP-T9: gepaarte native Exact/Trace/Combined/selektive Messung auf derselben konservierten Corpus-Basis; Slot-Firing bleibt ohne native Instrumentierung ungemessen. Combined 7/8 und Leak 0,8 aus Claudes Benchmark erhalten; Auto-Trainer unverändert. Für aktive selektive Zustellung fehlen weiterhin gemessene Sicherheit/Recall-Gates.
4. WP-T10: Retention-/Nutzen-Nachweise und die PARTIAL-Ziele; Gist benötigt tatsächlichen gelernten Kopf/Labels. Danach ursprüngliche STEP0/STEP1/STEP2, native B3/A3/F4/Dream/Redmi-Aufgaben fortsetzen. Gates/Canon nicht abschwächen.
5. Projekt-Commits auf den autorisierten Arbeitsbranch veröffentlichen und Remote-Quellbaum prüfen; ZIPs plus BUILD_STATE/Proofs aktualisieren.

`canonical_architecture_complete=false`, `user_full_scope_complete=false`.

## Abgeschlossener Nachweis-Stand dieses Checkpoints

Installations-ZIP tatsächlich entpackt und über Selftest gestartet: 982 Tests, 978 PASS, vier explizite PyTorch-Skips, keine Fehler. Voriger Lauf (981, ein FAIL) ist erhalten: Ein bisheriger Test forderte bei 30 zufälligen UUIDs weniger als acht ausgewählte Detail-Traces, obwohl ein zufälliger Treffer von acht die legitime Speichergrenze ist. Jetzt prüfen feste Ereignis-IDs den echten SHA-Sampler und ein zusätzlicher Test die exakte Grenze der neuesten verpflichtenden menschlichen Beobachtungen. Keine Produktionsregel/Rate/Grenze geändert.

Echter aktueller STEP012-Linuxlauf: :probe SMOKE_PASS, C3/B1/distinktes Qwen-B2/Needle mit 3072D laufen. Drei background-Turns liefern FINAL mit echten B1/B2/Re-entry-OfferPackets, keine Fallbacks, alle strukturellen Audits bestehen. **Antwortqualität ist in allen drei Budgetaufgaben falsch:** Blue verbleibt 10 EUR, doch die Ausgaben nennen 110 bzw. 30. Keine Antwortqualität-/Komplementaritäts-/STEP1-/STEP2-Freigabe. Turnzeiten 27,40/30,95/31,95 s; nicht Redmi. Das erste versehentlich mit observer_mode=off durchgeführte Diagnose-Set und seine fehlerhafte reine Zahlen-Regex-Bewertung sind als Rohartefakte erhalten; nur das getrennte background-Set belegt den Observer-Pfad. Vollausgaben/Offers/Telemetry/SQLite/Quellen/Frozen Sources sind im verifizierten `docs/proofs/continuation-20261011/native-vertical-20261011.zip`, Zusammenfassung direkt daneben.

Nächste offene Arbeit: vorhandene STEP1/STEP2-Nutzen-Messung mit eingefrorenem Korpus und mehreren Armen/Seeds/Reproduzierbarkeit fortsetzen (nicht aufgrund der drei Alpha-Antworten den Prompt/Output umgestalten), native Slot-Firing instrumentieren und den bestehenden selektiven Kontextpfad gepaart messen; dann die übrigen offenen Lernziel-/Body-/Redmi-Gates. Modelle/Runner des Linux-Prüfstands liegen derzeit in scratch `native_baseline_oct11/home`; sie sind Cache, kein persistenter Beleg und nicht in den ZIPs. Ihre Pins/Hashes und alle Ergebnisse sind dauerhaft im Repository gesichert, Downloads bei Bedarf mit bestehenden Bootstrap-Funktionen wiederholen.
