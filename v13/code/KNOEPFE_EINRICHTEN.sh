#!/usr/bin/env bash
# WP-UI1: V13-Knöpfe auf dem Startbildschirm (Termux:Widget).
# Legt vier Knöpfe an: V13 Chat, V13 Status (im Terminal) und V13 Notaus, V13 Stillstand (ohne Fenster).
# Notaus/Stillstand schalten nur EIN. Aufheben geht nur im Chat mit :notaus aus bzw. :stillstand aus.
# Aufruf in Termux:  bash KNOEPFE_EINRICHTEN.sh      (Entfernen: bash KNOEPFE_EINRICHTEN.sh weg)
set -Eeuo pipefail
V13_HOME="${V13_HOME:-$HOME/v13}"
SC="$HOME/.shortcuts"
BASH_BIN="${PREFIX:-/data/data/com.termux/files/usr}/bin/bash"
NAMES=("V13 Chat" "V13 Status" "tasks/V13 Notaus" "tasks/V13 Stillstand")

if [ "${1:-}" = "weg" ]; then
  for n in "${NAMES[@]}"; do rm -f -- "$SC/$n"; done
  echo "V13-Knöpfe entfernt. Das Widget zeigt es nach dem nächsten Aktualisieren."
  exit 0
fi

mkdir -p "$SC/tasks"
chmod 700 "$SC" "$SC/tasks"

write() {  # write <Name> <Inhalt>
  local f="$SC/$1"
  printf '#!%s\n%s\n' "$BASH_BIN" "$2" > "$f"
  chmod 700 "$f"
}

write "V13 Chat" "export V13_HOME='$V13_HOME'
command -v termux-wake-lock >/dev/null && termux-wake-lock
v13 chat
status=\$?
command -v termux-wake-unlock >/dev/null && termux-wake-unlock
[ \$status -eq 0 ] || { echo; echo \"V13 wurde mit Fehler \$status beendet. Enter schließt das Fenster.\"; read -r _; }"

write "V13 Status" "V13_HOME='$V13_HOME'
lock=\"\$V13_HOME/data/coordinator.lock\"
pid=\$(cat \"\$lock\" 2>/dev/null || true)
if [ -n \"\$pid\" ] && kill -0 \"\$pid\" 2>/dev/null; then echo \"V13 läuft (Prozess \$pid).\"; else echo 'V13 läuft gerade nicht.'; fi
for n in STILLSTAND NOTAUS; do [ -e \"\$V13_HOME/control/\$n\" ] && echo \"Wartet auf den Chat: Knopf \$n\"; done
echo
echo 'Genauer Stand im Chat: :stillstand status und :notaus status'
echo 'Enter schließt das Fenster.'; read -r _"

stop_button() {  # stop_button <DATEI> <Text>
  printf "V13_HOME='%s'\nmkdir -p \"\$V13_HOME/control\" && chmod 700 \"\$V13_HOME/control\"\n: > \"\$V13_HOME/control/%s\" && chmod 600 \"\$V13_HOME/control/%s\"\nmsg='%s'\ncommand -v termux-toast >/dev/null && termux-toast -g middle \"\$msg\"\ncommand -v termux-notification >/dev/null && termux-notification --id v13-stop --title 'V13' --content \"\$msg\" >/dev/null 2>&1\nexit 0" \
    "$V13_HOME" "$1" "$1" "$2"
}
write "tasks/V13 Notaus" "$(stop_button NOTAUS 'Notaus angefordert: Werkzeuge und Freigaben stoppen. Wirkt sofort im laufenden Chat, sonst beim nächsten Start. Aufheben nur im Chat: :notaus aus')"
write "tasks/V13 Stillstand" "$(stop_button STILLSTAND 'Stillstand angefordert: alles hält an (Werkzeuge, Lernen, Hintergrund, Alterung). Wirkt sofort im laufenden Chat, sonst beim nächsten Start. Aufheben nur im Chat: :stillstand aus')"

echo "Fertig. Vier V13-Knöpfe liegen in $SC."
echo "Für die Knöpfe auf dem Startbildschirm brauchst du die App Termux:Widget (aus derselben Quelle"
echo "wie Termux, z. B. F-Droid). Für kurze Meldungen beim Drücken zusätzlich Termux:API und: pkg install termux-api"
echo "Dann: lange auf den Startbildschirm drücken → Widgets → Termux:Widget hinziehen."
