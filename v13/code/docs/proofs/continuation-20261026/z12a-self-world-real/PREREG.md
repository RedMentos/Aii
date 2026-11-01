# WP-Z12a Vorregistrierung: G-SELF-WORLD-005 mit echten statt synthetischen Fällen (vor dem Lauf committet)

Frage: Unterscheidet das echte Selbstmodell (`v13/selfmodel.py`, SelfCorollary + attribute) eigene Wirkungen von
Wirkungen einer unabhängigen Welt, wenn beide echt auf dieselben Dateien wirken? Bisher gab es nur die sechs Fälle als
Unit-Tests mit erfundenen Beobachtungen.

Aufbau (`code/scripts/z12a_self_world_real.py`, unverändert für den Lauf):
- Self: echter WP-K-Weg `ToolRegistry.call('sandbox_note')` → PROPOSED mit Vorschau → Freigabe → Transaktion →
  echte Datei in `data/tool_sandbox`. Vor jeder Freigabe eine SelfCorollary aus der Vorschau (Inhalts-Hash der
  Zieldatei, Status EXECUTED, bei CREATE der erklärte Nebenkanal `listing`), Fenster 0,4 s.
- Welt: eigener Betriebssystem-Prozess mit eigenem Zeitplan, schreibt, blockiert (Verzeichnis statt Datei) und
  entfernt Dateien im selben Ordner. Beobachter-Thread liest den Ordner alle 20 ms und gibt jede Änderung zum Zeitpunkt
  des Sehens an `SelfSystem.observe()`.
- Wahrheit nur aus den beiden Schreib-Protokollen (Hashes), nie aus dem Klassifikator.
- Episoden-Arten je 1/7: own, world, interference (Welt überschreibt das eigene Ziel 0–300 ms danach), fail (Welt legt
  vorher ein Verzeichnis auf das Ziel, das eigene Schreiben scheitert echt), ambiguous (zwei eigene Vorschläge mit
  gleichem Inhalt), side_effect (eigenes CREATE ändert die Liste), delayed (Freigabe nach 1,25–2,75 Fenstern).
- Seeds 61, 62, 63, je 70 Episoden (2 s je Episode).
- Kontrollen auf denselben Beobachtungen: ohne Corollary (`attribute([], obs)`) und nur Zeit (offene eigene Aktion auf
  dem Kanal = SELF).

Kriterien (`Z12A_SELF_WORLD_REAL_PASS` nur wenn alle gelten):
- K1 Welt-Änderungen an Dateien als SELF gelesen ≤ 5 %.
- K2 eigene Änderungen (ohne ambiguous, inkl. delayed) als EXTERNAL gelesen ≤ 5 %.
- K3 Status FAILED einer echt gescheiterten eigenen Aktion als MIXED ≥ 90 %.
- K4 ambiguous als UNCLEAR ≥ 90 %. K5 eigener Listen-Nebeneffekt als UNCLEAR ≥ 90 %.
- K6 Kontrollen schlechter: ohne Corollary mindestens 50 Punkte mehr eigene Änderungen als EXTERNAL; nur Zeit
  mindestens 20 Punkte mehr Welt-Überschreibungen (interference) als SELF.
Beobachtungen mit unklarer Wahrheit (`unknown`/`both`) werden gezählt und nicht bewertet.

Grenzen (vorab): Vorhersage ist hier ein exakter Inhalts-Hash, das macht die Zuordnung leicht; geprüft wird vor allem
der echte Ablauf (Zeit, Wettläufe, verpasste Zwischenstände, echte Fehlschläge). Kein Sprachmodell, keine Handy-Sensoren,
keine Körper-JEPA (das ist WP-Z12b). Cloud-Zeiten.
