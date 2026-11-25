# V13 – vollständige Fähigkeiten statt einzelner Komponenten (Nutzerkorrektur 2026-11-11)

**Status:** verbindliche Nutzer-Zielpräzisierung / Koordination; kein neuer Runtime-Code, keine Fähigkeitsfreigabe. Zu lesen gemeinsam mit Canon v10.16.1, v13/AGENTS.md, v13/NUTZER_ENTSCHEIDUNGEN.md, neuerem Selbstoptimierungs-Nachtrag #1741 und dem bestehenden Build-State. Neue Nutzerentscheidungen schlagen widersprechende alte Desktop-Harness-Annahmen.

## 1. Zielbild (Ultron als Funktionsanalogie, nicht als behauptete Fähigkeit)
Der Vergleich „Ultron aus dem Film“ bedeutet **ein zusammenhängendes KI-System mit Wahrnehmung, Gedächtnis, Selbst-/Weltmodell, eigenständigem Problemlösen, Langzeitlernen, Sprache/Stimme, Werkzeugnutzung und situationsabhängiger Handlung**, das auf Android lokal laufen und die erlaubten Funktionen des eigenen Android-Geräts verwenden kann. **Keine** Behauptung von AGI/Filmfähigkeiten und **keine** implizite Erlaubnis für unkontrollierte Selbstermächtigung, Fernzugriffe, Datenzugriffe oder unsichtbare Aufnahme.

Nicht einzelne Organe mit dem Gesamtziel verwechseln: Jeder Meilenstein beweist, welchen **Endnutzer-Task** die kombinierten Organe jetzt leisten und wie er persistiert, lernt, rückgängig gemacht und auf Android betrieben werden kann. Vollständiger Blueprint bleibt verbindlich – diese Matrix ersetzt nicht den Canon.

## 2. Android-Handeln: Hintergrundpfad zuerst, Oberfläche als Zusatzpfad
**Zwei Ausführungswege** sind nötig, nicht nur „Screenshot → Tap“:
- **Hintergrund-/System-API-Tools**: passende Android Intents, Datenanbieter/ContentProvider und Storage-Access-Berechtigungen, genehmigte Benachrichtigungs-/Geräteereignisse, erlaubte App-/Dienst-APIs, zeitgeplante Arbeit und freigegebene Termux-Kommandos. Pro Fähigkeit verifizieren, ob Android die Operation für normale Apps überhaupt erlaubt und welche expliziten Permissions/Interaktionen erforderlich sind.
- **UI/Accessibility-Fallback**: genehmigte Accessibility-Aktionen, optionale mit Zustimmung erfasste Bildschirmdaten, Navigation und Eingabe, wenn keine geeignete offizielle Hintergrund-/Direkt-API existiert. Kein Bypass von Android-Berechtigungen.

Beide Wege teilen ActionIntent → Capability/Consent Gate → Broker → Executor → Result/Side Effect → trusted T8 Episode → JEF/JEPA Feedback. Jeder Schritt hat Provenance, Benutzer-Stop/Cancel, Audit, Wiederholungsschutz und angemessene Rücksetz-/Kompensationsstrategien. „Android ist im Hintergrund bedienbar“ heißt **nicht**, dass beliebige Dritt-Apps unsichtbar steuerbar sind: Android-BAL/Foreground-Service-/Mikrofon-/Akku-Limits und Herstellerrestriktionen sind zu prüfen. Native Gerätebestätigung bislang UNVERIFIED.

## 3. Stimme / Audio: bestehender Canon, kein optionaler Luxus
Der Canon v10.16.1 definiert in §4A.2–4A.5 und §18.10, STEP9 und G10C/G10D:
- Streaming **RAW EAR** (Frames/Codec/Timing, akustischer Encoder/Projektor, Sprecherinformationen, Prosodie, nichtsprachliche Geräusche) **plus** zeitlich zugeordneter, austauschbarer ASR/Audio-Teacher als Referenz, nicht als einziges Weltbild.
- **Eigenständiger Speech Effector**: JEF/Sprechabsicht → trainierbarer acoustic/speech decoder → Vocoder/TTS-Renderer/Waveform; getrennt von C3, das die sprachlichen Inhalte / schnellen Antworten organisiert.
- **Full-Duplex**: hören während Sprechen/Denken/Tools; Unterbrechung/Barge-in; provisional vs final audio/transcript/T8 SourceRefs mit Zeitstempeln und ggf. Korrektur.
- **Lernfähigkeit**: auditive und expressive Repräsentationen, Sprache/Sprecher-/Prosodiemerkmale und Sprachproduktion sollen durch verified Error/Feedback→Eligibility/Modulation, Teacher-/Human-/World-Outcome-Vergleiche, kontrollierte Online-/Replay-/Dream-Updates schrittweise verbessert werden. Nicht bloß statische STT→LLM→TTS-Kette. Vorher-/Nachher-Benchmark für Erkennung, Timing, Prosodie/Stimmqualität, Unterbrechungen, lange Kontexte, Retention und Restart; keine unbefugte Stimmenkopie.
- **Boot-Fallback erlaubt**: STT→Text-LLM→TTS als erste lauffähige inkrementelle Route. Diese allein beweist die lernfähige Roh-Audio-/Speech-Latent-Zielarchitektur nicht.

**Status 2026-11-11:** Im GitHub-Build noch keine verifizierte Android-nativ laufende Full-Duplex-/Online-Audio-Lernkette. Im Canon als STEP9/G10C/G10D verankert; GATES als UNAVAILABLE / OFF / SHADOW ehrlich führen, bis eigene Code+Runtime+Latency+T8+Retention+Android-Belege vorliegen.

## 4. Gesamt-Capability-Ledger (bei jeder täglichen Boss-Kontrolle getrennt ausfüllen)
| Fähigkeit / Produktverhalten | benötigte Organe/Wege | Aktueller Proof-Level (Stand Korrektur) | Endkriterium |
|---|---|---|---|
| Lokales Chatten/Planen | C/JEF, C3, B1/B2, Runtime | Age-0-Code/Harness vorhanden; volle Zielqualität nicht bewiesen | native Android-Inferenz, gestaffelte Offers, echte Antwort, Messungen |
| Wahrnehmen (Text, visuell, akustisch, Geräteereignisse) | A0–A5, SourceRef, A/B/C | Text teilweise; Vision/Audio und Android-Sensoren offen | getypte, zeitgestempelte und permissioned PerceptPackets bis JEF |
| Sprechen & Zuhören | RAW EAR, ASR reference, C3, C7 speech decoder/TTS | **OFF/UNVERIFIED** | Test mit lokaler Audio-I/O, Full-Duplex und Langzeitlernen |
| Gedächtnis & Welt-/Selbstmodell | T8, ContextOS, WorldJEPA, Selbstmodell | synthetische SQLite/JEPA-Proofs; Vollständigkeit offen | erlebte Task-Historie, Quellenlöschung, Langzeitnutzen, Restart |
| Lernen & organübergreifende Plastizität | JEPA/EMA, Replay, B1/B2/C3/Control Optimizer | einige synthetische Gradienten-/Holdout-Belege; aktive GGUF-/Cross-Organ-Lernfähigkeit offen | echte Deltas, Nutzen, Retention, Rollback, mobile Training-Proofs |
| Handeln über Android-APIs im Hintergrund | C5/C7 Action Broker, Android Companion + OS tools | **OFF/UNVERIFIED**, synthetischer Broker kein Android-Executor | erlaubter App-Task ohne unnötige UI-Clicks, auditierter Outcome |
| Android-Oberfläche bedienen | A-UI perception, Accessibility/optional Screen, C5/C7 | **OFF/UNVERIFIED** | realer genehmigter UI-Task auf Redmi und Stop/Restart |
| Dauerhaft arbeiten und proaktiv Aufgaben bearbeiten | JEF/Task-Graph, Scheduler, Events, Wake/Halt, Budgeter | Gesamtpfad UNVERIFIED | Android-lifecycle-konforme Jobs, Ressourcengrenzen, Abbruch, kein verstecktes Dauerrecording |
| Fehler erkennen und sich selbst verbessern | Judge, Feedback, Self-World, Error×Eligibility×Modulation, approved cross-organ edits | SHADOW/Research | Sicherheits- und Retentionsbewiesene eigene Verbesserung statt prompt-only Tuning |
| Sichere Lebensdauer und Gerätetauglichkeit | Installation/Update, F7 Budget, Logging, GATES, Rollback, Termux/Companion | einzelne Teile vorhanden, Redmi-E2E offen | Android 13/aarch64 Test, RAM/Leistung/Temperatur/Batterie, Zustimmungs-Grenzen |

Statuswerte: **CODE / WIRED / TESTED_SYNTHETIC / TESTED_NATIVE_ANDROID / ACTIVE** separat; keine Übertragung von synthetischem Linux-CI auf Android.

## 5. Arbeitsaufträge, ohne zusätzlichen angeblich aktiven Agenten
- **Core & Harness:** Background-API capability registry und Android companion/executor *zusätzlich* zur UI-Route; C5/JEF-Plan→Broker→T8/Outcome vollständig verbinden. Das bestehende lokale Android-Chat-Runtime-Ziel bleibt primär.
- **Perception/Research:** RAW EAR/Audiodaten + asynchrones Signal-/Zeit-/Quellen-Schema, später A5-Audio-PerceptPackets; Android-spezifische erlaubte Event-/UI-Observation ergänzen. Keine Gleichsetzung von Audio mit Transcript.
- **JEPA/Memory:** Audio/Speech-Episoden, A/B/C-Lernkontrakte und trainierbare Speech-/Ear-Adapter schrittweise über echte Quellen und Retention integrieren; prüfe #1741 Cross-Organ-Scope.
- **QA/Android:** echte Android-13-Permissions, Android-Hintergrund-Beschränkungen, Stop/Resume sowie Audio-Echtzeitlatenz/Budget testen, ohne Handyzugriff vorzutäuschen. Synthetische E2E-Tests jetzt.
- **Boss/Integration:** täglich das komplette Systemziel anhand dieser Matrix und aller Nutzer-Nachträge abgleichen; fehlende VOICE_AUDIO- und ANDROID_BACKGROUND_CONTROL-Reihen in Arbeitsledger führen. In funktionalen Slices arbeiten, nicht im UI-Broker oder CI-Hardening stecken bleiben.

## 6. Quellen und offene Grenzen
Projektinterne Primärquelle: `v13/code/docs/canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` (§4A.2–4A.5, §18.10, STEP9, G10C/D). Ältere Nutzervorgaben nennen Audio→Features/Latent, lernfähige langsam adaptive Parameter, schneller C3/JEF-Sprechpfad; genaue Stimme/Accent/Personalization nicht vom Nutzer spezifiziert, deshalb keine erfundene feste Stimmidentität. §18.11 und STEP8→9 erlauben inkrementelle Sequenz, aber Voice darf nicht aus dem Completion-Ledger verschwinden.

Android-Primärdokumentation zur späteren API-Implementierung:
- https://developer.android.com/develop/background-work/background-tasks/bg-work-restrictions
- https://developer.android.com/guide/components/activities/secure-bal
- https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start

**Kein externer Modell-/Codec- oder TTS-Lizenzentscheid** ist mit diesem Nachtrag getroffen. Vor Integration einzelner Modelle/Tools jeweils Modellkarte/Lizenz/Android-Lauffähigkeit prüfen.
