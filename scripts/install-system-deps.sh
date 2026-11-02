#!/usr/bin/env bash
# Installe, après confirmation, ce dont SigilDesk a besoin au niveau du système.
# À lancer une fois, depuis un compte administrateur (sudo demande le mot de passe) :
#
#   - paquets PySide6 et QML de Lubuntu, wmctrl (scripts/apt-packages.txt), puis VLC,
#     le pilote VA-API i965 du Celeron N3060, pour le décodage vidéo matériel, et
#     les outils de vérification vainfo et mesa-utils (scripts/apt-packages-asus.txt) ;
#   - traduction de qpdfview (qpdfview-translations, déjà présente dans Lubuntu
#     26.04 : simple garantie ; qpdfview suit la langue de la session) et pack
#     de langue française ;
#   - Chromium (snap, seule forme disponible sur Ubuntu 26.04) : c'est lui qui
#     ouvre Facebook, Mails et YouTube en fenêtre d'application, sans barre d'adresse ;
#   - mises à jour automatiques complètes : unattended-upgrades étendu aux mises
#     à jour courantes (data/52sigildesk-mises-a-jour), update-notifier-common
#     pour savoir quand un redémarrage est nécessaire (SigilDesk le propose alors),
#     et, pour l'utilisateur courant seulement, les notificateurs de Lubuntu
#     masqués (ils demandaient un mot de passe). Annulable : disable-auto-updates.sh ;
#   - habillage « Sigilys system » : écran de démarrage et d'arrêt, bouton du
#     menu (install-branding.sh ; annulable : remove-branding.sh).
#
# Ce script ne change ni la langue ni le fuseau horaire du système, ni GRUB, ni
# SDDM : choisir « Français » à l'installation de Lubuntu suffit pour une session
# en français. Options : --yes (pas de question), --sans-chromium,
# --sans-mises-a-jour, --sans-logo.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$here/lib.sh"
refuse_root

assume_yes=0
chromium=1
auto_updates=1
branding=1
for arg in "$@"; do
    case "$arg" in
        --yes) assume_yes=1 ;;
        --sans-chromium) chromium=0 ;;
        --sans-mises-a-jour) auto_updates=0 ;;
        --sans-logo) branding=0 ;;
        *) echo "Option inconnue : $arg (options : --yes, --sans-chromium, --sans-mises-a-jour, --sans-logo)" >&2; exit 64 ;;
    esac
done

# Les deux listes acceptent des lignes vides et des commentaires (#).
mapfile -t packages < <(grep -hv '^\s*\(#\|$\)' "$here/apt-packages.txt" "$here/apt-packages-asus.txt")
packages+=(qpdfview-translations language-pack-fr)
if [ "$auto_updates" = 1 ]; then packages+=(unattended-upgrades update-notifier-common); fi
has_chromium=0
if command -v chromium >/dev/null 2>&1 || [ -x /snap/bin/chromium ]; then has_chromium=1; fi

echo "Paquets Lubuntu à installer (apt) :"
printf '  %s\n' "${packages[@]}"
if [ "$chromium" = 1 ] && [ "$has_chromium" = 0 ]; then
    echo "Navigateur à installer : chromium (snap, environ 200 Mo)"
fi
if [ "$auto_updates" = 1 ]; then
    echo "Mises à jour automatiques : toutes les mises à jour, chaque jour, sans redémarrage forcé"
    echo "  ($AUTO_UPDATES_FILE ; notificateurs de Lubuntu masqués pour $(id -un))"
fi
if [ "$branding" = 1 ]; then
    echo "Habillage Sigilys system : écran de démarrage et d'arrêt, bouton du menu"
fi
if [ "$assume_yes" != 1 ]; then
    read -r -p "Continuer ? (o/N) " answer
    case "$answer" in o|O|oui|Oui) ;; *) echo "Rien n'a été installé."; exit 0 ;; esac
fi

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}"
if [ "$chromium" = 1 ] && [ "$has_chromium" = 0 ]; then
    sudo snap install chromium
fi
if [ "$auto_updates" = 1 ]; then
    sudo install -m 644 "$SRC/data/52sigildesk-mises-a-jour" "$AUTO_UPDATES_FILE"
    if ! apt-config dump > /dev/null 2>&1; then
        sudo rm -f "$AUTO_UPDATES_FILE"
        echo "Réglage des mises à jour refusé par apt : rien n'a été changé." >&2
        exit 1
    fi
    echo "Mises à jour automatiques activées."
    hide_update_notifiers
fi
if [ "$branding" = 1 ]; then
    bash "$SRC/scripts/install-branding.sh" --yes
fi
echo
echo "Terminé. Vérification : $here/check-deps.sh"
