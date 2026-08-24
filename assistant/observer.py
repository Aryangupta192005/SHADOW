"""
observer.py
-----------
Verifies that an action actually had the intended effect, beyond just
"the function call didn't raise an exception".

Milestone 1 keeps verification simple: most tools already return a
"success" flag that reflects a real check (e.g. file exists after
create_folder). Where a stronger check is cheap to do here, we do it.

Milestone 5 will extend this with screenshot + vision-based
verification for GUI actions that don't have a structured way to
confirm success.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from assistant.logger import get_logger
from tools.applications import is_application_running

log = get_logger("observer")


@dataclass
class VerificationResult:
    success: bool
    message: str


def verify(tool: str, arguments: dict, result: dict) -> VerificationResult:
    """Given the tool that ran, its arguments, and its raw result dict,
    decide whether the action truly succeeded."""

    if not result.get("success"):
        return VerificationResult(success=False, message=result.get("message", "Action reported failure."))

    # Extra real-world checks beyond the tool's own self-report:
    if tool == "open_application":
        name = arguments.get("name", "")
        check = is_application_running(name)
        if check.get("success") and not check.get("running"):
            return VerificationResult(
                success=False,
                message=f"{name} was launched but doesn't appear to be running yet.",
            )
        return VerificationResult(success=True, message=f"{name} is confirmed running.")

    if tool == "create_folder":
        path = Path(arguments.get("path", "")).expanduser()
        if not path.is_dir():
            return VerificationResult(success=False, message=f"Folder does not exist after creation: {path}")
        return VerificationResult(success=True, message=f"Confirmed folder exists: {path}")

    if tool in ("create_file", "move_file", "copy_file", "rename_file"):
        # These tools already check existence themselves; trust their message.
        return VerificationResult(success=True, message=result.get("message", "OK"))

    if tool in ("delete_file", "delete_folder"):
        path = Path(arguments.get("path", "")).expanduser()
        if path.exists():
            return VerificationResult(success=False, message=f"Path still exists after delete: {path}")
        return VerificationResult(success=True, message=f"Confirmed deleted: {path}")

    # Default: trust the tool's own success flag.
    return VerificationResult(success=True, message=result.get("message", "OK"))
