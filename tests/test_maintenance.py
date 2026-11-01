import unittest

import support

from sigildesk.domain.shortcuts import DEFAULT_SHORTCUT, ShortcutError, validate_shortcut
from sigildesk.infra.lxqt import SessionPower, find_shortcut_conflicts, shortcut_files


class ShortcutTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(validate_shortcut("ctrl+alt+m"), "Ctrl+Alt+M")
        self.assertEqual(validate_shortcut("Alt + Control + F9"), "Ctrl+Alt+F9")
        self.assertEqual(validate_shortcut("Super+Shift+Ctrl+q"), "Ctrl+Shift+Meta+Q")
        self.assertEqual(validate_shortcut(DEFAULT_SHORTCUT), "Ctrl+Alt+M")

    def test_rejections(self):
        for bad in ("", "M", "Ctrl+M", "Shift+Alt+M", "Ctrl+Alt+", "Ctrl+Alt+Échap", "Ctrl+Ctrl+M", "Hyper+Alt+M", 3):
            with self.subTest(bad=bad), self.assertRaises(ShortcutError):
                validate_shortcut(bad)


class ConflictTests(unittest.TestCase):
    def write(self, text):
        path = support.TempDir(self).path / "globalkeyshortcuts.conf"
        path.write_text(text, encoding="utf-8")
        return path

    def test_detects_lxqt_conflict(self):
        path = self.write("[Control%2BAlt%2BM.42]\nComment=Ouvrir le mixeur\nEnabled=true\nExec=pavucontrol-qt\n"
                          "[Control%2BAlt%2BT.12]\nComment=Terminal\nExec=qterminal\n")
        conflicts = find_shortcut_conflicts("Ctrl+Alt+M", [path])
        self.assertEqual(len(conflicts), 1)
        self.assertIn("mixeur", conflicts[0])

    def test_disabled_shortcut_is_not_a_conflict(self):
        path = self.write("[Control%2BAlt%2BM.42]\nComment=Ancien\nEnabled=false\n")
        self.assertEqual(find_shortcut_conflicts("Ctrl+Alt+M", [path]), [])

    def test_missing_or_broken_files(self):
        broken = self.write("pas un fichier ini [[[")
        self.assertEqual(find_shortcut_conflicts("Ctrl+Alt+M", [broken, broken.with_name("absent.conf")]), [])

    def test_shortcut_files_order(self):
        files = shortcut_files({"XDG_CONFIG_HOME": "/home/m/.config", "XDG_CONFIG_DIRS": "/etc/xdg:/usr/share"})
        self.assertEqual([str(f) for f in files],
                         ["/home/m/.config/lxqt/globalkeyshortcuts.conf", "/etc/xdg/lxqt/globalkeyshortcuts.conf",
                          "/usr/share/lxqt/globalkeyshortcuts.conf"])


class SessionPowerTests(unittest.TestCase):
    def make(self, can="   boolean true\n", leave="/usr/bin/lxqt-leave", dbus="/usr/bin/dbus-send", start_ok=True):
        self.runs, self.starts = [], []
        runner = lambda argv: (self.runs.append(argv), can)[1]
        starter = lambda program, args: (self.starts.append([program, *args]), start_ok)[1]
        return SessionPower(dbus, leave, runner, starter)

    def test_poweroff_through_session_without_second_dialog(self):
        self.assertEqual(self.make().request("poweroff"), "session")
        self.assertEqual(self.runs, [["/usr/bin/dbus-send", "--session", "--print-reply", "--dest=org.lxqt.session",
                                      "/LXQtSession", "org.lxqt.session.canPowerOff"]])
        self.assertEqual(self.starts, [["/usr/bin/dbus-send", "--session", "--type=method_call", "--dest=org.lxqt.session",
                                        "/LXQtSession", "org.lxqt.session.powerOff"]])

    def test_reboot(self):
        self.assertEqual(self.make().request("reboot"), "session")
        self.assertTrue(self.runs[0][-1].endswith("canReboot"))
        self.assertTrue(self.starts[0][-1].endswith(".reboot"))

    def test_falls_back_to_lxqt_leave(self):
        self.assertEqual(self.make(can="   boolean false\n").request("poweroff"), "lxqt-leave")
        self.assertEqual(self.starts, [["/usr/bin/lxqt-leave", "--shutdown"]])
        self.assertEqual(self.make(can="", dbus=None).request("reboot"), "lxqt-leave")
        self.assertEqual(self.starts, [["/usr/bin/lxqt-leave", "--reboot"]])

    def test_nothing_possible(self):
        self.assertEqual(self.make(can="", leave=None).request("poweroff"), "")
        self.assertEqual(self.make(start_ok=False).request("poweroff"), "")

    def test_detect(self):
        which = {"dbus-send": "/usr/bin/dbus-send", "lxqt-leave": "/usr/bin/lxqt-leave"}.get
        self.assertIsNotNone(SessionPower.detect({"XDG_CURRENT_DESKTOP": "LXQt"}, which))
        self.assertIsNone(SessionPower.detect({"XDG_CURRENT_DESKTOP": "Budgie:GNOME"}, which))
        self.assertIsNone(SessionPower.detect({"XDG_CURRENT_DESKTOP": "LXQt"}, lambda name: None))


if __name__ == "__main__":
    unittest.main()
