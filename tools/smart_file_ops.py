"""
tools/smart_file_ops.py
------------------------
Natural-language-friendly move/copy/rename/delete.

These wrap the strict, exact-path tools in tools/files.py with the same
kind of fuzzy resolution smart_open.py uses for "open X": if the user
doesn't give an exact path, common folders (Desktop, Documents, Downloads,
Pictures, Videos, Music) are searched for a matching file, a single strong
match is used automatically, and multiple matches are reported instead of
guessed at.

Every function here still goes through the same safety-manager risk
classification (assistant/safety.py) and, for deletes, the same
confirmation flow as the underlying tools — this module only makes the
INPUT more forgiving. It never loosens what happens before an action runs.

Folder deletion is deliberately NOT fuzzy-matched — only an exact path
deletes a folder. Fuzzy-matching is fine for a wrong FILE (one confirmation
prompt shows you exactly what's about to happen either way), but the blast
radius of deleting the wrong FOLDER is high enough to require the user be
unambiguous about which one they mean.
"""

from __future__ import annotations

import os
from pathlib import Path

from assistant.logger import get_logger
from tools import files

log = get_logger("tools.smart_file_ops")

_SKIP_DIR_NAMES = {
    "node_modules", "__pycache__", ".git", "venv", ".venv",
    "$recycle.bin", "system volume information", ".cache",
}
_MAX_FILES_SCANNED = 20000
_MAX_DEPTH = 4

_KNOWN_DIRS = {
    "desktop": "Desktop",
    "documents": "Documents",
    "downloads": "Downloads",
    "pictures": "Pictures",
    "videos": "Videos",
    "music": "Music",
}


def _candidate_directories() -> list[Path]:
    home = Path.home()
    candidates = [
        home / "Desktop", home / "Documents", home / "Downloads",
        home / "Pictures", home / "Videos", home / "Music",
        home / "OneDrive" / "Desktop", home / "OneDrive" / "Documents",
        home / "OneDrive" / "Pictures",
    ]
    return [d for d in candidates if d.is_dir()]


def _normalize(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _search_files(query: str, directories: list[Path], max_results: int = 5) -> list[str]:
    """Ranked exact/starts-with/contains/fuzzy search, scoped to files only
    (never matches a directory) — same ranking smart_open.py uses."""
    query_lower = query.strip().lower()
    query_stem = Path(query_lower).stem
    query_norm = _normalize(query_stem)

    exact, starts, contains, fuzzy = [], [], [], []
    scanned = 0

    for base in directories:
        base_depth = len(base.parts)
        stop = False
        for root, dirs, filenames in os.walk(base):
            dirs[:] = [d for d in dirs if d.lower() not in _SKIP_DIR_NAMES and not d.startswith(".")]
            depth = len(Path(root).parts) - base_depth
            if depth >= _MAX_DEPTH:
                dirs[:] = []

            for fname in filenames:
                scanned += 1
                if scanned > _MAX_FILES_SCANNED:
                    stop = True
                    break
                stem = Path(fname).stem.lower()
                full_lower = fname.lower()
                stem_norm = _normalize(stem)
                path = str(Path(root) / fname)

                if stem == query_stem or full_lower == query_lower:
                    exact.append(path)
                elif stem.startswith(query_stem) or full_lower.startswith(query_lower):
                    starts.append(path)
                elif query_stem and query_stem in stem:
                    contains.append(path)
                elif query_norm and query_norm in stem_norm:
                    fuzzy.append(path)
            if stop:
                break
        if stop:
            break

    ranked = exact + starts + contains + fuzzy
    seen: set[str] = set()
    deduped = []
    for p in ranked:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped[:max_results]


def _resolve_one_file(query: str) -> dict:
    """Resolve `query` to exactly one file path. Returns
    {"success": True, "path": ...} or {"success": False, "message": ...,
    ["matches": [...]]} describing why it couldn't."""
    candidate = Path(query).expanduser()
    if candidate.exists() and candidate.is_file():
        return {"success": True, "path": str(candidate.resolve())}

    directories = _candidate_directories()
    matches = _search_files(query, directories) if directories else []

    if not matches:
        return {
            "success": False,
            "message": f"Couldn't find a file matching '{query}' in Desktop, Documents, "
                       f"Downloads, Pictures, Videos, or Music.",
        }
    if len(matches) > 1:
        listing = "\n".join(f"  {i + 1}. {m}" for i, m in enumerate(matches))
        return {
            "success": False,
            "message": f"Found {len(matches)} matches for '{query}' — please be more specific:\n{listing}",
            "matches": matches,
        }
    return {"success": True, "path": matches[0]}


def _resolve_destination(destination: str, source_filename: str) -> str:
    """Expand a natural-language destination into a final target file path.

    - A known shorthand (Desktop/Documents/Downloads/Pictures/Videos/Music)
      or any existing directory -> the file keeps its name, inside that folder.
    - Otherwise, if the parent directory exists, the whole string is treated
      as the exact target path (supports 'move X to D:\\Backup\\X_old.txt').
    """
    key = destination.strip().lower()
    if key in _KNOWN_DIRS:
        expanded = Path.home() / _KNOWN_DIRS[key]
    else:
        expanded = Path(destination).expanduser()

    if expanded.is_dir():
        return str(expanded / source_filename)
    return str(expanded)


def smart_move(source: str, destination: str) -> dict:
    resolved = _resolve_one_file(source)
    if not resolved["success"]:
        return resolved

    src_path = resolved["path"]
    target = _resolve_destination(destination, Path(src_path).name)

    if not Path(target).parent.exists():
        return {"success": False, "message": f"Destination not found: {Path(target).parent}"}

    return files.move_file(src_path, target)


def smart_copy(source: str, destination: str) -> dict:
    resolved = _resolve_one_file(source)
    if not resolved["success"]:
        return resolved

    src_path = resolved["path"]
    target = _resolve_destination(destination, Path(src_path).name)

    if not Path(target).parent.exists():
        return {"success": False, "message": f"Destination not found: {Path(target).parent}"}

    return files.copy_file(src_path, target)


def smart_rename(path: str, new_name: str) -> dict:
    resolved = _resolve_one_file(path)
    if not resolved["success"]:
        return resolved

    return files.rename_file(resolved["path"], new_name)


def smart_delete(path: str) -> dict:
    """Resolve `path` and delete it.

    Files are found via fuzzy search across common folders, same as the
    other smart_* tools. Folders are only deleted when an exact,
    unambiguous path is given — see the module docstring for why.

    This is only ever reached AFTER the safety manager's HIGH-risk
    confirmation has already been shown and approved (smart_delete itself
    is classified HIGH risk in assistant/safety.py), so it's safe to pass
    confirmed=True to the underlying delete calls here.
    """
    candidate = Path(path).expanduser()
    if candidate.exists() and candidate.is_dir():
        return files.delete_folder(str(candidate.resolve()), confirmed=True)

    resolved = _resolve_one_file(path)
    if not resolved["success"]:
        return resolved

    return files.delete_file(resolved["path"], confirmed=True)