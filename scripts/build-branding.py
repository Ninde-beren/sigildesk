#!/usr/bin/env python3
"""Fabrique l'habillage « Sigilys system » à partir du logo choisi.

    .venv/bin/python scripts/build-branding.py --symbole <symbole.svg> --ecran <symbole-et-nom.svg> \\
        --fond "#16202B" --accent "#B4CFEC"

Produit dans `branding/sigilys-system/` :
  source/                 les SVG d'origine, pour pouvoir tout refaire
  menu.svg                l'icône du bouton de menu LXQt
  plymouth/sigilys/       le thème de démarrage et d'arrêt (module two-step) :
                          sigilys.plymouth, watermark.png, throbber-*.png, animation-*.png
  apercu-demarrage.png    l'écran de démarrage simulé en 1366×768, pour relecture

Les images de saisie de mot de passe (cadenas, champ) ne sont pas fournies ici :
install-branding.sh les reprend du thème déjà installé sur la machine.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "branding" / "sigilys-system"
FRAMES = 36
WATERMARK_HEIGHT = 230  # px, pour un écran de 768 px de haut

PLYMOUTH = """[Plymouth Theme]
Name=Sigilys system
Description=Écran de démarrage et d'arrêt Sigilys system (SigilDesk)
ModuleName=two-step

[two-step]
Font=Sans 12
TitleFont=Sans Light 26
ImageDir=/usr/share/plymouth/themes/sigilys
DialogHorizontalAlignment=.5
DialogVerticalAlignment=.75
TitleHorizontalAlignment=.5
TitleVerticalAlignment=.25
HorizontalAlignment=.5
VerticalAlignment=.78
WatermarkHorizontalAlignment=.5
WatermarkVerticalAlignment=.42
Transition=none
TransitionDuration=0.0
BackgroundStartColor={fond}
BackgroundEndColor={fond}
ProgressBarBackgroundColor={barre}
ProgressBarForegroundColor=0xffffff
MessageBelowAnimation=true

[boot-up]
UseEndAnimation=false
UseFirmwareBackground=false

[shutdown]
UseEndAnimation=false
UseFirmwareBackground=false

[reboot]
UseEndAnimation=false
UseFirmwareBackground=false

[updates]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
_Title=Installation des mises à jour…
_SubTitle=N'éteignez pas l'ordinateur

[system-upgrade]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
_Title=Mise à niveau du système…
_SubTitle=N'éteignez pas l'ordinateur

[firmware-upgrade]
SuppressMessages=true
ProgressBarShowPercentComplete=true
UseProgressBar=true
_Title=Mise à jour du micrologiciel…
_SubTitle=N'éteignez pas l'ordinateur
"""


def plymouth_color(hex_color: str) -> str:
    return "0x" + hex_color.lstrip("#").lower()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--symbole", type=Path, required=True, help="symbole en couleur (icône du menu)")
    parser.add_argument("--ecran", type=Path, required=True, help="symbole et nom, pour l'écran de démarrage")
    parser.add_argument("--fond", default="#16202B", help="couleur de fond de l'écran de démarrage")
    parser.add_argument("--accent", default="#B4CFEC", help="couleur de la roue d'attente")
    parser.add_argument("--sortie", type=Path, default=OUT, help="dossier produit (tests)")
    args = parser.parse_args()
    out = args.sortie

    from PySide6.QtCore import QRectF, QSize, Qt
    from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen
    from PySide6.QtSvg import QSvgRenderer

    app = QGuiApplication.instance() or QGuiApplication([])
    for svg in (args.symbole, args.ecran):
        if not QSvgRenderer(str(svg)).isValid():
            print(f"SVG illisible : {svg}", file=sys.stderr)
            return 1

    if out.exists():
        shutil.rmtree(out)
    theme = out / "plymouth" / "sigilys"
    (out / "source").mkdir(parents=True)
    theme.mkdir(parents=True)
    shutil.copy(args.symbole, out / "source" / "symbole.svg")
    shutil.copy(args.ecran, out / "source" / "ecran.svg")
    shutil.copy(args.symbole, out / "menu.svg")

    # Filigrane : symbole et nom, centrés, fond transparent.
    renderer = QSvgRenderer(str(args.ecran))
    size = renderer.defaultSize()
    scale = WATERMARK_HEIGHT / size.height()
    watermark = QImage(QSize(round(size.width() * scale), WATERMARK_HEIGHT), QImage.Format.Format_ARGB32_Premultiplied)
    watermark.fill(Qt.GlobalColor.transparent)
    painter = QPainter(watermark)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    watermark.save(str(theme / "watermark.png"))

    # Roue d'attente : un arc qui tourne, 36 images (throbber et animation).
    accent = QColor(args.accent)
    for n in range(FRAMES):
        frame = QImage(48, 48, QImage.Format.Format_ARGB32_Premultiplied)
        frame.fill(Qt.GlobalColor.transparent)
        p = QPainter(frame)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QColor(accent)
        track.setAlphaF(0.22)
        p.setPen(QPen(track, 4))
        p.drawEllipse(QRectF(6, 6, 36, 36))
        p.setPen(QPen(accent, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(6, 6, 36, 36), int(-n * 360 / FRAMES * 16), 100 * 16)
        p.end()
        for prefix in ("throbber", "animation"):
            frame.save(str(theme / f"{prefix}-{n + 1:04d}.png"))

    barre = QColor(args.fond).lighter(160).name()
    (theme / "sigilys.plymouth").write_text(
        PLYMOUTH.format(fond=plymouth_color(args.fond), barre=plymouth_color(barre)), encoding="utf-8")

    # Aperçu 1366×768, placé comme le fera Plymouth (alignements du .plymouth).
    preview = QImage(1366, 768, QImage.Format.Format_RGB32)
    preview.fill(QColor(args.fond))
    p = QPainter(preview)
    wx = round((1366 - watermark.width()) * 0.5)
    wy = round((768 - watermark.height()) * 0.42)
    p.drawImage(wx, wy, watermark)
    spinner = QImage(str(theme / "throbber-0004.png"))
    p.drawImage(round((1366 - 48) * 0.5), round((768 - 48) * 0.78), spinner)
    p.end()
    preview.save(str(out / "apercu-demarrage.png"))
    del app

    print(f"Habillage écrit dans {out}")
    print(f"  filigrane {watermark.width()}×{watermark.height()} px, {FRAMES} images de roue, fond {args.fond}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
