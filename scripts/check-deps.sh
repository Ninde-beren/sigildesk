#!/usr/bin/env bash
# Diagnostic sans rien modifier : PySide6, modules QML, formats d'image,
# applications (Chromium, PCManFM-Qt, LXImage-Qt, VLC/mpv, qpdfview),
# extinction par la session et associations de fichiers.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
cd "$SRC"
if ! "$PYTHON" -c 'import PySide6' 2>/dev/null; then
    echo "PySide6 absent pour $PYTHON. Paquets à installer :"
    echo "  sudo apt install $(grep -hv '^\s*\(#\|$\)' "$SRC/scripts/apt-packages.txt" "$SRC/scripts/apt-packages-asus.txt" | tr '\n' ' ')"
    exit 2
fi
exec "$PYTHON" -m sigildesk --doctor
