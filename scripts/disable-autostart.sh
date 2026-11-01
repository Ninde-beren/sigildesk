#!/usr/bin/env bash
# Désactive l'ouverture automatique de SigilDesk. Idempotent.
# Équivalent manuel : rm ~/.config/autostart/sigildesk.desktop
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
refuse_root

if owned "$AUTOSTART_FILE" "$DESKTOP_MARK"; then
    rm -f "$AUTOSTART_FILE"
    echo "Autostart désactivé : SigilDesk ne s'ouvrira plus seul à l'ouverture de session."
elif [ -e "$AUTOSTART_FILE" ]; then
    echo "Arrêt : $AUTOSTART_FILE n'a pas été créé par SigilDesk ; laissé tel quel." >&2
    exit 3
else
    echo "Autostart déjà désactivé."
fi
