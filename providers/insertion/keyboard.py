"""Keyboard-based text insertion via pynput."""

from __future__ import annotations

import logging
import time

from pynput.keyboard import Controller, Key

from speakink.providers.insertion.base import InsertionMethod

logger = logging.getLogger(__name__)


class KeyboardInsertion(InsertionMethod):
    name = "keyboard"
    display_name = "Keyboard Typing"

    def __init__(self):
        self._controller = Controller()

    def insert(self, text: str) -> None:
        if not text:
            return
        try:
            time.sleep(0.1)
            for char in text:
                if char == "\n":
                    self._controller.press(Key.enter)
                    self._controller.release(Key.enter)
                else:
                    self._controller.type(char)
            logger.info("Typed %d characters via keyboard", len(text))
        except Exception:
            logger.exception("Keyboard insertion failed")
