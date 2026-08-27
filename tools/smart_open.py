"""
tools/smart_open.py
---------------------
Handles "open X" requests where X isn't a recognized application or
website name.

Resolution order:
  1. Try resolving X as an installed application (same logic
     tools/applications.py uses — PATH + common install dirs).
  2. If that fails, search common user folders (Desktop, Documents,
     Downloads, Pictures, Videos, Music — including their OneDrive-
     redirected equivalents) for files whose name matches X.
  3. Exactly one strong match -> open it directly with its default app.
  4. Multiple matches -> report the candidates instead of guessing,
     so the user can say which one they meant.

Bounded so it can't turn into an accidental full-disk scan: capped
search depth and a hard cap on how many files it will look at.
"""

from __future__ import annotations

import os
from pathlib import Path

from assistant.logger import get_logger
from tools import files
from tools.applications import IS_WINDOWS, _resolve_executable, open_application

log = get_logger("tools.smart_open")

_SKIP_DIR_NAMES = {
    "node_modules", "__pycache__", ".git", "venv", ".venv",
    "$recycle.bin", "system volume information", ".cache",
}

_MAX_FILES_SCANNED = 20000
_MAX_DEPTH = 4


def _candidate_directories() -> list[Path]:
    """Common places a personal file is likely to live, including the
    OneDrive-redirected versions of Desktop/Documents/Pictures that
    Windows sets up by default on many machines."""
    home = Path.home()
    candidates = [
        home / "Desktop", home / "Documents", home / "Downloads",
        home / "Pictures", home / "Videos", home / "Music",
        home / "OneDrive" / "Desktop", home / "OneDrive" / "Documents",
        home / "OneDrive" / "Pictures",
    ]
    return [d for d in candidates if d.is_dir()]


def _normalize(s: str) -> str:
    """Strip spaces/underscores/hyphens so 'project report' can match
    'project_report.docx' or 'project-report.docx'."""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _search_directories(query: str, directories: list[Path], max_results: int = 5) -> list[str]:
    """Rank files under `directories` by how well their name matches `query`.
    Exact filename match first, then starts-with, then contains, then a
    normalized fuzzy match that ignores spaces/underscores/hyphens."""
    query_lower = query.strip().lower()
    query_stem = Path(query_lower).stem  # handles the user including an extension
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


def smart_open(query: str) -> dict:
    if not query or not query.strip():
        return {"success": False, "message": "No name given to open."}

    if IS_WINDOWS:
        exe = _resolve_executable(query)
        if exe:
            return open_application(query)

    directories = _candidate_directories()
    if not directories:
        return {
            "success": False,
            "message": f"Couldn't find an app matching '{query}', and no searchable folders were found.",
        }

    matches = _search_directories(query, directories)

    if not matches:
        return {
            "success": False,
            "message": f"Couldn't find an app or file matching '{query}' in Desktop, Documents, "
                       f"Downloads, Pictures, Videos, or Music.",
        }

    if len(matches) == 1:
        result = files.open_file(matches[0])
        if result.get("success"):
            result["message"] = f"Found and opened: {matches[0]}"
        return result

    listing = "\n".join(f"  {i + 1}. {m}" for i, m in enumerate(matches))
    log.info(f"'{query}' matched {len(matches)} files; asking user to be specific.")
    return {
        "success": False,
        "message": f"Found {len(matches)} matches for '{query}' — please be more specific:\n{listing}",
        "matches": matches,
    }