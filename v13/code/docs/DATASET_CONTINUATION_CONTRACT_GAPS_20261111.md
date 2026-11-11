# Nächster Anschluss: externe Corpusdaten an tatsächliche C3-Gewichte

Stand 2026-11-11, auf dem RECORD-Consumer `8d601e684917b692e004c00e464d806c19103016`. Nutzerziel bleibt langsames, begrenztes Lernen aus vorbereiteten Anfangsdaten. Aufnahme allein ist noch kein Lernen. Die jetzigen Aufnahmebelege bleiben unverändert PREVIEW_ONLY und `training_authority=0`; externe Texte sind keine menschlichen Korrekturen.

## Geprüfte Befunde

`guards.item_origin()` ordnet unbekannte Arten bisher als `human` ein. Ein neues Corpusitem unverändert einzuspeisen würde die Humanquote fälschen. `ORIGINS`, `DATA_MIX` und `mix_for_training` kennen keine eigene externe Herkunft; die normale Konsolidierung verlangt mindestens 60 Prozent Humananteil und null Seedanteil. Ein eigenes externes Curriculum benötigt einen ausdrücklichen separaten Vertrag und überprüfbare Herkunft, keine Umbenennung in human/human_replay und keine globale Lockerung bestehender Guards.

`LoraTrainer._encode()` erzeugt Chattemplate, Assistant-Anfang und Endmarker. Dokumentfortsetzung braucht dagegen einen ausdrücklich anderen Encoder: vollständiges Dokumentfenster einmal tokenisieren, einen echten Token-Cut festlegen, Präfixlabels maskieren und die verbleibenden Dokumenttokens vorhersagen. Tokenizer-/Fenster-/Cut-Digests gehören zur gespeicherten Bindung. Keine erfundene Nutzerfrage und kein durch Abschneiden vollständig verlorener Präfix.

`LlamaCppEvaluator` misst Chatantworten. Ein Corpusgate benötigt zusätzlich feste dokument- und inhaltsdisjunkte Continuation-Holdouts sowie alte Chat-/Fakten-/Leak-/KL-Retention. Eine nur sinkende Trainingsloss oder veränderte Tiny-LoRA ist dafür kein Qualitätsnachweis. `_guard_holdouts` allein verhindert keine semantischen oder vollständigen Dokumentüberschneidungen.

`WeightConsolidation.stage/train/_check_item_sources`, beide Approval-Transaktionen und `c3_consent_admission_candidate.check/training_cancel` müssen einen neuen typisierten Itemkind an einen separaten Corpusvalidator reichen. Alle übrigen Items behalten ihre F1/F5-Prüfung. Quelle/Importgrant/Lerngrant müssen vor Laden, bei jedem Schritt, nach Fit und vor Nutzung aktuell bleiben. Ein G13-Aufnahmeereignis ist kein USER-Ereignis.

Außerdem lädt `LoraTrainer._load_gguf_weights` die aktive LoRA nicht automatisch als Ausgangspunkt eines neuen Batches. Unterschiedliche Batches können deshalb wieder vom Basismodell beginnen. Ein dauerhaft lernendes C3 braucht eine gebundene Adapter-/Optimizer-Generationsfolge mit Replay/Retention und Quelle-/Widerrufslinie; derselbe Batch-Resume allein löst das nicht. Die World-Optimizer-Fortsetzung ersetzt diese C3-Lücke nicht.

## Konkreter Implementierungsvertrag

Separater, standardmäßig ausgeschalteter `DatasetLearningGrant`, gebunden an C3-Rolle, aktuelle Record-Grant-/Source-IDs, vollständige Zeilen-/Beleg-/Dokumentdigests, Quellrevision und Lizenz-/Provenienzbelege, Objective-/Tokenizer-/Masterrevision, begrenzte Tokenfenster und Train-/Holdout-/Retention-Kohorten. Aufnahmeberechtigungen werden nicht nachträglich umgedeutet. Die Grant- und Itemrevision muss in Dataset-, Resume- und Freigabedigest enthalten sein.

Eigene G13-Lernaktion mit tatsächlicher Worker-/DISPATCHED-Prüfung, SHADOW-Modus, Trainingspause, Vordergrund/Ressourcen und vorab persistiertem Schritt-/Token-/Zeit-/Speicherbudget. Erste geprüfte Fassung darf nur private TRAINED-Artefakte erzeugen. Aktivierung bleibt an unabhängige Gates und ausdrückliche Freigabe gebunden; ein Widerruf beendet Nutzung, beweist kein Unlernen.

Prüfung: echte RECORD-Aufnahme → getrennte Lernadmission → tatsächliche Tiny-LoRA-/Adam-Änderung → gleicher unterbrochener/fortgesetzter Stand; fehlender Grant, falsche Herkunft, geänderte Dokument-/Tokenizerbindung, Holdout-Kollision und Widerruf vor/während/nach Fit müssen blockieren. Danach generationsübergreifende Fortsetzung mit alten Fakten und festen Holdouts, bevor kontinuierliches Corpuslernen behauptet wird.

## Primärquelle und Behauptungsgrenze

Am 2026-11-11 wurde die [Cosmopedia-100k-Karte auf Revision 8fdb6dada238c1d46dd8cf61da2fb4f9c36f654d](https://huggingface.co/datasets/HuggingFaceTB/cosmopedia-100k/resolve/8fdb6dada238c1d46dd8cf61da2fb4f9c36f654d/README.md) unabhängig nachgelesen: 944 Byte, SHA256 `9b53e14d740b3292bfb19a337433a9860cfce4fb3c179c6a73370fc2f886ff24`. Sie deklariert Apache-2.0 und synthetische, mit Mixtral erzeugte Daten. Originalkarte und Abrufmetadaten: `proofs/dataset-continuation-research-20261111/`.

Das ist ein aktueller belegter Metadatenbefund und keine bereits ausgestellte Trainingsfreigabe oder vollständige Rechte-/Attributionsprüfung. Die bestehende Katalogpolicy sagt ausdrücklich `license_field_is_metadata_not_legal_review=true`; PROBE ist keine Trainingsberechtigung. Ein primär gebundener vollständiger Trainingsvertrag liegt im jetzigen Aufnahmeweg noch nicht vor. Es wurden keine Datasetzeilen heruntergeladen und keine öffentlichen Corpusdaten trainiert. Diese Arbeit ergänzt den ursprünglichen Blueprint und hält den offenen Umfang sichtbar.
