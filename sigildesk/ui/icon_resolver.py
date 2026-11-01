"""Résout un nom d'icône (« youtube », « meteo-pluie ») en URL de fichier pour le QML.

Une icône déposée par l'utilisateur dans `~/.local/share/sigildesk/icons/`
(même nom, `.svg` ou `.png`) remplace celle livrée. Le résultat est mémorisé :
le QML demande chaque icône à chaque liaison, et le disque n'a pas besoin
d'être interrogé plus d'une fois par nom (une icône déposée pendant que
SigilDesk tourne est prise en compte au prochain démarrage).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Slot


class IconResolver(QObject):
    def __init__(self, packaged_dir: Path, user_dir: Path, parent: QObject | None = None):
        super().__init__(parent)
        self._folders = (user_dir, packaged_dir)  # l'utilisateur d'abord
        self._cache: dict[str, str] = {}

    @Slot(str, result=str)
    def url(self, name: str) -> str:
        if not name or "/" in name or name.startswith("."):
            return ""
        try:
            return self._cache[name]
        except KeyError:
            pass
        url = ""
        for folder in self._folders:
            for extension in (".svg", ".png"):
                candidate = folder / f"{name}{extension}"
                if candidate.is_file():
                    url = QUrl.fromLocalFile(str(candidate)).toString()
                    break
            if url:
                break
        self._cache[name] = url
        return url
