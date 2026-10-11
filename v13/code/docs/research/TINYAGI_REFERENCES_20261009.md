# Tiny AGI / Tiiny-AI — Prüfung der Originalquellen, 2026-10-09

Die Schreibweise im Nutzerhinweis ist mehrdeutig. Drei unterschiedliche
Projekte wurden getrennt geprüft. Diese Notiz ändert die SSOT nicht und
aktiviert weder zusätzliche Modelle noch native Lern-/Receiver-Rechte.

## TinyAGI: Agenten-Orchestrator

Original: https://github.com/TinyAGI/tinyagi

Beschreibt getrennte Agenten-Workspaces, persistente Sitzungen, eine
transaktionale SQLite-Queue und Retry/Dead-Letter-Verarbeitung. Diese
Mechanismen passen zu bestehenden V13-Queue-/Provenance-Komponenten.
Sie belegen keine gemeinsame neuronale Repräsentation und kein Body-Training.
Kein zusätzlicher Orchestrator wird eingebaut.

## tinyAGI: biologischer CPU-Lernansatz

Original: https://playwithagi.com/
Autorprofil: https://huggingface.co/rootxhacker

Die Seite beschreibt eine Kombination aus Spiking Neural Networks und
Liquid Time-Constant Dynamics, Surprise-Signalen sowie Transfer/Retention.
Ihre kleinen Versuche und die dort selbst angegebenen schwächeren
Klassifikationsergebnisse reichen nicht als Beleg für einen Ersatz unserer
vortrainierten Sprachmodelle. Code-/Modellveröffentlichung wird auf der Seite
angekündigt; ein reproduzierbares, veröffentlichtes tinyAGI-Paket konnte
daraus nicht bestätigt werden. Interesse besteht an zeitabhängigen Zuständen
innerhalb bestehender Self-/World-/F4-Komponenten, mit getrennten Ablationen,
Fehlern und Retention statt automatischer Übernahme von Leistungsbehauptungen.

## Tiiny-AI: Sparse-Inferenz auf kleinen Geräten

Originale:
https://github.com/Tiiny-AI/PowerInfer
https://github.com/Tiiny-AI/PowerInfer/blob/main/smallthinker/README.md

SmallThinker beschreibt ReLU-bedingte Sparse-Berechnung, Router-Vorauswahl
und begrenzte Experten-Caches. Das ist für den bestehenden Sparse-Body-Port
interessant. Der dokumentierte Android-Build verwendet NDK API34 und
ARMv8.6; der speicherbegrenzte Termux-Pfad kann laut eigener Anleitung Root
benötigen. Gerätespezifische Voraussetzungen sind auf unserem Redmi nicht
nachgewiesen. Veröffentlichte Geschwindigkeiten anderer Geräte sind keine
V13-/Redmi-Messwerte. Der aktuelle gepinnte LFM/Needle-Runner bleibt erhalten.

Nächster sinnvoller Vergleich: eigener optionaler Sparse-Body-Kandidat im
bestehenden BodyPort, fest gebundene Revision/Lizenz/Quantisierung, tatsächlich
gemessene Speichergrenze, exakte Vergleichsantworten und getrennte native
Tap-/Train-Fähigkeiten. Sparse-Inferenz allein schließt die B3- und
TrainRunnerProof-Gates nicht.
