"""`app` côté QML : tuiles, réglages, maintenance, extinction.

Le contrôleur ne décide de rien lui-même : il lit la configuration validée
(`ConfigStore`), demande au `Launcher` d'ouvrir ce que la tuile désigne, et
traduit chaque résultat en un code court pour le QML (« ok », « retour »,
« attente », « reglage », « erreur ») ou en message (`toast`). Les réglages
passent tous par `_save`, qui valide, enregistre et prévient l'interface.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from sigildesk import AUTHOR, COPYRIGHT, PUBLISHER, USAGE, WEBSITE, __version__
from sigildesk.domain import catalog
from sigildesk.domain.commands import LaunchError
from sigildesk.domain.settings import BROWSERS, ConfigError
from sigildesk.domain.urls import UrlError, normalize_web_url
from sigildesk.domain.windows import OpenWindow, describe
from sigildesk.infra.config_store import ConfigStore
from sigildesk.infra.launcher import Launcher
from sigildesk.infra.lxqt import SessionPower, find_shortcut_conflicts, shortcut_files
from sigildesk.infra.paths import UserPaths, user_config_root
from sigildesk.infra.window_manager import WindowManager
from sigildesk.infra.xdg import check_associations, resolve_folder
from sigildesk.ui.favorites_model import FavoritesModel
from sigildesk.ui.theme import Theme
from sigildesk.ui.tiles_model import TilesModel

log = logging.getLogger(__name__)

# Un navigateur met plusieurs secondes à s'ouvrir sur un Celeron N3060 : un
# second clic pendant ce temps ouvrirait une deuxième fenêtre.
LAUNCH_COOLDOWN_S = 5.0

BROWSER_LABELS = {
    "auto": "Automatique (Chromium si présent)",
    "chromium": "Chromium",
    "firefox": "Firefox",
    "systeme": "Navigateur par défaut du système",
}


class AppController(QObject):
    settingsChanged = Signal()
    toast = Signal(str)
    mailSetupRequested = Signal()
    powerGuideRequested = Signal()
    minimizeRequested = Signal()
    activateRequested = Signal()
    panelRequested = Signal(str)
    diagnosticsReady = Signal("QVariantList", "QVariantList")

    def __init__(
        self,
        store: ConfigStore,
        theme: Theme,
        favorites: FavoritesModel,
        launcher: Launcher,
        paths: UserPaths,
        session_power: SessionPower | None,
        quit_app: Callable[[], None],
        clock: Callable[[], float] = time.monotonic,
        home: Path | None = None,
        start_fullscreen: bool = True,
        window_manager: WindowManager | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._store = store
        self._theme = theme
        self._favorites = favorites
        self._launcher = launcher
        self._paths = paths
        self._session_power = session_power
        self._quit = quit_app
        self._clock = clock
        self._home = home or Path.home()
        self._start_fullscreen = start_fullscreen
        self._windows = window_manager
        self._last_launch: dict[str, float] = {}
        self._app_hosts = self._compute_app_hosts()
        self.web_tiles = TilesModel("web", self.tile_needs_setup, self)
        self.local_tiles = TilesModel("local", self.tile_needs_setup, self)
        self._conflicts = self._detect_conflicts()

    # --- Lecture ---------------------------------------------------------------------

    def tile_needs_setup(self, tile_id: str) -> bool:
        """La tuile Mails reste « à régler » tant qu'aucune messagerie n'est choisie."""
        return tile_id == "mail" and not self._store.data["web"]["mail"]["url"]

    def _detect_conflicts(self) -> list[str]:
        try:
            return find_shortcut_conflicts(self._store.data["maintenance"]["shortcut"], shortcut_files())
        except ValueError:
            return []

    def _tile_url(self, tile_id: str) -> str:
        value = self._store.data["web"][tile_id]
        return value["url"] if isinstance(value, dict) else value  # « mail » est un objet {provider, url}

    def _compute_app_hosts(self) -> dict[str, tuple[str, str]]:
        """Hôte de chaque tuile ouverte en fenêtre d'application → (libellé, icône)."""
        hosts: dict[str, tuple[str, str]] = {}
        for tile in catalog.TILES:
            if tile.section == "web" and tile.app_window:
                host = urlsplit(self._tile_url(tile.id)).hostname if self._tile_url(tile.id) else None
                if host:
                    hosts[host] = (tile.label, tile.icon)
        return hosts

    def _user_dirs_file(self) -> Path:
        return user_config_root() / "user-dirs.dirs"

    version = Property(str, lambda self: __version__, constant=True)
    publisher = Property(str, lambda self: PUBLISHER, constant=True)
    author = Property(str, lambda self: AUTHOR, constant=True)
    website = Property(str, lambda self: WEBSITE, constant=True)
    copyright = Property(str, lambda self: COPYRIGHT, constant=True)
    usage = Property(str, lambda self: USAGE, constant=True)
    userName = Property(str, lambda self: self._store.data["user_name"], notify=settingsChanged)
    mailProvider = Property(str, lambda self: self._store.data["web"]["mail"]["provider"], notify=settingsChanged)
    mailUrl = Property(str, lambda self: self._store.data["web"]["mail"]["url"], notify=settingsChanged)
    browser = Property(str, lambda self: self._store.data["browser"], notify=settingsChanged)
    showLabels = Property(bool, lambda self: self._store.data["appearance"]["show_labels"], notify=settingsChanged)
    maintenanceShortcut = Property(str, lambda self: self._store.data["maintenance"]["shortcut"], constant=True)
    shortcutConflicts = Property("QVariantList", lambda self: self._conflicts, constant=True)
    canPowerOff = Property(bool, lambda self: self._session_power is not None, constant=True)
    startFullScreen = Property(bool, lambda self: self._start_fullscreen, constant=True)
    readOnlyConfig = Property(bool, lambda self: self._store.read_only, constant=True)
    configPath = Property(str, lambda self: str(self._store.path), constant=True)
    logPath = Property(str, lambda self: str(self._paths.log_file), constant=True)
    iconsPath = Property(str, lambda self: str(self._paths.icons_dir), constant=True)

    @Slot(result="QVariantList")
    def mailProviders(self) -> list[dict]:
        return [{"id": p.id, "label": p.label, "url": p.url} for p in catalog.MAIL_PROVIDERS]

    @Slot(result="QVariantList")
    def browserChoices(self) -> list[dict]:
        return [{"id": browser, "label": BROWSER_LABELS[browser]} for browser in BROWSERS]

    @Slot(result=str)
    def picturesFolderUrl(self) -> str:
        """Dossier Images, pour ouvrir le sélecteur d'image des fonds d'écran au bon endroit."""
        folder, _ = resolve_folder("pictures", self._home, self._user_dirs_file())
        return QUrl.fromLocalFile(str(folder)).toString()

    # --- Lancements -------------------------------------------------------------------

    def _cooling_down(self, key: str) -> bool:
        """Vrai si `key` a été lancée il y a moins de LAUNCH_COOLDOWN_S ; sinon note le lancement."""
        now = self._clock()
        last = self._last_launch.get(key)
        if last is not None and now - last < LAUNCH_COOLDOWN_S:
            return True
        self._last_launch[key] = now
        return False

    def _tile_folder(self, tile_id: str) -> tuple[Path, bool, str]:
        key = self._store.data["folders"][tile_id]
        folder, found = resolve_folder(key, self._home, self._user_dirs_file())
        return folder, found, key

    def _existing_window(self, tile: catalog.TileSpec) -> OpenWindow | None:
        """Fenêtre déjà ouverte par cette tuile, à ramener plutôt qu'en ouvrir une autre."""
        if self._windows is None:
            return None
        if tile.section == "local":
            return self._windows.find_folder_window(self._tile_folder(tile.id)[0])
        if tile.app_window:
            return self._windows.find_app_window(urlsplit(self._tile_url(tile.id)).hostname or "")
        return self._windows.find_browser_window()

    def describe_window(self, window: OpenWindow) -> tuple[str, str]:
        """(nom court, icône) d'une fenêtre ouverte, pour la barre des fenêtres."""
        return describe(window, self._app_hosts)

    def _open(self, key: str, launch: Callable[[], None]) -> str:
        """Lance avec garde anti-double-clic ; « ok », « attente » ou « erreur »."""
        if self._cooling_down(key):
            return "attente"
        try:
            launch()
        except LaunchError as exc:
            self._last_launch.pop(key, None)  # un échec ne doit pas bloquer un nouvel essai
            self.toast.emit(str(exc))
            return "erreur"
        return "ok"

    @Slot(str, result=str)
    def openTile(self, tile_id: str) -> str:
        """Lance la tuile ; renvoie « ok », « retour », « attente », « reglage » ou « erreur »."""
        tile = catalog.tile(tile_id)
        if tile is None:
            return "erreur"
        if self.tile_needs_setup(tile_id):
            self.mailSetupRequested.emit()
            return "reglage"
        existing = self._existing_window(tile)
        if existing and self._windows.activate(existing.id):
            log.info("tuile %s : fenêtre déjà ouverte ramenée (%s)", tile_id, existing.id)
            return "retour"

        if tile.section == "web":
            result = self._open(tile_id, lambda: self._launcher.open_url(
                self._tile_url(tile_id), self._store.data["browser"], tile.app_window))
            if result == "attente":
                self.toast.emit(f"{tile.label} est en cours d'ouverture, patientez un instant…")
            elif result == "ok":
                self.toast.emit(f"Ouverture de {tile.label}…")
            return result

        folder, found, key = self._tile_folder(tile_id)
        result = self._open(tile_id, lambda: self._launcher.open_folder(folder))
        if result == "attente":
            self.toast.emit(f"{tile.label} est en cours d'ouverture, patientez un instant…")
        elif result == "ok":
            if found:
                self.toast.emit(f"Ouverture de {tile.label}…")
            else:
                self.toast.emit(
                    f"Dossier « {catalog.FOLDER_LABELS[key]} » introuvable : ouverture du dossier personnel.")
        return result

    @Slot(int, result=str)
    def openFavorite(self, row: int) -> str:
        url = self._favorites.urlAt(row)
        if not url:
            return "erreur"
        result = self._open(f"favori:{url}", lambda: self._launcher.open_url(url, self._store.data["browser"]))
        if result == "ok":
            self.toast.emit(f"Ouverture de {self._favorites.get(row).get('name', 'ce site')}…")
        return result

    @Slot(str, result=str)
    def openLink(self, url: str) -> str:
        """Lien de la page À propos (site, attribution) : adresse http(s) validée, fenêtre normale."""
        return self._open(f"lien:{url}", lambda: self._launcher.open_url(url, self._store.data["browser"]))

    # --- Réglages -----------------------------------------------------------------------

    def _save(self, mutate: Callable[[dict], None]) -> str:
        """Applique `mutate` à une copie des réglages, valide, enregistre ; message d'erreur ou « »."""
        document = self._store.copy()
        mutate(document)
        try:
            self._store.replace(document)
        except ConfigError as exc:
            log.warning("réglage refusé : %s", exc)
            return "Ce réglage n'est pas valide."
        except OSError as exc:
            log.error("réglage non enregistré : %s", exc)
            return "Impossible d'enregistrer ce réglage."
        self._app_hosts = self._compute_app_hosts()
        self.settingsChanged.emit()
        self.web_tiles.refresh()
        return ""

    @Slot(bool, result=str)
    def setComfort(self, enabled: bool) -> str:
        error = self._save(lambda doc: doc["appearance"].__setitem__("comfort", bool(enabled)))
        if not error:
            self._theme.set_comfort(bool(enabled))
        return error

    @Slot(bool, result=str)
    def setShowLabels(self, show: bool) -> str:
        return self._save(lambda doc: doc["appearance"].__setitem__("show_labels", bool(show)))

    @Slot(str, result=str)
    def setUserName(self, name: str) -> str:
        name = (name or "").strip()
        if len(name) > catalog.MAX_USER_NAME:
            return f"{catalog.MAX_USER_NAME} caractères au plus."
        return self._save(lambda doc: doc.__setitem__("user_name", name))

    @Slot(str, result=str)
    def setBrowser(self, browser: str) -> str:
        if browser not in BROWSERS:
            return "Choix inconnu."
        return self._save(lambda doc: doc.__setitem__("browser", browser))

    @Slot(str, str, result=str)
    def setMail(self, provider: str, custom_url: str) -> str:
        if provider == "":
            mail = {"provider": "", "url": ""}
        elif provider == catalog.MAIL_CUSTOM:
            try:
                mail = {"provider": provider, "url": normalize_web_url(custom_url)}
            except UrlError as exc:
                return str(exc)
        elif catalog.mail_provider(provider):
            mail = {"provider": provider, "url": catalog.mail_provider(provider).url}
        else:
            return "Messagerie inconnue."
        return self._save(lambda doc: doc["web"].__setitem__("mail", mail))

    # --- Maintenance et extinction ----------------------------------------------------

    @Slot()
    def minimize(self) -> None:
        log.info("maintenance : SigilDesk réduit")
        self.minimizeRequested.emit()

    @Slot()
    def quit(self) -> None:
        log.info("maintenance : SigilDesk fermé")
        self._quit()

    def _leave(self, action: str) -> bool:
        """Après la confirmation du QML : la session LXQt éteint ou redémarre proprement."""
        how = self._session_power.request(action) if self._session_power else ""
        log.info("%s demandé : %s", action, how or "impossible, guide affiché")
        if not how:
            self.powerGuideRequested.emit()
            return False
        return True

    @Slot(result=bool)
    def powerOff(self) -> bool:
        return self._leave("poweroff")

    @Slot(result=bool)
    def reboot(self) -> bool:
        return self._leave("reboot")

    @Slot()
    def runDiagnostics(self) -> None:
        """Vérifie outils et associations dans un fil à part : `xdg-mime` est lent.

        Le fil ne touche à aucun objet Qt ; il émet seulement `diagnosticsReady`,
        que Qt met en file d'attente vers le fil de l'interface (connexion
        automatique entre fils), avec une copie des listes.
        """
        def work() -> None:
            tools = self._launcher.builder.available_tools()
            opener = next((t["path"] for t in tools if t["id"] == "xdg-open"), "")
            xdg_mime = str(Path(opener).with_name("xdg-mime")) if opener else ""
            reports = check_associations(xdg_mime if xdg_mime and Path(xdg_mime).exists() else None)
            associations = [
                {"label": r.label, "mime": r.mime, "current": r.current or "aucune", "status": r.status,
                 "fix": r.fix_command}
                for r in reports
            ]
            self.diagnosticsReady.emit(tools, associations)

        threading.Thread(target=work, name="diagnostic", daemon=True).start()
