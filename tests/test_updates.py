"""Mises à jour : besoin de redémarrage, état des mises à jour automatiques, rappel."""

import os
import time
import unittest

import support

from sigildesk.infra.updates import AUTO_UPDATES_CONF, AutoUpdates, RebootCheck, auto_updates_status, reboot_required


class RebootTests(unittest.TestCase):
    def setUp(self):
        self.root = support.TempDir(self).path
        self.run, self.boot = self.root / "run", self.root / "boot"
        self.run.mkdir()
        self.boot.mkdir()

    def kernels(self, *versions):
        for version in versions:
            (self.boot / f"vmlinuz-{version}").write_text("", encoding="ascii")

    def test_nothing_to_do(self):
        self.kernels("6.17.0-14-generic")
        self.assertFalse(reboot_required(self.run, self.boot, "6.17.0-14-generic").required)

    def test_flag_file_with_packages(self):
        (self.run / "reboot-required").write_text("*** System restart required ***\n", encoding="ascii")
        (self.run / "reboot-required.pkgs").write_text("libc6\nlinux-base\nlibc6\n", encoding="ascii")
        check = reboot_required(self.run, self.boot, "6.17.0-14-generic")
        self.assertEqual(check, RebootCheck(True, ("libc6", "linux-base")))

    def test_newer_kernel_installed(self):
        self.kernels("6.17.0-9-generic", "6.17.0-14-generic", "6.17.0-15-generic")
        check = reboot_required(self.run, self.boot, "6.17.0-14-generic")
        self.assertTrue(check.required)
        self.assertEqual(check.packages, ("linux 6.17.0-15-generic",))
        # 14 > 9 : un tri par ordre alphabétique se tromperait.
        self.assertFalse(reboot_required(self.run, self.boot, "6.17.0-15-generic").required)

    def test_other_flavour_ignored(self):
        self.kernels("6.17.0-14-generic", "6.18.0-1-lowlatency")
        self.assertFalse(reboot_required(self.run, self.boot, "6.17.0-14-generic").required)


class StatusTests(unittest.TestCase):
    def test_auto_updates_status(self):
        root = support.TempDir(self).path
        conf, stamp = root / "apt.conf.d", root / "unattended-upgrades-stamp"
        conf.mkdir()
        self.assertEqual(auto_updates_status(conf, stamp), AutoUpdates(False, None))
        (conf / AUTO_UPDATES_CONF).write_text("x", encoding="ascii")
        stamp.write_text("", encoding="ascii")
        moment = time.time() - 3600
        os.utime(stamp, (moment, moment))
        status = auto_updates_status(conf, stamp)
        self.assertTrue(status.enabled)
        self.assertAlmostEqual(status.last_run.timestamp(), moment, delta=1)

    def test_packaged_conf_matches_name(self):
        conf = support.REPO / "data" / AUTO_UPDATES_CONF
        text = conf.read_text(encoding="utf-8")
        self.assertIn('Unattended-Upgrade::Automatic-Reboot "false"', text)
        self.assertIn("-updates", text)


class MonitorTests(unittest.TestCase):
    def test_suggests_then_waits_after_later(self):
        support.qt_app()
        from sigildesk.ui.update_monitor import UpdateMonitor

        state = {"required": False}
        monitor = UpdateMonitor(check=lambda: RebootCheck(state["required"]), status=lambda: AutoUpdates(True, None))
        asked = []
        monitor.rebootSuggested.connect(lambda: asked.append(True))
        monitor.start()
        self.assertEqual(asked, [])
        self.assertTrue(monitor.property("autoUpdatesEnabled"))
        state["required"] = True
        monitor.check()
        self.assertEqual(asked, [True])
        self.assertTrue(monitor.property("rebootRequired"))
        monitor.later()
        monitor.check()
        self.assertEqual(asked, [True])  # pas de nouvelle question avant quatre heures
        monitor._end_snooze()
        self.assertEqual(asked, [True, True])

    def test_labels(self):
        support.qt_app()
        from sigildesk.ui.update_monitor import UpdateMonitor

        monitor = UpdateMonitor(check=lambda: RebootCheck(False), status=lambda: AutoUpdates(False, None))
        monitor.check()
        self.assertIn("non réglées", monitor.property("autoUpdatesLabel"))


if __name__ == "__main__":
    unittest.main()
