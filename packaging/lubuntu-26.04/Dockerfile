# Environnement de test aligné sur Lubuntu 26.04 : mêmes dépôts Ubuntu
# « resolute », mêmes paquets PySide6 (6.10) que ceux installés sur l'ASUS.
# Sert aux tests et aux captures ; il ne remplace pas un essai en session LXQt.
FROM ubuntu:26.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    QT_QPA_PLATFORM=offscreen \
    SIGILDESK_PYTHON=/usr/bin/python3

# Seule la liste commune : VLC, le pilote VA-API et les outils de vérification
# (scripts/apt-packages-asus.txt) sont propres à l'ASUS, inutiles sans écran ni
# carte graphique.
COPY scripts/apt-packages.txt /tmp/apt-packages.txt
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 xdg-utils fonts-noto-core $(grep -v '^\s*\(#\|$\)' /tmp/apt-packages.txt) \
 && rm -rf /var/lib/apt/lists/* \
 && dpkg-query -W -f='${Package} ${Version}\n' $(grep -v '^\s*\(#\|$\)' /tmp/apt-packages.txt) python3 > /etc/sigildesk-paquets.txt
