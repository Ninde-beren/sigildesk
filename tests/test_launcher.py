import unittest
from pathlib import Path

import support

from sigildesk.domain.commands import CommandBuilder, LaunchError
from sigildesk.infra.launcher import Launcher
from sigildesk.infra.xdg import parse_user_dirs, resolve_folder


def fake_which(present):
    table = {name: f"/usr/bin/{name}" for name in present}
    return lambda name: table.get(name)


class BrowserCommandTests(unittest.TestCase):
    def test_chromium_preferred(self):
        builder = CommandBuilder(fake_which({"chromium", "firefox", "xdg-open"}))
        cmd = builder.browser_command("https://www.youtube.com/")
        self.assertEqual(cmd.argv(), ["/usr/bin/chromium", "https://www.youtube.com/"])

    def test_chromium_browser_name(self):
        builder = CommandBuilder(fake_which({"chromium-browser", "xdg-open"}))
        self.assertEqual(builder.browser_command("exemple.fr").program, "/usr/bin/chromium-browser")

    def test_system_fallback(self):
        builder = CommandBuilder(fake_which({"xdg-open", "firefox"}))
        cmd = builder.browser_command("https://exemple.fr/")
        self.assertEqual(cmd.argv(), ["/usr/bin/xdg-open", "https://exemple.fr/"])

    def test_firefox_choice(self):
        builder = CommandBuilder(fake_which({"chromium", "firefox", "xdg-open"}))
        self.assertEqual(builder.browser_command("exemple.fr", "firefox").program, "/usr/bin/firefox")

    def test_no_browser(self):
        with self.assertRaises(LaunchError):
            CommandBuilder(fake_which(set())).browser_command("https://exemple.fr/")

    def test_app_window_without_address_bar(self):
        builder = CommandBuilder(fake_which({"chromium", "xdg-open"}))
        cmd = builder.browser_command("facebook.com", "auto", app_window=True)
        self.assertEqual(cmd.argv(), ["/usr/bin/chromium", "--app=https://facebook.com/", "--start-maximized"])
        # Sans Chromium : fenêtre normale du navigateur du système.
        cmd = CommandBuilder(fake_which({"xdg-open"})).browser_command("facebook.com", "auto", app_window=True)
        self.assertEqual(cmd.argv(), ["/usr/bin/xdg-open", "https://facebook.com/"])
        cmd = CommandBuilder(fake_which({"firefox", "xdg-open"})).browser_command("facebook.com", "firefox", app_window=True)
        self.assertEqual(cmd.argv(), ["/usr/bin/firefox", "https://facebook.com/"])

    def test_app_window_cannot_smuggle_options(self):
        builder = CommandBuilder(fake_which({"chromium"}))
        cmd = builder.browser_command("https://exemple.fr/ --disable-web-security".replace(" ", ""), app_window=True)
        self.assertEqual(len(cmd.args), 2)
        self.assertTrue(cmd.args[0].startswith("--app=https://"))
        with self.assertRaises(LaunchError):
            builder.browser_command("--headless", app_window=True)

    def test_url_is_one_separate_argument(self):
        builder = CommandBuilder(fake_which({"chromium"}))
        cmd = builder.browser_command("https://exemple.fr/?q=a;b&c=$(id)")
        self.assertEqual(len(cmd.args), 1)
        self.assertEqual(cmd.args[0], "https://exemple.fr/?q=a;b&c=$(id)")

    def test_dangerous_urls_refused(self):
        builder = CommandBuilder(fake_which({"chromium", "xdg-open"}))
        for bad in ("--remote-debugging-port=9222", "javascript:alert(1)", "file:///etc/shadow"):
            with self.subTest(bad=bad), self.assertRaises(LaunchError):
                builder.browser_command(bad)


class FolderTests(unittest.TestCase):
    def test_file_manager_then_fallback(self):
        tmp = support.TempDir(self).path
        self.assertEqual(CommandBuilder(fake_which({"pcmanfm-qt", "xdg-open"})).folder_command(tmp).argv(),
                         ["/usr/bin/pcmanfm-qt", str(tmp)])
        self.assertEqual(CommandBuilder(fake_which({"xdg-open"})).folder_command(tmp).argv(),
                         ["/usr/bin/xdg-open", str(tmp)])

    def test_missing_folder(self):
        with self.assertRaises(LaunchError):
            CommandBuilder(fake_which({"pcmanfm-qt"})).folder_command(Path("/nexiste/pas"))

    def test_user_dirs_parsing(self):
        home = Path("/home/marie")
        text = 'XDG_PICTURES_DIR="$HOME/Images"\n# commentaire\nXDG_VIDEOS_DIR="/media/Vidéos"\nXDG_X="relatif"\n'
        dirs = parse_user_dirs(text, home)
        self.assertEqual(dirs["XDG_PICTURES_DIR"], home / "Images")
        self.assertEqual(dirs["XDG_VIDEOS_DIR"], Path("/media/Vidéos"))
        self.assertNotIn("XDG_X", dirs)

    def test_resolve_folder(self):
        home = support.TempDir(self).path
        (home / "Photos-perso").mkdir()
        user_dirs = home / "user-dirs.dirs"
        user_dirs.write_text('XDG_PICTURES_DIR="$HOME/Photos-perso"\n', encoding="utf-8")
        self.assertEqual(resolve_folder("pictures", home, user_dirs), (home / "Photos-perso", True))
        # Dossier absent : repli sur le dossier personnel, signalé, sans création.
        self.assertEqual(resolve_folder("videos", home, user_dirs), (home, False))
        self.assertFalse((home / "Vidéos").exists())
        self.assertEqual(resolve_folder("home", home, user_dirs), (home, True))
        # Chemin absolu choisi dans les Paramètres : tel quel s'il existe, sinon le dossier personnel.
        (home / "Clé").mkdir()
        self.assertEqual(resolve_folder(str(home / "Clé"), home, user_dirs), (home / "Clé", True))
        self.assertEqual(resolve_folder(str(home / "Débranchée"), home, user_dirs), (home, False))


class LauncherTests(unittest.TestCase):
    def test_runs_through_starter_without_shell(self):
        calls = []
        launcher = Launcher(CommandBuilder(fake_which({"chromium"})), lambda p, a, w: calls.append((p, a, w)) or True,
                            workdir=Path("/home/marie"))
        launcher.open_url("facebook.com")
        self.assertEqual(calls, [("/usr/bin/chromium", ["https://facebook.com/"], "/home/marie")])

    def test_start_failure(self):
        launcher = Launcher(CommandBuilder(fake_which({"chromium"})), lambda p, a, w: False)
        with self.assertRaises(LaunchError):
            launcher.open_url("https://exemple.fr/")


class ControllerTests(unittest.TestCase):
    """Les tuiles passent par la configuration validée, jamais par une commande du JSON."""

    def setUp(self):
        support.qt_app()
        from sigildesk.infra.paths import UserPaths
        from sigildesk.ui.controller import AppController
        from sigildesk.ui.favorites_model import FavoritesModel
        from sigildesk.ui.theme import Theme

        self.store, root = support.make_store(self)
        self.calls = []
        self.now = [100.0]
        self.home = root / "home"
        (self.home / "Images").mkdir(parents=True)
        launcher = Launcher(CommandBuilder(fake_which({"chromium", "pcmanfm-qt", "xdg-open"})),
                            lambda p, a, w: self.calls.append([p, *a]) or True)
        self.controller = AppController(
            self.store, Theme(), FavoritesModel(self.store), launcher, UserPaths.from_environment(root),
            None, lambda: None, clock=lambda: self.now[0], home=self.home)
        self.toasts = []
        self.controller.toast.connect(self.toasts.append)

    def test_diagnostics_report_hardware_as_a_list(self):
        """Le rapport matériel arrive au QML comme une liste de dictionnaires, depuis le fil de travail."""
        from unittest import mock

        from PySide6.QtCore import QEventLoop, QTimer

        from sigildesk.infra.hardware import Verification

        received = []
        loop = QEventLoop()
        self.controller.diagnosticsReady.connect(lambda tools, assoc, hw: (received.append((tools, assoc, hw)), loop.quit()))
        fake = [Verification("opengl", "rendu graphique", "ok", "accéléré par la puce (Mesa)")]
        with (mock.patch("sigildesk.ui.controller.collect_hardware_report", return_value=fake),
              mock.patch("sigildesk.ui.controller.check_associations", return_value=[])):
            self.controller.runDiagnostics()
            QTimer.singleShot(5000, loop.quit)
            loop.exec()
        self.assertEqual(len(received), 1, "diagnosticsReady non reçu")
        tools, associations, hardware = received[0]
        self.assertTrue(any(t["id"] == "chromium" and t["path"] for t in tools))
        self.assertEqual(associations, [])
        self.assertEqual(hardware, [{"id": "opengl", "label": "rendu graphique", "status": "ok",
                                     "detail": "accéléré par la puce (Mesa)", "hint": ""}])

    def test_web_tiles(self):
        self.assertEqual(self.controller.openTile("internet"), "ok")
        self.assertEqual(self.controller.openTile("youtube"), "ok")
        self.assertEqual(self.controller.openTile("facebook"), "ok")
        self.assertEqual(self.calls, [
            ["/usr/bin/chromium", "https://www.google.fr/"],  # Internet garde la barre d'adresse
            ["/usr/bin/chromium", "--app=https://www.youtube.com/", "--start-maximized"],
            ["/usr/bin/chromium", "--app=https://www.facebook.com/", "--start-maximized"],
        ])

    def test_about_link(self):
        self.assertEqual(self.controller.openLink("https://sigilbo.fr/"), "ok")
        self.assertEqual(self.controller.openLink("javascript:alert(1)"), "erreur")
        self.assertEqual(self.calls, [["/usr/bin/chromium", "https://sigilbo.fr/"]])

    def test_mail_not_configured_asks_for_setup(self):
        asked = []
        self.controller.mailSetupRequested.connect(lambda: asked.append(True))
        self.assertEqual(self.controller.openTile("mail"), "reglage")
        self.assertEqual(asked, [True])
        self.assertEqual(self.calls, [])

    def test_mail_after_setup(self):
        self.assertEqual(self.controller.setMail("free", ""), "")
        self.controller.openTile("mail")
        self.assertEqual(self.calls, [["/usr/bin/chromium", "--app=https://webmail.free.fr/", "--start-maximized"]])

    def test_local_tile_opens_folder(self):
        self.controller.openTile("photos")
        self.assertEqual(self.calls[0][0], "/usr/bin/pcmanfm-qt")

    def test_folder_setting_accepts_an_existing_folder(self):
        from PySide6.QtCore import QUrl

        usb = self.home / "Clé" / "Photos"
        usb.mkdir(parents=True)
        self.assertEqual(self.controller.setFolder("photos", str(usb)), "")
        self.assertEqual(self.controller.openTile("photos"), "ok")
        self.assertEqual(self.calls, [["/usr/bin/pcmanfm-qt", str(usb)]])
        row = next(r for r in self.controller.folderSettings if r["id"] == "photos")
        self.assertEqual((row["setting"], row["path"], row["found"], row["custom"], row["defaultLabel"]),
                         (str(usb), str(usb), True, True, "Images"))
        self.assertEqual(QUrl(self.controller.folderUrl("photos")).toLocalFile(), str(usb))
        self.assertEqual(self.controller.resetFolder("photos"), "")
        self.assertEqual(self.store.data["folders"]["photos"], "pictures")

    def test_folder_from_picker_url(self):
        chosen = self.home / "Vidéos de famille"
        chosen.mkdir()
        self.assertEqual(self.controller.setFolderFromUrl("videos", chosen.as_uri()), "")
        self.assertEqual(self.store.data["folders"]["videos"], str(chosen))

    def test_folder_setting_refusals(self):
        missing = self.home / "Nulle-part"
        self.assertEqual(self.controller.setFolder("photos", str(missing)), "Ce dossier est introuvable.")
        self.assertEqual(self.controller.setFolder("photos", "Images"), "Ce réglage n'est pas valide.")
        self.assertEqual(self.controller.setFolder("internet", str(self.home)), "Tuile inconnue.")
        self.assertEqual(self.controller.setFolderFromUrl("photos", "https://exemple.fr/"),
                         "Ce dossier n'est pas sur cet ordinateur.")
        self.assertEqual(self.store.data["folders"]["photos"], "pictures")

    def test_unplugged_folder_falls_back_to_home(self):
        usb = self.home / "Clé"
        usb.mkdir()
        self.assertEqual(self.controller.setFolder("files", str(usb)), "")
        usb.rmdir()
        self.assertEqual(self.controller.openTile("files"), "ok")
        self.assertEqual(self.calls, [["/usr/bin/pcmanfm-qt", str(self.home)]])
        self.assertIn(str(usb), self.toasts[-1])

    def test_double_click_does_not_open_twice(self):
        self.assertEqual(self.controller.openTile("internet"), "ok")
        self.now[0] += 1
        self.assertEqual(self.controller.openTile("internet"), "attente")
        self.now[0] += 10
        self.assertEqual(self.controller.openTile("internet"), "ok")
        self.assertEqual(len(self.calls), 2)

    def test_unknown_tile(self):
        self.assertEqual(self.controller.openTile("rm -rf"), "erreur")
        self.assertEqual(self.calls, [])

    def test_power_and_reboot_through_session(self):
        from sigildesk.infra.lxqt import SessionPower

        starts = []
        self.controller._session_power = SessionPower(
            "/usr/bin/dbus-send", None, lambda argv: "boolean true", lambda p, a: starts.append(a[-1]) or True)
        self.assertTrue(self.controller.powerOff())
        self.assertTrue(self.controller.reboot())
        self.assertEqual(starts, ["org.lxqt.session.powerOff", "org.lxqt.session.reboot"])

    def test_power_without_session_shows_guide(self):
        guide = []
        self.controller.powerGuideRequested.connect(lambda: guide.append(True))
        self.assertFalse(self.controller.powerOff())
        self.assertEqual(guide, [True])
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
