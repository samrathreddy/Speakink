"""Clipboard-based text insertion."""

from __future__ import annotations

import logging
import platform
import time

import pyperclip
from pynput.keyboard import Controller, Key

from speakink.providers.insertion.base import InsertionMethod

logger = logging.getLogger(__name__)


class ClipboardInsertion(InsertionMethod):
    name = "clipboard"
    display_name = "Clipboard Paste"

    def __init__(self):
        self._controller = Controller()

    def insert(self, text: str) -> None:
        if not text:
            return

        try:
            # Save current clipboard
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                old_clipboard = ""

            # Copy text to clipboard and paste
            pyperclip.copy(text)
            logger.info("Copied to clipboard: %s", text[:50])
            time.sleep(0.1)

            paste_key = Key.cmd if platform.system() == "Darwin" else Key.ctrl
            self._controller.press(paste_key)
            self._controller.press("v")
            self._controller.release("v")
            self._controller.release(paste_key)
            logger.info("Pasted %d characters via clipboard", len(text))

            # Restore clipboard after a brief delay
            time.sleep(0.2)
            try:
                pyperclip.copy(old_clipboard)
            except Exception:
                pass
        except Exception:
            logger.exception("Clipboard insertion failed")
