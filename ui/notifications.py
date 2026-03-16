"""Native OS notifications via PyQt6."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtWidgets import QSystemTrayIcon

logger = logging.getLogger(__name__)


class NotificationManager:
    """Sends native OS notifications through the system tray icon."""

    def __init__(self, tray_icon: QSystemTrayIcon, enabled: bool = True):
        self._tray = tray_icon
        self._enabled = enabled

    def notify(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information) -> None:
        if not self._enabled:
            return
        if self._tray.supportsMessages():
            self._tray.showMessage(title, message, icon, 3000)
        logger.info("Notification: %s — %s", title, message)

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
