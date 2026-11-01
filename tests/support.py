"""Outils communs aux tests : application Qt hors écran et configuration jetable."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from sigildesk.infra.paths import DEFAULT_CONFIG  # noqa: E402

_APP = None


def qt_app():
    """Une seule QGuiApplication pour toute la suite (Qt n'en tolère qu'une)."""
    global _APP
    from PySide6.QtGui import QGuiApplication

    _APP = QGuiApplication.instance() or QGuiApplication(["tests"])
    return _APP


def default_document() -> dict:
    return json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))


class TempDir:
    """Dossier temporaire supprimé à la fin du test (`self.addCleanup`)."""

    def __init__(self, test):
        self._tmp = tempfile.TemporaryDirectory(prefix="sigildesk-test-")
        test.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name)


def make_store(test, document: dict | None = None):
    from sigildesk.infra.config_store import ConfigStore

    tmp = TempDir(test)
    path = tmp.path / "config" / "config.json"
    if document is not None:
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(document), encoding="utf-8")
    store = ConfigStore(path, DEFAULT_CONFIG)
    store.load()
    return store, tmp.path
