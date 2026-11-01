"""Lance une `Command` construite par `domain.commands`, et rien d'autre.

Le programme est déjà un chemin absolu, les arguments sont séparés, l'adresse
est validée : il ne reste qu'à appeler `QProcess.startDetached`, depuis le
dossier personnel, et à traduire un échec en message pour l'utilisateur.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from sigildesk.domain.commands import Command, CommandBuilder, LaunchError
from sigildesk.infra.processes import start_detached

log = logging.getLogger(__name__)

# starter(programme, arguments, dossier de travail) → démarré ?
Starter = Callable[[str, list[str], str], bool]


class Launcher:
    def __init__(self, builder: CommandBuilder, starter: Starter = start_detached, workdir: Path | None = None):
        self.builder = builder
        self._starter = starter
        self._workdir = str(workdir or Path.home())

    def run(self, command: Command) -> None:
        log.info("lancement : %s", command.argv())
        if not self._starter(command.program, list(command.args), self._workdir):
            raise LaunchError("Le programme n'a pas pu démarrer.")

    def open_url(self, url: str, preference: str = "auto", app_window: bool = False) -> None:
        self.run(self.builder.browser_command(url, preference, app_window))

    def open_folder(self, folder: Path) -> None:
        self.run(self.builder.folder_command(folder))
