"""État affiché dans la barre du haut : réseau et force du Wi-Fi, Bluetooth, batterie.

Relu toutes les 3 s (au lieu de 30 jusqu'au 2026-10-28 : sur l'ASUS, l'icône
Wi-Fi tardait, surtout au réveil). Le signal `changed` n'est émis que si
quelque chose a bougé, pour ne pas réveiller le QML pour rien.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal

from sigildesk.infra.system_probe import Battery, read_battery, read_bluetooth, read_network, read_wifi_level

NETWORK_LABELS = {"wifi": "Wi-Fi connecté", "filaire": "Réseau filaire connecté", "aucun": "Pas de réseau"}
BLUETOOTH_LABELS = {"on": "Bluetooth activé", "off": "Bluetooth désactivé", "absent": ""}


class SystemStatus(QObject):
    changed = Signal()

    def __init__(self, sys_root: Path = Path("/sys"), proc_root: Path = Path("/proc"), interval_ms: int = 3_000,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._sys_root = sys_root
        self._proc_root = proc_root
        self._battery = Battery(-1, False)
        self._network = "aucun"
        self._wifi_level = 0
        self._bluetooth = "absent"
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.refresh)
        self.refresh()
        self._timer.start()

    def refresh(self) -> None:
        battery = read_battery(self._sys_root)
        network, interface = read_network(self._sys_root)
        wifi_level = read_wifi_level(interface, self._proc_root) if network == "wifi" else 0
        bluetooth = read_bluetooth(self._sys_root)
        state = (battery, network, wifi_level, bluetooth)
        if state != (self._battery, self._network, self._wifi_level, self._bluetooth):
            self._battery, self._network, self._wifi_level, self._bluetooth = state
            self.changed.emit()

    def _network_icon(self) -> str:
        if self._network == "wifi":
            return f"statut-wifi-{self._wifi_level}"
        return "statut-filaire" if self._network == "filaire" else "statut-wifi-off"

    def _battery_label(self) -> str:
        if self._battery.percent < 0:
            return ""
        return f"Batterie {self._battery.percent} %" + (", en charge" if self._battery.charging else "")

    batteryPercent = Property(int, lambda self: self._battery.percent, notify=changed)
    charging = Property(bool, lambda self: self._battery.charging, notify=changed)
    batteryLabel = Property(str, lambda self: self._battery_label(), notify=changed)
    network = Property(str, lambda self: self._network, notify=changed)
    networkLabel = Property(str, lambda self: NETWORK_LABELS[self._network], notify=changed)
    networkIcon = Property(str, lambda self: self._network_icon(), notify=changed)
    bluetooth = Property(str, lambda self: self._bluetooth, notify=changed)
    bluetoothLabel = Property(str, lambda self: BLUETOOTH_LABELS[self._bluetooth], notify=changed)
    bluetoothIcon = Property(
        str, lambda self: "statut-bluetooth" if self._bluetooth == "on" else "statut-bluetooth-off", notify=changed)
