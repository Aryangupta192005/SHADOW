"""
safety.py
---------
Classifies every planned action into a risk tier and decides whether
it can run automatically or needs user confirmation.

This module NEVER executes anything itself — it only makes a decision.
The executor is responsible for actually calling the tool, and must
never bypass a HIGH risk confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from assistant.logger import get_logger
from config import CONFIRM_MEDIUM_RISK

log = get_logger("safety")


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# Tool name -> risk level. Anything not listed defaults to HIGH
# (fail safe: unknown tools require confirmation).
TOOL_RISK: dict[str, RiskLevel] = {
    # LOW — read-only or clearly reversible/benign
    "open_application": RiskLevel.LOW,
    "search_files": RiskLevel.LOW,
    "read_file": RiskLevel.LOW,
    "open_website": RiskLevel.LOW,
    "take_screenshot": RiskLevel.LOW,
    "create_folder": RiskLevel.LOW,
    "is_application_running": RiskLevel.LOW,
    "list_directory": RiskLevel.LOW,

    # MEDIUM — changes state but is reversible / low blast-radius
    "close_application": RiskLevel.MEDIUM,
    "move_file": RiskLevel.MEDIUM,
    "copy_file": RiskLevel.MEDIUM,
    "rename_file": RiskLevel.MEDIUM,
    "create_file": RiskLevel.MEDIUM,
    "keyboard_type": RiskLevel.MEDIUM,
    "press_key": RiskLevel.MEDIUM,
    "mouse_click": RiskLevel.MEDIUM,
    "install_package": RiskLevel.MEDIUM,
    "run_script": RiskLevel.MEDIUM,

    # HIGH — destructive, irreversible, or system-altering
    "delete_file": RiskLevel.HIGH,
    "delete_folder": RiskLevel.HIGH,
    "run_terminal_command": RiskLevel.HIGH,  # re-evaluated per-command below
    "shutdown_system": RiskLevel.HIGH,
    "restart_system": RiskLevel.HIGH,
    "modify_registry": RiskLevel.HIGH,
    "change_system_settings": RiskLevel.HIGH,
    "run_unknown_executable": RiskLevel.HIGH,
    "send_message": RiskLevel.HIGH,
    "make_purchase": RiskLevel.HIGH,
}

# Substrings that force a terminal command (or any free-text command) to HIGH,
# even if the tool itself is otherwise MEDIUM.
DANGEROUS_COMMAND_PATTERNS = [
    "del ", "rm ", "remove-item", "rd ", "rmdir",
    "format", "shutdown", "restart-computer", "logoff",
    "reg add", "reg delete", "regedit",
    "diskpart", "bcdedit", "vssadmin",
    "net user", "netsh",
    "> ", ">>",  # redirection that could overwrite files
    "iex ", "invoke-expression",
    "stop-computer",
]


@dataclass
class SafetyDecision:
    risk: RiskLevel
    requires_confirmation: bool
    reason: str


def classify(tool_name: str, arguments: dict) -> SafetyDecision:
    """Determine the risk level of a single planned step and whether
    it needs explicit user confirmation before the executor may run it."""

    risk = TOOL_RISK.get(tool_name, RiskLevel.HIGH)
    reason = f"tool '{tool_name}' default classification"

    if tool_name == "run_terminal_command":
        command = str(arguments.get("command", "")).lower()
        if any(pattern in command for pattern in DANGEROUS_COMMAND_PATTERNS):
            risk = RiskLevel.HIGH
            reason = "command matches a destructive pattern"
        else:
            risk = RiskLevel.MEDIUM
            reason = "terminal command without known destructive pattern"

    if tool_name not in TOOL_RISK and tool_name != "run_terminal_command":
        reason = f"unknown tool '{tool_name}' — defaulting to HIGH for safety"

    requires_confirmation = risk == RiskLevel.HIGH or (
        risk == RiskLevel.MEDIUM and CONFIRM_MEDIUM_RISK
    )

    decision = SafetyDecision(risk=risk, requires_confirmation=requires_confirmation, reason=reason)
    log.info(f"classify tool={tool_name} risk={risk.value} confirm={requires_confirmation} ({reason})")
    return decision


def describe_action(tool_name: str, arguments: dict) -> str:
    """Human-readable one-line description of an action, for confirmation prompts."""
    if tool_name == "delete_file":
        return f"Delete file: {arguments.get('path')}"
    if tool_name == "delete_folder":
        return f"Delete folder (and all contents): {arguments.get('path')}"
    if tool_name == "run_terminal_command":
        return f"Run terminal command: {arguments.get('command')}"
    if tool_name == "move_file":
        return f"Move {arguments.get('source')} -> {arguments.get('destination')}"
    if tool_name == "close_application":
        return f"Close application: {arguments.get('name')}"
    return f"{tool_name}({arguments})"
