#!/usr/bin/env bash
# Retire SigilDesk de l'utilisateur courant. Idempotent, sans sudo.
#
# Ne supprime que les fichiers marqués comme ceux de SigilDesk. Garde par
# défaut les réglages, favoris et fonds importés (~/.config/sigildesk,
# ~/.local/share/sigildesk/wallpapers) : --purge les efface après confirmation.
# Ne touche jamais au profil du navigateur, aux documents ni à LXQt.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
refuse_root

purge=0
assume_yes=0
for arg in "$@"; do
    case "$arg" in
        --purge) purge=1 ;;
        --yes) assume_yes=1 ;;
        *) echo "Option inconnue : $arg (options : --purge, --yes)" >&2; exit 64 ;;
    esac
done

remove_owned() {
    if owned "$1" "$2"; then
        rm -f "$1"
        echo "  retiré : $1"
    elif [ -e "$1" ]; then
        echo "  laissé : $1 (n'appartient pas à SigilDesk)"
    fi
}

echo "Désinstallation de SigilDesk pour $(id -un)"
remove_owned "$AUTOSTART_FILE" "$DESKTOP_MARK"
remove_owned "$DESKTOP_FILE" "$DESKTOP_MARK"
remove_owned "$LAUNCHER" "$LAUNCHER_MARK"
remove_owned "$ICON_FILE" "$ICON_MARK"
show_update_notifiers
python3 "$SRC/scripts/session-lock.py" retablir | sed 's/^/  /'
if [ -f "$BRANDING_ICON" ]; then
    python3 "$SRC/scripts/menu-icon.py" retirer | sed 's/^/  /'
    rm -f "$BRANDING_ICON"
fi
if [ -f "$APP_DIR/$APP_MARK" ]; then
    rm -rf "$APP_DIR"
    echo "  retiré : $APP_DIR"
fi
rm -rf "$APP_DIR".new.* "$APP_DIR.old" 2>/dev/null || true

if [ "$purge" = 1 ]; then
    echo
    echo "--purge efface aussi les réglages, favoris et fonds d'écran importés de SigilDesk :"
    echo "  $CONFIG_HOME/sigildesk"
    echo "  $DATA_HOME/sigildesk"
    echo "  $STATE_HOME/sigildesk"
    echo "  $CACHE_HOME/sigildesk"
    echo "Vos photos d'origine, vos documents et votre navigateur ne sont pas concernés."
    answer=""
    if [ "$assume_yes" = 1 ]; then answer="SUPPRIMER"; else read -r -p "Tapez SUPPRIMER pour confirmer : " answer; fi
    if [ "$answer" = "SUPPRIMER" ]; then
        rm -rf "$CONFIG_HOME/sigildesk" "$DATA_HOME/sigildesk" "$STATE_HOME/sigildesk" "$CACHE_HOME/sigildesk"
        echo "  données de SigilDesk effacées"
    else
        echo "  données conservées"
    fi
else
    rmdir "$DATA_HOME/sigildesk" 2>/dev/null || true
    echo "Réglages et fonds importés conservés ($CONFIG_HOME/sigildesk, $DATA_HOME/sigildesk)."
fi
echo "Si SigilDesk est encore ouvert : Paramètres › Maintenance › Quitter SigilDesk."
