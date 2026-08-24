"""
tools/files.py
---------------
Filesystem operations, built on pathlib.

Safety rules baked in here (defense in depth, on top of assistant/safety.py):
- delete_file / delete_folder NEVER run without an explicit `confirmed=True`
  flag set by the executor after the safety manager has approved the action.
- No recursive glob deletes. delete_folder requires an exact path.
- All paths are resolved and checked to exist (or explicitly allowed not to)
  before any destructive operation.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from assistant.logger import get_logger

log = get_logger("tools.files")


def _safe_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def search_files(directory: str, pattern: str = "*", recursive: bool = True) -> dict:
    """Find files under `directory` matching a glob `pattern` (e.g. '*.pdf')."""
    base = _safe_path(directory)
    if not base.exists() or not base.is_dir():
        return {"success": False, "message": f"Directory not found: {base}", "results": []}

    try:
        matches = list(base.rglob(pattern)) if recursive else list(base.glob(pattern))
        files = [str(p) for p in matches if p.is_file()]
        return {
            "success": True,
            "message": f"Found {len(files)} file(s) matching '{pattern}' in {base}.",
            "results": files,
        }
    except PermissionError as e:
        return {"success": False, "message": f"Permission denied: {e}", "results": []}


def create_folder(path: str) -> dict:
    target = _safe_path(path)
    try:
        target.mkdir(parents=True, exist_ok=True)
        log.info(f"Created folder: {target}")
        return {"success": True, "message": f"Folder created: {target}"}
    except PermissionError as e:
        return {"success": False, "message": f"Permission denied creating {target}: {e}"}
    except OSError as e:
        return {"success": False, "message": f"Could not create folder {target}: {e}"}


def create_file(path: str, content: str = "") -> dict:
    target = _safe_path(path)
    if target.exists():
        return {"success": False, "message": f"File already exists: {target} (use a different name, or rename/move instead)"}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        log.info(f"Created file: {target}")
        return {"success": True, "message": f"File created: {target}"}
    except (PermissionError, OSError) as e:
        return {"success": False, "message": f"Could not create file {target}: {e}"}


def read_file(path: str, max_chars: int = 20000) -> dict:
    target = _safe_path(path)
    if not target.exists() or not target.is_file():
        return {"success": False, "message": f"File not found: {target}", "content": None}
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        truncated = len(content) > max_chars
        return {
            "success": True,
            "message": f"Read {len(content)} chars from {target}." + (" (truncated)" if truncated else ""),
            "content": content[:max_chars],
            "truncated": truncated,
        }
    except (PermissionError, OSError) as e:
        return {"success": False, "message": f"Could not read {target}: {e}", "content": None}


def move_file(source: str, destination: str) -> dict:
    src, dst = _safe_path(source), _safe_path(destination)
    if not src.exists():
        return {"success": False, "message": f"Source not found: {src}"}
    if dst.exists():
        return {"success": False, "message": f"Destination already exists: {dst} (refusing to overwrite)"}
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        log.info(f"Moved {src} -> {dst}")
        return {"success": True, "message": f"Moved {src.name} to {dst}"}
    except (PermissionError, OSError) as e:
        return {"success": False, "message": f"Could not move {src} -> {dst}: {e}"}


def copy_file(source: str, destination: str) -> dict:
    src, dst = _safe_path(source), _safe_path(destination)
    if not src.exists() or not src.is_file():
        return {"success": False, "message": f"Source file not found: {src}"}
    if dst.exists():
        return {"success": False, "message": f"Destination already exists: {dst} (refusing to overwrite)"}
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        log.info(f"Copied {src} -> {dst}")
        return {"success": True, "message": f"Copied {src.name} to {dst}"}
    except (PermissionError, OSError) as e:
        return {"success": False, "message": f"Could not copy {src} -> {dst}: {e}"}


def rename_file(path: str, new_name: str) -> dict:
    src = _safe_path(path)
    if not src.exists():
        return {"success": False, "message": f"File not found: {src}"}
    dst = src.parent / new_name
    if dst.exists():
        return {"success": False, "message": f"A file named '{new_name}' already exists there."}
    try:
        src.rename(dst)
        log.info(f"Renamed {src} -> {dst}")
        return {"success": True, "message": f"Renamed to {dst.name}"}
    except OSError as e:
        return {"success": False, "message": f"Could not rename {src}: {e}"}


def delete_file(path: str, confirmed: bool = False) -> dict:
    """Delete a single file. Requires `confirmed=True` — the executor must only
    set this after the safety manager's HIGH-risk confirmation has been granted."""
    if not confirmed:
        return {"success": False, "message": "Refusing to delete: confirmation flag not set."}

    target = _safe_path(path)
    if not target.exists():
        return {"success": False, "message": f"File not found: {target}"}
    if target.is_dir():
        return {"success": False, "message": f"{target} is a directory — use delete_folder instead."}
    try:
        target.unlink()
        log.info(f"Deleted file: {target}")
        return {"success": True, "message": f"Deleted {target}"}
    except (PermissionError, OSError) as e:
        return {"success": False, "message": f"Could not delete {target}: {e}"}


def delete_folder(path: str, confirmed: bool = False) -> dict:
    """Delete a folder and its contents. Requires `confirmed=True`, and refuses
    to operate on root-like or extremely shallow paths as an extra guardrail."""
    if not confirmed:
        return {"success": False, "message": "Refusing to delete: confirmation flag not set."}

    target = _safe_path(path)
    if not target.exists() or not target.is_dir():
        return {"success": False, "message": f"Folder not found: {target}"}

    # Guardrail: refuse to delete drive roots or very shallow paths like C:\Users
    if len(target.parts) <= 3:
        return {"success": False, "message": f"Refusing to delete a top-level path for safety: {target}"}

    try:
        shutil.rmtree(target)
        log.info(f"Deleted folder: {target}")
        return {"success": True, "message": f"Deleted folder {target}"}
    except (PermissionError, OSError) as e:
        return {"success": False, "message": f"Could not delete folder {target}: {e}"}


def open_file(path: str) -> dict:
    """Open a file with its default associated application."""
    target = _safe_path(path)
    if not target.exists():
        return {"success": False, "message": f"File not found: {target}"}
    try:
        os.startfile(target)  # type: ignore[attr-defined]  # Windows-only
        log.info(f"Opened file: {target}")
        return {"success": True, "message": f"Opened {target}"}
    except AttributeError:
        return {"success": False, "message": "open_file requires Windows (os.startfile)."}
    except OSError as e:
        return {"success": False, "message": f"Could not open {target}: {e}"}
