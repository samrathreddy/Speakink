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
    """Check if the app can monitor keyboard input.

    Uses CGEventTapCreate as a practical test — more reliable than AXIsProcessTrusted
    for PyInstaller ad-hoc signed apps where the TCC code signature changes every build.
    """
    if not IS_MAC:
        return True
    try:
        cg = ctypes.CDLL(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
        )

        # CGEventTapCreate requires a real callback — NULL always returns NULL
        CGEVENT_CALLBACK = ctypes.CFUNCTYPE(
            ctypes.c_void_p,   # return: CGEventRef
            ctypes.c_void_p,   # proxy
            ctypes.c_uint32,   # event type
            ctypes.c_void_p,   # event
            ctypes.c_void_p,   # user info
        )

        def _passthrough(proxy, event_type, event, user_info):
            return event

        # Must keep a reference so it doesn't get garbage collected
        callback = CGEVENT_CALLBACK(_passthrough)

        cg.CGEventTapCreate.restype = ctypes.c_void_p
        cg.CGEventTapCreate.argtypes = [
            ctypes.c_uint32,   # tap location
            ctypes.c_uint32,   # place
            ctypes.c_uint32,   # options
            ctypes.c_uint64,   # events of interest
            ctypes.c_void_p,   # callback
            ctypes.c_void_p,   # user info
        ]

        kCGSessionEventTap = 1
        kCGHeadInsertEventTap = 0
        kCGEventTapOptionListenOnly = 1
        kCGEventKeyDown = 1 << 10

        tap = cg.CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            kCGEventKeyDown,
            callback,
            None,
        )

        if tap is None or tap == 0:
            return False

        # Clean up
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
    """
    if not IS_MAC:
        return
    try:
        objc = ctypes.CDLL(ctypes.util.find_library("objc"))
        objc.objc_getClass.restype = ctypes.c_void_p
        objc.sel_registerName.restype = ctypes.c_void_p

        AVCaptureDevice = objc.objc_getClass(b"AVCaptureDevice")

        # Create NSString for "soun" (AVMediaTypeAudio)
        NSString = objc.objc_getClass(b"NSString")
        sel_str = objc.sel_registerName(b"stringWithUTF8String:")
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_char_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        media_type = objc.objc_msgSend(NSString, sel_str, b"soun")

        # requestAccessForMediaType:completionHandler: triggers the system prompt
        sel_request = objc.sel_registerName(b"requestAccessForMediaType:completionHandler:")
        # completionHandler is a block — pass nil, the prompt still shows
        objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        objc.objc_msgSend.restype = ctypes.c_void_p
        objc.objc_msgSend(AVCaptureDevice, sel_request, media_type, None)
    except Exception:
        logger.debug("Could not request microphone access via AVCaptureDevice", exc_info=True)
        # Fallback: open System Settings
        try:
            subprocess.Popen([
                "open",
                "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
            ])
        except Exception:
            logger.debug("Could not open Microphone settings", exc_info=True)
