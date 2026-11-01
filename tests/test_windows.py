"""Fenêtres ouvertes : relevé wmctrl, retour à la fenêtre d'une tuile, dock."""

import unittest
from pathlib import Path

import support

from sigildesk.domain.windows import OpenWindow, host_matches, parse_wmctrl
from sigildesk.infra.window_manager import StaticWindowManager, WindowManager

# Relevé réel dans la VM Lubuntu 26.04 (wmctrl -lxp), machine « lubuntu ».
WMCTRL = """0x01e00007 -1 2030 pcmanfm-qt.pcmanfm-qt   lubuntu pcmanfm-desktop0
0x02400007  0 2227 qterminal.qterminal     lubuntu lubuntu@lubuntu: ~
0x0180000e  0 5200 __main__.py.sigildesk   lubuntu SigilDesk
0x02a00008 -1 5227 lxqt-panel.lxqt-panel   lubuntu LXQt Panel
0x03000003  0 5308 www.youtube.com.Chromium  lubuntu YouTube
0x01e00051  0 2030 pcmanfm-qt.pcmanfm-qt   lubuntu Pictures
0x03000007  0 5308 chromium.Chromium       lubuntu Google - Chromium
"""


class ParseTests(unittest.TestCase):
    def test_parse_real_output(self):
        windows = parse_wmctrl(WMCTRL)
        self.assertEqual(len(windows), 7)
        youtube = windows[4]
        self.assertEqual((youtube.id, youtube.desktop, youtube.pid, youtube.instance, youtube.wm_class, youtube.title),
                         ("0x03000003", 0, 5308, "www.youtube.com", "Chromium", "YouTube"))
        self.assertEqual(windows[2].instance, "__main__.py")
        self.assertEqual(windows[1].title, "lubuntu@lubuntu: ~")

    def test_list_hides_desktop_panel_and_self(self):
        manager = WindowManager("/usr/bin/wmctrl", lambda argv: WMCTRL, own_pid=5200)
        titles = [w.title for w in manager.list()]
        self.assertEqual(titles, ["lubuntu@lubuntu: ~", "YouTube", "Pictures", "Google - Chromium"])

    def test_matching(self):
        manager = WindowManager("/usr/bin/wmctrl", lambda argv: WMCTRL, own_pid=5200)
        self.assertEqual(manager.find_app_window("www.youtube.com").id, "0x03000003")
        self.assertIsNone(manager.find_app_window("www.facebook.com"))
        self.assertEqual(manager.find_browser_window().id, "0x03000007")
        self.assertEqual(manager.find_folder_window(Path("/home/lubuntu/Pictures")).id, "0x01e00051")
        self.assertTrue(host_matches("outlook.live.com__mail_", "outlook.live.com"))
        self.assertFalse(host_matches("www.youtube.com.evil", "www.youtube.com"))

    def test_activate_uses_window_id_only(self):
        calls = []
        manager = WindowManager("/usr/bin/wmctrl", lambda argv: calls.append(argv) or "", own_pid=1)
        self.assertTrue(manager.activate("0x03000003"))
        self.assertFalse(manager.activate("--help"))
        self.assertEqual(calls, [["/usr/bin/wmctrl", "-i", "-a", "0x03000003"]])

    def test_detect(self):
        which = lambda name: "/usr/bin/wmctrl"
        self.assertIsNotNone(WindowManager.detect({"DISPLAY": ":0", "XDG_SESSION_TYPE": "x11"}, which))
        self.assertIsNone(WindowManager.detect({"WAYLAND_DISPLAY": "wayland-0", "XDG_SESSION_TYPE": "wayland"}, which))
        self.assertIsNone(WindowManager.detect({"DISPLAY": ":0"}, lambda name: None))


class ControllerTests(unittest.TestCase):
    def setUp(self):
        support.qt_app()
        from sigildesk.domain.commands import CommandBuilder
        from sigildesk.infra.launcher import Launcher
        from sigildesk.infra.paths import UserPaths
        from sigildesk.ui.controller import AppController
        from sigildesk.ui.favorites_model import FavoritesModel
        from sigildesk.ui.theme import Theme

        self.store, root = support.make_store(self)
        self.home = root / "home"
        (self.home / "Images").mkdir(parents=True)
        self.launched = []
        table = {"chromium": "/usr/bin/chromium", "pcmanfm-qt": "/usr/bin/pcmanfm-qt"}
        launcher = Launcher(CommandBuilder(table.get), lambda p, a, w: self.launched.append(a) or True)
        self.windows = StaticWindowManager([
            OpenWindow("0x01", 0, 10, "www.youtube.com", "Chromium", "Recette - YouTube"),
            OpenWindow("0x02", 0, 11, "pcmanfm-qt", "pcmanfm-qt", "Images"),
            OpenWindow("0x03", 0, 12, "vlc", "vlc", "Souvenirs.mp4 - Lecteur multimédia VLC"),
            OpenWindow("0x04", 0, 13, "featherpad", "FeatherPad", "notes.txt - FeatherPad"),
        ])
        self.activated = []
        original = self.windows.activate
        self.windows.activate = lambda wid: self.activated.append(wid) or original(wid)
        self.controller = AppController(self.store, Theme(), FavoritesModel(self.store), launcher,
                                        UserPaths.from_environment(root), None, lambda: None, home=self.home,
                                        window_manager=self.windows)

    def test_tile_brings_back_its_window(self):
        self.assertEqual(self.controller.openTile("youtube"), "retour")
        self.assertEqual(self.controller.openTile("photos"), "retour")
        self.assertEqual(self.activated, ["0x01", "0x02"])
        self.assertEqual(self.launched, [])

    def test_tile_without_window_launches(self):
        self.assertEqual(self.controller.openTile("facebook"), "ok")
        self.assertEqual(self.launched, [["--app=https://www.facebook.com/", "--start-maximized"]])

    def test_describe(self):
        names = [self.controller.describe_window(w) for w in self.windows.list()]
        self.assertEqual(names, [("YouTube", "youtube"), ("Images", "files"), ("Vidéo", "videos"), ("notes.txt", "fenetre")])

    def test_model(self):
        from sigildesk.ui.windows_model import WindowsModel

        model = WindowsModel(self.windows, self.controller.describe_window)
        model.refresh()
        self.assertEqual(model.property("count"), 4)
        self.assertTrue(model.activate("0x03"))
        self.assertEqual(WindowsModel(None, self.controller.describe_window).property("available"), False)


if __name__ == "__main__":
    unittest.main()
