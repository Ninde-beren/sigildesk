"""Chemins locaux reçus du QML : les sélecteurs de fichiers et de dossiers renvoient des URL `file://`."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl


def url_from_qml(value: str) -> Path | None:
    """Chemin local depuis l'URL d'un sélecteur (`file:///…`) ; `None` si ce n'est pas un fichier local."""
    url = QUrl(value)
    if url.isLocalFile():
        return Path(url.toLocalFile())
    if not url.scheme() and value.startswith("/"):
        return Path(value)
    return None
