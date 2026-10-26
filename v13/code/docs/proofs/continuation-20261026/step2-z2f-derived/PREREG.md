# Vorregistrierung WP-Z2f: Körper-Frage fest aus der aktuellen Nachricht gebildet (2026-10-26)

Vor jeder Inferenz geschrieben und gepusht. Linux-Cloud, gleiche Modelle/Runner wie Z2b–Z2e, kein Redmi.

## Frage
WP-Z2e: Eine allgemeine Frage hilft nicht (+.03), die STEP2-spezifische schon (+.33). Der Gewinn kommt vom Benennen dessen,
was gebraucht wird. Kann eine feste, nicht generative Regel das Benötigte aus der Nachricht selbst benennen?

## Änderung (Schalter, Standard aus)
`cfg body_question_mode='derived'` mit `v13/bodyq.py`. Die Regel findet benannte Dinge (zwei großgeschriebene Wörter,
z. B. „Option A“, „Project Kestrel“) und Phrasen, auf die die Nachricht zurückzeigt („the earlier project rules“,
„the latest supplier data sheet“). Daraus baut sie je eine B1- und B2-Frage. Findet sie nichts, gilt die allgemeine
Z2e-Frage. Ein Text in `body_question_b1/_b2` und ein Rückfrage-Fokus haben Vorrang. Kettenglied
`integrated_candidates.body_question_derived`, Tests `tests/test_bodyq.py`.
Offenlegung: Die Regex-Regeln habe ich an den Texten der Z2-Episoden geprüft (Ausgabe der Regel, keine Modell-Antworten).
Die Seeds sind frisch.

## Aufbau
`scripts/step2_z2f_derived.py` (gleiche Mechanik wie Z2e), Seeds **26/27/28**, Arme C (keine Frage),
CL (spezifische Z2b-Fragen), CD (abgeleitete Frage).

## Entscheidungsregel (fest)
DERIVED_QUESTION_SUPPORTED genau dann, wenn (1) CD − C Mittel > 0 mit 95-%-KI-Untergrenze > 0 (Cluster-Bootstrap über
Episoden), (2) CD − CL Mittel ≥ −0,05, (3) 0 falsch festgelegte Werkzeug-Zeilen in CD.

## Grenzen
Nur STEP2-Episoden (englisch, „Option A/B“-Wortform). Ob die Frage im normalen Chat hilft oder stört, misst das nicht.
