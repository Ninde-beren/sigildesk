"""`sigildesk --doctor` : diagnostic lisible, sans fenêtre, sans rien modifier.

Vérifie dans l'ordre ce dont l'accueil a besoin : modules QML, formats
d'image, HTTPS pour la météo, applications lancées par les tuiles, décodage
vidéo matériel, extinction par la session, mises à jour automatiques,
associations de fichiers. Chaque
ligne commence par [ok], [--] (optionnel absent), [MANQUE] ou [!!].
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sigildesk import APP_NAME, __version__


def run_doctor() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import __version__ as pyside_version
    from PySide6.QtCore import QUrl, qVersion
    from PySide6.QtGui import QGuiApplication, QImageReader
    from PySide6.QtNetwork import QSslSocket
    from PySide6.QtQml import QQmlApplicationEngine

    from sigildesk.domain.commands import CommandBuilder
    from sigildesk.infra.lxqt import SessionPower
    from sigildesk.infra.processes import find_program
    from sigildesk.infra.updates import auto_updates_status, reboot_required
    from sigildesk.infra.video_decoding import check_hardware_decoding
    from sigildesk.infra.xdg import check_associations

    app = QGuiApplication(sys.argv[:1])
    ok = True
    print(f"{APP_NAME} {__version__} — Python {sys.version.split()[0]}, PySide6 {pyside_version}, Qt {qVersion()}")
    print(f"Session : {os.environ.get('XDG_CURRENT_DESKTOP', '?')} ({os.environ.get('XDG_SESSION_TYPE', '?')})")

    engine = QQmlApplicationEngine()
    modules = ("QtQuick", "QtQuick.Controls.Basic", "QtQuick.Templates", "QtQuick.Dialogs", "QtQuick.Window")
    for module in modules:
        engine.clearComponentCache()
        engine.loadData(f"import QtQuick\nimport {module}\nItem {{}}".encode(), QUrl(f"file:///verif-{module}.qml"))
    loaded = len(engine.rootObjects()) == len(modules)
    print(f"[{'ok' if loaded else 'MANQUE'}] modules QML ({', '.join(modules)})")
    ok &= loaded

    formats = {bytes(f).decode() for f in QImageReader.supportedImageFormats()}
    for fmt, package in (("svg", "qt6-svg-plugins"), ("jpeg", "libqt6gui6"), ("png", "libqt6gui6"),
                         ("webp", "qt6-image-formats-plugins")):
        present = fmt in formats
        print(f"[{'ok' if present else 'MANQUE'}] images {fmt.upper()}" + ("" if present else f" (paquet {package})"))
        ok &= present or fmt == "webp"  # WEBP est un confort, pas une nécessité

    https = QSslSocket.supportsSsl()
    print(f"[{'ok' if https else 'MANQUE'}] HTTPS pour la météo "
          f"({QSslSocket.sslLibraryVersionString() or 'aucune bibliothèque TLS'})")

    tools = CommandBuilder(find_program).available_tools()
    for tool in tools:
        where = f" : {tool['path']}" if tool["path"] else " : absent"
        print(f"[{'ok' if tool['path'] else '--'}] {tool['label']}{where}")
    paths = {t["id"]: t["path"] for t in tools}
    if not (paths["chromium"] or paths["firefox"] or paths["xdg-open"]):
        ok = False
    decoding = check_hardware_decoding(find_program("vainfo"))
    print(f"[{'ok' if decoding.status == 'ok' else '--'}] décodage vidéo matériel : {decoding.label}"
          + (f"  → {decoding.hint}" if decoding.hint else ""))

    session = SessionPower.detect()
    print(f"[{'ok' if session else '--'}] extinction et redémarrage par la session LXQt"
          + ("" if session else " : indisponible ici, un guide s'affichera"))
    auto = auto_updates_status()
    print(f"[{'ok' if auto.enabled else '--'}] mises à jour automatiques"
          + ("" if auto.enabled else " : à régler avec scripts/install-system-deps.sh")
          + (f" (dernière passe {auto.last_run:%d/%m %H:%M})" if auto.last_run else ""))
    reboot = reboot_required()
    print(f"[{'!!' if reboot.required else 'ok'}] redémarrage {'nécessaire' if reboot.required else 'non nécessaire'}"
          + (f" ({', '.join(reboot.packages)})" if reboot.packages else ""))

    xdg_mime = str(Path(paths["xdg-open"]).with_name("xdg-mime")) if paths["xdg-open"] else ""
    for report in check_associations(xdg_mime if xdg_mime and Path(xdg_mime).exists() else None):
        mark = {"ok": "ok", "autre": "!!", "aucune": "--"}[report.status]
        hint = "" if report.status == "ok" else f"  → {report.fix_command}"
        print(f"[{mark}] {report.label} ({report.mime}) : {report.current or 'aucune'}{hint}")
    del app
    return 0 if ok else 1
