"""Bandeau d'état : réseau, force du Wi-Fi, Bluetooth, batterie (faux /sys et /proc)."""

import unittest

import support

from sigildesk.infra.system_probe import read_battery, read_bluetooth, read_network, read_wifi_level

WIRELESS = """Inter-| sta-|   Quality        |   Discarded packets               | Missed | WE
 face | tus | link level noise |  nwid  crypt   frag  retry   misc | beacon | 22
wlp2s0: 0000   {q}.  -56.  -256        0      0      0      0     27        0
"""


class FakeSys:
    def __init__(self, test):
        self.root = support.TempDir(test).path

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="ascii")
        return path

    def interface(self, name, state, wireless=False, physical=True):
        base = f"sys/class/net/{name}"
        self.write(f"{base}/operstate", state + "\n")
        if physical:
            (self.root / base / "device").mkdir(parents=True, exist_ok=True)
        if wireless:
            (self.root / base / "wireless").mkdir(parents=True, exist_ok=True)


class NetworkTests(unittest.TestCase):
    def test_wifi_and_level(self):
        fake = FakeSys(self)
        fake.interface("lo", "unknown", physical=False)
        fake.interface("docker0", "up", physical=False)
        fake.interface("wlp2s0", "up", wireless=True)
        self.assertEqual(read_network(fake.root / "sys"), ("wifi", "wlp2s0"))
        for quality, bars in ((60, 3), (35, 2), (12, 1)):
            fake.write("proc/net/wireless", WIRELESS.format(q=quality))
            self.assertEqual(read_wifi_level("wlp2s0", fake.root / "proc"), bars)
        self.assertEqual(read_wifi_level("absent0", fake.root / "proc"), 3)

    def test_wired_and_none(self):
        fake = FakeSys(self)
        fake.interface("enp1s0", "up")
        self.assertEqual(read_network(fake.root / "sys"), ("filaire", ""))
        fake.interface("enp1s0", "down")
        self.assertEqual(read_network(fake.root / "sys"), ("aucun", ""))


class BluetoothTests(unittest.TestCase):
    def test_rfkill_states(self):
        fake = FakeSys(self)
        self.assertEqual(read_bluetooth(fake.root / "sys"), "absent")
        fake.write("sys/class/rfkill/rfkill0/type", "wlan\n")
        fake.write("sys/class/rfkill/rfkill1/type", "bluetooth\n")
        fake.write("sys/class/rfkill/rfkill1/soft", "0\n")
        fake.write("sys/class/rfkill/rfkill1/hard", "0\n")
        self.assertEqual(read_bluetooth(fake.root / "sys"), "on")
        fake.write("sys/class/rfkill/rfkill1/soft", "1\n")
        self.assertEqual(read_bluetooth(fake.root / "sys"), "off")

    def test_adapter_without_rfkill(self):
        fake = FakeSys(self)
        (fake.root / "sys/class/bluetooth/hci0").mkdir(parents=True)
        self.assertEqual(read_bluetooth(fake.root / "sys"), "on")


class BatteryTests(unittest.TestCase):
    def test_battery(self):
        fake = FakeSys(self)
        self.assertEqual(read_battery(fake.root / "sys").percent, -1)
        fake.write("sys/class/power_supply/AC/type", "Mains\n")
        fake.write("sys/class/power_supply/BAT0/type", "Battery\n")
        fake.write("sys/class/power_supply/BAT0/capacity", "42\n")
        fake.write("sys/class/power_supply/BAT0/status", "Charging\n")
        battery = read_battery(fake.root / "sys")
        self.assertEqual((battery.percent, battery.charging), (42, True))
        fake.write("sys/class/power_supply/BAT0/status", "Discharging\n")
        self.assertFalse(read_battery(fake.root / "sys").charging)

    def test_refresh_is_fast_enough_for_wifi(self):
        support.qt_app()
        from sigildesk.ui.system_status import SystemStatus

        fake = FakeSys(self)
        status = SystemStatus(fake.root / "sys", fake.root / "proc")
        self.assertLessEqual(status._timer.interval(), 5000)  # l'icône Wi-Fi suit vite la reconnexion
        self.assertEqual(status.property("networkIcon"), "statut-wifi-off")
        fake.interface("wlp2s0", "up", wireless=True)
        status.refresh()
        self.assertEqual(status.property("networkIcon"), "statut-wifi-3")

    def test_qt_object_exposes_icons(self):
        support.qt_app()
        from sigildesk.ui.system_status import SystemStatus

        fake = FakeSys(self)
        fake.interface("wlp2s0", "up", wireless=True)
        fake.write("proc/net/wireless", WIRELESS.format(q=12))
        fake.write("sys/class/rfkill/rfkill1/type", "bluetooth\n")
        fake.write("sys/class/rfkill/rfkill1/soft", "1\n")
        fake.write("sys/class/power_supply/BAT0/type", "Battery\n")
        fake.write("sys/class/power_supply/BAT0/capacity", "87\n")
        fake.write("sys/class/power_supply/BAT0/status", "Discharging\n")
        status = SystemStatus(fake.root / "sys", fake.root / "proc")
        self.assertEqual(status.property("networkIcon"), "statut-wifi-1")
        self.assertEqual(status.property("bluetoothIcon"), "statut-bluetooth-off")
        self.assertEqual(status.property("batteryLabel"), "Batterie 87 %")


if __name__ == "__main__":
    unittest.main()
