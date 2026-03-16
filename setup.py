"""
SpeakInk Setup
Run: python setup.py
Does everything — venv, deps, then launches the app.
Works on macOS and Windows.
"""

import subprocess
import sys
import os
import platform
import shutil
import venv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
    PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
else:
    VENV_DIR = os.path.join(SCRIPT_DIR, "venv")
    PYTHON = os.path.join(VENV_DIR, "bin", "python3")

REQUIREMENTS_FILE = os.path.join(SCRIPT_DIR, "requirements.txt")


def load_env():
    """Load .env file and return env dict."""
    env = os.environ.copy()
    env_file = os.path.join(SCRIPT_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip()
                    if v:
                        env[k] = v
    return env


def run(cmd, desc="", env=None):
    if desc:
        print(f"  {desc}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout


def has_uv():
    """Check if uv is available."""
    return shutil.which("uv") is not None


def find_python312():
    """Find Python 3.12 on the system."""
    for name in ["python3.12", "python3", "python"]:
        path = shutil.which(name)
        if path:
            try:
                version = subprocess.run(
                    [path, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
                    capture_output=True, text=True,
                ).stdout.strip()
                if version == "3.12":
                    return path
            except Exception:
                continue
    return None


def main():
    print("=========================================")
    print("  SpeakInk Setup")
    print("  AI-powered voice dictation")
    print("=========================================")
    print()

    env = load_env()
    use_uv = has_uv()
    fresh_install = not os.path.exists(PYTHON)

    # Step 1: Create venv with Python 3.12
    print("[1/3] Setting up virtual environment...")
    if fresh_install:
        py312 = find_python312()
        if not py312:
            print("  ERROR: Python 3.12 is required but not found.")
            print("  Install it: brew install python@3.12 (macOS) or download from python.org")
            sys.exit(1)
        print(f"  Using {py312}")
        subprocess.run([py312, "-m", "venv", VENV_DIR], check=True)
        print("  Created venv (Python 3.12)")
    else:
        print("  venv already exists")

    # Step 2: Install dependencies
    print()
    print("[2/3] Installing dependencies...")
    if use_uv:
        print("  Using uv for fast installs...")
        run(
            ["uv", "pip", "install", "-r", REQUIREMENTS_FILE, "--python", PYTHON],
            "Installing packages...",
        )
    else:
        pip = os.path.join(VENV_DIR, "Scripts" if IS_WINDOWS else "bin", "pip")
        run([PYTHON, "-m", "pip", "install", "--upgrade", "pip", "-q"], "Upgrading pip...")
        run([pip, "install", "-q", "-r", REQUIREMENTS_FILE], "Installing packages (this may take a few minutes)...")
    print("  All packages installed")

    # Step 3: Launch
    print()
    print("[3/3] Launching SpeakInk...")

    if fresh_install:
        print()
        print("=========================================")
        print("  Welcome to SpeakInk!")
        print("=========================================")
        print()
        print("  Setup your free STT provider:")
        print()
        print("    1. Go to https://build.nvidia.com")
        print("       Sign up/Log in (click NVIDIA icon)")
        print("       Copy your API key")
        print()
        print("    2. Open speakink/.env and add:")
        print("       NVIDIA_API_KEY=nvapi-your_key_here")
        print()
        print("    3. Run: python setup.py")
        print()
        print("    NVIDIA Parakeet is free with higher rate")
        print("    limits — best accuracy, no credits, no expiry.")
        print()
        print("  Shortcut:")
        print("    Hold Shift to speak, release to stop.")
        print("    (push-to-talk mode)")
        print()
        print("  Want a different provider or shortcut?")
        print("    Right-click the tray icon > Settings")
        print("    Choose from AssemblyAI, Cartesia, ElevenLabs,")
        print("    or local Whisper. Change hotkey, mode, and more.")
        print("    All changes apply instantly.")
        print()
        print("=========================================")
    else:
        print("  Hold Shift to dictate. Right-click tray icon for Settings.")

    print()

    parent_dir = os.path.dirname(SCRIPT_DIR)
    os.chdir(parent_dir)
    launch_env = env.copy()
    launch_env["PYTHONPATH"] = parent_dir
    subprocess.run([PYTHON, os.path.join(SCRIPT_DIR, "main.py")], env=launch_env)


if __name__ == "__main__":
    main()
