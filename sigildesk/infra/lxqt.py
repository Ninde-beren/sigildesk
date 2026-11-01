"""La session LXQt : ses raccourcis globaux (lecture seule) et l'extinction par la session.

Extinction et redémarrage passent par `org.lxqt.session` sur D-Bus (vérifié
dans Lubuntu 26.04) : `powerOff` et `reboot` ferment les applications puis
passent par systemd-logind, **sans** la boîte de confirmation de `lxqt-leave`.
SigilDesk a déjà posé la question, une seule fois. Repli : `lxqt-leave`, qui
redemande confirmation ; sinon rien, et l'interface affiche un guide vers le
menu. Jamais d'arrêt forcé (`systemctl poweroff`, `shutdown`).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path

from sigildesk.domain.shortcuts import find_conflicts
from sigildesk.infra.processes import find_program, run_capture, start_detached

# --- Raccourcis globaux -------------------------------------------------------------

def shortcut_files(env: Mapping[str, str] | None = None) -> list[Path]:
    """Fichiers de raccourcis globaux de LXQt, du plus prioritaire au moins prioritaire."""
    env = os.environ if env is None else env
    config_home = env.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    dirs = [config_home] + (env.get("XDG_CONFIG_DIRS") or "/etc/xdg").split(":")
    return [Path(d) / "lxqt" / "globalkeyshortcuts.conf" for d in dirs if d]


def find_shortcut_conflicts(shortcut: str, files: list[Path]) -> list[str]:
    """Raccourcis LXQt actifs égaux à `shortcut`. Le premier fichier qui en a masque les suivants."""
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        conflicts = find_conflicts(text, shortcut, str(path))
        if conflicts:
            return conflicts
    return []


# --- Extinction et redémarrage -----------------------------------------------------

LXQT_SERVICE = "org.lxqt.session"
LXQT_PATH = "/LXQtSession"
# action → (méthode « peut-on ? », méthode à appeler, option équivalente de lxqt-leave)
_ACTIONS = {"poweroff": ("canPowerOff", "powerOff", "--shutdown"), "reboot": ("canReboot", "reboot", "--reboot")}

Runner = Callable[[list[str]], str]
Starter = Callable[[str, list[str]], bool]


def _run(argv: list[str]) -> str:
    return run_capture(argv, timeout=4) or ""


def _start(program: str, args: list[str]) -> bool:
    return start_detached(program, args)


class SessionPower:
    """Éteindre ou redémarrer par la session LXQt."""

    def __init__(self, dbus_send: str | None, lxqt_leave: str | None, runner: Runner = _run, starter: Starter = _start):
        self.dbus_send = dbus_send
        self.lxqt_leave = lxqt_leave
        self._run = runner
        self._start = starter

    @classmethod
    def detect(cls, env: Mapping[str, str] | None = None,
               which: Callable[[str], str | None] = find_program) -> SessionPower | None:
        """Disponible seulement dans une session LXQt avec `dbus-send` ou `lxqt-leave`."""
        env = os.environ if env is None else env
        desktops = [d.strip().lower() for d in env.get("XDG_CURRENT_DESKTOP", "").split(":")]
        if "lxqt" not in desktops:
            return None
        dbus_send, lxqt_leave = which("dbus-send"), which("lxqt-leave")
        if not dbus_send and not lxqt_leave:
            return None
        return cls(dbus_send, lxqt_leave)

    def _call(self, method: str, reply: bool) -> list[str]:
        argv = [self.dbus_send, "--session"]
        argv += ["--print-reply"] if reply else ["--type=method_call"]
        return argv + [f"--dest={LXQT_SERVICE}", LXQT_PATH, f"{LXQT_SERVICE}.{method}"]

    def request(self, action: str) -> str:
        """« session », « lxqt-leave » ou « » (rien de possible : afficher le guide)."""
        can, method, leave_option = _ACTIONS[action]
        if self.dbus_send and "boolean true" in self._run(self._call(can, reply=True)):
            argv = self._call(method, reply=False)
            if self._start(argv[0], argv[1:]):
                return "session"
        if self.lxqt_leave and self._start(self.lxqt_leave, [leave_option]):
            return "lxqt-leave"
        return ""
