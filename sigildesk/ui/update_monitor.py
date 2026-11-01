"""Rappel de redémarrage après les mises à jour automatiques, sans insister.

Toutes les 30 minutes, `infra.updates` dit si un redémarrage est nécessaire ;
si oui, `rebootSuggested` ouvre le dialogue « Redémarrer pour terminer les
mises à jour ? ». « Plus tard » repose la question quatre heures après, ou au
prochain démarrage. L'état des mises à jour automatiques est affiché dans
Paramètres › Maintenance.
"""

from __future__ import annotations

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from sigildesk.infra.updates import AutoUpdates, auto_updates_status, reboot_required

CHECK_MS = 30 * 60 * 1000
SNOOZE_MS = 4 * 60 * 60 * 1000


class UpdateMonitor(QObject):
    changed = Signal()
    rebootSuggested = Signal()

    def __init__(self, check=reboot_required, status=auto_updates_status, parent: QObject | None = None):
        super().__init__(parent)
        self._check = check
        self._status = status
        self._required = False
        self._snoozed = False
        self._auto = AutoUpdates(False, None)
        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_MS)
        self._timer.timeout.connect(self.check)
        self._snooze = QTimer(self)
        self._snooze.setSingleShot(True)
        self._snooze.timeout.connect(self._end_snooze)

    @Slot()
    def start(self) -> None:
        self.check()
        self._timer.start()

    @Slot()
    def check(self) -> None:
        required = self._check().required
        auto = self._status()
        if (required, auto) != (self._required, self._auto):
            self._required, self._auto = required, auto
            self.changed.emit()
        if required and not self._snoozed:
            self.rebootSuggested.emit()

    @Slot()
    def later(self) -> None:
        """« Plus tard » : la question revient dans quatre heures."""
        self._snoozed = True
        self._snooze.start(SNOOZE_MS)

    def _end_snooze(self) -> None:
        self._snoozed = False
        self.check()

    def _auto_label(self) -> str:
        if not self._auto.enabled:
            return "Mises à jour automatiques non réglées (scripts/install-system-deps.sh)."
        if self._auto.last_run is None:
            return "Mises à jour automatiques activées ; aucune passe pour l'instant."
        last = self._auto.last_run.strftime("%d/%m à %H:%M")
        return f"Mises à jour automatiques activées ; dernière passe le {last}."

    rebootRequired = Property(bool, lambda self: self._required, notify=changed)
    autoUpdatesEnabled = Property(bool, lambda self: self._auto.enabled, notify=changed)
    autoUpdatesLabel = Property(str, lambda self: self._auto_label(), notify=changed)
