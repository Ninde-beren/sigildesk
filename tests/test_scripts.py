"""Scripts d'installation : idempotents, périmètre strict, réversibles, sans sudo.

Chaque test tourne dans un dossier personnel factice (HOME et XDG_* redirigés).
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

import support

SCRIPTS = support.REPO / "scripts"


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.home = support.TempDir(self).path
        self.env = {
            "HOME": str(self.home),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "SIGILDESK_PYTHON": sys.executable,
            "LANG": "C.UTF-8",
        }
        # Fichiers personnels qui ne doivent jamais bouger.
        self.personal = {
            self.home / ".config/chromium/Default/Bookmarks": "{}",
            self.home / ".local/share/applications/autre-appli.desktop": "[Desktop Entry]\nName=Autre\n",
            self.home / ".config/autostart/autre.desktop": "[Desktop Entry]\nName=Autre\n",
            self.home / ".config/lxqt/session.conf": "[General]\n",
            self.home / "Images/vacances.jpg": "photo",
        }
        for path, text in self.personal.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def run_script(self, name, *args, expect=0, env=None):
        done = subprocess.run(["bash", str(SCRIPTS / name), *args], env=env or self.env,
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, expect, done.stdout + done.stderr)
        return done.stdout + done.stderr

    LXQT_SESSION = Path(".config/lxqt/session.conf")

    def assert_personal_files_intact(self, installed=False):
        for path, text in self.personal.items():
            if installed and path == self.home / self.LXQT_SESSION:
                # Seule exception, voulue : sans verrouilleur, l'installation coupe le
                # verrouillage avant la veille (désinstaller le rétablit).
                self.assertEqual(path.read_text(encoding="utf-8"),
                                 "[General]\nlock_screen_before_power_actions=false\n", path)
                continue
            self.assertEqual(path.read_text(encoding="utf-8"), text, path)

    def installed(self):
        return {
            "app": self.home / ".local/share/sigildesk/app/sigildesk/__init__.py",
            "launcher": self.home / ".local/bin/sigildesk",
            "desktop": self.home / ".local/share/applications/sigildesk.desktop",
            "icon": self.home / ".local/share/icons/hicolor/scalable/apps/sigildesk.svg",
            "autostart": self.home / ".config/autostart/sigildesk.desktop",
        }

    def test_install_twice_then_uninstall_twice(self):
        out = self.run_script("install-user.sh")
        self.assertIn("autostart   : activé", out)
        self.run_script("install-user.sh")
        for path in self.installed().values():
            self.assertTrue(path.exists(), path)
        desktop = self.installed()["desktop"].read_text(encoding="utf-8")
        self.assertIn(f'Exec="{self.home}/.local/bin/sigildesk"', desktop)
        autostart = self.installed()["autostart"].read_text(encoding="utf-8")
        self.assertIn("OnlyShowIn=LXQt;", autostart)
        self.assertIn(f'Exec="{self.home}/.local/bin/sigildesk" --autostart', autostart)
        self.assertEqual(list((self.home / ".local/share/sigildesk/app").rglob("__pycache__")), [])

        # Le lanceur installé démarre vraiment (diagnostic seulement, sans fenêtre).
        launcher = self.installed()["launcher"]
        done = subprocess.run([str(launcher), "--version"], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("SigilDesk 1.0", done.stdout)

        self.run_script("uninstall-user.sh")
        self.run_script("uninstall-user.sh")
        for path in self.installed().values():
            self.assertFalse(path.exists(), path)
        self.assert_personal_files_intact()

    def test_autostart_cycle(self):
        self.run_script("enable-autostart.sh", expect=1)  # pas installé : refus
        autostart = self.installed()["autostart"]
        out = self.run_script("install-user.sh", "--sans-autostart")  # essai à la main d'abord
        self.assertIn("non activé", out)
        self.assertFalse(autostart.exists())
        app_scripts = self.home / ".local/share/sigildesk/app/scripts"
        self.run_script(str(app_scripts / "enable-autostart.sh"))
        self.run_script(str(app_scripts / "enable-autostart.sh"))
        text = autostart.read_text(encoding="utf-8")
        self.assertIn("OnlyShowIn=LXQt;", text)
        self.assertIn("--autostart", text)
        # Une mise à jour « sans autostart » garde un autostart déjà activé.
        self.run_script("install-user.sh", "--sans-autostart")
        self.assertTrue(autostart.exists())
        self.run_script(str(app_scripts / "disable-autostart.sh"))
        self.run_script(str(app_scripts / "disable-autostart.sh"))
        self.assertFalse(autostart.exists())
        self.run_script("install-user.sh", "--option-inconnue", expect=64)
        self.assert_personal_files_intact(installed=True)

    def test_foreign_files_are_never_overwritten(self):
        foreign = self.home / ".local/share/applications/sigildesk.desktop"
        foreign.parent.mkdir(parents=True, exist_ok=True)
        foreign.write_text("[Desktop Entry]\nName=Pas à nous\n", encoding="utf-8")
        self.run_script("install-user.sh", expect=3)
        self.assertIn("Pas à nous", foreign.read_text(encoding="utf-8"))
        self.run_script("uninstall-user.sh")
        self.assertTrue(foreign.exists())

        autostart = self.home / ".config/autostart/sigildesk.desktop"
        autostart.write_text("[Desktop Entry]\nName=Pas à nous\n", encoding="utf-8")
        self.run_script("disable-autostart.sh", expect=3)
        self.assertTrue(autostart.exists())
        foreign.unlink()
        out = self.run_script("install-user.sh")  # l'installation laisse cet autostart étranger
        self.assertIn("n'appartient pas à SigilDesk", out)
        self.assertIn("Pas à nous", autostart.read_text(encoding="utf-8"))
        self.run_script("uninstall-user.sh")
        self.assertTrue(autostart.exists())

    def test_user_data_kept_unless_purged(self):
        self.run_script("install-user.sh")
        config = self.home / ".config/sigildesk/config.json"
        wallpaper = self.home / ".local/share/sigildesk/wallpapers/perso-abc-light.jpg"
        weather = self.home / ".cache/sigildesk/meteo.json"
        for path in (config, wallpaper, weather):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
        self.run_script("uninstall-user.sh")
        self.assertTrue(config.exists() and wallpaper.exists())
        self.run_script("uninstall-user.sh", "--purge", "--yes")
        self.assertFalse(config.exists() or wallpaper.exists() or weather.exists())
        self.assert_personal_files_intact()

    def test_missing_pyside_is_reported_not_installed(self):
        env = dict(self.env, SIGILDESK_PYTHON="/usr/bin/false")
        out = self.run_script("install-user.sh", expect=2, env=env)
        self.assertIn("sudo apt install", out)
        self.assertFalse(self.installed()["launcher"].exists())

    def test_update_notifiers_hidden_only_with_auto_updates(self):
        system_autostart = self.home / "etc-xdg-autostart"
        apt_conf = self.home / "etc-apt-conf"
        system_autostart.mkdir()
        apt_conf.mkdir()
        (system_autostart / "lubuntu-update-autostart.desktop").write_text("[Desktop Entry]\nName=MAJ\n", encoding="utf-8")
        env = dict(self.env, SIGILDESK_SYSTEM_AUTOSTART_DIR=str(system_autostart), SIGILDESK_APT_CONF_DIR=str(apt_conf))
        override = self.home / ".config/autostart/lubuntu-update-autostart.desktop"

        self.run_script("install-user.sh", env=env)
        self.assertFalse(override.exists())  # mises à jour automatiques non réglées : on ne touche à rien

        (apt_conf / "52sigildesk-mises-a-jour").write_text("// SigilDesk : mises à jour automatiques\n", encoding="utf-8")
        self.run_script("install-user.sh", env=env)
        text = override.read_text(encoding="utf-8")
        self.assertIn("Hidden=true", text)
        self.assertIn("X-SigilDesk-Managed=true", text)
        self.assertFalse((self.home / ".config/autostart/org.kde.discover.notifier.desktop").exists())

        self.run_script("uninstall-user.sh", env=env)
        self.assertFalse(override.exists())
        self.assert_personal_files_intact()

    def test_installer_from_key_leaves_no_copy_in_home(self):
        import shutil

        key = self.home / "cle" / "SigilDesk"
        app = key / "sigildesk-app"
        for part in ("sigildesk", "config", "data", "scripts", "branding"):
            source = support.REPO / part
            if source.is_dir():
                shutil.copytree(source, app / part, ignore=shutil.ignore_patterns("__pycache__", "propositions"))
        shutil.copy(SCRIPTS / "installer-cle.sh", key / "installer.sh")
        (self.home / "sigildesk-app.ancien-20261027").mkdir()  # reste de l'ancien installeur

        # Étape système refusée (pas de sudo ici) : l'installation utilisateur se fait quand même.
        done = subprocess.run(["bash", str(key / "installer.sh")], env=self.env, input="n\n",
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("Rien n'a été installé.", done.stdout)
        self.assertIn("la clé peut être retirée", done.stdout)
        self.assertIn("rm -rf ~/sigildesk-app", done.stdout)
        for path in self.installed().values():
            self.assertTrue(path.exists(), path)
        self.assertFalse((self.home / "sigildesk-app").exists())
        self.assertEqual(sorted(p.name for p in self.home.glob("sigildesk-app*")), ["sigildesk-app.ancien-20261027"])
        # L'application installée ne dépend plus de la clé.
        shutil.rmtree(self.home / "cle")
        version = subprocess.run([str(self.installed()["launcher"]), "--version"], env=self.env,
                                 capture_output=True, text=True, timeout=60)
        self.assertIn("SigilDesk 1.0", version.stdout)

    def test_refuses_root(self):
        text = (SCRIPTS / "lib.sh").read_text(encoding="utf-8")
        self.assertIn('if [ "$(id -u)" = 0 ]', text)
        for name in ("install-user.sh", "uninstall-user.sh", "enable-autostart.sh", "disable-autostart.sh",
                     "install-system-deps.sh", "disable-auto-updates.sh"):
            script = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertIn("refuse_root", script)
            if name not in ("install-system-deps.sh", "disable-auto-updates.sh"):  # seuls scripts système, après confirmation
                self.assertNotIn("sudo ", script.replace("sudo apt install", "").replace("ni avec sudo", ""))


if __name__ == "__main__":
    unittest.main()
