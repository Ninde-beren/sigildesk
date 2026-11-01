#!/usr/bin/env bash
# Toute la suite de tests (unittest, bibliothèque standard), rendu Qt hors écran.
#   ./run-tests.sh            ./run-tests.sh -v            ./run-tests.sh -k favoris
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python="${SIGILDESK_PYTHON:-}"
if [ -z "$python" ]; then
    if [ -x "$here/.venv/bin/python" ]; then python="$here/.venv/bin/python"; else python="python3"; fi
fi
cd "$here"
export QT_QPA_PLATFORM=offscreen
exec "$python" -m unittest discover -s tests -t tests "$@"
