"""Les fenêtres ouvertes, telles que la barre du haut de l'accueil les montre.

Relevé toutes les 2 s par `infra.window_manager`, seulement quand l'accueil est
au premier plan (`setWatching`) : derrière une autre fenêtre, SigilDesk ne
consomme rien. Le nom et l'icône de chaque fenêtre sont décidés par la fonction
`describe` reçue du contrôleur, qui connaît les tuiles configurées.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Property, QAbstractListModel, QByteArray, QModelIndex, QObject, Qt, QTimer, Signal, Slot

from sigildesk.domain.windows import OpenWindow
from sigildesk.infra.window_manager import WindowManager

Describe = Callable[[OpenWindow], tuple[str, str]]


class WindowsModel(QAbstractListModel):
    IdRole = Qt.ItemDataRole.UserRole + 1
    LabelRole = Qt.ItemDataRole.UserRole + 2
    IconRole = Qt.ItemDataRole.UserRole + 3
    TitleRole = Qt.ItemDataRole.UserRole + 4
    countChanged = Signal()

    REFRESH_MS = 2000

    def __init__(self, manager: WindowManager | None, describe: Describe, parent: QObject | None = None):
        super().__init__(parent)
        self._manager = manager
        self._describe = describe
        self._rows: list[tuple[OpenWindow, str, str]] = []
        self._timer = QTimer(self)
        self._timer.setInterval(self.REFRESH_MS)
        self._timer.timeout.connect(self.refresh)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        window, label, icon = self._rows[index.row()]
        if role == self.IdRole:
            return window.id
        if role in (self.LabelRole, Qt.ItemDataRole.DisplayRole):
            return label
        if role == self.IconRole:
            return icon
        if role == self.TitleRole:
            return window.title
        return None

    def roleNames(self) -> dict:
        return {self.IdRole: QByteArray(b"windowId"), self.LabelRole: QByteArray(b"label"),
                self.IconRole: QByteArray(b"windowIcon"), self.TitleRole: QByteArray(b"title")}

    available = Property(bool, lambda self: self._manager is not None, constant=True)
    count = Property(int, lambda self: len(self._rows), notify=countChanged)

    @Slot(bool)
    def setWatching(self, watching: bool) -> None:
        if watching and self._manager:
            self.refresh()
            self._timer.start()
        else:
            self._timer.stop()

    @staticmethod
    def _signature(rows: list[tuple[OpenWindow, str, str]]) -> list[tuple[str, str, str]]:
        return [(window.id, label, icon) for window, label, icon in rows]

    @Slot()
    def refresh(self) -> None:
        if not self._manager:
            return
        rows = [(window, *self._describe(window)) for window in self._manager.list()]
        if self._signature(rows) == self._signature(self._rows):
            return  # rien n'a changé : pas de réinitialisation du modèle, donc pas de clignotement
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.countChanged.emit()

    @Slot(str, result=bool)
    def activate(self, window_id: str) -> bool:
        return bool(self._manager and self._manager.activate(window_id))
