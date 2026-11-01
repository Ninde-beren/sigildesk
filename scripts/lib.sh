# Chemins et garde-fous communs aux scripts d'installation (à sourcer, pas à lancer).
# Périmètre strict : SigilDesk n'écrit que les fichiers listés ici, tous marqués
# comme les siens, et refuse de toucher un fichier du même nom qui ne l'est pas.

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"
CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"

APP_DIR="$DATA_HOME/sigildesk/app"
LAUNCHER="$HOME/.local/bin/sigildesk"
DESKTOP_FILE="$DATA_HOME/applications/sigildesk.desktop"
ICON_FILE="$DATA_HOME/icons/hicolor/scalable/apps/sigildesk.svg"
AUTOSTART_FILE="$CONFIG_HOME/autostart/sigildesk.desktop"
PYTHON="${SIGILDESK_PYTHON:-/usr/bin/python3}"

APT_CONF_DIR="${SIGILDESK_APT_CONF_DIR:-/etc/apt/apt.conf.d}"
AUTO_UPDATES_FILE="$APT_CONF_DIR/52sigildesk-mises-a-jour"
AUTO_UPDATES_MARK="SigilDesk : mises à jour automatiques"
SYSTEM_AUTOSTART_DIR="${SIGILDESK_SYSTEM_AUTOSTART_DIR:-/etc/xdg/autostart}"
# Notificateurs de mises à jour de Lubuntu 26.04 : ils demandent un mot de
# passe administrateur. Inutiles une fois les mises à jour automatiques.
UPDATE_NOTIFIERS=(lubuntu-update-autostart.desktop org.kde.discover.notifier.desktop update-notifier.desktop)

# Habillage « Sigilys system » (install-branding.sh / remove-branding.sh).
PLYMOUTH_THEME_DIR="${SIGILDESK_PLYMOUTH_DIR:-/usr/share/plymouth/themes/sigilys}"
BRANDING_SRC_ICON="$SRC/branding/sigilys-system/menu.svg"
BRANDING_ICON="$DATA_HOME/sigildesk/branding/menu.svg"

DESKTOP_MARK="X-SigilDesk-Managed=true"
LAUNCHER_MARK="# SigilDesk launcher"
APP_MARK=".sigildesk-app"
ICON_MARK="SigilDesk : icône"

refuse_root() {
    if [ "$(id -u)" = 0 ]; then
        echo "Ne lancez pas ce script en root ni avec sudo : SigilDesk s'installe pour un seul utilisateur." >&2
        exit 1
    fi
}

# owned FICHIER MARQUE : vrai si le fichier existe et porte la marque de SigilDesk.
owned() {
    [ -f "$1" ] && grep -qF "$2" "$1"
}

# foreign FICHIER MARQUE : vrai si un fichier du même nom existe sans la marque.
foreign() {
    [ -e "$1" ] && ! owned "$1" "$2"
}

# hide_update_notifiers : pour l'utilisateur courant seulement, masque les
# notificateurs de Lubuntu par un fichier d'autostart « Hidden=true » (règle XDG).
# Aucun fichier de Lubuntu n'est modifié ; show_update_notifiers annule.
hide_update_notifiers() {
    local name target
    for name in "${UPDATE_NOTIFIERS[@]}"; do
        [ -f "$SYSTEM_AUTOSTART_DIR/$name" ] || continue
        target="$CONFIG_HOME/autostart/$name"
        if foreign "$target" "$DESKTOP_MARK"; then
            echo "  laissé : $target (n'appartient pas à SigilDesk)"
            continue
        fi
        mkdir -p "$(dirname "$target")"
        printf '%s\n' "[Desktop Entry]" "Type=Application" "Name=${name%.desktop}" \
            "Comment=Masqué par SigilDesk : les mises à jour s'installent seules." "Hidden=true" "$DESKTOP_MARK" \
            > "$target"
        echo "  notification de mises à jour masquée : ${name%.desktop}"
    done
}

show_update_notifiers() {
    local name
    for name in "${UPDATE_NOTIFIERS[@]}"; do
        if owned "$CONFIG_HOME/autostart/$name" "$DESKTOP_MARK"; then
            rm -f "$CONFIG_HOME/autostart/$name"
            echo "  notification de mises à jour rétablie : ${name%.desktop}"
        fi
    done
}

# render GABARIT CIBLE : écrit un .desktop à partir d'un gabarit, de façon atomique.
render() {
    mkdir -p "$(dirname "$2")"
    sed "s|@LAUNCHER@|$LAUNCHER|g" "$1" > "$2.tmp.$$"
    chmod 644 "$2.tmp.$$"
    mv -f "$2.tmp.$$" "$2"
}
