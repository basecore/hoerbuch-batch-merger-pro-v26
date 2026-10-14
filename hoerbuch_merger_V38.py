#!/usr/bin/env python3
"""Hörbuch Batch-Merger PRO V38 – Start mit automatischer Modulinstallation."""

import importlib
import os
import shutil
import subprocess
import sys

REQUIRED_PACKAGES = {
    "PyQt5": "PyQt5",
    "mutagen": "mutagen",
}

def ensure_python_packages():
    missing = []
    for module_name, package_name in REQUIRED_PACKAGES.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        print("📦 Fehlende Python-Pakete werden installiert:")
        print("   " + ", ".join(missing))
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--user", *missing]
        )

def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        print("⚠ ffmpeg wurde nicht gefunden.")
        print("   Bitte einmalig installieren:")
        print("   sudo apt install ffmpeg")

def main():
    ensure_python_packages()
    check_ffmpeg()

    script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "hoerbuch_merger_V37.py"
    )

    if not os.path.exists(script):
        print("❌ hoerbuch_merger_V37.py wurde nicht gefunden.")
        sys.exit(1)

    subprocess.call([sys.executable, script])

if __name__ == "__main__":
    main()
