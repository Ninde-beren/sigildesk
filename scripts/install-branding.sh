#!/usr/bin/env bash
# Habillage « Sigilys system », à la place du logo de Lubuntu, à deux endroits :
#   - l'écran de démarrage et d'arrêt (thème Plymouth « sigilys », sudo) ;
#   - le bouton du menu du panneau LXQt (utilisateur courant seulement).
# Le thème de Lubuntu reste installé : remove-branding.sh le rétablit.
# Après le thème, l'initramfs est reconstruit (1 à 3 minutes sur l'ASUS) ;
# dans une session live, cette étape est sautée (sans effet).
#   Options : --yes (pas de question), --menu-seulement (sans sudo).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
refuse_root

assume_yes=0
menu_only=0
for arg in "$@"; do
    case "$arg" in
        --yes) assume_yes=1 ;;
        --menu-seulement) menu_only=1 ;;
        *) echo "Option inconnue : $arg (options : --yes, --menu-seulement)" >&2; exit 64 ;;
    esac
done

theme_src="$SRC/branding/sigilys-system/plymouth/sigilys"
if [ ! -f "$theme_src/sigilys.plymouth" ] || [ ! -f "$BRANDING_SRC_ICON" ]; then
    echo "Habillage absent ($SRC/branding/sigilys-system) : lancer d'abord scripts/build-branding.py." >&2
    exit 1
fi

if [ "$menu_only" = 0 ]; then
    echo "Thème de démarrage et d'arrêt « Sigilys system » : $PLYMOUTH_THEME_DIR"
    if [ "$assume_yes" != 1 ]; then
        read -r -p "Continuer ? (o/N) " answer
        case "$answer" in o|O|oui|Oui) ;; *) echo "Rien n'a été changé."; exit 0 ;; esac
    fi
    sudo rm -rf "$PLYMOUTH_THEME_DIR"
    sudo mkdir -p "$PLYMOUTH_THEME_DIR"
    sudo cp "$theme_src"/* "$PLYMOUTH_THEME_DIR/"
    # Images de saisie de mot de passe (disque chiffré) : reprises du thème installé.
    for image in lock.png entry.png bullet.png capslock.png keyboard.png keymap-render.png; do
        for origin in /usr/share/plymouth/themes/lubuntu-logo/spinner /usr/share/plymouth/themes/spinner; do
            if [ -f "$origin/$image" ]; then sudo cp "$origin/$image" "$PLYMOUTH_THEME_DIR/"; break; fi
        done
    done
    sudo update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth \
        "$PLYMOUTH_THEME_DIR/sigilys.plymouth" 150
    sudo update-alternatives --set default.plymouth "$PLYMOUTH_THEME_DIR/sigilys.plymouth"
    if grep -qw 'boot=casper' /proc/cmdline 2>/dev/null; then
        echo "Session live : initramfs non reconstruit (le thème servira à l'arrêt)."
    else
        echo "Reconstruction de l'initramfs (1 à 3 minutes)…"
        sudo update-initramfs -u
    fi
    echo "Thème de démarrage installé."
fi

mkdir -p "$(dirname "$BRANDING_ICON")"
install -m 644 "$BRANDING_SRC_ICON" "$BRANDING_ICON"
python3 "$SRC/scripts/menu-icon.py" poser "$BRANDING_ICON"
