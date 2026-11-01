"""Les tuiles fixes d'une rangée de l'accueil (« Sur internet », « Sur cet ordinateur »)."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Qt

from sigildesk.domain import catalog


class TilesModel(QAbstractListModel):
    """Lecture seule : les tuiles viennent de `catalog.TILES`, seul « à régler » varie."""

    IdRole = Qt.ItemDataRole.UserRole + 1
    LabelRole = Qt.ItemDataRole.UserRole + 2
    IconRole = Qt.ItemDataRole.UserRole + 3
    HintRole = Qt.ItemDataRole.UserRole + 4
    NeedsSetupRole = Qt.ItemDataRole.UserRole + 5

    _ROLE_NAMES = {
        IdRole: QByteArray(b"tileId"),
        LabelRole: QByteArray(b"label"),
        IconRole: QByteArray(b"iconName"),
        HintRole: QByteArray(b"hint"),
        NeedsSetupRole: QByteArray(b"needsSetup"),
    }

    def __init__(self, section: str, needs_setup: Callable[[str], bool], parent: QObject | None = None):
        super().__init__(parent)
        self._tiles = [tile for tile in catalog.TILES if tile.section == section]
        self._needs_setup = needs_setup  # une tuile « à régler » (messagerie non choisie) s'affiche autrement

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._tiles)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._tiles):
            return None
        tile = self._tiles[index.row()]
        if role == self.IdRole:
            return tile.id
        if role in (self.LabelRole, Qt.ItemDataRole.DisplayRole):
            return tile.label
        if role == self.IconRole:
            return tile.icon
        if role == self.HintRole:
            return tile.hint
        if role == self.NeedsSetupRole:
            return self._needs_setup(tile.id)
        return None

    def roleNames(self) -> dict:
        return dict(self._ROLE_NAMES)

    def refresh(self) -> None:
        """Après un réglage : les délégués relisent `needsSetup`."""
        if self._tiles:
            self.dataChanged.emit(self.index(0), self.index(len(self._tiles) - 1), [self.NeedsSetupRole])
