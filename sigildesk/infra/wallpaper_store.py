"""Fonds d'écran de SigilDesk sur le disque : fonds livrés et images importées.

Une image importée (JPEG, PNG, WEBP) est décodée, redimensionnée si besoin puis
réenregistrée dans `~/.local/share/sigildesk/wallpapers/` : elle ne dépend plus
de la clé USB, ses métadonnées (EXIF, position GPS) disparaissent et l'original
n'est jamais modifié. Le nom de la copie, `perso-<empreinte>-<tonalité>.<ext>`,
porte la tonalité (claire ou sombre) pour que le démarrage n'ait rien à décoder.
Le modèle Qt qui présente ces fonds est `ui.wallpaper_model`.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QImageReader

from sigildesk.infra.paths import WALLPAPERS_DIR

log = logging.getLogger(__name__)

IMPORT_FORMATS = ("jpeg", "png", "webp")
MAX_IMPORT_BYTES = 60 * 1024 * 1024
MAX_IMPORT_PIXELS = 120_000_000  # refusé avant décodage : protège les 4 Go de RAM
MIN_WIDTH, MIN_HEIGHT = 320, 240
STORED_MAX = QSize(2560, 1440)
MAX_IMPORTED = 24
PREFIX = "perso-"


@dataclass(frozen=True)
class Wallpaper:
    id: str
    label: str
    path: Path | None  # None : dégradé « Brume » dessiné par le QML
    tone: str  # "light" ou "dark" : couleur des textes posés directement dessus
    builtin: bool


BUILTINS: tuple[Wallpaper, ...] = (
    Wallpaper("aube", "Aube solaire", WALLPAPERS_DIR / "aube-solaire.jpg", "light", True),
    Wallpaper("aurore", "Aurore arctique", WALLPAPERS_DIR / "aurore-arctique.jpg", "light", True),
    Wallpaper("orbite", "Orbite cyan", WALLPAPERS_DIR / "orbite-cyan.jpg", "dark", True),
    Wallpaper("blueprint", "Blueprint nocturne", WALLPAPERS_DIR / "blueprint-nocturne.jpg", "dark", True),
    Wallpaper("brume", "Brume (uni)", None, "light", True),
)
DEFAULT_ID = "aube"
FALLBACK_ID = "brume"


class WallpaperError(ValueError):
    """Image refusée ; le message s'adresse à l'utilisateur."""


def analyze_tone(image: QImage) -> str:
    """« light » ou « dark » d'après la luminance du tiers supérieur de l'image.

    Le haut porte la date, la salutation et l'heure, posées sans fond : c'est
    leur lisibilité qui compte. L'image est réduite à 64×36 avant la mesure.
    """
    small = image.scaled(64, 36, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    small = small.convertToFormat(QImage.Format.Format_RGB32)
    total, count = 0.0, 0
    for y in range(12):
        for x in range(small.width()):
            color = small.pixelColor(x, y)
            total += 0.2126 * color.redF() + 0.7152 * color.greenF() + 0.0722 * color.blueF()
            count += 1
    return "light" if count and total / count >= 0.5 else "dark"


def _reader(path: Path) -> QImageReader:
    reader = QImageReader(str(path))
    reader.setDecideFormatFromContent(True)  # le contenu fait foi, pas l'extension
    reader.setAutoTransform(True)  # applique l'orientation EXIF des photos
    return reader


def import_image(source: Path, dest_dir: Path) -> Wallpaper:
    """Copie propre d'une image dans `dest_dir`. Lève `WallpaperError`."""
    if not source.is_file():
        raise WallpaperError("Ce fichier est introuvable.")
    size = source.stat().st_size
    if size == 0:
        raise WallpaperError("Ce fichier est vide.")
    if size > MAX_IMPORT_BYTES:
        raise WallpaperError("Cette image est trop lourde (60 Mo au plus).")

    reader = _reader(source)
    fmt = bytes(reader.format()).decode("ascii", "replace").lower()
    if fmt not in IMPORT_FORMATS:
        if fmt == "" and source.suffix.lower() == ".webp":
            raise WallpaperError("Les images WEBP ne sont pas prises en charge sur cet ordinateur.")
        raise WallpaperError("Ce fichier n'est pas une image JPEG, PNG ou WEBP.")
    dims = reader.size()  # lu dans l'en-tête, avant tout décodage
    if dims.isValid():
        if dims.width() * dims.height() > MAX_IMPORT_PIXELS:
            raise WallpaperError("Cette image est trop grande.")
        if dims.width() < MIN_WIDTH or dims.height() < MIN_HEIGHT:
            raise WallpaperError("Cette image est trop petite pour un fond d'écran.")

    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    existing = sorted(dest_dir.glob(f"{PREFIX}{digest}-*.*")) if dest_dir.is_dir() else []
    if existing:
        return wallpaper_from_file(existing[0])  # déjà importée : même copie

    image = reader.read()
    if image.isNull():
        raise WallpaperError("Cette image est illisible ou abîmée.")
    if image.width() < MIN_WIDTH or image.height() < MIN_HEIGHT:
        raise WallpaperError("Cette image est trop petite pour un fond d'écran.")
    if image.width() > STORED_MAX.width() or image.height() > STORED_MAX.height():
        image = image.scaled(STORED_MAX, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    tone = analyze_tone(image)
    if image.hasAlphaChannel():
        extension, out_format, quality = "png", "PNG", -1
    else:
        image = image.convertToFormat(QImage.Format.Format_RGB888)
        extension, out_format, quality = "jpg", "JPEG", 90

    dest_dir.mkdir(parents=True, exist_ok=True)
    final = dest_dir / f"{PREFIX}{digest}-{tone}.{extension}"
    fd, tmp = tempfile.mkstemp(prefix=".import-", suffix=f".{extension}", dir=dest_dir)
    os.close(fd)
    try:
        if not image.save(tmp, out_format, quality):
            raise WallpaperError("Impossible d'enregistrer la copie de l'image.")
        os.replace(tmp, final)
    finally:
        Path(tmp).unlink(missing_ok=True)
    log.info("fond importé : %s → %s", source, final)
    return wallpaper_from_file(final)


def wallpaper_from_file(path: Path) -> Wallpaper:
    """Reconstruit un fond importé depuis son nom `perso-<empreinte>-<tonalité>.<ext>`."""
    stem = path.stem
    tone = "dark" if stem.endswith("-dark") else "light"
    return Wallpaper(stem.rsplit("-", 1)[0], "Mon image", path, tone, False)


def list_imported(dest_dir: Path) -> list[Wallpaper]:
    """Fonds importés, du plus ancien au plus récent."""
    if not dest_dir.is_dir():
        return []
    files = [p for p in dest_dir.iterdir()
             if p.is_file() and p.name.startswith(PREFIX) and p.suffix in (".jpg", ".png")]
    files.sort(key=lambda p: p.stat().st_mtime)
    return [wallpaper_from_file(p) for p in files]
