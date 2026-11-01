#!/usr/bin/env python3
"""Monte la vidéo LinkedIn à partir de l'enregistrement de vm-demo.py.

Format 4:5 (1080×1350), le plus visible dans le fil LinkedIn sur mobile :
légende en haut, écran de l'ordinateur au centre, logo et site en bas,
carte d'ouverture et carte de fin. Sans son.

    .venv/bin/python scripts/video-montage.py          # → build/video/sigildesk-linkedin.mp4 (temps réel)
    .venv/bin/python scripts/video-montage.py --court  # → build/video/sigildesk-linkedin-court.mp4 (~45 s)

Deux prises de vm-demo.py : « complete » (build/video/) et « noms »
(build/video/noms/, le réglage Noms sous les icônes), insérée après le mode
confort. La version courte garde les moments forts (COURT), accélérés ; les
légendes suivent le temps de chaque prise, et la carte d'ouverture annonce
l'accélération.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "build" / "video"
OUT = SRC / "montage"
W, H = 1080, 1350
FPS = 25
BG_TOP, BG_BOTTOM = "#1B2836", "#101820"
CREAM, MIST = "#F4EFE5", "#B4CFEC"
SCREEN = (40, 400, 1000)  # x, y, largeur de l'écran dans le cadre
INTRO_S, OUTRO_S = 3.2, 3.6

PRISES = {"complete": SRC, "noms": SRC / "noms"}
FIN_CONFORT = 118.5  # dans la prise complète : fin du mode confort, où s'insère la prise « noms »

# (prise, début, fin en secondes de la prise, vitesse)
LONG = [
    ("complete", 0.0, FIN_CONFORT, 1.0),
    ("noms", 0.0, 1e9, 1.0),
    ("complete", FIN_CONFORT, 1e9, 1.0),
]
# Version courte, prises du 2026-10-28 : la légende de chaque séquence reste lisible 3 s au moins.
COURT = [
    ("complete", 0.3, 5.0, 1.5),      # l'accueil
    ("complete", 13.0, 14.6, 1.5),    # clic sur YouTube…
    ("complete", 17.2, 20.6, 1.5),    # …qui s'ouvre sans barre d'adresse (chargement coupé)
    ("complete", 20.6, 23.0, 1.5),    # on revient à l'accueil…
    ("complete", 27.0, 30.2, 1.5),    # …et la pastille ramène YouTube
    ("complete", 31.5, 44.0, 2.0),    # les photos
    ("complete", 49.0, 57.0, 2.0),    # la vidéo dans VLC
    ("complete", 66.0, 68.0, 2.0),    # la recette en PDF
    ("complete", 68.0, 72.0, 1.2),
    ("complete", 77.0, 90.0, 2.8),    # favoris et météo
    ("complete", 90.2, 104.0, 2.8),   # fond d'écran
    ("complete", 104.2, 112.0, 2.0),  # mode confort
    ("noms", 2.5, 11.0, 2.5),         # noms sous les icônes retirés : les icônes remplissent les tuiles…
    ("noms", 14.0, 16.5, 3.0),        # …puis remis
    ("complete", 118.6, 124.0, 1.5),  # éteindre, puis annuler
]
COURT_INTRO_S, COURT_OUTRO_S = 2.0, 3.0


def main() -> int:
    court = "--court" in sys.argv[1:]
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath
    from PySide6.QtSvg import QSvgRenderer

    app = QGuiApplication.instance() or QGuiApplication([])
    prises = {
        name: (folder, json.loads((folder / "images.json").read_text(encoding="utf-8")),
               json.loads((folder / "legendes.json").read_text(encoding="utf-8")))
        for name, folder in PRISES.items() if (folder / "images.json").is_file()
    }
    symbol = QSvgRenderer(str(REPO / "branding" / "sigilys-system" / "source" / "symbole.svg"))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    def canvas() -> tuple[QImage, QPainter]:
        image = QImage(W, H, QImage.Format.Format_RGB32)
        painter = QPainter(image)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        gradient = QLinearGradient(0, 0, 0, H)
        gradient.setColorAt(0, QColor(BG_TOP))
        gradient.setColorAt(1, QColor(BG_BOTTOM))
        painter.fillRect(image.rect(), gradient)
        return image, painter

    def text(painter, rect, value, size, color, weight=QFont.Weight.Normal, flags=Qt.AlignmentFlag.AlignCenter):
        font = QFont("Noto Sans", size, weight)
        font.setPixelSize(size)
        painter.setFont(font)
        painter.setPen(QColor(color))
        painter.drawText(QRectF(*rect), int(flags | Qt.TextFlag.TextWordWrap), value)

    def footer(painter) -> None:
        symbol.render(painter, QRectF(W / 2 - 150, 1150, 64, 64))
        text(painter, (W / 2 - 74, 1150, 400, 36), "SigilDesk", 34, CREAM, QFont.Weight.DemiBold,
             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text(painter, (W / 2 - 74, 1188, 400, 30), "par Sigilbo · sigilbo.fr", 22, MIST, QFont.Weight.Normal,
             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def card(title: str, subtitle: str, small: str) -> QImage:
        image, painter = canvas()
        symbol.render(painter, QRectF(W / 2 - 120, 330, 240, 240))
        text(painter, (60, 620, W - 120, 90), title, 76, CREAM, QFont.Weight.DemiBold)
        text(painter, (90, 720, W - 180, 160), subtitle, 38, MIST)
        text(painter, (90, 1180, W - 180, 80), small, 24, MIST)
        painter.end()
        return image

    def caption_at(prise: str, t: float) -> str:
        for c in prises[prise][2]:
            if c["debut"] <= t < (c["fin"] if c["fin"] is not None else 1e9):
                return c["texte"]
        return ""

    sx, sy, sw = SCREEN
    entries: list[tuple[str, float]] = []

    intro = card("SigilDesk", "Un accueil simple, façon tablette,\npour celles et ceux qui débutent sur Linux",
                 "Enregistrement réel, en accéléré · Lubuntu 26.04" if court
                 else "Enregistrement réel, sans retouche · Lubuntu 26.04")
    intro.save(str(OUT / "intro.png"))
    entries.append(("intro.png", COURT_INTRO_S if court else INTRO_S))

    # Images retenues, dans l'ordre des séquences, et durée de chacune.
    chosen: list[tuple[str, int, float]] = []
    for prise, start, end, speed in (COURT if court else LONG):
        if prise not in prises:
            continue  # prise pas encore enregistrée
        frames = prises[prise][1]
        for i, (_, t) in enumerate(frames):
            following = frames[i + 1][1] if i + 1 < len(frames) else t + 0.1
            if start <= t < end:
                chosen.append((prise, i, (min(following, end) - t) / speed))

    for prise, i, duration in chosen:
        folder, frames, _ = prises[prise]
        name, t = frames[i]
        shot = QImage(str(folder / "images" / name))
        sh = round(shot.height() * sw / shot.width())
        image, painter = canvas()
        text(painter, (60, 110, W - 120, 250), caption_at(prise, t), 50, CREAM, QFont.Weight.DemiBold)
        # Ombre douce puis écran aux coins arrondis.
        for k, alpha in ((18, 0.10), (10, 0.16), (4, 0.22)):
            path = QPainterPath()
            path.addRoundedRect(QRectF(sx - k, sy - k + 10, sw + 2 * k, sh + 2 * k), 22 + k, 22 + k)
            painter.fillPath(path, QColor(0, 0, 0, round(255 * alpha)))
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(sx, sy, sw, sh), 18, 18)
        painter.setClipPath(clip)
        painter.drawImage(QRectF(sx, sy, sw, sh), shot)
        painter.setClipping(False)
        footer(painter)
        painter.end()
        out_name = f"{prise}-{i:05d}.png"
        image.save(str(OUT / out_name))
        entries.append((out_name, max(0.04, duration)))

    outro = card("SigilDesk", "Conçu par Antoine OBLIGIS pour Sigilbo\nsigilbo.fr",
                 "© 2026 Sigilbo · Usage non commercial · Données météo : Open-Meteo.com (CC BY 4.0)")
    outro.save(str(OUT / "outro.png"))
    entries.append(("outro.png", COURT_OUTRO_S if court else OUTRO_S))
    del app

    concat = OUT / "liste.txt"
    lines = [f"file '{name}'\nduration {duration:.3f}" for name, duration in entries]
    lines.append(f"file '{entries[-1][0]}'")  # le concat ignore la durée de la dernière entrée
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = SRC / ("sigildesk-linkedin-court.mp4" if court else "sigildesk-linkedin.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
                    "-vf", f"fps={FPS},format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "20",
                    "-movflags", "+faststart", str(result)], check=True)
    total = sum(d for _, d in entries)
    print(f"Vidéo : {result} ({total:.1f} s, {W}×{H}, {len(chosen)} images, prises : {', '.join(prises)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
