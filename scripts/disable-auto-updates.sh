#!/usr/bin/env bash
# Annule les mises à jour automatiques complètes posées par install-system-deps.sh :
# retire data/52sigildesk-mises-a-jour d'apt (sudo) et rétablit les notificateurs
# de mises à jour de Lubuntu pour l'utilisateur courant. Lubuntu reprend alors
# son comportement d'origine (mises à jour de sécurité seules). Idempotent.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
refuse_root

if [ -f "$AUTO_UPDATES_FILE" ]; then
    if grep -qF "$AUTO_UPDATES_MARK" "$AUTO_UPDATES_FILE"; then
        sudo rm -f "$AUTO_UPDATES_FILE"
        echo "Mises à jour automatiques complètes désactivées."
    else
        echo "Arrêt : $AUTO_UPDATES_FILE n'a pas été posé par SigilDesk ; laissé tel quel." >&2
        exit 3
    fi
else
    echo "Mises à jour automatiques complètes déjà désactivées."
fi
show_update_notifiers
