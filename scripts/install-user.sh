#!/usr/bin/env bash
# Installe (ou met à jour) SigilDesk pour l'utilisateur courant.
#
# Sans sudo, sans paquet, sans toucher à LXQt : copie l'application dans
# ~/.local/share/sigildesk/app, pose le lanceur ~/.local/bin/sigildesk,
# l'entrée de menu, l'icône et l'ouverture automatique à l'ouverture de session
# (décision du 2026-11-01 ; --sans-autostart pour essayer à la main d'abord,
# enable-autostart.sh l'active ensuite). Relancer ce script est sans risque :
# il remplace sa propre installation, rien d'autre.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
refuse_root

autostart=1
for arg in "$@"; do
    case "$arg" in
        --sans-autostart) autostart=0 ;;
        *) echo "Option inconnue : $arg (option : --sans-autostart)" >&2; exit 64 ;;
    esac
done

version="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$SRC/sigildesk/__init__.py")"
echo "SigilDesk $version — installation pour $(id -un)"

# 1. Dépendances : vérifiées, jamais installées en silence.
if ! "$PYTHON" -c 'import PySide6.QtQuick, PySide6.QtQml, PySide6.QtNetwork, PySide6.QtGui' 2>/dev/null; then
    cat >&2 <<EOF

PySide6 est introuvable pour $PYTHON. Sur Lubuntu 26.04, installez-le une fois
avec un compte administrateur, puis relancez ce script :

  sudo apt install $(grep -hv '^\s*\(#\|$\)' "$SRC/scripts/apt-packages.txt" "$SRC/scripts/apt-packages-asus.txt" | tr '\n' ' ')

(Ou désignez un autre interpréteur : SIGILDESK_PYTHON=/chemin/python3 $0)
EOF
    exit 2
fi

# 2. Refus de toucher un fichier du même nom qui n'appartient pas à SigilDesk.
for pair in "$LAUNCHER|$LAUNCHER_MARK" "$DESKTOP_FILE|$DESKTOP_MARK"; do
    if foreign "${pair%%|*}" "${pair#*|}"; then
        echo "Arrêt : ${pair%%|*} existe déjà et n'a pas été créé par SigilDesk." >&2
        exit 3
    fi
done
if [ -d "$APP_DIR" ] && [ ! -f "$APP_DIR/$APP_MARK" ]; then
    echo "Arrêt : $APP_DIR existe déjà et n'a pas été créé par SigilDesk." >&2
    exit 3
fi

# 3. Copie de l'application, remplacée d'un bloc.
if [ "$SRC" != "$APP_DIR" ]; then
    staging="$APP_DIR.new.$$"
    rm -rf "$staging"
    mkdir -p "$staging"
    cp -R "$SRC/sigildesk" "$SRC/config" "$SRC/data" "$SRC/scripts" "$staging/"
    if [ -d "$SRC/branding/sigilys-system" ]; then
        mkdir -p "$staging/branding" && cp -R "$SRC/branding/sigilys-system" "$staging/branding/"
    fi
    find "$staging" -name '__pycache__' -type d -prune -exec rm -rf {} +
    printf '%s\n' "$version" > "$staging/VERSION"
    : > "$staging/$APP_MARK"
    if [ -d "$APP_DIR" ]; then
        rm -rf "$APP_DIR.old"
        mv "$APP_DIR" "$APP_DIR.old"
    fi
    mv "$staging" "$APP_DIR"
    rm -rf "$APP_DIR.old"
    echo "  application : $APP_DIR"
fi

# 4. Lanceur. Il se place dans le dossier de l'application avant de démarrer :
#    un dossier « sigildesk » dans le répertoire courant ne peut pas s'y substituer.
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER.tmp.$$" <<EOF
#!/bin/sh
$LAUNCHER_MARK — écrit par install-user.sh, réécrit à chaque installation.
cd "$APP_DIR" || exit 1
exec "$PYTHON" -m sigildesk "\$@"
EOF
chmod 755 "$LAUNCHER.tmp.$$"
mv -f "$LAUNCHER.tmp.$$" "$LAUNCHER"
echo "  lanceur     : $LAUNCHER"

# 5. Entrée de menu (bouton de relance depuis LXQt) et icône.
render "$APP_DIR/data/sigildesk.desktop.in" "$DESKTOP_FILE"
mkdir -p "$(dirname "$ICON_FILE")"
install -m 644 "$APP_DIR/sigildesk/resources/icons/sigildesk.svg" "$ICON_FILE"
echo "  menu        : $DESKTOP_FILE"

# 6. Mises à jour automatiques réglées (install-system-deps.sh) : les
#    notificateurs de Lubuntu, qui demandent un mot de passe, sont masqués.
if [ -f "$AUTO_UPDATES_FILE" ]; then
    hide_update_notifiers
fi

# 7. Habillage Sigilys installé sur le système : icône du menu pour cet utilisateur aussi.
if [ -f "$PLYMOUTH_THEME_DIR/sigilys.plymouth" ] && [ -f "$APP_DIR/branding/sigilys-system/menu.svg" ]; then
    mkdir -p "$(dirname "$BRANDING_ICON")"
    install -m 644 "$APP_DIR/branding/sigilys-system/menu.svg" "$BRANDING_ICON"
    python3 "$APP_DIR/scripts/menu-icon.py" poser "$BRANDING_ICON" | sed 's/^/  /'
fi

# 8. Sans écran de verrouillage installé, LXQt échoue à verrouiller avant la
#    veille et affiche une erreur à chaque réveil : on coupe ce verrouillage.
python3 "$APP_DIR/scripts/session-lock.py" couper | sed 's/^/  /'

# 9. Ouverture automatique à l'ouverture de session (XDG autostart, LXQt seulement).
#    Un fichier du même nom qui n'est pas le nôtre est laissé tel quel.
if foreign "$AUTOSTART_FILE" "$DESKTOP_MARK"; then
    echo "  autostart   : laissé — $AUTOSTART_FILE n'appartient pas à SigilDesk"
elif [ "$autostart" = 1 ] || owned "$AUTOSTART_FILE" "$DESKTOP_MARK"; then
    render "$APP_DIR/data/sigildesk-autostart.desktop.in" "$AUTOSTART_FILE"
    echo "  autostart   : activé ($APP_DIR/scripts/disable-autostart.sh pour annuler)"
else
    echo "  autostart   : non activé (--sans-autostart) — pour l'activer plus tard :"
    echo "                $APP_DIR/scripts/enable-autostart.sh"
fi

echo
echo "Terminé. Pour essayer : menu des applications › Accessoires › SigilDesk, ou la commande « $LAUNCHER »."
echo "Vérification (rien n'est modifié) : $APP_DIR/scripts/check-deps.sh"
