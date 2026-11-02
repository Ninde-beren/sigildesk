"""Matériel et pilotes, en lecture seule : pour `--doctor`, l'installation et Paramètres › Applications.

Sur l'ASUS, VLC figeait les vidéos parce que le pilote VA-API manquait, et aucune
commande ne l'aurait dit : `ubuntu-drivers` ne connaît que les pilotes
additionnels, `lspci -k` les pilotes du noyau, et l'accélération en espace
utilisateur (OpenGL, VA-API, son) ne se voit qu'avec des sondes à part. Ce
module les réunit ; chacune lit une commande ou un fichier du système :

- rendu graphique : `glxinfo -B` (accéléré par la puce, ou logiciel « llvmpipe ») ;
- décodage vidéo : `vainfo` (module `video_decoding`) ;
- appareils PCI : `lspci -vmmk`, écran, son, réseau, USB et disques sans pilote ;
- appareils USB : sysfs, interfaces son, webcam, Bluetooth, stockage et clavier sans pilote ;
- son : `/proc/asound/cards` (cartes vues par le noyau), puis la sortie par défaut
  du serveur audio (`wpctl`, sinon `pactl`) ;
- micrologiciels : `journalctl -k -b`, fichiers que le noyau n'a pas trouvés au démarrage ;
- pilotes additionnels : `ubuntu-drivers devices`.

Chaque sonde donne une `Verification` : « ok », « attention » (quelque chose à
regarder, avec la commande conseillée, que SigilDesk n'exécute jamais) ou
« absent » (outil manquant : non vérifiable). Rien n'est modifié, pas de root.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sigildesk.infra.processes import find_program, run_capture
from sigildesk.infra.video_decoding import HardwareDecoding, check_hardware_decoding

Which = Callable[[str], str | None]
Runner = Callable[..., str | None]  # runner(argv, timeout=secondes) → sortie standard, ou None

STATUSES = ("ok", "attention", "absent")
DOCTOR_MARKS = {"ok": "ok", "attention": "!!", "absent": "--"}
INSTALL = "scripts/install-system-deps.sh"


@dataclass(frozen=True)
class Verification:
    id: str
    label: str  # « rendu graphique », « son »…
    status: str  # une valeur de STATUSES
    detail: str = ""  # ce qui a été vu
    hint: str = ""  # ce qu'il reste à faire, ou « »

    def as_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "status": self.status, "detail": self.detail, "hint": self.hint}


# Rendu graphique -------------------------------------------------------------

SOFTWARE_RENDERERS = ("llvmpipe", "softpipe", "swrast")


def parse_glxinfo(text: str) -> tuple[bool | None, str]:
    """(accéléré ?, nom du moteur) depuis `glxinfo -B` ; None si la sortie ne dit rien."""
    accelerated: bool | None = None
    renderer = ""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Accelerated:"):
            accelerated = stripped.split(":", 1)[1].strip().lower() == "yes"
        elif stripped.startswith("OpenGL renderer string:"):
            renderer = stripped.split(":", 1)[1].strip()
    if accelerated is None and renderer:
        accelerated = not any(soft in renderer.lower() for soft in SOFTWARE_RENDERERS)
    return accelerated, renderer


def check_opengl(glxinfo: str | None, runner: Runner) -> Verification:
    label = "rendu graphique"
    if not glxinfo:
        return Verification("opengl", label, "absent", "non vérifiable",
                            f"glxinfo absent : paquet mesa-utils ({INSTALL})")
    output = runner([glxinfo, "-B"], timeout=8)
    if not output:
        return Verification("opengl", label, "absent", "non vérifiable", "pas d'affichage : à lancer depuis la session")
    accelerated, renderer = parse_glxinfo(output)
    if accelerated is None:
        return Verification("opengl", label, "absent", "non vérifiable", "sortie de glxinfo inattendue")
    if not accelerated:
        return Verification("opengl", label, "attention", f"rendu logiciel ({renderer or 'llvmpipe'})",
                            "la puce graphique n'est pas utilisée, SigilDesk et les vidéos tournent sur le "
                            "processeur : pilote de l'écran à vérifier (lspci -k, journalctl -k)")
    return Verification("opengl", label, "ok", f"accéléré par la puce ({renderer})")


# Appareils PCI ---------------------------------------------------------------

PCI_CLASSES = ("VGA compatible controller", "Display controller", "3D controller",
               "Audio device", "Multimedia audio controller",
               "Ethernet controller", "Network controller", "Bluetooth",
               "USB controller", "SATA controller", "Non-Volatile memory controller", "SD Host controller")


@dataclass(frozen=True)
class PciDevice:
    slot: str
    class_name: str
    name: str
    driver: str  # « » si aucun pilote du noyau n'est attaché
    modules: tuple[str, ...]  # modules connus pour cet appareil, attachés ou non


def parse_lspci(text: str) -> tuple[PciDevice, ...]:
    """Enregistrements de `lspci -vmmk` : blocs séparés par une ligne vide, lignes « Clé:<tab>Valeur »."""
    devices = []
    for block in re.split(r"\n\s*\n", text.strip()):
        fields: dict[str, str] = {}
        modules: list[str] = []
        for line in block.splitlines():
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key, value = key.strip(), value.strip()
            if key == "Module":
                modules.append(value)
            else:
                fields[key] = value
        if "Slot" in fields:
            devices.append(PciDevice(fields["Slot"], fields.get("Class", ""), fields.get("Device", ""),
                                     fields.get("Driver", ""), tuple(modules)))
    return tuple(devices)


def pci_of_interest(devices: tuple[PciDevice, ...]) -> tuple[PciDevice, ...]:
    """Les appareils qui doivent avoir un pilote ; les ponts et registres du SoC n'en ont pas et c'est normal."""
    return tuple(d for d in devices if d.class_name.startswith(PCI_CLASSES))


def check_pci(lspci: str | None, runner: Runner) -> Verification:
    label = "appareils PCI"
    if not lspci:
        return Verification("pci", label, "absent", "non vérifiable", "lspci absent : paquet pciutils")
    output = runner([lspci, "-vmmk"], timeout=8)
    if output is None:
        return Verification("pci", label, "absent", "non vérifiable", "lspci a échoué")
    devices = pci_of_interest(parse_lspci(output))
    missing = [d for d in devices if not d.driver]
    if missing:
        items = "; ".join(f"{d.class_name} « {d.name} »" + (f" (module {', '.join(d.modules)})" if d.modules else "")
                          for d in missing)
        return Verification("pci", label, "attention", f"sans pilote : {items}",
                            "pilote du noyau manquant : ubuntu-drivers devices, puis journalctl -k pour le détail")
    return Verification("pci", label, "ok", f"{len(devices)} appareils pilotés (écran, son, réseau, USB, disques)")


# Appareils USB ---------------------------------------------------------------

USB_CLASSES = {"01": "son", "03": "clavier, souris ou pavé", "07": "imprimante", "08": "stockage",
               "0e": "webcam", "e0": "Bluetooth"}


@dataclass(frozen=True)
class UsbInterface:
    name: str  # « 1-3:1.0 »
    class_code: str  # clé de USB_CLASSES
    device: str  # « Chicony USB2.0 HD UVC WebCam »
    driver: bool


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def read_usb_interfaces(sysfs: Path) -> tuple[UsbInterface, ...] | None:
    """Interfaces USB des classes qui demandent un pilote du noyau ; None si sysfs n'expose pas l'USB."""
    root = sysfs / "bus" / "usb" / "devices"
    if not root.is_dir():
        return None
    interfaces = []
    for entry in sorted(root.iterdir()):
        if ":" not in entry.name:
            continue
        code = _read(entry / "bInterfaceClass").lower()
        if code not in USB_CLASSES:
            continue
        parent = root / entry.name.split(":")[0]
        device = " ".join(part for part in (_read(parent / "manufacturer"), _read(parent / "product")) if part)
        driver_link = entry / "driver"
        interfaces.append(UsbInterface(entry.name, code, device or entry.name,
                                       driver_link.is_symlink() or driver_link.exists()))
    return tuple(interfaces)


def check_usb(sysfs: Path) -> Verification:
    label = "appareils USB"
    interfaces = read_usb_interfaces(sysfs)
    if interfaces is None:
        return Verification("usb", label, "absent", "non vérifiable", "sysfs n'expose pas l'USB")
    missing = sorted({f"{i.device} ({USB_CLASSES[i.class_code]})" for i in interfaces if not i.driver})
    if missing:
        return Verification("usb", label, "attention", "sans pilote : " + " ; ".join(missing),
                            "si l'appareil ne marche pas, son pilote manque : journalctl -k")
    if not interfaces:
        return Verification("usb", label, "ok", "aucune interface à vérifier")
    return Verification("usb", label, "ok",
                        f"{len(interfaces)} interfaces pilotées (son, webcam, Bluetooth, stockage, clavier)")


# Son -------------------------------------------------------------------------

_CARD_LINE = re.compile(r"^\s*\d+\s+\[\S+\s*\]:\s*\S+\s+-\s+(.+?)\s*$")
_WPCTL_FIELD = re.compile(r'node\.(name|description)\s*=\s*"([^"]*)"')
_PACTL_SINK = re.compile(r"^Default Sink:\s*(\S+)", re.MULTILINE)
NO_SINK = "auto_null"  # la sortie factice du serveur audio quand il ne voit aucune carte


def parse_asound_cards(text: str) -> tuple[str, ...]:
    """Noms des cartes son de `/proc/asound/cards` (vide si « --- no soundcards --- »)."""
    return tuple(m.group(1) for line in text.splitlines() if (m := _CARD_LINE.match(line)))


def parse_wpctl_sink(text: str) -> tuple[str, str]:
    """(node.name, node.description) de `wpctl inspect @DEFAULT_AUDIO_SINK@`."""
    fields = {key: value for key, value in _WPCTL_FIELD.findall(text)}
    return fields.get("name", ""), fields.get("description", "")


def parse_pactl_sink(text: str) -> str:
    match = _PACTL_SINK.search(text)
    return match.group(1) if match else ""


def check_audio(proc: Path, wpctl: str | None, pactl: str | None, runner: Runner) -> Verification:
    label = "son"
    cards_file = proc / "asound" / "cards"
    if not cards_file.is_file():
        return Verification("son", label, "absent", "non vérifiable", "ALSA indisponible")
    cards = parse_asound_cards(_read(cards_file))
    if not cards:
        return Verification("son", label, "attention", "aucune carte son vue par le noyau",
                            "pilote son manquant : lspci -k (Audio device), journalctl -k")
    cards_text = ", ".join(cards)
    if wpctl:
        name, description = parse_wpctl_sink(runner([wpctl, "inspect", "@DEFAULT_AUDIO_SINK@"], timeout=8) or "")
        sink = description or name
    elif pactl:
        name = sink = parse_pactl_sink(runner([pactl, "info"], timeout=8) or "")
    else:
        return Verification("son", label, "ok", f"carte(s) : {cards_text} ; sortie par défaut non vérifiée")
    if not name or name == NO_SINK:
        return Verification("son", label, "attention", f"carte(s) : {cards_text} ; aucune sortie par défaut",
                            "le serveur audio ne voit pas la carte : réglages du son de LXQt (pavucontrol-qt)")
    return Verification("son", label, "ok", f"carte(s) : {cards_text} ; sortie : {sink}")


# Micrologiciels --------------------------------------------------------------

_FIRMWARE_PATTERNS = (
    re.compile(r"Direct firmware load for (\S+) failed"),
    re.compile(r"firmware: failed to load (\S+)"),
    re.compile(r"[Ff]ailed to load .*?firmware.*?(\S+\.(?:bin|fw|sfi|ddc|ucode|dat|hex|img))"),
)
_FIRMWARE_WORDS = ("failed", "not found", "no such file")
_FIRMWARE_NOISE = ("[firmware bug]", "[firmware info]")
MAX_FIRMWARE_SHOWN = 5
JOURNAL_OPTIONS = ("-k", "-b", "-q", "--no-pager", "-o", "cat")  # noyau, ce démarrage, messages seuls
BOOT_WINDOW = 600  # secondes après le démarrage : les micrologiciels se chargent là, et le journal y reste court


def parse_firmware_failures(text: str) -> tuple[str, ...]:
    """Fichiers de micrologiciel que le noyau n'a pas pu charger, chacun une fois, dans l'ordre."""
    found: list[str] = []
    for line in text.splitlines():
        low = line.lower()
        if "firmware" not in low or any(noise in low for noise in _FIRMWARE_NOISE):
            continue
        if not any(word in low for word in _FIRMWARE_WORDS):
            continue
        for pattern in _FIRMWARE_PATTERNS:
            if match := pattern.search(line):
                item = match.group(1).rstrip(":,;)")
                break
        else:
            item = line.strip()[:100]
        if item not in found:
            found.append(item)
    return tuple(found)


def _boot_time(proc: Path, now: Callable[[], float]) -> int | None:
    """Instant du démarrage (epoch), d'après `/proc/uptime` ; None si illisible."""
    try:
        return int(now() - float(_read(proc / "uptime").split()[0]))
    except (IndexError, ValueError):
        return None


def check_firmware(journalctl: str | None, runner: Runner, proc: Path = Path("/proc"),
                   now: Callable[[], float] = time.time) -> Verification:
    label = "micrologiciels"
    if not journalctl:
        return Verification("micrologiciels", label, "absent", "non vérifiable", "journalctl absent")
    argv = [journalctl, *JOURNAL_OPTIONS]
    boot = _boot_time(proc, now)
    if boot is not None:  # fenêtre bornée : un journal de plusieurs semaines se lit en vingt secondes, celle-ci en rien
        argv += ["--since", f"@{boot}", "--until", f"@{boot + BOOT_WINDOW}"]
    output = runner(argv, timeout=15)
    if not output:  # les premières minutes d'un démarrage ne sont jamais muettes : sans droit de lecture, elles le sont
        return Verification("micrologiciels", label, "absent", "non vérifiable",
                            "journal du noyau inaccessible (l'utilisateur doit être dans le groupe adm)")
    failures = parse_firmware_failures(output)
    if failures:
        shown = ", ".join(failures[:MAX_FIRMWARE_SHOWN]) + ("…" if len(failures) > MAX_FIRMWARE_SHOWN else "")
        return Verification("micrologiciels", label, "attention",
                            f"{len(failures)} fichier(s) non trouvé(s) au démarrage : {shown}",
                            "fournis par le paquet linux-firmware ; sans conséquence si l'appareil marche")
    return Verification("micrologiciels", label, "ok", "aucun échec de chargement au démarrage")


# Pilotes additionnels --------------------------------------------------------

_UD_FIELD = re.compile(r"^(model|driver)\s*:\s*(.+?)\s*$")


def parse_ubuntu_drivers(text: str) -> tuple[tuple[str, str], ...]:
    """(modèle, pilote conseillé) par appareil pour lequel `ubuntu-drivers devices` propose un paquet.

    Les pilotes « builtin » (libres, déjà dans le noyau) ne comptent pas ; parmi
    les autres, le « recommended » l'emporte, sinon le premier.
    """
    proposals: list[tuple[str, str]] = []
    model = ""
    drivers: list[tuple[str, bool]] = []

    def close() -> None:
        candidates = [d for d in drivers if not d[1]]
        if candidates:
            recommended = next((name for name, _ in candidates if name in recommended_names), candidates[0][0])
            proposals.append((model, recommended))

    recommended_names: set[str] = set()
    for line in text.splitlines():
        if line.startswith("=="):
            close()
            model, drivers, recommended_names = "", [], set()
            continue
        if match := _UD_FIELD.match(line.strip()):
            key, value = match.groups()
            if key == "model":
                model = value
            else:
                name, _, flags = value.partition(" - ")
                drivers.append((name.strip(), "builtin" in flags))
                if "recommended" in flags:
                    recommended_names.add(name.strip())
    close()
    return tuple(proposals)


def check_additional_drivers(ubuntu_drivers: str | None, runner: Runner) -> Verification:
    label = "pilotes additionnels"
    if not ubuntu_drivers:
        return Verification("additionnels", label, "absent", "non vérifiable",
                            "ubuntu-drivers absent : paquet ubuntu-drivers-common (livré avec Lubuntu)")
    output = runner([ubuntu_drivers, "devices"], timeout=40)  # lit le cache apt : lent sur un Celeron
    if output is None:
        return Verification("additionnels", label, "absent", "non vérifiable", "ubuntu-drivers a échoué")
    proposals = parse_ubuntu_drivers(output)
    if proposals:
        items = " ; ".join(f"{model} → {driver}" for model, driver in proposals)
        return Verification("additionnels", label, "attention", f"proposés : {items}",
                            "Préférences › Logiciels et mises à jour › Pilotes additionnels, "
                            "ou : sudo ubuntu-drivers install")
    return Verification("additionnels", label, "ok", "aucun pilote additionnel proposé")


# Rapport ---------------------------------------------------------------------

def decoding_verification(report: HardwareDecoding) -> Verification:
    status = {"ok": "ok", "aucun": "attention", "absent": "absent"}[report.status]
    return Verification("decodage", "décodage vidéo matériel", status, report.label, report.hint)


def collect_hardware_report(which: Which = find_program, runner: Runner = run_capture,
                            sysfs: Path = Path("/sys"), proc: Path = Path("/proc"),
                            now: Callable[[], float] = time.time) -> list[Verification]:
    """Les sept vérifications, dans l'ordre d'affichage. Lecture seule ; quelques secondes au plus."""
    return [
        check_opengl(which("glxinfo"), runner),
        decoding_verification(check_hardware_decoding(which("vainfo"), lambda argv: runner(argv, timeout=8))),
        check_pci(which("lspci"), runner),
        check_usb(sysfs),
        check_audio(proc, which("wpctl"), which("pactl"), runner),
        check_firmware(which("journalctl"), runner, proc, now),
        check_additional_drivers(which("ubuntu-drivers"), runner),
    ]
