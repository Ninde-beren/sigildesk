#!/usr/bin/env python3
"""Prépare la clé USB virtuelle de la VM d'essai (`build/vm/cle-usb/`).

Contenu : une copie de SigilDesk, le script `vm-installe.sh` à lancer dans la
VM, et des fichiers d'essai pour le guide de tests manuels : photo JPEG, PNG,
WEBP, document PDF de 3 pages, vidéo MP4 1280×720 H.264 + AAC (avec ffmpeg).
`scripts/vm-lubuntu.sh` branche ce dossier comme une clé USB (FAT, lecture seule).

    .venv/bin/python scripts/vm-cle-usb.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO = Path(__file__).resolve().parent.parent
KEY = REPO / "build" / "vm" / "cle-usb"
IGNORE = shutil.ignore_patterns(".venv", "build", "__pycache__", ".git", "captures", "*.pyc")

INSTALLER = r"""#!/bin/bash
# Installe SigilDesk dans la session live Lubuntu de la VM d'essai, puis le lance.
# (Dans la session live, sudo ne demande pas de mot de passe.)
set -euo pipefail
cle="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

# Écran de la VM au plus près de l'ASUS (1366×768) s'il a suivi la fenêtre QEMU.
# 1368 et non 1366 : multiple de 8, sinon la VGA de QEMU cisaille l'image.
sortie="$(xrandr | awk '/ connected/{print $1; exit}')"
if ! xrandr | grep -qE '^ *136[0-8]x768.*\*'; then
    xrandr --newmode 1368x768 85.86 1368 1440 1584 1800 768 769 772 795 +hsync +vsync 2>/dev/null || true
    xrandr --addmode "$sortie" 1368x768 2>/dev/null || true
    xrandr --output "$sortie" --mode 1368x768 || echo "Résolution 1368×768 impossible ici."
fi

echo "== 1/4 Paquets Lubuntu, traduction de qpdfview, Chromium (snap)"
bash "$cle/sigildesk-app/scripts/install-system-deps.sh" --yes
# Session de la VM en français et à l'heure de Paris, comme l'ASUS installé en français
# (effet à la prochaine ouverture de session : lxqt-leave --logout).
sudo update-locale LANG=fr_FR.UTF-8 LANGUAGE=fr_FR:fr
sudo timedatectl set-timezone Europe/Paris || true

echo "== 2/4 Copie depuis la clé et fichiers d'essai"
rm -rf ~/sigildesk-app
cp -r "$cle/sigildesk-app" ~/sigildesk-app
chmod +x ~/sigildesk-app/*.sh ~/sigildesk-app/scripts/*.sh ~/sigildesk-app/scripts/*.py
xdg-user-dirs-update || true
for kind in PICTURES VIDEOS DOCUMENTS; do mkdir -p "$(xdg-user-dir "$kind")"; done
cp "$cle"/essais/photo.jpg "$cle"/essais/capture.png "$cle"/essais/image.webp "$(xdg-user-dir PICTURES)/"
cp "$cle"/essais/*.mp4 "$(xdg-user-dir VIDEOS)/" 2>/dev/null || true
cp "$cle"/essais/document.pdf "$(xdg-user-dir DOCUMENTS)/"

echo "== 3/4 Installation utilisateur"
bash ~/sigildesk-app/scripts/install-user.sh

echo "== 4/4 Diagnostic"
bash ~/sigildesk-app/scripts/check-deps.sh || true

echo
echo "Lancement de SigilDesk (Ctrl+Alt+M pour revenir au bureau LXQt)…"
nohup ~/.local/bin/sigildesk > /dev/null 2>&1 &
"""


def make_images(folder: Path) -> None:
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPageSize, QPainter, QPdfWriter

    app = QGuiApplication.instance() or QGuiApplication([])

    def picture(width: int, height: int, top: str, bottom: str, text: str) -> QImage:
        image = QImage(width, height, QImage.Format.Format_RGB32)
        painter = QPainter(image)
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(top))
        gradient.setColorAt(1, QColor(bottom))
        painter.fillRect(image.rect(), gradient)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Sans", max(24, width // 20), QFont.Weight.Bold))
        painter.drawText(image.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
        return image

    picture(1600, 1200, "#3A7BD5", "#00D2FF", "Photo JPEG d'essai").save(str(folder / "photo.jpg"), "JPEG", 90)
    picture(1920, 1080, "#F7971E", "#FFD200", "Image PNG d'essai").save(str(folder / "capture.png"), "PNG")
    picture(1920, 1080, "#11998E", "#38EF7D", "Image WEBP d'essai").save(str(folder / "image.webp"), "WEBP", 85)

    writer = QPdfWriter(str(folder / "document.pdf"))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setResolution(150)
    painter = QPainter(writer)
    for page in range(1, 4):
        if page > 1:
            writer.newPage()
        painter.setFont(QFont("Sans", 28, QFont.Weight.Bold))
        painter.drawText(QRectF(100, 100, 1000, 120), f"Document d'essai — page {page} / 3")
        painter.setFont(QFont("Sans", 12))
        body = "SigilDesk : vérifier que ce PDF s'ouvre dans qpdfview et se lit confortablement. " * 12
        painter.drawText(QRectF(100, 260, 1040, 1200), Qt.TextFlag.TextWordWrap, body)
    painter.end()
    del app


def make_video(folder: Path) -> bool:
    if not shutil.which("ffmpeg"):
        print("ffmpeg absent : pas de vidéo d'essai (déposez un MP4 720p dans build/vm/cle-usb/essais/).")
        return False
    command = [
        "ffmpeg", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
        "-t", "20", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest", str(folder / "video-720p.mp4"),
    ]
    return subprocess.run(command, check=False).returncode == 0


def main() -> int:
    if KEY.exists():
        shutil.rmtree(KEY)
    essais = KEY / "essais"
    essais.mkdir(parents=True)
    shutil.copytree(REPO, KEY / "sigildesk-app", ignore=IGNORE)
    (KEY / "vm-installe.sh").write_text(INSTALLER, encoding="utf-8")
    make_images(essais)
    make_video(essais)
    size = sum(p.stat().st_size for p in KEY.rglob("*") if p.is_file())
    print(f"Clé USB virtuelle prête : {KEY} ({size // 1024} Ko)")
    for path in sorted(essais.iterdir()):
        print(f"  essais/{path.name}  {path.stat().st_size // 1024} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main())
