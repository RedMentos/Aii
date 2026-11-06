# V13 / Inquisition — Codex-Fortsetzung 2026-11-06

## Grundlage und Grenzen

Der vollständige Blueprint v10.16.1 ist im Repository unter
`v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md`.
Die maßgeblichen neueren Nutzerentscheidungen stehen in
`v13/NUTZER_ENTSCHEIDUNGEN.md`: mehrere spezialisierte Modelle, Englisch zuerst,
später Deutsch als Lerntest, World-Model und kontinuierliches Lernen als Ziel.
Die untersuchten Entwicklungszweige sind getrennt; die folgenden Entwürfe sind
nicht gemergt und ihre Kombination nicht als Gesamtsystem geprüft.

## Gesicherte Prüfzweige

1. **Historische Vorabprüfungen / Run117DH:**
   [PR #1588](https://github.com/RedMentos/Aii/pull/1588), Remote-Commit
   `ab289ef106f67f8c3b3e39375c8e141934e73755`, Tree
   `8f130ffa1e85785088906981c5c9b30f579d855e`, Basis
   `7bf3557bf5a94c6860285be7137c7da714c77995`.
   Die Tests berücksichtigen den absichtlichen Schutz gegen geänderte
   `utility.py` und prüfen Eingriffe in getrennten Quelldateikopien. 12
   fokussierte Tests bestanden, 18 mit benachbarten Modulen. Die alte
   native Source-Bindung wurde nicht geändert; kein Native-/Handy-PASS.
   Ein vorangegangener 5-Modul-Aufruf hatte einen Importfehler, weil das
   Run90-Testmodul auf diesem Zweig fehlt; der Befund ist im PR dokumentiert.

2. **BP6 / FS3, gleiche Konfidenzwerte:**
   [PR #1589](https://github.com/RedMentos/Aii/pull/1589), Remote-Commit
   `2766598914cbe1e42894071242c0b2ec0d901759`, Tree
   `0b8c134a78c3960a3d471b952169ad4fe3f58f7a`, Basis
   `d9e16783d6a36554b752c76d51ab49e6d78c0431`.
   Gleiche Werte bleiben in einem Bin; Umordnen derselben Paare ändert die
   Auswertung nicht mehr. 55 Tests bestanden. Nachträgliche Nachrechnung der
   300 gespeicherten Antworten: `share_above_half` meta_i 0,1552 → 0,1773;
   Ziffernkonfidenz bleibt mit 0,3589 vorn. Originaldaten und alter Bericht
   unverändert; kein neuer Modelllauf oder statistischer Gate-PASS.

3. **BP5 / BP9a, Vorabprüfung und Bericht:**
   [PR #1590](https://github.com/RedMentos/Aii/pull/1590), Remote-Commit
   `67ea08c2a1d481d741b543c76863dc33d2fee62b`, Tree
   `46ea149679877c5f049cd7d5a176803582b34354`, Basis
   `7f0158d223fefe5bb218ddccab6bf79dbbc44fb7`.
   Vorabprüfung verwirft ungültige Genauigkeiten/Zeilenzahlen und verlangt
   einen L1-Punktwert über SCALAR; Manifestprüfung bindet die Zeilen-Hashes.
   Das belegt weder unabhängige Texte/Saaten noch statistische Signifikanz,
   L2-Abnahme oder L3-Freigabe. 11 gezielte Tests bestanden. Der BP9a-Bericht
   unterscheidet jetzt das in den drei Originaldateien fehlende `no_own`-
   Recall-Ergebnis (`null`) von einem gemessenen Nullwert; Rohdaten und
   `BP9a_FAIL` bleiben erhalten.

   Erster vollständiger Software-Suite-Lauf nach der BP5-Codeänderung: 1887 Tests,
   14 Skips, ein Fehler. `test_toolforecast.CheckpointTests` erhielt
   `PermissionError`, weil `/root/native/restore/round8-note-tool-raw` in
   dieser Umgebung nicht lesbar ist. Der historische Vergleich wurde als
   eigener Test mit sichtbarem Skip bei fehlendem/nicht zugänglichem
   Ausgangspfad abgetrennt; andere Auswertungsprüfungen bleiben aktiv. Der
   anschließende vollständige Software-Lauf ergab 1888 Tests OK und 15 Skips.
   Einer davon ist dieser Planvergleich; der Python-Umgebung fehlen u. a.
   Torch/Transformers. Kein Modell- oder Redmi-Lauf wurde ausgeführt.

Alle drei Remote-Heads und Trees wurden nach der Veröffentlichung geprüft;
die jeweiligen öffentlichen Diffs wurden auf private Daten gescannt (CLEAN).
Alle drei PRs sind Entwürfe und betreffen unterschiedliche Grundlagen.
Die zusätzliche Drive-Sicherung dieser Übergabe schlug fehl: Google Drive
meldete `storageQuotaExceeded` (HTTP 403). Die Notiz ist stattdessen im
BP5-Prüfzweig unter `v13/code/docs/coordination/` gesichert.

## Nächster Schritt

Die drei Diffs unabhängig prüfen und nur nach expliziter Integration der
zugehörigen Entwicklungslinien zusammenführen. Den übersprungenen historischen
Toolforecast-Planvergleich bei Verfügbarkeit seiner Originaldaten nachholen;
fehlende Testsuite-Voraussetzungen getrennt behandeln. Weitere Blueprint-Pakete
gemäß aktuellem Plan fortsetzen. Fehlende
Redmi-/Native-Messungen und vorhandene negative Gates bleiben offen; keine
unbelegte Aussage über vollständiges System oder kontinuierliches Lernen.
