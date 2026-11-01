#!/usr/bin/env bash
# Retire l'habillage « Sigilys system » : thème de démarrage de Lubuntu rétabli
# (sudo, initramfs reconstruit) et icône d'origine du bouton de menu. Idempotent.
#   Option : --menu-seulement (sans sudo).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
refuse_root

menu_only=0
[ "${1:-}" = "--menu-seulement" ] && menu_only=1

if [ "$menu_only" = 0 ] && [ -d "$PLYMOUTH_THEME_DIR" ]; then
    sudo update-alternatives --remove default.plymouth "$PLYMOUTH_THEME_DIR/sigilys.plymouth" || true
    sudo rm -rf "$PLYMOUTH_THEME_DIR"
    if ! grep -qw 'boot=casper' /proc/cmdline 2>/dev/null; then
        sudo update-initramfs -u
    fi
    echo "Thème de démarrage de Lubuntu rétabli."
fi
python3 "$SRC/scripts/menu-icon.py" retirer
rm -f "$BRANDING_ICON"
