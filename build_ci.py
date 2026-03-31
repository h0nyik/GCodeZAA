#!/usr/bin/env python3
"""
Cross-platform PyInstaller build script for GCodeZAA GUI.
Used by GitHub Actions — handles platform differences in Python.
"""
import sys
import os
import subprocess

sep = ";" if sys.platform == "win32" else ":"
no_open3d = os.environ.get("NO_OPEN3D") == "1"

cmd = [
    sys.executable, "-m", "PyInstaller",
    "gui.py",
    "--name", "GCodeZAA",
    "--windowed",
    "--noconfirm",
    "--clean",
    "--collect-all", "customtkinter",
    "--collect-all", "tkinterdnd2",
    f"--add-data=gcodezaa{sep}gcodezaa",
]

if not no_open3d:
    cmd += ["--collect-all", "open3d"]

print("Running:", " ".join(cmd))
result = subprocess.run(cmd)
sys.exit(result.returncode)
