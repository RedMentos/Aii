# Handy-Pflichtmessungen (WP-Z7) — ein Befehl für alle Messungen, die nur das Redmi kann

Ohne diese Messungen können STEP5, STEP7 und drei §100-Gates (G-TRAIN-RUNNER-PROOF-001, G-MOBILE-LONGRUN-001,
Teile von G-PROCEDURALIZATION-004) nicht grün werden. Die Cloud kann RAM, Wärme, Akku und echte Handy-Zeiten nicht messen.

## Starten (Termux)
Vorher: Handy ans Ladegerät, andere Apps zu, laufenden V13-Chat mit `:shutdown` beenden. V13 muss eingerichtet sein
(sonst startet die Einrichtung automatisch, ca. 0,9 GB Download).
```
cd ~/v13-werkzeug/V13-Phone      # dort, wo das neue Paket entpackt ist
bash HANDY_PFLICHT.sh            # Stufe kurz, etwa 4–8 Stunden, gut über Nacht
bash HANDY_PFLICHT.sh voll       # länger und genauer, etwa 1–2 Nächte
```
Abbrechen mit Strg+C (Lautstärke-runter + C). Fertige Schritte bleiben; derselbe Befehl macht beim nächsten Mal weiter.
Nur einzelne Schritte: `bash HANDY_PFLICHT.sh --nur ram,residenz`. Alles neu: `--neu`.

## Was gemessen wird (Reihenfolge)
| Schritt | Was | Wofür |
|---|---|---|
| ram | RAM aller drei Modelle einzeln und zusammen | WP-R, „braucht AGI 8 GB?“, §24.33 |
| residenz | 5 Reihenfolgen der Beobachter (B1 vor B2, B2 vor B1, gleichzeitig, erst Antwort dann beide, nur Stichprobe): Qualität, Zeit bis erstes Angebot, Antwortzeit, RAM je Prozess, Seitenfehler, Akku/Temperatur; dazu Steuer-Overhead | §24.33, §24.14 |
| wiederholung | 12 (voll 24) ähnliche Aufgaben in einer Sitzung: wird es schneller, ohne schlechter zu werden? | Proceduralization |
| werkzeug | Werkzeug-Vorhersage (wie das Werkzeug-Paket, Stufe kurz) | Werkzeug-Vorhersage aus SHADOW |
| langlauf | 2 (voll 7) simulierte Tage durch die echte Runtime mit echten Modellen: Neustarts, Weckreihenfolge, Gedächtnis, Wachstum der Datenbank | G-MOBILE-LONGRUN-001 |
| training | Trainings-Nachweis für den Teil, der auf dem Handy wirklich lernt (kleiner Routen-Kopf, kein Sprachmodell): Gradient, gleiches Ergebnis bei Wiederholung, Abbruch mitten im Lernen, Absturz beim Speichern, Fortsetzen, Rücknahme, Behalten, Zeit je Schritt, Akku/Temperatur | G-TRAIN-RUNNER-PROOF-001 |

## Ergebnis
`V13-Pflicht-Ergebnis-<Stufe>-<Zeit>.zip` in Downloads, darin `KURZ.txt` (deutsche Zusammenfassung), `paket-bericht.json`
und die Berichte jedes Schritts. Keine Modelle, keine privaten Chats (Aufgaben sind erfundene englische Testaufgaben).
Bitte die ZIP-Datei hier im Projekt hochladen. Ausgewertet wird danach in der Cloud gegen vorher festgelegte Regeln.

Messung; einzige Änderung: das Eignungs-Werkzeug wird eingeschaltet (deine Entscheidung vom 22.10.), es läuft bei Age 0 nur im Schatten. Keine Lernrechte vergeben (`authority: 0`).
