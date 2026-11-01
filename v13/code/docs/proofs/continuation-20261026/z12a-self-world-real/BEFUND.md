# WP-Z12a Befund: Selbst/Welt mit echten Fällen — `Z12A_SELF_WORLD_REAL_PASS`

Vorregistriert in `PREREG.md` (vor dem Lauf committet und gepusht). Skript `code/scripts/z12a_self_world_real.py`,
Daten `v13/bench-results/z12a-self-world-real-20261026/z12a.json`. Seeds 61/62/63 × 70 Episoden, 510 Beobachtungen,
Wahrheit aus den Schreib-Protokollen, 0 Beobachtungen mit unklarer Wahrheit.

| Kriterium | Wert | |
|---|---|---|
| K1 Welt-Änderung als SELF gelesen | 0/93 | PASS |
| K2 eigene Änderung als EXTERNAL gelesen | 0/117 (delayed 30/30 SELF) | PASS |
| K3 echt gescheiterte eigene Aktion → MIXED | 30/30 | PASS |
| K4 zwei gleiche eigene Vorschläge → UNCLEAR | 30/30 | PASS |
| K5 eigener Listen-Nebeneffekt → UNCLEAR | 30/30 | PASS |
| K6 Kontrollen | ohne Corollary 117/117 eigene Änderungen als EXTERNAL; nur Zeit 29/29 Welt-Überschreibungen als SELF (mit Corollary 0/29) | PASS |

Urteil: **`Z12A_SELF_WORLD_REAL_PASS`**. 296 Modulator-Pakete `world_prediction_error` aus den Abweichungen.

Was das zeigt: Auf echten Datei-Aktionen über den echten Werkzeug-Weg, gegen einen unabhängigen zweiten Prozess, trennt
die Corollary eigene von fremden Wirkungen ohne Fehler, und beide Kontrollen versagen genau dort, wo man es erwartet
(ohne Kopie wird alles Eigene „fremd“; nur nach Zeit wird jede fremde Überschreibung „eigen“).
Echter Wettlauf beobachtet: bei interference sah der Beobachter den eigenen Zwischenstand 27/30 und die fremde
Überschreibung 29/30 Mal; die übrigen Zustände lagen zwischen zwei Abfragen (20 ms) und blieben unsichtbar.

Grenzen: Die Vorhersage ist ein exakter Inhalts-Hash, das macht die Zuordnung einfach; die Leistung liegt im Ablauf,
nicht in einem gelernten Vorhersager. Kein Sprachmodell, keine Handy-Sensoren, Cloud-Zeiten. G-SELF-WORLD-005 hat
damit echte Fälle (real_data); der gelernte Teil (handlungsgeerdetes World-JEPA, Körper-JEPA) ist WP-Z12b.
