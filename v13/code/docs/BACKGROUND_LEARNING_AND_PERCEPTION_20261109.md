# Hintergrundlernen, Ressourceneinsatz und erlaubte Wahrnehmung

## Nutzerziel vom 09.11.2026

Smooth/V13 soll später auch zwischen direkten Anfragen weiterarbeiten und
lernen können, bei Bedarf in einem langsamen, ressourcenschonenden Modus.
Langfristig soll es aus Erfahrung mitlernen, **wann und wie viel Rechenzeit**
für welche Aufgabe oder welchen Lernpfad sinnvoll ist. Es soll anfänglich
geeignete Daten erhalten und im Gebrauch aus freigegebenen Gesprächen und
Rückmeldungen lernen. Werkzeuge und Wahrnehmung, beispielsweise der Bildschirm,
sollen bei ausdrücklicher Erlaubnis hinzukommen. Innerhalb der gesetzten Grenzen
soll das System mit zunehmender nachgewiesener Fähigkeit selbstständiger werden.
Die weitergehenden Wahrnehmungs- und Autonomiefähigkeiten sind ein späteres
Ausbauziel; sie ersetzen nicht die noch offene Fertigstellung des Kernsystems.

Dies ergänzt den bestehenden Canon und die
[Gesamtscope-Notiz](V13_WHOLE_SYSTEM_LEARNING_CONTINUITY_20261108.md); es ist
kein Nachweis, dass diese Fähigkeiten bereits funktionieren oder aktiviert
sind. Die Nutzerformulierung ist hier sinngemäß als Projektziel festgehalten.

## Einordnung im vorhandenen System

* `SleepRuntime` und `EventScheduler` planen bereits bestimmte Arbeiten bei
  Leerlauf; `ResourceGuard`, Abbruch und Warteschlange liefern Bausteine. Ein
  durchgehend wirksames, gelerntes Hintergrundbudget und sein Nutzen sind damit
  noch nicht nachgewiesen. Bestehende `:stillstand`-, Pause- und Age-Regeln
  bleiben wirksam.
* Erfahrungen, Korrekturen, Replay und Konsolidierung gehören in die bestehenden
  F1/F5-/Experience-/Sleep-Pfade; die getrennten Kandidaten #1631, #1632 und
  #1640 liefern Teile der technischen und nutzerbezogenen Rückmeldung. Sie sind
  noch nicht als vollständiges lernendes System zusammengeführt.
* Screen ist im Modalitätenregister vorgesehen und standardmäßig aus; das ist
  noch kein funktionsfähiger Bildschirmzugriff. Wahrnehmung, Verstehen und eine
  Aktion auf dem Bildschirm sind getrennte Fähigkeiten. Das Werkzeug soll die
  vorhandene Wahrnehmungs-/Workspace-/Weltmodellarchitektur nutzen.

## Umsetzungsweg nach den jeweiligen Kernvoraussetzungen

1. **Ruhiger Hintergrundmodus:** Einen bewusst aktivierbaren, unterbrechbaren
   Scheduler für kurze Arbeitspakete auf bestehende Sleep-/Replay-Jobs und
   Ressourcenüberwachung aufsetzen. Beginnen mit einem festen, vom Nutzer
   einstellbaren Budget für Zeit, Speicher und Gerätebedingungen; bei fehlenden
   Messwerten konservativ pausieren. Neue Anfragen, Pause und Stillstand haben
   Vorrang. Checkpoints und Wiederaufnahme müssen auch nach Prozessende stimmen.
2. **Bedarf lernen:** Zuerst nur im Schatten vorschlagen, ob und wie viel
   Hintergrundzeit einem Organ oder einer Aufgabe hilft. Den Vorschlag später
   innerhalb der bereits festgelegten Obergrenzen anwenden, wenn Vergleich und
   Retention ihn tragen; bei fehlender oder schlechter Evidenz zum festen
   Budget zurückfallen. Das System darf seine Grenzen nicht selbst erhöhen.
3. **Geeignete Lerndaten:** Anfangsdaten mit Herkunft, Lizenz, Revision und
   getrennten Prüfaufgaben auswählen; danach zugelassene Gespräche, explizite
   Korrekturen und beobachtete Werkzeugergebnisse über die bestehenden
   Quellen- und Lernberechtigungen einbeziehen. Aufzeichnen, Erinnern und
   Gewichtslernen bleiben unterscheidbar; spätere Korrektur oder Löschung muss
   die abhängigen Lernstände nachvollziehbar beeinflussen können.
4. **Erlaubte Wahrnehmung und Werkzeuge:** Nach Aufbau der Kernpfade einen
   begrenzten Bildschirmlese-Pfad als eigene Fähigkeit mit sichtbarem Zustand,
   ausdrücklicher Nutzerfreigabe, abschaltbarem Umfang und Quellenbindung
   entwickeln. Eine Freigabe zum Sehen ist nicht automatisch eine Freigabe zum
   dauerhaften Speichern, Lernen, Weitergeben oder Bedienen. Werkzeugaktionen
   bleiben an die jeweils erteilten Rechte und die bestehenden Age-/Aktions-
   und Rücknahmewege gebunden.
5. **Schrittweise Selbstständigkeit:** Eigene Vorschläge und später begrenzte
   Aufgaben innerhalb der Nutzer- und Entwicklungsgrenzen mit messbaren
   Erfolgs-/Fehler- und Rücknahmepfaden erweitern. Wachstum einer Fähigkeit
   überträgt ihre Berechtigungen nicht automatisch auf andere Fähigkeiten.

## Nachweis vor breiter Nutzung

Mit festen, vorab dokumentierten Tests vergleichen: ohne Hintergrundlernen,
festes kleines Budget und gelernter Budgetvorschlag bei gleichem Arbeits- und
Datensatzbudget. Antwortlatenz, Abbruchzeit, RAM, Akkustand/Temperatur, Energie
sofern verfügbar, tatsächlichen Lernfortschritt und Vergessen messen. Gespräche
und Bildschirmereignisse auf Quelle, Erlaubnis, Aktualisierung, Löschung und
Neustart prüfen; für Screen getrennt Lesbarkeit, Scope und Ein-/Ausschalten
testen. Linux-/synthetische Ergebnisse und echte Redmi-/Android-Messungen
getrennt festhalten. Android kann Hintergrundprozesse pausieren oder beenden;
die Wiederaufnahme muss deshalb geprüft werden, ein dauerhaft laufender Prozess
wird nicht vorausgesetzt. Keine der Messungen ersetzt die ursprünglichen Gates.
