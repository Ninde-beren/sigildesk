"""GET JSON asynchrone sur la boucle d'événements Qt : aucun fil, l'interface ne bloque jamais.

Le résultat arrive par rappel : `callback(données, None)` en cas de succès,
`callback(None, "hors-ligne")` si le réseau manque, `callback(None, "service")`
si le serveur répond n'importe quoi. Une erreur HTTP accompagnée d'un corps
JSON (Open-Meteo : `{"error": true, "reason": …}`) est transmise comme une
donnée : c'est au fournisseur d'en faire un message.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from PySide6.QtCore import QObject, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from sigildesk import __version__

MAX_BODY = 512 * 1024
TIMEOUT_MS = 15_000

Callback = Callable[[object, "str | None"], None]

# Erreurs qui signifient « pas de réseau », par opposition à « le service répond mal ».
OFFLINE_ERRORS = frozenset({
    QNetworkReply.NetworkError.HostNotFoundError,
    QNetworkReply.NetworkError.ConnectionRefusedError,
    QNetworkReply.NetworkError.RemoteHostClosedError,
    QNetworkReply.NetworkError.TimeoutError,
    QNetworkReply.NetworkError.OperationCanceledError,
    QNetworkReply.NetworkError.TemporaryNetworkFailureError,
    QNetworkReply.NetworkError.NetworkSessionFailedError,
    QNetworkReply.NetworkError.UnknownNetworkError,
    QNetworkReply.NetworkError.ProxyConnectionRefusedError,
    QNetworkReply.NetworkError.ProxyNotFoundError,
})


class QtHttpClient(QObject):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._manager = QNetworkAccessManager(self)

    def get_json(self, url: str, callback: Callback) -> None:
        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(b"User-Agent", f"SigilDesk/{__version__}".encode())
        request.setTransferTimeout(TIMEOUT_MS)
        reply = self._manager.get(request)
        reply.finished.connect(lambda: self._finished(reply, callback))

    @staticmethod
    def _finished(reply: QNetworkReply, callback: Callback) -> None:
        try:
            body = bytes(reply.read(MAX_BODY + 1))
            error = reply.error()
            if error in OFFLINE_ERRORS:
                callback(None, "hors-ligne")
                return
            if len(body) > MAX_BODY:
                callback(None, "service")
                return
            try:
                data = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                callback(None, "service" if body or error != QNetworkReply.NetworkError.NoError else "hors-ligne")
                return
            callback(data, None)
        finally:
            reply.deleteLater()
