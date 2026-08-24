"""
tools/applications.py
----------------------
Open, close, and query the status of applications on Windows.

Design notes:
- We never hardcode a single user's install path. Resolution order:
    1. Known Windows "app name" launchers (start shell:AppsFolder / explorer verbs)
    2. shutil.which() on PATH
    3. Common installation directories (Program Files, LOCALAPPDATA, etc.)
    4. os.startfile() as a last resort for anything the OS itself can open
- All functions return a plain dict result: {"success": bool, "message": str, ...}
  so the executor/observer can reason about them without exceptions leaking out.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from assistant.logger import get_logger

log = get_logger("tools.applications")

IS_WINDOWS = platform.system() == "Windows"

# Common name -> list of candidate resolvers (exe names / well-known aliases).
# Each entry is tried in order until one resolves.
KNOWN_APPS: dict[str, list[str]] = {
    "chrome": ["chrome.exe", "chrome"],
    "google chrome": ["chrome.exe", "chrome"],
    "edge": ["msedge.exe", "msedge"],
    "microsoft edge": ["msedge.exe", "msedge"],
    "msedge": ["msedge.exe", "msedge"],
    "firefox": ["firefox.exe", "firefox"],
    "vs code": ["code.exe", "code", "code.cmd"],
    "vscode": ["code.exe", "code", "code.cmd"],
    "visual studio code": ["code.exe", "code", "code.cmd"],
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "file explorer": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
    "windows terminal": ["wt.exe"],
    "powershell": ["powershell.exe", "pwsh.exe"],
    "cmd": ["cmd.exe"],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "spotify": ["spotify.exe"],
    "slack": ["slack.exe"],
}

# Extra directories to search beyond PATH, in rough priority order.
_EXTRA_SEARCH_DIRS = [
    os.environ.get("PROGRAMFILES", r"C:\Program Files"),
    os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
    os.environ.get("LOCALAPPDATA", ""),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
]


def _resolve_executable(app_name: str) -> str | None:
    """Try to find a launchable path/command for a known or arbitrary app name."""
    key = app_name.strip().lower()
    candidates = KNOWN_APPS.get(key, [app_name])

    for candidate in candidates:
        # 1. Already on PATH?
        found = shutil.which(candidate)
        if found:
            return found

    # 2. Search common install directories (shallow, bounded depth) for a matching exe.
    #    Normalize every candidate to a ".exe" name so this works even when the
    #    user (or KNOWN_APPS) only gave a bare name like "msedge" or "chrome".
    target_names = {
        c.lower() if c.lower().endswith(".exe") else f"{c.lower()}.exe"
        for c in candidates
    }
    if target_names:
        for base in _EXTRA_SEARCH_DIRS:
            if not base or not os.path.isdir(base):
                continue
            try:
                for root, dirs, files in os.walk(base):
                    # Check files at THIS level first (e.g. msedge.exe lives at
                    # exactly depth 3: Microsoft\Edge\Application\msedge.exe),
                    # then bound how much deeper we're willing to descend.
                    for f in files:
                        if f.lower() in target_names:
                            return str(Path(root) / f)

                    depth = root[len(base):].count(os.sep)
                    if depth >= 3:
                        dirs[:] = []
            except (PermissionError, OSError):
                continue

    return None


def open_application(name: str) -> dict:
    """Launch an application by common name."""
    if not name or not name.strip():
        return {"success": False, "message": "No application name provided."}

    if not IS_WINDOWS:
        return {
            "success": False,
            "message": f"open_application is a Windows-only tool in this build "
                       f"(host OS is {platform.system()}). Cannot launch '{name}' here.",
        }

    exe_path = _resolve_executable(name)
    if not exe_path:
        return {
            "success": False,
            "message": f"Could not find an installation of '{name}'. "
                       f"It may not be installed, or its name isn't recognized.",
        }

    try:
        subprocess.Popen([exe_path], shell=False)
        log.info(f"Launched '{name}' -> {exe_path}")
        return {"success": True, "message": f"{name} is opening.", "resolved_path": exe_path}
    except Exception as e:
        log.error(f"Failed to launch '{name}': {e}")
        return {"success": False, "message": f"Failed to launch {name}: {e}"}


def close_application(name: str) -> dict:
    """Close a running application by name (Windows: taskkill by image name)."""
    if not IS_WINDOWS:
        return {"success": False, "message": "close_application requires Windows."}

    key = name.strip().lower()
    candidates = KNOWN_APPS.get(key, [name])
    exe_names = [c if c.lower().endswith(".exe") else f"{c}.exe" for c in candidates]

    last_error = None
    for exe in exe_names:
        try:
            result = subprocess.run(
                ["taskkill", "/IM", exe, "/F"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                log.info(f"Closed '{name}' ({exe})")
                return {"success": True, "message": f"{name} has been closed."}
            last_error = result.stderr.strip()
        except Exception as e:
            last_error = str(e)

    return {"success": False, "message": f"Could not close {name}: {last_error or 'not running'}"}


def is_application_running(name: str) -> dict:
    """Check whether a process matching `name` is currently running."""
    if not IS_WINDOWS:
        return {"success": False, "running": False, "message": "Requires Windows."}

    key = name.strip().lower()
    candidates = KNOWN_APPS.get(key, [name])
    exe_names = [c if c.lower().endswith(".exe") else f"{c}.exe" for c in candidates]

    try:
        result = subprocess.run(
            ["tasklist"], capture_output=True, text=True, timeout=10,
        )
        running_list = result.stdout.lower()
        for exe in exe_names:
            if exe.lower() in running_list:
                return {"success": True, "running": True, "message": f"{name} is running."}
        return {"success": True, "running": False, "message": f"{name} is not running."}
    except Exception as e:
        return {"success": False, "running": False, "message": str(e)}
