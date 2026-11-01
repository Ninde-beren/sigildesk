"""Habillage « Sigilys system » : icône du menu LXQt et thème de démarrage."""

import os
import subprocess
import sys
import unittest

import support

SCRIPTS = support.REPO / "scripts"
LUBUNTU_PANEL = """panels=panel1

[panel1]
plugins=fancymenu, desktopswitch, quicklaunch, taskbar
position=Bottom

[fancymenu]
buttonsAtTop=false
favorites\\1\\desktopFile=/usr/share/applications/featherpad.desktop
favorites\\size=1
showText=false
type=fancymenu

[taskbar]
type=taskbar
"""


class SessionLockTests(unittest.TestCase):
    """Option 1 : sans écran de verrouillage installé, pas de verrouillage avant la veille."""

    def setUp(self):
        self.root = support.TempDir(self).path
        self.conf = self.root / "config/lxqt/session.conf"
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "python3").symlink_to(sys.executable)
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.root / "config"), XDG_DATA_HOME=str(self.root / "data"),
                        PATH=str(self.bin))

    def run_lock(self, action):
        done = subprocess.run([sys.executable, str(SCRIPTS / "session-lock.py"), action], env=self.env,
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def test_cut_then_restore_keeps_the_rest(self):
        original = "[General]\n__userfile__=true\nleave_confirmation=true\n\n[Mouse]\ncursor_size=18\n"
        self.conf.parent.mkdir(parents=True)
        self.conf.write_text(original, encoding="utf-8")
        self.assertIn("coupé", self.run_lock("couper"))
        text = self.conf.read_text(encoding="utf-8")
        self.assertIn("[General]\n__userfile__=true\nleave_confirmation=true\nlock_screen_before_power_actions=false\n", text)
        self.assertIn("[Mouse]\ncursor_size=18\n", text)
        self.assertIn("déjà coupé", self.run_lock("couper"))
        self.run_lock("retablir")
        self.assertEqual(self.conf.read_text(encoding="utf-8"), original)
        self.assertIn("rien à rétablir", self.run_lock("retablir"))

    def test_without_session_file(self):
        self.run_lock("couper")
        self.assertEqual(self.conf.read_text(encoding="utf-8"), "[General]\nlock_screen_before_power_actions=false\n\n")

    def test_kept_when_a_locker_is_installed(self):
        (self.bin / "xscreensaver").write_text("#!/bin/sh\n", encoding="utf-8")
        (self.bin / "xscreensaver").chmod(0o755)
        self.assertIn("conservé", self.run_lock("couper"))
        self.assertFalse(self.conf.exists())

    def test_user_choice_is_never_undone(self):
        # Coupé à la main (sans SigilDesk) : « rétablir » n'y touche pas.
        self.conf.parent.mkdir(parents=True)
        self.conf.write_text("[General]\nlock_screen_before_power_actions=false\n", encoding="utf-8")
        self.run_lock("retablir")
        self.assertIn("lock_screen_before_power_actions=false", self.conf.read_text(encoding="utf-8"))


class MenuIconTests(unittest.TestCase):
    def setUp(self):
        self.root = support.TempDir(self).path
        (self.root / "sys/lxqt").mkdir(parents=True)
        (self.root / "sys/lxqt/panel.conf").write_text(LUBUNTU_PANEL, encoding="utf-8")
        self.icon = self.root / "home/.local/share/sigildesk/branding/menu.svg"
        self.icon.parent.mkdir(parents=True)
        self.icon.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        self.user_conf = self.root / "home/.config/lxqt/panel.conf"
        self.env = dict(os.environ, XDG_CONFIG_HOME=str(self.root / "home/.config"),
                        XDG_CONFIG_DIRS=str(self.root / "sys"), XDG_CURRENT_DESKTOP="TEST")

    def run_icon(self, *args):
        done = subprocess.run([sys.executable, str(SCRIPTS / "menu-icon.py"), *args], env=self.env,
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def section(self, name):
        lines, inside = [], False
        for line in self.user_conf.read_text(encoding="utf-8").splitlines():
            if line.startswith("["):
                inside = line == f"[{name}]"
            elif inside and line:
                lines.append(line)
        return lines

    def test_pose_then_remove_without_user_file(self):
        # Seules nos deux clés sont écrites : le reste vient toujours du fichier système.
        self.run_icon("poser", str(self.icon))
        self.assertEqual(self.section("fancymenu"), ["ownIcon=true", f"icon={self.icon}"])
        self.assertEqual(self.section("taskbar"), [])
        self.assertIn("déjà à jour", self.run_icon("poser", str(self.icon)))
        self.run_icon("retirer")
        self.assertNotIn("icon", self.user_conf.read_text(encoding="utf-8"))
        self.assertEqual((self.root / "sys/lxqt/panel.conf").read_text(encoding="utf-8"), LUBUNTU_PANEL)

    def test_full_user_file_keeps_everything_else(self):
        self.user_conf.parent.mkdir(parents=True)
        self.user_conf.write_text(LUBUNTU_PANEL, encoding="utf-8")
        self.run_icon("poser", str(self.icon))
        menu = self.section("fancymenu")
        self.assertEqual(menu[:2], ["ownIcon=true", f"icon={self.icon}"])
        self.assertIn("favorites\\1\\desktopFile=/usr/share/applications/featherpad.desktop", menu)
        self.run_icon("retirer")
        self.assertEqual(self.user_conf.read_text(encoding="utf-8"), LUBUNTU_PANEL)

    def test_user_overrides_without_menu_section(self):
        # Session live de Lubuntu : le fichier utilisateur ne porte que quelques
        # surcharges, le greffon de menu est défini dans le fichier du système.
        overrides = "[General]\n__userfile__=true\n\n[taskbar]\nalignment=Left\n"
        self.user_conf.parent.mkdir(parents=True)
        self.user_conf.write_text(overrides, encoding="utf-8")
        self.run_icon("poser", str(self.icon))
        self.assertEqual(self.section("fancymenu"), ["ownIcon=true", f"icon={self.icon}"])
        self.assertEqual(self.section("taskbar"), ["alignment=Left"])
        self.run_icon("retirer")
        text = self.user_conf.read_text(encoding="utf-8")
        self.assertNotIn("icon=", text)
        self.assertIn("__userfile__=true", text)

    def test_someone_elses_icon_is_kept_on_remove(self):
        self.user_conf.parent.mkdir(parents=True)
        self.user_conf.write_text(LUBUNTU_PANEL.replace("type=fancymenu", "ownIcon=true\nicon=/usr/share/icons/autre.svg\ntype=fancymenu"),
                                  encoding="utf-8")
        self.run_icon("retirer")
        self.assertIn("icon=/usr/share/icons/autre.svg", self.section("fancymenu"))

    def test_without_menu_or_conf(self):
        (self.root / "sys/lxqt/panel.conf").write_text("[panel1]\nplugins=taskbar\n\n[taskbar]\ntype=taskbar\n", encoding="utf-8")
        self.assertIn("rien à faire", self.run_icon("poser", str(self.icon)))
        self.assertFalse(self.user_conf.exists())


def _has_qtsvg() -> bool:
    try:
        import PySide6.QtSvg  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(_has_qtsvg(), "outil de développement : PySide6.QtSvg absent (paquets de l'ASUS)")
class ThemeBuildTests(unittest.TestCase):
    def test_build_theme(self):
        root = support.TempDir(self).path
        svg = root / "logo.svg"
        svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40" viewBox="0 0 100 40">'
                       '<circle cx="20" cy="20" r="18" fill="#fff"/></svg>', encoding="utf-8")
        out = root / "sortie"
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        done = subprocess.run([sys.executable, str(SCRIPTS / "build-branding.py"), "--symbole", str(svg), "--ecran", str(svg),
                               "--fond", "#16202B", "--sortie", str(out)], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        theme = out / "plymouth" / "sigilys"
        conf = (theme / "sigilys.plymouth").read_text(encoding="utf-8")
        self.assertIn("ModuleName=two-step", conf)
        self.assertIn("BackgroundStartColor=0x16202b", conf)
        self.assertIn("UseFirmwareBackground=false", conf)  # pas le logo du fabricant
        self.assertIn("ImageDir=/usr/share/plymouth/themes/sigilys", conf)
        self.assertIn("_Title=Installation des mises à jour…", conf)
        for name in ("watermark.png", "throbber-0001.png", "throbber-0036.png", "animation-0036.png"):
            self.assertTrue((theme / name).is_file(), name)
        self.assertTrue((out / "menu.svg").is_file())
        self.assertTrue((out / "apercu-demarrage.png").is_file())


if __name__ == "__main__":
    unittest.main()
