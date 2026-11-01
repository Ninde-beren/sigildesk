"""Liste et ramène les fenêtres par `wmctrl` (X11, EWMH). La lecture des lignes est dans `domain.windows`."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from pathlib import Path

from sigildesk.domain.windows import BROWSER_INSTANCES, HIDDEN_CLASSES, OpenWindow, host_matches, parse_wmctrl
from sigildesk.infra.processes import find_program, run_capture

Runner = Callable[[list[str]], "str | None"]


def _run(argv: list[str]) -> str | None:
    return run_capture(argv, timeout=3)


class WindowManager:
    def __init__(self, wmctrl: str, runner: Runner = _run, own_pid: int | None = None):
        self.wmctrl = wmctrl
        self._run = runner
        self._own_pid = os.getpid() if own_pid is None else own_pid

    @classmethod
    def detect(cls, env: Mapping[str, str] | None = None,
               which: Callable[[str], str | None] = find_program) -> WindowManager | None:
        """X11 avec wmctrl seulement : sous Wayland, la liste des fenêtres n'est pas accessible ainsi."""
        env = os.environ if env is None else env
        if env.get("XDG_SESSION_TYPE", "").lower() == "wayland" or not env.get("DISPLAY"):
            return None
        program = which("wmctrl")
        return cls(program) if program else None

    def list(self) -> list[OpenWindow]:
        """Les fenêtres de la personne : ni le bureau, ni le panneau, ni SigilDesk lui-même."""
        output = self._run([self.wmctrl, "-l", "-x", "-p"])
        if output is None:
            return []
        return [w for w in parse_wmctrl(output)
                if w.desktop >= 0 and w.pid != self._own_pid and w.wm_class.lower() not in HIDDEN_CLASSES]

    def activate(self, window_id: str) -> bool:
        if not window_id.startswith("0x"):
            return False
        return self._run([self.wmctrl, "-i", "-a", window_id]) is not None

    # --- correspondance avec les tuiles ----------------------------------------------

    def find_app_window(self, host: str) -> OpenWindow | None:
        return next((w for w in self.list() if host_matches(w.instance, host)), None)

    def find_browser_window(self) -> OpenWindow | None:
        return next((w for w in self.list() if w.instance.lower() in BROWSER_INSTANCES), None)

    def find_folder_window(self, folder: Path) -> OpenWindow | None:
        return next((w for w in self.list() if w.wm_class == "pcmanfm-qt" and w.title == folder.name), None)


class StaticWindowManager(WindowManager):
    """Fenêtres imaginaires, pour les captures et les tests de mise en page."""

    def __init__(self, windows: list[OpenWindow]):
        super().__init__("wmctrl", own_pid=-1)
        self._windows = windows

    def list(self) -> list[OpenWindow]:
        return list(self._windows)

    def activate(self, window_id: str) -> bool:
        return any(w.id == window_id for w in self._windows)
