"""« Mes favoris » pour le QML : jusqu'à 12 liens, enregistrés dans la configuration.

Chaque modification est validée (`domain.favorites`) puis enregistrée aussitôt
par `ConfigStore.replace`. Si l'écriture échoue, le modèle ne change pas : la
liste affichée reste celle du disque.
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, QObject, Qt, Signal, Slot

from sigildesk.domain import catalog
from sigildesk.domain.favorites import FavoriteError, validate_favorite
from sigildesk.domain.settings import ConfigError
from sigildesk.domain.urls import display_host
from sigildesk.infra.config_store import ConfigStore

log = logging.getLogger(__name__)


class FavoritesModel(QAbstractListModel):
    NameRole = Qt.ItemDataRole.UserRole + 1
    UrlRole = Qt.ItemDataRole.UserRole + 2
    IconRole = Qt.ItemDataRole.UserRole + 3
    HostRole = Qt.ItemDataRole.UserRole + 4

    countChanged = Signal()
    topChanged = Signal()

    HOME_COUNT = 4  # favoris repris en troisième rangée de l'accueil, dans l'ordre choisi

    def __init__(self, store: ConfigStore, parent: QObject | None = None):
        super().__init__(parent)
        self._store = store
        self._items: list[dict] = list(store.data["favorites"])

    # --- QAbstractListModel ---------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        item = self._items[index.row()]
        if role in (self.NameRole, Qt.ItemDataRole.DisplayRole):
            return item["name"]
        if role == self.UrlRole:
            return item["url"]
        if role == self.IconRole:
            return item["icon"]
        if role == self.HostRole:
            return display_host(item["url"])
        return None

    def roleNames(self) -> dict:
        return {
            self.NameRole: QByteArray(b"name"),
            self.UrlRole: QByteArray(b"url"),
            self.IconRole: QByteArray(b"iconName"),
            self.HostRole: QByteArray(b"host"),
        }

    # --- Persistance -------------------------------------------------------------------

    def _persist(self, items: list[dict]) -> str:
        """Enregistre `items` ; renvoie un message d'erreur, ou « » si c'est fait."""
        document = self._store.copy()
        document["favorites"] = items
        try:
            self._store.replace(document)
        except (ConfigError, OSError) as exc:
            log.error("favoris non enregistrés : %s", exc)
            return "Impossible d'enregistrer les favoris. Réessayez plus tard."
        return ""

    def _notify(self) -> None:
        self.countChanged.emit()
        self.topChanged.emit()

    def _top(self) -> list[dict]:
        return [
            {"index": i, "name": item["name"], "iconName": item["icon"], "host": display_host(item["url"])}
            for i, item in enumerate(self._items[: self.HOME_COUNT])
        ]

    # --- API pour le QML -----------------------------------------------------------------

    count = Property(int, lambda self: len(self._items), notify=countChanged)
    maximum = Property(int, lambda self: catalog.MAX_FAVORITES, constant=True)
    canAdd = Property(bool, lambda self: len(self._items) < catalog.MAX_FAVORITES, notify=countChanged)
    top = Property("QVariantList", lambda self: self._top(), notify=topChanged)

    @Slot(int, result=str)
    def urlAt(self, row: int) -> str:
        return self._items[row]["url"] if 0 <= row < len(self._items) else ""

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict:
        return dict(self._items[row]) if 0 <= row < len(self._items) else {}

    @Slot(str, str, result=str)
    def check(self, name: str, url: str) -> str:
        """Message d'erreur pour une saisie en cours, ou chaîne vide si elle est correcte."""
        try:
            validate_favorite(name, url, catalog.FAVORITE_ICON_IDS[0])
        except FavoriteError as exc:
            return str(exc)
        return ""

    @Slot(str, str, str, result=str)
    def add(self, name: str, url: str, icon: str) -> str:
        if len(self._items) >= catalog.MAX_FAVORITES:
            return f"La liste est pleine ({catalog.MAX_FAVORITES} favoris au plus)."
        try:
            favorite = validate_favorite(name, url, icon)
        except FavoriteError as exc:
            return str(exc)
        error = self._persist(self._items + [favorite])
        if error:
            return error
        row = len(self._items)
        self.beginInsertRows(QModelIndex(), row, row)
        self._items.append(favorite)
        self.endInsertRows()
        self._notify()
        return ""

    @Slot(int, str, str, str, result=str)
    def update(self, row: int, name: str, url: str, icon: str) -> str:
        if not 0 <= row < len(self._items):
            return "Ce favori n'existe plus."
        try:
            favorite = validate_favorite(name, url, icon)
        except FavoriteError as exc:
            return str(exc)
        items = list(self._items)
        items[row] = favorite
        error = self._persist(items)
        if error:
            return error
        self._items = items
        index = self.index(row)
        self.dataChanged.emit(index, index)
        self.topChanged.emit()
        return ""

    @Slot(int, result=bool)
    def remove(self, row: int) -> bool:
        if not 0 <= row < len(self._items):
            return False
        if self._persist(self._items[:row] + self._items[row + 1:]):
            return False
        self.beginRemoveRows(QModelIndex(), row, row)
        del self._items[row]
        self.endRemoveRows()
        self._notify()
        return True

    @Slot(int, int, result=bool)
    def move(self, row: int, delta: int) -> bool:
        """Déplace d'un cran (`delta` = -1 ou +1)."""
        target = row + delta
        if delta not in (-1, 1) or not 0 <= row < len(self._items) or not 0 <= target < len(self._items):
            return False
        items = list(self._items)
        items[row], items[target] = items[target], items[row]
        if self._persist(items):
            return False
        # beginMoveRows attend la position d'insertion avant suppression.
        destination = target + 1 if delta == 1 else target
        self.beginMoveRows(QModelIndex(), row, row, QModelIndex(), destination)
        self._items = items
        self.endMoveRows()
        self.topChanged.emit()
        return True

    def reload(self) -> None:
        """Relit la liste depuis la configuration (après un rechargement externe)."""
        self.beginResetModel()
        self._items = list(self._store.data["favorites"])
        self.endResetModel()
        self._notify()
