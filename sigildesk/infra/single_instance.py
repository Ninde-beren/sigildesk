"""Une seule instance par utilisateur : le second lancement réveille le premier.

Cliquer sur SigilDesk dans le menu LXQt alors qu'il est réduit le ramène au
premier plan au lieu d'ouvrir une deuxième fenêtre.
"""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket

log = logging.getLogger(__name__)


def default_name() -> str:
    return f"sigildesk-{os.getuid()}"


class SingleInstance(QObject):
    activated = Signal()

    def __init__(self, name: str | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self.name = name or default_name()
        self._server: QLocalServer | None = None

    def notify_running(self, timeout_ms: int = 400) -> bool:
        """Vrai si une instance tourne déjà (elle a alors été prévenue)."""
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if not socket.waitForConnected(timeout_ms):
            return False
        socket.write(b"show\n")
        socket.flush()
        socket.waitForBytesWritten(timeout_ms)
        socket.disconnectFromServer()
        return True

    def listen(self) -> bool:
        # Une socket orpheline (plantage précédent) bloquerait l'écoute.
        QLocalServer.removeServer(self.name)
        server = QLocalServer(self)
        server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        if not server.listen(self.name):
            log.warning("instance unique indisponible : %s", server.errorString())
            return False
        server.newConnection.connect(self._on_connection)
        self._server = server
        return True

    def _on_connection(self) -> None:
        while self._server and self._server.hasPendingConnections():
            connection = self._server.nextPendingConnection()
            connection.readyRead.connect(lambda c=connection: self._on_message(c))
            connection.disconnected.connect(connection.deleteLater)

    def _on_message(self, connection: QLocalSocket) -> None:
        if bytes(connection.readAll()).strip().startswith(b"show"):
            self.activated.emit()
