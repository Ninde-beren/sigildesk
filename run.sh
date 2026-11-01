#!/usr/bin/env bash
# Lance SigilDesk depuis le dépôt (développement). Utilise .venv s'il existe,
# sinon le python3 du système (paquets python3-pyside6.* sur Lubuntu).
#   ./run.sh --windowed --size 1366x768
#   ./run.sh --windowed --size 1024x600 --root /tmp/essai-sigildesk
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python="${SIGILDESK_PYTHON:-}"
if [ -z "$python" ]; then
    if [ -x "$here/.venv/bin/python" ]; then python="$here/.venv/bin/python"; else python="python3"; fi
fi
cd "$here"
exec "$python" -m sigildesk "$@"
