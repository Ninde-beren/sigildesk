#!/usr/bin/env python3
"""Pilote la VM d'essai par son socket QMP : capture d'écran, frappe au clavier.

    python3 scripts/vm-qmp.py screendump build/vm/ecran.png
    python3 scripts/vm-qmp.py key ctrl-alt-t
    python3 scripts/vm-qmp.py type 'echo bonjour\n'
    python3 scripts/vm-qmp.py click 262 372      # coordonnées dans la capture d'écran

La frappe suppose une disposition de clavier américaine (celle de la session
live Lubuntu par défaut).
"""

from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

SOCKET = Path(__file__).resolve().parent.parent / "build" / "vm" / "qmp.sock"

_PLAIN = {" ": "spc", "\n": "ret", "\t": "tab", "-": "minus", "=": "equal", "/": "slash", ".": "dot",
          ",": "comma", ";": "semicolon", "'": "apostrophe", "\\": "backslash", "[": "bracket_left",
          "]": "bracket_right", "`": "grave_accent"}
_SHIFTED = {"_": "minus", "+": "equal", "?": "slash", ">": "dot", "<": "comma", ":": "semicolon",
            '"': "apostrophe", "|": "backslash", "{": "bracket_left", "}": "bracket_right", "~": "grave_accent",
            "!": "1", "@": "2", "#": "3", "$": "4", "%": "5", "^": "6", "&": "7", "*": "8", "(": "9", ")": "0"}


def keys_for(char: str) -> list[str]:
    if char.isascii() and char.isalpha():
        return ["shift", char.lower()] if char.isupper() else [char]
    if char.isdigit():
        return [char]
    if char in _PLAIN:
        return [_PLAIN[char]]
    if char in _SHIFTED:
        return ["shift", _SHIFTED[char]]
    raise ValueError(f"caractère non pris en charge : {char!r}")


class Qmp:
    def __init__(self, path: Path):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(path))
        self.file = self.sock.makefile("rw", encoding="utf-8")
        json.loads(self.file.readline())  # salutation
        self.call("qmp_capabilities")

    def call(self, command: str, **arguments):
        self.file.write(json.dumps({"execute": command, "arguments": arguments}) + "\n")
        self.file.flush()
        while True:
            reply = json.loads(self.file.readline())
            if "return" in reply:
                return reply["return"]
            if "error" in reply:
                raise RuntimeError(reply["error"])

    def send(self, codes: list[str]) -> None:
        self.call("send-key", keys=[{"type": "qcode", "data": c} for c in codes], **{"hold-time": 12})
        time.sleep(0.06)

    def screen_size(self) -> tuple[int, int]:
        probe = SOCKET.with_name(".taille.png")
        self.call("screendump", filename=str(probe), format="png")
        header = probe.read_bytes()[16:24]  # bloc IHDR du PNG
        probe.unlink(missing_ok=True)
        return int.from_bytes(header[:4], "big"), int.from_bytes(header[4:], "big")

    def click(self, x: int, y: int) -> None:
        """Clic gauche à (x, y), en pixels de l'écran de la VM (tablette USB absolue)."""
        width, height = self.screen_size()
        position = [
            {"type": "abs", "data": {"axis": "x", "value": round(x * 32767 / (width - 1))}},
            {"type": "abs", "data": {"axis": "y", "value": round(y * 32767 / (height - 1))}},
        ]
        self.call("input-send-event", events=position)
        time.sleep(0.1)
        for down in (True, False):
            self.call("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": "left"}}])
            time.sleep(0.08)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 64
    action, value = sys.argv[1], sys.argv[2]
    qmp = Qmp(SOCKET)
    if action == "screendump":
        qmp.call("screendump", filename=str(Path(value).resolve()), format="png")
    elif action == "key":
        qmp.send(value.split("-"))
    elif action == "type":
        for char in value.replace("\\n", "\n"):
            qmp.send(keys_for(char))
    elif action == "click":
        qmp.click(int(value), int(sys.argv[3]))
    else:
        print(__doc__)
        return 64
    return 0


if __name__ == "__main__":
    sys.exit(main())
