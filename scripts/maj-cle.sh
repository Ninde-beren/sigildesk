#!/usr/bin/env bash
# Met à jour la clé USB d'installation (poste de développement) et vérifie la copie.
#   scripts/maj-cle.sh [/media/antoine/BONIFACI]
#   scripts/maj-cle.sh --attendre          # attend que la clé soit branchée (10 h au plus)
# Contenu écrit dans <clé>/SigilDesk/ : sigildesk-app/ (sans .git, .venv, build ni caches),
# installer.sh, LISEZ-MOI.txt et essais/. Le reste de la clé n'est pas touché.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
attendre=0
cle="/media/$(id -un)/BONIFACI"
for arg in "$@"; do
    case "$arg" in
        --attendre) attendre=1 ;;
        *) cle="$arg" ;;
    esac
done

if [ "$attendre" = 1 ]; then
    for _ in $(seq 7200); do
        findmnt -rn "$cle" > /dev/null && break
        sleep 5
    done
    sleep 3  # laisse le montage se stabiliser
fi
if ! findmnt -rn "$cle" > /dev/null; then
    echo "Clé non montée : $cle" >&2
    exit 1
fi

dest="$cle/SigilDesk"
mkdir -p "$dest/essais"
rm -rf "$dest/sigildesk-app.nouveau"
mkdir -p "$dest/sigildesk-app.nouveau"
(cd "$here" && tar --exclude=./.git --exclude=./.venv --exclude=./build --exclude=./.ruff_cache --exclude='__pycache__' --exclude='*.pyc' -cf - .) \
    | tar -xf - -C "$dest/sigildesk-app.nouveau" --no-same-owner
rm -rf "$dest/sigildesk-app"
mv "$dest/sigildesk-app.nouveau" "$dest/sigildesk-app"
cp "$here/scripts/installer-cle.sh" "$dest/installer.sh"
cp "$here/build/LISEZ-MOI.txt" "$dest/LISEZ-MOI.txt"
if [ -d "$here/build/vm/cle-usb/essais" ]; then cp "$here/build/vm/cle-usb/essais/"* "$dest/essais/"; fi
sync

# Vérification fichier par fichier.
sommes="$(mktemp)"
(cd "$here" && find . -path ./.git -prune -o -path ./.venv -prune -o -path ./build -prune -o -path ./.ruff_cache -prune -o -name __pycache__ -prune -o -type f ! -name '*.pyc' -print0 \
    | sort -z | xargs -0 sha256sum) > "$sommes"
(cd "$dest/sigildesk-app" && sha256sum -c --quiet "$sommes")
cmp -s "$here/scripts/installer-cle.sh" "$dest/installer.sh"
cmp -s "$here/build/LISEZ-MOI.txt" "$dest/LISEZ-MOI.txt"
echo "Clé à jour et vérifiée : $(wc -l < "$sommes") fichiers, installer.sh, LISEZ-MOI.txt ($dest)"
rm -f "$sommes"
