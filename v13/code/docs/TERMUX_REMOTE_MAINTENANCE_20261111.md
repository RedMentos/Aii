# V13 Android/Termux – sicherer KI-Fernwartungszugang (2026-11-11)

**Status:** SHADOW / REVIEW_ONLY. Code prüft und staged signierte Patches, aber startet KEINEN Listener, installiert nichts und gibt niemandem Zugang zum Android-Gerät. Redmi, Live-Zugriff und Berechtigungspfad UNVERIFIED.

## Produktanforderung

Berechtigte KI-Entwickler (ChatGPT, Claude, Codex usw.) sollen die lokal in Termux laufende V13-Installation künftig lesen/diagnostizieren, Patches prüfen, Tests starten und nach gesonderter Nutzerfreigabe kontrolliert aktualisieren oder zurückrollen können. **Android ist das Zielgerät.** Jede KI benötigt ihre **eigene** widerrufbare Identität und begrenzte Berechtigungen. Eine zufällige Adresse ist keine Sicherheitskontrolle; niemals einen gemeinsamen Master-Schlüssel verteilen oder einen öffentlichen Port mit frei zugänglicher Termux-Shell öffnen.

## Zwei Wege: Pull-Bridge vor Live-API

**A. GitHub-Pull-Brücke (bevorzugt als erster sicherer End-to-End-Weg):** KI erstellt PR/Commit/Bündel auf GitHub. Ein explizit eingeschalteter lokaler Termux-Wartungsagent lädt nur fest konfigurierte GitHub-Commit-/Blob-Hashes, verifiziert zusätzlich die Agent-Signatur, führt eine Vorschau/Tests im separaten Staging aus und zeigt dem Nutzer einen Freigabedialog. Nach Approval erfolgt später erst das atomare Update mit Wiederherstellungspunkt. Kein öffentlich erreichbarer Server auf dem Handy nötig. Die GitHub-Poll-Implementierung und die lokale Approval/Apply-Komponente fehlen noch: OFF.

**B. Direkter privater Kanal (optional):** Android-Tailscale/WireGuard als privater Netzpfad und **normales Termux OpenSSH sshd**, auf einen eingeschränkten, festen Command-Broker beschränkt. Tailscale SSH als integrierter SSH-Server ist aktuell nur für Linux/macOS-CLI geeignet und kann nicht einfach auf Android als Server eingeschaltet werden. Termux hat eigenen OpenSSH-Paketpfad; Port 8022 ist vorgesehen. VPN-Bindung, SSH-Schlüssel, Android-Hintergrundbetrieb und Zugriffsrechte müssen vor Aktivierung auf dem konkreten Gerät geprüft werden. Kein Portforwarding, Passwortlogin, freie Shell, TTY, Agent-Forwarding oder unbekannte IPs.

Quellen: https://tailscale.com/docs/features/tailscale-ssh ; https://github.com/termux/termux-packages/blob/master/packages/openssh/sshd_config.patch ; https://docs.oracle.com/en/operating-systems/oracle-linux/openssh/openssh-ConfiguringtheOpenSSHServerForUserAccess.html ; https://developer.android.com/develop/background-work/background-tasks/bg-work-restrictions

## Rechte und Trust Boundary

- Identitäten trennen: private VPN-/SSH-Zugangsdaten ≠ Ed25519 Patchsignatur ≠ lokale Zustimmung zum Ausführen/Anwenden.
- Rechte je Agent: STATUS_READ, SANITIZED_LOGS_READ, PATCH_STAGE, TEST_SANDBOX, HUMAN_APPROVED_APPLY, ROLLBACK. Keine impliziten Berechtigungen durch LLM-Ausgabe oder ein boolesches Approval.
- Agent-eigene Schlüssel auf seinem vertrauenswürdigen Gerät erzeugen und sicher speichern; **niemals private Schlüssel, Bearer-Tokens, geheime Adressen oder vollständige Geräte-Logs in PR, Chat oder Modell-Kontext einfügen**.
- Verifizierende öffentliche Ed25519-Schlüssel liegen in einer Keyring-Datei außerhalb des von Fernagenten beschreibbaren Projekts. Veränderungen daran brauchen eine unabhängige Android-Companion- oder lokale Bedienfreigabe.
- Die normale Termux-UID kann ihre eigenen Dateien bearbeiten. **Wer bereits volle Shell-Rechte derselben UID besitzt, könnte den Patchguard umgehen**. Ein wirklicher sicherer Wartungszugang darf daher nur einen eingeschränkten Command-Broker erlauben und lokale Freigabe/Schlüsselhaltung aus der fernsteuerbaren Trustzone auslagern.
- Nutzer kann jede Sitzung stoppen. Alles protokolliert, sensitive Operationen getrennt autorisieren; bei Neustart keine Wiederverwendung alter Grants.

## Schon implementiert – prüfbares signiertes Staging

Neue Dateien:
- v13/code/v13/termux_patch_staging.py
- v13/code/tests/test_termux_patch_staging.py
- .github/workflows/v13-termux-signed-patch-staging.yml

Der Reader verarbeitet einen Bundle-Ordner mit:
- manifest.json = original signierte Bytes
- manifest.sig = 64 rohe Bytes einer Ed25519-Signatur
- files/v13/code/v13/example.py = Patch-Inhalt

Signed manifest fields: schema = v13.termux.patch-staging/1, agent, nonce (32 hex), base_commit (40 hex), target_commit (40 hex), expires_at (Unix-Sekunden), files (Liste mit path, before_sha256 oder null, after_sha256, size). Die lokale Trust-JSON hat die Struktur agents: {agent-id: {public_key_b64: raw_ed25519_publickey_base64, allowed_prefixes: [v13/code/v13/]}}; ausschließlich öffentliche Schlüssel. 

Der CLI-Test kann nach manuell vorbereiteten Verzeichnissen so ausgeführt werden:

    pkg install python python-cryptography
    python -m v13.termux_patch_staging \
      --bundle "$HOME/v13-inbox/bundle1" \
      --trust-file "$HOME/.v13-private/agents-public.json" \
      --installed-root "$HOME/V13-source" \
      --installed-commit "<lokal verifizierter 40-Hex-Git-SHA>" \
      --staging-root "$HOME/v13-review"

Keine Key-Generierung oder echte Verbindung wird automatisch angelegt. Überprüft werden Agent-ID/öffentlicher Prüfschlüssel, Signatur, beschränkter Pfad/Dateityp, vorherige SHA256, neue SHA256, Quoten, Symlinks, Datum (<= 3600 Sek.), exakter installierter Commit und unterschiedliche Zielversion. Danach werden Dateien ausschließlich in ein neu erzeugtes privates Review-Verzeichnis kopiert und ein Receipt mit status STAGED_REVIEW_ONLY_NOT_INSTALLED geschrieben. Runtime und Android sind unverändert; kein importierter Patch-Code wird ausgeführt.

**Teststand:** 21 lokale synthetische pytest-Fälle mit cryptography 46.0.4 PASS. GitHub-CI auf neuem Head separat verifizieren. Keine nativen Redmi-Tests behaupten. Die Ed25519-Bibliothek ist ein zusätzlicher Termux-Paketbedarf, daher vor Installation Lizenz/Paket-Version über offiziellen Termux-Index bestätigen.

## Was noch NICHT geliefert ist

1. Vertrauenswürdige Android-seitige Keyring-Verwahrung, lokale Zustimmung, Anti-Replay-Nonce-Datenbank und Stop-/Entzugssignal.
2. Verschlüsselter Transport: GitHub-PR/Artefakt-Lesezugang oder geprüfter privater VPN-/SSH-Tunnel; keine öffentliche API und kein Passwort-Server.
3. Fest definierte STATUS/DIAGNOSE/READ/PATCH_STAGE/TEST/REVIEW/APPLY/ROLLBACK-Endpunkte mit unabhängigen Agent-Scopes, Zeitbudget, Resource Guard und begrenzter Dateiauswahl.
4. Sicherer Checkout mit Git-Commit-/Blob-Bindung; das target_commit im signierten Manifest ist aktuell nur eine signierte **Behauptung**, kein unabhängig geprüfter GitHub-Beleg. Der installed_commit muss vertrauenswürdig lokal gelesen werden, nicht vom fremden Agenten frei gesetzt.
5. Explizite Nutzerbestätigung an exakt gezeigten Patch/Diff/Hash binden; temporäre Arbeitskopie testen; Backup/atomare Aktivierung/Healthcheck/automatischer Rollback nach Fehlstart.
6. Android-13-Hintergrund- und Akku-Grenzen, VPN-Lifecycle, UI-Approval und Native-Erreichbarkeit auf dem Redmi messen. Kein Modell darf die lokale Zustimmung selbst vortäuschen.
7. Kein Upload privater Rohdaten nach GitHub. Diagnose-Export nur redigiert und vom Nutzer freigegeben.

Status: PATCH_SIGNATURE_VERIFY = TESTED_SYNTHETIC; PATCH_STAGING = TESTED_SYNTHETIC; REMOTE_POLL=OFF; REMOTE_SSH=OFF; APPLY=OFF; ROLLBACK_REMOTE=OFF; ANDROID_VERIFIED=OFF.

**Weiterer Ownership:** Core baut den begrenzten Transport und Android-Companion-Approval, QA prüft Missbrauch/Abbruch/Restart, Boss integriert sichere GitHub-Handoffs, JEPA verarbeitet keine Geheimnisse oder synthetische Patch-Auditdaten als Lerndaten, Perception übernimmt nur ausdrücklich genehmigte UI-Statusdaten. Alles auf eigener PR-Basis; kein Blindmerge.
