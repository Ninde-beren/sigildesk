"""Mesures et couleurs de l'interface, en version standard et en mode confort.

Le mode confort agrandit les textes (18–20 px au lieu de 14–16 px), les
surfaces cliquables et l'anneau de focus, et renforce les contrastes. Il ne
touche ni à l'échelle ni à la résolution de LXQt : seules ces valeurs changent.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from PySide6.QtCore import Property, QObject, Signal


@dataclass(frozen=True)
class Metrics:
    fontSmall: int
    fontBody: int
    fontLabel: int
    fontTitle: int
    fontPanelTitle: int
    fontClock: int
    iconSize: int
    tileWidth: int
    tileHeight: int
    tileGap: int
    controlHeight: int
    focusWidth: int
    radius: int
    dockHeight: int
    cardOpacity: float
    textColor: str
    mutedColor: str
    borderColor: str


STANDARD = Metrics(
    fontSmall=14, fontBody=15, fontLabel=15, fontTitle=22, fontPanelTitle=20, fontClock=56,
    iconSize=60, tileWidth=124, tileHeight=104, tileGap=44, controlHeight=44,
    focusWidth=3, radius=22, dockHeight=56, cardOpacity=0.86,
    textColor="#1D2935", mutedColor="#4B5A69", borderColor="#1A2B3B1F",
)
COMFORT = Metrics(
    fontSmall=18, fontBody=19, fontLabel=18, fontTitle=26, fontPanelTitle=24, fontClock=60,
    iconSize=64, tileWidth=136, tileHeight=116, tileGap=36, controlHeight=52,
    focusWidth=4, radius=24, dockHeight=60, cardOpacity=0.96,
    textColor="#0E1720", mutedColor="#2C3946", borderColor="#1A2B3B59",
)

# Signature « SigilDesk · v1.0 » : 12 px dans les deux modes, comme demandé.
SIGNATURE_SIZE = 12


class Theme(QObject):
    changed = Signal()

    def __init__(self, comfort: bool = False, parent: QObject | None = None):
        super().__init__(parent)
        self._comfort = comfort

    @property
    def metrics(self) -> Metrics:
        return COMFORT if self._comfort else STANDARD

    def _get_comfort(self) -> bool:
        return self._comfort

    def set_comfort(self, value: bool) -> None:
        if bool(value) != self._comfort:
            self._comfort = bool(value)
            self.changed.emit()

    comfort = Property(bool, _get_comfort, notify=changed)

    # Mesures : déclarées dans le corps de la classe, sinon Qt ne les voit pas.
    fontSmall = Property(int, lambda self: self.metrics.fontSmall, notify=changed)
    fontBody = Property(int, lambda self: self.metrics.fontBody, notify=changed)
    fontLabel = Property(int, lambda self: self.metrics.fontLabel, notify=changed)
    fontTitle = Property(int, lambda self: self.metrics.fontTitle, notify=changed)
    fontPanelTitle = Property(int, lambda self: self.metrics.fontPanelTitle, notify=changed)
    fontClock = Property(int, lambda self: self.metrics.fontClock, notify=changed)
    iconSize = Property(int, lambda self: self.metrics.iconSize, notify=changed)
    tileWidth = Property(int, lambda self: self.metrics.tileWidth, notify=changed)
    tileHeight = Property(int, lambda self: self.metrics.tileHeight, notify=changed)
    tileGap = Property(int, lambda self: self.metrics.tileGap, notify=changed)
    controlHeight = Property(int, lambda self: self.metrics.controlHeight, notify=changed)
    focusWidth = Property(int, lambda self: self.metrics.focusWidth, notify=changed)
    radius = Property(int, lambda self: self.metrics.radius, notify=changed)
    dockHeight = Property(int, lambda self: self.metrics.dockHeight, notify=changed)
    cardOpacity = Property(float, lambda self: self.metrics.cardOpacity, notify=changed)
    textColor = Property(str, lambda self: self.metrics.textColor, notify=changed)
    mutedColor = Property(str, lambda self: self.metrics.mutedColor, notify=changed)
    borderColor = Property(str, lambda self: self.metrics.borderColor, notify=changed)

    # Couleurs communes aux deux modes.
    accent = Property(str, lambda self: "#2763C9", constant=True)
    focusColor = Property(str, lambda self: "#1F56C2", constant=True)
    surface = Property(str, lambda self: "#FFFFFF", constant=True)
    surfaceAlt = Property(str, lambda self: "#F2F5F8", constant=True)
    pressed = Property(str, lambda self: "#E3EAF2", constant=True)
    danger = Property(str, lambda self: "#B3261E", constant=True)
    signatureSize = Property(int, lambda self: SIGNATURE_SIZE, constant=True)


# Garde-fou : chaque mesure de `Metrics` doit être exposée au QML.
assert all(hasattr(Theme, f.name) for f in fields(Metrics))
