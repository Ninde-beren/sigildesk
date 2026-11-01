"""Décodage vidéo matériel (VA-API), en lecture seule, par `vainfo`.

Le Celeron N3060 de l'ASUS décode H.264 et HEVC avec sa puce graphique si le
pilote `i965-va-driver` est installé (scripts/apt-packages-asus.txt) ; sans
lui, VLC décode en logiciel et une vidéo 1080p saccade ou se fige sur une
image. `vainfo` liste les profils que le pilote sait décoder ; ce module en
tire un rapport pour `--doctor` et Paramètres › Applications. Rien n'est
modifié, et sans `vainfo` le rapport dit seulement « non vérifiable ».
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from sigildesk.infra.processes import run_capture

Runner = Callable[[list[str]], str | None]

# Préfixe de profil VA-API → nom pour l'utilisateur, dans l'ordre d'affichage.
PROFILE_LABELS: tuple[tuple[str, str], ...] = (
    ("VAProfileH264", "H.264"),
    ("VAProfileHEVC", "HEVC"),
    ("VAProfileVP9", "VP9"),
    ("VAProfileAV1", "AV1"),
    ("VAProfileVP8", "VP8"),
    ("VAProfileMPEG2", "MPEG-2"),
    ("VAProfileVC1", "VC-1"),
    ("VAProfileJPEG", "JPEG"),
)
INSTALL_HINT = "installer le paquet i965-va-driver (scripts/install-system-deps.sh)"
_DECODE_LINE = re.compile(r"^\s*(VAProfile\w+?)\s*:\s*VAEntrypointVLD\b")  # VLD = décodage
_DRIVER_LINE = re.compile(r"^vainfo: Driver version:\s*(.+?)\s*$")


@dataclass(frozen=True)
class HardwareDecoding:
    status: str  # "ok" (des codecs), "aucun" (pilote absent ou muet), "absent" (vainfo introuvable)
    codecs: tuple[str, ...] = ()
    driver: str = ""

    @property
    def label(self) -> str:
        if self.status == "ok":
            return ", ".join(self.codecs) + (f" ({self.driver})" if self.driver else "")
        return "indisponible" if self.status == "aucun" else "non vérifiable"

    @property
    def hint(self) -> str:
        """Ce qu'il reste à faire, ou « » ; jamais exécuté par SigilDesk."""
        if self.status == "aucun":
            return INSTALL_HINT
        if self.status == "absent":
            return "vainfo absent (scripts/install-system-deps.sh)"
        return ""

    def as_dict(self) -> dict:
        return {"status": self.status, "codecs": list(self.codecs), "driver": self.driver,
                "label": self.label, "hint": self.hint}


def parse_vainfo(text: str) -> tuple[tuple[str, ...], str]:
    """(codecs décodables, nom du pilote) depuis la sortie de `vainfo`."""
    profiles: list[str] = []
    driver = ""
    for line in text.splitlines():
        if match := _DECODE_LINE.match(line):
            profiles.append(match.group(1))
        elif match := _DRIVER_LINE.match(line.strip()):
            driver = match.group(1)
    codecs = tuple(label for prefix, label in PROFILE_LABELS if any(p.startswith(prefix) for p in profiles))
    return codecs, driver


def _subprocess_runner(argv: list[str]) -> str | None:
    return run_capture(argv, timeout=8)  # vainfo ouvre l'affichage X11 : quelques secondes au pire


def check_hardware_decoding(vainfo: str | None, runner: Runner = _subprocess_runner) -> HardwareDecoding:
    """Rapport du décodage matériel ; `vainfo` est le chemin de l'outil, ou `None`."""
    if not vainfo:
        return HardwareDecoding("absent")
    codecs, driver = parse_vainfo(runner([vainfo]) or "")
    if not codecs:
        return HardwareDecoding("aucun", driver=driver)
    return HardwareDecoding("ok", codecs, driver)
