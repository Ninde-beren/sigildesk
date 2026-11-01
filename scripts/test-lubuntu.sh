#!/usr/bin/env bash
# Rejoue tests, diagnostic et captures dans un conteneur Ubuntu 26.04 (base de
# Lubuntu 26.04) avec les paquets PySide6 de la distribution, sans le .venv.
# Le dépôt est monté en lecture seule ; les captures sortent dans build/.
#   scripts/test-lubuntu.sh
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="sigildesk-lubuntu:26.04"
out="$here/build/lubuntu-26.04"
mkdir -p "$out/captures"

docker build -q -t "$image" -f "$here/packaging/lubuntu-26.04/Dockerfile" "$here" > /dev/null

docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp/essai \
    -v "$here:/src:ro" -v "$out:/out" "$image" bash -euc '
        mkdir -p /tmp/essai/sigildesk && cd /tmp/essai/sigildesk
        tar -C /src --exclude=./.venv --exclude=./build --exclude="__pycache__" -cf - . | tar -xf -
        echo "== Paquets de la distribution"; cat /etc/sigildesk-paquets.txt
        echo "== Tests"; ./run-tests.sh 2>&1 | grep -vE "^[0-9-]+ [0-9:,]+ (INFO|WARNING) |qt.gui.imageio"
        echo "== Diagnostic"; python3 -m sigildesk --doctor || true
        echo "== Captures"; python3 scripts/capture.py /out/captures
    ' 2>&1 | tee "$out/rapport.txt"
echo "Rapport : $out/rapport.txt"
