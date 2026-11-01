"""Les fonds d'écran pour le QML : liste, aperçu, application, import et retrait.

Le fond affiché est le fond prévisualisé s'il y en a un, sinon le fond
enregistré ; `apply` fait de l'aperçu le fond enregistré, `cancel` l'abandonne.
Le disque (fonds livrés, copies importées) est l'affaire de
`infra.wallpaper_store`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, QObject, Qt, QUrl, Signal, Slot

from sigildesk.domain.settings import ConfigError
from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.wallpaper_store import (
    BUILTINS,
    DEFAULT_ID,
    FALLBACK_ID,
    MAX_IMPORTED,
    Wallpaper,
    WallpaperError,
    import_image,
    list_imported,
)
from sigildesk.ui.qml_files import url_from_qml

log = logging.getLogger(__name__)


class WallpaperModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    LabelRole = Qt.ItemDataRole.UserRole + 2
    SourceRole = Qt.ItemDataRole.UserRole + 3
    ToneRole = Qt.ItemDataRole.UserRole + 4
    BuiltinRole = Qt.ItemDataRole.UserRole + 5

    displayChanged = Signal()
    message = Signal(str)

    def __init__(self, store: ConfigStore, dest_dir: Path, parent: QObject | None = None):
        super().__init__(parent)
        self._store = store
        self._dest_dir = dest_dir
        self._items: list[Wallpaper] = []
        self._preview: str | None = None
        self._scan()
        self._current = self._usable(store.data["appearance"]["wallpaper"])

    # --- Données -------------------------------------------------------------------------

    def _scan(self) -> None:
        self._items = list(BUILTINS) + list_imported(self._dest_dir)

    def _find(self, wallpaper_id: str) -> Wallpaper | None:
        return next((w for w in self._items if w.id == wallpaper_id), None)

    def _usable(self, wallpaper_id: str) -> str:
        """Repli : fond demandé, sinon fond par défaut, sinon dégradé Brume."""
        for candidate in (wallpaper_id, DEFAULT_ID):
            wallpaper = self._find(candidate)
            if wallpaper and (wallpaper.path is None or wallpaper.path.is_file()):
                return candidate
        return FALLBACK_ID

    def _displayed(self) -> Wallpaper:
        return self._find(self._preview or self._current) or self._find(FALLBACK_ID)

    @staticmethod
    def _source(wallpaper: Wallpaper) -> str:
        return QUrl.fromLocalFile(str(wallpaper.path)).toString() if wallpaper.path else ""

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        if role == self.IdRole:
            return item.id
        if role in (self.LabelRole, Qt.ItemDataRole.DisplayRole):
            return item.label
        if role == self.SourceRole:
            return self._source(item)
        if role == self.ToneRole:
            return item.tone
        if role == self.BuiltinRole:
            return item.builtin
        return None

    def roleNames(self) -> dict:
        return {
            self.IdRole: QByteArray(b"wallpaperId"),
            self.LabelRole: QByteArray(b"label"),
            self.SourceRole: QByteArray(b"source"),
            self.ToneRole: QByteArray(b"tone"),
            self.BuiltinRole: QByteArray(b"builtin"),
        }

    def _reset(self) -> None:
        self.beginResetModel()
        self._scan()
        self.endResetModel()

    # --- Propriétés lues par le fond de l'accueil -----------------------------------------

    source = Property(str, lambda self: self._source(self._displayed()), notify=displayChanged)
    tone = Property(str, lambda self: self._displayed().tone, notify=displayChanged)
    currentId = Property(str, lambda self: self._current, notify=displayChanged)
    selectedId = Property(str, lambda self: self._preview or self._current, notify=displayChanged)
    previewing = Property(bool, lambda self: self._preview is not None and self._preview != self._current,
                          notify=displayChanged)
    selectedIsImported = Property(bool, lambda self: not self._displayed().builtin, notify=displayChanged)

    # --- Actions -----------------------------------------------------------------------------

    @Slot(str)
    def preview(self, wallpaper_id: str) -> None:
        if self._find(wallpaper_id):
            self._preview = wallpaper_id
            self.displayChanged.emit()

    @Slot()
    def cancel(self) -> None:
        if self._preview is not None:
            self._preview = None
            self.displayChanged.emit()

    @Slot(result=bool)
    def apply(self) -> bool:
        if self._preview is None:
            return True
        if not self._save(self._preview):
            return False
        self._current, self._preview = self._preview, None
        self.displayChanged.emit()
        return True

    @Slot(result=bool)
    def reset(self) -> bool:
        """Revient au fond livré par défaut, enregistré aussitôt."""
        target = self._usable(DEFAULT_ID)
        if not self._save(target):
            return False
        self._current, self._preview = target, None
        self.displayChanged.emit()
        return True

    def _save(self, wallpaper_id: str) -> bool:
        document = self._store.copy()
        document["appearance"]["wallpaper"] = wallpaper_id
        try:
            self._store.replace(document)
        except (ConfigError, OSError) as exc:
            log.error("fond non enregistré : %s", exc)
            self.message.emit("Impossible d'enregistrer le fond d'écran.")
            return False
        return True

    @Slot(str, result=str)
    def importFile(self, file_url: str) -> str:
        """Importe puis prévisualise ; renvoie un message d'erreur ou une chaîne vide."""
        path = url_from_qml(file_url)
        if path is None:
            return "Choisissez une image enregistrée sur cet ordinateur ou sur une clé USB."
        if len(list_imported(self._dest_dir)) >= MAX_IMPORTED:
            return f"Vous avez déjà {MAX_IMPORTED} images. Retirez-en une avant d'en ajouter."
        try:
            wallpaper = import_image(path, self._dest_dir)
        except WallpaperError as exc:
            return str(exc)
        except OSError as exc:
            log.error("import impossible : %s", exc)
            return "Impossible de lire ou de copier cette image."
        self._reset()
        self.preview(wallpaper.id)
        return ""

    @Slot(str, result=bool)
    def removeImported(self, wallpaper_id: str) -> bool:
        """Supprime la copie gardée par SigilDesk (jamais l'original)."""
        wallpaper = self._find(wallpaper_id)
        if wallpaper is None or wallpaper.builtin or wallpaper.path is None or wallpaper.path.parent != self._dest_dir:
            return False
        if wallpaper_id == self._current and not self.reset():
            return False
        wallpaper.path.unlink(missing_ok=True)
        if self._preview == wallpaper_id:
            self._preview = None
        self._reset()
        self.displayChanged.emit()
        return True
