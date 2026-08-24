"""
tool_registry.py
-----------------
The single source of truth for every action SHADOW is allowed to take.

The AI brain never executes Python directly — it can only request a
tool by name with arguments. If a tool isn't registered here, it
cannot be called, full stop.
"""

from __future__ import annotations

from typing import Any, Callable

from tools import applications, browser, files

# name -> callable. Every callable must return a dict with at least
# a "success": bool key (tools/*.py already follow this convention).
TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "open_application": applications.open_application,
    "close_application": applications.close_application,
    "is_application_running": applications.is_application_running,

    "open_website": browser.open_website,

    "search_files": files.search_files,
    "create_folder": files.create_folder,
    "create_file": files.create_file,
    "read_file": files.read_file,
    "move_file": files.move_file,
    "copy_file": files.copy_file,
    "rename_file": files.rename_file,
    "delete_file": files.delete_file,
    "delete_folder": files.delete_folder,
    "open_file": files.open_file,
}


def get_tool(name: str) -> Callable[..., dict[str, Any]] | None:
    return TOOLS.get(name)


def list_tools() -> list[str]:
    return sorted(TOOLS.keys())


def tool_specs() -> list[dict]:
    """Lightweight specs for feeding into an LLM's tool-calling schema later.
    Kept hand-written and minimal for Milestone 1 / early Milestone 3."""
    return [
        {"name": "open_application", "description": "Open an application by name (e.g. Chrome, VS Code, Notepad).",
         "parameters": {"name": "string"}},
        {"name": "close_application", "description": "Close a running application by name.",
         "parameters": {"name": "string"}},
        {"name": "is_application_running", "description": "Check if an application is currently running.",
         "parameters": {"name": "string"}},
        {"name": "open_website", "description": "Open a URL in the user's default browser.",
         "parameters": {"url": "string"}},
        {"name": "search_files", "description": "Search a directory for files matching a glob pattern.",
         "parameters": {"directory": "string", "pattern": "string", "recursive": "bool"}},
        {"name": "create_folder", "description": "Create a folder (and parents) at the given path.",
         "parameters": {"path": "string"}},
        {"name": "create_file", "description": "Create a new file with optional text content.",
         "parameters": {"path": "string", "content": "string"}},
        {"name": "read_file", "description": "Read a text file's contents.",
         "parameters": {"path": "string"}},
        {"name": "move_file", "description": "Move a file from source to destination.",
         "parameters": {"source": "string", "destination": "string"}},
        {"name": "copy_file", "description": "Copy a file from source to destination.",
         "parameters": {"source": "string", "destination": "string"}},
        {"name": "rename_file", "description": "Rename a file in place.",
         "parameters": {"path": "string", "new_name": "string"}},
        {"name": "delete_file", "description": "Delete a single file. HIGH RISK — requires confirmation.",
         "parameters": {"path": "string"}},
        {"name": "delete_folder", "description": "Delete a folder and its contents. HIGH RISK — requires confirmation.",
         "parameters": {"path": "string"}},
        {"name": "open_file", "description": "Open a file with its default application.",
         "parameters": {"path": "string"}},
    ]
