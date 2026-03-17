"""
SpeakInk Build Script
Generates .app (macOS) or .exe (Windows) using PyInstaller.

Usage:
    python build.py
"""

import subprocess
import sys
import os
import platform
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# PROJECT_ROOT is the parent of SCRIPT_DIR so that `speakink` is a package on the path
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
if IS_WINDOWS:
    PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
    PIP = os.path.join(VENV_DIR, "Scripts", "pip.exe")
else:
    PYTHON = os.path.join(VENV_DIR, "bin", "python3")
    PIP = os.path.join(VENV_DIR, "bin", "pip")

APP_NAME = "SpeakInk"
ENTRY_POINT = os.path.join(SCRIPT_DIR, "main.py")

# All hidden imports that PyInstaller won't auto-detect
HIDDEN_IMPORTS = [
    # STT providers (lazy/conditional imports)
    "assemblyai",
    "assemblyai.streaming",
    "assemblyai.streaming.v3",
    "websocket",
    "websocket._abnf",
    "websocket._app",
    "websocket._core",
    "riva.client",
    "riva.client.asr",
    "faster_whisper",
    # LLM/correction providers
    "google.genai",
    "google.genai.types",
    "ollama",
    # Core deps
    "sounddevice",
    "numpy",
    "pynput",
    "pynput.keyboard",
    "pynput.keyboard._darwin" if IS_MAC else "pynput.keyboard._win32",
    "pyperclip",
    "webrtcvad",
    "httpx",
    "requests",
    # PyQt6
    "PyQt6.QtWidgets",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtSvg",
    "PyQt6.sip",
    # SpeakInk modules (provider registry auto-discovery)
    "speakink.providers.stt.nvidia_provider",
    "speakink.providers.stt.assemblyai_provider",
    "speakink.providers.stt.cartesia_provider",
    "speakink.providers.stt.elevenlabs_provider",
    "speakink.providers.stt.whisper_streaming",
    "speakink.providers.llm.gemini_provider",
    "speakink.providers.llm.ollama_provider",
    "speakink.providers.insertion.clipboard",
    "speakink.providers.insertion.keyboard",
    # gRPC (for nvidia riva)
    "grpc",
    "grpc._cython",
    "grpc._cython.cygrpc",
]

# Data files to bundle: (source, dest_in_bundle)
DATA_FILES = [
    (os.path.join(SCRIPT_DIR, "ui", "assets", "check.svg"), os.path.join("speakink", "ui", "assets")),
]


def ensure_pyinstaller():
    """Install PyInstaller in the venv if not present."""
    try:
        subprocess.run(
            [PYTHON, "-c", "import PyInstaller"],
            capture_output=True, check=True,
        )
        print("  PyInstaller already installed")
    except subprocess.CalledProcessError:
        print("  Installing PyInstaller...")
        subprocess.run([PIP, "install", "pyinstaller"], check=True)


def build():
    print("=========================================")
    print(f"  SpeakInk Build ({platform.system()})")
    print("=========================================")
    print()

    if not os.path.exists(PYTHON):
        print("ERROR: venv not found. Run 'python setup.py' first.")
        sys.exit(1)

    # Step 1: Ensure PyInstaller
    print("[1/3] Checking PyInstaller...")
    ensure_pyinstaller()

    # Step 2: Build command
    print()
    print("[2/3] Building application...")

    dist_dir = os.path.join(SCRIPT_DIR, "dist")
    build_dir = os.path.join(SCRIPT_DIR, "build")

    cmd = [
        PYTHON, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--windowed",
        "--noconfirm",
        "--clean",
        "--distpath", dist_dir,
        "--workpath", build_dir,
        "--paths", PROJECT_ROOT,
    ]

    # Collect the entire speakink package (fixes "No module named speakink.core")
    cmd.extend(["--collect-submodules", "speakink"])
    cmd.extend(["--collect-data", "speakink"])

    # Hidden imports
    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    # Data files
    for src, dest in DATA_FILES:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src}{os.pathsep}{dest}"])

    # Platform-specific options & icon
    if IS_MAC:
        icon_path = os.path.join(SCRIPT_DIR, "ui", "assets", "icon.icns")
        mac_args = ["--osx-bundle-identifier", "com.speakink.app"]
        if os.path.exists(icon_path):
            mac_args.extend(["--icon", icon_path])
        cmd.extend(mac_args)
    elif IS_WINDOWS:
        icon_path = os.path.join(SCRIPT_DIR, "ui", "assets", "icon.ico")
        if os.path.exists(icon_path):
            cmd.extend(["--icon", icon_path])

    # Entry point
    cmd.append(ENTRY_POINT)

    print(f"  Entry: {ENTRY_POINT}")
    print(f"  Output: {dist_dir}")
    print()

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print()
        print("ERROR: Build failed. Check output above.")
        sys.exit(1)

    # Step 3: Report
    print()
    print("[3/3] Build complete!")
    print()

    if IS_MAC:
        app_path = os.path.join(dist_dir, f"{APP_NAME}.app")
        if os.path.exists(app_path):
            size_mb = _dir_size_mb(app_path)
            print(f"  Output: {app_path}")
            print(f"  Size:   {size_mb:.1f} MB")
            print()
            print("  To run:")
            print(f"    open {app_path}")
            print()
            print("  To distribute:")
            print(f"    Create a DMG or zip {APP_NAME}.app")
    elif IS_WINDOWS:
        exe_path = os.path.join(dist_dir, APP_NAME, f"{APP_NAME}.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"  Output: {exe_path}")
            print(f"  Size:   {size_mb:.1f} MB")
            print()
            print("  To run:")
            print(f"    {exe_path}")

    print()
    print("=========================================")


def _dir_size_mb(path):
    """Get directory size in MB."""
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            total += os.path.getsize(os.path.join(dirpath, f))
    return total / (1024 * 1024)


if __name__ == "__main__":
    build()
