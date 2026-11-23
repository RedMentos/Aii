# WP-T11 Sleep-Rest: Hypothesen-Prüfung und Homöostase-Gate (§15.4–15.7, §16.2, §94.5, L8.2)

## Traum-Hypothesen gegen gespeicherte Quellen (`SleepCycle.validate_hypotheses`, `check_hypothesis`)
- Sleep B erzeugt wie bisher Hypothesen (ROUTE_ALTERNATIVE, SKILL_RECOMBINATION, WORLD_RELATION). Sie haben keine Fakt-Autorität (fact_write_authority 0). Neu: Am Ende jeder Sleep-B-Phase werden gequeuete Hypothesen geprüft (`DREAM.validation_required`, LOCKED true).
- **Anker:** Jede SourceRef muss noch lesbar sein und den richtigen Hash haben, sonst STALE/SOURCE_GONE. Jede genannte Erinnerung muss aktiv sein, sonst STALE/MEMORY_INACTIVE (etwa nach einer menschlichen Korrektur).
- **ROUTE_ALTERNATIVE:** Gespeicherte menschliche Routen-Entscheidungen zu ähnlichen Anfragen (gleicher Text oder `memory.relevance` ≥ 0,5). Mehr Belege für die Alternative ergeben SUPPORTED, mehr für die beobachtete Route CONTRADICTED.
- **SKILL_RECOMBINATION:** Die Routen der beiden Erinnerungen sind auseinandergelaufen → CONTRADICTED. Weitere ähnliche Anfragen mit derselben Route → SUPPORTED.
- **WORLD_RELATION:** Die Werte unterscheiden sich inzwischen → CONTRADICTED. Eine andere gespeicherte Erinnerung nennt beide Entitäten zusammen → SUPPORTED.
- **Sonst UNVERIFIED.** Solche Hypothesen werden höchstens täglich neu geprüft (`HYP_RECHECK_S`).
- **Ergebnis:** Je Prüfung ein ReplayItem-Paket (stage `SLEEP_B_VALIDATION`, outcome, Belege = Memory-IDs, fact_write_authority 0). CONTRADICTED und STALE scheiden aus der Queue aus. Die Prüfung schreibt nie Erinnerungen oder Fakten.

## Homöostase-Messung mit Gate (`v13/homeostasis.py`, in Sleep C)
- **Schnappschuss** der gelernten Steuerparameter: Attention-Gains, JEF-Brücke, Fast-Forward, C5-Modulatoren, Deliberation, Neuromod (langsame Spuren + META-Kopf) und Replay-Gains.
- **Messung** gegenüber der letzten Sleep C:
  - Drift (relative L2-Änderung, Nenner mindestens 0,05)
  - Sättigung (Anteil begrenzter Parameter auf einer Grenze)
  - tote Neuromod-Pfade (keine neue Aktivierung)
- **Gate** (BOOT-Werte): PASS, wenn Drift ≤ 0,5 und Sättigung ≤ 0,5 je Komponente; sonst FAIL mit Namen. Telemetrie `homeostasis_gate`.
- **Bei FAIL** hält `learn_slow` die AG6-Konsolidierung an (`consolidate_held = HOMEOSTASIS_GATE_FAIL`), bis eine spätere Sleep C besteht.
- **Grenze:** Homöostase misst nur und erzwingt keine Gleichverteilung. Native A/B/C-Gewichte sind hier nicht trainierbar und werden als UNAVAILABLE gemeldet, nicht als 0.

## Wake Replay (§94.5)
Schon vorhanden (WP-E): kurze Idle-Fenster reaktivieren hoch priorisierte Episoden und blockieren den Nutzer-Turn nie.

Tests: `tests/test_sleep_validation.py` (4).

## WP-U2 Homöostase-Regelung und Konflikt-Verifikation (§16.1, §16.2, §68)

**Regelung** (`homeostasis.regulate`, läuft in jeder Sleep C nach dem Gate). Für jeden N10-Lernpfad wird gezählt, was seit der letzten Sleep C passiert ist:
- Aktivierungen (LearningTrace) und ihr Anteil an allen Pfaden,
- Updates (PlasticityState-Pakete).

Daraus entsteht ein Ziel-Gain:
- **dominant:** Anteil > fair + (1 − fair) × `HOME.dominant_path_inhibition`, und mindestens 3 aktive Pfade → Ziel < 1.
- **tot, aber nützlich:** keine Aktivierung, Pfad war getaggt, stabil oder bestätigt → Ziel 1 + `HOME.dead_path_reopen`. Tote Pfade, die nie nützlich waren, bleiben unverändert, weil Spezialisierung erlaubt ist.
- **Update-Budget:** mehr Updates als der Mittelwert → Ziel × (Mittel/Updates)^`HOME.update_budget_normalization`.

Der Gain wandert pro Nacht um `HOME.activation_balance` Richtung Ziel und bleibt in [0,5; 1,5]. In der ersten Nacht wird nichts als dominant beurteilt, weil der Vergleich fehlt.

**Wirkung.** `neuromod.gate` zeigt `homeostasis.gain` immer an, multipliziert den Faktor aber nur im Modus ACTIVE. ACTIVE setzt nur der Mensch mit `:homeostasis active`; Standard ist SHADOW.

**Routen-Dominanz.** Eine C5-Route mit einem Anteil ≥ `HOME.router_collision_monitor` (ab 8 Stichproben) wird nur gemeldet (MONITOR_ONLY), nie korrigiert. `HOME.shared_representation_drift` bleibt unverbunden, weil es hier keine geteilte trainierbare Repräsentation gibt.

**Konflikt → erst verifizieren** (`META.conflict_verify_before_learn` = 0,80):
- Jeder Pfad sammelt stützende Belege (positive CONFIRMING-Kanäle) und widersprechende Belege (negative Kanäle, `repeated_failure`), jeweils gewichtet mit der Quellenklasse.
- Erreichen beide Seiten mindestens 0,2 und hat die schwächere Seite mindestens 80 % der stärkeren, ist `verify_first` aktiv: Gate-Faktor 0, `local_update` 0.
- Ein FINAL-Beleg aus `human_correction`, `real_deterministic_outcome` oder `primary_source` klärt den Konflikt. Sleep lässt beide Seiten abklingen.

**Befehle:** `:homeostasis [status|run|shadow|active]`.
**Tests:** `tests/test_homeostasis_regulation.py` (7).
**Grenze:** Alle HOME-/META-Werte sind BOOT-Werte aus §68 und nicht gemessen.
