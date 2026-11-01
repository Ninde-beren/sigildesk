"""Point d'entrée : assemble les couches et lance l'interface.

`main` lit les options (`cli`), prépare le journal, puis construit chaque
objet dans l'ordre de ses dépendances : réglages (`infra.config_store`),
modèles et services (`ui`), enfin le moteur QML auquel ils sont exposés par
nom. C'est le seul endroit où les couches se rencontrent : `domain` ne connaît
rien d'autre, `infra` connaît `domain`, `ui` connaît les deux.

Les imports Qt sont faits dans les fonctions : `--version` et `--doctor`
n'ouvrent pas de fenêtre, et certaines variables d'environnement Qt doivent
être posées avant le premier import.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

from sigildesk import APP_ID, APP_NAME, __version__
from sigildesk.cli import parse_args

log = logging.getLogger("sigildesk")
_T0 = time.monotonic()


def setup_logging(log_file: Path) -> None:
    """Console (stderr) et journal tournant de 3 × 256 Ko dans `~/.local/state/sigildesk/`."""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s : %(message)s")
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)
    root.addHandler(console)
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=256_000, backupCount=2, encoding="utf-8")
        handler.setFormatter(formatter)
        root.addHandler(handler)
    except OSError:
        pass  # dossier d'état inaccessible : la console suffit


def _install_qt_message_handler() -> None:
    """Les messages de Qt et du QML rejoignent le journal, sous `sigildesk.qml`."""
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    qml_log = logging.getLogger("sigildesk.qml")
    levels = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def handler(kind, context, message):
        qml_log.log(levels.get(kind, logging.WARNING), message)

    qInstallMessageHandler(handler)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.doctor:
        from sigildesk.doctor import run_doctor

        return run_doctor()
    if os.geteuid() == 0:
        print("SigilDesk ne doit pas être lancé en root.", file=sys.stderr)
        return 2

    if args.software or args.capture:
        os.environ["QT_QUICK_BACKEND"] = "software"
    # Style léger pour le sélecteur de fichiers de secours (sans module QtQuickControls2 en Python).
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Basic"
    return run_gui(args)


def run_gui(args) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow  # noqa: F401  (la racine QML est typée QQuickWindow)

    from sigildesk import devtools
    from sigildesk.domain.commands import CommandBuilder
    from sigildesk.infra.config_store import ConfigStore
    from sigildesk.infra.http_client import QtHttpClient
    from sigildesk.infra.launcher import Launcher
    from sigildesk.infra.lxqt import SessionPower
    from sigildesk.infra.open_meteo import OpenMeteo
    from sigildesk.infra.paths import DEFAULT_CONFIG, ICONS_DIR, QML_DIR, UserPaths
    from sigildesk.infra.processes import find_program
    from sigildesk.infra.single_instance import SingleInstance
    from sigildesk.infra.weather_cache import WeatherCache
    from sigildesk.infra.window_manager import WindowManager
    from sigildesk.ui.controller import AppController
    from sigildesk.ui.favorites_model import FavoritesModel
    from sigildesk.ui.icon_resolver import IconResolver
    from sigildesk.ui.system_status import SystemStatus
    from sigildesk.ui.theme import Theme
    from sigildesk.ui.update_monitor import UpdateMonitor
    from sigildesk.ui.wallpaper_model import WallpaperModel
    from sigildesk.ui.weather_service import WeatherService
    from sigildesk.ui.windows_model import WindowsModel

    paths = UserPaths.from_environment(args.root)
    setup_logging(paths.log_file)
    _install_qt_message_handler()
    log.info("démarrage de %s %s%s", APP_NAME, __version__, " (autostart)" if args.autostart else "")

    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName(APP_ID)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName(APP_ID)
    app.setWindowIcon(QIcon(str(ICONS_DIR / "sigildesk.svg")))

    # Une seule fenêtre par utilisateur : un second lancement réveille la première.
    instance = SingleInstance()
    if not args.capture:
        if instance.notify_running():
            log.info("SigilDesk tourne déjà : fenêtre existante ramenée au premier plan")
            return 0
        instance.listen()

    # 1. Réglages et thème.
    store = ConfigStore(paths.config_file, DEFAULT_CONFIG)
    report = store.load()
    theme = Theme(store.data["appearance"]["comfort"])

    # 2. Accès au système.
    launcher = Launcher(CommandBuilder(find_program))
    if args.fenetres_essai:
        manager = devtools.sample_window_manager(args.fenetres_essai)
    else:
        manager = None if args.capture else WindowManager.detect()

    # 3. Objets exposés au QML.
    favorites = FavoritesModel(store)
    wallpapers = WallpaperModel(store, paths.wallpapers_dir)
    controller = AppController(
        store, theme, favorites, launcher, paths, SessionPower.detect(), app.quit,
        start_fullscreen=not args.windowed and not args.capture and store.data["window"]["mode"] == "plein-ecran",
        window_manager=manager,
    )
    open_windows = WindowsModel(manager, controller.describe_window)
    status = SystemStatus()
    icons = IconResolver(ICONS_DIR, paths.icons_dir)
    weather = WeatherService(store, OpenMeteo(), WeatherCache(paths.weather_cache), QtHttpClient(),
                             network=not args.no_network)
    updates = UpdateMonitor()
    instance.activated.connect(controller.activateRequested)

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    for name, value in (
        ("app", controller), ("theme", theme), ("favorites", favorites), ("wallpapers", wallpapers),
        ("webTiles", controller.web_tiles), ("localTiles", controller.local_tiles),
        ("systemStatus", status), ("icons", icons), ("weather", weather), ("updates", updates),
        ("openWindows", open_windows),
    ):
        context.setContextProperty(name, value)
    context.setContextProperty("initialWidth", args.width)
    context.setContextProperty("initialHeight", args.height)
    engine.load(QML_DIR / "Main.qml")
    if not engine.rootObjects():
        log.critical("l'interface QML n'a pas pu être chargée")
        return 1
    window = engine.rootObjects()[0]

    QTimer.singleShot(0, weather.start)  # première actualisation, sans retarder l'affichage
    if not args.capture:
        QTimer.singleShot(20_000, updates.start)  # laisse la session finir de s'ouvrir avant de proposer un redémarrage
    if report.status in ("recovered", "future"):
        QTimer.singleShot(800, lambda: controller.toast.emit("Réglages illisibles : réglages par défaut utilisés."))

    # 4. Modes d'essai : capture puis sortie, ou mesure du temps de démarrage.
    watcher = None  # gardé en vie jusqu'à la fin de la boucle d'événements
    if args.capture:
        open_windows.refresh()
        if args.panel:
            QTimer.singleShot(0, lambda: controller.panelRequested.emit(args.panel))
        watcher = devtools.ReadyWatcher(window, weather, lambda: devtools.capture(
            app, window, args.screenshot, args.dump_geometry), parent=app)  # noqa: F821 (« window » effacé après app.exec)
    elif args.print_ready:
        watcher = devtools.ReadyWatcher(window, weather, lambda: print(
            f"SIGILDESK_READY ms={int((time.monotonic() - _T0) * 1000)}", flush=True), parent=app)
    if watcher is not None:
        watcher.start()

    code = app.exec()
    # Le moteur QML d'abord : ses liaisons lisent encore les objets Python.
    del watcher
    del window
    del engine
    return code
