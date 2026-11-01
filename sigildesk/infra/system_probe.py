"""État matériel lu dans /sys et /proc : réseau et force du Wi-Fi, Bluetooth, batterie.

Aucun service ni dépendance (ni D-Bus, ni NetworkManager, ni BlueZ) : une
dizaine de petits fichiers, relus toutes les 3 s par `ui.system_status`. Les
racines `/sys` et `/proc` sont des paramètres pour que les tests fournissent
une arborescence factice.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Battery:
    percent: int  # -1 sans batterie
    charging: bool


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="ascii", errors="replace").strip()
    except OSError:
        return ""


def read_battery(sys_root: Path = Path("/sys")) -> Battery:
    """Première batterie présente de `/sys/class/power_supply`."""
    try:
        entries = sorted((sys_root / "class" / "power_supply").iterdir())
    except OSError:
        return Battery(-1, False)
    for entry in entries:
        if _read(entry / "type") != "Battery" or _read(entry / "present") == "0":
            continue
        capacity = _read(entry / "capacity")
        if not capacity.isdigit():
            continue
        status = _read(entry / "status")
        return Battery(max(0, min(100, int(capacity))), status in ("Charging", "Full"))
    return Battery(-1, False)


def read_network(sys_root: Path = Path("/sys")) -> tuple[str, str]:
    """(« wifi », « filaire » ou « aucun », nom de l'interface Wi-Fi active)."""
    try:
        interfaces = sorted((sys_root / "class" / "net").iterdir())
    except OSError:
        return "aucun", ""
    wired = False
    for iface in interfaces:
        if iface.name == "lo" or not (iface / "device").exists():
            continue  # interfaces virtuelles (docker, vpn, pont) ignorées
        if _read(iface / "operstate") != "up":
            continue
        if (iface / "wireless").exists() or (iface / "phy80211").exists():
            return "wifi", iface.name
        wired = True
    return ("filaire" if wired else "aucun"), ""


def read_wifi_level(interface: str, proc_root: Path = Path("/proc")) -> int:
    """Force du signal en barres (1 à 3), d'après la qualité de lien sur 70 de `/proc/net/wireless`."""
    for line in _read(proc_root / "net" / "wireless").splitlines():
        name, _, rest = line.partition(":")
        if name.strip() != interface:
            continue
        fields = rest.split()
        try:
            quality = float(fields[1].rstrip("."))
        except (IndexError, ValueError):
            break
        ratio = quality / 70
        return 3 if ratio >= 0.66 else 2 if ratio >= 0.33 else 1
    return 3  # qualité inconnue : on ne montre pas un faux signal faible


def read_bluetooth(sys_root: Path = Path("/sys")) -> str:
    """« absent », « off » (bloqué par rfkill) ou « on »."""
    try:
        entries = sorted((sys_root / "class" / "rfkill").iterdir())
    except OSError:
        entries = []
    states = [
        not (_read(entry / "soft") == "1" or _read(entry / "hard") == "1")
        for entry in entries if _read(entry / "type") == "bluetooth"
    ]
    if states:
        return "on" if any(states) else "off"
    try:
        has_adapter = any(p.name.startswith("hci") for p in (sys_root / "class" / "bluetooth").iterdir())
    except OSError:
        has_adapter = False
    return "on" if has_adapter else "absent"
