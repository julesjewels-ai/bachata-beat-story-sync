"""Native file picker dialogs using tkinter (local mode only).

This module provides wrappers around tkinter file dialogs, executing them in
separate processes to avoid main-thread blocking on macOS.

Warning: File dialogs are only available in local mode (not Streamlit Cloud).
In deployed mode, users must upload files through the web UI.
"""

from __future__ import annotations

import json
import subprocess
import sys


def _run_safe_tk_dialog(script: str) -> str | None:
    """Execute tkinter script in separate process to avoid macOS main-thread issues.

    Args:
        script: Python script to execute (should print the selected path on success)

    Returns:
        User-selected path, or None if dialog was cancelled or execution failed.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:  # noqa: BLE001
        return None
    return None


def pick_folder(title: str = "Select folder") -> str | None:
    """Open a native folder picker dialog.

    Args:
        title: Dialog window title

    Returns:
        Selected folder path, or None if cancelled/unavailable.
    """
    # Safely serialize title to avoid injection attacks
    safe_title = json.dumps(title)

    script = f"""
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes("-topmost", True)
path = filedialog.askdirectory(title={safe_title})
root.destroy()
if path:
    print(path)
"""
    return _run_safe_tk_dialog(script)


def pick_audio_file() -> str | None:
    """Open a native file picker dialog for audio files.

    Returns:
        Selected audio file path (.wav or .mp3), or None if cancelled/unavailable.
    """
    script = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes("-topmost", True)
path = filedialog.askopenfilename(
    title='Select audio file',
    filetypes=[('Audio files', '*.wav *.mp3'), ('All files', '*.*')],
)
root.destroy()
if path:
    print(path)
"""
    return _run_safe_tk_dialog(script)


def pick_output_file() -> str | None:
    """Open a native save-as dialog for the output video file.

    Returns:
        Selected output file path (.mp4), or None if cancelled/unavailable.
    """
    script = """
import tkinter as tk
from tkinter import filedialog
root = tk.Tk()
root.withdraw()
root.wm_attributes("-topmost", True)
path = filedialog.asksaveasfilename(
    title='Save output video as',
    defaultextension='.mp4',
    filetypes=[('MP4 video', '*.mp4'), ('All files', '*.*')],
)
root.destroy()
if path:
    print(path)
"""
    return _run_safe_tk_dialog(script)
