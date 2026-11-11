# C3: gespeicherte Lernfreigabe und vollständige Korrekturquellen

Aufbau auf Body-Integrationscommit `bb1a94ca4d5b123640dff4574095f1d047f94846`, weiterhin dieselbe hashgebundene Reviewkopie unter SourceHandoff-Freeze. Neuer Builder `scripts/integrated_c3_consent_candidate_20261111.py`; keine eingefrorene produktive Datei geändert.

Der alte allgemeine AG6-Kandidatenpfad konnte aktive fact/style/preference-Erinnerungen trotz `permission=record` übernehmen. Zusätzlich lieferte der SDFT-Datasetpfad nur Source-ID/Hash ohne Zeichenspanne. Ein älterer Glue-Test hatte diese Lücke durch einen erfundenen, manuell vollständigen Mock-Datensatz verdeckt.

Der gemeinsame C3-Pfad verwendet jetzt den vorhandenen F1/F5-Prüfer: MemoryRecord, HumanDecision, Feedbackzeile, Ereignisgeneration und tatsächlicher USER-/Korrekturtext müssen zusammenpassen; Feedback und HumanDecision müssen konsistent **learn** erlauben. Ursprüngliche Eingaben bleiben als explizite SourceRef-Abhängigkeiten am Item. Record-Erinnerungen bleiben für Abruf gespeichert, gelangen aber nicht in direkte C3- oder SDFT-Trainingsbatches. Veraltete/beschädigte Nachweise erhalten keine stillschweigende Trainingsfreigabe.

SDFT wird aus denselben verifizierten menschlichen Korrekturen erzeugt. Die Referenz ist vollständig, der Student-Prompt entspricht der echten Eingabe, und der Teacher-Prompt wird aus dem festgelegten Template und exakt dieser Korrektur rekonstruiert. Target bleibt bis zum vorhandenen Selbst-Teacher-Schritt leer. Manipulierte Teacher-Prompts, veränderte Zielwerte, Löschung, fehlende F5-Entscheidung oder zurückgezogene Freigabe blockieren den gesamten Batch. Der bestehende zusätzliche Prüfer für ausdrücklich bewertete Antworten mit ihren Abhängigkeiten bleibt unverändert wirksam.

C3 prüft Modus, Trainingspause, Quelle, Freigabe und Holdouts vor Modellladen, über den bestehenden Cancel-Callback während des Fits und nochmals vor Veröffentlichung des Ergebnisses. Die Evidenzprüfung innerhalb des Callbacks erfolgt für einen ganzen begrenzten Batch statt als erneuter Vollscan je Item. Quellenwiderruf nach einem tatsächlichen AdamW-Schritt verhindert ein TRAINED-Ergebnis und eine spätere Freigabe. Private Zwischenartefakte können bestehen bleiben; vollständiges physisches Löschen oder Unlernen ist nicht behauptet.

Zulassung ist auf 256 Items mit begrenzten Text-/Evidenzlesevorgängen beschränkt. Historische benutzerdefinierte Erinnerungsschlüssel ohne unabhängig gebundenen menschlichen Schlüsselnachweis werden weiterhin gelesen, aber nicht als trainierbarer Prompt angenommen; normale Eingabe/Korrektur und die bestehende universelle Stilregel sind unterstützt. Ein zukünftiger expliziter Key-Source-Vertrag bleibt dafür offen. Die Mechanismen sind kein unabhängiger Qualitäts-/Retention- oder Handy-Ressourcennachweis.

## Prüfung

- **13 neue Fälle PASS**, äußerer Stage-Test PASS: record bleibt lesbar, direct/SDFT mit learn, vollständige Spannen, F1/F5-/Input-/Permission-Manipulation vor Fit, gefälschter Teacher-Prompt, tatsächlicher Tiny-C3-/PEFT-Schritt, Widerruf nach echtem AdamW-Schritt und verweigerte Freigabe danach.
- **486 gemeinsame Tests PASS / 3 CUDA SKIP / 58 Untertests PASS** in einer erzeugten Kopie einschließlich Body, World, Kontext/Archiv und vorhandener AG6-Freigabe-/Rollback-/Widerrufsprüfungen.
- Erster erweiterter Lauf **5 FAIL / 481 PASS**: alte positive Testfixtures hatten nur record erlaubt; der alte SDFT-Glue-Mock umging die echte Datenquelle. Positive Fixtures fordern nun ausdrücklich learn, und der Glue-Test verwendet die tatsächlich angelegte Korrektur. Keine Admission- oder Freigabeprüfung wurde abgeschwächt. Der rote Lauf bleibt erhalten.
- Modelle/Exporter sind ausdrücklich Tiny-/synthetische Testpfade; kein nativer GGUF- oder Redmi-Erfolg. Remote-CI erst nach tatsächlichem Abschluss ergänzen.

```bash
cd v13/code
python -m pytest -q -s tests/test_c3_consent_stage_20261111.py
python -m pytest -q -s tests/test_staged_integrated_regression_20261111.py
```

Quellen, geschlossene Rohlogs und SHA-Bindungen: `proofs/c3-consent-20261111/`. Aktueller Stager bleibt der einzige gemeinsame Erzeugungspfad; Body-Auswahl/-Batches und alte negative Gates werden beibehalten. Nächste Implementierung läuft bereits: tatsächlicher begrenzter World-JEPA-Idle-Job im vorhandenen G13-/Sleep-Scheduler ohne vorgetäuschte HUMAN-Autorität; separater Mode-/Pausenfehler im alten learn_medium-Ridge-Pfad. Datensatzimport und langfristige Speicherverdichtung sowie Cross-Organ-Selbstoptimierung bleiben offene Ziele.
