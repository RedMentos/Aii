# Vision-Lab Schritt 3 (WP-T16, 2026-10-10, Pakete A)

Skript `code/scripts/vision_bench3.py`, Rohdaten `vision_bench3.json`, Lehrer-Beschriftungen `captions.json`.

Aufbau der Messung:
- **Lehrer:** echtes LFM2.5-VL-450M (Q4_0 + mmproj Q8_0) über `llama-mtmd-cli` b10964. 432 neue Aufrufe, 1,6 s pro Aufruf (Cloud-CPU, 4 Threads).
- **Text-Encoder:** hashed bag of words und EmbeddingGemma-300M.
- **Testlauf:** 4 Falten je Bild. Beim Testen wird der Lehrer **nie** gerufen.

Synthetische Szenen mit bekannter Wahrheit:
- 48 Einzelobjekte (die Szenen aus WP-N15)
- 48 Bilder mit zwei Objekten verschiedener Farbe und Form in zwei verschiedenen Quadranten

## Ergebnisse
| | hashed | EmbeddingGemma | Zufall |
|---|---|---|---|
| Einzelobjekt, Kachel-Suche (beste der 16 Kacheln in der richtigen Hälfte) | **1,00** | **1,00** | 0,25 |
| Einzelobjekt, Regionen-Suche N15b (beste Hälfte) | 0,67 | 0,60 | 0,25 |
| Zwei Objekte, Kachel-Suche (beste Kachel im richtigen Quadranten) | 0,72 | **0,79** | 0,25 (0,5 unter den auffälligen Kacheln) |
| Zwei Objekte, Regionen-Suche (bester Quadrant) | **1,00** | **1,00** | 0,25 |

**Lehrer.** Bei zwei Objekten nennt die Gesamtbeschreibung beide Farben in 100 % der Bilder, die Quadranten-Beschreibung die richtige Farbe ebenfalls in 100 %. Er halluziniert aber: Auf eine leere weiße Fläche antwortet er mit „black rectangle in the center“. Beschreibungen bleiben deshalb REFERENCE_NOT_FACT.

**Lehrer-Entfernung (Abhängigkeitskurve).** Gemessen bei zwei Objekten mit EmbeddingGemma: Anteil der vom Lehrer beschriebenen Trainingsbilder und die Kachel-Suche danach.

| Anteil | Bilder je Falte | ohne Selbsttraining | mit Selbsttraining |
|---|---|---|---|
| 1 | 36 | 0,79 | 0,79 |
| 1/2 | 18 | 0,79 | 0,79 |
| 1/4 | 9 | 0,74 | 0,74 |
| 1/8 | 4–5 | 0,58 | **0,66** |

Beim Selbsttraining bekommen unbeschriftete Bilder vom Schüler die nächstliegende bekannte Beschreibung als Pseudo-Label.

## Befunde
1. **Ausrichtung pro Kachel ohne Kachel-Beschreibungen funktioniert.**
   - Schwache Labels: Eine auffällige Kachel erbt die Beschreibung der kleinsten beschriebenen Region um sie herum, sonst bekommt sie BACKGROUND.
   - Damit findet der Schüler das Objekt in 16 Kacheln sicher. Das ist feiner und besser als die Hälften-Suche aus N15b.
2. **Mehrere Objekte:** Kacheln trennen sie zu 72–79 % (Zufall unter auffälligen Kacheln 50 %).
   - Die Quadranten-Suche ist hier perfekt (1,00), weil die Quadranten genau die Lehrer-Regionen sind und je ein Objekt enthalten.
   - Kacheln sind die allgemeinere Karte (16 Felder, beliebige Lage), aber auf dieser Aufgabe schlechter. Grund: Eine Kachel sieht nur einen Teil des Objekts, und die Form ist dort schwer zu erkennen.
3. **Lehrer-Entfernung:** Ein Viertel der Lehrer-Beschriftungen kostet nur 5 Punkte.
   - Erst bei einem Achtel bricht die Leistung ein.
   - Selbsttraining hilft genau dort (+7 Punkte, hashed +5) und schadet sonst nicht.

## Grenzen
- Nur synthetische Formen auf hellem Grund. Die Auffälligkeit wird gegen die Randfarbe gemessen, das funktioniert bei echten Fotos mit unruhigem Hintergrund schlechter.
- **Echte Fotos fehlen.** Sie brauchen die Erlaubnis des Nutzers (kleiner Satz, nichts aus dem Netz). Offen.
- Eine Saat, 4 Falten, n = 96 Abfragen je Zwei-Objekt-Zeile.
