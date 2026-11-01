#!/usr/bin/env bash
# Active l'ouverture de SigilDesk au démarrage de la session LXQt (XDG autostart).
# À lancer seulement après avoir essayé SigilDesk à la main. Annulable par
# disable-autostart.sh. N'agit que dans une session LXQt (OnlyShowIn=LXQt).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
refuse_root

if ! owned "$LAUNCHER" "$LAUNCHER_MARK"; then
    echo "SigilDesk n'est pas installé. Lancez d'abord scripts/install-user.sh, puis essayez-le à la main." >&2
    exit 1
fi
if foreign "$AUTOSTART_FILE" "$DESKTOP_MARK"; then
    echo "Arrêt : $AUTOSTART_FILE existe déjà et n'a pas été créé par SigilDesk." >&2
    exit 3
fi
render "$SRC/data/sigildesk-autostart.desktop.in" "$AUTOSTART_FILE"
echo "Autostart activé : $AUTOSTART_FILE"
echo "SigilDesk s'ouvrira à la prochaine ouverture de session LXQt."
echo "Pour annuler : $SRC/scripts/disable-autostart.sh"
