# WP-T13: BodyPort, Bridge-Key, Body-Swap online (IH-H8, IH-H21, G2, G11). Übergabe von Pakete A, 2026-10-10

Code:
- `v13/bodyport.py` (neu: `Ports`, `BodySwap`, `:body`)
- Hooks in `runners.RunnerPool.get/_release`, `bodies.BodyFabric.path_override/revision_override`, `models.ModelManager.revision`

Tests: `tests/test_bodyport.py` (8, ohne echte Gewichte, mit dem FakeRunner aus `test_bodies`).

## BodyPort im Laufpfad (IH-H8)
Jede Körper-Rolle hat einen Port. Der RunnerPool meldet jeden echten Übergang:
- `ASSIGNED`: Runner angelegt, Prozess startet erst beim Laden.
- `READY`: Probe bestanden, `/health` ok.
- `RELEASED`
- `MODEL_CHANGE`: eine andere Gewichtsdatei für dieselbe Rolle.
- `FAILED`

Gespeichert werden je Rolle Zustand, Pfad, Revision, Bridge-Key und die Zähler loads/changes/failures. Dazu kommen die letzten 96 Übergänge im State `T13_BODY_PORTS`. Treffer, also derselbe Runner wiederverwendet, werden nicht gespeichert.

## Bridge-Key live (IH-H21)
Der Key ist sha256 über Rolle, Modell-ID, Revision, Datei-sha256, Dimensionen, Tokenizer und Fähigkeiten.

Bevor eine Rolle eine andere Datei bedient, prüft `Ports.model_change` live:
- B3-Bridge-Manifeste `b3/<SENDER>_TO_<EMPFÄNGER>.json`, deren sender- oder receiver_revision die alte Revision nennt, gelten als veraltet.
- Slot-Assets der Art `bridge` oder `latent_path` bekommen die Autorität `SHADOW_RECALIBRATE`.

Das Ergebnis steht in `T13_BRIDGE_KEYS` und unter `:body bridges`. `Ports.bridge_valid(direction)` ist streng: Es gibt nur dann True, wenn beide Seiten genau die Revision bedienen, für die die Bridge trainiert wurde. Veraltete Bridges fallen auf den konfigurierten SOURCE/EXACT-Kanal zurück. LATENT hat ohnehin Autorität 0.

## Body-Swap ohne Neustart (G11)
Ablauf mit `:body`:
1. `:body swap <Rolle> <gguf>`: GGUF-Prüfung und sha256, Kopie nach `models/swap/`. Danach wird über die AG0-Gates vorgeschlagen und auf SHADOW gesetzt.
2. `:body parity <Rolle> <alt.json> <neu.json>`: AG12-Achsen.
3. `:body ramp <Rolle>`: dreimal, Anteile 0,1 → 0,5 → 1,0. Während RAMP entscheidet der Turn-Schlüssel, welche Datei antwortet.
4. Nach dem letzten Schritt prüft eine Probe, ob die neue Datei lädt und `/health` antwortet. **Scheitert sie, folgt automatisch ein Rollback.**
5. `:body rollback <Rolle>`: geht aus jeder Stufe, auch nach ACTIVE. Das vorige Modell bedient wieder.

Alles wirkt beim nächsten `pool.get` ohne Neustart. `path_for` fragt den Slot, der Pool merkt die andere Datei, gibt den alten Runner frei und legt den neuen an. Ein fertiger Tausch überlebt einen Neustart, weil er im Slot-State steht. `models.revision(role)` meldet dann die neue Revision, damit Tap, LoRA und Bridges die alte nicht mehr anwenden. Ein eigener Tausch durch V13 braucht das Age-Recht `body_swap`.

## Grenzen / offen
- Die Probe zeigt nur „lädt und lebt“, nicht Qualität. Qualität prüft das Parity-Gate mit echter AG12-Auswertung.
- Wiederholtes Laden während RAMP (je Turn ggf. andere Datei) kostet Ladezeit. Auf dem Redmi ist das zu messen (WP-R).
- `installed` (models.json) bleibt beim alten Eintrag. Der Slot ist die Quelle der Wahrheit für den Tausch. `distinct_bodies` liest weiter `installed`.
