"""Global hotkey management via pynput."""

from __future__ import annotations

import logging
import platform
import threading
from typing import Callable, Optional

from pynput import keyboard

from speakink.core.types import HotkeyMode

logger = logging.getLogger(__name__)

# Map string keys to pynput keys
KEY_MAP = {
    "ctrl": keyboard.Key.ctrl,
    "shift": keyboard.Key.shift,
    "alt": keyboard.Key.alt,
    "cmd": keyboard.Key.cmd if platform.system() == "Darwin" else keyboard.Key.ctrl,
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "enter": keyboard.Key.enter,
}


def parse_hotkey(hotkey_str: str) -> set:
    """Parse a hotkey string like 'ctrl+shift+space' into a set of keys."""
    keys = set()
    for part in hotkey_str.lower().split("+"):
        part = part.strip()
        if part in KEY_MAP:
            keys.add(KEY_MAP[part])
        elif len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            logger.warning("Unknown key: %s", part)
    return keys


class HotkeyManager:
    """Manages global hotkeys for recording control."""

    def __init__(
        self,
        hotkey_str: str = "ctrl+shift+space",
        mode: HotkeyMode = HotkeyMode.TOGGLE,
        on_activate: Optional[Callable] = None,
        on_deactivate: Optional[Callable] = None,
    ):
        self._hotkey_keys = parse_hotkey(hotkey_str)
        self._mode = mode
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._pressed_keys: set = set()
        self._active = False
        self._suspended = False
        self._listener: Optional[keyboard.Listener] = None

    def start(self) -> None:
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info("Hotkey listener started: %s (%s)", self._hotkey_keys, self._mode.value)

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def _normalize_key(self, key) -> keyboard.Key | keyboard.KeyCode:
        """Normalize key variants (e.g., ctrl_l/ctrl_r -> ctrl)."""
        if hasattr(key, "name"):
            name = key.name
            # Map left/right variants to generic key
            if name.endswith("_l") or name.endswith("_r"):
                base_name = name[:-2]
                try:
                    return keyboard.Key[base_name]
                except KeyError:
                    pass
        return key

    def _on_press(self, key) -> None:
        normalized = self._normalize_key(key)
        self._pressed_keys.add(normalized)
        logger.debug("Key pressed: %s (normalized: %s) | current: %s | need: %s", key, normalized, self._pressed_keys, self._hotkey_keys)

        if self._suspended:
            return

        if self._hotkey_keys.issubset(self._pressed_keys):
            try:
                if self._mode == HotkeyMode.TOGGLE:
                    if self._active:
                        self._active = False
                        if self._on_deactivate:
                            self._on_deactivate()
                    else:
                        self._active = True
                        if self._on_activate:
                            self._on_activate()
                elif self._mode == HotkeyMode.PUSH_TO_TALK:
                    if not self._active:
                        self._active = True
                        if self._on_activate:
                            self._on_activate()
            except Exception:
                logger.exception("Hotkey activate/deactivate callback failed")

    def _on_release(self, key) -> None:
        normalized = self._normalize_key(key)
        self._pressed_keys.discard(normalized)

        if self._mode == HotkeyMode.PUSH_TO_TALK:
            if self._active and not self._hotkey_keys.issubset(self._pressed_keys):
                self._active = False
                if self._on_deactivate:
                    try:
                        self._on_deactivate()
                    except Exception:
                        logger.exception("Hotkey deactivate callback failed")

    @property
    def is_active(self) -> bool:
        return self._active

    def suspend(self) -> None:
        """Temporarily ignore hotkey (e.g. while settings window is recording a new hotkey)."""
        self._suspended = True
        logger.info("Hotkey listener suspended")

    def resume(self) -> None:
        """Re-enable hotkey listening."""
        self._suspended = False
        logger.info("Hotkey listener resumed")

    def update_hotkey(self, hotkey_str: str) -> None:
        self._hotkey_keys = parse_hotkey(hotkey_str)
        logger.info("Hotkey updated: %s", self._hotkey_keys)

    def update_mode(self, mode: HotkeyMode) -> None:
        self._mode = mode
        logger.info("Hotkey mode: %s", mode.value)
