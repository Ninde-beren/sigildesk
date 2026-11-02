"""Outillage de développement et de test : captures, géométrie, fenêtres imaginaires.

Rien ici ne sert en usage normal. `scripts/capture.py` et `tests/test_layout.py`
lancent l'application avec `--screenshot`, `--dump-geometry` ou
`--fenetres-essai`, et `app.py` délègue à ce module.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QTimer

from sigildesk.domain.windows import OpenWindow
from sigildesk.infra.window_manager import StaticWindowManager

log = logging.getLogger(__name__)

# nom court → (instance, classe, titre) d'une fenêtre imaginaire, comme wmctrl la montrerait.
SAMPLE_WINDOWS = {
    "youtube": ("www.youtube.com", "Chromium", "YouTube"),
    "facebook": ("www.facebook.com", "Chromium", "Facebook"),
    "internet": ("chromium", "Chromium", "Google - Chromium"),
    "images": ("pcmanfm-qt", "pcmanfm-qt", "Images"),
    "vlc": ("vlc", "vlc", "Souvenirs.mp4 - Lecteur multimédia VLC"),
    "photo": ("lximage-qt", "lximage-qt", "Aube.jpg"),
    "pdf": ("qpdfview", "qpdfview", "Recette.pdf"),
}


def sample_window_manager(names: str) -> StaticWindowManager:
    """`--fenetres-essai youtube,images` → gestionnaire de fenêtres factice."""
    windows = [
        OpenWindow(f"0x{n + 1:08x}", 0, 100 + n, *SAMPLE_WINDOWS[name])
        for n, name in enumerate(names.split(",")) if name in SAMPLE_WINDOWS
    ]
    return StaticWindowManager(windows)


def dump_geometry(window, path: Path) -> None:
    """Rectangles des zones nommées « geo_* », pour les tests anti-débordement."""
    from PySide6.QtCore import QRectF
    from PySide6.QtQuick import QQuickItem

    def walk(item: QQuickItem):
        # Arbre visuel : les éléments déclarés dans la fenêtre ont la fenêtre pour parent QObject.
        yield item
        for child in item.childItems():
            yield from walk(child)

    items = {}
    for item in walk(window.contentItem()):
        name = item.objectName()
        if not name.startswith("geo_"):
            continue
        rect = item.mapRectToScene(QRectF(0, 0, item.width(), item.height()))
        truncated = item.property("truncated")
        text = item.property("text")
        items[name] = {
            "x": rect.x(), "y": rect.y(), "w": rect.width(), "h": rect.height(),
            "visible": item.isVisible(),
            "truncated": bool(truncated) if truncated is not None else False,
            "text": text if isinstance(text, str) else None,
        }
    payload = {"window": {"w": window.width(), "h": window.height()}, "items": items}
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8")


class ReadyWatcher(QObject):
    """Appelle `callback` quand le fond d'écran est chargé et que la météo a fini de chercher.

    Interroge toutes les 50 ms, au plus `max_attempts` fois (10 s), puis laisse
    150 ms à Qt pour dessiner. Sert aux captures (`--screenshot`) et à la mesure
    du temps de démarrage (`--print-ready`).

    C'est un `QObject` à part entière, avec son propre `QTimer` enfant : PySide
    ne retient qu'une référence faible vers l'objet d'une méthode liée passée à
    `QTimer.singleShot`, et un veilleur sans parent serait ramassé avant de
    sonner. L'appelant garde aussi une référence sur lui.
    """

    def __init__(self, window, weather, callback: Callable[[], None], max_attempts: int = 200,
                 parent: QObject | None = None, extra: Callable[[], bool] | None = None):
        super().__init__(parent)
        self._window = window
        self._weather = weather
        self._callback = callback
        self._extra = extra  # condition supplémentaire (capture de la page Vérifier : rapport reçu)
        self._remaining = max_attempts
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._poll)

    def start(self) -> None:
        self._poll()

    def _settled(self) -> bool:
        return bool(self._window.property("imagesReady")) and self._weather.property("state") != "loading" \
            and not self._weather.property("searching") and (self._extra is None or self._extra())

    def _poll(self) -> None:
        self._remaining -= 1
        if self._settled() or self._remaining <= 0:
            self._timer.timeout.disconnect(self._poll)
            self._timer.timeout.connect(self._callback)
            self._timer.start(150)
        else:
            self._timer.start(50)


class DiagnosticsGate(QObject):
    """Vrai une fois `diagnosticsReady` reçu : la capture `--panel verification` attend le rapport."""

    def __init__(self, controller, parent: QObject | None = None):
        super().__init__(parent)
        self._done = False
        controller.diagnosticsReady.connect(self._mark)

    def _mark(self, *_) -> None:
        self._done = True

    def ready(self) -> bool:
        return self._done


def capture(app, window, screenshot: Path | None, geometry: Path | None) -> None:
    """Enregistre la capture et/ou la géométrie demandées, puis quitte (code 1 en cas d'échec)."""
    try:
        if geometry:
            dump_geometry(window, geometry)
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grabWindow().save(str(screenshot))
            log.info("capture enregistrée : %s", screenshot)
    except Exception:
        log.exception("capture impossible")
        app.exit(1)
    else:
        app.quit()
