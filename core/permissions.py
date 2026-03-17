"""macOS permission checks for microphone, accessibility, and input monitoring."""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import platform
import subprocess

logger = logging.getLogger(__name__)

IS_MAC = platform.system() == "Darwin"


def check_accessibility() -> bool:
    """Check if the app has Accessibility permission via AXIsProcessTrusted."""
    if not IS_MAC:
        return True
    try:
        hi = ctypes.CDLL(
            "/System/Library/Frameworks/ApplicationServices.framework"
            "/Frameworks/HIServices.framework/HIServices"
        )
        hi.AXIsProcessTrusted.restype = ctypes.c_bool
        return hi.AXIsProcessTrusted()
    except Exception:
        logger.debug("AXIsProcessTrusted check failed", exc_info=True)
        return True


def check_input_monitoring() -> bool:
    """Check if the app has Input Monitoring permission.

    Uses CGEventTapCreate as a practical test — if we can create an event tap
    that listens for key events, Input Monitoring is granted.
    """
    if not IS_MAC:
        return True
    try:
        cg = ctypes.CDLL(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
        )

        CGEVENT_CALLBACK = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_void_p,
        )

        def _passthrough(proxy, event_type, event, user_info):
            return event

        callback = CGEVENT_CALLBACK(_passthrough)

        cg.CGEventTapCreate.restype = ctypes.c_void_p
        cg.CGEventTapCreate.argtypes = [
            ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
            ctypes.c_uint64, ctypes.c_void_p, ctypes.c_void_p,
        ]

        kCGSessionEventTap = 1
        kCGHeadInsertEventTap = 0
        kCGEventTapOptionListenOnly = 1
        kCGEventKeyDown = 1 << 10

        tap = cg.CGEventTapCreate(
            kCGSessionEventTap, kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly, kCGEventKeyDown,
            callback, None,
        )

        if tap is None or tap == 0:
            return False

        cf = ctypes.CDLL(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        cf.CFRelease(tap)
        return True
    except Exception:
        logger.debug("CGEventTapCreate check failed", exc_info=True)
        return True


def check_microphone() -> bool:
    """Check if the app has Microphone permission via AVCaptureDevice API.

    Returns True only if status is Authorized (3). Returns False for
    NotDetermined (0), Restricted (1), or Denied (2).
    """
    if not IS_MAC:
        return True
    try:
        objc = ctypes.CDLL(ctypes.util.find_library("objc"))
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.sel_registerName.restype = ctypes.c_void_p

        AVCaptureDevice = objc.objc_getClass(b"AVCaptureDevice")
        sel_auth = objc.sel_registerName(b"authorizationStatusForMediaType:")

        # Create NSString for "soun" (AVMediaTypeAudio)
        NSString = objc.objc_getClass(b"NSString")
        sel_str = objc.sel_registerName(b"stringWithUTF8String:")
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        media_type = objc.objc_msgSend(NSString, sel_str, b"soun")

        # Get authorization status: 0=NotDetermined, 1=Restricted, 2=Denied, 3=Authorized
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        objc.objc_msgSend.restype = ctypes.c_long
        status = objc.objc_msgSend(AVCaptureDevice, sel_auth, media_type)

        return status == 3  # Authorized
    except Exception:
        logger.debug("Could not check microphone permission", exc_info=True)
        return True


def get_app_path() -> str:
    """Get the path of the running .app bundle, if any."""
    try:
        import sys
        if hasattr(sys, "_MEIPASS"):
            import os
            path = sys._MEIPASS
            while path and path != "/":
                if path.endswith(".app"):
                    return path
                path = os.path.dirname(path)
    except Exception:
        pass
    return ""


def request_accessibility() -> None:
    """Open Accessibility settings so the user can add the app."""
    if not IS_MAC:
        return
    try:
        subprocess.Popen([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        ])
    except Exception:
        logger.debug("Could not open Accessibility settings", exc_info=True)


def request_input_monitoring() -> None:
    """Open the Input Monitoring pane in System Settings."""
    if not IS_MAC:
        return
    try:
        subprocess.Popen([
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
        ])
    except Exception:
        logger.debug("Could not open Input Monitoring settings", exc_info=True)


def request_microphone() -> None:
    """Request microphone access — triggers the native macOS permission prompt.

    On macOS, apps are auto-added to the Microphone list when they first request
    access. There is no manual "+" button like Accessibility has.
    Uses sounddevice to briefly open the mic, which triggers the OS prompt.
    """
    if not IS_MAC:
        return
    try:
        import sounddevice as sd
        import threading

        def _trigger_mic_prompt():
            try:
                # Opening an input stream triggers the native macOS mic permission prompt
                stream = sd.InputStream(samplerate=16000, channels=1, blocksize=1024)
                stream.start()
                import time
                time.sleep(0.2)
                stream.stop()
                stream.close()
            except Exception:
                logger.debug("sounddevice mic prompt trigger failed", exc_info=True)

        # Run in thread to avoid blocking the UI
        threading.Thread(target=_trigger_mic_prompt, daemon=True).start()
    except Exception:
        logger.debug("Could not request microphone access", exc_info=True)
        # Fallback: open System Settings
        try:
            subprocess.Popen([
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
            ])
        except Exception:
            logger.debug("Could not open Microphone settings", exc_info=True)
