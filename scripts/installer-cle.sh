#!/usr/bin/env bash
# Installation complète de SigilDesk depuis la clé USB, en une commande.
# Copié à la racine du dossier SigilDesk de la clé sous le nom installer.sh :
#   bash /run/media/$USER/BONIFACI/SigilDesk/installer.sh
# Installe directement depuis la clé, sans copie dans le dossier personnel :
# install-system-deps.sh (récapitulatif, confirmation, mot de passe), puis
# install-user.sh, qui range l'application dans ~/.local/share/sigildesk/app,
# puis le diagnostic (check-deps.sh : applications, matériel et pilotes), qui
# ne modifie rien et dit ce qu'il reste à regarder.
# La clé peut ensuite être retirée. SigilDesk s'ouvre ensuite seul à chaque
# ouverture de session (disable-autostart.sh pour l'en empêcher).
set -euo pipefail
cle="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
app="$cle/sigildesk-app"

if [ "$(id -u)" = 0 ]; then
    echo "Lancez cette commande sans sudo : le mot de passe sera demandé au bon moment." >&2
    exit 1
fi
if [ ! -f "$app/scripts/install-user.sh" ]; then
    echo "SigilDesk introuvable à côté de ce script ($app)." >&2
    exit 1
fi

echo "== 1/3 Système : paquets, Chromium, mises à jour automatiques, logo Sigilys"
bash "$app/scripts/install-system-deps.sh"

echo "== 2/3 SigilDesk pour $(id -un)"
bash "$app/scripts/install-user.sh"

echo "== 3/3 Vérification : applications, matériel et pilotes (rien n'est modifié)"
source "$app/scripts/lib.sh"  # pour APP_DIR : le diagnostic tourne depuis la copie installée
bash "$APP_DIR/scripts/check-deps.sh" \
    || echo "(des lignes [MANQUE] ou [!!] ci-dessus demandent un coup d'œil : $cle/sigildesk-app/docs/recuperation.md)"

cat <<EOF

Installation terminée : la clé peut être retirée. Il reste :
  1. Ouvrir Chromium une fois et accepter ses conditions d'utilisation.
  2. Essayer SigilDesk : menu des applications › Accessoires › SigilDesk
     (régler la messagerie et la ville de la météo dans Paramètres).
  3. Redémarrer : le logo Sigilys apparaît au démarrage et SigilDesk s'ouvre
     seul à l'ouverture de session. Pour l'en empêcher :
       bash ~/.local/share/sigildesk/app/scripts/disable-autostart.sh
EOF

# Copies laissées par l'ancienne version de cet installeur : plus utilisées.
anciennes=("$HOME"/sigildesk-app "$HOME"/sigildesk-app.ancien-*)
existantes=()
for dossier in "${anciennes[@]}"; do [ -d "$dossier" ] && existantes+=("$dossier"); done
if [ "${#existantes[@]}" -gt 0 ]; then
    echo
    echo "Anciennes copies de SigilDesk, inutiles, que vous pouvez supprimer :"
    printf '  %s\n' "${existantes[@]}"
    echo "  rm -rf ~/sigildesk-app ~/sigildesk-app.ancien-*"
fi
