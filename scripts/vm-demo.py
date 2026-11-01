#!/usr/bin/env python3
"""Enregistre une démonstration de SigilDesk dans la VM, image par image.

Un scénario (liste d'étapes) pilote la souris et le clavier de la VM par QMP,
et l'écran est capturé à cadence fixe dans `build/video/images/`, avec les
légendes à incruster (`legendes.json`). Le montage est fait par video-montage.py.

    python3 scripts/vm-demo.py                   # enregistre le scénario complet (build/video/)
    python3 scripts/vm-demo.py --sequence noms   # séquence « noms sous les icônes » (build/video/noms/),
                                                 # à jouer depuis l'état de fin du mode confort
    python3 scripts/vm-demo.py --essai           # joue sans capturer (calage des positions)
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from importlib import import_module  # noqa: E402

qmp_module = import_module("vm-qmp")
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "build" / "video"


class Demo:
    def __init__(self, record: bool, fps: int = 10, out: Path = OUT):
        self.qmp = qmp_module.Qmp(qmp_module.SOCKET)
        self.record = record
        self.fps = fps
        self.width, self.height = self.qmp.screen_size()
        self.pos = (self.width // 2, self.height // 2)
        self.frames: list[tuple[str, float]] = []
        self.captions: list[dict] = []
        self.start = time.monotonic()
        self.out = out
        if record:
            # Seulement les images de cette prise : les vidéos et les autres prises restent.
            shutil.rmtree(out / "images", ignore_errors=True)
            (out / "images").mkdir(parents=True)

    # --- primitives -------------------------------------------------------------

    def now(self) -> float:
        return time.monotonic() - self.start

    def frame(self) -> None:
        began = time.monotonic()
        if self.record:
            path = self.out / "images" / f"{len(self.frames):05d}.png"
            self.qmp.call("screendump", filename=str(path), format="png")
            self.frames.append((path.name, self.now()))
        spent = time.monotonic() - began
        time.sleep(max(0.0, 1 / self.fps - spent))

    def _pointer(self, x: float, y: float) -> None:
        self.qmp.call("input-send-event", events=[
            {"type": "abs", "data": {"axis": "x", "value": round(x * 32767 / (self.width - 1))}},
            {"type": "abs", "data": {"axis": "y", "value": round(y * 32767 / (self.height - 1))}},
        ])

    def wait(self, seconds: float) -> None:
        for _ in range(max(1, round(seconds * self.fps))):
            self.frame()

    def move(self, x: float, y: float, seconds: float = 0.8) -> None:
        x0, y0 = self.pos
        steps = max(1, round(seconds * self.fps))
        for i in range(1, steps + 1):
            k = 0.5 - 0.5 * math.cos(math.pi * i / steps)  # départ et arrivée en douceur
            self._pointer(x0 + (x - x0) * k, y0 + (y - y0) * k)
            self.frame()
        self.pos = (x, y)

    def click(self, double: bool = False) -> None:
        for _ in range(2 if double else 1):
            for down in (True, False):
                self.qmp.call("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": "left"}}])
                time.sleep(0.05)
        self.frame()

    def key(self, combo: str) -> None:
        self.qmp.send(combo.split("-"))
        self.frame()

    # --- état réel de l'écran -------------------------------------------------------
    # Quand une autre fenêtre est au premier plan, le panneau LXQt réapparaît en
    # bas de l'écran ; quand c'est l'accueil, il le recouvre. Un pixel suffit.

    def _luma(self, x: int, y: int) -> float:
        probe = OUT.parent / "vm" / ".sonde.ppm"
        self.qmp.call("screendump", filename=str(probe))  # PPM : lisible sans bibliothèque
        data = probe.read_bytes()
        header_end, fields = 0, []
        while len(fields) < 4:  # « P6 », largeur, hauteur, 255
            while data[header_end:header_end + 1].isspace():
                header_end += 1
            start = header_end
            while not data[header_end:header_end + 1].isspace():
                header_end += 1
            fields.append(data[start:header_end])
        offset = header_end + 1 + (y * int(fields[1]) + x) * 3
        r, g, b = data[offset:offset + 3]
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255

    def home_visible(self) -> bool:
        return self._luma(250, 760) > 0.4

    def wait_until(self, condition, timeout: float, then: float = 0.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if condition():
                self.wait(then)
                return True
            self.frame()
        print(f"attente dépassée ({timeout} s)", file=sys.stderr)
        return False

    def wait_window(self, timeout: float = 15, then: float = 0.0) -> bool:
        return self.wait_until(lambda: not self.home_visible(), timeout, then)

    def wait_home(self, timeout: float = 6, then: float = 0.0) -> bool:
        return self.wait_until(self.home_visible, timeout, then)

    def close_windows(self) -> None:
        """Alt+F4 jusqu'au retour de l'accueil ; jamais quand l'accueil est devant."""
        for _ in range(4):
            if self.home_visible():
                return
            self.key("alt-f4")
            self.wait_until(self.home_visible, 1.6)

    def caption(self, text: str | None) -> None:
        if self.captions and self.captions[-1]["fin"] is None:
            self.captions[-1]["fin"] = self.now()
        if text:
            self.captions.append({"texte": text, "debut": self.now(), "fin": None})

    def save(self) -> None:
        self.caption(None)
        if self.record:
            (self.out / "images.json").write_text(json.dumps(self.frames), encoding="utf-8")
            (self.out / "legendes.json").write_text(json.dumps(self.captions, ensure_ascii=False, indent=1),
                                                    encoding="utf-8")
            print(f"{len(self.frames)} images, {self.now():.1f} s, {len(self.captions)} légendes → {self.out}")


# Positions dans l'écran de la VM (1368×768), relevées le 2026-10-28 dans la
# session Lubuntu française, dossiers et lecteurs agrandis une première fois.
COL = [433, 601, 769, 937]
ROW = [280, 428, 576]
DOCK = {"favoris": (524, 715), "parametres": (699, 715), "eteindre": (847, 715)}
DOCK_CONFORT = {"parametres": (699, 714)}
P = {
    "reduire": (1306, 15),            # bouton « réduire » d'une fenêtre agrandie
    "fenetre_youtube": (684, 47),     # pastille YouTube, barre des fenêtres ouvertes
    "vignettes": (236, 76),           # gestionnaire de fichiers : vue en grandes miniatures
    "premier_fichier": (309, 166),
    "meteo": (150, 95),
    "confort": (521, 258),
    "confort_confort": (556, 281),
    "changer_fond": (745, 582),
    "fond_orbite": (472, 592),
    "fond_appliquer": (1268, 710),
    "annuler_eteindre": (792, 432),
}


def open_file(d: Demo, tile: tuple[int, int]) -> None:
    d.move(*tile, 0.7)
    d.click()
    d.wait_window(then=0.8)
    d.move(*P["vignettes"], 0.8)
    d.click()
    d.wait(0.6)
    d.move(*P["premier_fichier"], 0.6)
    d.click(double=True)


def scenario(d: Demo) -> None:
    if not d.home_visible():
        raise SystemExit("L'accueil de SigilDesk doit être au premier plan avant l'enregistrement.")
    d.move(1000, 640, 0.1)
    d.caption("Un accueil simple, façon tablette, pour celles et ceux qui débutent")
    d.wait(2.2)
    for x in COL:
        d.move(x, ROW[0], 0.4)
    for x in reversed(COL):
        d.move(x, ROW[1], 0.4)

    d.caption("YouTube, Facebook, les mails : un clic, et sans barre d'adresse")
    d.move(COL[3], ROW[0], 0.7)
    d.click()
    d.wait_window(timeout=20, then=3.5)
    d.caption("Une fenêtre restée ouverte ? On y revient d'un clic")
    d.move(*P["reduire"], 0.9)
    d.click()
    d.wait_home(then=1.4)
    d.move(*P["fenetre_youtube"], 1.0)
    d.wait(0.6)
    d.click()
    d.wait_window(then=1.8)
    d.close_windows()
    d.wait(0.6)

    d.caption("Ses photos, ses vidéos, ses documents, sans chercher")
    open_file(d, (COL[1], ROW[1]))
    d.wait(2.2)
    d.key("right")
    d.wait(1.4)
    d.key("right")
    d.wait(1.4)
    d.close_windows()
    d.wait(0.5)
    open_file(d, (COL[2], ROW[1]))
    d.wait(4.5)
    d.close_windows()
    d.wait(0.5)
    open_file(d, (COL[3], ROW[1]))
    d.wait(3.0)
    d.close_windows()
    d.wait(0.8)

    d.caption("Ses sites préférés et la météo, toujours sous la main")
    for x in COL:
        d.move(x, ROW[2], 0.4)
    d.move(*P["meteo"], 1.0)
    d.wait(1.4)
    d.move(*DOCK["favoris"], 1.0)
    d.click()
    d.wait(2.4)
    d.key("esc")
    d.wait(0.6)

    d.caption("Son fond d'écran, choisi en un clin d'œil")
    d.move(*DOCK["parametres"], 0.8)
    d.click()
    d.wait(1.0)
    d.move(*P["changer_fond"], 0.8)
    d.click()
    d.wait(1.2)
    d.move(*P["fond_orbite"], 0.9)
    d.click()
    d.wait(1.8)
    d.move(*P["fond_appliquer"], 0.9)
    d.click()
    d.wait(1.8)

    d.caption("Mode confort : textes et boutons s'agrandissent")
    d.move(*DOCK["parametres"], 0.8)
    d.click()
    d.wait(0.9)
    d.move(*P["confort"], 0.8)
    d.click()
    d.wait(1.0)
    d.key("esc")
    d.wait(2.8)
    d.move(*DOCK_CONFORT["parametres"], 0.6)
    d.click()
    d.wait(0.8)
    d.move(*P["confort_confort"], 0.8)
    d.click()
    d.wait(0.8)
    d.key("esc")
    d.wait(0.8)

    d.caption("Et pour finir, éteindre en toute sécurité")
    d.move(*DOCK["eteindre"], 1.0)
    d.click()
    d.wait(2.2)
    d.move(*P["annuler_eteindre"], 0.8)
    d.click()
    d.wait(1.2)


LABELS_SWITCH = (521, 413)  # Paramètres › Affichage › Noms sous les icônes (mode standard)


def scenario_noms(d: Demo) -> None:
    """Noms sous les icônes : on les retire, les icônes remplissent les tuiles, on les remet."""
    d.move(1000, 640, 0.1)
    d.caption("Sans les noms, des icônes encore plus grandes")
    d.wait(0.6)
    d.move(*DOCK["parametres"], 0.8)
    d.click()
    d.wait(1.0)
    d.move(*LABELS_SWITCH, 0.8)
    d.click()
    d.wait(1.0)
    d.key("esc")
    d.wait(0.6)
    for x in COL:
        d.move(x, ROW[1], 0.35)
    d.wait(1.6)
    d.move(*DOCK["parametres"], 0.8)
    d.click()
    d.wait(0.8)
    d.move(*LABELS_SWITCH, 0.8)
    d.click()
    d.wait(0.8)
    d.key("esc")
    d.wait(1.0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--essai", action="store_true", help="joue le scénario sans capturer")
    parser.add_argument("--sequence", choices=("complete", "noms"), default="complete")
    args = parser.parse_args()
    if args.sequence == "noms":
        demo = Demo(record=not args.essai, out=OUT / "noms")
        scenario_noms(demo)
    else:
        demo = Demo(record=not args.essai)
        scenario(demo)
    demo.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
