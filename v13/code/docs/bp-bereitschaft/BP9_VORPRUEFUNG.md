# WP-BP9 Vorabueberlegung (Denk-vor-Test-Regel), 2026-11-01

**Frage:** Lohnt jetzt ein Test typisierter Modulatoren (G-MODULATOR-SPECIFICITY-001) an echten Updates?

**Antwort: nein, noch nicht.** Der einzige Laufzeit-Lerner mit Einzelgewichten ist der Route-Kopf (KL-Reihe). Er lernt nur aus
menschlichen Korrekturen, also aus *einer* Quellenart. Typisierte Einzelgewichte (`neuromod.sample_factor`, Zweig 8pfwut) brauchen
Updates aus mindestens drei Quellen (Selbst, Mensch, Ergebnis). Ohne gemischte Quellen gibt es nichts zu unterscheiden, der
sichtbare Gewinn ist null. Z6j/Z6k (FAIL) wurden an diesem Mangel gemessen, nicht an der Idee.

**Voraussetzung (kommt aus BP2):** jedes Gewichts-Update traegt ein Etikett `quelle in {selbst, mensch, ergebnis}` und einen
Zustand (Neuheit, Fehler, Sicherheit). BP2 muss diese Etiketten im Alltag liefern.

**Schnittstelle, damit BP9 danach sofort messen kann (nur Vertrag, kein Code):**
1. BP2-Lerner ruft vor jedem Update `faktor = neuromod.sample_factor(quelle, zustand)` und multipliziert die Lernrate.
2. Sicherheits-Veto bleibt vor dem Faktor (Verbote, Notaus).
3. Messung dann: gleiche Updates, Arme {kein Faktor, Pfad-Tor, Einzelfaktor, Gradient gleiches Budget}, 20 frische Saaten, vorregistriert.

**Nicht erneut testen, bis BP2 gemischte Quellen liefert.**
